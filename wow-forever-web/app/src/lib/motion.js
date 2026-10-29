/* 交互动效的运行时那一小半。
   动效本体全在 styles/motion.css 里（CSS-only、可整轮撤回），只有"滚到某一处"这一件事
   必须由 JS 决定 behavior——直接写 behavior:'smooth' 的话，系统开了"减弱动态效果"的
   玩家还是会被滑一段，浏览器不替我们兜这个。规格见 docs/PLAN-网页交互动效-2026-10-29.md。 */
const reduceMotion = () =>
  !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

export function scrollToEl(el, opt = {}) {
  if (!el || !el.scrollIntoView) return;
  el.scrollIntoView({ block: opt.block || 'start', behavior: reduceMotion() ? 'auto' : 'smooth' });
}
