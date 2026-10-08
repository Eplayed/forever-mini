/* 天赋树引擎：层解锁、前置校验、级联减点、方案编码 */
window.TalentEngine = (function () {
  function defaults(rules) {
    return {
      totalPoints: rules && rules.totalPoints ? rules.totalPoints : 51,
      tierUnlockCost: rules && rules.tierUnlockCost ? rules.tierUnlockCost : null
    };
  }
  function index(trees) {
    var map = {};
    trees.forEach(function (t) {
      t.nodes.forEach(function (n) { map[n.id] = { node: n, tree: t }; });
    });
    return map;
  }
  function ranksOf(state, id) { return state[id] || 0; }
  function treeSpent(tree, state) {
    return tree.nodes.reduce(function (a, n) { return a + ranksOf(state, n.id); }, 0);
  }
  function spent(state, trees) {
    return trees.reduce(function (a, t) { return a + treeSpent(t, state); }, 0);
  }
  function tierOpen(tree, state, node, r) {
    if (!r.tierUnlockCost || node.tier === null || node.tier === undefined) return true;
    var need = r.tierUnlockCost[node.tier] || 0;
    return treeSpent(tree, state) >= need;
  }
  function hasTiers(tree) {
    return !!(tree && tree.nodes && tree.nodes.length && tree.nodes[0].tier !== null && tree.nodes[0].tier !== undefined);
  }
  function reqMissing(node, state) {
    return (node.requires || []).filter(function (id) { return ranksOf(state, id) < 1; });
  }
  function canAdd(tree, state, node, r, allTrees) {
    if (node.maxRanks === null || node.maxRanks === undefined) return { ok: false, why: '该天赋点数上限未核实' };
    if (ranksOf(state, node.id) >= node.maxRanks) return { ok: false, why: '已达上限 ' + node.maxRanks + ' 点' };
    if (!tierOpen(tree, state, node, r)) return { ok: false, why: '本系需先投满 ' + (r.tierUnlockCost[node.tier] || 0) + ' 点解锁第 ' + (node.tier + 1) + ' 层' };
    var miss = reqMissing(node, state);
    if (miss.length) return { ok: false, why: '前置未点：' + miss.join('、') };
    if (spent(state, allTrees || [tree]) >= r.totalPoints) return { ok: false, why: '可用点数已用尽（共 ' + r.totalPoints + ' 点）' };
    return { ok: true };
  }
  function add(trees, state, node, fileRules) {
    var t = trees.filter(function (x) { return x.nodes.some(function (n) { return n.id === node.id; }); })[0];
    if (!t) return { state: state, msg: '未知节点' };
    var r = defaults(fileRules || t.rules);
    var c = canAdd(t, state, node, r, trees);
    if (!c.ok) return { state: state, msg: c.why };
    var s = Object.assign({}, state); s[node.id] = ranksOf(state, node.id) + 1;
    return { state: s, msg: null };
  }
  function dependents(tree, id) {
    var out = [];
    tree.nodes.forEach(function (n) {
      if ((n.requires || []).indexOf(id) >= 0) { out.push(n); out = out.concat(dependents(tree, n.id)); }
    });
    return out;
  }
  function remove(trees, state, node) {
    if (ranksOf(state, node.id) < 1) return { state: state, msg: '该天赋尚未加点' };
    var s = Object.assign({}, state);
    s[node.id] = ranksOf(state, node.id) - 1;
    var dropped = [];
    trees.forEach(function (t) {
      dependents(t, node.id).forEach(function (d) {
        var miss = reqMissing(d, s);
        if (miss.length && ranksOf(s, d.id) > 0) {
          s[d.id] = 0; dropped.push(d.nameCn || d.nameEn || d.id);
        }
      });
    });
    return { state: s, msg: dropped.length ? '已级联清空：' + dropped.join('、') : null };
  }
  /* 编码：每系按节点顺序取点数（0-9），系间用 - 分隔 */
  function encode(trees, state) {
    return trees.map(function (t) {
      return t.nodes.map(function (n) { return Math.min(ranksOf(state, n.id), 9).toString(36); }).join('');
    }).join('-');
  }
  function decode(str, trees) {
    var state = {}, bad = 0;
    if (!str) return { state: state, bad: 0 };
    var parts = String(str).split('-');
    trees.forEach(function (t, ti) {
      var s = parts[ti] || '';
      t.nodes.forEach(function (n, ni) {
        var v = parseInt(s.charAt(ni) || '0', 36);
        if (isNaN(v)) { v = 0; bad++; }
        var max = n.maxRanks === null || n.maxRanks === undefined ? 0 : n.maxRanks;
        if (v > max) { v = max; bad++; }
        if (v > 0) state[n.id] = v;
      });
    });
    return { state: state, bad: bad };
  }
  function tiers(tree) {
    var max = -1;
    tree.nodes.forEach(function (n) { if (n.tier > max) max = n.tier; });
    var out = [];
    for (var t = 0; t <= max; t++) {
      out.push(tree.nodes.filter(function (n) { return n.tier === t; })
        .sort(function (a, b) { return a.column - b.column; }));
    }
    return out;
  }
  function describe(trees, state) {
    return trees.map(function (t) {
      return t.nameCn + ' ' + treeSpent(t, state);
    }).join(' / ');
  }
  return { add: add, remove: remove, encode: encode, decode: decode, canAdd: canAdd, hasTiers: hasTiers,
    spent: spent, treeSpent: treeSpent, tiers: tiers, index: index, defaults: defaults, describe: describe };
})();
