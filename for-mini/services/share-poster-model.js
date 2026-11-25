/* 分享长图纯数据组装与分页模块（零微信 API 依赖，供小程序 Canvas 2D 与 Node 单测共用）
 * 严格兼容小程序旧基础库 ES5/ES6 语法。 */

var FOOTER_BRAND = '微信搜一搜 · 跑本无限助手'
var FOOTER_LEGAL = '非官方粉丝资料站，与暴雪娱乐及网易无关'
var L1_BIS_NOTE = '名单整理自第三方资料，非官方结论，未做模拟计算'

var CLASS_SHORT = {
  warrior: '战',
  paladin: '骑',
  hunter: '猎',
  rogue: '贼',
  priest: '牧',
  shaman: '萨',
  mage: '法',
  warlock: '术',
  druid: '德'
}

function visualWidth(str) {
  var s = String(str || '')
  var w = 0
  for (var i = 0; i < s.length; i++) {
    var code = s.charCodeAt(i)
    w += code > 127 ? 2 : 1.08
  }
  return w
}

function wrapText(text, maxUnits) {
  var raw = String(text || '').replace(/\r/g, '')
  if (!raw) return []
  var cap = maxUnits || 44
  var out = []
  var paragraphs = raw.split('\n')
  for (var p = 0; p < paragraphs.length; p++) {
    var para = paragraphs[p]
    if (!para) continue
    var cur = ''
    var curW = 0
    for (var i = 0; i < para.length; i++) {
      var ch = para.charAt(i)
      var cw = para.charCodeAt(i) > 127 ? 2 : 1.08
      if (cur && curW + cw > cap) {
        out.push(cur)
        cur = ch
        curW = cw
      } else {
        cur += ch
        curW += cw
      }
    }
    if (cur) out.push(cur)
  }
  return out
}

function normalizeDungeonName(src) {
  var s = String(src || '').trim()
  if (!s) return ''
  s = s.replace(/^副本(?:任务)?[：:]\s*/, '')
  var head = s.split('·')[0].split('（')[0].split('(')[0].split('/')[0].trim()
  if (!head) return ''
  if (/^(任务|专业|锻造|裁缝|制皮|工程|炼金|附魔|世界|声望|荣誉|战场|拍卖|商人|待核|出处|掉落)/.test(head)) {
    return ''
  }
  return head
}

/**
 * 构建副本图鉴索引：支持按 id、nameCn、nameCnConflict 或短名（如「厄运之槌」「斯坦索姆」「黑石塔」）检索副本底图
 */
function buildDungeonArtMap(dungeonItems, resolveArtUrl) {
  var list = Array.isArray(dungeonItems) ? dungeonItems : []
  var fn = typeof resolveArtUrl === 'function' ? resolveArtUrl : function (x) { return x || '' }
  var byKey = {}
  var entries = []
  for (var i = 0; i < list.length; i++) {
    var d = list[i]
    if (!d) continue
    var url = d.art ? fn(d.art) : ''
    var rec = { id: d.id || '', name: d.nameCn || d.nameEn || d.id || '', artUrl: url }
    entries.push(rec)
    if (d.id) byKey[d.id] = rec
    if (d.nameCn) byKey[d.nameCn] = rec
    if (d.nameCnConflict) byKey[d.nameCnConflict] = rec
  }
  return { byKey: byKey, entries: entries }
}

function lookupDungeonArt(dungeonArtMap, keyOrName) {
  if (!dungeonArtMap || !keyOrName) return null
  var k = String(keyOrName).trim()
  if (!k) return null
  if (dungeonArtMap.byKey) {
    if (dungeonArtMap.byKey[k]) return dungeonArtMap.byKey[k]
    var entries = dungeonArtMap.entries || []
    for (var i = 0; i < entries.length; i++) {
      var nm = entries[i].name || ''
      if (nm && (nm.indexOf(k) === 0 || k.indexOf(nm) === 0)) {
        return entries[i]
      }
    }
    return null
  }
  /* 兼容直接传 plain object { '厄运之槌': 'https://...' } */
  var direct = dungeonArtMap[k]
  if (typeof direct === 'string') return { id: '', name: k, artUrl: direct }
  if (direct && typeof direct === 'object') return direct
  var ks = Object.keys(dungeonArtMap)
  for (var j = 0; j < ks.length; j++) {
    var key = ks[j]
    if (key && (key.indexOf(k) === 0 || k.indexOf(key) === 0)) {
      var val = dungeonArtMap[key]
      if (typeof val === 'string') return { id: '', name: key, artUrl: val }
      if (val && typeof val === 'object') return val
    }
  }
  return null
}

