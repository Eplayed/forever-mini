#!/usr/bin/env node
/* 把 upstream/wclbox-world.json 整形成 src/data/world.json（世界线：区域 / 稀有精英 / 书籍 / 睡袋）。
 *
 * 这一步只做形状与口径，不做加工：
 *  - 只留事实性标识符：中文名、英文 key、等级区间、阵营、areaId/mapId、坐标、图标文件名、物品 ID；
 *  - 上游 JSON 里的书本正文（book.text）、营地路线讲解（stops 的 steps/landmarks/rewards）一律不进；
 *  - 坐标有两个来源可以互相验：地图 paint 的 areaId→mapId，和稀有/书籍分组自带的 id，不一致就报警。
 *  - 小地图只在本地图存在时才写 mapFile，页面据此决定贴图还是纯文字坐标。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'src', 'data');
const up = JSON.parse(fs.readFileSync(path.join(ROOT, 'upstream', 'wclbox-world.json'), 'utf8'));
const art = JSON.parse(fs.readFileSync(path.join(ROOT, 'art.json'), 'utf8'));
const MAP_IMG = art.maps || {};

const SRC = up.meta.source || 'https://wowforever.wclbox.com/ditu';
const PAGE = {
  rare: 'https://wowforever.wclbox.com/xiyou',
  book: 'https://wowforever.wclbox.com/shuji',
  bag: 'https://wowforever.wclbox.com/shuidai',
  map: 'https://wowforever.wclbox.com/ditu'
};
const SIDE = { a: '联盟', h: '部落', c: '争夺地带' };
const SIDE_OF = { 联盟: 'a', 部落: 'h', 争夺地带: 'c' };
const prov = (url, note) => [{ type: 'datamine_cn', url: url, note: note, checkedAt: up.meta.scrapedAt }];

const P = up.payload || {};
const zonesOf = P.zones || {};
const mapsBySlug = {};
(P.maps || []).forEach((m) => { mapsBySlug[m.slug] = m; });

/* ---------- 区域：等级与阵营来自 map-zones，mapId 来自大陆地图的 paint ---------- */
function areaToMapId(slug) {
  const out = {};
  ((mapsBySlug[slug] || {}).paint || []).forEach((x) => {
    if (typeof x.areaId === 'number' && typeof x.file === 'string' && /\.webp$/.test(x.file)) {
      out[x.areaId] = String(x.file).split('.')[0];
    }
  });
  return out;
}
// 稀有与书籍分组自带 mapId，用来和 paint 交叉验证
const idByName = {};
(P.xiyou ? P.xiyou.zones || [] : []).concat(P.shuji ? P.shuji.zones || [] : [])
  .forEach((g) => { if (g.name && g.id) idByName[g.name] = String(g.id); });

const CONTINENTS = [
  { id: 'ek', nameCn: '东部王国', slug: 'eastern-kingdoms' },
  { id: 'kal', nameCn: '卡利姆多', slug: 'kalimdor' }
];
const rareCountByZone = {}, bookCountByZone = {};
((P.xiyou || {}).where || []).forEach((w) => { rareCountByZone[w.zone] = w.count; });
((P.shuji || {}).zones || []).forEach((g) => { bookCountByZone[g.name] = (g.books || []).length; });

const mismatches = [];
/* 上游"怎样去新区域"那份清单：给区域打"无限新增"标，并补进大陆表里没有的区域。
   注意河林／海加尔山／辛德拉本来就在大陆区域表里（只是没给等级），不能重复建两行。 */
