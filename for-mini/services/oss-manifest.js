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

/* 功能开关对象（2026-10-27）：与指针同一档缓存语义，但它不在气密批次里——
   拧开关不换 buildId、不重发数据，也不发小程序版本。取数与校验归 services/features.js。 */
function flagsUrl(env) {
  return origin() + '/' + NAMESPACES[env] + '/flags.json'
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

/* —— 素材地址（M02）——
   图片走 <image> 组件，不在 wx.request 白名单范围内，所以不做 ETag 校验：
   能校验的是"路径不许越出 assets/"。拼出来的地址只允许
   {origin}/{namespace}/assets/... 这一种形状，出现 img/ 、绝对地址或 ../ 一律不给拼。 */
const ASSET_KEY_RE = /^[A-Za-z0-9][A-Za-z0-9._/-]*$/
function assetBase(batch) {
  const dir = (batch && batch.assets && batch.assets.dir) || 'assets/'
  return origin() + '/' + NAMESPACES[batch.env] + '/' + dir
}
function assetUrl(batch, rel) {
  const r = String(rel || '')
  /* 站内相对路径（img/ 开头）绝不能拼进来：那是网页端的地址，小程序里必然 404 */
  if (!batch || !batch.env || !ASSET_KEY_RE.test(r) || r.indexOf('..') >= 0
    || r.indexOf('img/') === 0 || r.indexOf('/img/') >= 0) return ''
  return assetBase(batch) + r
}
function iconUrl(batch, key) {
  const k = String(key || '')
  const ext = (batch && batch.assets && batch.assets.iconExt) || '.jpg'
  if (!k || !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(k)) return ''
  return assetUrl(batch, 'icons/' + k + ext)
}

/* 种族那一格的图（2026-10-23 站主定稿）：一律用素材层里 `art/races/` 那批 128 客户端种族头像，
   由分发层的 raceEntry() 放进 `portrait`；官方 CDN 的 `iconKey` 只作兜底
   （某族连大图都没有时才用它拼一张）。
   为什么不再优先官方 CDN 那张 56：同一排里 9 张 56 + 1 张 128 会明显两样，
   站主看完实拍说「10 个统一都换成大图」——口径记在根 AGENTS.md 2026-10-23 那一节。
   两个都没有就返回空串，界面回落自绘首字块，不留碎图。 */
function raceIconUrl(batch, race) {
  const r = race || {}
  return assetUrl(batch, r.portrait) || iconUrl(batch, r.iconKey)
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
    integrity: manifest.integrity || null,
    assets: manifest.assets || null
  }
}

/* 五项校验：清单值（etag/bytes）+ 内容自证（buildId/kind/id）。
   任何一项不符就 throw，由上层按缓存/快照降级，绝不把对不上的内容当 live 端给界面。 */
/* 优先 Content-MD5（base64）：真 bucket 上 wx.request 收到 gzip 变体时 ETag 会被按 HTTP 规则剥掉，
   而 Content-MD5 是对象存储的原始字节 MD5，不受传输编码影响。两个都没有才算验不了。 */
