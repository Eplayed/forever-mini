/* 天赋模拟器引擎（2026-10-22 站主：小程序的天赋树要"模拟器的样子，可以模拟点击配置，和网页版那样的功能"）。
   规则逐条对齐网页端 app/src/pages/TalentPage.vue 里那份引擎（加点/减点/级联清空/层级门槛/前置/编解码），
   两边同源不同文件——网页那份由 site-check 钉着，这一份由 tools/mini-m02-check.js 用同一组用例钉着，
   改任何一边都要在另一边补一条，不然两端会给出不同的"能不能点"。

   与网页有意不同的两处，都写在这里免得被当成漂移：
   1) 前置未点那句给的是天赋中文名，不是 warrior-0-重伤 这种内部编号（网页那条会把编号印到玩家面前）；
   2) 门槛与总点数没核到之前不下发 rules 时，这里退成"不做层级判定"，界面照实说"层级门槛未核实"。

   红线：门槛数（tierUnlockCost）来源是客户端解包转述、grid.note 自己写着"仍未核实"，
   所以它只用来做"能不能点"的判定，界面必须把"这是按经典旧世层级推的、无限服待实测"这句话留在屏幕上。 */

function ranksOf(state, id) {
  return state[id] || 0
}

function treeSpent(tree, state) {
  return (tree.nodes || []).reduce(function (a, n) { return a + ranksOf(state, n.id) }, 0)
}

function spent(state, trees) {
  return (trees || []).reduce(function (a, t) { return a + treeSpent(t, state) }, 0)
}

/* 缺 rules 时的兜底与网页 defaults() 同一组值：51 点 / 60 级上限 */
function normalizeRules(rules) {
  const r = rules || {}
  return {
    totalPoints: r.totalPoints ? r.totalPoints : 51,
    tierUnlockCost: r.tierUnlockCost ? r.tierUnlockCost : null
  }
}

function tierOpen(tree, state, node, r) {
  if (!r.tierUnlockCost || node.tier === null || node.tier === undefined) return true
  return treeSpent(tree, state) >= (r.tierUnlockCost[node.tier] || 0)
}

function reqMissing(node, state) {
  return (node.requires || []).filter(function (id) { return ranksOf(state, id) < 1 })
}

/* 能不能再点一点。why 是给玩家看的一句话，所以前置那条要翻成名字 */
function canAdd(tree, state, node, r, allTrees, nameOf) {
  if (node.maxRanks === null || node.maxRanks === undefined) return { ok: false, why: '这个天赋的点数上限还没核实' }
  if (ranksOf(state, node.id) >= node.maxRanks) return { ok: false, why: '已点满 ' + node.maxRanks + ' 点' }
  if (!tierOpen(tree, state, node, r)) {
    return { ok: false, why: '这一系要先投满 ' + (r.tierUnlockCost[node.tier] || 0) + ' 点才开第 ' + (node.tier + 1) + ' 层' }
  }
  const miss = reqMissing(node, state)
  if (miss.length) {
    const named = typeof nameOf === 'function' ? miss.map(function (id) { return nameOf(id) || id }) : miss
    return { ok: false, why: '要先点：' + named.join('、') }
  }
  if (spent(state, allTrees || [tree]) >= r.totalPoints) return { ok: false, why: '可用点数已用完（共 ' + r.totalPoints + ' 点）' }
  return { ok: true }
}

function treeOf(trees, node) {
  return (trees || []).filter(function (t) {
    return (t.nodes || []).some(function (n) { return n.id === node.id })
  })[0]
}

function add(trees, state, node, rules, nameOf) {
  const t = treeOf(trees, node)
  if (!t) return { state: state, msg: '这个天赋不在名单里' }
  const r = normalizeRules(rules)
  const c = canAdd(t, state, node, r, trees, nameOf)
  if (!c.ok) return { state: state, msg: c.why }
  const s = Object.assign({}, state)
  s[node.id] = ranksOf(state, node.id) + 1
  return { state: s, msg: null }
}

function dependents(tree, id) {
  let out = []
  ;(tree.nodes || []).forEach(function (n) {
    if ((n.requires || []).indexOf(id) >= 0) {
      out.push(n)
      out = out.concat(dependents(tree, n.id))
    }
  })
  return out
}

/* 减一点：靠它活着的天赋要跟着倒（与网页同一套级联），倒掉的名字回给界面说一句"已清空" */
function remove(trees, state, node) {
  if (ranksOf(state, node.id) < 1) return { state: state, msg: '这个天赋还没点' }
  const s = Object.assign({}, state)
  s[node.id] = ranksOf(state, node.id) - 1
  const dropped = []
  ;(trees || []).forEach(function (t) {
    dependents(t, node.id).forEach(function (d) {
      if (reqMissing(d, s).length && ranksOf(s, d.id) > 0) {
        s[d.id] = 0
        dropped.push(d.nameCn || d.nameEn || d.id)
      }
    })
  })
  return { state: s, msg: dropped.length ? '跟着清空：' + dropped.join('、') : null }
}

/* 一套配置的短码：每系按节点顺序取点数（0-9），系间用 - 分隔。
   与网页 encode/decode 逐字符同格式——小程序分享的串，网页那边能原样打开，反之也一样 */
function encode(trees, state) {
  return (trees || []).map(function (t) {
    return (t.nodes || []).map(function (n) { return Math.min(ranksOf(state, n.id), 9).toString(36) }).join('')
  }).join('-')
}

function decode(str, trees) {
  const state = {}
  let bad = 0
  if (!str) return { state: state, bad: 0 }
  const parts = String(str).split('-')
  ;(trees || []).forEach(function (t, ti) {
    const s = parts[ti] || ''
    ;(t.nodes || []).forEach(function (n, ni) {
      let v = parseInt(s.charAt(ni) || '0', 36)
      if (isNaN(v)) { v = 0; bad += 1 }
      const max = n.maxRanks === null || n.maxRanks === undefined ? 0 : n.maxRanks
      if (v > max) { v = max; bad += 1 }
      if (v > 0) state[n.id] = v
    })
  })
  return { state: state, bad: bad }
}

/* 按层分组、层内按列排：界面一列一列摆，跟游戏里那张树对得上 */
function tiersOf(tree) {
  let max = -1
  ;(tree.nodes || []).forEach(function (n) { if (n.tier > max) max = n.tier })
  const out = []
  for (let t = 0; t <= max; t += 1) {
    out.push(tree.nodes.filter(function (n) { return n.tier === t })
      .sort(function (a, b) { return (a.column || 0) - (b.column || 0) }))
  }
  return out
}

function describe(trees, state) {
  return (trees || []).map(function (t) { return (t.nameCn || t.id) + ' ' + treeSpent(t, state) }).join(' / ')
}

module.exports = {
  ranksOf, treeSpent, spent, normalizeRules, tierOpen, reqMissing, canAdd,
  add, remove, encode, decode, tiersOf, describe
}
