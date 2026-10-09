/* 首页只读天赋树预览的纯逻辑：把派生数据排成 7×4 网格、数改动状态、生成跳计算器的链接。
   数据本身是 tools/build-data.js 从 src/data/talents/*.json 派生的 talent-preview.json。 */

export const CHG_LABEL = {
  added: '新增', modified: '改动', moved: '换层或换系', unchanged: '未变', removed: '已移除'
};
// 一条节点 = [行, 列, 名称, 图标键, 上限层数, 改动状态]
export const PV_COLS = 4;

export function treeOf(preview, classId, ti) {
  const cls = ((preview || {}).classes || {})[classId];
  if (!cls || !(cls.trees || []).length) return null;
  return cls.trees[ti] || cls.trees[0];
}

/* 按行优先铺满 rows × PV_COLS，空格给 null，渲染方补占位元素。 */
export function gridCells(tree) {
  if (!tree) return [];
  const byPos = {};
  let rows = 0;
  tree.nodes.forEach((n) => {
    byPos[n[0] + '-' + n[1]] = n;
    if (n[0] > rows) rows = n[0];
  });
  const out = [];
  for (let r = 0; r <= rows; r++) {
    for (let c = 0; c < PV_COLS; c++) out.push(byPos[r + '-' + c] || null);
  }
  return out;
}

export function countStates(tree) {
  const cnt = {};
  ((tree || {}).nodes || []).forEach((n) => {
    const k = n[5] || 'none';
    cnt[k] = (cnt[k] || 0) + 1;
  });
  return ['added', 'modified', 'moved', 'unchanged', 'none']
    .filter((k) => cnt[k])
    .map((k) => ({ k, label: k === 'none' ? '没有对照结果' : CHG_LABEL[k], n: cnt[k] }));
}

export function nodeLabel(nd) {
  const st = nd[5] ? (CHG_LABEL[nd[5]] || '') : '';
  return nd[2] + '，上限 ' + (nd[4] === null || nd[4] === undefined ? '未核实' : nd[4] + ' 层') +
    (st ? '；与经典旧世相比：' + st : '；没有对照结果');
}

/* 跳进计算器：带着职业、哪一系与天赋名，落地由计算器自己描边高亮 */
export function nodeFile(classId, ti, name) {
  return 'talent.html?c=' + encodeURIComponent(classId) + '&tree=' + ti +
    '&q=' + encodeURIComponent(name);
}

export function calcFile(classId, ti) {
  return 'talent.html?c=' + encodeURIComponent(classId) + '&tree=' + ti;
}
