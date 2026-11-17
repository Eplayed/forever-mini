const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')
const adventure = require('../../services/adventure')

/* 配装页（2026-10-26 站主："根据 web 页面的 BIS 页面，在小程序中添加 BIS 页面"）
   数据来自分发层的三份配装产物：索引（38 套）+ 共享物品表（830 件）+ 每套一片。
   中间那一栏到 2026-11-02 已经换过三种形态，这段是为了下次别再换回去：
   ① 按种族的 2D 底图（2026-10-30）：底图表 data/bis-posters.js 的键是「职业|阵营」、
     值却是按种族渲的猎人那身，法师/牧师看到的是猎人装备，撞红线"不得用同职业另一套冒充当前套"，2026-11-01 撤；
   ② 真实 3D（2026-11-01 直接挂进这一栏）：站主 2026-11-02 说小程序不要 3D 了，
     组件、取模型契约（services/bis-model.js）与相机那套一起删掉——xr-frame 在这台模拟器里起不来，
     画面只能靠真机验，留着一套没人消费的链路下次还会被当成"照旧"接回去；
   ③ 逐件静态图（2026-11-02 站主："BIS 配装页装备展示全部替换成样图这样的，背景透明，根据职业装备来"）：
     一套一阵营一张透明底 PNG，地址由分发层桥表 posterLink 给（<setId>|<阵营> → 带内容哈希的文件名）。
     原来跑在客户端的三道闸搬到了构建时（tools/oss-release.js）：来源件不在 B1 索引、位置没 PASS、
     图记录的模型哈希与索引不符、名单逐格没对上、文件字节或哈希与清单不符——任一过不了就不进桥表。
     页面拿不到地址就只显示"这一格没有可显示的图"，不拿任何别的图填这一格。
   页头那三句（口径句 / 来源与核对日 / L1 留档）2026-11-01 起从界面撤下，数据层与溯源页一条没删。
   仍然照旧的三条：名字/品质/装等/属性行/图标全来自本站物品库；两家名单只并列不裁决；
   属性合计只加装备给的行。这一页没有打包快照（配装表 118 KB，主包只剩 6 KB 余量），
   离线时明确说"要联网才看得到"，不拿半截数据糊玩家。 */

const SUM_KEYS = ['力量', '敏捷', '耐力', '智力', '精神', '护甲'];
const POSTER_NONE = '这一格没有可显示的图';

