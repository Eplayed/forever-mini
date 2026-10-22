const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')

/* 品质四档是本站现用的叫法，与网页端 ItemsPage 的 QUALITY 同一份，别在页面里另写 */
const QUALITY = { 1: '普通', 2: '良好', 3: '稀有', 4: '史诗' }
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
    disclaimer: '',
    expandedId: ''
  },

  onLoad() {
    this.rows = []
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
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
              qualityText: QUALITY[row[iQ]] || '未说明',
              level: row[iLv] || 'L3',
              levelName: service.levelName(row[iLv]),
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
        note: d.note || '',
        qualityNote: d.qualityNote || '',
        disclaimer: d.lootDisclaimer || '',
        requiresUpdate: !!r.requiresUpdate,
        needOnline: r.source !== 'live' && r.source !== 'cache',
        offline: r.source !== 'live',
        sourceText: r.sourceText,
        buildId: r.buildId || '',
        errorText: mismatch
          ? '这张表的行数与条数对不上（清单写 ' + ((d.counts || {}).rows) + ' 行，拼出 ' + rowCount + ' 行），本站会记下来核对。'
          : (r.error ? String(r.error.message || r.error).slice(0, 120) : '')
      })
      this.applyFilter()
      return null
    })
  },

  applyFilter() {
    const kw = String(this.data.kw || '').trim().toLowerCase()
    const all = this.items || []
    const hit = !kw ? [] : all.filter((x) => {
      return String(x.name).toLowerCase().indexOf(kw) >= 0 || String(x.id).indexOf(kw) >= 0
    })
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

  onOpenDungeon(e) {
    const id = String(e.currentTarget.dataset.id || '')
    if (!id) return
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + encodeURIComponent(id) })
  },

  onCopy(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const x = (this.items || []).filter((y) => y.id === id)[0]
    if (!x) return
    const lines = [
      '《无限》掉落：' + x.name + '（物品编号 ' + x.id + '）',
      '品质：' + x.qualityText,
      x.sources.map((s) => '出自 ' + s.dungeon + (s.boss ? ' · ' + s.boss : '')).join('\n'),
      '整理自无限测试版客户端资料，本站不写掉落几率'
    ].filter(Boolean)
    wx.setClipboardData({ data: lines.join('\n'), success: () => wx.showToast({ title: '已复制', icon: 'none' }) })
  }
})
