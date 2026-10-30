const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const features = require('../../services/features')

/* 宏命令（2026-10-30 站主："web 网页端已经做完了，参考那边的数据来设计宏命令页面并实现"）
   数据真源只有一份：wow-forever-web/app/data/macros.json（网页宏页吃的就是它，245 条），
   分发层把它切成 1 张索引 + 9 片职业片（tools/oss-release.js 的宏命令线）。
   PLAN 当初写"沿用 guide.json.macros"，但那条一直是空的、宏实际落在 macros.json，
   所以这一页跟着真源走，不再复制第二份宏数据库。

   四条规矩从网页那条原样跟过来（根 AGENTS.md 2026-10-18「网页端放开清单」第 1 条 + 10-22 扩到小程序）：
   ① **只读 + 整条复制**：不做宏编辑器、不做导入导出、不做模拟执行、不跳外链（个人主体类目是"工具-信息查询"）；
   ② 一律免费，界面不出现收费/会员/兑换；
   ③ 每条都带"谁整理的 + 哪个文件 + 核对日期"，缺来源的构建时就不下发（不是标个"待核"糊上去）；
   ④ 不做循环提示类宏与强度评价——那句口径由索引下发，页面不改写措辞。
   这一页和配装页一样没有打包快照（一片最大 10 KB，但 245 条整份进主包不值当）：
   离线时明说"要联网才看得到"。入口由远程开关 macros 控制，关着的时候一个请求都不发。 */

const FLAG = 'macros'
/* 一次 setData 只画这么多条：整片 36 条一次塞进去还好，但"全部"视图与以后扩量都得有个上限
   （setData 有 1 MB 上限，专业页 511 行一次塞进去炸过一次） */
const LIST_STEP = 40

