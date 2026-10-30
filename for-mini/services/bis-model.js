/* BiS 真实 3D 的取数契约（2026-10-30 C 段）
   ------------------------------------------------------------------
   站主 2026-10-30 定的那条：小程序也接真实整人模型——按当前套装 ID＋阵营**精确匹配**、
   点击后懒加载、可拖动旋转；不得把模型打进主包、不得用别的套装冒充、失败回原画并明说。
   B1/B3 把 76 份 PNG 衍生件与这份清单发到了 wow/{env}/v1/
   （for-mini/docs/VERIFY-小程序3D分发-2026-10-30.md），B2 真机验过"直取 https 能加载出人物"
   （for-mini/docs/VERIFY-小程序3D远端单件-2026-10-30.md）。这一层只回答一件事：
   **这一套、这一阵营，能不能拿、拿哪一份。**

   三条硬规矩写死在这里，页面不许自己判：
   1) 只认 setId + faction 精确命中的那一条；命不中就说"这一套没有登记的真实模型"，
      **绝不借用同职业另一套或相似部位的模型**（借了就是拿别人的装备冒充玩家手里这一套）。
   2) 命中了还要两样同时对得上才给地址：登记的 `placementVerdict` 必须是 `PASS`，
      且清单里的 `dollSnapshot` 与**当前套装这一阵营的 doll 逐格**（部位/格号/物品 ID）相同。
      套装名单后来改过一件，这条就会拦住——宁可显示原画并说明原因，不许画一套假的。
   3) 取不到（断网、404、结构不对、契约比客户端新）一律 ok:false 带原因，从不"猜一个能用"。
      清单本身与开关同一档可变（max-age=60），所以每次都先试线上，连不上才用存下的那一份
      并标 stale——旧清单指到的仍是同一批不可变对象，不会指到半件模型。 */

const oss = require('./oss-manifest')

const PRODUCT = 'wow-forever-mini-models'
const KIND = 'bis-models-index'
const FORMAT = 'glb-png-v1'
/* 与那份对象自己的 max-age=60 对齐：一分钟内在这一页切职业切阵营不再重复取清单 */
const TTL_MS = 60 * 1000

/* 缓存 key 不带 @：带 @ 会被 noteBuild 当旧批缓存顺手清掉（同 services/features.js 那条） */
const STORE_KEY = oss.CACHE_PREFIX + 'bis_models_index'

function readStore() {
  try {
    return wx.getStorageSync(STORE_KEY) || null
  } catch (e) {
    return null
  }
}

function writeStore(payload) {
  try { wx.setStorageSync(STORE_KEY, payload) } catch (e) { /* 只影响断网时有没有兜底 */ }
}

/* doll 有两写法：清单里是 [{slot,cell,item}]，套装分片里是 [[slot,cell,item]]。
   归一成排序后的三元组串再比，键序与行序都不影响结论。 */
function triples(doll) {
  return (doll || []).map((r) => {
    const arr = Array.isArray(r)
    const slot = arr ? r[0] : (r && r.slot)
    const cell = arr ? r[1] : (r && r.cell)
    const item = arr ? r[2] : (r && r.item)
    return String(slot) + '|' + String(cell) + '|' + String(item)
  }).sort()
}

function sameDoll(a, b) {
  const x = triples(a), y = triples(b)
  if (x.length !== y.length) return false
  for (let i = 0; i < x.length; i += 1) { if (x[i] !== y[i]) return false }
  return true
}

/* 结构不对就整份当没有：宁可用上一层兜底，也不信"有一半可信"的清单 */
function validateIndex(obj) {
  if (!obj || typeof obj !== 'object') return '清单不是对象'
  if (Number(obj.schemaVersion) > oss.CLIENT_SCHEMA_VERSION) return '清单契约版本 ' + obj.schemaVersion + ' 比客户端新'
  if (obj.product !== PRODUCT) return 'product 是 ' + obj.product
  if (obj.kind !== KIND) return 'kind 是 ' + obj.kind
  if (obj.formatVersion !== FORMAT) return '这一版客户端只认 ' + FORMAT + '，清单写的是 ' + obj.formatVersion
  if (!Array.isArray(obj.models) || !obj.models.length) return '清单里没有模型条目'
  return null
}

let mem = null
let inflight = null

