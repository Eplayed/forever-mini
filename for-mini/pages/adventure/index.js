const adventure = require('../../services/adventure')
const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const dungeonIndex = require('../../data/forever-dungeon-snapshot')
const posterModel = require('../../services/share-poster-model')

const DUNGEONS = new Map(dungeonIndex.items.map((d) => [d.id, d.nameCn || d.nameEn || d.id]))
const PAGE_SIZE = 24
const PLAN_ROW_RPX = 104

Page({
  data: {
    plans: [],
    sorting: false,
    dragIndex: -1,
    dragTo: -1,
    dragY: 0,
    rowStep: 0,
    showDone: false,
    groups: [],
    more: false,
    pending: 0,
    posterOpen: false,
    posterSpec: null
  },

  onLoad() {
    this.limit = PAGE_SIZE
  },

  onShow() {
    this.render()
    this.loadSources()
  },

  onUnload() {
    this.closed = true
  },

  onPullDownRefresh() {
    this.loadSources(true).finally(() => wx.stopPullDownRefresh())
  },

  removePlan(e) {
    if (adventure.removePlan(e.currentTarget.dataset.id)) this.render()
  },

  toggleSort() {
    this.endDrag()
    this.setData({ sorting: !this.data.sorting })
  },

  startDrag(e) {
    const touch = e.touches[0]
    const { id, index } = e.currentTarget.dataset
    if (!touch || this.drag) return
    const width = wx.getWindowInfo ? wx.getWindowInfo().windowWidth : wx.getSystemInfoSync().windowWidth
    const step = PLAN_ROW_RPX * width / 750
    this.drag = { id, index, start: touch.clientY, step, last: 0 }
    this.setData({ dragIndex: index, dragTo: index, dragY: 0, rowStep: step })
  },

  dragPosition(touch) {
    const { index, start, step } = this.drag
    const max = this.data.plans.length - 1
    const y = Math.max(-index * step, Math.min((max - index) * step, touch.clientY - start))
    return { dragY: y, dragTo: index + Math.round(y / step) }
  },

  moveDrag(e) {
    if (!this.drag || !e.touches[0]) return
    const now = Date.now()
    if (now - this.drag.last < 16) return
    this.drag.last = now
    this.setData(this.dragPosition(e.touches[0]))
  },

  dropDrag(e) {
    if (!this.drag) return
    const target = e.changedTouches[0] ? this.dragPosition(e.changedTouches[0]).dragTo : this.data.dragTo
    adventure.movePlan(this.drag.id, target)
    this.endDrag()
    this.render()
  },

  endDrag() {
    if (!this.drag) return
    this.drag = null
    this.setData({ dragIndex: -1, dragTo: -1, dragY: 0 })
  },

  toggleDone() {
    this.limit = PAGE_SIZE
    this.setData({ showDone: !this.data.showDone })
    this.render()
  },

  showMore() {
    this.limit += PAGE_SIZE
    this.render()
  },

  loadSources(force) {
    if (this.sourceRequest) return this.sourceRequest
    if (!Object.keys(adventure.read().gear).length || (this.loot && !force)) return Promise.resolve()
    const loadLoot = service.loadLootIndex().then((result) => {
      if (this.closed || !result || !result.data) return
      this.loot = result.data
      this.batch = result.batch || this.batch
      this.sourceMode = result.source
      this.indexedIds = null
      this.indexTargets()
    }).catch(() => {})
    const loadBisIcons = (this.bisIcons && !force)
      ? Promise.resolve()
      : oss.loadKey('bisItems').then((res) => {
        if (this.closed || !res || !res.data || !Array.isArray(res.data.items)) return
        const batch = res.batch || this.batch || { env: oss.ACTIVE_ENV }
        this.batch = this.batch || batch
        const map = new Map()
        res.data.items.forEach((row) => {
          if (row && row[0] && row[4]) {
            map.set(String(row[0]), oss.iconUrl(batch, row[4]))
          }
        })
        this.bisIcons = map
      }).catch(() => {})
    this.sourceRequest = Promise.all([loadLoot, loadBisIcons]).then(() => {
      if (!this.closed) this.render()
    }).finally(() => { this.sourceRequest = null })
    return this.sourceRequest
  },

  indexTargets() {
    const gear = adventure.read().gear
    const ids = Object.keys(gear).sort().join(',')
    if (ids === this.indexedIds) return
    this.indexedIds = ids
    this.sources = new Map()
    this.lootIcons = new Map()
    const batch = this.batch || { env: oss.ACTIVE_ENV }
    const idAt = this.loot.cols.indexOf('itemId')
    const bossAt = this.loot.cols.indexOf('boss')
    const iconAt = this.loot.cols.indexOf('iconKey')
    for (const dungeon of this.loot.dungeons || []) {
      for (const row of dungeon.rows || []) {
        const id = String(row[idAt])
        if (!gear[id]) continue
        if (iconAt >= 0 && row[iconAt] && !this.lootIcons.has(id)) {
          this.lootIcons.set(id, oss.iconUrl(batch, row[iconAt]))
        }
        const matches = this.sources.get(id) || new Map()
        const source = matches.get(dungeon.id) || {
          id: dungeon.id, name: dungeon.nameCn || DUNGEONS.get(dungeon.id) || dungeon.id, bosses: []
        }
        const boss = (dungeon.bosses || [])[row[bossAt]]
        if (boss && !source.bosses.includes(boss)) source.bosses.push(boss)
        matches.set(dungeon.id, source)
        this.sources.set(id, matches)
      }
    }
  },

  render() {
    const { plans, gear } = adventure.read()
    const items = Object.values(gear)
    if (this.loot) this.indexTargets()
    const order = new Map(plans.map((plan, index) => [plan.id, index]))
    const rows = items.filter((item) => item.done === this.data.showDone).map((item) => {
      const matches = this.sources && this.sources.get(item.id)
      const primary = plans.find((plan) => matches ? matches.has(plan.id) : item.dungeonId === plan.id)
      return { item, key: primary ? primary.id : '', rank: primary ? order.get(primary.id) : plans.length }
    })
    rows.sort((a, b) => a.rank - b.rank)
    const groups = new Map()
    rows.slice(0, this.limit).forEach(({ item, key: plannedId }) => {
      const matched = this.sources && this.sources.get(item.id)
      const sources = matched ? Array.from(matched.values()).map((s) => ({
        id: s.id, label: s.name + (s.bosses.length ? ' · ' + s.bosses.join('、') : '')
      })) : []
      if (!sources.length && item.dungeonId) {
        const name = item.dungeon || DUNGEONS.get(item.dungeonId) || '副本'
        sources.push({ id: item.dungeonId, label: '已保存 · ' + name + (item.boss ? ' · ' + item.boss : '') })
      }
      const key = plannedId || (sources.length ? sources[0].id : '')
      const title = DUNGEONS.get(key) || item.dungeon || (key ? '其他副本' : '其他来源')
      if (!groups.has(key)) groups.set(key, { key, title, rows: [] })
      const resolvedIcon = item.iconUrl
        || (this.lootIcons && this.lootIcons.get(item.id))
        || (this.bisIcons && this.bisIcons.get(item.id))
        || ''
      groups.get(key).rows.push(Object.assign({}, item, {
        iconUrl: resolvedIcon,
        sources,
        sourceText: item.source || '副本掉落待核'
      }))
    })
    this.setData({
      plans,
      sorting: plans.length > 1 && this.data.sorting,
      groups: Array.from(groups.values()),
      more: rows.length > this.limit,
      pending: items.filter((item) => !item.done).length,
      cachedSources: this.sourceMode === 'cache'
    })
  },

  toggleGear(e) {
    const id = e.currentTarget.dataset.id
    const item = adventure.read().gear[id]
    if (item && adventure.setGearDone(id, !item.done)) {
      this.render()
      wx.showToast({ title: item.done ? '已恢复为想要' : '已标为获得', icon: 'none' })
    }
  },

  removeGear(e) {
    const id = e.currentTarget.dataset.id
    const item = adventure.read().gear[id]
    if (!item) return
    wx.showModal({
      title: '移除装备目标',
      content: item.name,
      confirmText: '移除',
      success: (r) => { if (r.confirm && adventure.removeGear(id)) this.render() }
    })
  },

  openDungeon(e) {
    const { id, item } = e.currentTarget.dataset
    if (!id) return
    const query = item ? '&drop=' + encodeURIComponent(item) + '&from=adventure' : '&tasks=1'
    wx.navigateTo({ url: adventure.dungeonUrl(id, query) })
  },

  browseDungeons() {
    wx.switchTab({ url: '/pages/dungeons/index' })
  },

  browseGear() {
    wx.navigateTo({ url: '/pages/bis/index?pick=1' })
  },

  getDungeonArtMap() {
    const batch = this.batch || { env: oss.ACTIVE_ENV }
    return posterModel.buildDungeonArtMap(dungeonIndex.items || [], (art) => oss.assetUrl(batch, art))
  },

  openAdventurePoster() {
    const launch = () => {
      if (this.closed) return
      const spec = posterModel.buildAdventurePoster(this.data.plans, this.data.groups, this.getDungeonArtMap())
      this.setData({ posterSpec: spec, posterOpen: true })
    }
    if (this.sourceRequest) {
      let fired = false
      const done = () => { if (!fired) { fired = true; launch() } }
      setTimeout(done, 800)
      this.sourceRequest.then(done, done)
      return
    }
    launch()
  },

  closeSharePoster() {
    this.setData({ posterOpen: false })
  },

  onShareAppMessage() {
    return { title: '我的冒险清单 · 跑本助手', path: '/pages/adventure/index' }
  },

  onShareTimeline() {
    return { title: '我的冒险清单 · 跑本助手' }
  }
})
