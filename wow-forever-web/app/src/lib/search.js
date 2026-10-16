/* 全站搜索的纯逻辑：索引条目 → 排序 → 分组 → 跳转目标。
   索引本身由 tools/build-data.js 从各数据文件派生（src/data/search.json），
   这里只负责"怎么搜、怎么排、跳到哪"，方便在 tests/ 里直接断言。 */
import { linkFor, legacyUrl } from './nav.js';

// 一条 = [类型, 名称, 归属副标题, 跳转附加参数, 分级]
// 必须与旧站 src/js/app.js 的 SKIND_ORDER 同一份表（build-data.js 只核对旧站那份）。
// 少一个板块不是"顺序不同"，是那一类在新站搜索里根本不出结果——分组是按这张表列出来的，
// 不在表里的类型会被静默丢掉。2026-10-16 补齐时顺手发现 'rdd'（团本）原来就漏在这里。
export const KIND_ORDER = ['cls', 'race', 'tal', 'lpg', 'lch', 'chg', 'term', 'abl', 'spl', 'ach',
  'dun', 'boss', 'rdd', 'zone', 'rare', 'bok', 'camp', 'prof', 'rec', 'gnd', 'tra'];
export const GROUP_SHOWN = 5;
export const HIT_LIMIT = 120;

/* 完全同名优先，其次前缀，再次包含；都不匹配返回 -1。 */
export function scoreName(name, needle) {
  const n = String(name == null ? '' : name).toLowerCase();
  const k = String(needle == null ? '' : needle).trim().toLowerCase();
  if (!k) return -1;
  if (n === k) return 0;
  if (n.indexOf(k) === 0) return 1;
  if (n.indexOf(k) > 0) return 2;
  return -1;
}

export function searchRun(items, query, limit = HIT_LIMIT) {
  const k = String(query || '').trim().toLowerCase();
  if (!k || !Array.isArray(items)) return [];
  const hits = [];
  items.forEach((it) => {
    const sc = scoreName(it[1], k);
    if (sc < 0) return;
    hits.push([sc, KIND_ORDER.indexOf(it[0]), String(it[1]).length, it]);
  });
  hits.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
  return hits.slice(0, limit).map((h) => h[3]);
}

/* 按板块分组：组内先列前几条，剩下的进对应页面看（并给出那一类的总命中数）。 */
export function searchGroups(items, query, kinds, shown = GROUP_SHOWN) {
  const hits = searchRun(items, query);
  const by = {};
  hits.forEach((it) => { (by[it[0]] = by[it[0]] || []).push(it); });
  const groups = KIND_ORDER.filter((k) => by[k] && kinds && kinds[k]).map((k) => ({
    k,
    label: kinds[k][0],
    page: kinds[k][1],
    param: kinds[k][2],
    all: by[k].length,
    show: by[k].slice(0, shown)
  }));
  return { groups, total: hits.length };
}

export function queryString(extra, param, name) {
  const qs = [];
  if (extra) qs.push(extra);
  if (param && name) qs.push(param + '=' + encodeURIComponent(name));
  return qs.length ? '?' + qs.join('&') : '';
}

/* 全站已迁：目标页一律走站内路由，query 塞进 to 对象（平铺 { to, query } 经 v-bind
   会把 query 掉进 fallthrough 属性静默丢失——2026-10-13 修正，与 ClassesPage calcLink 同形）。 */
export function itemLink(kinds, it) {
  const kd = kinds && kinds[it[0]];
  if (!kd) return { href: legacyUrl('index.html') };
  const file = kd[1] + queryString(it[3], kd[2], it[1]);
  const lk = linkFor(file);
  if (lk.to) {
    const query = {};
    String(it[3] || '').split('&').forEach((p) => {
      if (!p) return;
      const i = p.indexOf('=');
      query[i < 0 ? p : p.slice(0, i)] = i < 0 ? '' : decodeURIComponent(p.slice(i + 1));
    });
    if (kd[2]) query[kd[2]] = it[1];
    return { to: { path: lk.to, query } };
  }
  return { href: legacyUrl(file) };
}

export function groupLink(kinds, g, query) {
  const file = g.param ? g.page + '?' + g.param + '=' + encodeURIComponent(query) : g.page;
  return linkFor(file);
}