Page({
  data: {
    locked: false,
    lockName: '',
    loaded: false,
    offline: false,
    needOnline: false,
    sourceText: '',
    requiresUpdate: false,
    unavailable: false,
    errText: '',
    meta: null,
    classes: [],
    cls: '',
    clsName: '',
    groups: [],
    grp: '',
    q: '',
    rows: [],
    total: 0,
    shown: 0,
    rest: 0,
    loading: false,
    open: null,
    openSrc: '',
    statText: ''
  },

  onLoad(query) {
    this.want = (query && query.c) || ''
    this.start()
  },

  goHome() { wx.switchTab({ url: '/pages/home/index' }) },

  onPullDownRefresh() {
    this.start().then(() => wx.stopPullDownRefresh())
  },

  start() {
    return features.load(true).then(() => {
      if (!features.isOn(FLAG)) {
        const f = features.describe(FLAG) || {}
        /* loaded 保持 false：与专业页同一口径——"没开放"与"开放了但没数据"是两件事，
           界面走的是 locked 那一格，不该把 loaded 也点亮 */
        this.setData({ locked: true, lockName: f.name || '宏命令' })
        return null
      }
      return service.loadMeta().then((r) => {
        this.batch = r.batch
        this.setData({
          locked: false,
          sourceText: oss.sourceLabel(r),
          offline: r.source !== 'live',
          requiresUpdate: !!r.requiresUpdate
        })
        if (r.requiresUpdate) return null
        return oss.loadKey('macrosIndex').then((ri) => {
          const d = ri.data
          if (!d || !Array.isArray(d.classes) || !d.classes.length) {
            this.setData({ loaded: true, unavailable: true, errText: (ri.error && ri.error.message) || '宏清单没取到' })
            return null
          }
          this.index = d
          this.cols = d.cols || []
          this.shards = {}
          this.setData({
            loaded: true,
            meta: d.meta,
            classes: d.classes,
            statText: d.counts.sent + ' 条宏 · ' + d.counts.classes + ' 个职业 · '
              + d.counts.groups + ' 类用途 · 无限新增标"新" ' + d.counts.foreverNew + ' 条',
            needOnline: ri.source !== 'live'
          })
          const want = this.want && d.classes.some((c) => c.classId === this.want) ? this.want : d.classes[0].classId
          this.pickClassId(want)
        })
      })
    }).catch((e) => {
      this.setData({ loaded: true, unavailable: true, errText: ((e && (e.stack || e.message)) || String(e)).slice(0, 300) })
    })
  },

  /* 取这一职业那一片：点过就不再取一次（同一批内片是不可变的，缓存由取数层管） */
  pickClassId(classId) {
    const entry = (this.index.classes || []).filter((c) => c.classId === classId)[0]
    if (!entry) return
    this.setData({ cls: classId, clsName: entry.className, grp: '', rows: [], total: 0, shown: 0, rest: 0, loading: true })
    if (this.shards[classId]) { this.afterShard(this.shards[classId]); return }
    oss.loadMacroClass(entry, this.batch).then((r) => {
      if (!r.data || r.data.kind !== 'macros-class' || String(r.data.classId) !== String(classId)) {
        this.setData({ loading: false, errText: (r.error && r.error.message) || '这一职业的宏片没取到' })
        return
      }
      this.shards[classId] = r.data
      if (this.data.cls !== classId) return      /* 迟到的那一片不许盖掉后来选中的职业 */
      this.afterShard(r.data)
    }).catch((e) => this.setData({ loading: false, errText: (e && e.message) || String(e) }))
  },

  afterShard(shard) {
    const cols = this.cols
    const at = (row, name) => row[cols.indexOf(name)]
    const rows = (shard.rows || []).map((row) => {
      const nf = at(row, 'nameFrom') || {}
      const back = Object.keys(nf).filter((k) => nf[k] === 'addon').length
      return {
        id: at(row, 'id'),
        title: at(row, 'title'),
        group: at(row, 'group'),
        note: at(row, 'note') || '',
        body: at(row, 'body') || '',
        minLevel: at(row, 'minLevel'),
        isNew: at(row, 'new') === 1,
        srcName: ((shard.srcs || [])[at(row, 'src')] || {}).name || '来源待核',
        srcChecked: ((shard.srcs || [])[at(row, 'src')] || {}).date || '',
        nameBack: back
      }
    })
    const groups = []
    rows.forEach((r) => { if (groups.indexOf(r.group) < 0) groups.push(r.group) })
    this.all = rows
    this.setData({
      loading: false,
      groups: groups,
      errText: rows.length ? '' : this.data.errText
    })
    this.render()
  },

  /* 三个条件同时生效：用途 + 关键字（标题/说明/正文都参与），筛的就是当前职业那一片 */
  render() {
    const rows = this.all || []
    const q = String(this.data.q || '').trim().toLowerCase()
    const grp = this.data.grp
    const out = rows.filter((r) => {
      if (grp && r.group !== grp) return false
      if (!q) return true
      return (r.title + ' ' + r.note + ' ' + r.body + ' ' + r.group).toLowerCase().indexOf(q) >= 0
    })
    const cap = this._cap || LIST_STEP
    const shown = Math.min(out.length, cap)
    this.setData({
      rows: out.slice(0, shown),
      total: out.length,
      shown: shown,
      rest: Math.max(0, out.length - shown),
      filtered: !!q || !!grp
    })
  },

  pickClass(e) { this.pickClassId(e.currentTarget.dataset.id) },

  pickGroup(e) {
    const g = e.currentTarget.dataset.g
    this.setData({ grp: this.data.grp === g ? '' : g })
    this.render()
  },

  onSearch(e) { this.setData({ q: (e.detail && e.detail.value) || '' }); this.render() },

  /* "再显示 N 条"：只抬上限，筛选条件不变（一次塞整片会顶 setData 的 1 MB 上限） */
  showMore() { this._cap = (this._cap || LIST_STEP) + LIST_STEP; this.render() },

  clearFilters() { this._cap = LIST_STEP; this.setData({ q: '', grp: '' }); this.render() },

  openMacro(e) {
    const id = e.currentTarget.dataset.id
    const r = (this.all || []).filter((x) => x.id === id)[0]
    if (!r) return
    this.setData({ open: r, openSrc: r.srcName + (r.srcChecked ? ' · 核对 ' + r.srcChecked : '') })
  },

  closeMacro() { this.setData({ open: null, openSrc: '' }) },

  noop() {},

  copyBody() {
    const r = this.data.open
    if (!r || !r.body) return
    wx.setClipboardData({
      data: r.body,
      success: () => wx.showToast({ title: '宏文本已复制，进游戏粘贴即可', icon: 'none', duration: 2200 })
    })
  },

  copySource() {
    const r = this.data.open
    const url = ((this.index || {}).meta || {}).sources || []
    const s = url.filter((x) => r && x.name === r.srcName)[0]
    const text = s ? (s.name + '：' + s.url + '（核对 ' + (s.date || '?') + '）') : (r ? r.srcName : '')
    if (!text) return
    wx.setClipboardData({ data: text, success: () => wx.showToast({ title: '来源已复制', icon: 'none' }) })
  },

  shareNote() {
    return { title: '宏命令 · 免费列出、标来源', path: '/pages/macros/index' }
  },

  onShareAppMessage() {
    const r = this.data.open
    return {
      title: r ? (r.title + ' · 宏命令') : '宏命令 · 免费列出、标来源',
      path: '/pages/macros/index' + (this.data.cls ? '?c=' + this.data.cls : '')
    }
  }
})
