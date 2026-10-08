const service = require('../../services/forever-data')

const SOURCE_TEXT = {
  live: '实时数据',
  cache: '离线缓存',
  snapshot: '打包快照'
}

Page({
  data: {
    loaded: false,
    meta: null,
    source: '',
    sourceText: '',
    offline: false,
    covList: [],
    modules: [
      { id: 'glossary', name: '中英术语速查', desc: '按中文名搜官方译名，可复制', ready: true, path: '/pages/glossary/index' },
      { id: 'talent', name: '天赋计算器', desc: '结构已入库，层级点数门槛待实测', ready: false, path: '' },
      { id: 'skills', name: '技能书', desc: '官方中文稿只覆盖 4 职业，其余待采', ready: false, path: '' },
      { id: 'dungeons', name: '副本手册', desc: '名单与等级区间已入库，BOSS 与掉落待实测', ready: false, path: '' },
      { id: 'provenance', name: '溯源与方法', desc: '每条数据的来源与核对日期', ready: false, path: '' }
    ]
  },

  onLoad() {
    this.refresh()
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
        sourceText: SOURCE_TEXT[result.source] || '',
        offline: result.source !== 'live',
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
    wx.switchTab({ url: module.path })
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
