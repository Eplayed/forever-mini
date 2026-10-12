#!/usr/bin/env node
/* 把 upstream/wclbox-talent-<class>.json 并进 src/data/talents/<class>.json。
 *
 * 按"第几棵树 + 第几行 + 第几列"对齐，不按名字对齐：名字两边可能差一个字，
 * 位置才是天赋树的事实。对不上的两边都记下来，不静默丢。
 * 顺带从连线 SVG 还原前置关系、从"第 N 层 · 需在较低层投入 M 点"还原层级点数门槛。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'src', 'data');
const CLASSES = ['warrior', 'paladin', 'hunter', 'rogue', 'priest', 'shaman', 'mage', 'warlock', 'druid'];
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));
const write = (p, o) => fs.writeFileSync(path.join(ROOT, p), JSON.stringify(o, null, 1) + '\n');
const CELL = 54, HALF = 27;

function endpoints(d) {
  // 支持 M x y V y2 / H x2 / L x y 这类路径，取首尾坐标
  const m = /^M\s*([-\d.]+)[ ,]+([-\d.]+)/.exec(d);
  if (!m) return null;
  const start = { x: +m[1], y: +m[2] };
  let cur = { x: start.x, y: start.y };
  const re = /([VHLvh])\s*([-\d.]+)/g;
  let g;
  while ((g = re.exec(d))) {
    if (g[1] === 'V') cur.y = +g[2];
    else if (g[1] === 'H') cur.x = +g[2];
  }
  const last = /([-\d.]+)[ ,]+([-\d.]+)\s*$/.exec(d.replace(/[VH]\s*[-\d.]+\s*$/, (s) => {
    return '';
  }));
  return { a: start, b: cur };
}

function nearest(nodes, pt) {
  let best = null, bd = 1e9;
  nodes.forEach((n) => {
    const cx = (n.col - 1) * CELL + HALF, cy = (n.row - 1) * CELL + HALF;
    const d = Math.abs(cx - pt.x) + Math.abs(cy - pt.y);
    if (d < bd) { bd = d; best = n; }
  });
  return bd <= CELL ? best : null;
}

function tierCosts(refs) {
  const cost = {};
  refs.forEach((r) => {
    const c = r.condition || '';
    const tier = /第\s*(\d+)\s*层/.exec(c);
    const need = /投入\s*(\d+)\s*点/.exec(c);
    if (tier && need) cost[+tier[1] - 1] = Math.max(cost[+tier[1] - 1] || 0, +need[1]);
  });
  return cost;
}

/* 官方中文专精名（2026-10-12 逐页核过，只取"专精叫什么"这一个事实）：
   24301515 猎人与德鲁伊 · 24301514 牧师与战士 · 24302097 法师与萨满祭司 · 24310968 潜行者与术士。
   顺序按官方页里三个专精出现的先后，对应我们的 tree 0/1/2。圣骑士官方还没发解析稿，所以不在表里。
   规则（用户 2026-10-12 定）：树名以官方为准；官方与上游或我们不一致时，两个名字都留，
   官方那个当显示名，另一个进 nameAlt，页面按节点级的同一套约定露出第二个叫法。 */
const OFFICIAL_SPEC = {
  hunter: ['野兽控制', '射击', '生存'], druid: ['平衡', '野性战斗', '恢复'],
  priest: ['戒律', '神圣', '暗影'], warrior: ['武器', '狂怒', '防护'],
  mage: ['奥术', '火焰', '冰霜'], shaman: ['元素战斗', '增强', '恢复'],
  rogue: ['奇袭', '战斗', '敏锐'], warlock: ['痛苦', '恶魔学识', '毁灭']
};
const OFFICIAL_SPEC_SRC = 'https://wow.blizzard.cn/news/24301515 · 24301514 · 24302097 · 24310968';