const ownMapNames = {};
(P.maps || []).forEach((m) => { ownMapNames[m.name] = m.slug; });
const reachBy = {};
((P.reach || {}).items || []).forEach((r) => {
  const lv = r.lv ? String(r.lv).replace(/[\u2013\u2014~]/g, '-').split('-').map((x) => parseInt(x, 10)) : null;
  reachBy[r.name] = {
    lv: lv && lv.length === 2 && !isNaN(lv[0]) ? lv : null,
    faction: r.faction || null,
    ownMap: !!ownMapNames[r.name], ownMapSlug: ownMapNames[r.name] || null,
    // 上游给的 sub 是它自己写的路线讲解，本站不搬；只保留"有没有飞行路线"这个可核实状态
    flight: /还没有通往这里的飞行路线/.test(r.sub || '') ? 'no-route'
      : /^飞行：/.test(r.sub || '') ? 'by-flight' : null
  };
});
function ranged(lo, hi) {
  const a = typeof lo === 'number' ? lo : null, b = typeof hi === 'number' ? hi : null;
  return {
    levelRange: [a, b],
    levelStatus: a !== null && b !== null ? 'ok' : '客户端暂时没给出区域等级'
  };
}
const zones = [];
CONTINENTS.forEach((c) => {
  const p = areaToMapId(c.slug);
  (zonesOf[c.slug] || []).forEach((z) => {
    const byPaint = p[z.area] || null;
    const byGroup = idByName[z.name] || null;
    if (byPaint && byGroup && byPaint !== byGroup) mismatches.push(z.name + '（paint ' + byPaint + ' / 分组 ' + byGroup + '）');
    const mapId = byPaint || byGroup || null;
    const r = reachBy[z.name] || null;
    zones.push(Object.assign({
      id: z.slug, level: 'L0',
      nameCn: z.name, slug: z.slug, continent: c.id, continentCn: c.nameCn,
      faction: z.faction || (r ? r.faction : null),
      side: SIDE_OF[z.faction] || (r ? SIDE_OF[r.faction] : null),
      isNew: !!r, ownMap: r ? r.ownMap : false, flight: r ? r.flight : null,
      flightNote: r ? '飞行路线的存在性取自上游，具体站点待实测' : null,
      areaId: typeof z.area === 'number' ? z.area : null,
      mapId: mapId,
      mapFile: mapId && MAP_IMG[mapId] ? MAP_IMG[mapId] : null,
      rareCount: rareCountByZone[z.name] || 0,
      bookCount: bookCountByZone[z.name] || 0,
      levelNote: '等级与阵营同一条上游记录，两处在用的表没有冲突',
      provenance: prov(SRC, '区域等级区间与阵营来自无限客户端地图数据（经新手盒子转述）')
    }, ranged(z.min, z.max)));
  });
});
// 大陆表里没有、只出现在新区域清单里的（泽风岛：客户端给它单独一张地图）
const inTable = {};
zones.forEach((z) => { inTable[z.nameCn] = true; });
Object.keys(reachBy).forEach((name) => {
  if (inTable[name]) return;
  const r = reachBy[name], mapId = idByName[name] || null;
  zones.push(Object.assign({
    id: r.ownMapSlug || name, level: 'L0',
    nameCn: name, slug: r.ownMapSlug || null, continent: 'new', continentCn: '无限新增',
    faction: r.faction, side: SIDE_OF[r.faction] || null,
    isNew: true, ownMap: r.ownMap, flight: r.flight,
    flightNote: '飞行路线的存在性取自上游，具体站点待实测',
    areaId: null, mapId: mapId,
    mapFile: mapId && MAP_IMG[mapId] ? MAP_IMG[mapId] : null,
    rareCount: rareCountByZone[name] || 0, bookCount: bookCountByZone[name] || 0,
    levelNote: '客户端单独给了这张地图，不在东部王国／卡利姆多的区域表里',
    provenance: prov(PAGE.map, '新增区域的存在、阵营归属与等级档（经新手盒子转述）')
  }, ranged(r.lv ? r.lv[0] : null, r.lv ? r.lv[1] : null)));
});
const ORDER = { ek: 0, kal: 1, new: 2 };
zones.sort((a, b) => {
  if (a.continent !== b.continent) return ORDER[a.continent] - ORDER[b.continent];
  const la = a.levelRange[0], lb = b.levelRange[0];
  if (la === null && lb === null) return a.nameCn < b.nameCn ? -1 : 1;
  if (la === null) return 1;
  if (lb === null) return -1;
  return la - lb;
});

/* ---------- 客户端地图清单 ---------- */
const maps = (P.maps || []).map((m) => ({
  slug: m.slug, mapId: String(m.id), nameCn: m.name, group: m.group || null,
  placeCount: typeof m.places === 'number' ? m.places : null,
  painted: typeof m.painted === 'number' ? m.painted : null,
  isNew: m.group === '无限新增',
  zoneNames: m.zones || []
}));

