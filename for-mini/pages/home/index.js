const service = require('../../services/forever-data')
const DUNGEON_INDEX = require('../../data/forever-dungeon-snapshot')

Page({
  data: {
    loaded: false,
    meta: null,
    source: '',
    sourceText: '',
    offline: false,
    covList: [],
    recent: [],
    requiresUpdate: false,
    modules: [
      { id: 'glossary', name: '中英术语速查', desc: '按中文名搜官方译名，可复制', ready: true, path: '/pages/glossary/index', tab: true },
      { id: 'talent', name: '天赋计算器', desc: '结构已入库，层级点数门槛待实测', ready: false, path: '' },
      { id: 'skills', name: '技能书', desc: '官方中文稿只覆盖 4 职业，其余待采', ready: false, path: '' },
      { id: 'dungeons', name: '副本随手查', desc: '38 座本的中英名、等级、首领与掉落，断网也能查', ready: true, path: '/pages/dungeons/index', tab: false },
      { id: 'dungeon-note', name: '副本手册还缺什么', desc: '38 座全都没有实测路线；掉落按经典旧世公开库推的，一律标待实测', ready: false, path: '' },
      { id: 'provenance', name: '溯源与方法', desc: '每条数据的来源与核对日期', ready: false, path: '' }
    ]
  },

  onLoad() {
    this.refresh()
    this.syncRecent()
  },

  onShow() {
    this.syncRecent()
  },

  /* 最近看过直接读索引快照里的那几条，不为首页再发一次网络请求 */
  syncRecent() {
    const map = {}
    ;(DUNGEON_INDEX.items || []).forEach((it) => {
      map[it.id] = { id: it.id, title: it.nameCn || it.nameEn || it.id, level: it.level || 'L3', range: it.levelRange || '等级待实测' }
    })
    const ids = service.getRecentDungeons()
    const recent = ids.map((id) => map[id] || { id: id, title: id, level: 'L3', range: '' }).slice(0, 4)
    /* 存储里记了但快照里没有的 id（比如改了副本 id）要主动丢掉，否则首页会一直显示一排原始编号 */
    const stale = ids.filter((id) => !map[id])
    if (stale.length) {
      try { wx.setStorageSync(service.RECENT_DUNGEON_KEY, ids.filter((id) => map[id])) } catch (e) {}
    }
    this.setData({ recent })
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  refresh() {
    return service.loadMeta().then((result) => {
      const meta = result.data || {}
      const cov = meta.coverage || {}
      const total = Math.max(cov.total || 0, 1)
      const covList = ['L0', 'L1', 'L2', 'L3'].map((level) => ({
        level,
        name: service.levelName(level),
        count: cov[level] || 0,
        pct: Math.round((cov[level] || 0) / total * 100)
      }))
      this.setData({
        loaded: true,
        meta,
        source: result.source,
        sourceText: result.sourceText,
        offline: result.source !== 'live',
        requiresUpdate: result.requiresUpdate,
        covList
      })
    })
  },

  onModuleTap(e) {
    const index = e.currentTarget.dataset.index
    const module = this.data.modules[index]
    if (!module.ready) {
      wx.showToast({ title: module.desc, icon: 'none', duration: 2500 })
      return
    }
    /* 速查在 tabBar 里只能 switchTab；副本页是普通页，只能 navigateTo。
       用错一个就是"点了没反应"，所以入口类型写在模块表里，别在handler里猜 */
    if (module.tab) {
      wx.switchTab({ url: module.path })
    } else {
      wx.navigateTo({ url: module.path })
    }
  },

  onModuleTapGo() {
    wx.navigateTo({ url: '/pages/dungeons/index' })
  },

  onRecentTap(e) {
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + encodeURIComponent(e.currentTarget.dataset.id) })
  },

  onDisclaimer() {
    const meta = this.data.meta || {}
    wx.showModal({
      title: '数据来源与声明',
      content: (meta.disclaimer || '') + '\n\n数据基准：' + ((meta.dataBaseline && meta.dataBaseline.build) || '未记录')
        + '\n核对日期：' + (meta.checkedAt || '未记录'),
      showCancel: false
    })
  }
})
