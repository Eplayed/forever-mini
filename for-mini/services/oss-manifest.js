/* OSS 分发层 · 客户端契约（与 tools/oss-release.js 产出的批次一一对应）
   ------------------------------------------------------------------
   为什么单独一个文件：PoE 那条线把 bucket 地址硬编码散在 11 个页面里，
   新旧前缀三套并存，清单拿不到就静默回退旧地址，用户读到上一代数据还不显示。
   这一层把取数收在一个口子，任何一次读取都必须说清四件事：
     1) 这批数据是不是线上当前批：source = live / cache / snapshot / none
        （cache 只在"指针也取不到、只能用本地存的那一份"时出现；
          指针在线、数据命中同批缓存 = live + cacheHit，不叫离线）
     2) 是哪一批：buildId（写进缓存 key，也逐份回读校验，旧批不可能冒充新批）
     3) 内容对不对得上清单：每个文件按批次清单里记的 ETag + 字节数 + buildId +
        kind + ID 五项校验，任一项不符整条当失败（见 checkIntegrity）
     4) 核对到什么时候：factDates（数据里的真实核对日期，不是构建时间）

   界面义务：source !== 'live' 必须显式提示，不许静默呈现（for-mini/AGENTS.md）。
   完整口径（包含"这不是抗伪造签名"那层坦白）写在批次清单的 integrity 段里。

   用法（页面里）：
     const oss = require('../services/oss-manifest')
     oss.loadKey('dungeonIndex', { fallback: SNAPSHOT_INDEX }).then((r) => {
       // r.data / r.source / r.cacheHit / r.buildId / r.factDates / r.requiresUpdate / r.batch
       return oss.loadDungeonDetail(item, r.batch)   // r.batch 把整条查询钉在同一批
     }) */

const OSS_ORIGIN = 'https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com'
const NAMESPACES = { beta: 'wow/beta/v1', release: 'wow/release/v1' }

/* 站点主线上批次没发之前，先跑 beta；改成 release 是唯一需要动的开关。 */
const ACTIVE_ENV = 'beta'

/* 客户端能读的数据契约版本；比 manifest.minClientSchemaVersion 小就要提示更新小程序 */
const CLIENT_SCHEMA_VERSION = 1
const PRODUCT = 'wow-forever-mini'

const CACHE_PREFIX = 'wow_forever_v1_'
const POINTER_TTL_MS = 5 * 60 * 1000
const BUILDS_INDEX_KEY = CACHE_PREFIX + 'builds_seen'
const MAX_KEEP_BUILDS = 2

const SOURCE_TEXT = {
  live: '实时数据',
  cache: '离线缓存',
  snapshot: '打包快照',
  none: '没取到数据'
}

const BUILD_ID_RE = /^[a-f0-9]{12}$/
const ETAG_RE = /^[0-9A-F]{32}$/

/* 开发者工具用的取数地址覆盖：storage 里写 wow_forever_v1_dev_origin = http://127.0.0.1:8899
   就改打本地假 OSS（tools/oss-fake-server.js 起的那一个），用来验 live 路径与 ETag 校验。
   为什么放 storage 而不是编译期常量：线上真机这个 key 不存在，走的是原来的 OSS_ORIGIN；
   而且微信线上域名白名单只放 https 的备案域，http://127.0.0.1 在真机上根本发不出去。 */
const DEV_ORIGIN_KEY = CACHE_PREFIX + 'dev_origin'
function origin() {
  try {
    const o = wx.getStorageSync(DEV_ORIGIN_KEY)
    if (o && /^(https?:)?\/\//.test(String(o))) return String(o).replace(/\/+$/, '')
  } catch (error) {}
  return OSS_ORIGIN
}

function pointerUrl(env) {
  return origin() + '/' + NAMESPACES[env] + '/manifest.json'
}

function requestRaw(url) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: url,
      method: 'GET',
      dataType: 'json',
      timeout: 10000,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300 && res.data) {
          resolve(res)
          return
        }
        reject(new Error('HTTP ' + res.statusCode + ': ' + url))
      },
      fail: reject
    })
  })
}

function readStore(key) {
  try {
    return wx.getStorageSync(key) || null
  } catch (error) {
    return null
  }
}

