const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')

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
    sum: [],
    sumNote: '',
    enchants: [],
    consumables: [],
    /* 中间这一栏只有"这一套穿这一身"那一张图（2026-11-02 起）。桥表里没有这一格时
       posterSrc 一直为空，格子里显示 posterText，下面那行说清原因——不拿任何图去填。 */
    posterSrc: '',
    posterState: 'none',
    posterText: POSTER_NONE,
    posterErr: '',
    slot: null,
    slotRows: [],
    slotHead: '',
    slotTheirs: null
  },

  onLoad(query) {
    this.want = (query && query.c) || ''
    this.start()
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
    return service.loadMeta().then((r) => {
      this.batch = r.batch
      this.setData({
        sourceText: oss.sourceLabel(r),
        offline: r.source !== 'live',
        requiresUpdate: !!r.requiresUpdate
      })
      if (r.requiresUpdate) return null
      return oss.loadKey('bisIndex').then((ri) => {
        if (!ri.data || !ri.data.sets || !ri.data.sets.length) {
          this.setData({ loaded: true, unavailable: true, errText: (ri.error && ri.error.message) || '' })
          return null
        }
        this.index = ri.data
        return oss.loadKey('bisItems').then((rt) => {
          const items = {}
          const stOf = {}
          /* 结构不对时给空表而不是白屏：这一片 830 行，崩一次玩家看到的是整页空白。
             （2026-10-26 写这一页时确实撞到过一次"items 不是数组"，原因没查到底，先留这道闸） */
          const raw = (rt.data || {}).items
          const list = Array.isArray(raw) ? raw : []
          list.forEach((row) => {
            const k = String(row[0])
            items[k] = {
              id: row[0], name: row[1], q: row[2], ilvl: row[3],
              iconUrl: oss.iconUrl(this.batch, row[4])
            }
            stOf[k] = row[5] || []
          })
          this.items = items
          this.stOf = stOf
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
          this.pickClassId(want, true)
        })
      })
    }).catch((e) => {
      this.setData({ loaded: true, unavailable: true, errText: ((e && (e.stack || e.message)) || String(e)).slice(0, 300) })
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
    this.loadSet()
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
    return oss.loadBisSet(entry, this.batch).then((r) => {
      if (!r.data || r.data.kind !== 'bis-set') {
        this.setData({ set: null, errText: (r.error && r.error.message) || '这一套没取到' })
        return null
      }
      this.set = r.data
      this.render()
      return r
    }).catch((e) => { this.setData({ set: null, errText: e.message }) })
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
  showPoster() {
    const setId = this.data.setId
    const fac = this.data.fac
    const key = setId + '|' + fac
    const rel = ((this.index || {}).posterLink || {})[key]
    if (!this.set || !((this.set.byFac || {})[fac] || {}).doll) {
      this._posterKey = ''
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE,
        posterErr: '这一套的名单还没取到，先不指图' })
      return
    }
    if (!rel) {
      this._posterKey = ''
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE,
        posterErr: '分发层没给这一套（' + setId + ' · ' + this.data.facCn + '）登记过图：'
          + '要么这一件没从客户端导出、要么装备位置没核对通过、要么名单后来改过——不拿别的套装冒充' })
      return
    }
    const url = oss.assetUrl(this.batch, rel)
    if (!url) {
      this._posterKey = ''
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE,
        posterErr: '这张图的地址拼不出来（批次是 ' + ((this.batch || {}).buildId || '空') + '），先确认这批发过素材' })
      return
    }
    this._posterKey = key
    this.setData({ posterSrc: url, posterState: 'loading', posterText: '正在取这一套的图', posterErr: '' })
  },

  clearPoster() {
    this._posterKey = ''
    if (this.data.posterSrc || this.data.posterState !== 'none') {
      this.setData({ posterSrc: '', posterState: 'none', posterText: POSTER_NONE, posterErr: '' })
    }
  },

  onPosterLoad() {
    /* 迟到的那一张不许盖掉现在选的这套：键不对就当没看见 */
    if (this._posterKey !== this.data.setId + '|' + this.data.fac) return
    this.setData({ posterState: 'ok', posterText: '', posterErr: '' })
  },

  onPosterError() {
    const key = this.data.setId + '|' + this.data.fac
    if (this._posterKey !== key) return
    this.setData({
      posterSrc: '', posterState: 'bad', posterText: POSTER_NONE,
      posterErr: '这一张取不到（断网、没发过或对象不在这个批里）——上面那句"分发层登记过"仍然成立，'
        + '但今天这台设备上没拿到图'
    })
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