/**
 * 团长开荒一图流：把 27 套 60 级团前 BiS 聚合成「最值得全团优先刷的五人本排行榜」
 * 每座副本带副本底图缩略图 + 前 3 件核心装备真实图标，适合团长/队长一键发 500 人公会微信群。
 */
function buildRaidPrepOneSheet(bis60Sets, bis60Src, itemsMap, dungeonArtMap) {
  var sets = Array.isArray(bis60Sets) ? bis60Sets : []
  var srcMap = bis60Src || {}
  var items = itemsMap || {}
  var byDungeon = {}

  sets.forEach(function (set) {
    var specKey = (set.cls || '') + ':' + (set.mode || set.id || '')
    var clsShort = CLASS_SHORT[set.cls] || (set.clsCn ? String(set.clsCn).charAt(0) : '')
    var seenInSpec = {}
    var slots = set.doll || set.slots || []
    slots.forEach(function (row) {
      var itemId = Array.isArray(row) ? String(row[2] || '') : String((row && row.item) || '')
      if (!itemId) return
      var rawSrc = srcMap[itemId]
      var srcText = typeof rawSrc === 'string'
        ? rawSrc
        : ((rawSrc && rawSrc.src) ? rawSrc.src : ((row && !Array.isArray(row) && row.src) ? row.src : ''))
      var dName = normalizeDungeonName(srcText)
      if (!dName) return
      if (!byDungeon[dName]) {
        byDungeon[dName] = {
          name: dName,
          specs: {},
          classes: {},
          items: {},
          itemList: []
        }
      }
      var bucket = byDungeon[dName]
      if (!seenInSpec[dName]) {
        seenInSpec[dName] = true
        bucket.specs[specKey] = true
      }
      if (clsShort) bucket.classes[clsShort] = true
      if (!bucket.items[itemId]) {
        var meta = items[itemId]
        var nm = (meta && meta.name) ? meta.name : ('#' + itemId)
        var q = meta && typeof meta.q === 'number' ? meta.q : 3
        var iconUrl = (meta && meta.iconUrl) ? meta.iconUrl : ''
        bucket.items[itemId] = true
        bucket.itemList.push({ id: itemId, name: nm, q: q, iconUrl: iconUrl, count: 1 })
      } else {
        for (var j = 0; j < bucket.itemList.length; j++) {
          if (bucket.itemList[j].id === itemId) {
            bucket.itemList[j].count += 1
            break
          }
        }
      }
    })
  })

  var ranked = Object.keys(byDungeon).map(function (k) {
    var b = byDungeon[k]
    b.itemList.sort(function (a, c) { return (c.count - a.count) || (c.q - a.q) })
    return {
      name: b.name,
      specCount: Object.keys(b.specs).length,
      itemCount: b.itemList.length,
      classTags: Object.keys(b.classes).join('/'),
      topItems: b.itemList.slice(0, 3)
    }
  })

  ranked.sort(function (a, b) {
    return (b.specCount - a.specCount) || (b.itemCount - a.itemCount) || a.name.localeCompare(b.name)
  })

  var topList = ranked.slice(0, 12)
  var entries = topList.map(function (d, idx) {
    var art = lookupDungeonArt(dungeonArtMap, d.name)
    var drops = d.topItems.map(function (it) { return it.name }).join('、')
    var miniIcons = d.topItems.map(function (it) {
      return {
        id: it.id,
        name: it.name,
        quality: it.q,
        url: it.iconUrl || ''
      }
    })
    return {
      tag: 'TOP ' + (idx + 1),
      title: d.name + '  (' + d.specCount + ' 专精 · ' + d.itemCount + ' 件)',
      quality: d.topItems.length ? d.topItems[0].q : 3,
      sub: (d.classTags ? ('适用：' + d.classTags + '  |  ') : '') + (drops ? ('核心：' + drops) : '查看详情了解掉落'),
      iconKind: 'dungeon',
      iconUrl: (art && art.artUrl) ? art.artUrl : '',
      iconLabel: d.name.slice(0, 2),
      miniIcons: miniIcons
    }
  })

  if (!entries.length) {
    entries.push({
      tag: '提示',
      title: '当前暂无可汇总的 60 级团前副本掉落',
      quality: 1,
      sub: '联网加载最新配装数据后重试',
      iconKind: 'none',
      iconUrl: '',
      iconLabel: ''
    })
  }

  return {
    kind: 'raid_prep',
    badge: '团长开荒一图流',
    title: '60 级团前必刷五人本总览',
    subtitle: '汇总 ' + sets.length + ' 套全职业团前配装 · 按需求热度排序，可直接发群',
    note: L1_BIS_NOTE,
    entries: entries,
    footerBrand: FOOTER_BRAND,
    footerHint: '进小程序按职业查看完整配装、同部位备选与副本任务坐标',
    footerLegal: FOOTER_LEGAL
  }
}

