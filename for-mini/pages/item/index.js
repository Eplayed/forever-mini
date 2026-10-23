const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')

/* 装备详情（2026-10-23 站主："点击装备可以单独展示装备详情"）
   数据只取这座本的掉落片——那一件的名字、品质、图标、掉它的首领在同片的 drops 里，
   属性行/装等/卖价/状态在同片的 cards 里按 itemId 对上。一次 GET，点回来的第二件也命中同一份缓存。
   所以地址要带这座本（d）：只给物品编号没有意义，本站没有全库单件接口。 */

/* 状态键→那句话。与网页端 ItemsPage 的 STN 同一份叫法，两边不许各写一套 */
const ST_TEXT = {
  new: '无限新加的物品',
  changed: '相对经典旧世有改动',
  rebuilt: '相对经典旧世重做过',
  missing: '参考站名录里说无限中没有',
  srvHas: '玩家 2026-10-19 在测试服确认有这件'
}

Page({
  data: {
    dungeonId: '',
    itemId: '',
    loaded: false,
    notFound: false,
    needOnline: false,
    offline: false,
    sourceText: '',
    requiresUpdate: false,
    name: '',
    missing: false,
    q: '',
    qualityText: '',
    iconUrl: '',
    type: '',
    ilvl: '',
    st: [],
    sell: '',
    stText: '',
    boss: '',
    dungeon: '',
    idNote: '',
    gradeNote: ''
  },

  onLoad(query) {
    const q = query || {}
    this.setData({
      dungeonId: dec(q.d),
      itemId: dec(q.i)
    })
    this.start()
  },

  onPullDownRefresh() {
    this.start().then(() => wx.stopPullDownRefresh())
  },

  start() {
    const dungeonId = this.data.dungeonId
    const itemId = this.data.itemId
    if (!dungeonId || !itemId) {
      this.setData({ loaded: true, notFound: true })
      return Promise.resolve(null)
    }
    return service.loadDungeonIndex().then((r) => {
      const item = ((r.data && r.data.items) || []).filter((x) => x.id === dungeonId)[0]
      if (!item) {
        this.setData({ loaded: true, notFound: true, offline: r.source !== 'live', sourceText: r.sourceText })
        return null
      }
      this.batch = r.batch || null
      this.setData({
        loaded: true,
        notFound: false,
        offline: r.source !== 'live',
        requiresUpdate: r.requiresUpdate,
        sourceText: r.sourceText,
        dungeon: item.nameCn || item.nameEn || item.id
      })
      if (!r.batch) {
        this.setData({ needOnline: true })
        return null
      }
      return service.loadDungeonLoot(item, r.batch).then((l) => {
        const drops = (l.data && l.data.drops) || []
        const row = drops.filter((x) => String(x.itemId) === itemId)[0] || null
        const card = joinCard(l.data, itemId)
        if (!row && !card) {
          this.setData({ loaded: true, notFound: true, needOnline: l.source !== 'live' && l.source !== 'cache' })
          return null
        }
        const q = row ? row.quality : null
        this.setData({
          needOnline: l.source !== 'live' && l.source !== 'cache',
          offline: l.source !== 'live' || r.source !== 'live',
          sourceText: l.sourceText || this.data.sourceText,
          name: (row && row.nameCn) || '（中文名待核）',
          missing: !(row && row.nameCn),
          q: q === undefined || q === null ? '' : q,
          qualityText: quality.qualityName(q),
          iconUrl: oss.iconUrl(this.batch, row && row.iconKey),
          type: (card && card.type) || '',
          ilvl: card && card.ilvl !== null && card.ilvl !== undefined ? String(card.ilvl) : '',
          st: ((card && card.st) || []).map(stRow),
          sell: (card && card.sell) || '',
          stText: card && card.stKey ? (ST_TEXT[card.stKey] || '') : '',
          boss: (row && row.bossCn) || '',
          idNote: card ? '' : '这件的数值行还没入库，先只给名单里有的那些。',
          gradeNote: '属性行与卖价取自第三方名录，本站未做游戏内实测；掉落本身按经典旧世推的，官方说过无限服重做过掉落。'
        })
        return null
      })
    })
  },

  onOpenDungeon() {
    wx.navigateTo({ url: '/pages/dungeon/index?id=' + encodeURIComponent(this.data.dungeonId) })
  },

  onCopyId() {
    wx.setClipboardData({
      data: this.data.itemId,
      success() { wx.showToast({ title: '物品编号已复制', icon: 'none' }) }
    })
  },

  onShareAppMessage() {
    const d = this.data
    return {
      title: (d.name || '这件装备') + (d.dungeon ? ' · ' + d.dungeon : ''),
      path: '/pages/item/index?d=' + encodeURIComponent(d.dungeonId) + '&i=' + encodeURIComponent(d.itemId)
    }
  }
})

/* cards 是位置数组（列名在同片 cardCols 里），按列名取值而不是按序号写死：
   生成器加一列不会把这一页读歪。 */
function joinCard(loot, itemId) {
  if (!loot || !Array.isArray(loot.cards)) return null
  const cols = loot.cardCols || []
  const row = loot.cards.filter((r) => String(r[cols.indexOf('itemId')]) === itemId)[0]
  if (!row) return null
  const at = (k) => (cols.indexOf(k) >= 0 ? row[cols.indexOf(k)] : null)
  return {
    type: at('type'),
    ilvl: at('ilvl'),
    st: at('st') || [],
    sell: at('sell'),
    stKey: at('stKey')
  }
}

/* 属性行分两类：数值行（护甲/属性加成/速度）与那句话（装备效果、套装名与套装件数）。
   游戏里的悬浮框就是这个层次，玩家扫一眼能先看到数值。 */
const SAID_LINE = /装备|使用|套装|（\d+\s*[件/／]|\(\d+\s*[件/／]/
function stRow(line) {
  const t = String(line || '')
  return { t: t, said: SAID_LINE.test(t) }
}

function dec(v) {
  const s = String(v || '')
  try {
    return decodeURIComponent(s)
  } catch (e) {
    return s
  }
}