let report = [];
CLASSES.forEach((cid) => {
  const mine = read(path.join('talents', cid + '.json'));
  const up = read(path.join('upstream', 'wclbox-talent-' + cid + '.json'));
  const text = {};
  const problems = [];
  const rows = [];

  mine.trees.forEach((tr, ti) => {
    const g = up.grids[ti];
    if (!g || !g.nodes.length) { problems.push('第 ' + (ti + 1) + ' 棵树上游没有数据'); return; }
    if (g.title && tr.nameCn && g.title !== tr.nameCn) {
      tr.nameAltUpstream = g.title;
      problems.push('树名不一致：我们「' + tr.nameCn + '」/ 上游「' + g.title + '」');
    }
    /* 定名：官方写过哪个就用哪个，另一个名字不删——两个都留并标冲突（红线：分歧不取舍）。
       官方没覆盖的职业（圣骑士）保持现状，只留上游别名。
       注意幂等：第二次跑时 nameCn 已经是官方名，"另一个叫法"只存在于上一轮写下的 nameAlt 里，
       所以候选名要把已有的 nameAlt 也算进来，否则重跑一次就把分歧记录冲没了（实测踩过）。 */
    const off = (OFFICIAL_SPEC[cid] || [])[ti];
    const others = Array.from(new Set([tr.nameCn, tr.nameAltUpstream, tr.nameAlt]
      .filter((x) => x && x !== off)));
    if (off && tr.nameCn !== off) {
      problems.push('树名按官方定名：「' + tr.nameCn + '」→「' + off + '」（另一个叫法留在 nameAlt）');
      tr.nameCn = off;
    }
    if (off) {
      tr.nameAlt = others[0] || null;
      tr.nameConflict = !!tr.nameAlt;
      tr.nameVerified = true;
      tr.nameSource = OFFICIAL_SPEC_SRC;
    }
    const byPos = {};
    g.nodes.forEach((n) => { byPos[n.row + ':' + n.col] = n; });
    const used = {};
    tr.nodes.forEach((n) => {
      const key = (n.tier + 1) + ':' + (n.column + 1);
      const u = byPos[key];
      if (!u) { problems.push('位置 ' + key + '（' + n.nameCn + '）上游没有'); return; }
      used[key] = true;
      n.upstreamId = u.id;
      const same = u.name === n.nameCn;
      if (!same) {
        // 同一格两边名字不同：可能是译名分歧，也可能是结构本身不一样。
        // 只记冲突，不拿对方的上限/改动标记覆盖我们这条——覆盖等于张冠李戴。
        n.nameAlt = u.name;
        n.nameConflict = true;
        n.posMismatch = true;
        problems.push('同位置名字不同（不合并字段）：' + n.nameCn + ' / ' + u.name);
        // 图标是「这一格」的属性，不是名字的属性：两边都承认这一格有一个上限相同的节点、
        // 只是中文叫法不同时，把格子的图标补过来不是覆盖，是填空缺。
        // 上限不同就跳过——那说明两源说的可能根本不是同一个天赋。
        if (!n.iconKey && u.icon && u.maxRanks && u.maxRanks === n.maxRanks) {
          n.iconKey = u.icon;
          n.iconFromCell = true;
          problems.push('补同格图标（译名分歧但位置与上限一致）：' + n.nameCn + ' / ' + u.name + ' → ' + u.icon);
        }
      } else {
        n.changeState = u.change || null;
        if (u.maxRanks && u.maxRanks !== n.maxRanks) {
          problems.push(n.nameCn + ' 点数上限 ' + n.maxRanks + ' → ' + u.maxRanks);
          n.maxRanks = u.maxRanks;
        }
        if (!n.iconKey && u.icon) n.iconKey = u.icon;
      }
      const ref = same ? up.refs.find((r) => r.id === u.id) : null;
      if (ref) {
        text[n.id] = { name: ref.name, tag: ref.tag, condition: ref.condition,
                       effect: ref.effect, changeNote: ref.changeNote, ranks: ref.ranks || [] };
        n.nameVerified = n.nameVerified || /改动|新增|移动/.test(ref.tag || '');
      }
    });
    Object.keys(byPos).forEach((k) => {
      if (!used[k]) problems.push('上游多出一条：第 ' + (ti + 1) + ' 树 ' + k + ' ' + byPos[k].name);
    });

    // 连线还原前置：路径两端各落到一个节点上
    const links = (g.connectors || []).filter((c) => c.d && c.cls.indexOf('link-line') >= 0);
    const req = {};
    links.forEach((c) => {
      const ep = endpoints(c.d);
      if (!ep) return;
      const a = nearest(g.nodes, ep.a), b = nearest(g.nodes, ep.b);
      if (!a || !b || a === b) return;
      const to = tr.nodes.find((n) => (n.tier + 1) + ':' + (n.column + 1) === b.row + ':' + b.col);
      const from = tr.nodes.find((n) => (n.tier + 1) + ':' + (n.column + 1) === a.row + ':' + a.col);
      if (to && from && to.requires.indexOf(from.id) < 0) to.requires.push(from.id);
    });
    rows.push({ tree: tr.nameCn, nodes: tr.nodes.length, links: links.length });
  });

  const costs = tierCosts(up.refs);
  const tiers = Math.max.apply(null, mine.trees.map((t) => Math.max.apply(null, t.nodes.map((n) => n.tier))));
  const arr = [];
  for (let i = 0; i <= tiers; i++) arr.push(costs[i] || 0);
  // 引擎读的是 rules.tierUnlockCost（talent.js 第 6 行），写到顶层它拿不到
  mine.rules = mine.rules || {};
  mine.rules.tierUnlockCost = arr;
  mine.structureStatus = 'confirmed';
  mine.structureSources = [{ type: 'datamine_cn', url: up.meta.source,
                             note: '格子位置、改动标记、前置连线与层级点数门槛取自无限客户端（经新手盒子转述）',
                             checkedAt: up.meta.scrapedAt }];
  write(path.join('talents', cid + '.json'), mine);
  write(path.join('talent-text', cid + '.json'), {
    meta: { classId: cid, source: up.meta.source, scrapedAt: up.meta.scrapedAt,
            note: '每个天赋的层级/前置文字、当前等级效果、改动摘要与逐等级对照（无限 vs 经典旧世）' },
    nodes: text
  });
  report.push({ cid: cid, rows: rows, problems: problems });
});

