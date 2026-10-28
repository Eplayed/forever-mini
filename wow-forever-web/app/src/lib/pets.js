/* 猎人宠物那一页的纯函数（单测直接打这些，见 app/tests/pets.spec.js）。
   页面只负责排版，筛选与显示文本都从这里出——两边共用一份，不会出现"页面上 18 个、搜出来 17 个"。 */

/* 三项修正是相对值，0 要写成 0 而不是空着：空着会被读成"这一格没数据"，
   而"没数据"和"不偏"是两回事（缺数据才写待实测，这里是真有 0 这个值）。 */
export function modText(v) {
  if (v === null || v === undefined) return '待实测';
  const n = Number(v);
  if (!Number.isFinite(n)) return '待实测';
  if (n === 0) return '0';
  return (n > 0 ? '+' : '−') + Math.abs(n);
}

/* 冷却 0 与"没这个字段"是两回事：0 是这条技能本来就不占冷却，
   写成"没写"会让玩家以为数据缺了、去别处再查一遍。 */
export function cdText(v) {
  if (v === null || v === undefined) return '待实测';
  const n = Number(v);
  if (!Number.isFinite(n)) return '待实测';
  return n === 0 ? '不用冷却' : n + ' 秒';
}

function hit(row, needle) {
  const k = String(needle || '').trim().toLowerCase();
  if (!k) return true;
  return (String(row.name || '') + String(row.nameEn || '')).toLowerCase().indexOf(k) >= 0;
}

export function filterFamilies(rows, opt) {
  const o = opt || {};
  return (rows || []).filter((x) => {
    if (o.onlyNew && !x.isNew) return false;
    return hit(x, o.q);
  });
}

export function filterSkills(rows, opt) {
  const o = opt || {};
  return (rows || []).filter((x) => {
    if (o.onlyNew && !x.isNew) return false;
    if (o.fam && !(x.families || []).includes(o.fam)) return false;
    return hit(x, o.q);
  });
}

/* 下拉里只列"技能表里真出现过的族"——某族一条技能都没挂上时，
   列它等于放一个选了必然为空的选项。 */
export function familyOptions(families, skills) {
  const used = new Set();
  (skills || []).forEach((s) => (s.families || []).forEach((n) => used.add(n)));
  return (families || []).filter((f) => used.has(f.name)).map((f) => f.name).sort((a, b) => a.localeCompare(b, 'zh'));
}

/* 技能那一列在家族行里显示成"名（是不是新增）"，页面自己拼，数据里不存第二份 */
export function skillChips(fam) {
  return ((fam && fam.skills) || []).map((s) => ({
    id: s.id, name: s.nameCn || s.nameEn, isNew: !!s.isNew
  }));
}
