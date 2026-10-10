#!/usr/bin/env node
/* 把 upstream/wclbox-dungeons.json 并进 src/data/dungeons.json。
 *
 * 规则：
 *  - 名单 / 等级区间 / BOSS / 掉落归属来自解包站（客户端数据转述），来源记 datamine_cn + 抓取日期。
 *  - 我们自己攒的官方来源、译名冲突、英文原名一律保留，不被解包站覆盖。
 *  - 掉落是它按经典旧世开放数据库推的（它自己也这么写），所以掉落记 L2 待实测，不升 L0，也不写百分比。
 *  - 它没有的条目（我们的 3 座团本）原样留着。
 *  - 客户端队伍查找器表（upstream/db2-group-finder.json，由 tools/fetch-db2-groupfinder.py 取回）
 *    在这里做第三方的对账：补英文原名、写进入人数上限、并列客户端的等级区间。
 *    对账一律**每次从这份表全量重算**，字段一致时写 null——不然改一次数据就永久留一层旧结论（重跑必须幂等）。
 *  - 对账结果另外落一份 src/data/queue.json：客户端里现在能排到、本站还没有名单的条目。
 *    它单独成文件，因为 tools/export-mini.js 会把整份 dungeons 原样打进小程序，
 *    混进去会让首页把座数虚报。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'src', 'data');
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const dg = read('dungeons.json');
const up = read('upstream/wclbox-dungeons.json');

// 上游 slug → 我们已有条目的 id（我们先用了自己的命名，改回去没必要，链接会断）
const ALIAS = {
  'the-deadmines': 'deathmine',
  'the-stockade': 'the-stocks',
  'razorfen-downs': 'razor-krendor',
  'excavation-site': 'whelgars-excavation'
};
// 我们那条聚合的"血色修道院"要拆成上游的四区
const RETIRE = { 'scarlet-monastery': true };
const SCARLET = ['scarlet-monastery-graveyard', 'scarlet-monastery-library',
  'scarlet-monastery-armory', 'scarlet-monastery-cathedral'];

const byId = {};
const byCn = {};
[].concat(dg.newDungeons, dg.classicDungeons).forEach((x) => {
  byId[x.id] = x;
  if (x.nameCn) byCn[x.nameCn] = x;
});

function provFor(row, d) {
  const url = up.meta.source + '/' + d.slug + '/';
  const list = [];
  if (row) list.push(...(row.provenance || []));
  list.push({
    type: 'datamine_cn', url,
    note: '名单/等级区间/BOSS 名取自无限客户端（经新手盒子转述）；本页抓取',
    checkedAt: up.meta.scrapedAt
  });
  return list;
}

function build(d) {
  const slug = d.slug;
  const mine = byId[ALIAS[slug] || slug] || byCn[d.nameCn];
  // 「小怪」不是首领名：上游 2026-10-10 的黑暗深渊名单里有一条就叫「小怪」，
  // 直接收进来会在副本页上出现一个假首领。
  const junk = (s) => !s || /^(小怪|精英怪|trash|other)$/i.test(String(s).trim());
  const upB = (d.bosses || []).filter((b) => !junk(b.nameCn));
  const mineB = (mine && mine.bosses) || [];
  // 上游删掉的有名首领不跟着删：我们没法进游戏数首领，删错了就是丢数据。
  // 保留原名单、追加上游新增的，并把差额报出来等人工核。
  const gone = mineB.filter((b) => !junk(b.nameCn) &&
    !upB.some((u) => u.id === b.id || u.nameCn === b.nameCn));
  const fresh = upB.filter((u) => !mineB.some((b) => b.id === u.id || b.nameCn === u.nameCn));
  const junkMine = mineB.filter((b) => junk(b.nameCn));
  if (junkMine.length) console.log('%s 去掉 %d 条不是首领名的行（%s）——我们自己以前的数据里也有',
    slug, junkMine.length, junkMine.map((b) => b.nameCn).join('、'));
  if (gone.length) {
    console.log('%s 上游名单少了 %d 个首领（保留我们已有的，等人工核）：%s',
      slug, gone.length, gone.map((b) => b.nameCn).join('、'));
  }
  if (fresh.length) console.log('%s 上游新增首领 %d 个：%s', slug, fresh.length,
    fresh.map((b) => b.nameCn).join('、'));
  const mk = (b) => ({
    id: b.id, nameCn: b.nameCn,
    level: (d.drops || []).some((x) => x.bossId === b.id) ? 'L0' : 'L2',
    // 这句是玩家看到的，不能写「上游标了：」（禁词卡口会红，2026-10-10 实测：
    // 重跑副本线就把这句带回过数据里）。上游原话是「开放数据库里还没有它的掉落。」，
    // 意思一样，这里用站得住的说法写死，不整句转述别人的话。
    note: (d.drops || []).some((x) => x.bossId === b.id) ? null : '公开数据库里还没有它的掉落记录。'
  });
  const bosses = upB.map(mk).concat(gone.map((b) => ({
    id: b.id, nameCn: b.nameCn, level: b.level || 'L2',
    note: (d.drops || []).some((x) => x.bossId === b.id) ? null : b.note || '公开数据库里还没有它的掉落记录。'
  })));
  const drops = (d.drops || []).map((x) => ({
    itemId: x.itemId, nameCn: x.nameCn, iconKey: x.iconKey || null, quality: x.quality === undefined ? null : x.quality,
    bossId: x.bossId, bossCn: x.bossCn,
    level: 'L2'
  }));
  const row = {
    id: mine ? mine.id : slug,
    // 这条链接是为了让后面的卡片信息与客户端对账能找到同一条：我们的 id 与它的 slug 不同名
    upstreamSlug: slug,
    nameCn: (mine && mine.nameCn) || d.nameCn,
    // 上一轮由客户端表补出来的英文名不当成"我们原有的名字"，每轮重算
    nameEn: (mine && mine.nameEnFrom !== 'db2' && mine.nameEn) || null,
    nameCnConflict: mine ? mine.nameCnConflict : null,
    kind: d.isNew ? 'new' : 'classic',
    levelRange: (mine && mine.levelRange) || d.levelRange || null,
    bosses, route: (mine && mine.route) || [],
    drops,
    lootNote: drops.length ? (d.lootSourceNote || null) : null,
    level: 'L0',
    provenance: provFor(mine, d)
  };
  if (mine && mine.provenance && mine.provenance.some((p) => (p.type || '').indexOf('official') === 0)) {
    row.officialBacked = true;
  }
  if (mine) {
    // 官方中文/英文来源排在前面，界面上"来源"先看到权威的
    row.provenance = (mine.provenance || []).concat(row.provenance.filter(
      (p) => !(mine.provenance || []).some((q) => q.url === p.url && q.type === p.type)));
  }
  return row;
}

const merged = up.dungeons.map(build);
const kept = [].concat(dg.newDungeons, dg.classicDungeons).filter((x) => {
  if (RETIRE[x.id]) return false;
  return !merged.some((m) => m.id === x.id);
});
if (kept.length) console.log('上游没有、我们原有的条目保留：' + kept.map((x) => x.id).join('、'));

const isNew = (x) => x.kind === 'new';
dg.newDungeons = merged.filter(isNew);
dg.classicDungeons = merged.filter((x) => !isNew(x)).concat(kept.filter((x) => !isNew(x)));
dg.meta = dg.meta || {};
// 这句会写进数据、玩家看得到：不能出现「上游」这类维护者措辞（禁词卡口管），
// 也不点名厂商。改文案要连这里一起改，只改 JSON 的话下次重跑副本线就被盖回去。
dg.meta.lootDisclaimer = '掉落是按经典旧世公开数据库推出来的，官方说过无限服重做过掉落，'
  + '正式开放可能变化——所以掉落一律标待实测，本站不写百分比。';
dg.meta.upstream = { site: up.meta.site, source: up.meta.source, scrapedAt: up.meta.scrapedAt };

const cardsPath = path.join(ROOT, 'upstream', 'wclbox-cards.json');
if (fs.existsSync(cardsPath)) {
  const cards = JSON.parse(fs.readFileSync(cardsPath, 'utf8'));
  const bySlug = {};
  (cards.cards || []).forEach((c) => { bySlug[c.slug] = c; });
  const artIdx = JSON.parse(fs.readFileSync(path.join(ROOT, 'art.json'), 'utf8')).dungeons || {};
  let z = 0;
  [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).forEach((d) => {
    // 以前这里只按我们的 id 找卡片，四座不同名的（死亡矿井 / 监狱 / 剃刀高地 / 湿地挖掘场）
    // 一直没有所在区域、卡片计数与载入图——2026-10-10 实测补上
    const c = bySlug[d.upstreamSlug || d.id] || bySlug[d.id];
    if (!c) return;
    if (c.zone) { d.zoneCn = c.zone; z += 1; }
    if (c.range) {
      const up = String(c.range).replace(/[–—~]/g, '-').replace(/[^0-9-]/g, '').replace(/-+/g, '-');
      if (d.levelRange && d.levelRange !== up) d.levelRangeAlt = up;
      else if (!d.levelRange) d.levelRange = up;
    }
    d.cardCounts = { bosses: c.bosses || null, drops: c.drops || null };
    d.art = artIdx[d.id] || null;
  });
  console.log('卡片信息：补上所在区域 %d 条', z);
}

/* ---------- 排队元数据包（_shuju/<发布号>/dungeons.json）：补阵营与所在区域 ---------- */
const metaPath = path.join(ROOT, 'upstream', 'wclbox-dungeon-meta.json');
if (fs.existsSync(metaPath)) {
  const dm = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
  const bySlug2 = {};
  (dm.dungeons || []).forEach((r) => { bySlug2[r.id] = r; });
  let fac = 0, zone = 0, stateDiff = 0;
  [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).forEach((d) => {
    const r = bySlug2[d.upstreamSlug || d.id];
    if (!r) return;
    // 阵营原来只混在「丹莫罗，铁炉堡地下 · 联盟」这种字符串里，没法拿来分组
    d.faction = r.faction || null;
    if (r.faction) fac += 1;
    if (!d.zoneCn && r.zone) {
      d.zoneCn = r.zone + (r.faction ? ' · ' + r.faction : '');
      zone += 1;
    }
    if (r.status && d.kind && r.status !== d.kind) {
      stateDiff += 1;
      console.log('%s 是不是无限新增，两份资料说法不同（本站记 %s / 它记 %s）——先不动，人工核',
        d.id, d.kind, r.status);
    }
  });
  console.log('排队元数据包：写上阵营 %d 座 / 补上所在区域 %d 座 / 新增说法不一致 %d 座',
    fac, zone, stateDiff);
} else {
  console.log('没有 upstream/wclbox-dungeon-meta.json（先跑 scrape-wclbox-shuju.py --group dungeons），本轮不补阵营');
}

