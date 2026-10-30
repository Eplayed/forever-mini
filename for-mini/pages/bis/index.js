const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')
const bisModel = require('../../services/bis-model')

/* 配装页（2026-10-26 站主："根据 web 页面的 BIS 页面，在小程序中添加 BIS 页面…3D 模型先放模型占位"）
   数据来自分发层的三份配装产物：索引（38 套）+ 共享物品表（830 件）+ 每套一片。
   网页那一版的规则一条不改地跟过来：
   ① 口径那一句由索引下发，页面不自己改写（红线：不冒充官方结论、不做模拟计算）；
   ② 名字/品质/装等/属性行/图标全部来自本站物品库，名单只存"哪件在哪个部位"；
   ③ 两家名单只是并列摆出来，本站不裁决；
   ④ 属性合计只加装备给的行，不含职业与种族基础值、不含附魔与套装效果。
   这一页没有打包快照：配装表 118 KB，主包只剩 6 KB 余量，硬塞会把别的通道挤掉——
   所以离线时明确说"要联网才看得到"，不拿半截数据糊玩家。 */

const SUM_KEYS = ['力量', '敏捷', '耐力', '智力', '精神', '护甲'];
const CMP_CN = { same: '两家一致', diff: '两家分歧', none: '另一家没列' };

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
    stageUrl: '',
    /* 真实 3D 那一层：modelOn 才是挂了 xr-frame 组件的状态。
       进这一页时它必须是 false 且 modelSrc 为空——一个模型请求都不发（站主要的是点开才有）。 */
    modelOn: false,
    modelSrc: '',
    modelState: 'idle',
    modelText: '',
    modelErr: '',
    modelDetail: '',
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
    /* 换阵营＝换的那一件模型是另一条登记，先拆场景、再让在飞的回包作废，然后才重画 */
    this.teardownModel()
    this.setData({ fac: f, facCn: f === 'horde' ? '部落' : '联盟', slot: null })
    this.render()
  },

  loadSet() {
    const entry = (this.index.sets || []).filter((x) => x.id === this.data.setId)[0]
    if (!entry) { this.setData({ set: null, rows: [] }); return Promise.resolve() }
    /* 切职业与切套装都经过这里：先把上一套的 xr 场景拆掉，否则旧场景还在画旧的那一身 */
    this.teardownModel()
    this.setData({ stageUrl: '' })
    return oss.loadBisSet(entry, this.batch).then((r) => {
      if (!r.data || r.data.kind !== 'bis-set') {
        this.setData({ set: null, errText: (r.error && r.error.message) || '这一套没取到' })
        return null
      }
      this.set = r.data
      /* 中间那一栏默认是职业原画（与网页配装页同一张，走素材层）；占位人台叠在它上面 */
      this.setData({ stageUrl: oss.assetUrl(this.batch, r.data.art || null) })
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
    const altList = (set.alt || {})[fac] || []
    const rows = (one.doll || []).map((c) => {
      const it = this.items[String(c[2])] || {}
      const a = altList.filter((x) => x[0] === c[0] && x[1] === c[1])[0]
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
        n: alts.length,
        cmp: a ? (a[3] === 'same' ? 'same' : 'diff') : 'none'
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
  },

  itemLine(id, tail) {
    const it = (this.items || {})[String(id)] || {}
    return {
      item: id, name: it.name || ('#' + id), missing: !it.name,
      q: it.q || 0, ilvl: it.ilvl == null ? '' : it.ilvl,
      iconUrl: it.iconUrl || '', tail: tail || '',
      st: (this.stOf || {})[String(id)] || [],
      src: ((this.set.src || {})[this.data.fac] || {})[String(id)] || ''
    }
  },

  /* 弹层不许页面在底下滚过去；点人台上那一块等于点那个部位那一行 */
  noop() {},

  openSlot(e) {
    const label = e.currentTarget.dataset.slot
    const cell = Number(e.currentTarget.dataset.cell || 1)
    const head = (this.data.rows || []).filter((r) => r.slot === label && r.cell === cell)[0] || {}
    const ids = this.altsFor(label)
    const altRow = ((this.set.alt || {})[this.data.fac] || [])
      .filter((x) => x[0] === label && x[1] === cell)[0]
    let theirs = null
    if (altRow) {
      const t = (this.items || {})[String(altRow[2])] || {}
      theirs = { state: altRow[3] === 'same' ? 'same' : 'diff', cn: CMP_CN[altRow[3] === 'same' ? 'same' : 'diff'],
        name: t.name || (altRow[2] == null ? '' : '#' + altRow[2]), q: t.q || 0,
        ilvl: t.ilvl == null ? '' : t.ilvl, iconUrl: t.iconUrl || '',
        unknown: altRow[2] != null && !t.name }
    } else {
      theirs = { state: 'none', cn: CMP_CN.none }
    }
    this.setData({
      slot: label + '·' + cell,
      slotHead: (this.set.clsCn || '') + ' · ' + (this.set.mode || '') + ' · ' + this.data.facCn + ' · ' + label,
      slotTheirs: theirs,
      slotRows: ids.map((id) => this.itemLine(id, ''))
    })
  },

  closeSlot() { this.setData({ slot: null, slotRows: [], slotTheirs: null }) },

  /* 「查看 3D」：到这里才第一次碰模型清单。
     顺序是"拆旧场景 → 拿一个号 → 过三道闸 → 才给 src"，
     组件挂上（有 src）才会真的下载，所以点一次最多取一件。 */
  showModel() {
    this.teardownModel()
    const seq = this._seq
    const setId = this.data.setId
    const fac = this.data.fac
    const doll = ((this.set && this.set.byFac && this.set.byFac[fac]) || {}).doll || []
    if (!this.set || !doll.length) {
      this.setData({ modelOn: false, modelState: 'bad', modelText: '', modelErr: '这一套的名单还没取到，先不猜模型' })
      return
    }
    this.setData({
      modelOn: true, modelSrc: '', modelDetail: '',
      modelState: 'loading', modelText: '在对这一套的名单', modelErr: ''
    })
    bisModel.load(setId, fac, doll).then((r) => {
      /* 迟到的那一份不许盖掉后来选中的那一套：号不对就直接丢 */
      if (seq !== this._seq) return
      if (!r.ok) { this.modelFail(r.reason); return }
      this._modelEntry = r.entry
      this.setData({ modelSrc: r.url, modelText: '正在从远端取这一套的模型' })
    }).catch((e) => {
      if (seq !== this._seq) return
      this.modelFail(((e && e.message) || String(e)).slice(0, 200))
    })
  },

  hideModel() { this.teardownModel() },

  /* 拆场景 + 作废所有在飞的回包。切职业/切套/切阵营/离开这一页都先走这里。 */
  teardownModel() {
    this._seq = (this._seq || 0) + 1
    this._modelEntry = null
    if (this.data.modelOn || this.data.modelSrc) {
      this.setData({ modelOn: false, modelSrc: '', modelState: 'idle', modelText: '', modelErr: '', modelDetail: '' })
    }
  },

  modelFail(reason) {
    this.setData({
      modelOn: false, modelSrc: '', modelState: 'bad', modelText: '', modelDetail: '',
      modelErr: String(reason || '这一套的模型没取到').slice(0, 300)
    })
  },

  onModelStatus(e) {
    const d = (e && e.detail) || {}
    if (d.state === 'ok') {
      const en = this._modelEntry || {}
      this.setData({
        modelState: 'ok',
        modelText: '',
        modelDetail: '画面里 ' + d.meshes + ' 个网格、' + d.tex + ' 张贴图（' + (en.raceId || '?') + ' · ' + (en.bodyType || '?') + '）'
      })
      return
    }
    if (d.state === 'loading') { this.setData({ modelText: d.text || '正在取模型' }); return }
    if (d.state === 'shown') {
      /* 资源 loaded 且没报错＝这一件已经在这台机器上画出来了（2026-10-30 真机对过：
         这种状态下人是带的、贴图是好的）。xr-frame 有时不把网格列表交出来，
         量不到只说明尺子不对——照样按"已显示"处理，但把数到的/没数到的分开写。 */
      this.setData({
        modelState: 'shown', modelText: '',
        modelDetail: '本站数到网格 ' + (d.meshes || 0) + ' 个、贴图 ' + (d.tex || 0) + ' 张'
          + '（xr-frame 没把清单交全时这一项会偏少，画面以你看到的为准）｜ '
          + String(d.detail || '').slice(0, 200)
      })
      return
    }
    this.modelFail((d.text || '模型没画出来') + (d.err ? '：' + d.err : ''))
  },

  onStageError() { this.setData({ stageUrl: '' }) },

  onUnload() { this.teardownModel() },

  copyUrl() {
    const u = ((this.index || {}).meta || {}).source
    if (!u) return
    wx.setClipboardData({ data: u, success: () => wx.showToast({ title: '来源地址已复制', icon: 'none' }) })
  }
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
