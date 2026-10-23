#!/usr/bin/env node
/* 把 upstream/wclbox-legacy.json 整形成 src/data/legacy.json —— 传承（Legacy）模块的数据基底。

   口径（2026-10-10 定，和改动清单同一把尺子）：
   - 只留名称、坐标、前置、点数、上限、图标文件名与规则数值；
     专长的每层效果说明、常见问题、领取说明这些别人转述的句子，抓取阶段就已经删了，这里也不会补回来。
   - 专长名与奖励名标 L0：它们是客户端里的游戏内中文名（经第三方站转述），按 2026-10-08 的决策算 L0 支撑，
     但每条都带 url + 抓取日期，并且由 tools/audit-translations.py 逐字回查。
   - 挑战记录标 L2：完成条件出自客户端解包，没进游戏一项项打过。
   - 树上 27 个槽位里只有 21 个有明细，另外 6 个官方还没公布——槽位留着并标"未公开"，不猜名字。

   2026-10-23 这一版加三件事（客户端 1.60.1.70338 → 1.60.1.70532，站主指令"保留旧值、来源和核对日期"）：
   - **本树门槛进成品**：上游 trees[].nodes[].spent 取值 0/5/10，原来在整形这一步被丢掉了。
     语义已核（见下面 gateNote）：它不是 maxRank、也不是示例加点，是"这一格要本树先投入 N 点"。
   - **常规挑战与测试参与记录分账**：官方页写"傳承挑戰總共有六十五項…每完成一項就會獲得一點傳承點數"，
     而客户端条目是 66 条、合计 81 点——多出来的那条正是客户端标 16 点的"参与过 Beta 测试"。
     所以按"每条 1 点"划出常规 65 条，特殊那条单独标 special，不并进常规分母。
   - **值变了不覆盖**：改名、改条件、挪格子这些变化，旧值连同它出自哪个客户端版本、哪天核对的，
     一律追加进该条目的 history，重跑不重复追加。
*/
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'src', 'data');
const UP = path.join(ROOT, 'upstream', 'wclbox-legacy.json');
const OUT = path.join(ROOT, 'legacy.json');
const TREE_ID = { professions: 'crafting', adventure: 'adventure', resourcefulness: 'resource' };
const TREE_CN = { crafting: '专业', adventure: '冒险', resource: '资源' };
/* 官方繁中那篇三棵树叫「專業技能 / 冒險 / 精明」。前两个与我们的写法是同一个词的字形/后缀差，
   第三个「精明」对「资源」是另一个词——只把真分歧记进 nameAlt，不把字形差冒充成分歧。 */
const TREE_ALT = { resource: '精明' };
/* 官方《无限》传承系统说明（繁中页与英文页同一篇）——65 项、每项 1 点、单角色上限 16 点、
   开放条件三条途径，这四件事只有这篇能撑，第三方转述页给的是另一套说法。 */
const OFFICIAL = {
  zhTw: 'https://worldofwarcraft.blizzard.com/zh-tw/news/24307383',
  en: 'https://worldofwarcraft.blizzard.com/en-us/news/24307383',
  checkedAt: '2026-10-23'
};
const OFFICIAL_COUNTS = { 职业: 27, 商业技能: 18, 玩家对战: 12, 冒险: 2, 地下城: 3, 团队副本: 3 };
const GATE_VALUES = [0, 5, 10];

const raw = JSON.parse(fs.readFileSync(UP, 'utf8'));
const m = raw.meta || {};
const prev = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : null;
const prevMeta = (prev || {}).meta || {};
const prevClientBuild = prevMeta.clientBuild || null;
const prevCheckedAt = prevMeta.fetchedAt || null;
const baseProv = [
  { type: 'datamine_cn', url: m.source,
    note: '传承页（无限测试版客户端解包，经新手盒子转述）；每层效果说明本站不复制',
    checkedAt: m.fetchedAt },
  { type: 'datamine_cn', url: m.endpoint,
    note: '本页渲染用的记录，名称、槽位坐标、前置与点数以此为准',
    checkedAt: m.fetchedAt }
];
const officialProv = [
  { type: 'official_cn', url: OFFICIAL.zhTw,
    note: '官方繁中《无限》传承系统说明：挑战总数 65 项、每项 1 点、单角色最多 16 点、开放条件',
    checkedAt: OFFICIAL.checkedAt },
  { type: 'official_en', url: OFFICIAL.en, note: '同一篇的英文原页，用来对繁中的数字与条件',
    checkedAt: OFFICIAL.checkedAt }
];

