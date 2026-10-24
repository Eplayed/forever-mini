const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const countdown = require('../../services/countdown')
const DUNGEON_INDEX = require('../../data/forever-dungeon-snapshot')
const META_SNAPSHOT = require('../../data/forever-meta-snapshot')

/* 首页（2026-10-22 站主重排，四段从上到下）
   1) 开服倒计时：占顶部约 1/4 屏，正式服上线那一刻这块整块消失，不留"0 天"。
   2) 四个入口卡：副本 / 职业 / 掉落查询 / 指南。中英速查按站主指令从这里撤了
      （页面还在 app.json 里，但首页不再有入口——要不要一起下线是下一个待拍板项）。
   3) 职业格：九个职业一排铺开，超出的换行走 grid，不许出现横向滚动条（站主原话）。
      默认选中战士，点别的只是换下面的内容，不是跳页。
   4) 选中职业的可选种族 + 种族特长：图标和文字都要有，缺特长（天裔两条都是空的）
      就写"还没核到"，不猜、不拿别的种族凑。
   玩家面规矩不变：这一屏不出现条数、覆盖率、缺口清单、核对日期、批次号。 */
const FACTION = { alliance: '联盟', horde: '部落' }
const DEFAULT_CLASS = 'warrior'

Page({
  data: {
    loaded: false,
    offline: false,
    requiresUpdate: false,
    cd: null,
    /* 页面背景与四张卡的底图：地址由 meta.uiArt + 批次拼出来，取不到就是空串（版式回落纯色） */
    bgUrl: '',
    cardBg: { dungeons: '', classes: '', loots: '', guide: '' },
    classes: [],
    activeClass: '',
    activeName: '',
    races: [],
    raceNote: '',
    classEmpty: '',
    recent: []
  },

  onLoad() {
    /* 第一帧就用主包里的开服日期把倒计时点亮，不等网络：
       线上 meta 取回来若不一样，refresh 里会覆盖并重算。 */
    this.batch = null
    this.launch = META_SNAPSHOT.launch
    this.raceSource = []
    this.tick()
    this.startTimer()
    this.refresh()
    this.syncRecent()
  },

  onShow() {
    this.syncRecent()
    this.startTimer()
  },

  /* tab 页切走就停表：倒计秒是纯本地计算，别让首页在后台每秒 setData */
  onHide() {
    this.clearTimer()
  },

  onUnload() {
    this.clearTimer()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  /* 只到天，不跳秒：这张表存在的唯一理由是把"过了一天"这件事跟上，
     所以 60 秒看一次，而且天数没变就不 setData（首页不是秒表，不该有每秒的渲染负担）。 */
  startTimer() {
    if (this.timer || !this.data.cd) return
    this.timer = setInterval(() => this.tick(), 60000)
  },

  clearTimer() {
    if (!this.timer) return
    clearInterval(this.timer)
    this.timer = null
  },

  /* 开服后 state() 返回 on=false → 这块从界面上移除，表也一起停 */
  tick() {
    const s = countdown.state(Date.now(), this.launch)
    if (!s.on) {
      this.clearTimer()
      if (this.data.cd) this.setData({ cd: null })
      return
    }
    /* 只到天：天数没变就不重绘（60 秒一次的心跳不该变成另一个秒表） */
    if (this.data.cd && this.data.cd.d === s.d) return
    this.setData({ cd: s })
  },

  refresh() {
    return Promise.all([service.loadMeta(), service.loadClassIndex()]).then((list) => {
      const meta = list[0]
      const cls = list[1]
      const m = meta.data || {}
      this.disclaimer = m.disclaimer || ''
      if (m.launch && m.launch !== this.launch) {
        this.launch = m.launch
        this.tick()
      }
      this.batch = cls.batch || this.batch
      this.raceSource = (cls.data || {}).races || []
      /* 底图走 meta 下发的那份清单（真源在 wow-forever-web/app/data/ui-art.json），页面不各自抄路径；
         批次取 meta 的（拿不到再退到职业索引的），断网没有批次时 assetUrl 返回空 → 版式回落纯色 */
      const mBatch = meta.batch || cls.batch
      const ui = m.uiArt || {}
      this.setData({
        bgUrl: oss.assetUrl(mBatch, ui.tabBg),
        cardBg: {
          dungeons: oss.assetUrl(mBatch, (ui.cards || {}).dungeons),
          classes: oss.assetUrl(mBatch, (ui.cards || {}).classes),
          loots: oss.assetUrl(mBatch, (ui.cards || {}).loots),
          guide: oss.assetUrl(mBatch, (ui.cards || {}).guide)
        }
      })
      const classes = ((cls.data || {}).classes || []).map((c) => ({
        classId: c.classId,
        nameCn: c.nameCn || '',
        iconUrl: oss.iconUrl(this.batch, c.iconKey)
      }))
      const named = classes.filter((c) => c.nameCn)
      /* 站主要默认选中战士；哪天名单里没有战士（改数据、或快照没更上），
         退到名单第一个，别让用户看见一个"选中的职业名字是空的" */
      const want = named.filter((c) => c.classId === DEFAULT_CLASS).length ? DEFAULT_CLASS : (named[0] || {}).classId || ''
      this.classes = named
      this.setData({
        loaded: true,
        offline: meta.source !== 'live' || cls.source !== 'live',
        requiresUpdate: !!(meta.requiresUpdate || cls.requiresUpdate),
        classes: named,
        classEmpty: named.length ? '' : '职业名单还没取到，联网后再选。'
      })
      this.pickClass(want)
      return null
    })
  },

  /* 选职业：只换下面那一段的内容，不跳转（跳转留给"看这个职业的技能书与天赋树"那条） */
  onPickClass(e) {
    const id = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.id) || '')
    if (id) this.pickClass(id)
  },

  pickClass(classId) {
    /* 与全站同一取法（用 filter()[0] 不用 Array.find，老基础库上不赌） */
    const cur = this.classes.filter((c) => c.classId === classId)[0]
    const races = this.raceSource
      .filter((r) => (r.classes || []).indexOf(classId) >= 0)
      .map((r) => ({
        id: r.id,
        key: r.id + '|' + (r.faction || ''),
        nameCn: r.nameCn || '',
        nameMissing: !r.nameCn,
        /* 天裔两条都叫"天裔"，靠子族名才分得开（塑风者 / 高阶会） */
        subCn: r.subgroup ? (r.subgroup.nameCn || '') : '',
        factionText: FACTION[r.faction] || r.faction || '',
        iconUrl: oss.raceIconUrl(this.batch, r),
        traits: (r.traits || []).map((t) => ({
          key: t.name,
          name: t.name,
          passive: !!t.passive,
          effect: t.effect || '',
          iconUrl: oss.iconUrl(this.batch, t.iconKey)
        }))
      }))
    this.setData({
      activeClass: classId,
      activeName: (cur && cur.nameCn) || '',
      races: races,
      /* 一个种族都没匹配上＝矩阵里没这个组合或数据没对上，界面必须说一句，
         不能让玩家以为"这职业没人能选" */
      raceNote: races.length ? '' : '这个职业的可选种族还没核到，不猜。'
    })
  },

  /* 选中职业的技能书与天赋树在职业详情页（天赋树可分享），首页只做"选" */
  goClass() {
    if (!this.data.activeClass) return
    wx.navigateTo({ url: '/pages/class/index?classId=' + encodeURIComponent(this.data.activeClass) })
  },

  /* 副本与职业都在 tabBar 里，只能 switchTab；用 navigateTo 会静默失败＝"点了没反应" */
  goDungeons() {
    wx.switchTab({ url: '/pages/dungeons/index' })
  },

  goClasses() {
    wx.switchTab({ url: '/pages/classes/index' })
  },

  goLoots() {
    wx.navigateTo({ url: '/pages/loots/index' })
  },

  /* 指南卡固定占一格：宏与插件一条都还没整理时也摆着，进去是诚实的空状态
     （2026-10-22 站主：「我要的是指南卡片」——上一版按有没有内容决定显不显示，撤掉） */
  goGuide() {
    wx.navigateTo({ url: '/pages/guide/index' })
  },

  /* 最近看过直接读索引快照里的那几条，不为首页再发一次网络请求 */
  syncRecent() {
    const map = {}
    ;(DUNGEON_INDEX.items || []).forEach((it) => {
      map[it.id] = { id: it.id, title: it.nameCn || it.nameEn || it.id, range: it.levelRange || '等级待实测' }
    })
    const ids = service.getRecentDungeons()
    const recent = ids.map((id) => map[id] || { id: id, title: id, range: '' }).slice(0, 4)
    /* 存储里记了但快照里没有的 id（比如改了副本 id）要主动丢掉，否则首页会一直显示一排原始编号 */
    if (ids.some((id) => !map[id])) {
      try { wx.setStorageSync(service.RECENT_DUNGEON_KEY, ids.filter((id) => map[id])) } catch (e) {}
    }
    this.setData({ recent })
  },

  /* 底图取不到（素材还没发、这张被撤、路径换了）就把那一层撤掉，卡片回到纯色版式。
     红线是不许出现碎图：加载失败必须接住，而不是留一个黑框在页面上。 */
  onArtError(e) {
    const k = String((e && e.currentTarget && e.currentTarget.dataset && e.currentTarget.dataset.k) || '')
    if (k === 'bg') {
      this.setData({ bgUrl: '' })
      return
    }
    if (k && this.data.cardBg[k]) {
      const cardBg = Object.assign({}, this.data.cardBg)
      cardBg[k] = ''
      this.setData({ cardBg })
    }
  },

  onRecentTap(e) {
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + encodeURIComponent(e.currentTarget.dataset.id) })
  },

  onDisclaimer() {
    wx.showModal({
      title: '声明',
      content: this.disclaimer || '非官方粉丝资料站，与暴雪娱乐及网易无关。',
      showCancel: false
    })
  }
})
