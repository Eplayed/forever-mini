/* 导航结构与旧站 app.js 的 NAV 一一对应（两级常驻：一级是分组标签，二级项全部露出，说明进 title），
   但只写"旧文件名"，由 linkFor() 决定这个入口走新站路由还是回旧站——迁一页改一处，不会漏改。 */
import { MIGRATED } from '../router.js';

/* 与旧站 src/js/app.js 的 NAV 同一份表：项名、顺序、说明文字（title）逐字对齐。
   两栈各写一份必然会飘（2026-10-12 就发现这里少了「团本」一格、传承的说明也不是同一句），
   改导航必须两处一起改，改完跑 tools/app-parity.py --strict 与 site-check 的导航那组断言。 */
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
    { file: 'world.html', t: '区域与稀有', d: '44 个区域 · 36 个稀有刷新点 · 书籍与营地' },
    { file: 'dungeons.html', t: '副本', d: '38 座按十级一档分：首领与掉落归属' },
    { file: 'raids.html', t: '团本', d: '客户端能排到的团队条目与另一份名单对照' },
    { file: 'systems.html', t: '系统规则', d: '规则、区域、装备名的官方中文说法' }] },
  { t: '专业', items: [
    { file: 'professions.html', t: '配方', d: '13 个专业 · 配方材料与采集点' }] },
  { t: '工具', items: [
    { file: 'glossary.html', t: '速查', d: '中英术语，点一下即复制' },
    { file: 'timeline.html', t: '时间表', d: '11 个上线时间点带官方原文' },
    { file: 'updates.html', t: '动态', d: '官方时间点 + 客户端改动（仅网页）' },
    { file: 'rank.html', t: '排行', d: '本站资料完整度排序，不是强度（仅网页）' },
    { file: 'provenance.html', t: '溯源', d: '哪些已核实、哪些只是线索' }] }
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

/* 迁完一页要做两件事：路由表加一条，这里标记一下已迁（导航才会走内部链接） */
export const MIGRATION_NOTE = '新站已迁：首页 / 世界页 / 职业页；其余 15 页仍在旧站。';