/* 旧值留档：把变化记成 {field, from, atClientBuild, checkedAt}，重跑时先带上原有的再追加。 */
function historyOf(kind, key, next, fields) {
  const bucket = kind === 'perk' ? prevPerks : kind === 'challenge' ? prevChallenges : prevTrees;
  const p = bucket[key];
  const keep = ((p || {}).history || []).map((h) => h);
  if (!p) return keep.length ? keep : null;
  fields.forEach((f) => {
    const a = p[f], b = next[f];
    if (a === undefined || b === undefined || JSON.stringify(a) === JSON.stringify(b)) return;
    keep.push({ field: f, from: a, atClientBuild: prevClientBuild, checkedAt: prevCheckedAt });
  });
  return keep.length ? keep : null;
}
const prevPerks = {}, prevChallenges = {}, prevTrees = {};
if (prev) {
  (prev.perks || []).forEach((p) => { prevPerks[p.id] = p; });
  (prev.challenges || []).forEach((c) => {
    (c.items || []).forEach((i) => { prevChallenges[String(i.id)] = i; });
  });
  (prev.trees || []).forEach((t) => { prevTrees[t.id] = t; });
}

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

/* 上游 trees[].nodes[].spent 是"这一格要本树先投入几点"。语义怎么定的（2026-10-23 逐格核过）：
   ① 它不等于 maxRank——"以物易物"上限 2 格却写 5；② 它不是示例加点，6 个未公开槽根本没这个字段；
   ③ 每棵树里 spent=0 的那几格 maxRank 加起来恰好是 10，也就是刚好够点开唯一那格 spent=10
   （三棵树都是 maxRank=1 的最深格，且都带前置）。三条一起看，只能是"本树已投入点数门槛"。 */
const nodeGate = {};
(raw.trees || []).forEach((t) => (t.nodes || []).forEach((n) => {
  const ref = n.perk || n.id || '';
  if (n.spent === undefined) { nodeGate[ref] = null; return; }
  if (GATE_VALUES.indexOf(n.spent) < 0) throw new Error('上游门槛出现没见过的取值：' + ref + ' = ' + n.spent);
  nodeGate[ref] = n.spent;
}));

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
      slots.push({ row: r, col: c, perk: ref, empty: false, unknown: !known,
                   gate: known ? (nodeGate[ref] === undefined ? null : nodeGate[ref]) : null });
    }
  }
  const out = {
    id, nameCn: TREE_CN[id] || t.name || '', nameUpstream: t.name || '',
    rows: h, cols: w, slots,
    links: (t.links || []).map((l) => ({ from: l[0], to: l[1] })),
    level: 'L0', provenance: baseProv
  };
  // 官方繁中那篇给这一树起的名字与客户端解包出来的不是一个词（不只是繁简之别），两个都留
  if (TREE_ALT[id]) {
    out.nameAlt = [{ nameCn: TREE_ALT[id], from: 'official_zh_tw', url: OFFICIAL.zhTw,
                     checkedAt: OFFICIAL.checkedAt }];
    out.nameAltNote = '这一棵树客户端里叫「' + out.nameCn + '」，官方繁中那篇写作「' + TREE_ALT[id] +
      '」——不是繁简字形差，是另一个词。页面用哪个还没定，两个都先留着。';
  }
  const hist = historyOf('tree', id, out, ['nameCn', 'rows', 'cols']);
  if (hist) out.history = hist;
  return out;
});

const perks = (raw.perks || []).map((p) => {
  const prereq = slugToId((p.structure || {}).prerequisite);
  const treeId = treeIdByCn(p.tree_name);
  const out = {
    id: p.id, nameCn: p.name, treeId: treeId, treeCn: p.tree_name || '',
    row: (p.structure || {}).tier, col: (p.structure || {}).col,
    maxRank: p.max_rank === undefined ? null : p.max_rank,
    iconKey: p.icon || null,
    prerequisite: prereq || null,
    prerequisiteCn: prereq && byId[prereq] ? byId[prereq].name : null,
    // 本树要先投满几点才点得开这一格（上游节点字段叫 spent，语义见上面 nodeGate 那段注释）
    treePointsRequired: nodeGate[p.id] === undefined ? null : nodeGate[p.id],
    discoveredAt: p.discovered_at || null,
    evidenceStatus: p.evidence_status || null,
    level: 'L0', provenance: baseProv
  };
  const hist = historyOf('perk', p.id, out,
    ['nameCn', 'row', 'col', 'maxRank', 'treePointsRequired', 'prerequisite']);
  if (hist) out.history = hist;
  return out;
});

