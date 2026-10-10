#!/usr/bin/env node
/* 把 upstream/wclbox-legacy.json 整形成 src/data/legacy.json —— 传承（Legacy）模块的数据基底。

   口径（2026-10-10 定，和改动清单同一把尺子）：
   - 只留名称、坐标、前置、点数、上限、图标文件名与规则数值；
     专长的每层效果说明、常见问题、领取说明这些别人转述的句子，抓取阶段就已经删了，这里也不会补回来。
   - 专长名与奖励名标 L0：它们是客户端里的游戏内中文名（经第三方站转述），按 2026-10-08 的决策算 L0 支撑，
     但每条都带 url + 抓取日期，并且由 tools/audit-translations.py 逐字回查。
   - 挑战记录标 L2：完成条件出自客户端解包，没进游戏一项项打过。
   - 树上 27 个槽位里只有 21 个有明细，另外 6 个官方还没公布——槽位留着并标"未公开"，不猜名字。
*/
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'src', 'data');
const UP = path.join(ROOT, 'upstream', 'wclbox-legacy.json');
const TREE_ID = { professions: 'crafting', adventure: 'adventure', resourcefulness: 'resource' };
const TREE_CN = { crafting: '专业', adventure: '冒险', resource: '资源' };

const raw = JSON.parse(fs.readFileSync(UP, 'utf8'));
const m = raw.meta || {};
const baseProv = [
  { type: 'datamine_cn', url: m.source,
    note: '传承页（无限测试版客户端解包，经新手盒子转述）；每层效果说明本站不复制',
    checkedAt: m.fetchedAt },
  { type: 'datamine_cn', url: m.endpoint,
    note: '本页渲染用的记录，名称、槽位坐标、前置与点数以此为准',
    checkedAt: m.fetchedAt }
];

function treeIdOf(t) {
  const slug = String(t.portrait || '').replace(/^\/chuancheng-tu\/portrait-/, '').replace(/\.jpg$/, '');
  return TREE_ID[slug] || slug || '';
}
// 上游在 structure.prerequisite 里写的是英文专长名（如 Bartering），转成我们的 perk id
function slugToId(en) {
  const s = String(en || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return s ? 'legacy-perk-' + s : null;
}

const byId = {};
raw.perks.forEach((p) => { byId[p.id] = p; });
// 上游给的是中文系名，我们存语义 id，两边都要能对上
const TREE_BY_CN = {};
Object.keys(TREE_CN).forEach((k) => { TREE_BY_CN[TREE_CN[k]] = k; });
function treeIdByCn(cn) { return TREE_BY_CN[cn] || ''; }

const trees = (raw.trees || []).map((t) => {
  const id = treeIdOf(t);
  const rows = {}, cols = {};
  (t.nodes || []).forEach((n) => { rows[n.row] = 1; cols[n.col] = 1; });
  const h = Math.max.apply(null, Object.keys(rows).map(Number)) + 1;
  const w = Math.max.apply(null, Object.keys(cols).map(Number)) + 1;
  const slots = [];
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      const n = (t.nodes || []).filter((x) => x.row === r && x.col === c)[0];
      if (!n) { slots.push({ row: r, col: c, perk: null, empty: true }); continue; }
      // 未公开的那 6 个槽位只有 id（unknown-<数字>），没有 perk 字段
      const ref = n.perk || n.id || '';
      const known = !!byId[ref];
      slots.push({ row: r, col: c, perk: ref, empty: false, unknown: !known });
    }
  }
  return {
    id, nameCn: TREE_CN[id] || t.name || '', nameUpstream: t.name || '',
    rows: h, cols: w, slots,
    links: (t.links || []).map((l) => ({ from: l[0], to: l[1] })),
    level: 'L0', provenance: baseProv
  };
});

const perks = (raw.perks || []).map((p) => {
  const prereq = slugToId((p.structure || {}).prerequisite);
  const treeId = treeIdByCn(p.tree_name);
  return {
    id: p.id, nameCn: p.name, treeId: treeId, treeCn: p.tree_name || '',
    row: (p.structure || {}).tier, col: (p.structure || {}).col,
    maxRank: p.max_rank === undefined ? null : p.max_rank,
    iconKey: p.icon || null,
    prerequisite: prereq || null,
    prerequisiteCn: prereq && byId[prereq] ? byId[prereq].name : null,
    discoveredAt: p.discovered_at || null,
    evidenceStatus: p.evidence_status || null,
    level: 'L0', provenance: baseProv
  };
});