/**
 * 单职业/套装配装分享图（支持 30 级、60 级团前、T1、14–58 套装图鉴）
 */
function buildBisSetPoster(opts) {
  var o = opts || {}
  var stageKey = o.stageKey || '60'
  var rows = Array.isArray(o.rows) ? o.rows : []
  var entries = rows.map(function (r) {
    var slotText = r.slotLabel || r.slot || ''
    var itemName = r.missing ? ('物品待核 (#' + r.item + ')') : (r.name || '待补')
    var subParts = []
    if (r.ilvl !== '' && r.ilvl !== undefined && r.ilvl !== null) subParts.push('装等 ' + r.ilvl)
    if (r.src) subParts.push(r.src)
    else if (r.pieceText) subParts.push(r.pieceText)
    return {
      tag: slotText,
      title: itemName,
      quality: typeof r.q === 'number' ? r.q : 3,
      sub: subParts.join(' · '),
      iconKind: r.iconKind || 'item',
      iconUrl: r.iconUrl || '',
      iconLabel: (slotText || itemName).slice(0, 1)
    }
  })

  if (!entries.length) {
    entries.push({
      tag: '提示',
      title: '本套暂无装备条目',
      quality: 1,
      sub: '请先选择有效职业与套装',
      iconKind: 'none',
      iconUrl: '',
      iconLabel: ''
    })
  }

  var isThirdParty = stageKey === '30' || stageKey === '60'
  return {
    kind: 'bis_set',
    badge: o.badge || '配装分享卡',
    title: o.title || '配装清单',
    subtitle: o.subtitle || ('共 ' + entries.length + ' 件核心装备'),
    note: isThirdParty ? L1_BIS_NOTE : (o.note || '仅展示已收录部件事实，未知项标待实测'),
    entries: entries,
    footerBrand: FOOTER_BRAND,
    footerHint: '搜一搜进入查看同部位备选与一键加入冒险清单',
    footerLegal: FOOTER_LEGAL
  }
}

/**
 * 玩家个人「今晚刷本缺口卡 / 组队喊人图」（来自我的冒险清单）
 * 顶部跑本顺序带副本封面缩略条，每件目标装备带装备图标 + 对应副本小徽标。
 */
function buildAdventurePoster(plans, groups, dungeonArtMap) {
  var planList = Array.isArray(plans) ? plans : []
  var groupList = Array.isArray(groups) ? groups : []
  var entries = []

  if (planList.length) {
    var routeNames = planList.slice(0, 6).map(function (p, i) {
      return (i + 1) + '.' + (p.name || p.id)
    }).join('  →  ')
    var routeThumbs = planList.slice(0, 5).map(function (p) {
      var art = lookupDungeonArt(dungeonArtMap, p.id) || lookupDungeonArt(dungeonArtMap, p.name)
      return {
        id: p.id || '',
        name: p.name || p.id || '',
        artUrl: (art && art.artUrl) ? art.artUrl : ''
      }
    })
    entries.push({
      tag: '跑本顺序',
      title: routeNames,
      quality: 5,
      sub: '共排了 ' + planList.length + ' 个副本，求同路车队一起刷',
      iconKind: 'route',
      iconUrl: routeThumbs.length ? routeThumbs[0].artUrl : '',
      iconLabel: '路线',
      routeThumbs: routeThumbs
    })
  }

  var totalItems = 0
  groupList.forEach(function (g) {
    var gRows = Array.isArray(g.rows) ? g.rows : []
    var gArt = lookupDungeonArt(dungeonArtMap, g.key) || lookupDungeonArt(dungeonArtMap, g.title)
    var gArtUrl = (gArt && gArt.artUrl) ? gArt.artUrl : ''
    gRows.forEach(function (row) {
      totalItems += 1
      var srcText = (row.sources && row.sources.length)
        ? row.sources.map(function (s) { return s.label }).join(' / ')
        : (row.sourceText || g.title || '出处待核')
      var rowArtUrl = gArtUrl
      if (!rowArtUrl && row.dungeonId) {
        var rArt = lookupDungeonArt(dungeonArtMap, row.dungeonId)
        rowArtUrl = (rArt && rArt.artUrl) ? rArt.artUrl : ''
      }
      entries.push({
        tag: g.title || '目标',
        title: row.name || ('#' + row.id),
        quality: typeof row.quality === 'number' ? row.quality : 3,
        sub: srcText,
        iconKind: 'item',
        iconUrl: row.iconUrl || '',
        iconLabel: (row.name || '#').slice(0, 1),
        badgeIconUrl: rowArtUrl
      })
    })
  })

  if (!entries.length) {
    entries.push({
      tag: '空清单',
      title: '还没有添加想刷的副本或装备',
      quality: 1,
      sub: '先去副本手册或 BIS 配装点「想要」加入清单',
      iconKind: 'none',
      iconUrl: '',
      iconLabel: ''
    })
  }

  return {
    kind: 'adventure',
    badge: '今晚组队喊人卡',
    title: '我的刷本缺口清单',
    subtitle: (planList.length ? ('计划 ' + planList.length + ' 个本 · ') : '') + '还差 ' + totalItems + ' 件目标装备',
    note: '可直接发到微信开黑群喊队友一起组队刷本',
    entries: entries,
    footerBrand: FOOTER_BRAND,
    footerHint: '打开小程序排好自己的跑本计划与任务接取坐标',
    footerLegal: FOOTER_LEGAL
  }
}

