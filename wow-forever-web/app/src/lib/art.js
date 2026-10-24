/* 素材索引（app/data/art.json）的取值口：与旧站 src/js/app.js 里的 specArt() / artOf() 同一套规则。
   2026-10-13 用户实拍：卡片背景要的是图，不是把 128 的图标拉开放大——
   所以这里取不到就返回空字符串，让调用方留纯色，绝不拿别的图凑数。 */

export function artOf(A, group, key) {
  return ((A || {})[group] || {})[key] || '';
}

/* 专精背景：键是「职业-第几系」（warrior-0 … druid-2），共 27 张 320×384。
   那一系没有图就退回该职业第一系，再没有就空——不返回图标。 */
export function specArt(A, cid, ti) {
  const S = (A || {}).specs || {};
  return S[(cid || '') + '-' + (ti === undefined ? 0 : ti)] || S[(cid || '') + '-0'] || '';
}