const unknownSlots = [];
trees.forEach((t) => t.slots.forEach((s) => {
  if (s.unknown) unknownSlots.push({ treeId: t.id, treeCn: t.nameCn, row: s.row, col: s.col, id: s.perk });
}));

const challenges = (raw.challenges || []).map((c) => ({
  id: c.name, nameCn: c.name, subcategories: c.subcategories || [],
  items: (c.items || []).map((x) => ({
    id: x.id, nameCn: x.name, requirement: x.requirement || null,
    sub: x.sub || null, group: x.group || null, iconKey: x.icon || null,
    points: x.points === undefined ? null : x.points,
    level: 'L2', provenance: baseProv
  }))
}));

const rewards = (raw.rewards || []).map((r) => ({
  at: r.at, nameCn: r.name || r.item_name || '', itemId: r.item || null,
  iconKey: r.icon || null, level: 'L2', provenance: baseProv
}));

const rules = raw.rules || {};
const cm = raw.challengeMeta || {};
const out = {
  meta: {
    kind: 'legacy',
    generatedAt: new Date().toISOString().slice(0, 10),
    method: 'tools/scrape-wclbox-legacy.py 抓 → tools/merge-legacy.js 整形；数据真相在 upstream/',
    source: m.source, endpoint: m.endpoint, build: m.build, clientBuild: m.clientBuild,
    upstreamUpdatedAt: m.upstreamUpdatedAt, fetchedAt: m.fetchedAt,
    textPolicy: '只留名称与数值结构。每个专长的每层效果说明、常见问题与领取说明都是别人转述的文本，' +
      '本站不存也不显示；要看逐字效果请去来源页。',
    rules: {
      pointPerChallenge: rules.point_per_challenge === undefined ? null : rules.point_per_challenge,
      launchSpendingCap: rules.launch_spending_cap === undefined ? null : rules.launch_spending_cap,
      launchEarnableTotal: rules.launch_earnable_total === undefined ? null : rules.launch_earnable_total,
      unlock: cm.unlock || null
    },
    counts: {
      perks: perks.length,
      // 格子是矩形（4×4），"槽位"只数真放了专长的位置
      slots: trees.reduce((a, t) => a + t.slots.filter((x) => !x.empty).length, 0),
      unknownSlots: unknownSlots.length,
      challenges: challenges.reduce((a, c) => a + c.items.length, 0),
      upstreamChallengeTotal: cm.total === undefined ? null : cm.total,
      rewards: rewards.length
    },
    notCollected: [
      '每个专长各层的具体效果数值：那是客户端说明文本由别人转述的内容，本站红线不复制，等官方中文稿或游戏内实测',
      '未公开的 6 个专长槽位里是什么：客户端的树里只有位置，名字与效果都还没放出',
      '传承点数的分配建议与"先点什么最划算"：属攻略性质，不做',
      '挑战的完成进度与账号级状态：要登录与个人数据，类目不允许'
    ],
    provenance: baseProv
  },
  trees: trees, perks: perks, unknownSlots: unknownSlots,
  challenges: challenges, rewards: rewards
};

const n = out.meta.counts;
fs.writeFileSync(path.join(ROOT, 'legacy.json'), JSON.stringify(out, null, 1) + '\n');
console.log('传承 → src/data/legacy.json：专长 ' + n.perks + ' / 槽位 ' + n.slots +
  '（未公开 ' + n.unknownSlots + '）/ 挑战 ' + n.challenges +
  '（上游自报 ' + n.upstreamChallengeTotal + '）/ 进度奖励 ' + n.rewards +
  '｜规则：每挑战 ' + out.meta.rules.pointPerChallenge + ' 点，首发上限 ' +
  out.meta.rules.launchSpendingCap + ' 点，可得合计 ' + out.meta.rules.launchEarnableTotal + ' 点');