/* 同一份上游里"专长自己的坐标"与"树上的坐标"是两处写的（2026-10-23 对过：一致）。
   不一致就是上游自己飘了，别让它悄悄进成品。 */
const posErr = [];
(raw.trees || []).forEach((t) => (t.nodes || []).forEach((n) => {
  const p = byId[n.perk];
  if (!p) return;
  const s = p.structure || {};
  if (s.tier !== n.row || s.col !== n.col) {
    posErr.push(p.name + '：树上写 行' + n.row + ' 列' + n.col + '，专长自己写 行' + s.tier + ' 列' + s.col);
  }
}));
if (posErr.length) throw new Error('上游两处坐标对不上，先停下来核：' + posErr.join('；'));

const unknownSlots = [];
trees.forEach((t) => t.slots.forEach((s) => {
  if (s.unknown) unknownSlots.push({ treeId: t.id, treeCn: t.nameCn, row: s.row, col: s.col, id: s.perk });
}));

/* 上游有条目把"完成条件"和领取提示连写成一句（…即可获得此奖励。感谢你参与测试！）。
   本站只留条件那半截，两处都切：句号前、"即可获得此奖励"前——整句是别人页面上的表述，
   不是事实字段；原文记在 docs/DATA-传承页更新-2026-10-23.md 里。 */
const CLAIM_NOISE = ['。', '即可获得'];
function normRequirement(x) {
  const s = x.requirement || null;
  if (s === null) return { requirement: null, requirementNote: null };
  const at = CLAIM_NOISE.map((t) => s.indexOf(t)).filter((i) => i >= 0);
  if (!at.length) return { requirement: s, requirementNote: null };
  const cut = Math.min.apply(null, at);
  return { requirement: s.slice(0, cut),
    requirementNote: '这一条来源把完成条件与领取提示连写成了整句，本站只留条件那半截，整句不存也不显示。' };
}

const challenges = (raw.challenges || []).map((c) => ({
  id: c.name, nameCn: c.name, subcategories: c.subcategories || [],
  officialPoints: OFFICIAL_COUNTS[c.name] === undefined ? null : OFFICIAL_COUNTS[c.name],
  items: (c.items || []).map((x) => {
    const nr = normRequirement(x);
    const it = {
      id: x.id, nameCn: x.name, requirement: nr.requirement, requirementNote: nr.requirementNote,
      sub: x.sub || null, group: x.group || null, iconKey: x.icon || null,
      points: x.points === undefined ? null : x.points,
      special: null, level: 'L2', provenance: baseProv
    };
    const hist = historyOf('challenge', String(x.id), it, ['nameCn', 'requirement', 'points']);
    if (hist) it.history = hist;
    return it;
  })
}));

const rewards = (raw.rewards || []).map((r) => ({
  at: r.at, nameCn: r.name || r.item_name || '', itemId: r.item || null,
  iconKey: r.icon || null, level: 'L2', provenance: baseProv
}));

const rules = raw.rules || {};
const cm = raw.challengeMeta || {};
/* 每项挑战给几点：界面把它直接写成"每项 N 点"，所以它必须等于明细里的普遍值。
   1.60.1.70338 起客户端规则栏写 16，而 66 条明细里 65 条各写 1 点、只有"参与过测试"那条写 16
   （65 + 16 = 81，正好等于它自己给的合计）——两个说法冲突，这里都不静默改：
   界面用的取明细普遍值，客户端那个说法原样留在 rulesClientPointPerChallenge 里，
   冲突本身写进 rulesConflict，并在 pointVariants 里逐条声明，交给 build-data.js 拦"没声明的偏差"。 */
const chItems = challenges.reduce((a, c) => a.concat(c.items), []);
const chPointSum = chItems.reduce((a, x) => a + (Number(x.points) || 0), 0);
const pointTally = {};
chItems.forEach((x) => { pointTally[x.points] = (pointTally[x.points] || 0) + 1; });
const modalPoint = Object.keys(pointTally).sort((a, b) => pointTally[b] - pointTally[a])[0];
const pointVariants = Object.keys(pointTally).filter((k) => k !== modalPoint).map((k) => ({
  points: +k, count: pointTally[k], ids: chItems.filter((x) => String(x.points) === k).map((x) => String(x.id))
}));
/* 常规 / 特殊分账：官方那篇写"六十五項傳承挑戰，每完成一項獲得一點"，
   所以"每条 1 点"就是常规的定义，客户端明细里点数不是 1 的那条单独算特殊记录
   （现库正好是 65 条 1 点 + 1 条 16 点）。不写死 ID，也不把 16 点那条并进常规分母。 */
