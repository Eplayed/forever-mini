/* 轻量隐私友好统计与转化归因层（2026-11-25）。
   设计原则：
   1. 零 Cookie、不收集个人身份信息、尊重浏览器 DNT；
   2. 严格按 data/analytics.json 中的 allowedHosts 控制是否发包：本地预览、自动化门禁与 GitHub Pages
      绝不向不存在的 /api/t 发请求，彻底避免 404 噪声；
   3. 生产域名 paoben.top 走同源 FC 3.0 的 POST /api/t（sendBeacon 优先，fetch keepalive 兜底），
      并预留可选第三方轻量统计提供商（umami / baidu / clarity），配置好白名单脚本后免改代码生效；
   4. 所有异常静默吸收，绝不阻塞页面渲染与用户交互。 */
import { load } from './data.js';

const SID_KEY = 'wow_forever_v1_sid';
const MAX_STAY_MS = 30 * 60 * 1000;
const MIN_STAY_MS = 300;
const MAX_BUFFER = 80;

const ALLOWED_PROVIDER_HOSTS = {
  umami: /^https:\/\/[a-z0-9.-]+\//i,
  baidu: /^https:\/\/hm\.baidu\.com\/hm\.js\?[a-z0-9]+$/i,
  clarity: /^https:\/\/www\.clarity\.ms\/tag\/[a-z0-9]+$/i
};

let cfg = null;
let ready = false;
let initialized = false;
let currentPath = '/';
let pageEnteredAt = 0;
let stayFlushed = false;
let thirdPartyInjected = false;
const viewedSlots = new Set();
const eventBuffer = [];

export function getViewportBucket(width) {
  const w = Number(width || (typeof window !== 'undefined' ? window.innerWidth : 0)) || 0;
  if (w >= 1600) return 'wide';
  if (w >= 1200) return 'desktop';
  if (w >= 768) return 'tablet';
  return 'mobile';
}

export function extractHost(url) {
  try {
    const u = new URL(String(url || ''), typeof location !== 'undefined' ? location.href : 'https://paoben.top/');
    return (u.hostname || '').toLowerCase().slice(0, 80);
  } catch (_) {
    return '';
  }
}

export function getSessionId() {
  try {
    let sid = window.sessionStorage.getItem(SID_KEY);
    if (!sid) {
      sid = (Date.now().toString(36) + Math.random().toString(36).slice(2, 8)).slice(0, 16);
      window.sessionStorage.setItem(SID_KEY, sid);
    }
    return sid;
  } catch (_) {
    return '';
  }
}

export function isDntEnabled() {
  try {
    const nav = typeof navigator !== 'undefined' ? navigator : {};
    const win = typeof window !== 'undefined' ? window : {};
    return nav.doNotTrack === '1' || win.doNotTrack === '1' || nav.msDoNotTrack === '1';
  } catch (_) {
    return false;
  }
}

export function isHostAllowed(config, hostname) {
  if (!config || !config.enabled) return false;
  if (config.respectDnt && isDntEnabled()) return false;
  const hosts = Array.isArray(config.allowedHosts) ? config.allowedHosts : [];
  if (!hosts.length) return false;
  const h = String(hostname || (typeof location !== 'undefined' ? location.hostname : '')).toLowerCase();
  return hosts.some((x) => String(x || '').toLowerCase() === h);
}

function recordBuffer(payload) {
  eventBuffer.push(payload);
  if (eventBuffer.length > MAX_BUFFER) eventBuffer.shift();
}

function sendBeaconPayload(endpoint, payload) {
  try {
    const body = JSON.stringify(payload);
    if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
      const blob = new Blob([body], { type: 'application/json' });
      if (navigator.sendBeacon(endpoint, blob)) return true;
    }
    if (typeof fetch === 'function') {
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true
      }).catch(() => {});
      return true;
    }
  } catch (_) {}
  return false;
}

function injectProviderScript(provider) {
  if (thirdPartyInjected || typeof document === 'undefined' || !provider) return;
  const type = String(provider.type || 'none');
  if (type === 'none') return;
  const rule = ALLOWED_PROVIDER_HOSTS[type];
  const url = String(provider.scriptUrl || '');
  const siteId = String(provider.siteId || '').trim();
  if (!rule || !rule.test(url)) return;
  if (type === 'umami' && !siteId) return;
  thirdPartyInjected = true;
  try {
    const s = document.createElement('script');
    s.async = true;
    s.defer = true;
    s.src = url;
    if (type === 'umami') s.setAttribute('data-website-id', siteId);
    document.head.appendChild(s);
  } catch (_) {}
}

