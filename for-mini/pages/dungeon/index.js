const service = require('../../services/forever-data')
const oss = require('../../services/oss-manifest')
const quality = require('../../services/quality')

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
    quest: { rows: [], summary: '', note: '', empty: '' },
    artUrl: '',
    mapUrl: '',
    mapZone: '',
    mapEntry: '',
    mapDrawn: false,
    drops: [],
    fav: false,
    disclaimer: ''
  },

  onLoad(query) {
    this.dropQuery = String((query && query.drop) || '')
    /* 从哪儿点来的（bis＝配装名单）。提示要说真话，不能把配装页来的玩家说成"从掉落反查过来" */
    this.dropFrom = String((query && query.from) || '')
    this.setData({ id: pickId(query) })
    this.start()
  },

  /* 高亮那句提示按"这件在本页的掉落表里到底有没有"来说。
     配装页那行出处是参考站写的，本站的掉落归属是另一份来源，两边不一致时这里根本没有那行——
     那就直说没有，不能一边找不到一边告诉玩家"下面高亮的是你查的那件"。 */
  dropNoticeFor(drops) {
    const q = this.dropQuery
    if (!q) return ''
    const from = this.dropFrom === 'bis' ? '配装名单' : '掉落反查'
    let hit = false
    for (let i = 0; i < drops.length; i += 1) {
      if (String(drops[i].itemId) === q) { hit = true; break }
    }
    return hit
      ? '你从' + from + '点过来：下面高亮的是这一件，它左边就是掉它的首领。'
      : '你从' + from + '点过来。这座本的掉落表里没有这一件——出处只有参考站那行字说过，本站这份没挂上这层归属，所以这里没有可高亮的行。'
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

  /* 站主 2026-11-09：点首领 → 跳掉落页只看这位首领掉的装备（带副本＋首领两个参数） */
  onOpenBoss(e) {
    const id = String(e.currentTarget.dataset.id || '')
    const name = String(e.currentTarget.dataset.name || '')
    if (!id) return
    const dname = encodeURIComponent(this.data.nameCn || this.data.title || this.data.id || '')
    wx.navigateTo({ url: '/pages/loots/index?dungeon=' + encodeURIComponent(this.data.id || '') + '&dname=' + dname + '&boss=' + encodeURIComponent(name) })
  },

  /* 任务线（2026-11-08 第一批②）：详情分片里的 det.quests（构建时从
     dungeon-quests.json 并进来，与详情同一次请求）。行里只摆事实字段；
     中文名没核出来就摆英文名 + "译名待核"，缺数字就不写那一段，不编。
     2026-11-09 站主要求把"在哪接的"摆出来：接取 NPC 336/396、地点 300/396 有值，
     都缺的那条照实说"没记录"，不猜接取人。 */
  questPack(dd) {
    const q = dd && dd.quests
    if (!q) return { rows: [], summary: '', note: '', empty: '这座本的任务线还没有记录，不猜。' }
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
        pickup: npc || zone ? [npc, zone].filter(Boolean).join(' · ') : '',
        pickupNone: !npc && !zone,
        src: x.source || ''
      }
    })
    return {
      rows: rows,
      summary: q.summary || '',
      note: q.note || '',
      empty: rows.length ? '' : '这座本的任务线还没有记录，不猜。'
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
          /* 首领一律走 icon-cell：有头像就出图，没有的由组件回落成自绘块（名字首字垫色块）。
             2026-10-23 站主说"头像图标都没有"——先分清是哪一种：经典本 146 个首领的头像
             线上有文件、界面也拼得出地址；三座无限新本的 15 个首领是**源站就没有这张脸**
             （2026-10-13 抓的时候 0/15，今天重探仍 0/15），不是我们漏接。
             所以这里不再摆一个写"没有这张头像"的虚线空框——那看着像坏了。 */
          bosses: d.data && d.data.dungeon ? (d.data.dungeon.bosses || []).map((b) => ({
            id: b.id,
            name: b.nameCn || b.id,
            missing: !b.nameCn,
            portraitUrl: oss.assetUrl(this.batch, b.portrait)
          })) : [],
          bossEmpty: d.data && d.data.dungeon && !(d.data.dungeon.bosses || []).length
            ? '这座的首领名单还没有记录，不猜。' : '',
          drops: l.data ? (l.data.drops || []).map((x) => ({
            itemId: String(x.itemId || ''),
            name: x.nameCn || x.itemId,
            boss: x.bossCn || '',
            quality: quality.qualityName(x.quality),
            iconUrl: oss.iconUrl(this.batch, x.iconKey)
          })) : [],
          dropGroups: this.groupDrops(l.data ? (l.data.drops || []) : []),
          highlightDrop: this.dropQuery || '',
          dropNotice: this.dropNoticeFor(l.data ? (l.data.drops || []) : []),
          detailSource: d.source,
          needOnline: d.source !== 'live' && d.source !== 'cache',
          offline: d.source !== 'live' || l.source !== 'live' || r.source !== 'live',
          sourceText: d.sourceText
        })
        return null
      })
    })
  },

  /* 掉落按首领分组：玩家问的是"这个 boss 掉什么"，不是一条平铺的长单子。
     没标首领的归到"没标首领"一组，不偷偷塞进第一组。
     组内按稀有度从高往下排（2026-10-23 站主指令），同档按名字排，
     这样紫的绿的一眼分得开，不用逐条读品质文字。 */
  groupDrops(drops) {
    const order = []
    const byBoss = {}
    drops.forEach((x) => {
      const b = x.bossCn || '没标首领'
      if (!byBoss[b]) { byBoss[b] = []; order.push(b) }
      byBoss[b].push({
        itemId: String(x.itemId || ''),
        name: x.nameCn || x.itemId || '（中文名待核）',
        missing: !x.nameCn,
        q: x.quality === undefined || x.quality === null ? '' : x.quality,
        quality: quality.qualityName(x.quality),
        iconUrl: oss.iconUrl(this.batch, x.iconKey)
      })
    })
    return order.map((b) => ({
      boss: b,
      rows: byBoss[b].sort((a, c) => quality.qualityRank(c.q) - quality.qualityRank(a.q)
        || String(a.name).localeCompare(String(c.name)))
    }))
  },

  /* 点一件装备 → 它自己的详情页。掉落片里已经带着每件的详情行了（属性/装等/卖价），
     详情页按这座本取同一片，不再发第二次网络请求。 */
  onOpenItem(e) {
    const id = e.currentTarget.dataset.item
    const d = e.currentTarget.dataset.dungeon
    if (!id) {
      wx.showToast({ title: '这件还没有物品编号', icon: 'none' })
      return
    }
    wx.navigateTo({ url: '/pages/item/index?d=' + encodeURIComponent(d) + '&i=' + encodeURIComponent(id) })
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

/* 分享出去的地址冷启动时 query 里就是 id；不认识的 id 走"没收录"分支，不白屏 */
function pickId(query) {
  const raw = query && query.id ? String(query.id) : ''
  try {
    return decodeURIComponent(raw)
  } catch (e) {
    return raw
  }
}
