const service = require('../../services/forever-data')

const SOURCE_TEXT = {
  live: '实时数据',
  cache: '离线缓存',
  snapshot: '打包快照'
}

const CLASS_CN = {
  warrior: '战士',
  paladin: '圣骑士',
  hunter: '猎人',
  rogue: '潜行者',
  priest: '牧师',
  shaman: '萨满祭司',
  mage: '法师',
  warlock: '术士',
  druid: '德鲁伊'
}

const RENDER_LIMIT = 200

Page({
  data: {
    all: [],
    list: [],
    kinds: [],
    activeKind: 'all',
    kw: '',
    onlyFav: false,
    favIds: [],
    expandedId: '',
    truncated: 0,
    loaded: false,
    offline: false,
    sourceText: '',
    baseline: ''
  },

  onLoad() {
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  refresh() {
    return service.loadGlossary().then((result) => {
      const payload = result.data || {}
      const all = (payload.items || []).map((item) => this.decorate(item))
      const kindsMap = {}
      all.forEach((item) => {
        kindsMap[item.kindKey] = (kindsMap[item.kindKey] || 0) + 1
      })
      const kinds = [{ key: 'all', name: '全部', count: all.length }]
        .concat(Object.keys(kindsMap).map((key) => ({ key, name: key, count: kindsMap[key] })))
      const meta = payload.meta || {}
      this.setData({
        all,
        kinds,
        loaded: true,
        sourceText: SOURCE_TEXT[result.source] || '',
        offline: result.source !== 'live',
        baseline: meta.generatedAt || '',
        favIds: service.getFavorites()
      })
      this.applyFilter()
    })
  },

  decorate(item) {
    return {
      id: item.id,
      cn: item.cn,
      en: item.en || '',
      kindKey: service.kindName(item.kind),
      classCn: item.classId ? (CLASS_CN[item.classId] || item.classId) : '种族',
      level: item.level || 'L3',
      levelName: service.levelName(item.level),
      prov: item.provenance || [],
      fav: false
    }
  },

  applyFilter() {
    const kw = this.data.kw.trim().toLowerCase()
    const kind = this.data.activeKind
    const onlyFav = this.data.onlyFav
    const favSet = {}
    service.getFavorites().forEach((id) => { favSet[id] = 1 })
    const matched = this.data.all.filter((item) => {
      if (kind !== 'all' && item.kindKey !== kind) return false
      if (onlyFav && !favSet[item.id]) return false
      if (!kw) return true
      return (item.cn || '').toLowerCase().indexOf(kw) >= 0
        || (item.en || '').toLowerCase().indexOf(kw) >= 0
    })
    // 收藏心标只更新列表数据，不整页刷新
    this.setData({
      favIds: Object.keys(favSet),
      list: matched.slice(0, RENDER_LIMIT).map((item) => Object.assign({}, item, { fav: !!favSet[item.id] })),
      truncated: Math.max(matched.length - RENDER_LIMIT, 0)
    })
  },

  onKw(e) {
    this.setData({ kw: e.detail.value }, () => this.applyFilter())
  },

  onKind(e) {
    this.setData({ activeKind: e.currentTarget.dataset.kind }, () => this.applyFilter())
  },

  onToggleFavOnly() {
    this.setData({ onlyFav: !this.data.onlyFav }, () => this.applyFilter())
  },

  onFav(e) {
    const id = e.currentTarget.dataset.id
    const added = service.toggleFavorite(id)
    wx.showToast({ title: added ? '已收藏' : '已取消收藏', icon: 'none' })
    this.applyFilter()
  },

  onToggleDetail(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ expandedId: this.data.expandedId === id ? '' : id })
  },

  onCopy(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.all.filter((x) => x.id === id)[0]
    if (!item) return
    const text = item.cn + (item.en ? ' / ' + item.en : '（英文名待补）') + ' · ' + item.kindKey + ' · ' + item.levelName
    wx.setClipboardData({
      data: text,
      success() {
        wx.showToast({ title: '已复制', icon: 'none' })
      }
    })
  },

  onOpenSource(e) {
    const url = e.currentTarget.dataset.url
    if (!url) return
    wx.setClipboardData({
      data: url,
      success() {
        wx.showToast({ title: '来源链接已复制，请到浏览器打开', icon: 'none', duration: 2500 })
      }
    })
  }
})
