const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')
const joinCard = require('../../services/item-card')

const KIND_LABEL = { new: '无限新本', classic: '经典本', raid: '团本' }

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
    kindLabel: '',
    rows: [],
    bosses: [],
    bossEmpty: '',
    quest: { rows: [], summary: '', empty: '' },
    artUrl: '',
    mapUrl: '',
    mapZone: '',
    mapEntry: '',
    mapDrawn: false,
    openBoss: '',
    openItem: '',
    itemCard: null,
    lootState: 'loading',
    highlightDrop: '',
    dropNotice: '',
    fav: false,
    disclaimer: ''
  },

  onLoad(query) {
    this.dropQuery = String((query && query.drop) || '')
    this.followDrop = !!this.dropQuery
    /* 从哪儿点来的（bis＝配装名单）。提示要说真话，不能把配装页来的玩家说成"从掉落反查过来" */
    this.dropFrom = String((query && query.from) || '')
    this.setData({ id: pickId(query) })
    this.start()
  },

  dropNoticeFor(groups, lootState) {
    if (!this.dropQuery || lootState !== 'ready') return ''
    const from = this.dropFrom === 'bis' ? '配装名单' : '掉落反查'
    return groups.some((b) => b.items.some((x) => x.itemId === this.dropQuery))
      ? '从' + from + '查看的物品已标出。'
      : '从' + from + '查看的物品尚未收录在这座本的掉落表里。'
  },

  onPullDownRefresh() {
    this.start().then(() => wx.stopPullDownRefresh())
  },

  /* 朋友圈（2026-11-03 站主要求全站可分享）：query 与 onShareAppMessage 的 path 参数一致 */
  onShareTimeline() {
    const d = this.d
    return {
      title: d ? (d.nameCn || d.nameEn || '副本详情') : '副本详情',
      query: d ? 'id=' + encodeURIComponent(d.id) : ''
    }
  },

  onToggleBoss(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ openBoss: this.data.openBoss === id ? '' : id, openItem: '', itemCard: null })
  },

  onToggleItem(e) {
    const { key, item } = e.currentTarget.dataset
    const openItem = this.data.openItem === key ? '' : key
    this.setData({ openItem, itemCard: openItem ? joinCard(this.loot, String(item || '')) : null })
  },

  /* 任务与详情同一次取数。页面只整理任务与接取信息，来源留在分片中。 */
  questPack(dd) {
    const q = dd && dd.quests
    if (!q) return { rows: [], summary: '', empty: '暂无任务记录。' }
    /* summary 判型：旧批缓存里它是 wclbox 自报的汇总对象，直接绑会渲出 [object Object]；
       新批已在分发层拼成字符串，这里两种都接，不许对象漏到模板。 */
    const summaryText = (s) => {
      if (!s) return ''
      if (typeof s === 'string') return s
      const seg = []
      if (s.faction) seg.push(s.faction + '阵营')
      if (s.questCount) seg.push(s.questCount + ' 条任务')
      if (s.xpTotal) seg.push('总经验 ' + s.xpTotal)
      return seg.join(' · ')
    }
    const rows = (q.rows || []).map((x) => {
      const seg = []
      if (x.questLevel !== null && x.questLevel !== undefined) seg.push(x.questLevel + ' 级')
      if (x.reqLevel !== null && x.reqLevel !== undefined) seg.push('需 ' + x.reqLevel + ' 级')
      if (x.xp !== null && x.xp !== undefined) seg.push('经验 ' + x.xp)
      const npc = (x.pickupNpc || '').trim()
      const zone = (x.pickupZone || '').trim()
      return {
        name: x.nameCn || x.nameEn || '（任务名待核）',
        missing: !x.nameCn,
        meta: seg.join(' · '),
        pickupNpc: npc,
        startItem: npc ? '' : (x.startItem || '').trim(),
        pickupZone: zone,
        pickupCoords: pickupCoords(x),
        pickupMap: x.pickupMap && x.pickupMap !== zone ? x.pickupMap : ''
      }
    })
    return {
      rows: rows,
      summary: summaryText(q.summary),
      empty: rows.length ? '' : '暂无任务记录。'
    }
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
        this.setData({ needOnline: true, detailSource: 'snapshot', lootState: 'offline' })
        return null
      }
      return Promise.all([
        service.loadDungeonDetail(item, r.batch),
        service.loadDungeonLoot(item, r.batch)
      ]).then((pair) => {
        const d = pair[0]
        const l = pair[1]
        const merged = baseRows.slice()
        const roster = d.data && d.data.dungeon ? d.data.dungeon.bosses || [] : []
        const lootState = l.data ? 'ready' : 'offline'
        this.loot = l.data
        const bosses = this.groupDrops(roster, (l.data && l.data.drops) || [])
        const highlighted = this.followDrop && bosses.find((b) => b.items.some((x) => x.itemId === this.dropQuery))
        if (l.data && d.data) this.followDrop = false
        if (d.data && d.data.dungeon) {
          const g = d.data.dungeon
          const alt = g.levelRangeAlt || g.levelRangeClient
          if (alt && alt !== g.levelRange) {
            merged[0].note = '客户端/资料另记 ' + alt + (g.levelRangeOfficial && g.levelRangeOfficial !== g.levelRange ? '；官方英文页 ' + g.levelRangeOfficial : '')
          }
          /* lootNote 是方法论长段（谁取的、怎么推的），玩家面不上；
             掉落那一节的标题已经写了"按经典旧世公开数据库推的，本站不写几率"。 */
          const geo = g.geo || null
          this.setData({
            artUrl: oss.assetUrl(this.batch, g.art),
            mapUrl: geo && geo.map ? oss.assetUrl(this.batch, geo.map) : '',
            mapZone: geo ? (geo.zone || '') : '',
            mapEntry: geo && geo.entryX !== null && geo.entryX !== undefined
              ? '入口约在 ' + geo.zone + ' ' + geo.entryX + ', ' + geo.entryY : '',
            mapDrawn: geo && geo.mapKind === 'addon-drawn'
          })
        }
        this.setData({
          rows: merged,
          quest: this.questPack(d.data),
          bosses,
          bossEmpty: d.data && !bosses.length ? '这座副本还没有首领记录。' : '',
          openBoss: highlighted ? highlighted.id : this.data.openBoss,
          openItem: '',
          itemCard: null,
          lootState,
          highlightDrop: this.dropQuery,
          dropNotice: this.dropNoticeFor(bosses, lootState),
          detailSource: d.source,
          needOnline: d.source !== 'live' && d.source !== 'cache',
          offline: d.source !== 'live' || l.source !== 'live' || r.source !== 'live',
          sourceText: d.sourceText
        })
        return null
      })
    })
  },

  groupDrops(roster, drops) {
    const bosses = roster.map((b) => ({
      id: b.id,
      name: b.nameCn || b.id,
      missing: !b.nameCn,
      portraitUrl: oss.assetUrl(this.batch, b.portrait),
      items: []
    }))
    const byId = new Map(bosses.map((b) => [b.id, b]))
    const byName = new Map()
    bosses.forEach((b) => byName.set(b.name, byName.has(b.name) ? null : b))
    const other = { id: '__other', name: '其他掉落', other: true, items: [] }
    drops.forEach((x, index) => {
      const boss = byId.get(x.bossId) || byName.get(x.bossCn) || other
      boss.items.push({
        key: String(index),
        itemId: String(x.itemId || ''),
        name: x.nameCn || x.nameEn || String(x.itemId || '') || '物品名待核',
        missing: !x.nameCn,
        boss: boss === other ? x.bossCn || '首领归属待实测' : '',
        q: x.quality === undefined || x.quality === null ? '' : x.quality,
        quality: quality.qualityName(x.quality),
        iconUrl: oss.iconUrl(this.batch, x.iconKey)
      })
    })
    if (other.items.length) bosses.push(other)
    bosses.forEach((b) => b.items.sort((a, c) => quality.qualityRank(c.q) - quality.qualityRank(a.q)
      || a.name.localeCompare(c.name)))
    return bosses
  },

  /* 副本列表现在是 tabBar 页：redirectTo / navigateTo 都打不开它，只会静默失败
     （＝玩家点"回到副本列表"没反应），必须 switchTab */
  onBack() {
    wx.switchTab({ url: '/pages/dungeons/index' })
  },

  onFav() {
    const added = service.toggleFavoriteDungeon(this.data.id)
    this.setData({ fav: added })
    wx.showToast({ title: added ? '已收藏' : '已取消收藏', icon: 'none' })
  },

  onShareAppMessage() {
    const d = this.data
    return {
      title: (d.title || d.id) + ' · ' + (d.rows.length ? d.rows[0].v : '副本资料'),
      path: '/pages/dungeon/index?id=' + encodeURIComponent(d.id)
    }
  }
})

function pickupCoords(row) {
  const { pickupX: x, pickupY: y } = row
  if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > 100 || y < 0 || y > 100) return ''
  return x + ', ' + y
}

/* 分享出去的地址冷启动时 query 里就是 id；不认识的 id 走"没收录"分支，不白屏 */
function pickId(query) {
  const raw = query && query.id ? String(query.id) : ''
  try {
    return decodeURIComponent(raw)
  } catch (e) {
    return raw
  }
}
