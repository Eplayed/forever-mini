/* 导航结构与旧站 app.js 的 NAV 一一对应（两级常驻：一级是分组标签，二级项全部露出，说明进 title），
   但只写"旧文件名"，由 linkFor() 决定这个入口走新站路由还是回旧站——迁一页改一处，不会漏改。 */
import { MIGRATED } from '../router.js';

/* 与旧站 src/js/app.js 的 NAV 曾经逐字一致。**2026-10-16 站主决定收窄新站导航，两栈从此有意不同**：
   世界那一组只留「区域与稀有 / 副本 / 团本」，工具那一组只留「排行」。
   旧站已冻结，导航保持原来 17 格不动——**不要把这份表又"同步"回旧站，也不要照旧站把这两组补回来**。
   被摘掉导航的 7 页（成就、系统规则、物品库、速查、时间表、动态、溯源）页面照旧在，
   入口走首页的板块卡与首页底部那四个小链接（站主选的"只摘导航，其余不动"）。
   **2026-10-28 站主改这一条**：宠物页上线后他在首页与线上都找不到入口，要求导航加一格 + 首页加一张卡，
   这一组从 11 格变 12 格；**2026-10-30 站主要宏命令上导航，工具组再加一格，共 13 格**。
   再要摘回 12 格 / 11 格，先改这条。这 13 格的名字与顺序由 site-check 的 [16] 节钉住。 */
export const NAV = [
  { t: '首页', file: 'index.html', d: '数据覆盖率与全部入口' },
  { t: '天赋', items: [
    { file: 'talent.html', t: '计算器', d: '9 职业 · 树结构与加点' }] },
  { t: '职业', items: [
    { file: 'classes.html', t: '职业', d: '9 职业逐页：三系与节点数、技能变化、可选种族' },
    { file: 'chooser.html', t: '玩法问答', d: '7 题玩法取向问答，不是强度排行' },
    { file: 'legacy.html', t: '传承', d: '三棵专长树与全部传承挑战，每条点数照客户端写' },
    // 2026-10-28 站主：这一页上线后他在首页和线上都找不到入口。说明里不写"18 家族 / 22 技能"
    // 那种数——和上面世界那一组同一条理由，数会随采集变，写死在导航里就是发给玩家的假数。
    { file: 'pets.html', t: '宠物', d: '猎人宠物家族与技能：三项修正、几级能学、会哪些技能' } ] },
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
  // 2026-10-30 站主：宏命令上线要导航加入口，这一组从 1 格变 2 格。
  // 说明里不写条数（"245 条"那种）——数会随采集变，写死在导航里就是发给玩家的假数。
  { t: '工具', items: [
    { file: 'rank.html', t: '排行', d: '本站资料完整度排序，不是强度（仅网页）' },
    { file: 'macros.html', t: '宏命令', d: '9 职业宏库：按用途分组、写清几级能用、宏正文一键复制' } ] }
];

/* 站内地址只有这一种产出方式（2026-10-24 旧站删除后，`legacyUrl()` 与它的地址基准一起撤掉）。
   为什么绝不让 `<a href>` 出现文件式地址：这一站由托管方按静态目录发，`talent.html`
   那种地址要么 404、要么被 SPA 兜底成 200 + index.html——hash 路由拿不到路由，
   点完只是"重新回到首页"，看起来就是**点了没反应**（2026-10-18 首页 12 处全是这个毛病）。
   所以一律出 #/路由；带查询的照带；旧站那种 #锚点 改成 ?to=，由目标页自己滚。
   认不出的文件名交给路由表的 catch-all，由 Unmigrated 送去有内容的一页，不静默变死链。 */
function internal(s) {
  const base = s.split('?')[0].split('#')[0];
  const to = MIGRATED[base];
  if (!to) return '/' + s.replace(/^\/+/, '');
  const qi = s.indexOf('?');
  const hi = s.indexOf('#');
  const q = qi >= 0 ? s.slice(qi + 1).split('#')[0] : '';
  const frag = hi >= 0 ? s.slice(hi + 1) : '';
  const qs = [];
  if (q) qs.push(q);
  if (frag) qs.push('to=' + encodeURIComponent(frag));
  return to + (qs.length ? '?' + qs.join('&') : '');
}

/* 给 <a href> 用（前面加 # 才是 hash 路由的完整地址）。 */
export function hrefOf(file) {
  return '#' + internal(String(file || ''));
}

/* 给 router-link 用：v-bind 上去的必须是 { to } 对象——平铺成 { to, query }
   再 v-bind 的话 query 会掉进 fallthrough 属性里静默丢失（2026-10-13 发现）。 */
export function linkFor(file) {
  const s = String(file || '');
  const loc = internal(s);
  const qi = loc.indexOf('?');
  if (qi < 0) return { to: loc };
  const query = {};
  loc.slice(qi + 1).split('&').forEach((p) => {
    if (!p) return;
    const i = p.indexOf('=');
    query[i < 0 ? p : p.slice(0, i)] = i < 0 ? '' : decodeURIComponent(p.slice(i + 1));
  });
  return { to: { path: loc.slice(0, qi), query } };
}