function writeStore(key, payload) {
  try {
    wx.setStorageSync(key, payload)
  } catch (error) {
    /* 写失败只影响下次断网有没有兜底，本次照常返回 */
  }
}

/* buildId 进 key：这是"旧缓存不会冒充新数据"的唯一硬保证，
   所以不能只按文件名缓存（PoE 那边就是这么踩的）。 */
function cacheKey(kind, buildId) {
  return CACHE_PREFIX + kind + '@' + buildId
}

function noteBuild(env, buildId) {
  const seen = readStore(BUILDS_INDEX_KEY) || {}
  const list = seen[env] || []
  if (list.indexOf(buildId) < 0) list.unshift(buildId)
  const keep = list.slice(0, MAX_KEEP_BUILDS)
  /* 清掉不再保留的旧批缓存：小程序 storage 只有 10 MB */
  let info = null
  try { info = wx.getStorageInfoSync() } catch (error) { info = null }
  const keys = info && info.keys ? info.keys : []
  keys.forEach((k) => {
    if (k.indexOf(CACHE_PREFIX) !== 0) return
    if (k.indexOf(CACHE_PREFIX + 'pointer@') === 0) return
    if (k.indexOf('@') < 0) return
    const parts = k.split('@')
    const id = parts[parts.length - 1]
    if (keep.indexOf(id) < 0) {
      try { wx.removeStorageSync(k) } catch (error) {}
    }
  })
  seen[env] = keep
  writeStore(BUILDS_INDEX_KEY, seen)
}

