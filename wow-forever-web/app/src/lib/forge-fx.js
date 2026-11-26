/* forge-fx.js —— 黑曜锻炉全站交互光影、3D 金属倾角与快捷键引擎（零外部依赖）
   1. 鼠标金光追踪（--mx / --my）：事件委托挂在 document，所有卡片/职业格/团本卡/插件卡共享；
   2. 3D 金属倾角（perspective + rotateX/rotateY + 轻浮起）：悬停跟手响应（60ms），离场平滑归位；
   3. 快捷搜（Ctrl+K / Cmd+K / '/'）：首页聚焦主搜索框 #gs，其余页聚焦顶栏搜索框。 */

const SPOT_SEL = '.cls9 > a, .classbar .cls, .hrt .hrt-b, .mod, .raidcard-v2, .card.go, .addon-card, .heros .cd, .sr-card, [data-forge-spot]';
const TILT_SEL = '.cls9 > a, .classbar .cls, .hrt .hrt-b, .heros .cd, [data-forge-tilt]';

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return true;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function isFinePointer() {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
}

function isTypingTarget(el) {
  if (!el || !el.tagName) return false;
  const tag = el.tagName.toUpperCase();
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
}

export function initForgeFx() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return () => {};

  let activeEl = null;
  let rafId = 0;
  let lastEvt = null;

  function resetTilt(el) {
    if (!el) return;
    el.style.removeProperty('transition');
    el.style.removeProperty('transform');
    el.style.removeProperty('--mx');
    el.style.removeProperty('--my');
  }

  function applyPointer() {
    rafId = 0;
    const e = lastEvt;
    if (!e) return;
    const target = e.target && e.target.closest ? e.target.closest(SPOT_SEL) : null;
    if (activeEl && activeEl !== target) {
      resetTilt(activeEl);
    }
    activeEl = target;
    if (!target || prefersReducedMotion()) return;

    const rect = target.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = Math.max(0, Math.min(rect.width, e.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
    target.style.setProperty('--mx', Math.round(x) + 'px');
    target.style.setProperty('--my', Math.round(y) + 'px');

    if (isFinePointer() && target.matches && target.matches(TILT_SEL)) {
      const rx = ((y / rect.height) - 0.5) * -12;
      const ry = ((x / rect.width) - 0.5) * 14;
      target.style.transition = 'transform 65ms ease-out';
      target.style.transform =
        'perspective(660px) rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg) translateY(-5px) scale3d(1.02,1.02,1.02)';
    }
  }

  function onPointerMove(e) {
    lastEvt = e;
    if (!rafId) rafId = window.requestAnimationFrame(applyPointer);
  }

  function onPointerLeave() {
    if (activeEl) {
      resetTilt(activeEl);
      activeEl = null;
    }
  }

  function onKeyDown(e) {
    if (!e) return;
    const isK = (e.ctrlKey || e.metaKey) && String(e.key || '').toLowerCase() === 'k';
    const isSlash = !e.ctrlKey && !e.metaKey && !e.altKey && e.key === '/' && !isTypingTarget(e.target);
    if (!isK && !isSlash) return;
    const box = document.getElementById('gs') || document.querySelector('.top-search input');
    if (!box) return;
    e.preventDefault();
    box.focus();
    if (typeof box.select === 'function') box.select();
  }

  document.addEventListener('pointermove', onPointerMove, { passive: true });
  document.addEventListener('pointerleave', onPointerLeave, { passive: true });
  window.addEventListener('blur', onPointerLeave);
  document.addEventListener('keydown', onKeyDown);

  return () => {
    if (rafId) window.cancelAnimationFrame(rafId);
    if (activeEl) resetTilt(activeEl);
    document.removeEventListener('pointermove', onPointerMove);
    document.removeEventListener('pointerleave', onPointerLeave);
    window.removeEventListener('blur', onPointerLeave);
    document.removeEventListener('keydown', onKeyDown);
  };
}
