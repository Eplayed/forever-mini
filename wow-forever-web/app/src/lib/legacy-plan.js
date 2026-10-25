/* 传承规划器引擎（2026-10-23）——纯函数，不依赖 Vue，单测在 app/tests/legacy-plan.spec.js。
   事实全部从 app/data/legacy.json 现读，这里一个数都不写死：
   上限取 meta.rules.launchSpendingCap、门槛取 perks[].treePointsRequired、
   层数取 perks[].maxRank、连线取 trees[].links、奖励档取 rewards[].at。
   红线：每级按 1 点只是**规划假设**（游戏内消耗没核实），界面必须把这句带上；
        没有可靠效果文本的专长一律显示"具体效果待实测"，这里不生成任何效果描述。 */

/* 把一份 legacy.json 拍成引擎要的索引。返回的 ctx 是所有判定函数的入参。 */
export function buildCtx(data) {
  const d = data || {};
  const rules = (d.meta || {}).rules || {};
  const perks = d.perks || [];
  const byId = {};
  perks.forEach((p) => { byId[p.id] = p; });
  const treeOf = {};
  (d.trees || []).forEach((t) => { treeOf[t.id] = t; });
  /* 门槛一律读 perks[].treePointsRequired（数据里就有），不去改缓存里的对象。 */
  /* 反向依赖表：谁把这一格当前置。退点时要靠它找出会被打断的后续格。 */
  const dependents = {};
  perks.forEach((p) => {
    if (p.prerequisite) (dependents[p.prerequisite] = dependents[p.prerequisite] || []).push(p.id);
  });
  return {
    perks: perks,
    byId: byId,
    trees: d.trees || [],
    treeOf: treeOf,
    dependents: dependents,
    cap: rules.launchSpendingCap == null ? null : rules.launchSpendingCap,
    pointPerChallenge: rules.pointPerChallenge == null ? null : rules.pointPerChallenge,
    gates: ((rules.treePointGates || {}).values) || [],
    rewards: d.rewards || [],
    challenges: d.challenges || [],
    clientBuild: (d.meta || {}).clientBuild || ''
  };
}

/* 一条方案的点数合计：state = { perkId: 已点层数 }。每层按 1 点算（规划假设）。 */
export function totalSpent(state) {
  let n = 0;
  Object.keys(state || {}).forEach((k) => { n += Number(state[k]) || 0; });
  return n;
}

/* 某一棵树已投点数（门槛判定用这一棵的，不是全局的） */
export function treeSpent(ctx, state, treeId) {
  let n = 0;
  ctx.perks.forEach((p) => {
    if (p.treeId === treeId) n += Number((state || {})[p.id]) || 0;
  });
  return n;
}

export function spentByTree(ctx, state) {
  const out = {};
  ctx.trees.forEach((t) => { out[t.id] = treeSpent(ctx, state, t.id); });
  return out;
}

/* 能不能给这一格加一点。返回 {ok, reason}，reason 是要给玩家看的大白话。 */
export function canAdd(ctx, state, perkId) {
  const p = ctx.byId[perkId];
  if (!p) return { ok: false, reason: '这一格还没收录，点不了' };
  if (p.maxRank == null) return { ok: false, reason: p.nameCn + '：层数上限还没核实，不做模拟' };
  const now = Number((state || {})[perkId]) || 0;
  if (now >= p.maxRank) return { ok: false, reason: p.nameCn + ' 已经点满 ' + p.maxRank + ' 层' };
  const cap = ctx.cap;
  if (cap != null && totalSpent(state) >= cap) {
    return { ok: false, reason: '这个角色已经花满 ' + cap + ' 点，先退掉别处的点' };
  }
  const gate = p.treePointsRequired;
  if (gate != null && treeSpent(ctx, state, p.treeId) < gate) {
    return { ok: false, reason: p.nameCn + ' 要先在「' + p.treeCn + '」这一棵投满 ' + gate + ' 点' };
  }
  if (p.prerequisite) {
    const pre = ctx.byId[p.prerequisite];
    if (!((state || {})[p.prerequisite] > 0)) {
      return { ok: false, reason: p.nameCn + ' 要先点「' + ((pre && pre.nameCn) || '前置专长') + '」' };
    }
  }
  return { ok: true, reason: '' };
}

