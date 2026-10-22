const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')

/* 职业详情（M03）：可选种族 → 技能书入口 → 天赋树（只读）。
   天赋树按 (tier, column) 摆位：grid 是 7 行 4 列，界面就照这个格子摆，
   不做解锁判定、不显示"还差几点"——门槛没核到之前那些数都是猜（根 AGENTS.md 第五条）。
   分享走微信卡片（标题 + 路径），个人主体不做图片分享与 web-view。 */
const FACTION = { alliance: '联盟', horde: '部落' }

Page({
  data: {
    classId: '',
    nameCn: '',
    nameEn: '',
    iconUrl: '',
    races: [],
    trees: [],
    treeTab: 0,
    loaded: false,
    talentLoaded: false,
    offline: false,
    requiresUpdate: false,
    errorText: '',
    note: ''
  },

  onLoad(query) {
    this.batch = null
    this.classId = String((query && query.classId) || 'warrior')
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  onShareAppMessage() {
    return {
      title: '无限 ' + (this.data.nameCn || '职业') + '：可选种族、技能书与天赋树',
      path: '/pages/class/index?classId=' + this.classId
    }
  },

  refresh() {
    return service.loadClassIndex().then((r) => {
      this.batch = r.batch
      const d = r.data || {}
      const entry = (d.classes || []).filter((c) => c.classId === this.classId)[0]
      if (!entry) {
        this.setData({ loaded: true, errorText: '这个职业不在名单里：' + this.classId })
        return null
      }
      const races = (d.races || []).filter((x) => (x.classes || []).indexOf(this.classId) >= 0)
        .map((x) => ({
          id: x.id,
          nameCn: x.nameCn || '中文名待核',
          factionText: FACTION[x.faction] || x.faction || '',
          iconUrl: oss.iconUrl(this.batch, x.iconKey),
          subgroup: x.subgroup ? (x.subgroup.nameCn || '') : ''
        }))
      this.talentEntry = entry
      this.setData({
        classId: entry.classId,
        nameCn: entry.nameCn || '中文名待核',
        nameEn: entry.nameEn || '',
        iconUrl: oss.iconUrl(this.batch, entry.iconKey),
        races,
        loaded: true,
        offline: r.source !== 'live',
        requiresUpdate: !!r.requiresUpdate
      })
      if (!entry.shardPath) {
        this.setData({ talentLoaded: true, errorText: '这个职业的天赋树还没有整理好。' })
        return null
      }
      return service.loadTalentClass(entry, this.batch).then((t) => {
        const td = t.data || {}
        const trees = (td.trees || []).map((tr) => ({
          name: tr.nameCn || tr.id,
          conflict: !!tr.nameConflict,
          rows: this.rowsOf(tr.nodes || [])
        }))
        this.setData({
          trees,
          treeTab: 0,
          talentLoaded: true,
          note: td.note || '',
          offline: this.data.offline || t.source !== 'live',
          errorText: t.error && !trees.length ? String(t.error.message || t.error).slice(0, 120) : this.data.errorText
        })
        return null
      })
    })
  },

  /* 7 行 4 列的格子：同一 tier 的节点按 column 排，空位留空，
     手机上横着摆四个刚好，不缩放不重叠 */
  rowsOf(nodes) {
    const byTier = {}
    nodes.forEach((n) => {
      const t = Number(n.tier) || 0
      if (!byTier[t]) byTier[t] = []
      byTier[t].push(n)
    })
    return Object.keys(byTier).sort((a, b) => a - b).map((t) => ({
      tier: Number(t),
      cells: byTier[t].sort((a, b) => (a.column || 0) - (b.column || 0)).map((n) => ({
        id: n.id,
        name: n.nameCn || '（名字待核）',
        missing: !n.nameCn,
        ranks: n.maxRanks,
        iconUrl: oss.iconUrl(this.batch, n.iconKey),
        requires: (n.requires || []).length,
        level: n.level || 'L3'
      }))
    }))
  },

  onTreeTab(e) {
    this.setData({ treeTab: Number(e.currentTarget.dataset.i || 0) })
  },

  onNode(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const row = (this.data.trees[this.data.treeTab] || { rows: [] }).rows
    let node = null
    row.forEach((r) => r.cells.forEach((c) => { if (c.id === id) node = c }))
    if (!node) return
    wx.showModal({
      title: node.name,
      content: '最多 ' + node.ranks + ' 级'
        + (node.requires ? '\n需要先点它上面的前置天赋' : '')
        + '\n\n名字与坐标来自第三方资料站转述，本站逐条留了来源；缺的写待核，不机翻。',
      showCancel: false
    })
  },

  onSpells() {
    wx.navigateTo({ url: '/pages/spells/index?classId=' + encodeURIComponent(this.classId) })
  }
})