/* ---------- 坐标解析 ---------- */
function worldFromHref(href) {
  const m = /[?#&]x=([\d.]+)&y=([\d.]+)&z=(\d+)/.exec(href || '');
  return m ? { x: Number(m[1]), y: Number(m[2]), z: Number(m[3]) } : null;
}
function mapSlugFromHref(href) {
  const m = /^\/ditu\/([a-z0-9-]+)/.exec(href || '');
  return m ? m[1] : null;
}

/* ---------- 物品：只留 ID / 名称 / 品质 / 图标键 / 物品等级 / 绑定与需求等级 ---------- */
function itemOf(it) {
  if (!it) return null;
  const lines = it.x || [];
  const bind = lines.filter((l) => /绑定$/.test(l))[0] || null;
  const req = lines.map((l) => /需要等级\s*(\d+)/.exec(l)).filter(Boolean)[0];
  return {
    itemId: it.id, nameCn: it.n, quality: typeof it.q === 'number' ? it.q : null,
    iconKey: it.k || null, itemLevel: typeof it.l === 'number' ? it.l : null,
    bind: bind, reqLevel: req ? Number(req[1]) : null
  };
}

/* ---------- 稀有精英：22 个带掉落的 + 9 个区域内卡片，合计 36 ---------- */
const rares = [];
((P.xiyou || {}).hunts || []).forEach((h) => {
  const c = (h.coords || [])[0] || {};
  const world = worldFromHref(c.map);
  const mf = (h.map || {}).img ? String((h.map || {}).img).split('/').pop().split('.')[0] : null;
  rares.push({
    id: h.key || h.name, level: 'L0',
    nameCn: h.name, nameEn: h.key || null, zone: h.zone, kind: h.kind === 'rare-elite' ? 'rare-elite' : 'rare',
    isNew: !!h.new, levelRange: h.level && h.level[0] === h.level[1] ? [h.level[0]] : (h.level || null),
    mapId: mf || null, mapFile: mf && MAP_IMG[mf] ? MAP_IMG[mf] : null,
    mark: typeof c.x === 'number' ? { x: c.x, y: c.y } : null,
    world: world, mapSlug: mapSlugFromHref(c.map),
    drops: (h.drops || []).map((d) => itemOf(d.item)).filter(Boolean),
    provenance: prov(PAGE.rare, '稀有名称、等级、刷新点坐标与掉落归属（客户端解包，经新手盒子转述）')
  });
});
((P.xiyou || {}).zones || []).forEach((g) => {
  const gworld = worldFromHref(g.map);
  (g.cards || []).forEach((c) => {
    const cc = (c.coords || [])[0] || {};
    rares.push({
      id: c.key || c.name, level: 'L0',
      nameCn: c.name, nameEn: c.key || null, zone: g.name, kind: c.kind === 'rare-elite' ? 'rare-elite' : 'rare',
      isNew: !!c.new, levelRange: g.level || null,
      mapId: g.mapId ? String(g.mapId) : null,
      mapFile: g.mapId && MAP_IMG[String(g.mapId)] ? MAP_IMG[String(g.mapId)] : null,
      mark: typeof cc.x === 'number' ? { x: cc.x, y: cc.y } : (typeof c.x === 'number' ? { x: c.x, y: c.y } : null),
      world: worldFromHref(cc.map) || gworld, mapSlug: mapSlugFromHref(cc.map || g.map),
      drops: [],
      provenance: prov(PAGE.rare, '稀有名称与刷新点坐标（客户端解包，经新手盒子转述）；掉落未采到')
    });
  });
});
const rareRegions = ((P.xiyou || {}).where || []).map((w) => ({
  zone: w.zone, count: w.count, levelRange: w.level || null, side: SIDE[w.side] ? w.side : null,
  faction: SIDE[w.side] || null,
  mapId: w.anchor && /^zone-\d+$/.test(w.anchor) ? w.anchor.split('-')[1] : null
}));
const rareSets = ((P.xiyou || {}).sets || []).map((s) => ({
  nameCn: s.name, known: !!s.known,
  pieces: (s.pieces || []).map((p) => {
    const it = itemOf(p.item) || {};
    it.fromRare = p.name || null;
    return it;
  })
}));
const raresUnplaced = ((P.xiyou || {}).unplaced || []).map((n) => ({ nameCn: n }));

/* ---------- 书籍：29 个带坐标 + 7 个满级后的 + 2 个只有名字的 ---------- */
// 大陆区域表里没有"铁炉堡"这类主城，但客户端给它单独一张地图，得单独标 zoneKind，
// 否则卡口会把"区域名对不上"当成数据错误。
const continentZoneNames = {};
zones.forEach((z) => { continentZoneNames[z.nameCn] = true; });
const books = [];
(P.shuji ? P.shuji.zones || [] : []).forEach((g) => {
  (g.books || []).forEach((b) => {
    const w = worldFromHref(b.map);
    books.push({
      id: b.key || b.name, level: 'L0',
      nameCn: b.name, nameEn: b.key || null, itemId: b.item || null, iconKey: b.icon || null,
      container: b.container || null, zone: g.name, continent: g.group === 'ek' ? 'ek' : g.group === 'kal' ? 'kal' : null,
      place: null, mark: typeof b.x === 'number' ? { x: b.x, y: b.y } : null, world: w,
      mapId: g.id ? String(g.id) : null, mapFile: g.id && MAP_IMG[String(g.id)] ? MAP_IMG[String(g.id)] : null,
      zoneKind: continentZoneNames[g.name] ? 'zone' : 'city', forever: false, placed: true,
      provenance: prov(PAGE.book, '书名、所在容器与坐标（客户端解包，经新手盒子转述）；书本正文不搬')
    });
  });
});
(P.shuji ? P.shuji.more || [] : []).forEach((grp) => {
  (grp.books || []).forEach((b) => {
    books.push({
      id: b.key || b.name, level: 'L0',
      nameCn: b.name, nameEn: b.key || null, itemId: b.item || null, iconKey: b.icon || null,
      container: b.container || null, zone: b.zone || null, continent: null, place: b.place || null,
      mark: typeof b.x === 'number' ? { x: b.x, y: b.y } : null, world: null,
      mapId: b.mapId ? String(b.mapId) : null,
      mapFile: b.mapId && MAP_IMG[String(b.mapId)] ? MAP_IMG[String(b.mapId)] : null,
      zoneKind: continentZoneNames[b.zone] ? 'zone' : 'city',
      forever: !!b.forever, placed: true, afterLevel: grp.level || null,
      provenance: prov(PAGE.book, '满级后新增书籍的名称、容器与坐标（客户端解包，经新手盒子转述）')
    });
  });
});
const booksMissing = (P.shuji ? P.shuji.missing || [] : []).map((b) => ({
  nameCn: b.name, nameEn: b.key || null, itemId: b.item || null, iconKey: b.icon || null, placed: false,
  provenance: prov(PAGE.book, '上游只给出书名与物品 ID，没给坐标')
}));
const bookRewards = ((P.shuji || {}).rewards || []).map((r) => ({
  books: r.books, title: r.title, questId: r.quest || null, level: typeof r.level === 'number' ? r.level : null,
  items: (r.items || []).map(itemOf).filter(Boolean),
  // 上游这一档只给了门槛和任务 ID，没列奖励物品：写清楚，界面显示"待实测"而不是留白
  noReward: !(r.items || []).length,
  noRewardNote: (r.items || []).length ? null : '上游只给出上交门槛与任务 ID，奖励物品未采集',
  provenance: prov(PAGE.book, '上交数量门槛、称号与奖励物品 ID（客户端解包，经新手盒子转述）')
}));
const librarians = ((P.shuji || {}).librarians || []).map((l) => ({
  nameCn: l.name, side: l.side, faction: SIDE[l.side] || null, quarter: l.quarter || null, city: l.city || null,
  mark: typeof l.x === 'number' ? { x: l.x, y: l.y } : null,
  provenance: prov(PAGE.book, '管理员名字与所在城市（客户端解包，经新手盒子转述）')
}));

/* ---------- 睡袋：只留物品、机制数值与地点，路线讲解不搬 ---------- */
const sd = P.shuidai || {};
const bagItem = itemOf((sd.items || {})['211527']);
const camps = (sd.stops || []).map((st) => ({
  stop: st.id,
  places: (st.places || []).map((p) => {
    const pin = (p.pins || [])[0] || {};
    const inset = p.inset && p.inset.img ? String(p.inset.img).split('/').pop().split('.')[0] : null;
    return {
      zone: p.zone || null, whereCn: p.sub || null, landmark: pin.label || null,
      mark: typeof pin.left === 'number' ? { x: pin.left, y: pin.top } : null,
      world: worldFromHref(p.map), mapSlug: mapSlugFromHref(p.map),
      mapId: inset, mapFile: inset && MAP_IMG[inset] ? MAP_IMG[inset] : null,
      provenance: prov(PAGE.bag, '营地点所在区域与坐标（客户端解包，经新手盒子转述）')
    };
  })
}));
const bagTool = {
  usableLevel: typeof sd.level === 'number' ? sd.level : null,
  bag: bagItem,
  params: sd.bag ? {
    castSec: sd.bag.cast, lastsMin: sd.bag.lasts, cdMin: sd.bag.cd, buffName: sd.bag.buff || null,
    stacks: sd.bag.stacks, buffHours: sd.bag.buffSec ? Math.round(sd.bag.buffSec / 3600) : null
  } : null,
  paramsLevel: 'L2',
  paramsNote: '机制数值取自上游对物品说明的解析，本站没有游戏内实测过；具体收益以游戏内为准',
  camps: camps
};

const payload = {
  meta: {
    generatedAt: up.meta.scrapedAt,
    kind: 'client-datamine',
    method: 'tools/scrape-wclbox-shuju.py 抓 _shuju 数据包 → tools/merge-world.js 整形',
    release: up.meta.release, foreverBuild: up.meta.foreverBuild, dropsAsOf: up.meta.dropsAsOf,
    sources: [
      { url: PAGE.map, label: '新手盒子 · 魔兽世界无限数据库 世界地图' },
      { url: PAGE.rare, label: '新手盒子 · 稀有精英' },
      { url: PAGE.book, label: '新手盒子 · 图书馆书籍' },
      { url: PAGE.bag, label: '新手盒子 · 舒适的睡袋' }
    ],
    took: '区域等级与阵营、mapId 与区域坐标、稀有精英位置与掉落归属、书籍容器与坐标、睡袋物品与营地点',
    skipped: '上游的书本正文、营地路线讲解与步骤、任何攻略性建议、任何百分比概率',
    notCollected: [
      '世界地图底图与可缩放交互：那是上游自己切的 1715 张瓦片，本站不搬图也不做交互地图，只给区域清单与坐标',
      '睡袋页面的冲级路线（步骤、途经点顺序、收益讲解）：属攻略性质，本站红线不做，只保留地点与坐标',
      '睡袋相关的 17 件杂物清单：上游把路线补给品混在一张表里，拆不出干净的物品口径',
      '成就：上游已经放出 46 条结构化数据，本轮没接，属于另一个模块',
      '区域人口、天气、稀有刷新计时：客户端里没有这类字段，编不出来'
    ],
    levelNote: '本文件全部字段是无限客户端解包出来的游戏内中文（经第三方站转述），按 2026-10-08 决策记 L0；未经游戏内实测的部分单列',
    mapNote: '小地图只转存上游真的切出来的那些：上游没给的区域显示 mapId 与坐标，不放假图',
    coordinateNote: '坐标两套并存：mapId 定位到具体那张图，mark 是图上百分比，world 是客户端世界坐标；三者都来自同一次解包',
    mapIdMismatch: mismatches
  },
  continents: CONTINENTS.map((c) => ({
    id: c.id, nameCn: c.nameCn, slug: c.slug,
    mapId: mapsBySlug[c.slug] ? String(mapsBySlug[c.slug].id) : null,
    zoneCount: (zonesOf[c.slug] || []).length
  })),
  zones: zones,
  maps: maps,
  rareRegions: rareRegions,
  rares: rares,
  rareSets: rareSets,
  raresUnplaced: raresUnplaced,
  books: books,
  booksMissing: booksMissing,
  bookRewards: bookRewards,
  librarians: librarians,
  bagTool: bagTool,
  provenance: prov(SRC, '世界线整块数据取自无限客户端解包（经新手盒子转述），本页只做形状与口径')
};
// 上游没切出小地图的区域：写进 meta，界面据此说明"为什么这块是空的"
payload.meta.mapsWithoutImage = zones.filter((z) => z.mapId && !z.mapFile).map((z) => z.nameCn);

fs.writeFileSync(path.join(ROOT, 'world.json'), JSON.stringify(payload, null, 1) + '\n');
const has = (k) => payload[k].length;
console.log('区域 %d（%s）· 其中无限新增 %d · 客户端地图 %d',
  has('zones'), payload.continents.map((c) => c.nameCn + ' ' + c.zoneCount).join(' / '),
  zones.filter((z) => z.isNew).length, has('maps'));
console.log('稀有精英 %d（带掉落 %d，贴图 %d）· 未定位 %d · 套装 %d 组',
  has('rares'), payload.rares.filter((r) => r.drops.length).length,
  payload.rares.filter((r) => r.mapFile).length, has('raresUnplaced'), has('rareSets'));
console.log('书籍 %d（未定位 %d）· 奖励 %d 档 · 管理员 %d · 营地 %d 处 %d 个地点 · 睡袋物品 %s',
  has('books'), has('booksMissing'), has('bookRewards'), has('librarians'),
  camps.length, camps.reduce((n, c) => n + c.places.length, 0),
  bagItem ? bagItem.nameCn + '（#' + bagItem.itemId + '）' : '没解析出来');
if (mismatches.length) console.log('!! mapId 两套来源不一致：%s', mismatches.join('、'));