chItems.forEach((x) => { x.special = (+x.points !== +modalPoint); });
const regular = chItems.filter((x) => !x.special);
const specials = chItems.filter((x) => x.special);
const regularSum = regular.reduce((a, x) => a + (Number(x.points) || 0), 0);
/* 官方给的六个类别点数与我们的分组条数逐组对：对不上就是"多出来的那条在哪一组"变了，
   不能让它悄悄改掉 65 这个数。 */
const groupMismatch = challenges.filter((c) =>
  c.officialPoints !== null &&
  c.items.filter((x) => !x.special).length !== c.officialPoints).map((c) =>
  c.nameCn + '：本站常规 ' + c.items.filter((x) => !x.special).length + ' 条，官方页写 ' + c.officialPoints + ' 点');
if (groupMismatch.length) throw new Error('挑战分组与官方数对不上：' + groupMismatch.join('；'));
const officialTotal = Object.keys(OFFICIAL_COUNTS).reduce((a, k) => a + OFFICIAL_COUNTS[k], 0);
if (officialTotal !== regular.length) {
  throw new Error('官方六类合计 ' + officialTotal + ' 点，与本站常规挑战 ' + regular.length + ' 条不等');
}
/* 每项给几点，两个说法现在能并起来看清楚了：客户端那个字段名叫 point_per_challenge、值却是 16，
   而官方页的 16 是"每个角色最多花 16 点"——它本来就是上限，不是每项的点数。
   旧说法不删，原样留在 clientRulePointPerChallenge 与下面这段记录里。 */
const rulesConflict = ('每项挑战给多少点有过两个说法：客户端给的字段写 ' + rules.point_per_challenge +
  ' 点，明细里 ' + regular.length + ' 条各写 ' + modalPoint + ' 点' +
  (pointVariants.length ? '、' + pointVariants.map((v) => v.count + ' 条写 ' + v.points + ' 点').join('、') : '') +
  '。官方那篇说清楚了：每完成一项挑战获得一点传承点数，而 ' + rules.launch_spending_cap +
  ' 是每个角色最多能花的点数——客户端那个字段名叫每项点数，值其实是上限。' +
  '两个来源的原始值都留着，界面按每条自己的点数摆。');
