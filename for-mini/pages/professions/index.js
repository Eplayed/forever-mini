const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const features = require('../../services/features')

/* 专业与配方（2026-10-27 站主："下一步做小程序端的专业页面，根据 web 网页的专业页面"）
   对齐的是网页 app/src/pages/ProfessionsPage.vue，规则一条不改地跟过来：
   ① 分箱（技能橙点 1–75 / 76–150 / 151–225 / 226–300）、技能四档、来源那三行怎么拼，
      全部读分发层下发的 bands / skillKeys / cols，页面自己不抄一份（抄两份必然飘）；
   ② 数据里没写的就不显示：没标档位的那箱进"技能档位没标出来"，被源截断的处数用 vMore/dMore 补"等 N 处"；
   ③ 红线：只列名称与数量，不给掉率、不做冲级建议、不做性价比与强度评价——那句话由索引下发，页面不改写；
   ④ 空态那句话取自数据里的 note（比如野营"那一版还没能拆出条目"），不在代码里另编。
   这一页没有打包快照：单片最大 65.6 KB（制皮 511 条），主包只剩 6 KB 余量，硬塞会把别的通道挤掉——
   离线时明确说"要联网才取到"。
   入口由远程开关 professions 控制（services/features.js）：关着的时候这一屏直接拒绝取数，
   只说"这一页还没开放"，不摆空白格。 */

const FLAG = 'professions'
/* 一次 setData 只画这么多行：511 条整片塞进 data 会顶到 setData 的 1 MB 上限，
   而且手机滚动也吃不下一屏几千个节点。 */
const LIST_STEP = 60
const KIND_CN = { gather: '采集', craft: '制作' }