Page({
  data: {
    loaded: false,
    offline: false,
    needOnline: false,
    sourceText: '',
    requiresUpdate: false,
    unavailable: false,
    errText: '',
    meta: null,
    sourceHost: '',
    classes: [],
    cls: '',
    setList: [],
    setId: '',
    fac: 'alliance',
    facCn: '联盟',
    set: null,
    rows: [],
    savedTargets: {},
    picking: false,
    selected: {},
    selectedCount: 0,
    sum: [],
    sumNote: '',
    enchants: [],
    consumables: [],
    /* 中间这一栏只有"这一套穿这一身"那一张图（2026-11-02 起）。桥表里没有这一格时
       posterSrc 一直为空，格子里显示 posterText，下面那行说清原因——不拿任何图去填。 */
    posterSrc: '',
    posterRequest: 0,
    posterState: 'none',
    posterText: POSTER_NONE,
    posterErr: '',
    slot: null,
    slotRows: [],
    slotHead: '',
    slotTheirs: null,
    itemSetCats: [],
    itemSetCat: 'new',
    filteredItemSets: [],
    activeItemSetId: '',
    activeItemSet: null
  },

  onLoad(query) {
    this.want = (query && query.c) || ''
    this.draft = new Map()
    this.fromList = !!(query && query.pick === '1')
    if (this.fromList) this.setData({ picking: true })
    this.start()
  },

  onShow() {
    this.syncGear()
  },

  syncGear() {
    const gear = adventure.read().gear
    if (this.savedGear === gear) return
    this.savedGear = gear
    const savedTargets = {}
    Object.keys(gear).forEach((id) => { savedTargets[id] = true })
    this.setData({ savedTargets })
  },

  saveTarget(e) {
    const id = String(e.currentTarget.dataset.id || '')
    if (adventure.read().gear[id]) {
      if (!this.data.picking) wx.navigateTo({ url: '/pages/adventure/index' })
      return
    }
    const item = (this.data.slotRows || []).find((r) => String(r.item) === id)
      || (this.data.rows || []).find((r) => String(r.item) === id)
      || (((this.data.activeItemSet && this.data.activeItemSet.pieces) || []).find((r) => String(r.item) === id))
    if (!item) return
    const target = { id, name: item.name, quality: item.q, dungeonId: item.go, source: item.src }
    if (!this.data.picking) {
      if (adventure.addGear(target)) this.syncGear()
      return
    }
    const chosen = !this.draft.has(id)
    if (chosen) this.draft.set(id, target)
    else this.draft.delete(id)
    const selected = Object.fromEntries(Array.from(this.draft.keys(), (key) => [key, true]))
    this.setData({ selected, selectedCount: this.draft.size })
  },

  beginPick() {
    this.setData({ picking: true })
    this.goEquipment()
  },

  cancelPick() {
    this.draft.clear()
    this.setData({ picking: false, selected: {}, selectedCount: 0 })
  },

  saveSelection() {
    if (!this.draft.size) return
    const count = adventure.addGearBatch(Array.from(this.draft.values()))
    if (count === null) return
    this.cancelPick()
    this.syncGear()
    wx.showToast({ title: '已加入 ' + count + ' 件装备', icon: 'none' })
    if (this.fromList && getCurrentPages().length > 1) wx.navigateBack()
  },

  goEquipment() {
    wx.pageScrollTo({ selector: '#bis-equipment', duration: 240, offsetTop: -12 })
  },

  goItemSets() {
    wx.pageScrollTo({ selector: '#bis-item-sets', duration: 240, offsetTop: -12 })
  },

  addItemSetToAdventure() {
    const cur = this.data.activeItemSet
    if (!cur || !cur.pieces || !cur.pieces.length) return
    const list = cur.pieces
      .filter((r) => r.item && !r.missing)
      .map((r) => ({ id: String(r.item), name: r.name, quality: r.q, dungeonId: r.go, source: r.src }))
    if (!list.length) return
    const count = adventure.addGearBatch(list)
    if (count === null) return
    this.syncGear()
    wx.showToast({ title: count ? ('已加入 ' + count + ' 件套装部件') : '本套部件已在清单中', icon: 'none' })
  },

  onPullDownRefresh() {
    this.start().then(() => wx.stopPullDownRefresh())
  },

  /* 微信分享（2026-11-03 站主要求全站可分享）：带当前职业，接收方打开就是同一身配装。
     阵营不带（页面默认联盟起步，接收方自己切）。 */
  onShareAppMessage() {
    return {
      title: 'BIS配装 · 30 级这一身穿什么',
      path: '/pages/bis/index' + (this.data.cls ? '?c=' + this.data.cls : '')
    }
  },

  onShareTimeline() {
    return { title: 'BIS配装 · 30 级这一身穿什么', query: this.data.cls ? 'c=' + this.data.cls : '' }
  },

  start() {
    const request = this.startRequest = (this.startRequest || 0) + 1
    this.setData({ unavailable: false, errText: '' })
    return oss.loadPointer().then((pointer) => {
      return oss.loadKey('bisIndex', { pointer }).then((ri) => {
        if (this.startRequest !== request) return
        this.setData({ sourceText: oss.sourceLabel(ri), offline: ri.source !== 'live', requiresUpdate: !!ri.requiresUpdate })
        if (ri.requiresUpdate) return
        if (!ri.data || !ri.data.sets || !ri.data.sets.length) {
          this.setData({ loaded: true, unavailable: true, errText: (ri.error && ri.error.message) || '' })
          return null
        }
        return oss.loadKey('bisItems', { pointer }).then((rt) => {
          if (this.startRequest !== request) return
          if (!rt.data || !Array.isArray(rt.data.items)) {
            this.setData({ loaded: true, unavailable: true })
            return
          }
          this.batch = ri.batch
          this.index = ri.data
          const items = {}
          const stOf = {}
          /* 结构不对时给空表而不是白屏：这一片 830 行，崩一次玩家看到的是整页空白。
             （2026-10-26 写这一页时确实撞到过一次"items 不是数组"，原因没查到底，先留这道闸） */
          rt.data.items.forEach((row) => {
            const k = String(row[0])
            items[k] = {
              id: row[0], name: row[1], q: row[2], ilvl: row[3],
              iconUrl: oss.iconUrl(this.batch, row[4])
            }
            stOf[k] = row[5] || []
          })
          this.items = items
          this.stOf = stOf
          this.initItemSets(ri.data.itemSets || [])
          this.setData({
            loaded: true,
            meta: ri.data.meta,
            sourceHost: hostOf(ri.data.meta && ri.data.meta.source),
            classes: (ri.data.classes || []).map((c) => ({
              cls: c.cls, clsCn: c.clsCn, n: (c.sets || []).length,
              iconUrl: oss.iconUrl(this.batch, c.iconKey)
            })),
            needOnline: rt.source !== 'live' || ri.source !== 'live'
          })
          const want = this.want && (ri.data.classes || []).some((c) => c.cls === this.want)
            ? this.want : ((ri.data.classes || [])[0] || {}).cls
          return this.pickClassId(want, true)
        })
      })
    }).catch((e) => {
      if (this.startRequest === request) this.setData({ loaded: true, unavailable: true })
    })
  },

  pickClass(e) { this.pickClassId(e.currentTarget.dataset.cls, true) },

  pickClassId(cls, resetSet) {
    const idx = this.index
    if (!idx) return
    const c = (idx.classes || []).filter((x) => x.cls === cls)[0] || idx.classes[0]
    const ids = (c || {}).sets || []
    this.setData({
      cls: c.cls,
      setList: ids.map((id) => {
        const s = idx.sets.filter((x) => x.id === id)[0] || {}
        return { id, mode: s.mode, label: s.mode || id }
      }),
      setId: resetSet ? (ids[0] || '') : this.data.setId
    })
    return this.loadSet()
  },

  pickSet(e) {
    this.setData({ setId: e.currentTarget.dataset.id, slot: null })
    this.loadSet()
  },

  pickFac(e) {
    const f = e.currentTarget.dataset.fac
    if (f === this.data.fac) return
    /* 换阵营取的是另一件登记：render() 会重新指一次图，旧的 src 同时作废，
       不许在飞的那一张回来盖掉现在选的这一套（指图前会核 _posterKey） */
    this.clearPoster()
    this.setData({ fac: f, facCn: f === 'horde' ? '部落' : '联盟', slot: null })
    this.render()
  },

  loadSet() {
    const entry = (this.index.sets || []).filter((x) => x.id === this.data.setId)[0]
    if (!entry) { this.setData({ set: null, rows: [] }); return Promise.resolve() }
    /* 切职业与切套装都经过这里：先把上一套的图摘掉，否则名单还没到、画面上还是那一身旧的 */
    this.clearPoster()
    const request = this.setRequest = (this.setRequest || 0) + 1
    this.set = null
    this.setData({ set: null, rows: [], errText: '', slot: null })
    return oss.loadBisSet(entry, this.batch).then((r) => {
      if (this.setRequest !== request) return
      if (!r.data || r.data.kind !== 'bis-set') {
        this.setData({ set: null, errText: (r.error && r.error.message) || '这一套没取到' })
        return null
      }
      this.set = r.data
      this.render()
      return r
    }).catch(() => {
      if (this.setRequest === request) this.setData({ set: null, errText: '这一套没取到' })
    })
  },

  /* 索引里的部位键桥（slotKeys / slotSiblings）算出一格的备选：
     桥表由分发层随索引下发，两端读同一份，不许页面各自抄一遍 */
  altsFor(label) {
    const idx = this.index || {}
    const set = this.set
    if (!set) return []
    const all = (set.byFac[this.data.fac] || {}).alts || {}
    const keys = (idx.slotSiblings || {})[label] || [keyOf(idx.slotKeys || {}, label)]
    for (let i = 0; i < keys.length; i += 1) {
      if ((all[keys[i]] || []).length) return all[keys[i]]
    }
    return []
  },

  render() {
    const set = this.set
    if (!set) return
    const fac = this.data.fac
    const one = set.byFac[fac] || {}
    const src = (set.src || {})[fac] || {}
    /* 出处跳转桥表随索引下发（分发层现算，页面不解析出处文字）：
       只有"这一行出处就写着某座副本"的才给目标，其余保持纯文字不可点。 */
    const link = (this.index || {}).dropLink || {}
    const linkOf = (id) => {
      const v = link[String(id)]
      return v && v.length ? v[0] : ''
    }
    const rows = (one.doll || []).map((c) => {
      const it = this.items[String(c[2])] || {}
      const alts = this.altsFor(c[0])
      return {
        slot: c[0], cell: c[1], item: c[2],
        slotLabel: c[0] + (c[1] > 1 ? ' · ' + c[1] : ''),
        name: it.name || null,
        missing: !it.name,
        q: it.q || 0,
        qText: quality.qualityName(it.q),
        ilvl: it.ilvl == null ? '' : it.ilvl,
        iconUrl: it.iconUrl || '',
        src: src[String(c[2])] || '',
        go: linkOf(c[2]),
        n: alts.length
      }
    })
    const sum = set.sum || {}
    const sumRows = SUM_KEYS.filter((k) => sum[fac] && sum[fac][k]).map((k) => ({ k, v: sum[fac][k] }))
    this.setData({
      rows,
      sum: sumRows,
      sumNote: set.sumNote || '',
      enchants: ((one.enchants) || []).map((x) => this.itemLine(x[0], x[1] + (x[2] == null ? '' : '（技能 ' + x[2] + '）'))),
      consumables: ((one.consumables) || []).map((x) => this.itemLine(x, '')),
      fetched: set.fetched,
      set: set
    })
    /* 指图不放在 setData 回调里：它只读 this.data.setId/fac 与内存里那份索引，不依赖视图，
       等回调会让"切完阵营这一拍"仍停在没有画面的空档（m01 抓到过一次）。 */
    this.showPoster()
  },

  itemLine(id, tail) {
    const it = (this.items || {})[String(id)] || {}
    const dl = ((this.index || {}).dropLink || {})[String(id)]
    return {
      item: id, name: it.name || ('#' + id), missing: !it.name,
      q: it.q || 0, ilvl: it.ilvl == null ? '' : it.ilvl,
      iconUrl: it.iconUrl || '', tail: tail || '',
      st: (this.stOf || {})[String(id)] || [],
      src: ((this.set.src || {})[this.data.fac] || {})[String(id)] || '',
      go: dl && dl.length ? dl[0] : ''
    }
  },

  /* 点出处那一行 → 副本详情页，并把这一件带过去高亮（from=bis 让那边的话说得准）。
     行上没有 go 的（任务奖励、专业制造这类）根本不渲染成可点，不拿"点了没反应"骗玩家。 */
  goDungeon(e) {
    const ds = e.currentTarget.dataset
    if (!ds.d) return
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + ds.d + '&drop=' + ds.item + '&from=bis' })
  },

  /* 弹层开着时不许页面在底下滚过去（图上没有可点的部位，这一格只是看） */
  noop() {},

  /* 指这一套、这一阵营那一张图。地址只从分发层桥表里取：
     桥表在构建时已经过五道闸（见文件头第三条），页面这一层不再判来源，
     但也绝不"猜"一个地址——键不在表里就是没有。 */
  showPoster(retry) {
    const setId = this.data.setId
    const fac = this.data.fac
    const key = setId + '|' + fac
    if (!retry && key === this._posterKey && this.data.posterSrc) return
    const rel = ((this.index || {}).posterLink || {})[key]
    if (!this.set || !((this.set.byFac || {})[fac] || {}).doll) {
      this._posterKey = ''
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE,
        posterErr: '配装暂未加载，请稍后再试。' })
      return
    }
    if (!rel) {
      this._posterKey = ''
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE,
        posterErr: '分发层没给这一套登记底图' })
      return
    }
    const url = oss.assetUrl(this.batch, rel)
    if (!url) {
      this._posterKey = ''
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE,
        posterErr: '预览图暂不可用。' })
      return
    }
    this._posterKey = key
    const posterRequest = this.data.posterRequest + 1
    this.setData({
      posterSrc: retry ? url + '?retry=' + Date.now() : url, posterRequest,
      posterState: 'loading', posterText: '正在取这一套的图', posterErr: ''
    })
  },

  clearPoster() {
    this._posterKey = ''
    if (this.data.posterSrc || this.data.posterState !== 'none') {
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE, posterErr: '' })
    }
  },

  isCurrentPoster(e) {
    return this._posterKey === this.data.setId + '|' + this.data.fac
      && (!e || Number(e.currentTarget.dataset.request) === this.data.posterRequest)
  },

  onPosterLoad(e) {
    if (!this.isCurrentPoster(e)) return
    this.setData({ posterState: 'ok', posterText: '', posterErr: '' })
  },

  onPosterError(e) {
    if (!this.isCurrentPoster(e)) return
    this.setData({
      posterSrc: '', posterState: 'bad', posterText: POSTER_NONE,
      posterErr: '这一张图取不到，请稍后重试'
    })
  },

  retryPoster() {
    this.showPoster(true)
  },

  openSlot(e) {
    const label = e.currentTarget.dataset.slot
    const cell = Number(e.currentTarget.dataset.cell || 1)
    const head = (this.data.rows || []).filter((r) => r.slot === label && r.cell === cell)[0] || {}
    const ids = this.altsFor(label)
    const altRow = ((this.set.alt || {})[this.data.fac] || [])
      .filter((x) => x[0] === label && x[1] === cell)[0]
    /* 第二家在这一格列的那一件：只带"是谁列的"这一层，不给一致/分歧的判词（站主 2026-11-02）。
       比较结果仍在数据分片里（alt[].state），界面不显示不等于数据删掉。 */
    let theirs = null
    if (altRow) {
      const t = (this.items || {})[String(altRow[2])] || {}
      theirs = { shown: altRow[2] != null,
        name: t.name || (altRow[2] == null ? '' : '#' + altRow[2]), q: t.q || 0,
        ilvl: t.ilvl == null ? '' : t.ilvl, iconUrl: t.iconUrl || '',
        unknown: altRow[2] != null && !t.name }
    } else {
      theirs = { shown: false }
    }
    this.setData({
      slot: label + '·' + cell,
      slotHead: (this.set.clsCn || '') + ' · ' + (this.set.mode || '') + ' · ' + this.data.facCn + ' · ' + label,
      slotTheirs: theirs,
      slotRows: ids.map((id) => this.itemLine(id, ''))
    })
  },

  initItemSets(rawSets) {
    this.itemSets = rawSets || []
    if (!this.itemSets.length) {
      this.setData({ itemSetCats: [], filteredItemSets: [], activeItemSetId: '', activeItemSet: null })
      return
    }
    const CATS = [
      { key: 'new', label: '无限新套装' },
      { key: 't0', label: '52级职业T0' },
      { key: 'endgame', label: '满级副本套' },
      { key: 'craft', label: '练级与制造套' },
      { key: 'all', label: '全部' }
    ]
    const cats = CATS.map((c) => ({
      key: c.key,
      label: c.label,
      n: c.key === 'all' ? this.itemSets.length : this.itemSets.filter((x) => x.cat === c.key).length
    })).filter((c) => c.n > 0)
    const defCat = (cats[0] && cats[0].key) || 'all'
    this.setData({ itemSetCats: cats })
    this.applyItemSetCat(defCat)
  },

  pickItemSetCat(e) {
    const k = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.cat) || '')
    if (k) this.applyItemSetCat(k)
  },

  applyItemSetCat(cat) {
    const all = this.itemSets || []
    const list = (cat === 'all' ? all : all.filter((x) => x.cat === cat)).map((s) => ({
      id: s.id,
      name: s.name,
      level: s.level,
      clsCn: s.clsCn,
      isNew: !!s.isNew,
      count: (s.pieces || []).length
    }))
    const firstId = (list[0] && list[0].id) || ''
    this.setData({ itemSetCat: cat, filteredItemSets: list, activeItemSetId: firstId })
    this.renderItemSet(firstId)
  },

  pickItemSet(e) {
    const id = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.id) || '')
    if (!id) return
    this.setData({ activeItemSetId: id })
    this.renderItemSet(id)
  },

  renderItemSet(id) {
    const s = (this.itemSets || []).filter((x) => x.id === id)[0]
    if (!s) {
      this.setData({ activeItemSet: null })
      return
    }
    const link = (this.index || {}).dropLink || {}
    const linkOf = (iid) => {
      const v = link[String(iid)]
      return v && v.length ? v[0] : ''
    }
    const pieces = (s.pieces || []).map((p) => {
      const iid = p[0]
      const slot = p[1] || ''
      const src = p[2] || ''
      const it = (this.items || {})[String(iid)] || {}
      return {
        item: iid,
        slot: slot,
        name: it.name || ('#' + iid),
        missing: !it.name,
        q: it.q || 0,
        qText: quality.qualityName(it.q),
        ilvl: it.ilvl == null ? '' : it.ilvl,
        iconUrl: it.iconUrl || '',
        st: (this.stOf || {})[String(iid)] || [],
        src: src,
        go: linkOf(iid)
      }
    })
    const sum = s.sum || {}
    const sumRows = SUM_KEYS.filter((k) => sum[k]).map((k) => ({ k: k, v: sum[k] }))
    this.setData({
      activeItemSet: {
        id: s.id,
        name: s.name,
        level: s.level,
        catCn: s.catCn,
        clsCn: s.clsCn,
        isNew: !!s.isNew,
        sumRows: sumRows,
        pieces: pieces
      }
    })
  },

  closeSlot() { this.setData({ slot: null, slotRows: [], slotTheirs: null }) }
})

function keyOf(map, label) {
  const ks = Object.keys(map)
  for (let i = 0; i < ks.length; i += 1) { if (map[ks[i]] === label) return ks[i] }
  return label
}
function hostOf(u) {
  const s = String(u || '')
  const m = /https?:\/\/([^/]+)/.exec(s)
  return m ? m[1] : s
}
