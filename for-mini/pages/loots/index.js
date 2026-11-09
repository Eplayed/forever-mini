const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')
const RENDER_LIMIT = 100

Page({
  data: {
    kw: '',
    list: [],
    total: 0,
    itemCount: 0,
    loaded: false,
    offline: false,
    needOnline: false,
    sourceText: '',
    requiresUpdate: false,
    buildId: '',
    truncated: 0,
    errorText: '',
    note: '',
    qualityNote: '',
    expandedId: '',
    filterDungeon: '',
    filterBoss: '',
    filterDungeonName: ''
  },

  onLoad(options) {
    this.rows = []
    /* 从副本详情点首领跳过来：只看那座本那位首领掉的装备（2026-11-09 站主要求）。
       微信的 onLoad options 不会自动解码——真机踩过：筛选条直接显示 %E9 编码串、
       一件都匹配不上。传的时候编了码，接的时候必须自己解回来。 */
    const dec = (v) => { try { return decodeURIComponent(String(v || '')) } catch (e) { return String(v || '') } }
    this.setData({
      filterDungeon: dec(options && options.dungeon),
      filterBoss: dec(options && options.boss),
      filterDungeonName: dec(options && options.dname)
    })
    this.refresh()
  },

  onClearFilter() {
    this.setData({ filterDungeon: '', filterBoss: '', filterDungeonName: '', kw: '', list: [], truncated: 0, expandedId: '' })
    this.applyFilter()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  /* 朋友圈（2026-11-03 站主要求全站可分享） */
  onShareTimeline() {
    return { title: '掉落查询：搜副本或物品名，直达那座本' }
  },

  onShareAppMessage() {
    return { title: '无限掉落反查：这件装备哪座本掉', path: '/pages/loots/index' }
  },

  refresh() {
    return service.loadLootIndex().then((r) => {
      const d = r.data || {}
      const cols = d.cols || []
      const iId = Math.max(cols.indexOf('itemId'), 0)
      const iName = Math.max(cols.indexOf('name'), 0)
      const iQ = Math.max(cols.indexOf('quality'), 0)
      const iIcon = Math.max(cols.indexOf('iconKey'), 0)
      const iBoss = Math.max(cols.indexOf('boss'), 0)
      const iLv = Math.max(cols.indexOf('level'), 0)
      const byItem = {}
      const order = []
      let rowCount = 0
      ;(d.dungeons || []).forEach((du) => {
        (du.rows || []).forEach((row) => {
          rowCount += 1
          const key = String(row[iId] || row[iName] || '')
          if (!key) return
          if (!byItem[key]) {
            byItem[key] = {
              id: key,
              name: row[iName] || '（中文名待核）',
              missing: !row[iName],
              quality: row[iQ],
              qualityText: quality.qualityName(row[iQ]),
              iconUrl: oss.iconUrl(r.batch, row[iIcon]),
              sources: []
            }
            order.push(byItem[key])
          }
          byItem[key].sources.push({
            dungeonId: du.id,
            dungeon: du.nameCn || du.id,
            dungeonMissing: !du.nameCn,
            boss: (du.bosses || [])[row[iBoss]] || '未记首领'
          })
        })
      })
      this.items = order
      /* 表说 N 行、拼出来 M 行：这是数据问题，界面必须说出来 */
      const mismatch = (d.counts && d.counts.rows && d.counts.rows !== rowCount)
        || (d.counts && d.counts.items && d.counts.items !== order.length)
      this.setData({
        loaded: true,
        total: rowCount,
        itemCount: order.length,
        buildId: r.buildId || '',
        note: d.note || '',
        qualityNote: d.qualityNote || '',
        requiresUpdate: !!r.requiresUpdate,
        needOnline: r.source !== 'live' && r.source !== 'cache',
        offline: r.source !== 'live',
        sourceText: r.sourceText,
        errorText: mismatch
          ? '这张表的行数与条数对不上（清单写 ' + ((d.counts || {}).rows) + ' 行，拼出 ' + rowCount + ' 行），本站会记下来核对。'
          : (r.error ? this.errText(r.error) : '')
      })
      this.applyFilter()
      return null
    })
  },

  /* 真机踩过：error 是对象且没有 message 字段时，String() 出来就是 [object Object]——
     界面上滚一条人话，不放调试残渣 */
  errText(e) {
    if (!e) return ''
    if (typeof e === 'string') return e.slice(0, 120)
    const m = e.message || e.errMsg
    return (typeof m === 'string' ? m : JSON.stringify(e)).slice(0, 120)
  },

  applyFilter() {
    const kw = String(this.data.kw || '').trim().toLowerCase()
    const fd = this.data.filterDungeon || ''
    const fb = this.data.filterBoss || ''
    const base = this.items || []
    let pool = base
    if (fd || fb) {
      /* 只看某座本（某位首领）：把没命中的来源整组裁掉，一件装备在别处也掉时不把别处混进来 */
      pool = base
        .map((x) => ({ x, hits: x.sources.filter((s) => (!fd || s.dungeonId === fd) && (!fb || s.boss === fb)) }))
        .filter((p) => p.hits.length)
        .map((p) => Object.assign({}, p.x, { sources: p.hits }))
    }
    /* 两种给清单的方式：带筛选进来（副本详情点首领跳转）→ 落地直接列这一位掉的，
       不让玩家再打一遍关键词；没筛选 → 保持原样"先输入要查的东西"，不把一千行全泼出来 */
    const hit = kw
      ? pool.filter((x) => String(x.name).toLowerCase().indexOf(kw) >= 0 || String(x.id).indexOf(kw) >= 0)
      : (fd || fb ? pool : [])
    const shown = hit.slice(0, RENDER_LIMIT)
    this.setData({ list: shown, truncated: hit.length > shown.length ? hit.length : 0 })
  },

  onKw(e) {
    this.setData({ kw: e.detail.value })
    this.applyFilter()
  },

  onClear() {
    this.setData({ kw: '', list: [], truncated: 0, expandedId: '' })
  },

  onToggle(e) {
    const id = String(e.currentTarget.dataset.id || '')
    this.setData({ expandedId: this.data.expandedId === id ? '' : id })
  },

  /* 站主要的路径：搜到物品 → 跳进那座本 → 把查的这件高亮出来 */
  onOpenDungeon(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const item = String(e.currentTarget.dataset.item || '')
    if (!id) return
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + encodeURIComponent(id) + (item ? '&drop=' + encodeURIComponent(item) : '') })
  },

  onCopy(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const x = (this.items || []).filter((y) => y.id === id)[0]
    if (!x) return
    const lines = [
      '《无限》掉落：' + x.name + '（物品编号 ' + x.id + '）',
      '品质：' + x.qualityText,
      x.sources.map((s) => '出自 ' + s.dungeon + (s.boss ? ' · ' + s.boss : ''))
    ].filter(Boolean)
    wx.setClipboardData({ data: lines.join('\n'), success: () => wx.showToast({ title: '已复制', icon: 'none' }) })
  }
})
