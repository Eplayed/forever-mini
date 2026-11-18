const oss = require('./services/oss-manifest')

App({
  onLaunch() {
    try { wx.removeStorageSync(oss.DEV_ORIGIN_KEY) } catch (error) {}
  },
  globalData: {
    // 2026-10-23 站主定名「跑本助手」；此前一直是占位，不得出现商标词
    appName: '跑本助手',
    dataNamespace: oss.NAMESPACES[oss.ACTIVE_ENV]
  }
})
