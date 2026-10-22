const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')

/* 与网页端 app/src/pages/SkillsPage.vue 同一套说法，两边不许各写一版 */
const SP_STATE = { same: '与经典一致', changed: '改动', new: '无限新增', removed: '已移除', renamed: '改名' }
const SP_REL = { talent: '天赋赋予', race: '种族技能', earlier: '比经典更早学会', baseline: '职业技能' }
const RENDER_LIMIT = 200

Page({
  data: {
    classes: [],
    classId: '',
    className: '',
    fieldNote: '',
    pageNote: '',
    groups: [],
    list: [],
    kw: '',
    total: 0,
    expandedId: '',
    loaded: false,
    offline: false,
    needOnline: false,
    sourceText: '',
    requiresUpdate: false,
    buildId: '',
    truncated: 0,
    errorText: ''
  },

  onLoad(query) {
    this.batch = null
    this.all = []
    this.refresh(query && query.classId ? String(query.classId) : '')
  },

  onPullDownRefresh() {
    this.refresh(this.data.classId).then(() => wx.stopPullDownRefresh())
  },

  onShareAppMessage() {
    const c = this.currentClass()
    return {
      title: c ? '无限 ' + c.nameCn + ' 技能速查' : '无限职业技能速查',
      path: c ? '/pages/spells/index?classId=' + c.classId : '/pages/spells/index'
    }
  },

  refresh(pickClassId) {
    return service.loadSpellClasses().then((r) => {
      this.batch = r.batch
      const data = r.data || {}
      const classes = (data.classes || []).map((c) => Object.assign({}, c, {
        iconUrl: oss.iconUrl(this.batch, c.iconKey),
        levelName: service.levelName(c.level),
        tabCount: (c.tabs || []).length
      }))
      this.classes = classes
      this.setData({
        classes,
        fieldNote: data.fieldNote || '',
        pageNote: data.pageNote || '',
        loaded: true,
        requiresUpdate: !!r.requiresUpdate,
        offline: r.source !== 'live',
        sourceText: r.sourceText,
        buildId: r.buildId || '',
        errorText: r.error ? String(r.error.message || r.error).slice(0, 120) : ''
      })
      if (pickClassId) return this.selectClass(pickClassId)
      return null
    })
  },

  currentClass() {
    const id = this.data.classId
    return (this.classes || []).filter((c) => c.classId === id)[0] || null
  },

  selectClass(classId) {
    const item = (this.classes || []).filter((c) => c.classId === classId)[0]
    if (!item) {
      this.setData({ classId: '', className: '', groups: [], list: [] })
      return Promise.resolve(null)
    }
    this.setData({ classId: item.classId, className: item.nameCn || item.classId, loaded: false, expandedId: '' })
    return service.loadSpellClass(item, this.batch).then((r) => {
      const rows = r.data && r.data.spells ? r.data.spells : []
      this.all = rows.map((s) => this.decorate(s))
      this.setData({
        loaded: true,
        total: this.all.length,
        needOnline: r.source !== 'live' && r.source !== 'cache',
        offline: r.source !== 'live',
        sourceText: r.sourceText,
        errorText: r.error ? String(r.error.message || r.error).slice(0, 120) : ''
      })
      /* 名单说 N 条、分片里只有 M 条：这是数据问题，界面必须说出来，
         不许静默少给（客户端契约里 shape 已经拦过一层，这里再兜一次） */
      if (item.count && rows.length && rows.length !== item.count) {
        this.setData({ errorText: '职业名单写 ' + item.count + ' 条，这一片里只有 ' + rows.length + ' 条，本站会记下来核对。' })
      }
      this.applyFilter()
      return null
    })
  },

  decorate(s) {
    const alt = []
    if (s.ranksAlt && s.ranksAlt !== s.ranks) alt.push('级数另有一说：' + s.ranksAlt + ' 级（' + (s.ranksAltFrom || '另一份资料') + '）')
    if (s.learnAlt && s.learnAlt !== s.learnLevel) alt.push('起学等级另有一说：' + s.learnAlt + ' 级（' + (s.learnAltFrom || '另一份资料') + '）')
    return {
      id: s.id,
      name: s.name || '（中文名待核）',
      missing: !s.name,
      tab: s.tab || '未分类',
      iconUrl: oss.iconUrl(this.batch, s.iconKey),
      rankText: s.ranks ? s.ranks + ' 级' : '级数待实测',
      learnText: s.learnLevel ? s.learnLevel + ' 级起' : '学习等级待实测',
      stateText: s.state ? (SP_STATE[s.state] || s.state) : '',
      stateKey: s.state || '',
      relText: s.relation ? (SP_REL[s.relation] || s.relation) : '',
      level: s.level || 'L3',
      levelName: service.levelName(s.level),
      altText: alt.join('；'),
      ranks: (s.spellRanks || []).map((x) => ({ spellId: x.spellId, learnLevel: x.learnLevel })),
      prov: (s.provenance || []).map((p) => ({
        type: p.type || '未标注',
        url: p.url || '',
        checkedAt: p.checkedAt || '未记录'
      }))
    }
  },

  applyFilter() {
    const kw = String(this.data.kw || '').trim().toLowerCase()
    const hit = !kw ? this.all : this.all.filter((s) => {
      return String(s.name).toLowerCase().indexOf(kw) >= 0
        || String(s.tab).toLowerCase().indexOf(kw) >= 0
        || String(s.stateText).toLowerCase().indexOf(kw) >= 0
    })
    const shown = hit.slice(0, RENDER_LIMIT)
    const byTab = {}
    const order = []
    shown.forEach((s) => {
      if (!byTab[s.tab]) { byTab[s.tab] = []; order.push(s.tab) }
      byTab[s.tab].push(s)
    })
    this.setData({
      list: shown,
      groups: order.map((t) => ({ tab: t, rows: byTab[t] })),
      truncated: hit.length > shown.length ? hit.length : 0
    })
  },

  onKw(e) {
    this.setData({ kw: e.detail.value })
    this.applyFilter()
  },

  onPick(e) {
    this.selectClass(String(e.currentTarget.dataset.id || ''))
  },

  onBackToClasses() {
    this.setData({ classId: '', className: '', groups: [], list: [], kw: '', expandedId: '' })
  },

  onToggle(e) {
    const id = String(e.currentTarget.dataset.id || '')
    this.setData({ expandedId: this.data.expandedId === id ? '' : id })
  },

  onOpenSource(e) {
    const url = String(e.currentTarget.dataset.url || '')
    if (!url || url.indexOf('http') !== 0) {
      wx.showToast({ title: '这条只记了资料名，没有可打开的网址', icon: 'none' })
      return
    }
    /* 个人主体不开 web-view，只能复制链接让玩家自己看 */
    wx.setClipboardData({
      data: url,
      success: () => wx.showToast({ title: '来源网址已复制', icon: 'none' })
    })
  },

  onCopy(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const s = (this.all || []).filter((x) => x.id === id)[0]
    if (!s) return
    const lines = [
      '《无限》' + (this.data.className || '') + ' · ' + s.tab,
      s.name,
      s.rankText + ' · ' + s.learnText,
      s.stateText ? '与经典旧世：' + s.stateText : '',
      s.altText ? '另一说：' + s.altText : '',
      '整理自无限测试版客户端资料，非官方结论'
    ].filter(Boolean)
    wx.setClipboardData({ data: lines.join('\n'), success: () => wx.showToast({ title: '已复制', icon: 'none' }) })
  }
})
