#!/usr/bin/env node
/* 把 upstream/wclbox-dungeons.json 并进 app/data/dungeons.json。
 *
 * 规则：
 *  - 名单 / 等级区间 / BOSS / 掉落归属来自解包站（客户端数据转述），来源记 datamine_cn + 抓取日期。
 *  - 我们自己攒的官方来源、译名冲突、英文原名一律保留，不被解包站覆盖。
 *  - 掉落是它按经典旧世开放数据库推的（它自己也这么写），所以掉落记 L2 待实测，不升 L0，也不写百分比。
 *  - 它没有的条目（我们的 3 座团本）原样留着。
 *  - 客户端队伍查找器表（upstream/db2-group-finder.json，由 tools/fetch-db2-groupfinder.py 取回）
 *    在这里做第三方的对账：补英文原名、写进入人数上限、并列客户端的等级区间。
 *    对账一律**每次从这份表全量重算**，字段一致时写 null——不然改一次数据就永久留一层旧结论（重跑必须幂等）。
 *  - 对账结果另外落一份 app/data/queue.json：客户端里现在能排到、本站还没有名单的条目。
 *    它单独成文件，因为 tools/export-mini.js 会把整份 dungeons 原样打进小程序，
 *    混进去会让首页把座数虚报。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'app', 'data');
const IMG = path.resolve(ROOT, '..', 'img');
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const dg = read('dungeons.json');
const up = read('upstream/wclbox-dungeons.json');
const thanesLootPath = 'upstream/hall-of-thanes-loot.json';
const thanesLoot = fs.existsSync(path.join(ROOT, thanesLootPath)) ? read(thanesLootPath) : null;
const thanesAliases = thanesLoot ? thanesLoot.bosses.flatMap((b) => b.aliases || []) : [];
const foreverLootPath = 'upstream/df-forever-boss-loot.json';
const foreverLoot = fs.existsSync(path.join(ROOT, foreverLootPath)) ? read(foreverLootPath) : null;
const foreverById = new Map((foreverLoot ? foreverLoot.dungeons : []).map((d) => [d.id, d.bosses]));

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
  const refreshed = foreverById.get(mine ? mine.id : slug) || [];
  const retired = new Set(refreshed.flatMap((b) => (b.aliases || []).map((a) => a.bossId)
    .concat(b.match === 'new' ? [b.bossId] : [])));
  if (thanesLoot && slug === thanesLoot.dungeonId) thanesAliases.forEach((a) => retired.add(a.bossId));
  const mineB = ((mine && mine.bosses) || []).filter((b) => !retired.has(b.id));
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
    // 定稿前那个数（官方公告）要一轮一轮往下带：不带的话第二次重跑就把留档洗掉了，
    // 而界面上已经只显示定稿值，等于"记录了但决定不告诉你"。下面定稿那一段负责写它。
    levelRangeOfficial: (mine && mine.levelRangeOfficial) || null,
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

/* ---------- 第三家首领名单（DungeonsForever 的掉落表）：只补我们缺的，我们有的不删 ---------- */
// 快照由 tools/extract-df-loot.py 落在 upstream/df-dungeon-loot.json。
// 为什么并进这个文件而不是另起一个脚本去改 dungeons.json：本文件每轮从 upstream 整表重算，
// 补在外面的首领下一轮就被冲掉了——专业线栽过同一个坑（见 tools/refresh.sh 的 prof 那段注释）。
// DF 的 300 行里有 41 行没有 npcId（小兵 / 图纸 / 战利品这类分组占位），那不是首领，一条都不收。
const DF_PATH = path.join(ROOT, 'upstream', 'df-dungeon-loot.json');
if (fs.existsSync(DF_PATH)) {
  const dfsnap = JSON.parse(fs.readFileSync(DF_PATH, 'utf8'));
  const byOurId = {};
  (dfsnap.dungeons || []).forEach((x) => { byOurId[x.id] = x; });
  const prov = {
    type: 'addon',
    url: 'DungeonsForever ' + (dfsnap.meta.addonVersion || '版本未记') + ' 的 Core/Data/Data_DungeonLoot.lua',
    note: '第三份首领名单，由插件整理，本站没有逐条进游戏数过；它没有的首领本站不删',
    checkedAt: dfsnap.meta.fetched
  };
  // 与 build() 里那条同一个判断，另加 DF 常用的三种占位名
  const notBoss = (s) => !s || /^(小怪|小兵|精英怪|图纸|战利品|trash|other)$/i.test(String(s).trim());
  const slugOf = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  let added = 0, touched = 0;
  const diffs = [];
  [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).forEach((d) => {
    const src = byOurId[d.id];
    if (!src) return;
    d.bosses = d.bosses || [];
    const real = (src.bosses || []).filter((b) => b.npcId !== null && !notBoss(b.nameCn));
    const refreshedAliases = (foreverById.get(d.id) || []).flatMap((b) => b.aliases || []);
    const fresh = real.filter((b) => !refreshedAliases.some((a) => a.nameCn === b.nameCn)
      && !d.bosses.some((x) => x.nameCn === b.nameCn ||
      (b.nameEn && x.nameEn && x.nameEn === b.nameEn)) &&
      (!thanesLoot || d.id !== thanesLoot.dungeonId || !thanesAliases.some((a) => a.nameCn === b.nameCn)));
    fresh.forEach((b) => {
      const base = slugOf(b.nameEn) || ('rare-' + b.npcId);
      let id = base, k = 2;
      while (d.bosses.some((x) => x.id === id)) id = base + '-' + (k++);
      d.bosses.push({
        id, nameCn: b.nameCn, nameEn: b.nameEn || null, npcId: b.npcId,
        level: 'L1', from: 'df',
        note: '这份名单由插件整理，本站没进游戏逐条核对，也还没有它的掉落记录。'
      });
      added += 1;
    });
    if (fresh.length) {
      touched += 1;
      d.provenance = (d.provenance || []).filter((p) => !(p.type === prov.type && p.url === prov.url))
        .concat([prov]);
    }
    const ours = d.bosses.length;
    if (ours - fresh.length !== real.length) diffs.push([d.id, d.nameCn, ours - fresh.length, real.length]);
  });
  dg.meta.bossRosterThirdSource = {
    addon: 'DungeonsForever', addonVersion: dfsnap.meta.addonVersion || null,
    sourceStamp: dfsnap.meta.sourceStamp || null, checkedAt: dfsnap.meta.fetched,
    addedBossRows: added, dungeonsTouched: touched, countDiff: diffs,
    note: '只补本站缺的首领，本站已有而它没有的一条不删；补进来的每条带 L1 与来源，掉落不写百分比'
  };
  console.log('第三家首领名单（DF 掉落表）：补进 %d 条首领，涉及 %d 座；两边条数不同（只补不删）%d 座',
    added, touched, diffs.length);
  if (diffs.length) {
    console.log('  本站 / DF 逐座不同的：%s', diffs.slice(0, 8).map((x) => `${x[1] || x[0]} ${x[2]}:${x[3]}`).join('、')
      + (diffs.length > 8 ? ` …共 ${diffs.length} 座` : ''));
  }
} else {
  console.log('没有 upstream/df-dungeon-loot.json（先跑 tools/extract-df-loot.py），本轮不并第三家首领名单');
}

