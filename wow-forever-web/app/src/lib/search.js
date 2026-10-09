/* 全站搜索的纯逻辑：索引条目 → 排序 → 分组 → 跳转目标。
   索引本身由 tools/build-data.js 从各数据文件派生（src/data/search.json），
   这里只负责"怎么搜、怎么排、跳到哪"，方便在 tests/ 里直接断言。 */
import { linkFor, legacyUrl } from './nav.js';

// 一条 = [类型, 名称, 归属副标题, 跳转附加参数, 分级]
export const KIND_ORDER = ['cls', 'race', 'tal', 'chg', 'term', 'abl', 'dun', 'boss', 'zone',
  'rare', 'bok', 'camp', 'prof', 'rec', 'gnd', 'tra'];
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

/* 迁移期：目标页已迁到新站就走路由（带 query），没迁就链回旧站文件。 */
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
    return { to: lk.to, query };
  }
  return { href: legacyUrl(file) };
}

export function groupLink(kinds, g, query) {
  const file = g.param ? g.page + '?' + g.param + '=' + encodeURIComponent(query) : g.page;
  return linkFor(file);
}
