/* 导航结构与旧站 app.js 的 NAV 一一对应（两级常驻：一级是分组标签，二级项全部露出，说明进 title），
   但只写"旧文件名"，由 linkFor() 决定这个入口走新站路由还是回旧站——迁一页改一处，不会漏改。 */
import { MIGRATED } from '../router.js';

/* 与旧站 src/js/app.js 的 NAV 曾经逐字一致。**2026-10-16 站主决定收窄新站导航，两栈从此有意不同**：
   世界那一组只留「区域与稀有 / 副本 / 团本」，工具那一组只留「排行」。
   旧站已冻结，导航保持原来 17 格不动——**不要把这份表又"同步"回旧站，也不要照旧站把这两组补回来**。
   被摘掉导航的 7 页（成就、系统规则、物品库、速查、时间表、动态、溯源）页面照旧在，
   入口走首页的板块卡与首页底部那四个小链接（站主选的"只摘导航，其余不动"）。
   收窄后的 11 格由 site-check 的 [16] 节钉住名字与顺序。 */
export const NAV = [
  { t: '首页', file: 'index.html', d: '数据覆盖率与全部入口' },
  { t: '天赋', items: [
    { file: 'talent.html', t: '计算器', d: '9 职业 · 树结构与加点' }] },
  { t: '职业', items: [
    { file: 'classes.html', t: '职业', d: '9 职业逐页：三系与节点数、技能变化、可选种族' },
    { file: 'chooser.html', t: '玩法问答', d: '7 题玩法取向问答，不是强度排行' },
    { file: 'legacy.html', t: '传承', d: '三棵专长树与全部传承挑战，每条点数照客户端写' }] },
  { t: '种族', items: [
    { file: 'races.html', t: '总览', d: '10 个种族行 · 可选职业矩阵' }] },
  { t: '世界', items: [
    // 说明里不写稀有条数：那个数会随采集变（10-16 从 36 走到 362），写在导航里就是发给玩家的假数
    { file: 'world.html', t: '区域与稀有', d: '44 个区域 · 稀有精英刷新点 · 书籍与营地' },
    { file: 'dungeons.html', t: '副本', d: '38 座按十级一档分：首领与掉落归属' },
    { file: 'raids.html', t: '团本', d: '客户端能排到的团队条目与另一份名单对照' }] },
  { t: '专业', items: [
    { file: 'professions.html', t: '配方', d: '13 个专业 · 配方材料与采集点' }] },
  // 站主 2026-10-16 定：配装单独一组（旧站没有这一页，linkFor 走 MIGRATED 里的 bis.html → /bis）
  { t: '配装', items: [
    { file: 'bis.html', t: '配装', d: '30 级各职业各专精的部位名单与同部位备选（本站整理，不是官方结论）' }] },
  { t: '工具', items: [
    { file: 'rank.html', t: '排行', d: '本站资料完整度排序，不是强度（仅网页）' }] }
];

const LEGACY = (import.meta.env.VITE_LEGACY_BASE || '/');

export function legacyUrl(file) {
  const clean = String(file || '').replace(/^\/+/, '');
  return LEGACY.replace(/\/$/, '/') + clean;
}

/* 返回 { to } 走 router-link，或 { href } 走旧站。锚点（races.html#traits）一律回旧站。
   带查询串的入口（world.html?t=rares&q=…）按文件名查表，query 交给调用方传。 */
export function linkFor(file) {
  const base = String(file || '').split(/[?#]/)[0];
  if (/#/.test(file)) return { href: legacyUrl(file) };
  return MIGRATED[base] ? { to: MIGRATED[base] } : { href: legacyUrl(file) };
}

export function isMigrated(file) {
  return !!MIGRATED[String(file || '').split(/[?#]/)[0]];
}

/* 带查询串的旧站文件链接 → 站内 { to: { path, query } }。linkFor 只按文件名查表（query 会丢），
   首页天赋预览的格子（talent.html?c=..&tree=..&q=..）这类要保参数的入口走这里。
   to 用 router-link 原生的对象形式——平铺成 { to, query } 再 v-bind 的话 query 会掉进
   fallthrough 属性里静默丢失（2026-10-13 全量迁移时发现并修正）。
   未迁的页原样返回 { href }（含 query），与 linkFor 一致。 */
export function linkForQ(file) {
  const l = linkFor(file);
  if (!l.to) return l;
  const query = {};
  (String(file || '').split('?')[1] || '').split('&').forEach((p) => {
    if (!p) return;
    const i = p.indexOf('=');
    query[i < 0 ? p : p.slice(0, i)] = i < 0 ? '' : decodeURIComponent(p.slice(i + 1));
  });
  return { to: { path: l.to, query } };
}

/* 迁完一页要做两件事：路由表加一条，这里标记一下已迁（导航才会走内部链接） */
export const MIGRATION_NOTE = '2026-10-13 全量迁移：18 个旧页已全部迁入 Vue 新站。';
