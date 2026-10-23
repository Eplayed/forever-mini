const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const uiArt = require('../../services/ui-art')

/* 职业 tab（M03）
   站主给的新 IA：种族 → 职业 → 可选职业 → 天赋树。
   玩家面规矩照旧：不挂条数、不挂分级徽标、不写"我们缺什么"；
   天赋树只读摆位，门槛没核到之前不做解锁判定（根 AGENTS.md 第五条）。 */
const FACTION = { alliance: '联盟', horde: '部落' }

Page({
  data: {
    races: [],
    allianceRaces: [],
    hordeRaces: [],
    padAlliance: [],
    padHorde: [],
    picked: null,
    classes: [],
    combos: [],
    expandedRace: '',
    loaded: false,
    offline: false,
    requiresUpdate: false,
    bgUrl: '',
    errorText: ''
  },

  onLoad() {
    this.batch = null
    uiArt.tabBg().then((b) => this.setData({ bgUrl: b.url }))
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  /* 底图取不到就撤这两层，页面回纯色版式（碎图比没图更糟） */
  onBgError() {
    this.setData({ bgUrl: '' })
  },

  onShareAppMessage() {
    return { title: '无限职业与种族：可选组合、技能书与天赋树', path: '/pages/classes/index' }
  },

  refresh() {
    return service.loadClassIndex().then((r) => {
      this.batch = r.batch
      const d = r.data || {}
      const classMap = {}
      ;(d.classes || []).forEach((c) => { classMap[c.classId] = c })
      this.classMap = classMap
      /* WXML 里不能用变量当下标取对象（classMap[cid] 不生效），
         所以可选职业在 JS 里先拼成带名字的数组 */
      const races = (d.races || []).map((x) => ({
        id: x.id,
        nameCn: x.nameCn || '中文名待核',
        nameEn: x.nameEn || '',
        faction: x.faction || '',
        factionText: FACTION[x.faction] || x.faction || '',
        /* 种族小图优先走素材层那张（暗夜精灵与天裔官方 CDN 都没有，用库里已有的那张） */
        iconUrl: oss.raceIconUrl(this.batch, x),
        subgroup: x.subgroup ? (x.subgroup.nameCn || '') : '',
        traits: (x.traits || []).map((t) => ({
          name: t.name, passive: t.passive, effect: t.effect || '',
          iconUrl: oss.iconUrl(this.batch, t.iconKey)
        })),
        classList: (x.classes || []).map((cid) => ({
          classId: cid,
          nameCn: (classMap[cid] || {}).nameCn || cid
        }))
      }))
      /* 种族区按阵营分两框（2026-10-23 站主："按照职业详情中做的那样，分 2 框体显示"）：
         框色吃阵营令牌，框内一格只有图标与名字，一行三个、补空位往下排，
         框里不再写"联盟/部落"——那两句话由框体的颜色与位置说。
         点一格不在框里展开（一框只有约 170rpx 宽，特长那种整句压不住），
         而是把这一族的可选职业与特长铺在两框下面整宽显示。 */
      const byFaction = { alliance: [], horde: [] }
      races.forEach((x) => { if (byFaction[x.faction]) byFaction[x.faction].push(x) })
      const cell = (x) => ({ id: x.id, nameCn: x.nameCn, iconUrl: x.iconUrl })
      const pads = (n) => [0, 1, 2].slice(0, (3 - n % 3) % 3)
      this.raceById = {}
      races.forEach((x) => { this.raceById[x.id] = x })
      this.setData({
        races,
        allianceRaces: byFaction.alliance.map(cell),
        hordeRaces: byFaction.horde.map(cell),
        padAlliance: pads(byFaction.alliance.length),
        padHorde: pads(byFaction.horde.length),
        picked: this.pickRow(this.data.expandedRace),
        classes: (d.classes || []).map((c) => ({
          classId: c.classId,
          nameCn: c.nameCn || '中文名待核',
          nameEn: c.nameEn || '',
          iconUrl: oss.iconUrl(this.batch, c.iconKey),
          hasTalents: !!c.hasTalents
        })),
        /* 组合卡：图标在上、"兽人法师"这样的整名在下（2026-10-22 站主要 3 列上下结构）。
           2026-10-23 二次指令：格子里放**种族**图标，不是职业图标——
           一格写着"兽人法师"却画一张法师脸，玩家看不出这组合新在哪个种族。
           点它进的还是那个职业的天赋页（classId 没变）。 */
        combos: (d.combos || []).map((x) => ({
          label: x.label || (x.raceCn + x.classCn),
          classId: x.classId || '',
          raceId: x.raceId || '',
          iconUrl: oss.raceIconUrl(this.batch, { portrait: x.racePortrait, iconKey: x.raceIconKey })
        })),
        loaded: true,
        offline: r.source !== 'live',
        requiresUpdate: !!r.requiresUpdate,
        errorText: r.error ? String(r.error.message || r.error).slice(0, 120) : ''
      })
      return null
    })
  },

  pickRow(id) {
    return (this.raceById || {})[id] || null
  },

  onRaceToggle(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const next = this.data.expandedRace === id ? '' : id
    this.setData({ expandedRace: next, picked: this.pickRow(next) })
  },

  onPickClass(e) {
    const id = String(e.currentTarget.dataset.id || '')
    if (!id) return
    wx.navigateTo({ url: '/pages/class/index?classId=' + encodeURIComponent(id) })
  },

  /* 组合格：有职业的开这个职业的天赋页；只有种族没有职业的那一格（"天裔"——
     公告里它是"首次登场的种族"，不属于哪个新组合）就选中原族、把下面那块详情铺出来。
     点了没反应的那一格不许留在页面上。 */
  onPickCombo(e) {
    const ds = (e && e.currentTarget && e.currentTarget.dataset) || {}
    const cls = String(ds.id || '')
    if (cls) {
      wx.navigateTo({ url: '/pages/class/index?classId=' + encodeURIComponent(cls) })
      return
    }
    const race = String(ds.race || '')
    if (!race) return
    this.setData({ expandedRace: race, picked: this.pickRow(race) })
    wx.pageScrollTo({ selector: '.race-body', duration: 200 })
  }
})