function normB64(v) { return String(v || '').replace(/\s+/g, '') }
function checkIntegrity(res, expect, spec, batch) {
  const reasons = []
  const md5 = normB64(headerGet(res.header, 'content-md5'))
  const etag = normEtag(res.header)
  if (!expect || (!expect.md5 && !expect.etag)) reasons.push('清单里没有这一份的校验值')
  else if (expect.md5 && !md5 && !etag) reasons.push('响应既没有 Content-MD5 也没有 ETag，无法确认字节')
  else if (expect.md5 && md5 && md5 !== normB64(expect.md5)) reasons.push('Content-MD5 与清单不符（线上 ' + md5 + ' ≠ 清单 ' + expect.md5 + '）')
  else if (expect.md5 && !md5 && etag && etag !== String(expect.etag).toUpperCase()) reasons.push('ETag 与清单不符（线上 ' + etag + ' ≠ 清单 ' + expect.etag + '）')
  else if (!expect.md5 && (!etag || etag !== String(expect.etag).toUpperCase())) reasons.push('ETag 与清单不符（线上 ' + etag + ' ≠ 清单 ' + expect.etag + '）')
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
    writeStore(key, { data: res.data, at: Date.now(), buildId: batch.buildId, etag: normEtag(res.header), md5: normB64(headerGet(res.header, 'content-md5')) })
    /* 字节是刚从线上取的，但批次身份来自哪一级指针决定它算不算"实时"：
       指针都取不到时，即便这一份下载成功，也只是"上一份已知批次"的内容 → cache */
    return Object.assign({}, base, {
      data: res.data, source: liveSource, cacheHit: false,
      bytes: Number(headerGet(res.header, 'content-length') || expect.bytes || 0), etag: normEtag(res.header), md5: normB64(headerGet(res.header, 'content-md5'))
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
  },
  spellClasses: {
    name: 'spell-class-index',
    kind: 'spell-class-index',
    shape: (d) => Array.isArray(d.classes) && !!d.counts && d.counts.classes === d.classes.length
  },
  classIndex: {
    name: 'class-index',
    kind: 'class-index',
    shape: (d) => Array.isArray(d.races) && Array.isArray(d.classes) && !!d.counts
      && d.counts.races === d.races.length && d.counts.classes === d.classes.length
  },
  guide: {
    name: 'guide',
    kind: 'guide',
    shape: (d) => Array.isArray(d.macros) && Array.isArray(d.addons)
  },
  /* 配装索引：套数与 classes 里各套数加起来必须等于 sets；口径那一句必须在
     （它是红线要求界面固定显示的，谁把它从索引里漏掉，页面就只能自己编一句） */
  bisIndex: {
    name: 'bis-index',
    kind: 'bis-index',
    shape: (d) => Array.isArray(d.sets) && Array.isArray(d.classes) && !!d.meta
      && !!d.meta.disclaimer && d.meta.disclaimer.indexOf('不是官方结论') >= 0
      && d.classes.reduce((n, c) => n + (c.sets || []).length, 0) === d.sets.length
      && !!d.slotKeys
  },
  /* 共享物品表：列名 6 列、count 与行数一致（位置数组，列名漂了界面就会把装等当品质） */
  bisItems: {
    name: 'bis-items',
    kind: 'bis-items',
    shape: (d) => Array.isArray(d.items) && Array.isArray(d.cols) && d.cols.length === 6
      && d.count === d.items.length
  },
  /* 专业索引：专业数、配方数都要与逐条数对上；列名与分箱在这里带一份（分片不再各抄一遍）；
     口径那一句必须在——红线要求界面固定显示，谁把它漏掉，页面就只能自己编一句 */
  professionsIndex: {
    name: 'professions-index',
    kind: 'professions-index',
    shape: (d) => Array.isArray(d.professions) && !!d.counts && !!d.meta
      && d.counts.professions === d.professions.length
      && d.counts.recipes === d.professions.reduce((s, p) => s + ((p.counts || {}).recipes || 0), 0)
      && Array.isArray(d.bands) && Array.isArray(d.skillKeys)
      && !!d.cols && Array.isArray(d.cols.recipe) && Array.isArray(d.cols.node)
      && Array.isArray(d.cols.sk) && !!d.meta.title
      && !!d.meta.disclaimer && d.meta.disclaimer.indexOf('不给掉率') >= 0
  },
  lootIndex: {
    name: 'loot-index',
    kind: 'loot-index',    /* 行数与列数都要对上：列名是位置数组的解释，少一列界面就会把首领序号当品质显示 */
    shape: (d) => Array.isArray(d.dungeons) && Array.isArray(d.cols) && d.cols.length === 6
      && !!d.counts && d.counts.rows === d.dungeons.reduce((s, x) => s + (x.rows || []).length, 0)
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
const SHARD_KINDS = {
  detail: { dir: 'detail/', pathKey: 'detailPath', etag: 'detailEtag', md5: 'detailMd5', bytes: 'detailBytes', readId: (d) => (d.dungeon ? d.dungeon.id : null) },
  loot: { dir: 'loot/', pathKey: 'lootPath', etag: 'lootEtag', md5: 'lootMd5', bytes: 'lootBytes', readId: (d) => d.dungeonId }
}

function shardRef(item, which) {
  const k = SHARD_KINDS[which]
  if (!k) return { error: new Error('不认识的分片类型 ' + which) }
  const rel = 'dungeons/' + k.dir + item.id + '.json'
  if (String(item[k.pathKey]) !== rel) {
    return { error: new Error('索引条目 ' + item.id + ' 的 ' + which + ' 路径不是由 id 推出来的：' + item[k.pathKey]) }
  }
  return {
    rel,
    cacheKind: 'dungeon-' + which + ':' + item.id,
    expect: { etag: item[k.etag], md5: item[k.md5], bytes: item[k.bytes] },
    spec: {
      name: 'dungeon-' + which,
      kind: 'dungeon-' + which,
      id: item.id,
      readId: k.readId
    }
  }
}

function loadRef(ref, batch, fallback) {
  const p = contextOf(batch)
  if (!batch || !batch.buildId || !BUILD_ID_RE.test(String(batch.buildId))) {
    return Promise.resolve({
      data: fallback || null, source: fallback ? 'snapshot' : 'none', buildId: null, factDates: batch ? batch.factDates : null,
      requiresUpdate: false, cacheHit: false, pointerSource: p.source, stale: p.stale, batch: batch || null,
      error: new Error('没有可用的批次上下文')
    })
  }
  if (ref.error) {
    return Promise.resolve({
      data: fallback || null, source: fallback ? 'snapshot' : 'none', buildId: batch.buildId, factDates: batch.factDates,
      requiresUpdate: batch.minClientSchemaVersion > CLIENT_SCHEMA_VERSION, cacheHit: false, integrityError: true,
      pointerSource: p.source, stale: p.stale, batch, error: ref.error
    })
  }
  return loadShard(batch, batchPath(batch, ref.rel), ref.cacheKind, ref.expect, ref.spec, fallback || null, p)
}

function loadByRef(item, which, batch, fallback) {
  return loadRef(shardRef(item, which), batch, fallback)
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

/* 配装：38 套各一片，点开哪套取哪片；共享物品表随索引一次下发（进这一页才要）。
   与副本分片同一套规矩——路径由 setId 现推并与索引条目的 path 比对，
   校验值取条目自带的 shardEtag/shardMd5/shardBytes，条目被改成 ../ 也走不出本批目录。 */
function bisSetRef(item) {
  const id = String((item && item.id) || '')
  if (!/^[a-z][a-z0-9_-]*$/.test(id)) return { error: new Error('配装套编号不能当文件名：' + id) }
  const rel = 'bis/set/' + id + '.json'
  if (String(item.path) !== rel) {
    return { error: new Error('配装 ' + id + ' 的分片路径不是由编号推出来的：' + item.path) }
  }
  return {
    rel,
    cacheKind: 'bis-set:' + id,
    expect: { etag: item.shardEtag, md5: item.shardMd5, bytes: item.shardBytes },
    spec: {
      name: 'bis-set',
      kind: 'bis-set',
      id,
      readId: (d) => d.setId,
      /* 两个阵营都得有 doll，且每行是 [部位, 序号, 物品 ID] 三格 */
      shape: (d) => !!d.byFac && !!d.byFac.alliance && !!d.byFac.horde
        && Array.isArray(d.byFac.alliance.doll) && Array.isArray(d.byFac.horde.doll)
        && d.byFac.alliance.doll.every((r) => r.length === 3)
    }
  }
}

function loadBisSet(item, batch, fallback) {
  return loadRef(bisSetRef(item), batch, fallback)
}

/* 专业分片：与配装那一片同一套规矩——路径由专业 id 现推、与索引条目里的 path 比对，
   校验值取条目自带的 shardEtag/shardMd5/shardBytes。
   这里的 shape 只查"行是不是齐长的位置数组"；行到底几列、哪列是什么，
   由索引的 cols 解释，页面在解码前把列数与行长对一遍（列名漂了会把品质当材料序号）。 */
function profSetRef(item) {
  const id = String((item && item.id) || '')
  if (!/^[a-z][a-z0-9_-]*$/.test(id)) return { error: new Error('专业编号不能当文件名：' + id) }
  const rel = 'professions/set/' + id + '.json'
  if (String(item.path) !== rel) {
    return { error: new Error('专业 ' + id + ' 的分片路径不是由编号推出来的：' + item.path) }
  }
  const sameLen = (rows) => Array.isArray(rows) && (rows.length === 0
    || rows.every((r) => Array.isArray(r) && r.length === rows[0].length))
  return {
    rel,
    cacheKind: 'prof-set:' + id,
    expect: { etag: item.shardEtag, md5: item.shardMd5, bytes: item.shardBytes },
    spec: {
      name: 'professions-set',
      kind: 'professions-set',
      id,
      readId: (d) => d.profId,
      /* 这里只查"行是齐长的位置数组"；一行有几列、哪列是材料，由索引的 cols 解释，
         页面解码时按列名再核一遍（序号在这里写死等于把列名抄第二份，抄两份必然飘） */
      shape: (d) => sameLen(d.recipes) && sameLen(d.nodes) && Array.isArray(d.icons) && Array.isArray(d.mats)
        && Array.isArray(d.vendors) && Array.isArray(d.drops) && Array.isArray(d.sources)
        && !!d.counts && d.counts.recipes === (d.recipes || []).length
        && d.counts.nodes === (d.nodes || []).length
    }
  }
}

function loadProfSet(item, batch, fallback) {
  return loadRef(profSetRef(item), batch, fallback)
}

/* 职业法术片：和副本分片同一套规矩——路径由 classId 现推，与名单条目里的 shardPath 比对，
   校验值取条目自带的 shardEtag/shardMd5/shardBytes。条目被改成 ../ 也走不出本批目录。 */
function spellClassRef(item) {
  const id = String((item && item.classId) || '')
  if (!/^[a-z][a-z0-9_-]*$/.test(id)) return { error: new Error('职业编号不能当文件名：' + id) }
  const rel = 'spells/class/' + id + '.json'
  if (String(item.shardPath) !== rel) {
    return { error: new Error('职业 ' + id + ' 的分片路径不是由 classId 推出来的：' + item.shardPath) }
  }
  return {
    rel,
    cacheKind: 'spell-class:' + id,
    expect: { etag: item.shardEtag, md5: item.shardMd5, bytes: item.shardBytes },
    spec: {
      name: 'spell-class',
      kind: 'spell-class',
      id,
      readId: (d) => d.classId,
      shape: (d) => Array.isArray(d.spells) && d.spells.length === item.count
    }
  }
}

function loadSpellClass(item, batch, fallback) {
  return loadRef(spellClassRef(item), batch, fallback)
}

/* 天赋片：与职业法术片同一套规矩——路径由 classId 现推、与名单里的 shardPath 比对、
   校验值取条目自带的三个字段。名单里 shardPath 为 null 的职业（没有天赋树）直接判失败，不发请求。 */
function talentClassRef(item) {
  const id = String((item && item.classId) || '')
  if (!/^[a-z][a-z0-9_-]*$/.test(id)) return { error: new Error('职业编号不能当文件名：' + id) }
  const rel = 'talents/class/' + id + '.json'
  if (!item.shardPath) return { error: new Error('职业 ' + id + ' 在名单里没有天赋分片') }
  if (String(item.shardPath) !== rel) {
    return { error: new Error('职业 ' + id + ' 的天赋分片路径不是由 classId 推出来的：' + item.shardPath) }
  }
  return {
    rel,
    cacheKind: 'talent-class:' + id,
    expect: { etag: item.shardEtag, md5: item.shardMd5, bytes: item.shardBytes },
    spec: {
      name: 'talent-class',
      kind: 'talent-class',
      id,
      readId: (d) => d.classId,
      shape: (d) => Array.isArray(d.trees) && d.trees.length > 0
        && d.trees.every((t) => Array.isArray(t.nodes))
    }
  }
}

function loadTalentClass(item, batch, fallback) {
  return loadRef(talentClassRef(item), batch, fallback)
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
  bisSetRef,
  loadBisSet,
  profSetRef,
  loadProfSet,
  flagsUrl,
  requestRaw,
  loadDungeonDetail,
  loadDungeonLoot,
  loadKey,
  loadPointer,
  loadSpellClass,
  loadTalentClass,
  spellClassRef,
  talentClassRef,
  pointerUrl,
  requiresUpdate,
  resolveUrl,
  sourceLabel,
  assetBase,
  assetUrl,
  iconUrl,
  raceIconUrl,
  validatePointer
}
