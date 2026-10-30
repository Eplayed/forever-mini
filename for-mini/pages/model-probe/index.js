/* 临时探针页（提示词 A）：只回答一个问题——微信原生 xr-frame 能不能把
   app/img/models/real/hunter-alliance.glb 这份"要求 EXT_texture_webp"的整人模型
   画出来、能不能转、退出重进还能不能加载。
   正式 BiS 页一行没动，不发 OSS，探针样本不进发布包。
   结论写 for-mini/docs/VERIFY-小程序真实3D探针-2026-10-30.md。 */

/* 三份要验的东西。MODEL_DIR 由构建预览工程的那一步改写：
   正式小程序里样本在 tmp-model/（不进包），隔离预览工程里在 probe-model/（必须进包）。
   空场景档 src 为空 → 组件只画清屏绿，用来先确认这台设备到底会不会发 ready。 */
const MODEL_DIR = '/tmp-model/'
const SRC = {
  blank: '',
  webp: MODEL_DIR + 'hunter-alliance.glb',
  png: MODEL_DIR + 'hunter-alliance-png.glb'
}

Page({
  data: {
    alive: true,
    state: 'loading',
    stateText: '准备加载',
    metaText: '',
    meshCount: 0,
    texCount: 0,
    noTexCount: 0,
    texDetail: '',
    errText: '',
    yaw: 0,
    which: 'blank',
    src: SRC.blank
  },

  onLoad() {
    let si = {}
    try { si = wx.getSystemInfoSync() || {} } catch (e) { si = {} }
    this.setData({
      metaText: '基础库 ' + (si.SDKVersion || '?') + ' · ' + (si.platform || '?') + ' ' + (si.system || '')
        + ' · ' + (si.model || '?') + ' · 微信 ' + (si.version || '?')
    })
    this.hookLogs()
  },

  /* 把 xr-frame 自己打的日志与未捕获拒绝抓下来：要的是错误原文，不是我对源码的推测 */
  hookLogs() {
    const that = this
    this.logs = []
    const push = (tag, text) => {
      const line = String(text).slice(0, 400)
      if (!/GLTF|EXT_|KHR_|xr|webgl|texture|gltf/i.test(line)) return
      that.logs.push('[' + tag + '] ' + line)
      that.setData({ errText: that.logs.slice(-8).join('\n') })
    }
    ;['error', 'warn'].forEach((k) => {
      const old = console[k]
      console[k] = function () {
        const parts = Array.prototype.slice.call(arguments).map((x) => {
          try { return typeof x === 'string' ? x : JSON.stringify(x) } catch (e) { return String(x) }
        })
        push(k, parts.join(' '))
        return old.apply(console, arguments)
      }
    })
    try {
      wx.onUnhandledRejection((res) => {
        const r = res && res.reason
        push('reject', (r && (r.message || r.errMsg)) || r)
      })
    } catch (e) { push('hook', 'onUnhandledRejection 挂不上：' + e.message) }
  },

  onStatus(e) {
    const d = (e && e.detail) || {}
    const patch = {}
    if (d.state) patch.state = d.state
    if (d.text) patch.stateText = d.text
    if (d.meshes !== undefined) patch.meshCount = d.meshes
    if (d.tex !== undefined) patch.texCount = d.tex
    if (d.noTex !== undefined) patch.noTexCount = d.noTex
    if (d.detail) patch.texDetail = d.detail
    if (d.err) patch.errText = (this.data.errText ? this.data.errText + '\n' : '') + d.err
    if (d.yaw !== undefined) patch.yaw = d.yaw
    this.setData(patch)
  },

  /* 退出重进：把整个场景组件拆掉再建一遍（比 reLaunch 更狠，验同一页面内能不能重载） */
  reloadScene() {
    this.setData({
      alive: false, state: 'loading', stateText: '重建中', errText: '',
      meshCount: 0, texCount: 0, noTexCount: 0, texDetail: '', yaw: 0
    })
    setTimeout(() => this.setData({ alive: true }), 320)
  },

  /* 换要验的那一份：拆掉场景再建，路径只在页面这一处写 */
  pickFile(e) {
    const w = (e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.w) || 'webp'
    const src = SRC[w]
    if (w === this.data.which) return
    this.setData({
      which: w, src: src, alive: false,
      state: 'loading', stateText: '换文件中', errText: '',
      meshCount: 0, texCount: 0, noTexCount: 0, texDetail: '', yaw: 0
    })
    setTimeout(() => this.setData({ alive: true }), 320)
  },

  turnLeft() { this.turn(-60) },
  turnRight() { this.turn(60) },

  turn(deg) {
    const sc = this.selectComponent('#sc')
    if (!sc || typeof sc.turn !== 'function') {
      this.setData({ state: 'bad', stateText: '失败', errText: '取不到 probe-scene 组件实例' })
      return
    }
    sc.turn(deg)
  }
})
