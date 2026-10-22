const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')

/* 素材来源一句话，挂在原画下面：客户端画面经第三方站转存，不是本站画的 */
const ART_NOTE = '副本原画取自游戏客户端画面，经第三方资料站转存，不是本站绘制。'

const KIND_LABEL = { new: '无限新本', classic: '经典本', raid: '团本' }
const QUALITY = { 0: '未说明', 1: '常见', 2: '优良', 3: '稀有', 4: '史诗', 5: '传说' }

/* 副本详情（M01）
   取数三段：索引（列表页给的同一批）→ 详情分片 → 掉落分片。
   批次上下文 r.batch 一路传下去，中途线上换了批次也不会半新半旧。
   断网首用只有索引快照时，明确写"详情需联网"，不拿索引里那几个数冒充完整详情。 */

Page({
  data: {
    id: '',
    loaded: false,
    notFound: false,
    needOnline: false,
    offline: false,
    sourceText: '',
    detailSource: '',
    requiresUpdate: false,
    title: '',
    nameCn: '',
    nameEn: '',
    nameMissing: false,
    enMissing: false,
    conflict: '',
    kindLabel: '',
    rows: [],
    bosses: [],
    bossEmpty: '',
    artUrl: '',
    artNote: ART_NOTE,
    drops: [],
    prov: [],
    provOpen: false,
    fav: false,
    disclaimer: ''
  },

  onLoad(query) {
    this.setData({ id: pickId(query) })
    this.start()
  },

  onPullDownRefresh() {
    this.start().then(() => wx.stopPullDownRefresh())
  },

  start() {
    return service.loadDungeonIndex().then((r) => {
      const items = (r.data && r.data.items) || []
      const item = items.filter((x) => x.id === this.data.id)[0]
      if (!item) {
        this.setData({ loaded: true, notFound: true, offline: r.source !== 'live', sourceText: r.sourceText })
        return null
      }
      this.setData({
        loaded: true,
        notFound: false,
        offline: r.source !== 'live',
        sourceText: r.sourceText,
        requiresUpdate: r.requiresUpdate,
        /* 同列表页：批次号与核对日期不上界面，但留给门禁与排障读 */
        factLatest: (r.factDates && r.factDates.latest) || '',
        buildId: r.buildId || '',
        kindLabel: KIND_LABEL[item.kind] || item.kind || '副本',
        title: item.nameCn || item.nameEn || item.id,
        nameCn: item.nameCn || '',
        nameEn: item.nameEn || '',
        nameMissing: !item.nameCn,
        enMissing: !item.nameEn,
        conflict: item.nameCnConflict || '',
        fav: service.isFavoriteDungeon(item.id)
      })
      this.batch = r.batch || null
      /* 进过一次就算"最近看过"，不要求详情分片也取到（断网首用同样要有痕迹） */
      service.noteRecentDungeon(item.id)
      /* 索引就能确定的几行先落屏：断网时这一屏仍有可读内容 */
      const baseRows = [
        { k: '可进入等级', v: item.levelRange || '待实测', note: item.levelRange && item.levelRangeOfficial && item.levelRangeOfficial !== item.levelRange ? '官方英文页另写 ' + item.levelRangeOfficial : '' },
        { k: '阵营', v: item.faction || '未记录', note: '' },
        { k: '位置', v: item.zoneCn || '待补充', note: '' },
        { k: '队伍人数', v: item.partySize ? item.partySize + ' 人' : '未记录', note: item.partySizeAlt ? '另一说法：' + item.partySizeAlt + ' 人' : (item.sizeClaim || '') }
      ]
      /* 2026-10-22 站主定的：玩家不看"几个首领几条掉落"这类计数，
         下面两节本来就把名单和掉落一条条列出来了，行里再报一遍数只是台账。 */
      this.setData({ rows: baseRows })
      if (!r.batch) {
        this.setData({ needOnline: true, detailSource: 'snapshot' })
        return null
      }
      return Promise.all([
        service.loadDungeonDetail(item, r.batch),
        service.loadDungeonLoot(item, r.batch)
      ]).then((pair) => {
        const d = pair[0]
        const l = pair[1]
        const merged = baseRows.slice()
        if (d.data && d.data.dungeon) {
          const g = d.data.dungeon
          const alt = g.levelRangeAlt || g.levelRangeClient
          if (alt && alt !== g.levelRange) {
            merged[0].note = '客户端/资料另记 ' + alt + (g.levelRangeOfficial && g.levelRangeOfficial !== g.levelRange ? '；官方英文页 ' + g.levelRangeOfficial : '')
          }
          /* lootNote 是方法论长段（谁取的、怎么推的），玩家面不上；
             掉落那一节的标题已经写了"按经典旧世公开数据库推的，本站不写几率"。 */
          this.setData({ artUrl: oss.assetUrl(this.batch, g.art) })
        }
        this.setData({
          rows: merged,
          bosses: d.data && d.data.dungeon ? (d.data.dungeon.bosses || []).map((b) => ({
            name: b.nameCn || b.id,
            missing: !b.nameCn,
            portraitUrl: oss.assetUrl(this.batch, b.portrait),
            hasPortrait: !!b.portrait
          })) : [],
          bossEmpty: d.data && d.data.dungeon && !(d.data.dungeon.bosses || []).length
            ? '这座的首领名单还没有记录，不猜。' : '',
          prov: d.data && d.data.dungeon ? (d.data.dungeon.provenance || []).map((p) => ({
            type: p.type || '未标注',
            note: p.note || '',
            url: p.url || '',
            checkedAt: p.checkedAt || '未记录'
          })) : [],
          drops: l.data ? (l.data.drops || []).map((x) => ({
            name: x.nameCn || x.itemId,
            boss: x.bossCn || '',
            quality: QUALITY[x.quality] || '未说明',
            iconUrl: oss.iconUrl(this.batch, x.iconKey)
          })) : [],
          detailSource: d.source,
          needOnline: d.source !== 'live' && d.source !== 'cache',
          offline: d.source !== 'live' || l.source !== 'live' || r.source !== 'live',
          sourceText: d.sourceText
        })
        return null
      })
    })
  },

  /* 副本列表现在是 tabBar 页：redirectTo / navigateTo 都打不开它，只会静默失败
     （＝玩家点"回到副本列表"没反应），必须 switchTab */
  onProvToggle() {
    this.setData({ provOpen: !this.data.provOpen })
  },

  onBack() {
    wx.switchTab({ url: '/pages/dungeons/index' })
  },

  onFav() {
    const added = service.toggleFavoriteDungeon(this.data.id)
    this.setData({ fav: added })
    wx.showToast({ title: added ? '已收藏' : '已取消收藏', icon: 'none' })
  },

  onCopy() {
    const d = this.data
    const lines = [d.title + (d.nameEn ? ' / ' + d.nameEn : '')]
    d.rows.forEach((r) => { lines.push(r.k + '：' + r.v + (r.note ? '（' + r.note + '）' : '')) })
    if (d.bosses.length) lines.push('首领：' + d.bosses.map((b) => b.name).join('、'))
    lines.push('来自「无限资料」小程序 · 非官方粉丝资料站')
    wx.setClipboardData({ data: lines.join('\n'), success() { wx.showToast({ title: '已复制', icon: 'none' }) } })
  },

  onOpenSource(e) {
    const url = e.currentTarget.dataset.url
    if (!url) {
      wx.showToast({ title: '这条来源没有链接', icon: 'none' })
      return
    }
    wx.setClipboardData({
      data: url,
      success() { wx.showToast({ title: '来源链接已复制，请到浏览器打开', icon: 'none', duration: 2500 }) }
    })
  },

  onShareAppMessage() {
    const d = this.data
    return {
      title: (d.title || d.id) + ' · ' + (d.rows.length ? d.rows[0].v : '副本资料'),
      path: '/pages/dungeon/index?id=' + encodeURIComponent(d.id)
    }
  }
})

/* 分享出去的地址冷启动时 query 里就是 id；不认识的 id 走"没收录"分支，不白屏 */
function pickId(query) {
  const raw = query && query.id ? String(query.id) : ''
  try {
    return decodeURIComponent(raw)
  } catch (e) {
    return raw
  }
}
