const oss = require('../../services/oss-manifest')
const features = require('../../services/features')
const roll = require('../../services/name-roll')
const NAMES_SNAPSHOT = require('../../data/forever-names-snapshot')

/* 角色起名（2026-11-03 站主："取名功能先选择职业，点击生成，要有随机滚动效果，
   展示一条名字，并且可以编辑，下方是复制按钮"）
   ------------------------------------------------------------------
   数据真源 wow-forever-web/app/data/name-generator.json（站主提供 1400 条创意名），
   分发层照宏命令同一套形制：names/index.json + names/set/{classId}.json 九片。
   主包带一份离线小池（每专精 5 条），断网也能摇，界面会明说摇的是本机那份。

   三条界线（照宏命令页的口径）：
   ① 只读 + 复制：编辑只是改输入框里的字，不回写词库、不做收藏、不做分享名字；
   ② 免费、零 UGC、不查占用——游戏收不收这个名字，以创建角色时的判定为准，页面不承诺；
   ③ 随机滚动是纯前端动画（快速换字逐步减速），不发请求、不装老虎机音效。 */

const FLAG = 'namer'
/* 滚动的节奏表（毫秒）：前段快后段慢，最后一步落定。纯 setTimeout 链，
   onHide/onUnload 时整链作废，不往已卸载的页面上 setData。 */
const ROLL_STEPS = [60, 60, 60, 60, 60, 70, 70, 90, 90, 120, 120, 160]

Page({
  data: {
    locked: false,
    lockName: '',
    loaded: false,
    offline: false,
    requiresUpdate: false,
    unavailable: false,
    errText: '',
    classes: [],
    cls: '',
    clsName: '',
    poolText: '',
    name: '',
    rolling: false
  },

  onLoad(query) {
    this.want = (query && query.c) || ''
    this.index = null
    this.shards = {}
    this.batch = null
    this.start()
  },

  onUnload() { this.stopRoll() },
  onHide() { this.stopRoll() },

  goHome() { wx.switchTab({ url: '/pages/home/index' }) },

  start() {
    return features.load(true).then(() => {
      if (!features.isOn(FLAG)) {
        const f = features.describe(FLAG) || {}
        this.setData({ locked: true, lockName: f.name || '角色起名' })
        return null
      }
      return oss.loadKey('nameGenerator', { fallback: NAMES_SNAPSHOT }).then((r) => {
        const d = r.data
        if (!d || !Array.isArray(d.classes) || !d.classes.length) {
          this.setData({ loaded: true, unavailable: true, errText: (r.error && r.error.message) || '起名词库没取到' })
          return null
        }
        this.batch = r.batch
        this.index = d
        this.setData({
          locked: false,
          loaded: true,
          offline: r.source !== 'live',
          requiresUpdate: !!r.requiresUpdate,
          classes: d.classes.map((c) => ({
            classId: c.classId,
            className: c.className,
            iconUrl: oss.iconUrl(r.batch, c.iconKey)
          }))
        })
        /* 带参进来（分享/最近用过）就预选那个职业；没带就等玩家自己点 */
        const want = this.want && d.classes.some((c) => c.classId === this.want) ? this.want : ''
        if (want) this.pickClassId(want)
        return null
      })
    }).catch((e) => {
      this.setData({ loaded: true, unavailable: true, errText: ((e && (e.stack || e.message)) || String(e)).slice(0, 300) })
    })
  },

  /* 选职业 → 取这一职业那一片（点过就缓存，同批片不可变）。
     离线兜底：快照里同一职业那一格（每专精只有 5 条的小池）。 */
  pickClassId(classId) {
    if (this.data.rolling) this.stopRoll()
    const entry = (this.index.classes || []).filter((c) => c.classId === classId)[0]
    if (!entry) return
    this.setData({ cls: classId, clsName: entry.className, name: '', poolText: '' })
    if (this.shards[classId]) { this.afterShard(this.shards[classId]); return }
    const snapCls = (NAMES_SNAPSHOT.classes || []).filter((c) => c.classId === classId)[0] || null
    oss.loadNamesClass(entry, this.batch, snapCls).then((r) => {
      const d = r.data
      if (!d || d.classId !== classId || !Array.isArray(d.talents) || !d.talents.length) {
        this.setData({ poolText: '', errText: (r.error && r.error.message) || '这一职业的名单没取到' })
        return
      }
      this.shards[classId] = d
      if (this.data.cls !== classId) return   /* 迟到的那一片不许盖掉后来选中的职业 */
      this.afterShard(d)
    })
  },

  afterShard(shard) {
    const pool = roll.poolOf(shard)
    this.pool = pool
    this.setData({
      poolText: '这一职业 ' + pool.length + ' 个候选，三系混着摇' +
        (this.data.offline ? '（现在摇的是机子里存的小份）' : '')
    })
  },

  pickClass(e) { this.pickClassId(e.currentTarget.dataset.id) },

  /* 生成：整条滚动链。每步从池里随手拿一条刷上去，节奏表越走越慢，
     最后一步落定一条（与上一步不同名）。连点无效（rolling 时按钮已禁）。 */
  roll() {
    if (this.data.rolling) return
    if (!this.data.cls || !this.pool || !this.pool.length) {
      wx.showToast({ title: '先在上面点一个职业', icon: 'none' })
      return
    }
    this.stopRoll()
    const pool = this.pool
    let i = 0
    this.setData({ rolling: true })
    const step = () => {
      const last = ROLL_STEPS[i] === undefined
      const next = roll.pick(pool, Math.random, this.data.name)
      this.setData({ name: next })
      if (last) {
        this.rolling = null
        this.setData({ rolling: false })
        return
      }
      this.rolling = setTimeout(step, ROLL_STEPS[i])
      i += 1
    }
    step()
  },

  stopRoll() {
    if (this.rolling) { clearTimeout(this.rolling); this.rolling = null }
    if (this.data.rolling) this.setData({ rolling: false })
  },

  onEdit(e) { this.setData({ name: (e.detail && e.detail.value) || '' }) },

  copyName() {
    const n = String(this.data.name || '').trim()
    if (!n) { wx.showToast({ title: '还没有名字可复制', icon: 'none' }); return }
    wx.setClipboardData({
      data: n,
      success: () => wx.showToast({ title: '已复制，创建角色时粘贴就行', icon: 'none', duration: 2200 })
    })
  },

  noop() {},

  shareNote() {
    return { title: '角色起名', path: '/pages/namer/index' }
  },

  onShareAppMessage() {
    return {
      title: '角色起名 · 摇一个有意思的',
      path: '/pages/namer/index' + (this.data.cls ? '?c=' + this.data.cls : '')
    }
  },

  /* 朋友圈（2026-11-03 站主要求全站可分享）：query 与 onShareAppMessage 的 path 参数一致 */
  onShareTimeline() {
    return { title: '角色起名 · 摇一个有意思的', query: this.data.cls ? 'c=' + this.data.cls : '' }
  }
})
