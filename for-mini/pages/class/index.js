const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const engine = require('../../services/talent-engine')

/* 职业详情（2026-10-22 站主第二轮指令改的四件事）
   ① 可选种族按联盟 / 部落左右两个框分，框体吃阵营色，框内一格＝图标在上名字在下、一行三个往下排；
      框里不再写"联盟/部落"——颜色与左右位置本身就是那件事（色相与网页 glyph.js 的 8 / 212 同一组）。
   ② "复制这套"撤掉，"分享这套"挪进工具条、放在清空左边。
   ③ 别人打开分享链接要能直接看到点法：路径带 &b=短码，进来先解它（短码格式与网页 encode 逐字符相同）。
   ④ 天赋系要有底图，与网页同一张（art.json 的 specs/{classId}-{系序号}）。
   两条不能忘的口径：
   · 层级门槛与总点数是按经典旧世推的、无限服待实测，这句话留在屏幕上（gateNote）；
   · 天赋的"具体说明"库里没有（两家上游只给名称/坐标/上限/前置），详情里照实说，不机翻、不编。 */
const FACTION = { alliance: '联盟', horde: '部落' }
const CHANGE_TEXT = {
  added: '无限新增的天赋',
  modified: '相对经典旧世改过',
  moved: '换了层级',
  unchanged: '与经典旧世一致'
}
const BUILD_KEY = 'wow_forever_v1_tbuild_'
const LEGACY_BUILD_KEY = 'wow_forever_v1_tbuild@'