/* ---------- 客户端队伍查找器表：英文原名 / 人数上限 / 等级区间对账 ---------- */
const DB2_PATH = path.join(ROOT, 'upstream', 'db2-group-finder.json');
const norm = (s) => String(s || '').toLowerCase()
  .replace(/['`’´]/g, '')            // 客户端名里的撇号不算分隔符：Zul'Farrak 与 zulfarrak 是同一条
  .replace(/[^a-z0-9]+/g, '-')
  .replace(/^the-/, '')
  .replace(/^-+|-+$/g, '');
// 我们的 id 与客户端英文原名对不上的四条。这只是"怎么找到同一条"的连接提示，
// 不是替它们改名——真正显示什么，由下面的规则决定。
const EN_ALIAS = {
  deathmine: 'deadmines',                            // 客户端写 Deadmines，我们最早用了 deathmine
  'the-stocks': 'stormwind-stockades',               // 客户端写 Stormwind Stockades
  'razor-krendor': 'razorfen-downs',                 // 参考站给过 The Razor Krendor，客户端写 Razorfen Downs
  'whelgars-excavation': 'excavation-site-wetlands'  // 官方回顾写 Whelgar's Excavation，客户端写 Excavation Site: Wetlands
};
const QUEUE_KIND = { Dungeons: 'dungeon', Raids: 'raid' };

function buildQueue(data) {
  if (!data) return null;
  const all = [].concat(dg.newDungeons, dg.classicDungeons, dg.raids);
  const rows = (data.activities || []).filter((a) => QUEUE_KIND[a.categoryName]);
  // 按活动号排序再去重：同一座团本在表里有两行，不排序的话每次重跑 diff 都在漂
  rows.sort((a, b) => a.activityId - b.activityId);
  const byName = {};
  rows.forEach((a) => { const k = norm(a.nameEn); (byName[k] = byName[k] || []).push(a); });
  const ownName = (d) => (d.nameEnFrom === 'db2' ? null : d.nameEn) || null;
  const findRows = (d) => {
    const keys = [];
    if (EN_ALIAS[d.id]) keys.push(EN_ALIAS[d.id]);
    if (ownName(d)) keys.push(norm(ownName(d)));
    keys.push(norm(d.id));
    for (let i = 0; i < keys.length; i += 1) if (byName[keys[i]]) return byName[keys[i]];
    return [];
  };
  const checked = data.meta.fetchedAt;
  const srcUrl = data.meta.url;
  // 用到这份表的条目都要挂上它的出处，不能只在 queue.json 里记一次——
  // 界面上"来源"点开的是这座本自己的来源清单
  const prov = {
    type: 'datamine_en', url: srcUrl,
    note: '客户端版本 ' + data.meta.build + ' 的队伍查找器：英文原名、等级与人数上限'
      + '（经第三方客户端数据站取回）',
    checkedAt: checked
  };
  const matched = {};
  const st = { nameEn: 0, party: 0, range: 0, nameDiff: 0, noQueue: 0, sizeAlt: 0 };

  all.forEach((d) => {
    const hits = findRows(d);
    // 主数取「地下城」类那行；同一座另有的团队类条目只当分歧，不当成新的一座本
    const main = hits.filter((r) => r.categoryName === 'Dungeons')[0] || hits[0] || null;
    hits.forEach((r) => { matched[r.activityId] = d.id; });
    const own = ownName(d);
    d.nameEn = own;                        // 每轮从这份表重算，不带上一轮的补值
    d.nameEnFrom = own ? null : (main ? 'db2' : null);
    d.clientActivityId = main ? main.activityId : null;
    d.partySize = main ? main.maxPlayers : null;
    d.partySizeAlt = null;
    d.clientAltIds = null;
    d.levelRangeClient = null;
    d.nameEnClient = null;
    if (!main) { st.noQueue += 1; return; }
    d.provenance = d.provenance || [];
    if (!d.provenance.some((p) => p.type === prov.type && p.url === prov.url)) d.provenance.push(prov);
    if (!own) { d.nameEn = main.nameEn || null; if (d.nameEn) st.nameEn += 1; }
    else if (norm(own) !== norm(main.nameEn)) { d.nameEnClient = main.nameEn; st.nameDiff += 1; }
    const cli = main.minLevel + '-' + main.maxLevel;
    const ours = d.levelRange ? String(d.levelRange).replace(/[–—~]/g, '-') : null;
    if (ours !== cli) { d.levelRangeClient = cli; st.range += 1; }
    const sizes = [];
    hits.forEach((r) => { if (r.maxPlayers && sizes.indexOf(r.maxPlayers) < 0) sizes.push(r.maxPlayers); });
    if (sizes.length > 1) {
      d.partySizeAlt = sizes.filter((v) => v !== d.partySize)[0] || null;
      if (d.partySizeAlt) st.sizeAlt += 1;
    }
    // 同一座在表里不止一条时，其余活动号也记下来：两份文件互相能认，卡口才对得上账
    const others = [];
    hits.forEach((r) => { if (r !== main && others.indexOf(r.activityId) < 0) others.push(r.activityId); });
    d.clientAltIds = others.length ? others.sort((a, b) => a - b) : null;
    if (d.partySize) st.party += 1;
  });

  const items = rows.map((r) => ({
    activityId: r.activityId,
    nameEn: r.nameEn,
    kind: QUEUE_KIND[r.categoryName],
    categoryName: r.categoryName,
    levelRange: r.minLevel + '-' + r.maxLevel,
    partySize: r.maxPlayers || null,
    mapId: r.mapId === undefined ? null : r.mapId,
    matchedId: matched[r.activityId] || null,
    level: 'L1',
    provenance: [prov]
  }));
  console.log('客户端排队表：补英文名 %d 座 / 写人数上限 %d 座 / 等级区间另有一说 %d 座 / '
      + '英文名另有一说 %d 座 / 同一座有两种人数 %d 座 / 表里还没有排队条目 %d 座',
    st.nameEn, st.party, st.range, st.nameDiff, st.sizeAlt, st.noQueue);
  return {
    meta: {
      generatedAt: checked,
      build: data.meta.build,
      source: data.meta.url,
      note: '这一份是客户端队伍查找器里现在的排队条目，不是本站的副本名单。'
        + '没对上本站的那几条，是「客户端能排到、本站还没有首领与掉落名单」的：'
        + '英文名取自客户端，中文定名还没公布，正式开放前可能变化。',
      categories: ['Dungeons', 'Raids'],
      counts: { total: items.length, unlisted: items.filter((i) => !i.matchedId).length }
    },
    items: items
  };
}

const db2 = fs.existsSync(DB2_PATH) ? JSON.parse(fs.readFileSync(DB2_PATH, 'utf8')) : null;
const queueOut = buildQueue(db2);
if (queueOut) {
  fs.writeFileSync(path.join(ROOT, 'queue.json'), JSON.stringify(queueOut, null, 1) + '\n');
  console.log('已写 queue.json：排队条目 %d 条，其中本站还没有名单 %d 条',
    queueOut.meta.counts.total, queueOut.meta.counts.unlisted);
} else {
  console.log('没有 upstream/db2-group-finder.json（先跑 tools/fetch-db2-groupfinder.py），本轮不做客户端排队表对账');
}

fs.writeFileSync(path.join(ROOT, 'dungeons.json'), JSON.stringify(dg, null, 1) + '\n');
const cnt = (a) => a.reduce((s, x) => s + (x.bosses || []).length, 0);
console.log('已写 dungeons.json：新本 %d / 经典本 %d / 团本 %d，BOSS 共 %d 个，掉落条目 %d 条',
  dg.newDungeons.length, dg.classicDungeons.length, dg.raids.length,
  cnt(dg.newDungeons) + cnt(dg.classicDungeons) + cnt(dg.raids),
  [].concat(dg.newDungeons, dg.classicDungeons).reduce((s, x) => s + (x.drops || []).length, 0));
console.log('其中 %d 座带官方来源支撑，%d 座只有客户端解包转述',
  merged.filter((x) => x.officialBacked).length, merged.filter((x) => !x.officialBacked).length);
