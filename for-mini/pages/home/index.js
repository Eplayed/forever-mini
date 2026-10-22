const service = require('../../services/forever-data')
const DUNGEON_INDEX = require('../../data/forever-dungeon-snapshot')

/* 首页（2026-10-22 玩家面清理）
   这一屏只回答玩家一件事："我现在要查什么，从哪儿进"。
   站主定的规矩：玩家不需要看到"数据有多少、缺多少、核到哪天、第几批"——
   那些是我们的台账，不是玩家的任务，所以覆盖率读数、缺口清单、WIP chip、
   入口卡上的条数、核对日期与批次号全部下线（口径见
   wow-forever-web/docs/PLAN-小程序玩家面-2026-10-22.md）。
   留下的只有：入口、最近看过、断网提示、页脚声明。 */

Page({
  data: {
    loaded: false,
    offline: false,
    requiresUpdate: false,
    recent: []
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

  /* 仍然取一次 meta：它是"连没连上线"的最便宜判据，断网提示要靠它。
     取回来的覆盖率/计数不再上界面。 */
  refresh() {
    return service.loadMeta().then((result) => {
      const meta = result.data || {}
      this.disclaimer = meta.disclaimer || ''
      this.setData({
        loaded: true,
        offline: result.source !== 'live',
        requiresUpdate: !!result.requiresUpdate
      })
      return null
    })
  },

  /* 最近看过直接读索引快照里的那几条，不为首页再发一次网络请求 */
  syncRecent() {
    const map = {}
    ;(DUNGEON_INDEX.items || []).forEach((it) => {
      map[it.id] = { id: it.id, title: it.nameCn || it.nameEn || it.id, range: it.levelRange || '等级待实测' }
    })
    const ids = service.getRecentDungeons()
    const recent = ids.map((id) => map[id] || { id: id, title: id, range: '' }).slice(0, 4)
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

  onDisclaimer() {
    wx.showModal({
      title: '声明',
      content: this.disclaimer || '非官方粉丝资料站，与暴雪娱乐及网易无关。',
      showCancel: false
    })
  }
})