report.forEach((r) => {
  const n = r.rows.reduce((s, x) => s + x.nodes, 0), l = r.rows.reduce((s, x) => s + x.links, 0);
  console.log(r.cid.padEnd(9) + ' 节点 ' + n + ' · 还原前置连线 ' + l + ' · 问题 ' + r.problems.length);
  r.problems.slice(0, 4).forEach((p) => console.log('    · ' + p));
});

/* classes.json 的 talentCount / nameVerified 是手抄的，抄漏过两次（build-data 为此专门设了断言）。
   天赋文件才是这两个数的真相，所以由这一步同步，不再靠人记——每次合并完自动对上。 */
try {
  const cls = read('classes.json');
  let touched = 0;
  (cls.classes || []).forEach((c) => {
    let f;
    try { f = read('talents/' + c.id + '.json'); } catch (e) { return; }
    const nodes = f.trees.reduce((a, t) => a + t.nodes.length, 0);
    const ver = f.trees.reduce((a, t) => a + t.nodes.filter((x) => x.nameVerified).length, 0);
    if (c.talentCount !== nodes || c.nameVerified !== ver) {
      console.log('  classes ' + c.id + '：talentCount ' + c.talentCount + '→' + nodes +
        ' ｜ nameVerified ' + c.nameVerified + '→' + ver);
      c.talentCount = nodes; c.nameVerified = ver; touched++;
    }
  });
  if (touched) write('classes.json', cls);
  console.log('classes.json 的天赋数与核实数已按 talent 文件同步（' + touched + ' 个职业）');
} catch (e) { console.error('classes.json 同步失败：' + e.message); }
