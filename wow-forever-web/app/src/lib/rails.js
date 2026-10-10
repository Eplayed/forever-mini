/* 来源轨（签名元素）——与旧站 src/js/app.js 的 applyRails 同一套规则，两份实现由
   tools/app-parity.py 逐页对拍保证不漂移。规则本身写在 docs/DESIGN-REFRESH-2026-10-10.md。
   级别只从页面已渲染出的事实现读（分级徽标 + 来源类型标签），不在这里另定一份真相。 */
const LV_ORDER = { L0: 0, L1: 1, L2: 2, L3: 3 };
const ST_LV = {
  official_cn: 'L0', official_en: 'L1', datamine_cn: 'L0',
  fan_db: 'L2', media_cn: 'L2', video: 'L2'
};
const SEL = '.card, .mod, .dcard, .drawer';

export function levelOfCard(c) {
  let worst = null;
  const take = (k) => {
    if (!Object.prototype.hasOwnProperty.call(LV_ORDER, k || '')) return;
    if (worst === null || LV_ORDER[k] > LV_ORDER[worst]) worst = k;
  };
  c.querySelectorAll('.pill').forEach((p) => {
    // 图例里的徽标数的是全站分布，不是这张卡的数据，见 docs/DESIGN-REFRESH-2026-10-10.md
    if (p.closest('.covnum, .legend, .tlegend, .chipsrow, .cov')) return;
    const m = /\bL([0-3])\b/.exec(p.className);
    if (m) take('L' + m[1]);
  });
  c.querySelectorAll('.src .st').forEach((s) => {
    take(ST_LV[[...s.classList].find((x) => x !== 'st')]);
  });
  return worst;
}

export function applyRails(root) {
  if (!root) return 0;
  let n = 0;
  root.querySelectorAll(SEL).forEach((c) => {
    if (c.dataset.lv) { c.classList.add('rail'); n += 1; return; }   // 显式定级：补类，不重新推断
    const lv = levelOfCard(c);
    if (!lv) return;
    c.classList.add('rail');
    c.dataset.lv = lv;
    n += 1;
  });
  return n;
}