function headerGet(header, name) {
  if (!header) return ''
  const k = Object.keys(header).filter((x) => String(x).toLowerCase() === name)[0]
  return k === undefined ? '' : header[k]
}
const normEtag = (header) => String(headerGet(header, 'etag')).replace(/"/g, '').toUpperCase()

/* —— 指针：线上 → 缓存 → null ——
   线上取回来但结构不对，不能当"正常空数据"：那会让有缓存的用户白白掉到打包快照。
   所以非法指针优先退回本地上一份合法的，并如实标 pointerSource:'invalid'。 */
function validatePointer(m, env) {
  if (!m || typeof m !== 'object') return '指针不是对象'
  if (m.product !== PRODUCT) return '指针的 product 是 ' + m.product
  if (m.schemaVersion > CLIENT_SCHEMA_VERSION) return '指针契约版本 ' + m.schemaVersion + ' 比客户端新'
  if (m.env !== env) return '指针的 env 是 ' + m.env + '，请求的是 ' + env
  if (m.namespace !== NAMESPACES[env]) return '指针的 namespace 是 ' + m.namespace
  if (!BUILD_ID_RE.test(String(m.buildId))) return '指针的 buildId 形制不对：' + m.buildId
  if (!m.fetch || !m.bundle) return '指针缺 fetch 或 bundle'
  const inBatch = (p) => String(p || '').indexOf('builds/' + m.buildId + '/') === 0
  if (!inBatch(m.bundle.path)) return 'files.json 不在本批目录下：' + m.bundle.path
  if (!ETAG_RE.test(String(m.bundle.etag || '')) || !m.bundle.sha256) return 'files.json 缺校验值'
  const missing = ['meta', 'glossary', 'dungeonIndex'].filter((k) =>
    !m.fetch[k] || !inBatch(m.fetch[k].path) || !ETAG_RE.test(String(m.fetch[k].etag || '')) || !(m.fetch[k].bytes > 0))
  if (missing.length) return '指针入口文件缺 etag/bytes 或路径越批：' + missing.join(',')
  return null
}

function loadPointer(env) {
  const targetEnv = env || ACTIVE_ENV
  const key = CACHE_PREFIX + 'pointer@' + targetEnv
  const cached = readStore(key)
  return requestRaw(pointerUrl(targetEnv))
    .then((res) => {
      const manifest = res.data
      const why = validatePointer(manifest, targetEnv)
      if (why) {
        if (cached && cached.manifest && !validatePointer(cached.manifest, targetEnv)) {
          return { manifest: cached.manifest, source: 'cache', pointerSource: 'invalid', stale: true, error: new Error('线上指针不可用：' + why) }
        }
        return { manifest: null, source: 'invalid', pointerSource: 'invalid', error: new Error('线上指针不可用：' + why) }
      }
      writeStore(key, { manifest, at: Date.now() })
      noteBuild(targetEnv, manifest.buildId)
      return { manifest, source: 'live', pointerSource: 'live', stale: false, error: null }
    })
    .catch((error) => {
      if (cached && cached.manifest && !validatePointer(cached.manifest, targetEnv)) {
        return { manifest: cached.manifest, source: 'cache', pointerSource: 'cache', stale: Date.now() - cached.at > POINTER_TTL_MS, error }
      }
      return { manifest: null, source: 'none', pointerSource: 'none', error }
    })
}

function resolveUrl(manifest, relPath) {
  return origin() + '/' + NAMESPACES[manifest.env] + '/' + relPath
}

/* 索引条目里的 detailPath/lootPath 是相对批次目录的，指针里的 fetch/bundle 是相对命名空间根的。
   批次目录 = builds/{buildId}/，所以取分片一律先过这一层，别自己拼。 */
function batchPath(batch, relInBatch) {
  return 'builds/' + batch.buildId + '/' + relInBatch
}

function requiresUpdate(manifest) {
  return !!manifest && (manifest.minClientSchemaVersion || 0) > CLIENT_SCHEMA_VERSION
}

/* 把"这一批"钉成一个对象交给页面，之后取详情/掉落都拿它，不再读新指针 */
function makeBatch(manifest, pointerSource, stale) {
  return {
    buildId: manifest.buildId,
    env: manifest.env,
    product: manifest.product,
    schemaVersion: manifest.schemaVersion,
    factDates: manifest.factDates || null,
    minClientSchemaVersion: manifest.minClientSchemaVersion || 1,
    pointerSource: pointerSource || 'live',
    stale: !!stale,
    integrity: manifest.integrity || null
  }
}

/* 五项校验：清单值（etag/bytes）+ 内容自证（buildId/kind/id）。
   任何一项不符就 throw，由上层按缓存/快照降级，绝不把对不上的内容当 live 端给界面。 */
function checkIntegrity(res, expect, spec, batch) {
  const reasons = []
  const etag = normEtag(res.header)
  if (!expect || !expect.etag || !ETAG_RE.test(String(expect.etag).toUpperCase())) reasons.push('清单里没有这一份的校验值')
  else if (!etag) reasons.push('响应没有 ETag，无法确认字节')
  else if (etag !== String(expect.etag).toUpperCase()) reasons.push('ETag 与清单不符（线上 ' + etag + ' ≠ 清单 ' + expect.etag + '）')
  const len = Number(headerGet(res.header, 'content-length') || 0)
  if (expect.bytes > 0 && len > 0 && len !== expect.bytes) reasons.push('字节数与清单不符（' + len + ' ≠ ' + expect.bytes + '）')
  const data = res.data
  if (!data || typeof data !== 'object' || Array.isArray(data)) reasons.push('内容不是一个对象')
  else {
    if (data.product !== PRODUCT) reasons.push('product 是 ' + data.product)
    if (data.schemaVersion > CLIENT_SCHEMA_VERSION) reasons.push('契约版本 ' + data.schemaVersion + ' 比客户端新')
    if (!BUILD_ID_RE.test(String(data.buildId))) reasons.push('分片没有合法 buildId：' + data.buildId)
    else if (data.buildId !== batch.buildId) reasons.push('分片批次 ' + data.buildId + ' ≠ 指针 ' + batch.buildId)
    if (spec.kind && data.kind !== spec.kind) reasons.push('类型是 ' + data.kind + '，不是 ' + spec.kind)
    if (spec.id) {
      const got = spec.readId(data)
      if (got !== spec.id) reasons.push('内容里的 ID 是 ' + got + '，请求的是 ' + spec.id)
    }
    if (spec.shape && !spec.shape(data)) reasons.push('结构不对（' + spec.name + '）')
  }
  return reasons
}

/* 取一份数据并校验。expect = {etag,bytes}，spec 描述该文件自带的身份字段。 */
function loadShard(batch, relPath, cacheKind, expect, spec, fallback, p) {
  const offlinePointer = p.source !== 'live'
  const key = cacheKey(cacheKind, batch.buildId)
  const hit = readStore(key)
  const hitUsable = !!(hit && hit.data && String(hit.data.buildId) === String(batch.buildId))
  const liveSource = offlinePointer ? 'cache' : 'live'
  const base = {
    buildId: batch.buildId,
    factDates: batch.factDates,
    requiresUpdate: batch.minClientSchemaVersion > CLIENT_SCHEMA_VERSION,
    pointerSource: p.pointerSource || p.source,
    stale: !!p.stale,
    batch
  }
  if (hitUsable) {
    /* 同批已有缓存就不再打网络：这是 PRD 里"读请求尽量只取索引"的落点。
       批次仍是线上当前批，所以 source 还是 live，只多带一个 cacheHit 说明字节没重新下。 */
    return Promise.resolve(Object.assign({}, base, { data: hit.data, source: liveSource, cacheHit: true, bytes: 0, etag: hit.etag || null }))
  }
  return requestRaw(resolveUrl({ env: batch.env }, relPath)).then((res) => {
    const reasons = checkIntegrity(res, expect, spec, batch)
    if (reasons.length) {
      const err = new Error('校验不过：' + reasons.join('；'))
      if (hitUsable) return Object.assign({}, base, { data: hit.data, source: liveSource, cacheHit: true, integrityError: true, error: err })
      if (fallback) return Object.assign({}, base, { data: fallback, source: 'snapshot', cacheHit: false, integrityError: true, error: err })
      return Object.assign({}, base, { data: null, source: 'none', cacheHit: false, integrityError: true, error: err })
    }
    writeStore(key, { data: res.data, at: Date.now(), buildId: batch.buildId, etag: normEtag(res.header) })
    /* 字节是刚从线上取的，但批次身份来自哪一级指针决定它算不算"实时"：
       指针都取不到时，即便这一份下载成功，也只是"上一份已知批次"的内容 → cache */
    return Object.assign({}, base, {
      data: res.data, source: liveSource, cacheHit: false,
      bytes: Number(headerGet(res.header, 'content-length') || expect.bytes || 0), etag: normEtag(res.header)
    })
  }).catch((error) => {
    if (hitUsable) return Object.assign({}, base, { data: hit.data, source: liveSource, cacheHit: true, error })
    if (fallback) return Object.assign({}, base, { data: fallback, source: 'snapshot', cacheHit: false, buildId: null, error })
    return Object.assign({}, base, { data: null, source: 'none', cacheHit: false, buildId: null, error })
  })
}

const SHARD_SPECS = {
  meta: { name: 'meta', kind: 'batch-meta', shape: (d) => !!d.counts && !!d.coverage },
  glossary: { name: 'glossary', kind: 'glossary', shape: (d) => Array.isArray(d.items) },
  dungeonIndex: {
    name: 'dungeon-index',
    kind: 'dungeon-index',
    shape: (d) => Array.isArray(d.items) && !!d.counts && d.counts.total === d.items.length
  }
}

function loadKey(kind, opts) {
  const options = opts || {}
  return loadPointer(options.env).then((p) => {
    const fallback = options.fallback || null
    if (!p.manifest) {
      return {
        data: fallback,
        source: fallback ? 'snapshot' : 'none',
        buildId: null,
        factDates: null,
        requiresUpdate: false,
        cacheHit: false,
        pointerSource: p.pointerSource || p.source,
        stale: false,
        batch: null,
        error: p.error
      }
    }
    const batch = makeBatch(p.manifest, p.pointerSource || p.source, p.stale)
    const f = p.manifest.fetch[kind]
    if (!f) {
      return {
        data: fallback,
        source: fallback ? 'snapshot' : 'none',
        buildId: batch.buildId,
        factDates: batch.factDates,
        requiresUpdate: requiresUpdate(p.manifest),
        cacheHit: false,
        pointerSource: p.pointerSource || p.source,
        stale: !!p.stale,
        batch,
        error: new Error('指针里没有 ' + kind)
      }
    }
    const spec = SHARD_SPECS[kind]
    if (!spec) {
      return Object.assign({}, { data: fallback, source: fallback ? 'snapshot' : 'none', batch, pointerSource: p.source },
        { buildId: batch.buildId, factDates: batch.factDates, requiresUpdate: requiresUpdate(p.manifest), cacheHit: false, stale: !!p.stale, pointerSource: p.pointerSource || p.source, error: new Error('客户端不认识的分片类型 ' + kind) })
    }
    return loadShard(batch, f.path, kind, f, Object.assign({ id: null }, spec), fallback, p)
  })
}

/* 索引条目自带 detailPath/lootPath 与两份分片的校验值。
   路径一律由 id 重新推导并与条目比对：条目被改成 ../.. 也走不出去。 */
function shardRef(item, which) {
  const rel = 'dungeons/' + (which === 'detail' ? 'detail/' : 'loot/') + item.id + '.json'
  if (String(which === 'detail' ? item.detailPath : item.lootPath) !== rel) {
    return { error: new Error('索引条目 ' + item.id + ' 的 ' + which + ' 路径不是由 id 推出来的：' + (which === 'detail' ? item.detailPath : item.lootPath)) }
  }
  return {
    rel,
    cacheKind: 'dungeon-' + which + ':' + item.id,
    expect: { etag: which === 'detail' ? item.detailEtag : item.lootEtag, bytes: which === 'detail' ? item.detailBytes : item.lootBytes },
    spec: {
      name: 'dungeon-' + which,
      kind: 'dungeon-' + which,
      id: item.id,
      readId: which === 'detail' ? (d) => (d.dungeon ? d.dungeon.id : null) : (d) => d.dungeonId
    }
  }
}

function loadByRef(item, which, batch, fallback) {
  const p = contextOf(batch)
  if (!batch || !batch.buildId || !BUILD_ID_RE.test(String(batch.buildId))) {
    return Promise.resolve({
      data: fallback || null, source: fallback ? 'snapshot' : 'none', buildId: null, factDates: batch ? batch.factDates : null,
      requiresUpdate: false, cacheHit: false, pointerSource: p.source, stale: p.stale, batch: batch || null,
      error: new Error('没有可用的批次上下文')
    })
  }
  const ref = shardRef(item, which)
  if (ref.error) {
    return Promise.resolve({
      data: fallback || null, source: fallback ? 'snapshot' : 'none', buildId: batch.buildId, factDates: batch.factDates,
      requiresUpdate: batch.minClientSchemaVersion > CLIENT_SCHEMA_VERSION, cacheHit: false, integrityError: true,
      pointerSource: p.source, stale: p.stale, batch, error: ref.error
    })
  }
  return loadShard(batch, batchPath(batch, ref.rel), ref.cacheKind, ref.expect, ref.spec, fallback || null, p)
}

function contextOf(batch) {
  if (batch && batch.pointerSource) return { source: batch.pointerSource, stale: !!batch.stale }
  return { source: 'none', stale: false }
}

function loadDungeonDetail(item, batch, fallback) {
  return loadByRef(item, 'detail', batch, fallback)
}

function loadDungeonLoot(item, batch, fallback) {
  return loadByRef(item, 'loot', batch, fallback)
}

/* 逐文件哈希表：正常取数不需要它（校验值已随指针与索引下发），
   留给排障与"把整批核一遍"的场景。 */
function loadBundle(manifest) {
  const batch = makeBatch(manifest, 'live', false)
  return loadShard(batch, manifest.bundle.path, 'bundle', manifest.bundle,
    { name: 'batch-files', kind: 'batch-files', shape: (d) => !!d.files && Object.keys(d.files).length > 0 }, null, { source: 'live', stale: false })
}

function sourceLabel(r) {
  if (!r) return SOURCE_TEXT.none
  if (r.source === 'live') return r.cacheHit ? '实时数据（本机缓存，没重新下载）' : SOURCE_TEXT.live
  if (r.source === 'cache') return '离线缓存（连不上线上清单）'
  if (r.source === 'snapshot') return SOURCE_TEXT.snapshot
  return SOURCE_TEXT.none
}

module.exports = {
  ACTIVE_ENV,
  CACHE_PREFIX,
  CLIENT_SCHEMA_VERSION,
  NAMESPACES,
  OSS_ORIGIN,
  PRODUCT,
  SOURCE_TEXT,
  batchPath,
  cacheKey,
  loadBundle,
  loadDungeonDetail,
  loadDungeonLoot,
  loadKey,
  loadPointer,
  pointerUrl,
  requiresUpdate,
  resolveUrl,
  sourceLabel,
  validatePointer
}
