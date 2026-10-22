const service = require('../../services/forever-data')

/* 副本随手查（M01 首单）
   ------------------------------------------------------------------
   数据只有一条路：services/forever-data.js → oss-manifest 的指针 → 索引分片 → 主包快照兜底。
   界面这里的规矩：
   · 字段按"有没有"显示，缺的说「待实测 / 没有记录」，不许拿空值冒充 0 或"不存在"；
   · 筛选计数与筛选结果同一口径（切一个维度，其它维度按钮上的数字跟着变）；
   · source 不是 live 就顶条说明，缓存/快照不许静默呈现。 */

const KIND_LABEL = { new: '无限新本', classic: '经典本', raid: '团本' }
const KIND_ORDER = ['new', 'classic', 'raid']
const LEVELS = ['L0', 'L1', 'L2', 'L3']

Page({
  data: {
    all: [],
    list: [],
    kinds: [],
    levels: [],
    activeKind: 'all',
    activeLevel: 'all',
    kw: '',
    onlyFav: false,
    favCount: 0,
    recent: [],
    empty: false,
    loaded: false,
    offline: false,
    sourceText: '',
    requiresUpdate: false,
    factLatest: '',
    buildId: '',
    totals: { total: 0, newDungeons: 0, classicDungeons: 0, raids: 0 },
    routeMissing: 0,
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
      const all = (payload.items || []).map(decorate)
      this.setData({
        all,
        loaded: true,
        offline: r.source !== 'live',
        sourceText: r.sourceText,
        requiresUpdate: r.requiresUpdate,
        factLatest: (r.factDates && r.factDates.latest) || '',
        buildId: r.buildId || '',
        dataFrom: r.source,
        totals: payload.counts || {},
        routeMissing: (payload.notCollected && payload.notCollected.route) || 0,
        disclaimer: payload.lootDisclaimer || ''
      })
      this.syncLocal()
      this.applyFilter()
    })
  },

  syncLocal() {
    const map = {}
    this.data.all.forEach((it) => { map[it.id] = it })
    const fav = service.getFavoriteDungeons().filter((id) => map[id])
    const recent = service.getRecentDungeons().filter((id) => map[id]).slice(0, 6).map((id) => map[id])
    this.setData({ favCount: fav.length, recent })
  },

  matches(item, facets, favSet, kw) {
    if (facets.kind !== 'all' && item.kind !== facets.kind) return false
    if (facets.level !== 'all' && item.level !== facets.level) return false
    if (facets.fav && !favSet[item.id]) return false
    if (!kw) return true
    return [item.nameCn, item.nameEn, item.nameCnConflict, item.zoneCn, item.id]
      .some((v) => v && String(v).toLowerCase().indexOf(kw) >= 0)
  },

  facets(skip) {
    return {
      kind: skip === 'kind' ? 'all' : this.data.activeKind,
      level: skip === 'level' ? 'all' : this.data.activeLevel,
      fav: skip === 'fav' ? false : this.data.onlyFav
    }
  },

  applyFilter() {
    const favSet = {}
    service.getFavoriteDungeons().forEach((id) => { favSet[id] = 1 })
    const kw = this.data.kw.trim().toLowerCase()
    const all = this.data.all
    const matched = all.filter((it) => this.matches(it, this.facets(), favSet, kw))
    /* 每个按钮上的数字＝"其它筛选已生效时，这一类有几座"，
       所以不会出现"筛完只剩 3 座、别的按钮还写着 26"。 */
    const countBy = (key, value) => all.filter((it) => {
      const f = this.facets(key)
      f[key] = value
      return this.matches(it, f, favSet, kw)
    }).length
    const kinds = [{ key: 'all', label: '全部', count: countBy('kind', 'all') }]
      .concat(KIND_ORDER.filter((k) => all.some((it) => it.kind === k))
        .map((k) => ({ key: k, label: KIND_LABEL[k], count: countBy('kind', k) })))
    const levels = [{ key: 'all', label: '全部可信度', count: countBy('level', 'all') }]
      .concat(LEVELS.filter((l) => all.some((it) => it.level === l))
        .map((l) => ({ key: l, label: l, count: countBy('level', l) })))
    this.setData({
      list: matched.map((it) => Object.assign({}, it, { fav: !!favSet[it.id] })),
      kinds,
      levels,
      favCount: countBy('fav', true),
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

  onLevel(e) {
    this.setData({ activeLevel: e.currentTarget.dataset.level })
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

  onNote() {
    const d = this.data
    wx.showModal({
      title: '这一页的数据从哪来',
      content: '收录 ' + d.totals.total + ' 座（新本 ' + d.totals.newDungeons + ' · 经典本 ' + d.totals.classicDungeons
        + ' · 团本 ' + d.totals.raids + '）。'
        + (d.routeMissing ? '路线没实测的有 ' + d.routeMissing + ' 座，本页不画路线。' : '')
        + '\n\n' + d.disclaimer
        + '\n\n最近核对：' + (d.factLatest || '未记录')
        + '\n列表数据来源：' + d.sourceText
        + (d.buildId ? '\n线上当前批次：' + d.buildId + (d.dataFrom === 'snapshot' || d.dataFrom === 'none' ? '（这一批没取到或没通过校验，所以下面是主包快照）' : '') : '\n线上当前批次：还没取到')
        + '\n缺数据的字段显示「待实测」，不机翻、不编造。',
      showCancel: false
    })
  },

  onShareAppMessage() {
    return { title: '无限服副本随手查：' + this.data.totals.total + ' 座的等级、首领与掉落', path: '/pages/dungeons/index' }
  }
})

function decorate(item) {
  const range = item.levelRange || ''
  const official = item.levelRangeOfficial || ''
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
    level: item.level || 'L3',
    levelName: service.levelName(item.level),
    rangeText: range || '等级待实测',
    officialNote: official && official !== range ? '官方英文页：' + official : '',
    faction: item.faction || '',
    zoneCn: item.zoneCn || '',
    bossText: item.bossCount > 0 ? item.bossCount + ' 个首领' : '首领没有记录',
    dropText: item.dropCount > 0 ? '掉落 ' + item.dropCount + ' 条' : '掉落没有记录',
    routeText: item.hasRoute ? '' : '路线未实测',
    fav: false
  }
}