export function add(ctx, state, perkId) {
  const c = canAdd(ctx, state, perkId);
  if (!c.ok) return { state: state, msg: c.reason };
  const next = Object.assign({}, state);
  next[perkId] = (Number(next[perkId]) || 0) + 1;
  return { state: next, msg: '' };
}

/* 退点：先算出"退了会把谁的后续打断"。会打断就阻止并点名，绝不静默清掉别的点。 */
export function remove(ctx, state, perkId) {
  const p = ctx.byId[perkId];
  if (!p) return { state: state, msg: '这一格还没收录' };
  const now = Number((state || {})[perkId]) || 0;
  if (now <= 0) return { state: state, msg: p.nameCn + ' 这一点还没投' };
  const trial = Object.assign({}, state);
  trial[perkId] = now - 1;
  if (trial[perkId] <= 0) delete trial[perkId];
  const blocked = cascadeBlockers(ctx, trial, state);
  if (blocked.length) {
    return { state: state, msg: '不能退：' + blocked.join('；') };
  }
  return { state: trial, msg: '' };
}

/* 一份 state 里所有不成立的点（用于退点后的试算与外部方案校验）。
   返回 ["「X」还点着，但它的前置「Y」退到 0", "「X」还点着，但这一棵只剩 N 点、不够它要的 M 点"] */
export function cascadeBlockers(ctx, trial, origin) {
  const out = [];
  ctx.perks.forEach((p) => {
    const v = Number((trial || {})[p.id]) || 0;
    if (v <= 0) return;
    if (p.prerequisite && !((trial || {})[p.prerequisite] > 0)) {
      const pre = ctx.byId[p.prerequisite];
      out.push('「' + p.nameCn + '」还点着，但它的前置「' + ((pre && pre.nameCn) || '未收录') + '」退到 0 了');
      return;
    }
    const gate = p.treePointsRequired;
    if (gate != null && treeSpent(ctx, trial, p.treeId) < gate) {
      out.push('「' + p.nameCn + '」还点着，但「' + p.treeCn + '」这一棵退到 ' +
        treeSpent(ctx, trial, p.treeId) + ' 点，不够它要的 ' + gate + ' 点');
    }
  });
  return out;
}

/* 整棵清空是允许的：同一棵里的点互相依赖，一起退掉不会留下"点着但已不成立"的格子。
   跨树不互相依赖（门槛只看本树，前置 trees[].links 只在同树内），所以按树清是安全的。 */
export function clearTree(ctx, state, treeId) {
  const next = {};
  Object.keys(state || {}).forEach((k) => {
    const p = ctx.byId[k];
    if (p && p.treeId === treeId) return;
    next[k] = state[k];
  });
  return next;
}

/* ============ 方案码：只装 21 个格子的层数 + 一个 schema 版本，不装个人挑战记录 ============ */
export const SCHEMA = 1;

export function encode(ctx, state) {
  const parts = [];
  ctx.perks.forEach((p) => {
    const v = Number((state || {})[p.id]) || 0;
    if (v > 0) parts.push(p.id.replace(/^legacy-perk-/, '') + '.' + v);
  });
  return 'v' + SCHEMA + (parts.length ? ':' + parts.join(',') : '');
}

/* 解码一律"按能认的还原 + 把不认的报出来"，不静默吞：
   未知 id、超层数、坏版本、非数字，全部进 errors；认完的结果再过一遍 validate。 */
