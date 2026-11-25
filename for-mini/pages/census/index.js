const service = require('../../services/forever-data')
const classSnapshot = require('../../data/forever-class-snapshot')

const FACTIONS = [{ id: 'alliance', name: '联盟' }, { id: 'horde', name: '部落' }]
const CLASSES = classSnapshot.classes.map((c) => ({ id: c.classId, name: c.nameCn }))
const CLASS_COLOR = {
  warrior: '#C79C6E',
  paladin: '#F58CBA',
  hunter: '#ABD473',
  rogue: '#FFF569',
  priest: '#FFFFFF',
  shaman: '#0070DE',
  mage: '#69CCF0',
  warlock: '#9482C9',
  druid: '#FF7D0A'
}
const SHARE_TITLE = '无限服人口普查 · 社区角色样本'

function countText(n) {
  return Number.isInteger(n) && n >= 0 ? '约 ' + n.toLocaleString('zh-CN') : ''
}

function rows(order, published, wholePercent) {
  const byId = new Map((Array.isArray(published) ? published : []).map((r) => [r.id, r]))
  return order.map(({ id, name }) => {
    const { count, share } = byId.get(id) || {}
    const measured = typeof share === 'number' && Number.isFinite(share) && share >= 0 && share <= (wholePercent ? 100 : 1)
    const label = measured ? (wholePercent ? String(share) : (share * 100).toFixed(1)) : ''
    return {
      id,
      name,
      color: CLASS_COLOR[id] || '#d9af69',
      progress: measured ? Number(label) : null,
      percent: measured ? label + '%' : '暂无数据',
      count: countText(count)
    }
  })
}

function viewOf(d) {
  if (!d || !d.provenance || !d.scope || !d.window || !countText(d.characters) || d.characters === 0) return null
  const factions = rows(FACTIONS, d.factions)
  const classes = rows(CLASSES, d.classes)
  if (!factions.concat(classes).some((r) => r.progress !== null)) return null
  return {
    factions,
    classes,
    classNote: '全样本分布 · 未按阵营拆分'
  }
}

function chinaView(d) {
  if (!d || !d.provenance || !d.factions || !d.classes) return null
  return {
    factions: rows(FACTIONS, d.factions, true),
    classes: rows(CLASSES, d.classes, true),
    classNote: '按来源保留整数，合计可能偏离 100%。'
  }
}

Page({
  data: { loading: true, sample: null, selectedSource: 'china', hasChina: false, notice: '', offline: false },

  onLoad() {
    this.refresh()
  },

  onPullDownRefresh() {
    this.refresh().then(() => wx.stopPullDownRefresh())
  },

  onRetry() {
    this.refresh()
  },

  onSourceSelect(e) {
    const selectedSource = e.currentTarget.dataset.source
    const sample = this.samples && this.samples[selectedSource]
    if (!sample) return
    this.preferredSource = selectedSource
    this.setData({ selectedSource, sample })
  },

  refresh() {
    if (this.pending) return this.pending
    this.setData({ loading: true })
    this.pending = service.loadCensus().then((r) => {
      const community = r.requiresUpdate ? null : viewOf(r.data)
      const china = community ? chinaView(r.data.china) : null
      this.samples = { community, china }
      const selectedSource = china && this.preferredSource !== 'community' ? 'china' : 'community'
      const sample = this.samples[selectedSource]
      const missing = r.error && r.error.code === 'missing'
      const notice = r.requiresUpdate ? '请更新小程序后查看。'
        : sample ? '' : missing || !r.error ? '暂无可查看的社区样本。' : '暂时无法获取样本，请稍后重试。'
      this.setData({ selectedSource, sample, hasChina: !!china, notice, offline: r.source !== 'live' })
    }).catch(() => {
      this.samples = null
      this.setData({ sample: null, hasChina: false, notice: '暂时无法获取样本，请稍后重试。', offline: true })
    }).then(() => {
      this.pending = null
      this.setData({ loading: false })
    })
    return this.pending
  },

  onShareTimeline() {
    return { title: SHARE_TITLE }
  },

  onShareAppMessage() {
    return { title: SHARE_TITLE, path: '/pages/census/index' }
  }
})
