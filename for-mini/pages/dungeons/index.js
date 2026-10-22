const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')

/* 副本随手查（2026-10-22 玩家面清理）
   ------------------------------------------------------------------
   数据只有一条路：services/forever-data.js → oss-manifest 的指针 → 索引分片 → 主包快照兜底。
   界面这里的规矩：
   · 字段按"有没有"显示，缺的说「待实测 / 没有记录」，不许拿空值冒充 0 或"不存在"；
   · source 不是 live 就顶条说明，缓存/快照不许静默呈现；
   · 站主定的：玩家不看聚合数——chip 上不挂条数、行里不写"几个首领几条掉落"、
     可信度筛选整排下线（那是维护用的档，不是玩家的任务）。 */

const KIND_LABEL = { new: '无限新本', classic: '经典本', raid: '团本' }
const KIND_ORDER = ['new', 'classic', 'raid']

Page({
  data: {
    all: [],
    list: [],
    kinds: [],
    activeKind: 'all',
    kw: '',
    onlyFav: false,
    recent: [],
    empty: false,
    loaded: false,
    offline: false,
    sourceText: '',
    requiresUpdate: false,
    factLatest: '',
    buildId: '',
    dataFrom: '',
    cacheHit: false,
    disclaimer: ''
  },

  onLoad() {
    this.refresh()
  },

  onShow() {
    this.syncLocal()
    this.applyFilter()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  refresh() {
    return service.loadDungeonIndex().then((r) => {
      const payload = r.data || {}
      const all = (payload.items || []).map((it) => decorate(it, r.batch))
      /* sourceText / buildId / factLatest / dataFrom / cacheHit 不上界面（玩家面规矩），
         但它们是四态契约的读点：门禁与排障要能读到"这一屏到底是 live 还是缓存/快照"，
         所以留在 data 里、不渲染。 */
      this.setData({
        all,
        loaded: true,
        offline: r.source !== 'live',
        sourceText: r.sourceText,
        requiresUpdate: r.requiresUpdate,
        factLatest: (r.factDates && r.factDates.latest) || '',
        buildId: r.buildId || '',
        dataFrom: r.source,
        cacheHit: !!r.cacheHit,
        disclaimer: payload.lootDisclaimer || ''
      })
      this.syncLocal()
      this.applyFilter()
    })
  },

  syncLocal() {
    const map = {}
    this.data.all.forEach((it) => { map[it.id] = it })
    const recent = service.getRecentDungeons().filter((id) => map[id]).slice(0, 6).map((id) => map[id])
    this.setData({ recent })
  },

  matches(item, facets, favSet, kw) {
    if (facets.kind !== 'all' && item.kind !== facets.kind) return false
    if (facets.fav && !favSet[item.id]) return false
    if (!kw) return true
    return [item.nameCn, item.nameEn, item.nameCnConflict, item.zoneCn, item.id]
      .some((v) => v && String(v).toLowerCase().indexOf(kw) >= 0)
  },

  applyFilter() {
    const favSet = {}
    service.getFavoriteDungeons().forEach((id) => { favSet[id] = 1 })
    const kw = this.data.kw.trim().toLowerCase()
    const all = this.data.all
    const facets = { kind: this.data.activeKind, fav: this.data.onlyFav }
    const matched = all.filter((it) => this.matches(it, facets, favSet, kw))
    const kinds = [{ key: 'all', label: '全部' }]
      .concat(KIND_ORDER.filter((k) => all.some((it) => it.kind === k))
        .map((k) => ({ key: k, label: KIND_LABEL[k] })))
    this.setData({
      list: matched.map((it) => Object.assign({}, it, { fav: !!favSet[it.id] })),
      kinds,
      empty: matched.length === 0 && all.length > 0
    })
  },

  onKw(e) {
    this.setData({ kw: e.detail.value })
    this.applyFilter()
  },

  onKind(e) {
    this.setData({ activeKind: e.currentTarget.dataset.kind })
    this.applyFilter()
  },

  onFavOnly() {
    this.setData({ onlyFav: !this.data.onlyFav })
    this.applyFilter()
  },

  onFav(e) {
    const id = e.currentTarget.dataset.id
    const added = service.toggleFavoriteDungeon(id)
    wx.showToast({ title: added ? '已收藏' : '已取消收藏', icon: 'none' })
    this.syncLocal()
    this.applyFilter()
  },

  onOpen(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + encodeURIComponent(id) })
  },

  /* 虚线边那一格是跳页，不是本页筛选；掉落反查不是 tab 页，用 navigateTo */
  onLoots() {
    wx.navigateTo({ url: '/pages/loots/index' })
  },

  onShareAppMessage() {
    return { title: '无限服副本随手查：等级、首领与掉落', path: '/pages/dungeons/index' }
  }
})

function decorate(item, batch) {
  return {
    id: item.id,
    kind: item.kind,
    kindLabel: KIND_LABEL[item.kind] || item.kind || '副本',
    nameCn: item.nameCn || '',
    nameEn: item.nameEn || '',
    nameCnConflict: item.nameCnConflict || '',
    title: item.nameCn || item.nameEn || item.id,
    nameMissing: !item.nameCn,
    enMissing: !item.nameEn,
    rangeText: item.levelRange || '等级待实测',
    faction: item.faction || '',
    zoneCn: item.zoneCn || '',
    /* 列表行缩略图：art 是相对 assets/ 的路径，地址由 oss-manifest 拼（页面不自己拼 URL）。
       没这张图的座（art 为 null）界面直接不摆格子，不摆一个空框冒充有图。 */
    artUrl: item.art ? oss.assetUrl(batch, item.art) : '',
    fav: false
  }
}