export function decode(ctx, code) {
  const s = String(code || '');
  const out = { state: {}, errors: [], bad: false };
  if (!s) return out;
  const m = /^v(\d+)(?::(.*))?$/.exec(s);
  if (!m) { out.bad = true; out.errors.push('方案码看不懂（不是 v版本号 开头）'); return out; }
  if (+m[1] !== SCHEMA) {
    out.bad = true;
    out.errors.push('这是第 ' + m[1] + ' 版方案码，本页认的是第 ' + SCHEMA + ' 版');
    return out;
  }
  (m[2] || '').split(',').filter(Boolean).forEach((seg) => {
    const i = seg.lastIndexOf('.');
    const key = i < 0 ? '' : seg.slice(0, i);
    const raw = i < 0 ? '' : seg.slice(i + 1);
    const id = 'legacy-perk-' + key;
    const p = ctx.byId[id];
    const v = Number(raw);
    if (!p) { out.bad = true; out.errors.push('方案里有一个这一版没有的格子：' + key); return; }
    if (!/^\d+$/.test(raw) || v <= 0) { out.bad = true; out.errors.push('「' + p.nameCn + '」的层数看不懂：' + raw); return; }
    if (p.maxRank != null && v > p.maxRank) {
      out.bad = true;
      out.errors.push('「' + p.nameCn + '」最多 ' + p.maxRank + ' 层，方案里写了 ' + v + ' 层，按 ' + p.maxRank + ' 层收');
      out.state[id] = p.maxRank;
      return;
    }
    out.state[id] = v;
  });
  const v = validate(ctx, out.state);
  if (!v.ok) {
    out.bad = true;
    out.errors.push.apply(out.errors, v.errors);
  }
  return out;
}

/* 一份方案本身成不成立：总额、门槛、前置。不成立时给出逐条原因（给玩家看，不是内部术语）。 */
export function validate(ctx, state) {
  const errors = [];
  if (ctx.cap != null && totalSpent(state) > ctx.cap) {
    errors.push('方案一共 ' + totalSpent(state) + ' 点，超过每个角色 ' + ctx.cap + ' 点的上限');
  }
  ctx.perks.forEach((p) => {
    const v = Number((state || {})[p.id]) || 0;
    if (v <= 0) return;
    if (p.maxRank != null && v > p.maxRank) {
      errors.push('「' + p.nameCn + '」最多 ' + p.maxRank + ' 层，方案里写了 ' + v + ' 层');
      return;
    }
    if (p.prerequisite && !((state || {})[p.prerequisite] > 0)) {
      const pre = ctx.byId[p.prerequisite];
      errors.push('「' + p.nameCn + '」点着，但它的前置「' + ((pre && pre.nameCn) || '未收录') + '」是 0 点');
    }
    const gate = p.treePointsRequired;
    if (gate != null && treeSpent(ctx, state, p.treeId) < gate) {
      errors.push('「' + p.nameCn + '」点着，但「' + p.treeCn + '」这一棵只有 ' +
        treeSpent(ctx, state, p.treeId) + ' 点，不够它要的 ' + gate + ' 点');
    }
  });
  return { ok: !errors.length, errors: errors };
}

/* ============ 挑战勾选 → 进度 ============
   常规 65 项与那条测试参与记录（special）分开数：特殊记录不并进常规分母。 */
export function challengeIndex(ctx) {
  const items = [];
  const byId = {};
  (ctx.challenges || []).forEach((g) => {
    (g.items || []).forEach((x) => {
      items.push(x);
      byId[String(x.id)] = { item: x, group: g };
    });
  });
  const regular = items.filter((x) => !x.special);
  const special = items.filter((x) => x.special);
  return { items: items, map: byId, regular: regular, special: special };
}

/* 勾选集合 → 点数。只认数据里真有的 id：本机存的旧记录里如果有已经不存在的 id，
   丢掉并回报，绝不把完成状态错给一个对不上的新条目。 */
export function applyChecks(ctx, ids) {
  const idx = challengeIndex(ctx);
  const kept = [], dropped = [];
  (ids || []).forEach((raw) => {
    const k = String(raw);
    if (idx.map[k]) kept.push(k); else dropped.push(k);
  });
  const set = {};
  kept.forEach((k) => { set[k] = true; });
  let regularPoints = 0, specialPoints = 0;
  Object.keys(set).forEach((k) => {
    const x = idx.map[k].item;
    const pts = Number(x.points) || 0;
    if (x.special) specialPoints += pts; else regularPoints += pts;
  });
  return { set: set, kept: kept, dropped: dropped, regularPoints: regularPoints,
    specialPoints: specialPoints, regularDone: kept.filter((k) => !idx.map[k].item.special).length,
    specialDone: kept.filter((k) => idx.map[k].item.special).length };
}

