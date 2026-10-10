#!/usr/bin/env node
/* 把 upstream/wclbox-dungeons.json 并进 src/data/dungeons.json。
 *
 * 规则：
 *  - 名单 / 等级区间 / BOSS / 掉落归属来自上游（客户端解包转述），来源记 datamine_cn + 抓取日期。
 *  - 我们自己攒的官方来源、译名冲突、英文原名一律保留，不被上游覆盖。
 *  - 掉落是上游按经典旧世开放数据库推的（它自己也这么写），所以掉落记 L2 待实测，不升 L0，也不写百分比。
 *  - 上游没有的条目（我们的 3 座团本）原样留着。
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
  'razorfen-downs': 'razor-krendor'
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
  const bosses = (d.bosses || []).map((b, i) => ({
    id: b.id, nameCn: b.nameCn,
    level: (d.drops || []).some((x) => x.bossId === b.id) ? 'L0' : 'L2',
    // 这句是玩家看到的，不能写「上游标了：」（禁词卡口会红，2026-10-10 实测：
    // 重跑副本线就把这句带回过数据里）。上游原话是「开放数据库里还没有它的掉落。」，
    // 意思一样，这里用站得住的说法写死，不整句转述别人的话。
    note: (d.drops || []).some((x) => x.bossId === b.id) ? null : '公开数据库里还没有它的掉落记录。'
  }));
  const drops = (d.drops || []).map((x) => ({
    itemId: x.itemId, nameCn: x.nameCn, iconKey: x.iconKey || null, quality: x.quality === undefined ? null : x.quality,
    bossId: x.bossId, bossCn: x.bossCn,
    level: 'L2'
  }));
  const row = {
    id: mine ? mine.id : slug,
    nameCn: (mine && mine.nameCn) || d.nameCn,
    nameEn: (mine && mine.nameEn) || null,
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
    const c = bySlug[d.id];
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

fs.writeFileSync(path.join(ROOT, 'dungeons.json'), JSON.stringify(dg, null, 1) + '\n');
const cnt = (a) => a.reduce((s, x) => s + (x.bosses || []).length, 0);
console.log('已写 dungeons.json：新本 %d / 经典本 %d / 团本 %d，BOSS 共 %d 个，掉落条目 %d 条',
  dg.newDungeons.length, dg.classicDungeons.length, dg.raids.length,
  cnt(dg.newDungeons) + cnt(dg.classicDungeons) + cnt(dg.raids),
  [].concat(dg.newDungeons, dg.classicDungeons).reduce((s, x) => s + (x.drops || []).length, 0));
console.log('其中 %d 座带官方来源支撑，%d 座只有客户端解包转述',
  merged.filter((x) => x.officialBacked).length, merged.filter((x) => !x.officialBacked).length);
