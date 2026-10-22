const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const engine = require('../../services/talent-engine')

/* 职业详情（2026-10-22 站主：天赋树要"模拟器的样子，可以模拟点击配置，和网页版那样的功能"）
   三系切换 → 点天赋加一点 → 长按看详情（详情里能加能减）→ 顶部读数与"清空这套"。
   判定全在 services/talent-engine.js（与网页端同一套规则），这一页只管摆与刷新。
   两条不能忘的口径：
   · 层级门槛与总点数是"按经典旧世推的、无限服待实测"，这句话必须留在屏幕上（gateNote）；
   · maxRanks 为 null 的节点不做判定，点它会给一句"上限还没核实"，不猜一个数出来。
   本机记一套（存储），分享带短码（与网页 encode 同格式，网页那边能原样打开）。 */
const FACTION = { alliance: '联盟', horde: '部落' }
const BUILD_KEY = 'wow_forever_v1_tbuild@'

Page({
  data: {
    classId: '',
    nameCn: '',
    nameEn: '',
    iconUrl: '',
    races: [],
    trees: [],
    treeTab: 0,
    treeName: '',
    treeSpent: 0,
    totalPoints: 51,
    remaining: 51,
    spentText: '',
    gateNote: '',
    buildCode: '',
    loaded: false,
    talentLoaded: false,
    offline: false,
    requiresUpdate: false,
    errorText: '',
    note: '',
    pop: null
  },

  onLoad(query) {
    this.batch = null
    this.classId = String((query && query.classId) || 'warrior')
    this.shareBuild = String((query && query.b) || '')
    this.trees = []
    this.rules = null
    this.state = {}
    this.nodeById = {}
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  onUnload() {
    this.saveBuild()
  },

  onHide() {
    this.saveBuild()
  },

  onShareAppMessage() {
    const code = engine.encode(this.trees, this.state)
    const used = engine.spent(this.state, this.trees)
    return {
      title: '无限 ' + (this.data.nameCn || '职业') + '天赋：' + (used ? this.data.spentText : '还没加点'),
      path: '/pages/class/index?classId=' + encodeURIComponent(this.classId)
        + (used ? '&b=' + encodeURIComponent(code) : '')
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
          iconUrl: oss.raceIconUrl(this.batch, x),
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
        this.rules = engine.normalizeRules(td.rules)
        this.trees = (td.trees || []).map((tr) => ({
          id: tr.id,
          /* describe()/级联清空那句要用 nameCn，别只塞一个 name——
             少了这个字段，读数就变成 "warrior-0 2" 这种内部编号（实测踩过） */
          nameCn: tr.nameCn || tr.id,
          name: tr.nameCn || tr.id,
          conflict: !!tr.nameConflict,
          nodes: tr.nodes || []
        }))
        this.nodeById = {}
        this.trees.forEach((tr) => tr.nodes.forEach((n) => { this.nodeById[n.id] = n }))
        this.state = this.startBuild()
        this.setData({
          talentLoaded: true,
          gateNote: this.rules.tierUnlockCost
            ? '层级门槛按经典旧世推（第 2 层起 ' + this.rules.tierUnlockCost.slice(1).join(' / ') + ' 点），无限服还没实测'
            : '层级点数门槛未核实：这一版不做分层限制，只做前置与总点数判定',
          note: td.note || '',
          offline: this.data.offline || t.source !== 'live',
          errorText: t.error && !this.trees.length ? String(t.error.message || t.error).slice(0, 120) : this.data.errorText
        })
        this.render()
        return null
      })
    })
  },

  /* 打开时先用哪个配置：分享链接带的码 > 本机存过的 > 空 */
  startBuild() {
    if (this.shareBuild) {
      const got = engine.decode(this.shareBuild, this.trees)
      if (engine.spent(got.state, this.trees) > 0) return got.state
    }
    try {
      const saved = wx.getStorageSync(BUILD_KEY + this.classId)
      if (saved) {
        const got = engine.decode(String(saved), this.trees)
        if (engine.spent(got.state, this.trees) > 0) return got.state
      }
    } catch (e) {}
    return {}
  },

  saveBuild() {
    if (!this.trees || !this.trees.length) return
    try {
      const code = engine.encode(this.trees, this.state)
      if (engine.spent(this.state, this.trees) > 0) wx.setStorageSync(BUILD_KEY + this.classId, code)
      else wx.removeStorageSync(BUILD_KEY + this.classId)
    } catch (e) {}
  },

  /* 每次加减点重画整棵树：52 个节点算一遍"现在能不能点"，比让 WXML 判逻辑可靠 */
  render() {
    const trees = this.trees
    const rules = this.rules
    const nameOf = (id) => (this.nodeById[id] || {}).nameCn || ''
    const shown = trees.map((tr) => ({
      name: tr.name,
      conflict: tr.conflict,
      spent: engine.treeSpent(tr, this.state),
      rows: engine.tiersOf(tr).map((row) => ({
        tier: row.length ? row[0].tier : 0,
        cells: row.map((n) => {
          const ranks = engine.ranksOf(this.state, n.id)
          const can = engine.canAdd(tr, this.state, n, rules, trees, nameOf)
          return {
            id: n.id,
            name: n.nameCn || '',
            missing: !n.nameCn,
            ranks: ranks,
            max: n.maxRanks === null || n.maxRanks === undefined ? '' : n.maxRanks,
            maxNote: n.maxRanks === null || n.maxRanks === undefined ? '上限未核实' : '',
            iconUrl: oss.iconUrl(this.batch, n.iconKey),
            tier: n.tier,
            requires: (n.requires || []).map(nameOf).filter((x) => x).join('、'),
            full: !!n.maxRanks && ranks >= n.maxRanks,
            can: can.ok,
            why: can.ok ? '' : can.why
          }
        })
      }))
    }))
    const used = engine.spent(this.state, trees)
    this.setData({
      trees: shown,
      treeName: (shown[this.data.treeTab] || {}).name || '',
      treeSpent: (shown[this.data.treeTab] || {}).spent || 0,
      totalPoints: rules ? rules.totalPoints : 51,
      remaining: Math.max(0, (rules ? rules.totalPoints : 51) - used),
      spentText: engine.describe(trees, this.state),
      buildCode: engine.encode(trees, this.state)
    })
  },

  onTreeTab(e) {
    const i = Number(e.currentTarget.dataset.i || 0)
    this.setData({ treeTab: i, treeName: (this.data.trees[i] || {}).name || '', treeSpent: (this.data.trees[i] || {}).spent || 0 })
  },

  findCell(id) {
    let cell = null
    this.data.trees.forEach((t) => t.rows.forEach((r) => r.cells.forEach((c) => { if (c.id === id) cell = c })))
    return cell
  },

  onTapNode(e) {
    const id = String((e.currentTarget.dataset || {}).id || '')
    const node = this.nodeById[id]
    if (!node) return
    const got = engine.add(this.trees, this.state, node, this.rules, (x) => (this.nodeById[x] || {}).nameCn || '')
    if (got.msg) {
      wx.showToast({ title: got.msg, icon: 'none', duration: 2000 })
      return
    }
    this.state = got.state
    this.saveBuild()
    this.render()
  },

  /* 长按＝看详情（站主指令）。详情弹窗是本站自己的面板，不是系统对话框——样式要跟主题一致 */
  onLongNode(e) {
    const id = String((e.currentTarget.dataset || {}).id || '')
    const cell = this.findCell(id)
    if (!cell) return
    this.setData({ pop: cell })
  },

  popAdd() {
    const cell = this.data.pop
    if (!cell) return
    const node = this.nodeById[cell.id]
    const got = engine.add(this.trees, this.state, node, this.rules, (x) => (this.nodeById[x] || {}).nameCn || '')
    if (got.msg) wx.showToast({ title: got.msg, icon: 'none', duration: 2000 })
    else {
      this.state = got.state
      this.saveBuild()
      this.render()
      this.setData({ pop: this.findCell(cell.id) })
    }
  },

  popRemove() {
    const cell = this.data.pop
    if (!cell) return
    const node = this.nodeById[cell.id]
    const got = engine.remove(this.trees, this.state, node)
    if (got.msg) wx.showToast({ title: got.msg, icon: 'none', duration: 2000 })
    else {
      this.state = got.state
      this.saveBuild()
      this.render()
      this.setData({ pop: this.findCell(cell.id) })
    }
  },

  popClose() {
    this.setData({ pop: null })
  },

  onReset() {
    wx.showModal({
      title: '清空这套天赋',
      content: '把 ' + (this.data.nameCn || '这个职业') + ' 现在点的 ' + (this.data.totalPoints - this.data.remaining) + ' 点全部退回？',
      confirmText: '清空',
      success: (res) => {
        if (!res.confirm) return
        this.state = {}
        this.saveBuild()
        this.render()
      }
    })
  },

  onCopyBuild() {
    const used = engine.spent(this.state, this.trees)
    if (!used) {
      wx.showToast({ title: '还没加点，没有可复制的配置', icon: 'none' })
      return
    }
    const text = (this.data.nameCn || '') + ' 天赋 ' + this.data.spentText
      + '（共 ' + used + '/' + this.data.totalPoints + ' 点） 码：' + this.data.buildCode
    wx.setClipboardData({ data: text })
  },

  onSpells() {
    wx.navigateTo({ url: '/pages/spells/index?classId=' + encodeURIComponent(this.classId) })
  }
})
