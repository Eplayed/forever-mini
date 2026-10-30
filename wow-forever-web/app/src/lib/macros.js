/* 宏命令页的纯函数（2026-10-30）。
   和 lib/pets.js、lib/legacy-plan.js 同一做法：筛选与计数写成不碰 DOM 的函数，
   单测 app/tests/macros.spec.js 直接打真数据，页面只负责摆。
   两条口径写在函数里而不是写在页面里，免得"选了不生效"这种毛病只在人眼看得出来：
   ① 分组芯片只出**当前筛出来的集合里真有的**组（放了必然为空的芯片比不放更坏）；
   ② 计数一律从数据现算，不抄字面量。 */

/** 职业顺序：跟 classes.json 那一套走（页面与导航都按这个次序排）。 */
export const CLASS_ORDER = ['warrior', 'paladin', 'hunter', 'rogue', 'priest',
                            'shaman', 'mage', 'warlock', 'druid'];

export function classCounts(macros) {
  const m = {};
  (macros || []).forEach((x) => { m[x.classId] = (m[x.classId] || 0) + 1; });
  return m;
}

/** 只保留数据里真出现过的职业，顺序仍按 CLASS_ORDER。 */
export function classOptions(macros) {
  const c = classCounts(macros || []);
  return CLASS_ORDER.filter((id) => c[id]).map((id) => ({ id, n: c[id], name: (macros.find((x) => x.classId === id) || {}).className || id }));
}

/** 当前职业下有哪些用途分组，带条数，按数据里第一次出现的顺序排。 */
export function groupOptions(macros) {
  const seen = [];
  const m = {};
  (macros || []).forEach((x) => {
    if (!(x.group in m)) { m[x.group] = 0; seen.push(x.group); }
    m[x.group] += 1;
  });
  return seen.map((g) => ({ group: g, n: m[g] }));
}

/** 一条宏是否命中关键词：宏名（中英）、说明（中英）、正文里的法术名都算。 */
export function matches(m, q) {
  const k = String(q || '').trim().toLowerCase();
  if (!k) return true;
  return [m.title, m.titleEn, m.note, m.noteEn, m.body, m.group]
    .some((s) => String(s || '').toLowerCase().indexOf(k) >= 0);
}

/** 等级滤：只留"我这个等级学得会"的；minLevel 为 0 表示没有等级门槛，任何等级都留。 */
export function learnable(m, level) {
  if (!level && level !== 0) return true;
  const need = Number(m.minLevel) || 0;
  return need <= Number(level);
}

export function filterMacros(macros, sel) {
  const s = sel || {};
  return (macros || []).filter((m) =>
    (!s.classId || m.classId === s.classId)
    && (!s.group || m.group === s.group)
    && learnable(m, s.level)
    && matches(m, s.q));
}

/** 页顶那行读数：全部从数据现算，改一条宏这里就跟着变。 */
export function summary(macros) {
  const list = macros || [];
  return {
    total: list.length,
    classes: new Set(list.map((m) => m.classId)).size,
    groups: new Set(list.map((m) => m.group)).size,
    foreverNew: list.filter((m) => m.foreverNew).length,
    rankMarker: list.filter((m) => m.rankMarker).length
  };
}

/** 「几级能用」的显示：0 是"没有等级门槛"，不是"0 级"，两者不能都写成 0 级。 */
export function levelText(m) {
  const n = Number(m.minLevel);
  if (!n) return '没有等级门槛';
  return n + ' 级能用';
}