const gateByTree = {};
trees.forEach((t) => {
  const v = {};
  t.slots.forEach((s) => { if (!s.empty && !s.unknown) v[s.gate] = (v[s.gate] || 0) + 1; });
  gateByTree[t.nameCn] = Object.keys(v).sort((a, b) => a - b).map((k) => k + ' 点门槛 ' + v[k] + ' 格');
});
const out = {
  meta: {
    kind: 'legacy',
    generatedAt: new Date().toISOString().slice(0, 10),
    method: 'tools/scrape-wclbox-legacy.py 抓 → tools/merge-legacy.js 整形；数据真相在 upstream/',
    source: m.source, endpoint: m.endpoint, build: m.build, clientBuild: m.clientBuild,
    upstreamUpdatedAt: m.upstreamUpdatedAt, fetchedAt: m.fetchedAt,
    /* 换过哪几个客户端版本、哪天取的，逐条留着——每条旧值自己的 history 记的就是它出自哪个版本。
       第一次跑这一步时旧版还没有这条轨迹，所以把上一版那一条也补进去（幂等：已存在就不重复加）。 */
    versionHistory: (function () {
      const list = (prevMeta.versionHistory || []).slice();
      [{ clientBuild: prevMeta.clientBuild, build: prevMeta.build, fetchedAt: prevMeta.fetchedAt },
       { clientBuild: m.clientBuild, build: m.build, fetchedAt: m.fetchedAt }].forEach((v) => {
        if (v.clientBuild && !list.some((x) => x.clientBuild === v.clientBuild)) list.push(v);
      });
      return list;
    })(),
    officialSource: { url: OFFICIAL.zhTw, urlEn: OFFICIAL.en, checkedAt: OFFICIAL.checkedAt,
      what: '挑战总数 65 项、每项 1 点、单角色最多 16 点、开放条件的三条途径、六个类别各自点数' },
    textPolicy: '只留名称与数值结构。每个专长的每层效果说明、常见问题与领取说明都是别人转述的文本，' +
      '本站不存也不显示；要看逐字效果请去来源页。',
    rules: {
      pointPerChallenge: modalPoint === undefined ? null : +modalPoint,
      pointPerChallengeSource: '官方《无限》传承系统说明：每完成一项挑战获得一点传承点数',
      pointVariants: pointVariants,
      clientRulePointPerChallenge: rules.point_per_challenge === undefined ? null : rules.point_per_challenge,
      rulesConflict: rulesConflict,
      launchSpendingCap: rules.launch_spending_cap === undefined ? null : rules.launch_spending_cap,
      launchSpendingCapSource: '官方那篇同一条：游戏推出时每个角色最多使用 16 点',
      launchEarnableTotal: rules.launch_earnable_total === undefined ? null : rules.launch_earnable_total,
      launchEarnableTotalNote: '客户端给的这个数是' + chItems.length + ' 条条目的点数合计（含那条 16 点的测试参与记录），' +
        '不是"人人可得 81 点"，也不是挑战条数。常规 ' + regular.length + ' 条各 1 点，合计 ' + regularSum + ' 点。',
      unlock: '首次拿到任意一点传承点数就开放；多数人是第一个角色到 25 级，' +
        '也可以用非采集类主专业练到 150、或把整张世界地图探完来拿到第一点。',
      unlockLevel: 'L0', unlockSource: OFFICIAL.zhTw, unlockCheckedAt: OFFICIAL.checkedAt,
      unlockUpstream: cm.unlock || null,
      unlockUpstreamNote: '转述页给的那句与官方那篇不一致（它只写 25 级这一条途径），原话留着不覆盖。',
      treePointGates: { values: GATE_VALUES, perTree: gateByTree,
        meaning: '这一格要本树先投满 N 点才点得开；0 就是入口格。取值只有 0/5/10 三种，' +
          '每棵树 0 门槛那几格的上限加起来正好 10 点，够点开唯一那格 10 门槛的。',
        evidenceStatus: 'client_data', level: 'L2',
        note: '门槛数字出自客户端解包，还没进游戏逐格点过，所以整条按 L2 留档。' }
    },
    counts: {
      perks: perks.length,
      slots: trees.reduce((a, t) => a + t.slots.filter((x) => !x.empty).length, 0),
      unknownSlots: unknownSlots.length,
      challenges: chItems.length,
      challengesRegular: regular.length,
      challengesSpecial: specials.length,
      specialIds: specials.map((x) => String(x.id)),
      challengePointsRegular: regularSum,
      challengePointSum: chPointSum,
      upstreamChallengeTotal: cm.total === undefined ? null : cm.total,
      officialChallengeTotal: officialTotal,
      rewards: rewards.length
    },
    notCollected: [
      '每个专长各层的具体效果数值：那是客户端说明文本由别人转述的内容，本站红线不复制，等官方中文稿或游戏内实测',
      '未公开的 6 个专长槽位里是什么：客户端的树里只有位置，名字与效果都还没放出',
      '传承点数的分配建议与"先点什么最划算"：属攻略性质，不做',
      '挑战的完成进度与账号级状态：要登录与个人数据，类目不允许',
      '那条 16 点的测试参与记录正式服还给不给、谁能领：官方那篇没提它，资格待核'
    ],
    provenance: baseProv.concat(officialProv)
  },
  trees: trees, perks: perks, unknownSlots: unknownSlots,
  challenges: challenges, rewards: rewards
};

const n = out.meta.counts;
fs.writeFileSync(OUT, JSON.stringify(out, null, 1) + '\n');
console.log('传承 → src/data/legacy.json：专长 ' + n.perks + ' / 槽位 ' + n.slots +
  '（未公开 ' + n.unknownSlots + '）/ 条目 ' + n.challenges + ' 条 = 常规 ' + n.challengesRegular +
  ' + 特殊 ' + n.challengesSpecial + '（' + n.specialIds.join('、') + '）' +
  '｜常规点数 ' + n.challengePointsRegular + ' 与官方六类合计 ' + n.officialChallengeTotal + ' 对上' +
  '，条目点数合计 ' + n.challengePointSum + '（客户端给的合计 ' + n.upstreamChallengeTotal + '）' +
  '｜进度奖励 ' + n.rewards + '｜门槛取值 ' + GATE_VALUES.join('/') +
  '｜客户端 ' + (prevClientBuild ? prevClientBuild + ' → ' : '') + m.clientBuild);
const changed = [].concat(perks.filter((p) => p.history), chItems.filter((x) => x.history),
  trees.filter((t) => t.history));
if (changed.length) {
  console.log('  本轮值有变的条目 ' + changed.length + ' 个（旧值留在各自 history 里，没覆盖）：');
  changed.forEach((x) => (x.history || []).forEach((h) => console.log('   ', x.id, h.field,
    JSON.stringify(h.from), '→', JSON.stringify(x[h.field]), '（旧值出自 ' + h.atClientBuild + '，' + h.checkedAt + ' 核对）')));
}
