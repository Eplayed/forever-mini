/* 临时探针页（提示词 A）：只回答一个问题——微信原生 xr-frame 能不能把
   app/img/models/real/hunter-alliance.glb 这份"要求 EXT_texture_webp"的整人模型
   画出来、能不能转、退出重进还能不能加载。
   正式 BiS 页一行没动，不发 OSS，探针样本不进发布包。
   结论写 for-mini/docs/VERIFY-小程序真实3D探针-2026-10-30.md。 */

/* 三份要验的东西。MODEL_DIR 由构建预览工程的那一步改写：
   正式小程序里样本在 tmp-model/（不进包），隔离预览工程里在 probe-model/（必须进包）。
   空场景档 src 为空 → 组件只画清屏绿，用来先确认这台设备到底会不会发 ready。 */
const MODEL_DIR = '/tmp-model/'
/* B2（2026-10-30）要验的是"远端那一份能不能取到"，不是"本机能不能读到磁盘"。
   正式工程里这一句是空串（④⑤ 两档也就点不开）；tools/build-xr-probe.py --remote
   会把 beta 的 HTTPS 地址烘进隔离预览工程那一份。空串被点到时页面明说"没得测"，
   不许演成"绿屏＝加载成功"。 */
const REMOTE_URL = ''
const SRC = {
  blank: '',
  webp: MODEL_DIR + 'hunter-alliance.glb',
  png: MODEL_DIR + 'hunter-alliance-png.glb',
  remote: REMOTE_URL,
  dl: ''
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
    dlText: '',
    hasRemote: false,
    yaw: 0,
    which: 'blank',
    src: SRC.blank
  },

  onLoad() {
    let si = {}
    try { si = wx.getSystemInfoSync() || {} } catch (e) { si = {} }
    this.setData({
      hasRemote: !!REMOTE_URL,
      metaText: '基础库 ' + (si.SDKVersion || '?') + ' · ' + (si.platform || '?') + ' ' + (si.system || '')
        + ' · ' + (si.model || '?') + ' · 微信 ' + (si.version || '?')
        + ' · 远端 ' + (REMOTE_URL ? '已配' : '未配')
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
    if (w === this.data.which) return
    if (w === 'dl') return this.pull()
    const src = SRC[w]
    if (!src && w !== 'blank') {
      this.setData({ which: w, state: 'bad', stateText: '没得测', errText: '这一档没有可取的东西：远端地址没配进这个包' })
      return
    }
    this.setData({
      which: w, src: src, alive: false, dlText: '',
      state: 'loading', stateText: w === 'remote' ? '从远端取' : '换文件中', errText: '',
      meshCount: 0, texCount: 0, noTexCount: 0, texDetail: '', yaw: 0
    })
    setTimeout(() => this.setData({ alive: true }), 320)
  },

  /* B2 的第二条路：先 wx.downloadFile 落到本机临时文件，再交给 xr-frame。
     它和"直接把 HTTPS 地址给 xr-asset-load"是两条独立结论，必须分开记——
     一条成了不能说另一条也成了，一条坏了也不能说另一条坏了。 */
  pull() {
    if (!REMOTE_URL) {
      this.setData({ which: 'dl', state: 'bad', stateText: '没得测', errText: '远端地址没配进这个包' })
      return
    }
    const t0 = Date.now()
    this.setData({
      which: 'dl', src: '', alive: false, state: 'loading', stateText: '先下载到本机',
      errText: '', dlText: '下载中…', meshCount: 0, texCount: 0, noTexCount: 0, texDetail: '', yaw: 0
    })
    const that = this
    wx.downloadFile({
      url: REMOTE_URL,
      success(res) {
        const ms = Date.now() - t0
        const size = res.dataLength === undefined ? '?' : res.dataLength
        that.setData({
          dlText: 'downloadFile：HTTP ' + res.statusCode + ' · ' + size + ' B · ' + ms + ' ms · ' + res.tempFilePath
        })
        if (res.statusCode !== 200 || !res.tempFilePath) {
          that.setData({ state: 'bad', stateText: '下载失败', errText: 'HTTP ' + res.statusCode + '，没有临时文件路径' })
          return
        }
        that.setData({ src: res.tempFilePath, state: 'loading', stateText: '交给场景加载' })
        setTimeout(() => that.setData({ alive: true }), 320)
      },
      fail(err) {
        that.setData({
          state: 'bad', stateText: '下载失败',
          errText: 'downloadFile 原文：' + ((err && err.errMsg) || JSON.stringify(err || {}))
        })
      }
    })
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
