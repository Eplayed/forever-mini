/* 功能开关（2026-10-27 站主要求："这个专业页面我暂时先不公开，等下次想公开了，
   不需要小程序发布就可以公开页面"）
   ------------------------------------------------------------------
   取的是 wow/{env}/v1/flags.json 那一份可变对象：它与数据批次并列、不在气密目录里，
   改它不换 buildId、不重发数据、不发小程序版本；缓存语义与指针同一档（max-age=60），
   所以线上拧完大约一分钟玩家侧就生效。

   三层优先，逐条落定（这是这一层唯一要紧的规矩）：
     live（远端这一条） > cache（上次存下的这一条） > local（打包默认表 data/flags-local.js）
   —— 断网 / 没发过 / 结构不对，都不许把已经公开的页关掉，也不许把没公开的页放出来。
   界面义务：关着的页只说"这一页还没开放"这一句事实，不许编"数据维护中"那种理由；
   入口卡被关掉时整块收掉，不留空白格。

   用法（页面里）：
     const features = require('../../services/features')
     features.load(true).then(() => {
       if (!features.isOn('professions')) { this.setData({ locked: true }); return }
       ... 正常取数
     }) */

const oss = require('./oss-manifest')
const LOCAL = require('../data/flags-local')

const FLAGS_PRODUCT = 'wow-forever-mini-flags'
/* 与指针那一档 max-age=60 对齐：一分钟内的重复调用不再发请求 */
const FLAGS_TTL_MS = 60 * 1000

/* 缓存 key 里刻意不带 @：oss-manifest 的 noteBuild 会把带 @ 的旧批缓存按 buildId 清掉，
   开关不是按批存的东西，被它顺手清了就等于断网时没有兜底。 */
const cacheKeyOf = (env) => oss.CACHE_PREFIX + 'flags_' + env

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

/* 结构不对就整份当没有：宁可用上一层兜底，也不要"有一半可信" */
function validateFlags(obj, env) {
  if (!obj || typeof obj !== 'object') return '开关对象不是对象'
  if (obj.product !== FLAGS_PRODUCT) return 'product 是 ' + obj.product + '，不是 ' + FLAGS_PRODUCT
  if (obj.env !== env) return 'env 是 ' + obj.env + '，请求的是 ' + env
  if (obj.namespace !== oss.NAMESPACES[env]) return 'namespace 是 ' + obj.namespace
  if (Number(obj.schemaVersion) > oss.CLIENT_SCHEMA_VERSION) {
    return '开关契约版本 ' + obj.schemaVersion + ' 比客户端新'
  }
  if (!obj.features || typeof obj.features !== 'object') return '没有 features'
  const bad = Object.keys(obj.features).filter((n) => typeof obj.features[n].on !== 'boolean')
  if (bad.length) return '这几条的 on 不是 true/false：' + bad.join(',')
  return null
}

/* 逐条合成：远端没提到的名字退回打包默认表，而不是当成"没开" */
function merge(remote, cached, env, source, stale, error) {
  const out = {}
  const names = {}
  Object.keys(LOCAL.features || {}).forEach((n) => { names[n] = 1 })
  Object.keys(remote || {}).forEach((n) => { names[n] = 1 })
  Object.keys(names).forEach((n) => {
    const r = (remote || {})[n]
    const c = (cached || {})[n]
    const l = (LOCAL.features || {})[n] || {}
    let picked = null
    let from = 'local'
    if (r) { picked = r; from = source }
    else if (c) { picked = c; from = 'cache' }
    else if (l) { picked = l; from = 'local' }
    out[n] = {
      on: !!(picked && picked.on === true),
      name: (picked && picked.name) || (l && l.name) || n,
      note: (picked && picked.note) || '',
      from: from
    }
  })
  return { env, features: out, source, stale: !!stale, at: Date.now(), error: error || null }
}

/* 模块级的一份状态：页面第一帧就要能同步问一句"这页开着吗"，不能等网络。
   初始值就是打包默认表——它保证"没取到远端"和"取到了但没说"两种情况下行为一致。 */
let state = merge(null, null, null, 'local', false, null)
let inflight = null

/* load(force)：env 一律取 oss-manifest 的 ACTIVE_ENV。
   （2026-10-27 写完第一版签名是 load(env, force)，页面按直觉传了 load(true)，
     env 就成了 true → 命名空间拼成 undefined → 请求必失败 → 永远走打包默认表，
     而且界面看不出任何不对——"开关不生效"就是这么来的。签名只留一个参数。） */
function load(force) {
  const targetEnv = oss.ACTIVE_ENV
  if (!force && state.env === targetEnv && Date.now() - state.at < FLAGS_TTL_MS) {
    return Promise.resolve(state)
  }
  if (!force && inflight) return inflight
  const cached = readStore(cacheKeyOf(targetEnv))
  const cachedFeatures = cached && cached.features
  const p = oss.requestRaw(oss.flagsUrl(targetEnv))
    .then((res) => {
      const obj = res.data
      const why = validateFlags(obj, targetEnv)
      if (why) {
        /* 线上这份不合法：退回存下的那一份，并如实标 invalid——不许拿"有一半可信"的开关当实时 */
        const err = new Error('线上开关不可用：' + why)
        state = cachedFeatures
          ? merge(null, cachedFeatures, targetEnv, 'cache', true, err)
          : merge(null, null, targetEnv, 'local', true, err)
        return state
      }
      writeStore(cacheKeyOf(targetEnv), { features: obj.features, at: Date.now() })
      state = merge(obj.features, cachedFeatures, targetEnv, 'live', false, null)
      return state
    })
    .catch((error) => {
      if (cachedFeatures) {
        state = merge(null, cachedFeatures, targetEnv, 'cache',
          Date.now() - (cached.at || 0) > FLAGS_TTL_MS, error)
      } else {
        state = merge(null, null, targetEnv, 'local', true, error)
      }
      return state
    })
    .then((s) => {
      inflight = null
      return s
    })
  inflight = p
  return p
}

function isOn(name) {
  const f = state.features[name]
  /* 名字两边都没有：当没开。远端加了新页而代码包里没这页，本来也该是看不见 */
  return !!(f && f.on === true)
}

function describe(name) {
  return state.features[name] || { on: false, name: name, note: '', from: 'absent' }
}

function snapshot() {
  return state
}

module.exports = {
  FLAGS_PRODUCT,
  FLAGS_TTL_MS,
  cacheKeyOf,
  load,
  isOn,
  describe,
  snapshot,
  validateFlags,
  merge
}
