/* 纯函数：分级徽标、时间、搜索高亮、来源标签。
   旧站这些逻辑散在字符串拼接里，没法单测；这里全部拆成纯函数，tests/ 里直接断言。 */

export const PILL_NAME = { L0: '已官方核实', L1: '仅官方英文', L2: '待实测', L3: '缺数据' };

export function pillLevel(level) {
  return PILL_NAME[level] ? level : 'L3';
}

export const TYPE_LABEL = {
  official_cn: '官方中文', official_en: '官方英文', datamine_cn: '客户端解包',
  fan_db: '第三方资料站', media_cn: '中文转载', video: '实测视频',
  'site-promise': '本站承诺', 'site-note': '本站说明'
};

export function typeLabel(t) {
  return TYPE_LABEL[t] || t || '来源';
}

/* 上线时间固定：2026-11-05 00:00 +08:00（国服口径）。
   日期只有 data/meta.json 一处真相，tools/build-data.js 会卡这里和旧站 app.js 的常量是否一致。 */
export const LAUNCH_AT = Date.parse('2026-11-05T00:00:00+08:00');

export function launchLeft(now) {
  const ms = Math.max(0, LAUNCH_AT - (now === undefined ? Date.now() : now));
  return {
    d: Math.floor(ms / 86400000), h: Math.floor(ms / 3600000) % 24,
    m: Math.floor(ms / 60000) % 60, s: Math.floor(ms / 1000) % 60
  };
}

export function pad2(n) { return (n < 10 ? '0' : '') + n; }

/* 倒计时读数：顶栏那条写"26 天 04:23:11"，首页那块把天数单独放大 */
export function clockText(l) {
  return pad2(l.h) + ':' + pad2(l.m) + ':' + pad2(l.s);
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/* 时间表里"待定""择期"这类没具体日期的条目排最后，别顶掉首屏 */
export function byDate(a, b) {
  const ra = DATE_RE.test(a.date || ''), rb = DATE_RE.test(b.date || '');
  if (ra && rb) return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
  if (ra !== rb) return ra ? -1 : 1;
  const sa = String(a.date || ''), sb = String(b.date || '');
  return sa < sb ? -1 : sa > sb ? 1 : 0;   // 都没日期时按文字排，结果与输入顺序无关
}

/* 搜索高亮：返回 [{t, hit}] 片段，模板里用 <mark> 渲染。
   旧站是拼 HTML 字符串（D.hl），新站不拼字符串也不 v-html——转义交给 Vue。 */
export function hlParts(text, query) {
  const s = String(text == null ? '' : text);
  const q = String(query || '').trim();
  if (!q) return [{ t: s, hit: false }];
  const hay = s.toLowerCase(), needle = q.toLowerCase();
  const out = [];
  let i = 0;
  while (i < s.length) {
    const at = hay.indexOf(needle, i);
    if (at < 0) { out.push({ t: s.slice(i), hit: false }); break; }
    if (at > i) out.push({ t: s.slice(i, at), hit: false });
    out.push({ t: s.slice(at, at + needle.length), hit: true });
    i = at + needle.length;
  }
  return out.length ? out : [{ t: '', hit: false }];
}

/* 等级区间 → 中文读数。数据里 [null, null] 与缺字段都要落到"客户端暂时没给出"。 */
export function levelRangeText(rec) {
  const a = (rec && rec.levelRange) || [];
  const lo = a[0], hi = a[1];
  if (lo === undefined || lo === null) {
    return (rec && rec.levelStatus && rec.levelStatus !== 'ok') ? rec.levelStatus : '—';
  }
  if (hi === undefined || hi === null || hi === lo) return lo + ' 级';
  return lo + '–' + hi + ' 级';
}

export function lvStart(rec) {
  const a = (rec && rec.levelRange) || [];
  return (a[0] === null || a[0] === undefined) ? 99 : a[0];
}
/* 时间点分档：与旧站 src/js/app.js 的 tlCounts 同一算法；now 由调用方给，方便单测。 */
export function tlCounts(items, now) {
  const n = now === undefined ? Date.now() : now;
  let done = 0, upcoming = 0;
  (items || []).forEach((x) => {
    const t = /^\d{4}-\d{2}-\d{2}$/.test(x.date || '') ? new Date(x.date + 'T00:00:00+08:00').getTime() : null;
    if (t === null) return;
    if (t <= n) done += 1; else upcoming += 1;
  });
  return { done: done, upcoming: upcoming };
}