const cardsPath = path.join(ROOT, 'upstream', 'wclbox-cards.json');
if (fs.existsSync(cardsPath)) {
  const cards = JSON.parse(fs.readFileSync(cardsPath, 'utf8'));
  const bySlug = {};
  (cards.cards || []).forEach((c) => { bySlug[c.slug] = c; });
  const artIdx = JSON.parse(fs.readFileSync(path.join(ROOT, 'art.json'), 'utf8')).dungeons || {};
  let z = 0;
  [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).forEach((d) => {
    // 载入图先挂：团本不在卡片列表里（卡片只有 35 座地下城），以前 return 得太早，
    // 结果奥妮克希亚的巢穴明明转存到了本地却一直挂不上，团本页整列都是空的
    d.art = artIdx[d.id] || null;
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
  });
  console.log('卡片信息：补上所在区域 %d 条', z);
}

/* ---------- 首领头像：把 art.json 的 bosses 索引按首领 id 挂到每条首领上 ---------- */
// 只有源站页面上真的摆着这张脸的才挂得上来（146/228），剩下的 portrait 为 null，
// 界面退回自绘方块——不拿别的种族或别的本的脸凑。
try {
  const bossArt = JSON.parse(fs.readFileSync(path.join(ROOT, 'art.json'), 'utf8')).bosses || {};
  const renderedPath = path.join(IMG, 'art/bosses-m2/manifest.json');
  const rendered = fs.existsSync(renderedPath) ? JSON.parse(fs.readFileSync(renderedPath, 'utf8')).portraits : {};
  let n = 0, tot = 0;
  [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).forEach((d) => {
    (d.bosses || []).forEach((b) => {
      tot += 1;
      const model = rendered[b.id];
      const modelFile = 'art/bosses-m2/' + b.id + '.webp';
      b.portrait = bossArt[b.id] || null;
      if (!b.portrait && b.id !== 'infurnus' && model && model.dungeon === d.id
        && fs.existsSync(path.join(IMG, modelFile))) b.portrait = 'img/' + modelFile;
      if (b.portrait) n += 1;
    });
  });
  dg.meta.bossPortraits = { total: tot, withPortrait: n,
    note: '客户端遭遇战手册头像，经第三方站转存在本地 img/art/bosses/；源站自己标"没有这张脸"的首领留空',
    manifest: 'app/img/art/manifest.json' };
  console.log('首领头像：%d / %d 挂上本地转存的脸，其余 %d 个源站也没有（界面留自绘占位）',
    n, tot, tot - n);
} catch (e) {
  console.log('首领头像：读不到 art.json，本轮不挂（%s）', e.message);
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
    // 同一张表的出处只留最新一次：url 里带 build 号，按整条 url 去重等于每重取一次就多挂一行
    // （10-10 与 10-11 两次重取已经让每座本同时挂着 70334 与 70338 两行同表出处，就是这个坑）。
    // 红线说的"两源分歧两个都留"指的是**不同来源**，不是同一张表的旧版本。
    const tableKey = (u) => String(u || '').replace(/[?&]build=[^&]*/, '');
    d.provenance = d.provenance.filter((p) =>
      !(p.type === prov.type && tableKey(p.url) === tableKey(prov.url)));
    d.provenance.push(prov);
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
    // 条目号：同一座在表里挂两条时，靠它说清是"两种规模"还是"两个入口"，不靠猜
    difficultyId: r.difficultyId === undefined ? null : r.difficultyId,
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

/* ---------- 等级区间按参考站的副本卡片定稿（2026-10-13 站主决定） ----------
   同一座本的等级区间以前有三个数在打架：官方公告（levelRange）、参考站的副本卡片
   （levelRangeAlt）、客户端的队伍查找器（levelRangeClient）。站主拍板：按参考站卡片上
   显示的那个数定稿，界面上不再摆"两说"（卡片与客户端在分歧的那几座上本来就是同一个数）。
   定稿不等于把另一个数扔掉——官方公告那个留在 levelRangeOfficial 里，出处与这条决定
   写在溯源页；客户端那个数只有在和定稿值不一致时才留着，那说明还没对上，不是旧说法。 */
const RANGE_SETTLED_AT = '2026-10-13';
let settled = 0, filled = 0;
[].concat(dg.newDungeons, dg.classicDungeons, dg.raids).forEach((d) => {
  const norm = (v) => (v ? String(v).replace(/[–—~]/g, '-') : null);
  const card = norm(d.levelRangeAlt);
  if (!card) {
    // 卡片没列这座本（团本就不在那 35 张卡里）：客户端有数而本站空着，就用客户端的补上
    if (!d.levelRange && d.levelRangeClient) {
      d.levelRange = norm(d.levelRangeClient);
      d.levelRangeClient = null;
      filled += 1;
    }
    return;
  }
  if (d.levelRange && d.levelRange !== card && !d.levelRangeOfficial) d.levelRangeOfficial = d.levelRange;
  d.levelRange = card;
  d.levelRangeAlt = null;
  if (norm(d.levelRangeClient) === card) d.levelRangeClient = null;
  settled += 1;
});
// 定稿之后这个键一律留着（值是 null）：不留的话第二次重跑因为"卡片与本站已经一样、
// 这一支根本没走到"而把键整个丢掉，JSON 少一行，重跑两次 md5 就对不上（幂等是硬要求）。
[].concat(dg.newDungeons, dg.classicDungeons, dg.raids).forEach((d) => {
  if (d.levelRangeAlt === undefined) d.levelRangeAlt = null;
});
dg.meta.levelRangeSettled = {
  at: RANGE_SETTLED_AT,
  by: '参考站 wowforever.wclbox.com 的副本卡片',
  url: 'https://wowforever.wclbox.com/fuben',
  note: '同一座本的等级区间以前有官方公告与参考站卡片两个数，2026-10-13 站主决定按参考站卡片定稿。'
    + '官方公告那个数没有删，还留在这座本的记录里（定稿前那个数），界面上只摆定稿后的那一个。'
};
if (settled || filled) {
  console.log('等级区间定稿：按参考站卡片改写 %d 座 / 用客户端数补上空值 %d 座', settled, filled);
}

/* 领主大厅的旧掉落表只有一件任务物品。用逐件对过 ID 的无限服资料补全，
   同一 NPC 的两种译名留在同一条首领记录，免得点到重复的空行。 */
if (thanesLoot) {
  const pack = thanesLoot;
  const dungeon = dg.newDungeons.find((d) => d.id === pack.dungeonId);
  if (!dungeon) throw new Error('找不到已核掉落所属的副本：' + pack.dungeonId);
  const portraitManifest = path.join(ROOT, '..', 'img', 'art', 'hall-of-thanes-bosses', 'manifest.json');
  const portraits = fs.existsSync(portraitManifest)
    ? JSON.parse(fs.readFileSync(portraitManifest, 'utf8')).files : {};
  pack.bosses.forEach(({ bossId, drops, aliases = [], ...facts }) => {
    const boss = dungeon.bosses.find((b) => b.id === bossId);
    if (!boss) throw new Error('找不到已核掉落所属的首领：' + bossId);
    const aliasIds = new Set(aliases.map((b) => b.bossId));
    dungeon.bosses = dungeon.bosses.filter((b) => !aliasIds.has(b.id));
    Object.assign(boss, facts, { note: null });
    if (aliases.length) boss.aliases = aliases;
    if (boss.id === 'infurnus' && boss.portrait === 'img/art/bosses-m2/infurnus.webp') boss.portrait = null;
    const portrait = portraits[bossId];
    if (portrait && portrait.origin === 'game-capture' && portrait.npcId === boss.npcId && portrait.encounterId === boss.encounterId) {
      boss.portrait = portrait.file;
    }
    dungeon.drops.forEach((x) => {
      if (aliasIds.has(x.bossId)) Object.assign(x, { bossId, bossCn: boss.nameCn });
    });
    drops.forEach((x) => {
      const existing = dungeon.drops.find((row) => row.bossId === bossId && String(row.itemId) === String(x.itemId));
      if (existing) Object.assign(existing, x);
      else dungeon.drops.push(Object.assign({}, x, { bossId, bossCn: boss.nameCn }));
    });
  });
  const lootSource = { type: 'fan_db', url: pack.sourceUrl, checkedAt: pack.checkedAt,
    note: '领主大厅首领掉落按无限服资料逐件核对归属，本站待实测' };
  dungeon.provenance = dungeon.provenance.filter((p) => p.url !== lootSource.url || p.type !== lootSource.type);
  dungeon.provenance.push(lootSource);
  dungeon.lootNote = '领主大厅的掉落按无限服公开资料及插件记录核对，本站待实测。';
}

if (foreverLoot) {
  const pack = foreverLoot;
  const items = new Map(read('items.json').items.map((item) => [String(item.id), item]));
  const dungeons = new Map([].concat(dg.newDungeons, dg.classicDungeons, dg.raids).map((d) => [d.id, d]));
  const source = { type: 'addon', url: pack.sourceUrl, checkedAt: pack.checkedAt,
    note: 'DungeonsForever 当前客户端版本的首领名单与掉落归属，本站待实测。旧表与未对齐条目留档。' };
  let updated = 0;
  let added = 0;
  for (const data of pack.dungeons) {
    const dungeon = dungeons.get(data.id);
    if (!dungeon || (data.id === 'hall-of-thanes' && thanesLoot)) continue;
    const touched = new Set();
    for (const row of data.bosses) {
      if (!row.bossId) continue;
      if (touched.has(row.bossId)) throw new Error('新版插件重复挂接首领：' + data.id + '/' + row.bossId);
      touched.add(row.bossId);
      let boss = dungeon.bosses.find((b) => b.id === row.bossId);
      if (!boss && row.match === 'new') {
        boss = { id: row.bossId, nameCn: row.nameCn, nameEn: row.nameEn, npcId: row.npcId,
          level: 'L2', note: '首领名单来自客户端插件，待实测。', portrait: null };
        dungeon.bosses.push(boss);
        added += 1;
      }
      if (!boss) throw new Error('新版插件未对上已核首领：' + data.id + '/' + row.bossId);
      const aliases = row.aliases || [];
      const ids = new Set([boss.id].concat(aliases.map((b) => b.bossId)));
      const names = new Set([boss.nameCn].concat(aliases.map((b) => b.nameCn)));
      if (aliases.length) {
        const portrait = dungeon.bosses.find((b) => ids.has(b.id) && b.portrait);
        if (!boss.portrait && portrait) boss.portrait = portrait.portrait;
        boss.aliases = aliases;
        dungeon.bosses = dungeon.bosses.filter((b) => b.id === boss.id || !ids.has(b.id));
      }
      dungeon.drops = (dungeon.drops || []).map((x) =>
        ids.has(x.bossId) || names.has(x.bossCn)
          ? Object.assign({}, x, { bossId: boss.id, bossCn: boss.nameCn }) : x);
      if (!row.itemIds.length) continue;
      const rows = row.itemIds.map((id) => items.get(String(id)));
      if (rows.some((item) => !item || !item.name)) throw new Error('新版插件的物品未入名录：' + data.id + '/' + row.bossId);
      dungeon.drops = dungeon.drops.filter((x) => x.bossId !== boss.id);
      for (const item of rows) {
        const iconKey = item.iconKey && fs.existsSync(path.join(IMG, 'icons', item.iconKey + '.jpg')) ? item.iconKey : null;
        dungeon.drops.push({ itemId: String(item.id), nameCn: item.name, iconKey,
          quality: item.quality ?? null, bossId: boss.id, bossCn: boss.nameCn, level: 'L2', from: 'df-forever' });
      }
      boss.note = null;
      updated += 1;
    }
    if (!touched.size) continue;
    dungeon.provenance = (dungeon.provenance || []).filter((p) => p.url !== source.url || p.type !== source.type);
    dungeon.provenance.push(source);
    if (dungeon.drops.length) dungeon.lootNote = '已对齐的首领使用无限服插件掉落记录，其他条目参考已有资料，本站待实测。';
  }
  dg.meta.lootDisclaimer = '掉落来自无限服插件与公开资料，均待实测，本站不写掉落几率。';
  console.log('新版插件掉落：更新 %d 位首领，补名单 %d 位', updated, added);
}

const captureManifest = path.join(IMG, 'art/bosses-game-capture/manifest.json');
if (fs.existsSync(captureManifest)) {
  const { files } = JSON.parse(fs.readFileSync(captureManifest, 'utf8'));
  for (const dungeon of [].concat(dg.newDungeons, dg.classicDungeons, dg.raids)) {
    for (const boss of dungeon.bosses) {
      const portrait = files[dungeon.id + '|' + boss.id];
      if (portrait && portrait.origin === 'game-capture') boss.portrait = portrait.file;
    }
  }
}

if (dg.meta.bossPortraits) {
  const bosses = [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).flatMap((d) => d.bosses);
  dg.meta.bossPortraits.total = bosses.length;
  dg.meta.bossPortraits.withPortrait = bosses.filter((b) => b.portrait).length;
  dg.meta.bossPortraits.note = '已登记的游戏原图、实录裁切与本机客户端模型渲染，未核头像留空。';
}

fs.writeFileSync(path.join(ROOT, 'dungeons.json'), JSON.stringify(dg, null, 1) + '\n');
const cnt = (a) => a.reduce((s, x) => s + (x.bosses || []).length, 0);
console.log('已写 dungeons.json：新本 %d / 经典本 %d / 团本 %d，BOSS 共 %d 个，掉落条目 %d 条',
  dg.newDungeons.length, dg.classicDungeons.length, dg.raids.length,
  cnt(dg.newDungeons) + cnt(dg.classicDungeons) + cnt(dg.raids),
  [].concat(dg.newDungeons, dg.classicDungeons).reduce((s, x) => s + (x.drops || []).length, 0));
console.log('其中 %d 座带官方来源支撑，%d 座只有客户端解包转述',
  merged.filter((x) => x.officialBacked).length, merged.filter((x) => !x.officialBacked).length);