/* 奖励轨：每一档写清"要攒多少点、现在攒到没"。门槛是点数，不是挑战条数。 */
export function rewardTrack(ctx, regularPoints) {
  const got = Number(regularPoints) || 0;
  return (ctx.rewards || []).map((r) => ({
    at: r.at, nameCn: r.nameCn, itemId: r.itemId, iconKey: r.iconKey,
    reached: got >= r.at, left: Math.max(0, r.at - got)
  }));
}

/* 格子在客户端那张 5×5 里可能整排/整列是空的（2026-10-23 客户端就这么留白）。
   显示时把全空的排与列收掉，但**编号仍用客户端的真实行列**，收掉不等于改掉。 */
export function visibleGrid(tree) {
  const slots = (tree || {}).slots || [];
  const used = slots.filter((s) => !s.empty);
  const rows = [], cols = [];
  for (let r = 0; r < tree.rows; r++) if (used.some((s) => s.row === r)) rows.push(r);
  for (let c = 0; c < tree.cols; c++) if (used.some((s) => s.col === c)) cols.push(c);
  return { rows: rows, cols: cols };
}

/* 前置连线：trees[].links 给的是 {from,to}，换算成"两端格子的显示坐标"，
   两端只要有一个不在显示网格里（未公开槽也算在）就不画，但数据本身不丢。 */
export function linkSegments(tree, grid) {
  const at = {};
  grid.rows.forEach((r, i) => {
    grid.cols.forEach((c, j) => { at[r + '-' + c] = { row: i, col: j }; });
  });
  const out = [];
  ((tree || {}).links || []).forEach((l) => {
    const a = slotAt(tree, l.from), b = slotAt(tree, l.to);
    if (!a || !b) return;
    const pa = at[a.row + '-' + a.col], pb = at[b.row + '-' + b.col];
    if (!pa || !pb) return;
    out.push({ from: l.from, to: l.to, a: pa, b: pb });
  });
  return out;
}

export function slotAt(tree, perkId) {
  return ((tree || {}).slots || []).filter((s) => s.perk === perkId)[0] || null;
}

/* 挑战矩阵（2026-10-25）：把"每行一个子分类、每列一档"的组摆成网格——
   职业那组是 9 个职业 × 新手/熟练/高阶，商业技能是 6 个专业 × 中级/高级/专家级。
   两条硬规矩：
   ① **列头不写死**。"新手/熟练/高阶"是从条目名里剥掉子分类名得到的（新手德鲁伊 − 德鲁伊），
      剥不出来、剥完是空、或者各行的档位序列不一致，一律返回 null 让页面回落成表格。
      写死列名的话，客户端哪天把"高阶"改成"大师"，页面就会拿旧词盖住新数据。
   ② 只有"每个子分类条数相同且 ≥2"才摆矩阵。玩家对战那组三个子类条数不齐（军衔按等级排），
      地下城/冒险没有子分类，都自动回落。
   搜索态由调用方决定不摆：搜索要的是命中行连着完成条件一起看，网格会把条件藏起来。 */
export function challengeMatrix(items) {
  const list = (items || []).filter((x) => x && x.sub && x.nameCn);
  if (list.length !== (items || []).length) return null;
  const order = [];
  const by = {};
  list.forEach((x) => {
    if (!by[x.sub]) { by[x.sub] = []; order.push(x.sub); }
    by[x.sub].push(x);
  });
  if (order.length < 2) return null;
  const n = by[order[0]].length;
  if (n < 2) return null;
  const cols = [];
  const rows = order.map((sub) => {
    const its = by[sub];
    if (its.length !== n) return null;
    const cells = its.map((x) => {
      const at = x.nameCn.indexOf(sub);
      if (at < 0) return null;
      const label = (x.nameCn.slice(0, at) + x.nameCn.slice(at + sub.length)).trim();
      return label ? { item: x, label: label } : null;
    });
    if (cells.some((c) => !c)) return null;
    const labels = cells.map((c) => c.label);
    if (new Set(labels).size !== labels.length) return null;
    if (!cols.length) labels.forEach((l) => cols.push(l));
    else if (labels.join('|') !== cols.join('|')) return null;
    return { sub: sub, cells: cells };
  });
  if (rows.some((r) => !r)) return null;
  return { cols: cols, rows: rows };
}
