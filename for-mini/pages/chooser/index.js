const oss = require('../../services/oss-manifest')

/* 职业怎么选（2026-11-08 站主第一批③，chooser.json / 素材库"选职业"题材实证）
   数据是 chooser/chooser.json：七题、每题选项带九职业权重——那是本站整理的玩法
   归类（meta.kind=site-opinion），不是官方推荐，更不是强度排行（meta.notRanked）。
   分数全部在这台手机上算：把答过的选项权重加回各职业，服务器不做任何计算；
   结果页只给方向不给强弱，并按红线把口径句固定在页头（数据下发 meta.note）。 */

const CLASS_CN = {
  warrior: '战士',
  paladin: '圣骑士',
  hunter: '猎人',
  rogue: '潜行者',
  priest: '牧师',
  shaman: '萨满祭司',
  mage: '法师',
  warlock: '术士',
  druid: '德鲁伊'
}

Page({
  data: {
    loaded: false,
    errorText: '',
    note: '',
    offline: false,
    step: 0,
    total: 0,
    q: null,
    picked: '',
    finished: false,
    results: [],
    tieNote: ''
  },

  onLoad() {
    this.answers = {}
    this.pack = null
    this.load()
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh())
  },

  onRetry() {
    this.load()
  },

  load() {
    this.setData({ loaded: false, errorText: '' })
    return oss.loadKey('chooser').then((r) => {
      const d = r.data
      if (!d || !Array.isArray(d.questions) || !d.questions.length) {
        this.setData({
          loaded: true,
          errorText: '问卷要联网才能取，现在取不到——待会儿再试。',
          offline: r.source !== 'live'
        })
        return
      }
      this.pack = d
      this.setData({
        loaded: true,
        offline: r.source !== 'live',
        note: (d.meta && d.meta.note) || '',
        total: d.questions.length
      })
      this.show(0)
    })
  },

  show(i) {
    const q = this.pack.questions[i]
    this.setData({ step: i, q: q, picked: this.answers[q.id] || '', finished: false })
  },

  onPick(e) {
    const oid = String(e.currentTarget.dataset.oid || '')
    if (!oid || !this.data.q) return
    this.answers[this.data.q.id] = oid
    this.setData({ picked: oid })
    const next = this.data.step + 1
    if (next < this.data.total) {
      setTimeout(() => this.show(next), 180)
    } else {
      setTimeout(() => this.finish(), 180)
    }
  },

  onBack(e) {
    const to = Number(e.currentTarget.dataset.step)
    if (to >= 0 && to < this.data.total) this.show(to)
  },

  finish() {
    const score = {}
    Object.keys(CLASS_CN).forEach((id) => { score[id] = 0 })
    this.pack.questions.forEach((q) => {
      const oid = this.answers[q.id]
      const opt = q.options.filter((o) => o.id === oid)[0]
      if (!opt) return
      Object.keys(opt.weight || {}).forEach((cid) => {
        if (score[cid] === undefined) score[cid] = 0
        score[cid] += Number(opt.weight[cid]) || 0
      })
    })
    const ranked = Object.keys(score)
      .map((id) => ({ id: id, name: CLASS_CN[id] || id, score: score[id] }))
      .sort((a, b) => b.score - a.score || a.id.localeCompare(b.id))
    const top = ranked[0].score
    const firstTier = ranked.filter((x) => x.score === top)
    const rest = ranked.filter((x) => x.score < top).slice(0, 3)
    const max = top || 1
    this.setData({
      finished: true,
      results: firstTier.concat(rest).map((x) => ({
        id: x.id,
        name: x.name,
        score: x.score,
        pct: Math.round((x.score / max) * 100),
        first: x.score === top,
        tie: firstTier.length > 1 && x.score === top
      })),
      tieNote: firstTier.length > 1
        ? '这几个方向同分并列——说明你的口味不止一头对得上，都可以试试。'
        : ''
    })
  },

  onRestart() {
    this.answers = {}
    this.show(0)
  },

  onOpenClass(e) {
    const id = String(e.currentTarget.dataset.id || '')
    if (!id) return
    wx.navigateTo({ url: '/pages/class/index?classId=' + encodeURIComponent(id) })
  },

  /* 全站分享（2026-11-03）：query 与 onShareAppMessage 的 path 参数一致（本页无参数） */
  onShareAppMessage() {
    return { title: '7 道题看看你适合玩哪个职业', path: '/pages/chooser/index' }
  },

  onShareTimeline() {
    return { title: '7 道题看看你适合玩哪个职业' }
  }
})