Page({
  data: {
    classId: '',
    nameCn: '',
    nameEn: '',
    iconUrl: '',
    allianceRaces: [],
    hordeRaces: [],
    raceEmpty: '',
    padAlliance: 0,
    padHorde: 0,
    trees: [],
    treeTab: 0,
    treeName: '',
    totalPoints: 51,
    remaining: 51,
    spentText: '',
    gateNote: '',
    buildCode: '',
    fromShare: false,
    importMode: '',
    importError: '',
    loaded: false,
    talentLoaded: false,
    offline: false,
    requiresUpdate: false,
    errorText: '',
    pop: null
  },

  onLoad(query) {
    this.batch = null
    this.classId = String((query && query.classId) || 'warrior')
    this.shareBuild = String((query && query.b) || '')
    this.shareLayout = String((query && query.s) || '')
    const mode = query && query.mode
    this.shareMode = mode === 'leveling' || mode === 'partial' ? mode : ''
    this.scrollToTalent = !!this.shareBuild
    this.trees = []
    this.rules = null
    this.state = {}
    this.nodeById = {}
    this.migrateSavedBuild()
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  onShareTimeline() {
    return this.shareTalent()
  },

  onUnload() {
    this.saveBuild()
  },

  onHide() {
    this.saveBuild()
  },

  /* 分享出去的就是当前这套：路径带短码，别人点开直接是同一个点法 */
  onShareAppMessage() {
    const { title, query } = this.shareTalent()
    return { title, path: '/pages/class/index?' + query }
  },

  shareTalent() {
    const name = this.data.nameCn || '职业'
    const used = engine.spent(this.state, this.trees)
    let query = 'classId=' + encodeURIComponent(this.classId)
    if (!used) return { title: '无限 ' + name + '天赋树', query }
    query += '&b=' + encodeURIComponent(engine.encode(this.trees, this.state))
      + '&s=' + encodeURIComponent(this.talentLayout)
    const mode = this.data.importMode
    if (mode) query += '&mode=' + mode
    const title = '无限 ' + name + '天赋：' + this.data.spentText + (mode === 'partial' ? '（部分加点）' : '')
    return { title, query }
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
      /* 种族按阵营分两框；框内只留图标与名字（阵营由框体本身说） */
      const byFaction = { alliance: [], horde: [] }
      ;(d.races || []).filter((x) => (x.classes || []).indexOf(this.classId) >= 0)
        .forEach((x) => {
          const cell = {
            id: x.id,
            nameCn: x.nameCn || '待核',
            iconUrl: oss.raceIconUrl(this.batch, x)
          }
          if (byFaction[x.faction]) byFaction[x.faction].push(cell)
        })
      const total = byFaction.alliance.length + byFaction.horde.length
      this.talentEntry = entry
      this.setData({
        classId: entry.classId,
        nameCn: entry.nameCn || '中文名待核',
        nameEn: entry.nameEn || '',
        iconUrl: oss.raceIconUrl(this.batch, entry),
        allianceRaces: byFaction.alliance,
        hordeRaces: byFaction.horde,
        raceEmpty: total ? '' : '暂无可选种族记录。',
        /* 补齐到 3 的倍数，最后一行不留半格错位（(3 - n%3) % 3：正好整除时不补） */
        padAlliance: (3 - byFaction.alliance.length % 3) % 3,
        padHorde: (3 - byFaction.horde.length % 3) % 3,
        loaded: true,
        offline: r.source !== 'live',
        requiresUpdate: !!r.requiresUpdate
      })
      if (!entry.shardPath) {
        this.setData({ talentLoaded: true, errorText: '暂无该职业的天赋数据。' })
        return null
      }
      return service.loadTalentClass(entry, this.batch).then((t) => {
        const td = t.data || {}
        this.rules = engine.normalizeRules(td.rules)
        this.trees = (td.trees || []).map((tr, ti) => ({
          id: tr.id,
          /* 系底图：分片里带的是 assets 相对路径（真源在 art.json 的 specs），取不到就留纯色 */
          art: oss.assetUrl(this.batch, tr.specArt),
          nameCn: tr.nameCn || tr.id,
          name: tr.nameCn || tr.id,
          conflict: !!tr.nameConflict,
          nodes: tr.nodes || []
        }))
        this.nodeById = {}
        this.trees.forEach((tr) => tr.nodes.forEach((n) => { this.nodeById[n.id] = n }))
        this.talentLayout = engine.layoutKey(this.trees)
        const start = this.startBuild()
        this.state = start.state
        const patch = {
          talentLoaded: true,
          fromShare: start.from === 'share',
          importMode: start.mode || '',
          importError: start.error || '',
          gateNote: this.rules.tierUnlockCost
            ? '层级门槛按经典旧世推（第 2 层起 ' + this.rules.tierUnlockCost.slice(1).join(' / ') + ' 点），无限服还没实测'
            : '层级点数门槛未核实：这一版不做分层限制，只做前置与总点数判定',
          offline: this.data.offline || t.source !== 'live',
          errorText: t.error && !this.trees.length ? String(t.error.message || t.error).slice(0, 120) : this.data.errorText
        }
        if (start.mode) {
          patch.treeTab = this.trees.reduce((best, tree, index) =>
            engine.treeSpent(tree, this.state) > engine.treeSpent(this.trees[best], this.state) ? index : best, 0)
        }
        this.setData(patch)
        const jump = this.scrollToTalent && this.trees.length
        if (jump) this.scrollToTalent = false
        this.render(jump ? () => wx.pageScrollTo({ selector: '#talent-simulator', duration: 220 }) : undefined)
        return null
      })
    })
  },

  migrateSavedBuild() {
    try {
      const key = BUILD_KEY + this.classId
      if (wx.getStorageSync(key)) return
      const legacy = wx.getStorageSync(LEGACY_BUILD_KEY + this.classId)
      if (legacy) wx.setStorageSync(key, legacy)
    } catch (e) {}
  },

  /* 打开时先用哪套：分享链接带的码 > 本机存过的 > 空。
     分享那条要标出来——别人给的点法不是自己点的，界面得说清是谁的这套。 */
  startBuild() {
    if (this.shareBuild) {
      if (this.shareLayout && this.shareLayout !== this.talentLayout) {
        return { state: {}, error: '这套点法与当前天赋树版本不同，暂时无法带入。' }
      }
      const got = engine.decode(this.shareBuild, this.trees)
      const used = engine.spent(got.state, this.trees)
      if (used > 0 && (!this.shareLayout || (!got.bad && used <= this.rules.totalPoints))) {
        return { state: got.state, from: 'share', mode: this.shareMode }
      }
      if (this.shareLayout) return { state: {}, error: '这套点法暂时无法带入。' }
    }
    try {
      const saved = wx.getStorageSync(BUILD_KEY + this.classId)
      if (saved) {
        const got = engine.decode(String(saved), this.trees)
        if (engine.spent(got.state, this.trees) > 0) return { state: got.state, from: 'mine' }
      }
    } catch (e) {}
    return { state: {}, from: '' }
  },

  saveBuild() {
    if (this.shareBuild || !this.trees || !this.trees.length) return
    try {
      const code = engine.encode(this.trees, this.state)
      if (engine.spent(this.state, this.trees) > 0) wx.setStorageSync(BUILD_KEY + this.classId, code)
      else wx.removeStorageSync(BUILD_KEY + this.classId)
    } catch (e) {}
  },

  saveEditedBuild() {
    this.shareBuild = ''
    this.shareLayout = ''
    this.shareMode = ''
    this.setData({ fromShare: false, importMode: '', importError: '' })
    this.saveBuild()
  },

  /* 每次加减点重画整棵树：让 WXML 判"能不能点"会写出第二套规则，那是这次天裔漂移的老毛病 */
  render(onReady) {
    const trees = this.trees
    const rules = this.rules
    const nameOf = (id) => (this.nodeById[id] || {}).nameCn || ''
    const shown = trees.map((tr) => ({
      name: tr.name,
      art: tr.art,
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
            alt: n.nameAlt || '',
            missing: !n.nameCn,
            ranks: ranks,
            max: n.maxRanks === null || n.maxRanks === undefined ? '' : n.maxRanks,
            iconUrl: oss.iconUrl(this.batch, n.iconKey),
            tier: n.tier,
            treeName: tr.name,
            changeText: CHANGE_TEXT[n.changeState] || '',
            requires: (n.requires || []).map(nameOf).filter((x) => x).join('、'),
            full: !!n.maxRanks && ranks >= n.maxRanks,
            can: can.ok,
            why: can.ok ? '' : can.why
          }
        })
      }))
    }))
    const used = engine.spent(this.state, trees)
    const tab = this.data.treeTab
    this.setData({
      trees: shown,
      treeName: (shown[tab] || {}).name || '',
      remaining: Math.max(0, (rules ? rules.totalPoints : 51) - used),
      totalPoints: rules ? rules.totalPoints : 51,
      spentText: engine.describe(trees, this.state),
      buildCode: engine.encode(trees, this.state)
    }, onReady)
  },

  onTreeTab(e) {
    const i = Number(e.currentTarget.dataset.i || 0)
    this.setData({ treeTab: i, treeName: (this.data.trees[i] || {}).name || '' })
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
    this.saveEditedBuild()
    this.render()
  },

  /* 长按＝看详情（站主指令）。面板是本站自己的，系统对话框吃不到主题色 */
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
      this.saveEditedBuild()
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
    if (got.state !== this.state) {
      this.state = got.state
      this.saveEditedBuild()
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
        this.saveEditedBuild()
        this.render()
      }
    })
  },

  onSpells() {
    wx.navigateTo({ url: '/pages/spells/index?classId=' + encodeURIComponent(this.classId) })
  }
})
