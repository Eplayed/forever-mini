const service = require('../../services/forever-data')
const DUNGEON_INDEX = require('../../data/forever-dungeon-snapshot')

/* 首页（H01 重做）
   这一屏只回答玩家一件事："我现在要查什么，从哪儿进"。
   · 能用的入口才做成卡；没做完的模块降级成「还在整理」的说明 chip，
     不再摆四个点了只弹 toast 的假入口（玩家会以为产品坏了）。
   · 数据完整度从首屏大条收成一行读数——那是我们的台账，不是玩家的任务。
   · 数字一律从当轮基底现读（meta.counts / 索引快照条数），不抄成常量。 */

const WIP = [
  {
    name: '天赋计算器',
    gap: '天赋树结构已入库，但每层需要多少点的门槛没有官方或客户端证据。'
      + '猜一个数就会误导玩家加点，所以门槛核到之前这一格不做。'
  },
  {
    name: '技能书',
    gap: '官方中文稿只覆盖 4 个职业，其余职业的技能中文名叫法还没采到，缺的一律不机翻补上。'
  },
  {
    name: '溯源与方法',
    gap: '网页端已有溯源页；小程序侧要把「每条数据的来源与核对日期」做成独立一页，等副本与速查两条线跑稳再开。'
  }
]

Page({
  data: {
    loaded: false,
    meta: null,
    source: '',
    sourceText: '',
    offline: false,
    requiresUpdate: false,
    factDate: '',
    baseline: '',
    buildId: '',
    covList: [],
    counts: { terms: 0, dungeons: 0, spells: 0, lootRows: 0, talentNodes: 0 },
    recent: [],
    wip: WIP
  },

  onLoad() {
    this.refresh()
    this.syncRecent()
  },

  onShow() {
    this.syncRecent()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  refresh() {
    return service.loadMeta().then((result) => {
      const meta = result.data || {}
      const cov = meta.coverage || {}
      const total = Math.max(cov.total || 0, 1)
      const counts = meta.counts || {}
      this.setData({
        loaded: true,
        meta,
        source: result.source,
        sourceText: result.sourceText,
        offline: result.source !== 'live',
        requiresUpdate: result.requiresUpdate,
        factDate: (result.factDates && result.factDates.latest) || meta.checkedAt || '',
        baseline: (meta.dataBaseline && (meta.dataBaseline.checkedAt || meta.dataBaseline.build)) || meta.checkedAt || '',
        buildId: result.buildId || '',
        counts: {
          terms: counts.terms || 0,
          dungeons: counts.dungeons || (DUNGEON_INDEX.items || []).length,
          spells: counts.spells || 0,
          lootRows: counts.lootRows || 0,
          talentNodes: counts.talentNodes || 0
        },
        covList: ['L0', 'L1', 'L2', 'L3'].map((level) => ({
          level,
          name: service.levelName(level),
          count: cov[level] || 0,
          pct: Math.round((cov[level] || 0) / total * 100)
        }))
      })
    })
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
    if (ids.some((id) => !map[id])) {
      try { wx.setStorageSync(service.RECENT_DUNGEON_KEY, ids.filter((id) => map[id])) } catch (e) {}
    }
    this.setData({ recent })
  },

  /* 副本与速查都在 tabBar 里了，只能 switchTab；用 navigateTo 会静默失败＝"点了没反应" */
  goDungeons() {
    wx.switchTab({ url: '/pages/dungeons/index' })
  },

  goGlossary() {
    wx.switchTab({ url: '/pages/glossary/index' })
  },

  /* 技能与掉落反查都不在 tabBar 里（三个位置已给 首页/副本/速查），
     用 navigateTo 保留返回栈；switchTab 打不开它们＝点了没反应 */
  goSpells() {
    wx.navigateTo({ url: '/pages/spells/index' })
  },

  goLoots() {
    wx.navigateTo({ url: '/pages/loots/index' })
  },

  onRecentTap(e) {
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + encodeURIComponent(e.currentTarget.dataset.id) })
  },

  onLevels() {
    const d = this.data
    const cov = d.covList.map((x) => x.level + ' ' + x.name + '：' + x.count + ' 条（' + x.pct + '%）').join('\n')
    wx.showModal({
      title: '这些数是什么意思',
      content: cov
        + '\n\nL0 已官方核实 / L1 只有官方英文 / L2 待实测 / L3 缺数据。'
        + '分级看的是「这条信息我们核到什么程度」，不是内容好坏。'
        + '\n\n数据基准 ' + (d.baseline || '未记录')
        + '\n最近核对 ' + (d.factDate || '未记录')
        + '\n线上批次 ' + (d.buildId || '没取到，用的是主包快照'),
      showCancel: false
    })
  },

  onWip(e) {
    const item = this.data.wip[e.currentTarget.dataset.i]
    wx.showModal({ title: item.name + '·还缺什么', content: item.gap, showCancel: false })
  },

  onDisclaimer() {
    const meta = this.data.meta || {}
    wx.showModal({
      title: '数据来源与声明',
      content: (meta.disclaimer || '非官方粉丝资料站，与暴雪娱乐及网易无关。')
        + '\n\n数据基准：' + (this.data.baseline || '未记录')
        + '\n核对日期：' + (this.data.factDate || '未记录')
        + '\n当前数据来源：' + this.data.sourceText,
      showCancel: false
    })
  }
})