export function trackEvent(ev, extra = {}) {
  try {
    const payload = {
      ev: String(ev || ''),
      p: String(extra.p || currentPath || '/').slice(0, 120),
      sid: getSessionId(),
      vw: getViewportBucket()
    };
    if (extra.ref) payload.ref = String(extra.ref).slice(0, 80);
    if (extra.slot) payload.slot = String(extra.slot).slice(0, 64);
    if (extra.kind) payload.kind = String(extra.kind).slice(0, 32);
    if (extra.pos) payload.pos = String(extra.pos).slice(0, 32);
    if (extra.host) payload.host = String(extra.host).slice(0, 80);
    if (typeof extra.ms === 'number' && Number.isFinite(extra.ms)) {
      payload.ms = Math.max(0, Math.min(MAX_STAY_MS, Math.round(extra.ms)));
    }
    if (typeof extra.hit === 'boolean') payload.hit = extra.hit;

    recordBuffer(payload);

    if (!ready || !cfg || !isHostAllowed(cfg)) return false;
    const fc = cfg.fcBeacon || {};
    if (fc.enabled && fc.endpoint) {
      return sendBeaconPayload(fc.endpoint, payload);
    }
  } catch (_) {}
  return false;
}

export function trackSlotView(slot) {
  if (!slot || !slot.id) return false;
  const dedupeKey = `${slot.id}|${currentPath || '/'}`;
  if (viewedSlots.has(dedupeKey)) return false;
  viewedSlots.add(dedupeKey);
  return trackEvent('slot_view', {
    slot: slot.id,
    kind: slot.kind || '',
    pos: slot.position || '',
    host: slot.url ? extractHost(slot.url) : ''
  });
}

export function trackSlotClick(slot) {
  if (!slot || !slot.id) return false;
  return trackEvent('slot_click', {
    slot: slot.id,
    kind: slot.kind || '',
    pos: slot.position || '',
    host: slot.url ? extractHost(slot.url) : ''
  });
}

function flushStay(reasonPath) {
  if (stayFlushed || !pageEnteredAt) return;
  const elapsed = Date.now() - pageEnteredAt;
  stayFlushed = true;
  if (elapsed >= MIN_STAY_MS) {
    trackEvent('page_stay', { p: reasonPath || currentPath || '/', ms: elapsed });
  }
}

function handleDocumentClick(e) {
  try {
    const target = e && e.target && typeof e.target.closest === 'function' ? e.target.closest('a[href]') : null;
    if (!target) return;
    // 带 data-slot-id 的链接已由组件自身的 trackSlotClick 记账，避免重复计数
    if (target.hasAttribute('data-slot-id')) return;
    const href = target.getAttribute('href') || '';
    if (!/^https?:\/\//i.test(href)) return;
    const host = extractHost(href);
    const selfHost = typeof location !== 'undefined' ? location.hostname.toLowerCase() : '';
    if (!host || host === selfHost) return;
    trackEvent('outbound_click', { host });
  } catch (_) {}
}

function handleVisibility() {
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    flushStay(currentPath);
  } else if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
    pageEnteredAt = Date.now();
    stayFlushed = false;
  }
}

function handlePageHide() {
  flushStay(currentPath);
}

export function initAnalytics(router, customConfig) {
  if (initialized) return Promise.resolve(cfg);
  initialized = true;

  const boot = (doc) => {
    cfg = doc && typeof doc === 'object' ? doc : { enabled: false };
    ready = true;
    if (isHostAllowed(cfg)) {
      injectProviderScript(cfg.provider);
    }
    const initRoute = router && router.currentRoute && router.currentRoute.value;
    currentPath = (initRoute && initRoute.path) || '/';
    pageEnteredAt = Date.now();
    stayFlushed = false;
    const refHost = typeof document !== 'undefined' && document.referrer ? extractHost(document.referrer) : '';
    const selfHost = typeof location !== 'undefined' ? location.hostname.toLowerCase() : '';
    trackEvent('pv', {
      p: currentPath,
      ref: refHost && refHost !== selfHost ? refHost : ''
    });

    if (router && typeof router.afterEach === 'function') {
      router.afterEach((to, from) => {
        if (from && from.path && from.path !== to.path) {
          flushStay(from.path);
        }
        currentPath = (to && to.path) || '/';
        pageEnteredAt = Date.now();
        stayFlushed = false;
        trackEvent('pv', { p: currentPath });
        if (to && to.path === '/' && to.query && String(to.query.q || '').trim()) {
          trackEvent('search', { p: '/' });
        }
      });
    }

    if (typeof document !== 'undefined') {
      document.addEventListener('click', handleDocumentClick, { capture: true });
      document.addEventListener('visibilitychange', handleVisibility);
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('pagehide', handlePageHide);
    }
    return cfg;
  };

  if (customConfig) {
    return Promise.resolve(boot(customConfig));
  }
  return load('data/analytics.json')
    .then(boot)
    .catch(() => {
      cfg = { enabled: false };
      ready = true;
      return cfg;
    });
}

export function getAnalyticsBuffer() {
  return eventBuffer.slice();
}

export function resetAnalyticsForTest() {
  if (typeof document !== 'undefined') {
    document.removeEventListener('click', handleDocumentClick, { capture: true });
    document.removeEventListener('visibilitychange', handleVisibility);
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('pagehide', handlePageHide);
  }
  cfg = null;
  ready = false;
  initialized = false;
  currentPath = '/';
  pageEnteredAt = 0;
  stayFlushed = false;
  thirdPartyInjected = false;
  viewedSlots.clear();
  eventBuffer.length = 0;
}