Page({
  data: {
    locked: false,
    lockName: '',
    loaded: false,
    offline: false,
    needOnline: false,
    sourceText: '',
    requiresUpdate: false,
    unavailable: false,
    errText: '',
    meta: null,
    headUrl: '',
    stats: null,
    chips: [],
    selId: '',
    sel: null,
    q: '',
    lv: '',
    onlyNew: false,
    nodeHead: '采集点',
    nodeRows: [],
    bands: [],
    totalRecipes: 0,
    shown: 0,
    rest: 0,
    loading: false,
    provText: '',
    srcHost: '',
    bandNote: ''
  },

  onLoad(query) {
    this.want = (query && query.p) || ''
    this.start()
  },

  onPullDownRefresh() {
    this.start().then(() => wx.stopPullDownRefresh())
  },

  /* 开关在前，取数在后：关着的页一次请求都不该发，也不该让玩家看到半屏空白 */
  start() {
    return features.load(true).then(() => {
      const f = features.describe(FLAG)
      if (!features.isOn(FLAG)) {
        this.setData({ locked: true, lockName: f.name || '', loaded: false })
        return null
      }
      this.setData({ locked: false })
      return this.fetch()
    })
  },

  fetch() {
    return service.loadMeta().then((r) => {
      this.batch = r.batch
      this.setData({
        sourceText: oss.sourceLabel(r),
        offline: r.source !== 'live',
        requiresUpdate: !!r.requiresUpdate,
        needOnline: r.source !== 'live' && r.source !== 'cache'
      })
      if (r.requiresUpdate) return null
      return oss.loadKey('professionsIndex').then((ri) => {
        const idx = ri.data
        if (!idx || !(idx.professions || []).length) {
          this.setData({ loaded: true, unavailable: true, errText: (ri.error && ri.error.message) || '' })
          return null
        }
        this.index = idx
        this.cols = idx.cols || {}
        this.items = null
        this.setData({
          loaded: true,
          meta: idx.meta,
          headUrl: oss.iconUrl(this.batch, idx.headIcon),
          stats: idx.counts,
          chips: (idx.professions || []).map((p) => ({
            id: p.id,
            nameCn: p.nameCn,
            n: (p.counts || {}).recipes || (p.counts || {}).nodes || 0,
            gather: p.kind === 'gather'
          })),
          srcHost: hostOf((idx.meta || {}).sources),
          bandNote: idx.bandNote || ''
        })
        const want = this.want
        const hit = (idx.professions || []).filter((p) => p.id === want)[0] || (idx.professions || [])[0]
        if (!hit) {
          this.setData({ unavailable: true, errText: '索引里一个专业都没有' })
          return null
        }
        return this.selectProf(hit.id)
      })
    })
  },

  pickProf(e) {
    const id = String(e.currentTarget.dataset.id || '')
    if (id === this.data.selId) return
    this.selectProf(id)
  },

  selectProf(id) {
    const entry = (this.index.professions || []).filter((p) => p.id === id)[0]
    if (!entry) return Promise.resolve(null)
    const prov = (entry.prov || [])[0] || {}
    this.setData({
      selId: id,
      sel: {
        nameCn: entry.nameCn,
        nameEn: entry.nameEn || '',
        kindCn: KIND_CN[entry.kind] || '',
        note: entry.note || '',
        unparsed: !!entry.unparsed,
        counts: entry.counts || {},
        level: entry.level || '',
        levelNote: entry.levelNote || ''
      },
      nodeHead: (this.index.nodeHeadLabels || {})[id] || '采集点',
      provText: prov.checkedAt ? prov.checkedAt : '',
      loading: true,
      q: '',
      lv: '',
      onlyNew: false,
      nodeRows: [],
      bands: [],
      shown: 0,
      rest: 0,
      totalRecipes: 0
    })
    /* 换专业先把上一片的解码结果清掉，并给这一轮排个号：
       筛选回调是 setData 的异步回调，可能在新的一片渲染完之后才落地，
       不挡就会拿旧专业的 0 条覆盖掉新专业刚画出来的表（2026-10-27 探针里真撞到过一次） */
    this.prof = null
    this.seq = (this.seq || 0) + 1
    if (!this.cols || !this.cols.recipe) {
      this.setData({ loading: false, unavailable: true, errText: '索引里没有列名，这一片没法解' })
      return Promise.resolve(null)
    }
    return oss.loadProfSet(entry, this.batch).then((rs) => {
      const s = rs.data
      if (!s) {
        this.setData({ loading: false, unavailable: true, errText: (rs.error && rs.error.message) || '' })
        return null
      }
      if (String(s.profId) !== String(entry.id)) {
        this.setData({ loading: false, unavailable: true, errText: '分片的专业编号对不上索引' })
        return null
      }
      this.prof = this.decode(s)
      this.applyFilter()
      return null
    })
  },

  /* 位置数组 → 界面用得上的形状。列名来自索引的 cols，页面按名字取列，
     分发层以后加列也不会把这一页顶歪（按位置写死才会）。 */
  decode(s) {
    const C = this.cols
    const icons = s.icons || []
    const url = (i) => (typeof i === 'number' && i >= 0 ? oss.iconUrl(this.batch, icons[i]) : '')
    const skIx = {}
    ;(C.sk || []).forEach((k, i) => { skIx[k] = i })
    const rc = C.recipe || []
    const at = (name) => rc.indexOf(name)
    const nc = C.node || []
    const bad = rc.length && s.recipes.some((r) => r.length !== rc.length)
    if (bad) {
      this.setData({ loading: false, unavailable: true, errText: '配方行的列数与索引的列名对不上' })
      return null
    }
    const recipes = s.recipes.map((r) => {
      const sk = r[at('sk')] || []
      const flat = r[at('mats')] || []
      const mats = []
      for (let i = 0; i + 1 < flat.length; i += 2) {
        const m = (s.mats || [])[flat[i]] || []
        mats.push({ key: String(m[0] || '') + '_' + i, name: m[0] || '', iconUrl: url(m[1]), count: flat[i + 1] })
      }
      const vend = (r[at('vend')] || []).map((i) => (s.vendors || [])[i] || ['', ''])
      const drops = (r[at('drops')] || []).map((i) => (s.drops || [])[i] || ['', ''])
      const srcCode = r[at('src')]
      return {
        itemId: r[at('itemId')],
        name: r[at('name')],
        q: r[at('q')] || 0,
        isNew: r[at('new')] === 1,
        iconUrl: url(r[at('icon')]),
        mats,
        matTotal: mats.reduce((a, m) => a + (m.count || 1), 0),
        orange: typeof sk[skIx.orange] === 'number' ? sk[skIx.orange] : null,
        skList: (this.index.skillKeys || []).map((k) => ({
          cn: k.cn, v: sk[skIx[k.k]], k: k.k
        })).filter((x) => typeof x.v === 'number'),
        source: srcCode >= 0 ? (s.sources || [])[srcCode] : '',
        vend, drops,
        xr: r[at('xr')] === 1,
        vMore: r[at('vMore')] || 0,
        dMore: r[at('dMore')] || 0
      }
    })
    const nodes = s.nodes.map((r) => {
      const sk = r[nc.indexOf('sk')]
      return {
        name: r[nc.indexOf('name')],
        iconUrl: url(r[nc.indexOf('icon')]),
        /* 草药点那 30 行"可得的就只有它自己"，再写一遍名字等于每行重复一次（实拍里一眼看出来）：
           与名字相同就不显示，那一行只留区域。搜材料名仍然命中（名字那一格本来就在搜） */
        yields: (function () {
          const ys = (r[nc.indexOf('yields')] || []).map(String)
          return ys.length === 1 && ys[0] === r[nc.indexOf('name')] ? '' : ys.join('、')
        })(),
        zone: r[nc.indexOf('zone')] || '',
        skList: (this.index.skillKeys || []).map((k) => ({
          cn: k.cn, v: (sk || [])[skIx[k.k]], k: k.k
        })).filter((x) => !!sk && typeof x.v === 'number')
      }
    })
    return { recipes, nodes }
  },

  onSearch(e) {
    this.setData({ q: e.detail.value || '' }, () => this.applyFilter())
  },

  onLevel(e) {
    this.setData({ lv: e.detail.value || '' }, () => this.applyFilter())
  },

  toggleNew() {
    this.setData({ onlyNew: !this.data.onlyNew }, () => this.applyFilter())
  },

  /* 三个筛选项都要真生效（站主抓到过"白放"的选项）：
     q 命中等级的橙点、q 命中材料名、只看无限新增、技能档位——每个都改结果数 */
  applyFilter() {
    const prof = this.prof
    if (!prof) return
    const kw = String(this.data.q || '').trim().toLowerCase()
    const lvNum = parseInt(this.data.lv, 10)
    const hasLv = !isNaN(lvNum)
    const onlyNew = this.data.onlyNew

    const recipes = prof.recipes.filter((x) => {
      if (onlyNew && !x.isNew) return false
      if (hasLv && !(typeof x.orange === 'number' && x.orange <= lvNum)) return false
      if (!kw) return true
      if (String(x.name || '').toLowerCase().indexOf(kw) >= 0) return true
      return x.mats.some((m) => String(m.name || '').toLowerCase().indexOf(kw) >= 0)
    })
    const nodes = prof.nodes.filter((x) => !kw
      || String(x.name || '').toLowerCase().indexOf(kw) >= 0
      || String(x.yields || '').toLowerCase().indexOf(kw) >= 0)

    /* 材料条的基准是当前这批里总量最大的一条：与网页同一算法，
       "要 20 个草"和"只要 1 个矿"得一眼看出不一样 */
    const maxMat = recipes.reduce((m, x) => Math.max(m, x.matTotal), 1)

    const bands = (this.index.bands || []).map((b) => ({
      label: b[2],
      lo: b[0],
      hi: b[1],
      items: recipes.filter((x) => typeof x.orange === 'number' && x.orange >= b[0] && x.orange <= b[1])
    }))
    const banded = {}
    bands.forEach((b) => b.items.forEach((x) => { banded[x.itemId] = 1 }))
    const rest = recipes.filter((x) => !banded[x.itemId])
    if (rest.length) bands.push({ label: '技能档位没标出来', lo: null, hi: null, items: rest })

    this.groups = bands.filter((b) => b.items.length)
    this.maxMat = maxMat
    this.filtered = recipes.length
    const seq = this.seq
    this.setData({
      nodeRows: nodes,
      totalRecipes: recipes.length,
      shown: 0,
      rest: recipes.length
    }, () => {
      if (seq !== this.seq || this.prof !== prof) return
      this.renderList()
    })
  },

  /* 一屏只画 LIST_STEP 行；箱头那一个数是这一箱的全部条数，不是已画出来的条数——
     不然"熟练 240 条"只显示 60 条时，玩家会以为剩下的是筛掉了 */
  renderList() {
    const seq = this.seq
    let budget = this.data.shown + LIST_STEP
    const out = []
    let used = 0
    this.groups.forEach((g) => {
      if (budget <= 0) {
        out.push({ label: g.label, count: g.items.length, rows: [], hidden: g.items.length })
        return
      }
      const take = g.items.slice(0, budget).map((x) => this.rowOf(x))
      budget -= take.length
      used += take.length
      out.push({
        label: g.label,
        count: g.items.length,
        rows: take,
        hidden: g.items.length - take.length
      })
    })
    this.setData({
      bands: out,
      shown: used,
      rest: this.filtered - used,
      loading: false
    }, () => {
      /* 这一批行画完之前用户又切了专业 / 又改了筛选：这次结果作废，让位给新的那一次 */
      if (seq !== this.seq) this.renderList()
    })
  },

  rowOf(x) {
    return {
      itemId: x.itemId,
      name: x.name,
      q: x.q,
      isNew: x.isNew,
      iconUrl: x.iconUrl,
      matPct: Math.max(6, Math.round(x.matTotal / this.maxMat * 100)),
      mats: x.mats,
      hasMats: x.mats.length > 0,
      skList: x.skList,
      srcLines: this.srcLines(x)
    }
  },

  /* "再画 60 行"：shown 由 renderList 自己算，这里只是再走一遍它 */
  loadMore() {
    if (this.data.rest <= 0) return
    this.renderList()
  },

  /* 来源那一格的三层信息，与网页 srcLines 同一算法（各来自不同资料，缺哪层就不写哪层）。
     掉率是红线，源里也没有，所以图纸掉落只写"从谁身上掉"，不写百分之几。 */
  srcLines(x) {
    const out = []
    if (x.source) out.push(x.source)
    const vs = x.vend || []
    if (vs.length) {
      out.push('商人：' + vs.slice(0, 2).map((v) => v[0] + (v[1] ? '（' + v[1] + '）' : '')).join('、')
        + (vs.length > 2 ? ' 等 ' + (vs.length + (x.vMore || 0)) + ' 处' : ''))
    }
    const ds = x.drops || []
    if (ds.length) {
      out.push('图纸掉落：' + ds.slice(0, 2).map((d) => d[0] + (d[1] ? '（' + d[1] + '）' : '')).join('、')
        + (ds.length > 2 ? ' 等 ' + (ds.length + (x.dMore || 0)) + ' 处' : ''))
    }
    return out
  },

  goHome() {
    wx.switchTab({ url: '/pages/home/index' })
  }
})

function hostOf(sources) {
  const first = (sources || [])[0] || {}
  return String(first.url || '').replace(/^https?:\/\//, '').replace(/\/.*$/, '')
}
