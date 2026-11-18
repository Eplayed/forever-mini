const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')
const joinCard = require('../../services/item-card')
const adventure = require('../../services/adventure')

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
    quest: { rows: [], empty: '' },
    faction: '',
    hasFactions: false,
    planned: false,
    artUrl: '',
    mapUrl: '',
    mapZone: '',
    mapEntry: '',
    mapDrawn: false,
    openBoss: '',
    openItem: '',
    itemCard: null,
    itemSaved: false,
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
    this.wantTasks = !!(query && query.tasks === '1')
    this.setData({ id: pickId(query) })
    this.start()
  },

  onShow() {
    const { faction, plans, gear } = adventure.read()
    const patch = { planned: plans.some((plan) => plan.id === this.data.id) }
    if (faction !== this.data.faction) {
      patch.faction = faction
      if (this.questRows) patch.quest = this.filteredQuests(faction)
    }
    if (this.openTarget) patch.itemSaved = !!gear[this.openTarget.id]
    this.setData(patch)
  },

  dropNoticeFor(groups, lootState) {
    if (!this.dropQuery || lootState !== 'ready') return ''
    if (this.dropFrom === 'adventure') {
      return groups.some((b) => b.items.some((x) => x.itemId === this.dropQuery))
        ? '' : '当前掉落表未收录这件目标装备。'
    }
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
    this.openTarget = null
    this.setData({ openBoss: this.data.openBoss === id ? '' : id, openItem: '', itemCard: null, itemSaved: false })
  },

  onToggleItem(e) {
    const { key, item } = e.currentTarget.dataset
    const openItem = this.data.openItem === key ? '' : key
    const boss = openItem && this.data.bosses.find((b) => b.id === this.data.openBoss)
    const row = boss && boss.items.find((r) => r.key === key)
    this.setData(this.itemSelection(row, boss, String(item || '')))
  },

  itemSelection(row, boss, itemId) {
    this.openTarget = row ? {
      id: row.itemId, name: row.name, quality: row.q, dungeonId: this.data.id, dungeon: this.data.title,
      boss: boss.other ? '' : boss.name
    } : null
    return {
      openItem: row ? row.key : '',
      itemCard: row ? joinCard(this.loot, itemId) : null,
      itemSaved: !!(row && adventure.read().gear[row.itemId])
    }
  },

  onAddGear() {
    const item = this.openTarget
    if (!item) return
    if (adventure.read().gear[item.id]) {
      wx.navigateTo({ url: '/pages/adventure/index' })
      return
    }
    if (adventure.addGear(item)) this.setData({ itemSaved: true })
  },

  scrollToTasks() {
    wx.pageScrollTo({ selector: '#dungeon-quests', offsetTop: -12, duration: 220 })
  },

  onPlanDungeon() {
    if (this.data.planned) {
      wx.navigateTo({ url: '/pages/adventure/index' })
      return
    }
    if (adventure.addPlan({ id: this.data.id, name: this.data.title })) {
      this.setData({ planned: true })
      wx.showToast({ title: '已加入跑本计划', icon: 'none' })
    }
  },

  pickQuestFaction(e) {
    const faction = e.currentTarget.dataset.faction
    if (faction === this.data.faction || !adventure.setFaction(faction)) return
    this.setData({ faction, quest: this.filteredQuests(faction) })
  },

  filteredQuests(faction) {
    const visible = this.questRows.filter((q) => adventure.matchesQuest(q, faction))
    let region
    const rows = visible.map((q) => {
      const group = questRegion(q)
      const header = region === group ? '' : group
      region = group
      return Object.assign({}, q, { header, location: q.pickupZone === group ? '' : q.pickupZone })
    })
    return { rows, empty: rows.length ? '' : (this.questRows.length ? '这个阵营暂无已知任务。' : '暂无任务记录。') }
  },

  /* 任务与详情同一次取数。页面只整理任务与接取信息，来源留在分片中。 */
  questPack(dd) {
    const q = dd && dd.quests
    this.questRows = ((q && q.rows) || []).map((x, i) => {
      const npc = (x.pickupNpc || '').trim()
      const zone = (x.pickupZone || '').trim()
      return {
        key: String(i),
        faction: x.faction || '',
        reqLevel: x.reqLevel || 0,
        preQuest: x.preQuest || '',
        name: x.nameCn || x.nameEn || '（任务名待核）',
        missing: !x.nameCn,
        pickupNpc: npc,
        startItem: (x.startItem || '').trim(),
        pickupZone: zone,
        pickupCoords: pickupCoords(x),
        pickupMap: x.pickupMap && x.pickupMap !== zone ? x.pickupMap : ''
      }
    }).sort((a, b) => questRegion(a).localeCompare(questRegion(b)))
    return this.filteredQuests(this.data.faction)
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
        this.openTarget = null
        const bosses = this.groupDrops(roster, (l.data && l.data.drops) || [])
        const highlighted = this.followDrop && bosses.find((b) => b.items.some((x) => x.itemId === this.dropQuery))
        const target = highlighted && this.dropFrom === 'adventure' && highlighted.items.find((x) => x.itemId === this.dropQuery)
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
        const quest = this.questPack(d.data)
        this.setData({
          rows: merged,
          quest,
          hasFactions: this.questRows.some((q) => q.faction === '联盟' || q.faction === '部落'),
          bosses,
          bossEmpty: d.data && !bosses.length ? '这座副本还没有首领记录。' : '',
          openBoss: highlighted ? highlighted.id : this.data.openBoss,
          ...this.itemSelection(target, highlighted, this.dropQuery),
          lootState,
          highlightDrop: this.dropQuery,
          dropNotice: this.dropNoticeFor(bosses, lootState),
          detailSource: d.source,
          needOnline: d.source !== 'live' && d.source !== 'cache',
          offline: d.source !== 'live' || l.source !== 'live' || r.source !== 'live',
          sourceText: d.sourceText
        }, () => {
          if (target) {
            wx.pageScrollTo({ selector: '#goal-drop-' + target.key, offsetTop: -12, duration: 220 })
            return
          }
          if (!this.wantTasks) return
          this.wantTasks = false
          this.scrollToTasks()
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

function questRegion(row) {
  return row.pickupMap || row.pickupZone || (row.startItem ? '物品开启' : '接取地点待实测')
}

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