function fetchIndex(force) {
  if (!force && mem && Date.now() - mem.at < TTL_MS) return Promise.resolve(mem)
  if (!force && inflight) return inflight
  const cached = readStore()
  const p = oss.requestRaw(oss.modelsIndexUrl(oss.ACTIVE_ENV))
    .then((res) => {
      const obj = res.data
      const why = validateIndex(obj)
      if (why) {
        mem = cached && !cached.invalid
          ? { models: cached.models, at: cached.at || 0, source: 'cache', stale: true, error: new Error('线上清单不可用：' + why) }
          : { models: null, at: Date.now(), source: 'none', stale: true, error: new Error('线上清单不可用：' + why) }
        return mem
      }
      writeStore({ models: obj.models, at: Date.now() })
      mem = { models: obj.models, at: Date.now(), source: 'live', stale: false, error: null }
      return mem
    })
    .catch((error) => {
      mem = cached
        ? { models: cached.models, at: cached.at || 0, source: 'cache', stale: Date.now() - (cached.at || 0) > TTL_MS, error }
        : { models: null, at: Date.now(), source: 'none', stale: true, error }
      return mem
    })
    .then((s) => { inflight = null; return s })
  inflight = p
  return p
}

/* pick：在清单里按 setId+faction 找那一条，并过三道闸。
   返回 { ok, url, entry, reason }——reason 是给人看的一句话，页面原样显示，不改写。 */
function pick(models, setId, fac, currentDoll) {
  const hit = (models || []).filter((m) => String(m.setId) === String(setId) && String(m.faction) === String(fac))
  if (hit.length !== 1) {
    return {
      ok: false,
      reason: hit.length ? '清单里这一条重复了（' + hit.length + ' 条），先修清单'
        : '这一套（' + setId + ' · ' + (fac === 'horde' ? '部落' : '联盟') + '）没有登记的真实模型'
    }
  }
  const m = hit[0]
  /* 文件名里那 12 位必须就是 pngSha256 的头 12 位：客户端没法给下载回来的 GLB 算哈希，
     但这一条能拦住"手改过的清单"（名字与校验值脱钩），不至于让页面去取一件谁也没核过的东西 */
  const hashInName = /^.*-([0-9a-f]{12})\.glb$/.exec(String(m.file || ''))
  if (!hashInName || String(m.pngSha256 || '').slice(0, 12) !== hashInName[1]) {
    return { ok: false, entry: m, reason: '这一条的文件名与 pngSha256 对不上，先修清单再发' }
  }
  if (m.placementVerdict !== 'PASS') {
    return { ok: false, reason: '这份模型的装备位置没通过核对（登记是 ' + m.placementVerdict + '），不拿来当这一套', entry: m }
  }
  if (!sameDoll(m.dollSnapshot, currentDoll)) {
    return {
      ok: false, entry: m,
      reason: '这份模型是按另一版名单核对的：登记 ' + triples(m.dollSnapshot).length + ' 格 · 现在这一套 '
        + triples(currentDoll).length + ' 格，逐格没对上——不借用别的套装冒充'
    }
  }
  const u = oss.modelUrl(oss.ACTIVE_ENV, m)
  if (u.error) return { ok: false, reason: '清单里的地址用不了：' + u.error.message, entry: m }
  return { ok: true, url: u.url, entry: m }
}

/* load(setId, fac, currentDoll, force)：页面点"查看 3D"才调，进页一次都不该调。 */
function load(setId, fac, currentDoll, force) {
  return fetchIndex(force).then((s) => {
    if (!s.models) {
      return { ok: false, source: s.source, stale: s.stale, reason: '取不到模型清单（' + ((s.error && s.error.message) || '没连上') + '）' }
    }
    const r = pick(s.models, setId, fac, currentDoll)
    r.source = s.source
    r.stale = s.stale
    if (s.error && s.source === 'cache') r.indexError = s.error.message
    return r
  })
}

module.exports = {
  PRODUCT,
  KIND,
  FORMAT,
  TTL_MS,
  STORE_KEY,
  triples,
  sameDoll,
  validateIndex,
  pick,
  load,
  fetchIndex,
  /* 给门禁与切套时用：清掉内存那一份，下一次真的重新取清单 */
  reset() { mem = null; inflight = null }
}
