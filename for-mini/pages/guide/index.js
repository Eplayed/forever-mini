const service = require('../../services/forever-data')

/* 指南（M03）：宏命令 + 插件名单。
   2026-10-22 站主拍板把这两样从"仅限网页"扩到小程序，边界照根 AGENTS.md 清单第 1、5 条：
   一律免费、标作者/原帖/抓取日期、不推荐循环提示类插件、不分发插件本体。
   内容还没整理时这一页从首页进不来（首页卡按有没有内容显示），直接进也只看到一句实话。 */

Page({
  data: {
    macros: [],
    addons: [],
    boundaries: '',
    loaded: false,
    offline: false,
    requiresUpdate: false,
    errorText: ''
  },

  onLoad() {
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  onShareAppMessage() {
    return { title: '无限指南：宏命令与插件名单（免费、标来源）', path: '/pages/guide/index' }
  },

  refresh() {
    return service.loadGuide().then((r) => {
      const d = r.data || {}
      this.setData({
        macros: (d.macros || []).map((m) => ({
          id: m.id || m.name,
          name: m.name,
          use: m.use || '',
          text: m.text || '',
          author: m.author || '',
          prov: (m.provenance || []).map((p) => ({ type: p.type || '未标注', url: p.url || '', checkedAt: p.checkedAt || '未记录' }))
        })),
        addons: (d.addons || []).map((a) => ({
          id: a.id || a.name,
          name: a.name,
          author: a.author || '',
          use: a.use || '',
          url: a.url || '',
          prov: (a.provenance || []).map((p) => ({ type: p.type || '未标注', url: p.url || '', checkedAt: p.checkedAt || '未记录' }))
        })),
        boundaries: (d.meta && d.meta.boundaries) || '',
        loaded: true,
        offline: r.source !== 'live',
        requiresUpdate: !!r.requiresUpdate,
        errorText: r.error ? String(r.error.message || r.error).slice(0, 120) : ''
      })
      return null
    })
  },

  onCopyMacro(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const m = this.data.macros.filter((x) => x.id === id)[0]
    if (!m) return
    wx.setClipboardData({
      data: m.text,
      success: () => wx.showToast({ title: '宏文本已复制，进游戏粘贴即可', icon: 'none', duration: 2200 })
    })
  },

  onCopyUrl(e) {
    const url = String(e.currentTarget.dataset.url || '')
    if (!url) {
      wx.showToast({ title: '这条没留链接', icon: 'none' })
      return
    }
    wx.setClipboardData({
      data: url,
      success: () => wx.showToast({ title: '链接已复制，到浏览器打开', icon: 'none', duration: 2200 })
    })
  }
})