/**
 * 确定性分页：把长条目拆成多张易读卡片，单张高度可控不爆 Canvas 显存
 */
function paginatePoster(spec, maxRowsPerPage) {
  var safeSpec = spec || {}
  var all = Array.isArray(safeSpec.entries) ? safeSpec.entries : []
  var perPage = maxRowsPerPage || 9
  var prepared = all.map(function (entry) {
    var kind = entry.iconKind || 'none'
    var hasLeftIcon = kind === 'dungeon' || kind === 'item'
    var titleCap = kind === 'dungeon' ? 38 : (kind === 'route' ? 38 : (hasLeftIcon ? 28 : 34))
    var subCap = kind === 'dungeon' ? 46 : (kind === 'route' ? 44 : (hasLeftIcon ? 38 : 44))
    return {
      tag: String(entry.tag || '').slice(0, 12),
      titleLines: wrapText(entry.title || '', titleCap).slice(0, 2),
      subLines: wrapText(entry.sub || '', subCap).slice(0, 2),
      quality: typeof entry.quality === 'number' ? entry.quality : 1,
      iconKind: kind,
      iconUrl: entry.iconUrl || '',
      iconLabel: entry.iconLabel || '',
      badgeIconUrl: entry.badgeIconUrl || '',
      miniIcons: Array.isArray(entry.miniIcons) ? entry.miniIcons.slice(0, 3) : [],
      routeThumbs: Array.isArray(entry.routeThumbs) ? entry.routeThumbs.slice(0, 5) : []
    }
  })

  var chunks = []
  for (var i = 0; i < prepared.length; i += perPage) {
    chunks.push(prepared.slice(i, i + perPage))
  }
  if (!chunks.length) chunks.push([])

  var totalPages = chunks.length
  return chunks.map(function (rows, idx) {
    return {
      pageIndex: idx,
      totalPages: totalPages,
      kind: safeSpec.kind || 'generic',
      badge: safeSpec.badge || '分享长图',
      titleLines: wrapText(safeSpec.title || '跑本助手', 32).slice(0, 2),
      subtitleLines: wrapText(safeSpec.subtitle || '', 48).slice(0, 2),
      noteLines: wrapText(safeSpec.note || '', 50).slice(0, 2),
      rows: rows,
      footerBrand: safeSpec.footerBrand || FOOTER_BRAND,
      footerHint: safeSpec.footerHint || '',
      footerLegal: safeSpec.footerLegal || FOOTER_LEGAL
    }
  })
}

module.exports = {
  FOOTER_BRAND: FOOTER_BRAND,
  FOOTER_LEGAL: FOOTER_LEGAL,
  L1_BIS_NOTE: L1_BIS_NOTE,
  visualWidth: visualWidth,
  wrapText: wrapText,
  normalizeDungeonName: normalizeDungeonName,
  buildDungeonArtMap: buildDungeonArtMap,
  lookupDungeonArt: lookupDungeonArt,
  buildRaidPrepOneSheet: buildRaidPrepOneSheet,
  buildBisSetPoster: buildBisSetPoster,
  buildAdventurePoster: buildAdventurePoster,
  paginatePoster: paginatePoster
}
