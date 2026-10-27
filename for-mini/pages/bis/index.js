const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')

/* 配装页（2026-10-26 站主："根据 web 页面的 BIS 页面，在小程序中添加 BIS 页面…3D 模型先放模型占位"）
   数据来自分发层的三份配装产物：索引（38 套）+ 共享物品表（830 件）+ 每套一片。
   网页那一版的规则一条不改地跟过来：
   ① 口径那一句由索引下发，页面不自己改写（红线：不冒充官方结论、不做模拟计算）；
   ② 名字/品质/装等/属性行/图标全部来自本站物品库，名单只存"哪件在哪个部位"；
   ③ 两家名单只是并列摆出来，本站不裁决；
   ④ 属性合计只加装备给的行，不含职业与种族基础值、不含附魔与套装效果。
   这一页没有打包快照：配装表 118 KB，主包只剩 6 KB 余量，硬塞会把别的通道挤掉——
   所以离线时明确说"要联网才看得到"，不拿半截数据糊玩家。 */

/* 占位人台：一件一块，颜色跟品质走。坐标是相对展示框的百分比。
   这是本站自己拼的示意图，不是游戏里的样子（界面上固定写这一句）。 */
const DOLL_LAYOUT = {
  '头部': [[43, 3, 14, 10, 1]],
  '项链': [[44, 14, 12, 5]],
  '肩部': [[29, 19, 42, 7]],
  '背部': [[22, 26, 7, 26]],
  '胸部': [[39, 26, 22, 20]],
  '手腕': [[25, 34, 8, 7]],
  '手': [[23, 45, 10, 9]],
  '腰部': [[39, 47, 22, 7]],
  '腿部': [[39, 55, 22, 24]],
  '脚': [[38, 80, 24, 8]],
  '主手': [[8, 24, 7, 54]],
  '副手': [[15, 26, 5, 40]],
  '副手：盾牌': [[15, 26, 6, 34]],
  '副手：手持物品': [[15, 26, 5, 40]],
  '双手武器': [[7, 22, 9, 62]],
  '远程': [[86, 26, 7, 40]],
  '戒指': [[21, 56, 6, 6], [28, 56, 6, 6]],
  '饰品': [[66, 44, 9, 9], [66, 55, 9, 9]]
};
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
    nodes: [],
    unmapped: [],
    live3d: false,
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
    this.setData({ fac: f, facCn: f === 'horde' ? '部落' : '联盟', slot: null })
    this.render()
  },

  loadSet() {
    const entry = (this.index.sets || []).filter((x) => x.id === this.data.setId)[0]
    if (!entry) { this.setData({ set: null, rows: [] }); return Promise.resolve() }
    this.setData({ stageUrl: '' })
    return oss.loadBisSet(entry, this.batch).then((r) => {
      if (!r.data || r.data.kind !== 'bis-set') {
        this.setData({ set: null, errText: (r.error && r.error.message) || '这一套没取到' })
        return null
      }
      this.set = r.data
      /* 中间那一栏默认是职业原画（与网页配装页同一张，走素材层）；占位人台叠在它上面 */
      this.setData({ stageUrl: oss.assetUrl(this.batch, r.data.art || null), live3d: false })
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
    /* 占位人台：一件一块；库里没有格子的部位照实列出来，不硬塞到别的块上冒充 */
    const used = {}
    const nodes = []
    const unmapped = []
    rows.forEach((r) => {
      const plan = DOLL_LAYOUT[r.slot]
      if (!plan) { unmapped.push(r.slotLabel); return }
      const pick = plan[Math.min(r.cell, plan.length) - 1] || plan[0]
      nodes.push({
        key: r.slot + '-' + r.cell, l: pick[0], t: pick[1], w: pick[2], h: pick[3],
        round: !!pick[4], q: r.q, label: r.slot.charAt(0), name: r.name || ('#' + r.item),
        slot: r.slot, cell: r.cell
      })
      used[r.slot] = 1
    })
    this.setData({
      rows,
      sum: sumRows,
      sumNote: set.sumNote || '',
      nodes,
      unmapped,
      unmappedText: unmapped.join('、'),
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

  toggle3d() {
    this.setData({ live3d: !this.data.live3d })
  },

  onStageError() { this.setData({ stageUrl: '' }) },

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
