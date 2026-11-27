/* forge-fx.js —— 黑曜锻炉全站交互光影、3D 金属倾角、手动特效开关与快捷键引擎
   1. 不再因 Windows「调整为最佳性能」导致的 prefers-reduced-motion 而静默关闭装饰特效，
      改为默认开启 + 左侧导航栏底部提供一键手动「特效 开/关」（存 localStorage）；
   2. 鼠标金光追踪（--mx / --my）与 3D 金属倾角（perspective + rotateX/Y，65ms 跟手响应）；
   3. 快捷搜（Ctrl+K / Cmd+K / '/'）：首页聚焦主搜索框 #gs，其余页聚焦顶栏搜索框。 */

const FX_KEY = 'wow_forever_v1_forge_fx';
const SPOT_SEL = '.cls9 > a, .classbar .cls, .hrt .hrt-b, .mod, .raidcard-v2, .card.go, .addon-card, .heros .cd, .sr-card, [data-forge-spot]';
const TILT_SEL = '.cls9 > a, .classbar .cls, .hrt .hrt-b, .heros .cd, [data-forge-tilt]';

function readSavedOff() {
  try {
    return typeof window !== 'undefined' && window.localStorage
      && window.localStorage.getItem(FX_KEY) === '0';
  } catch (_) {
    return false;
  }
}

function fxDisabled() {
  return typeof document !== 'undefined'
    && document.documentElement.classList.contains('forge-fx-off');
}

export function isForgeFxOff() {
  if (fxDisabled()) return true;
  if (readSavedOff()) {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.add('forge-fx-off');
    }
    return true;
  }
  return false;
}

export function setForgeFxOff(off) {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('forge-fx-off', !!off);
  }
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(FX_KEY, off ? '0' : '1');
    }
  } catch (_) {}
}

export function toggleForgeFx() {
  const next = !fxDisabled();
  setForgeFxOff(next);
  return !next;
}

function isFinePointer() {
  if (typeof window === 'undefined' || !window.matchMedia) return true;
  return !window.matchMedia('(pointer: coarse)').matches;
}

function isTypingTarget(el) {
  if (!el || !el.tagName) return false;
  const tag = el.tagName.toUpperCase();
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
}

export function initForgeFx() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return () => {};

  try {
    if (window.localStorage && window.localStorage.getItem(FX_KEY) === '0') {
      document.documentElement.classList.add('forge-fx-off');
    }
  } catch (_) {}

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
    if (!target || fxDisabled()) return;

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
