import { createRouter, createWebHashHistory } from 'vue-router';
import HomePage from './pages/HomePage.vue';
import WorldPage from './pages/WorldPage.vue';
import ClassesPage from './pages/ClassesPage.vue';
import TalentPage from './pages/TalentPage.vue';
import ChooserPage from './pages/ChooserPage.vue';
import LegacyPage from './pages/LegacyPage.vue';
import RacesPage from './pages/RacesPage.vue';
import DungeonsPage from './pages/DungeonsPage.vue';
import DungeonPage from './pages/DungeonPage.vue';
import RaidsPage from './pages/RaidsPage.vue';
import SystemsPage from './pages/SystemsPage.vue';
import ProfessionsPage from './pages/ProfessionsPage.vue';
import GlossaryPage from './pages/GlossaryPage.vue';
import TimelinePage from './pages/TimelinePage.vue';
import SkillsPage from './pages/SkillsPage.vue';
import AchievementsPage from './pages/AchievementsPage.vue';
import UpdatesPage from './pages/UpdatesPage.vue';
import RankPage from './pages/RankPage.vue';
import ProvenancePage from './pages/ProvenancePage.vue';
import ItemsPage from './pages/ItemsPage.vue';
import Unmigrated from './pages/Unmigrated.vue';

/* 哪些旧页已经迁到新站：键是旧站的 html 文件名。
   导航与首页入口都查这张表决定走 router-link 还是链回旧站，避免"迁完一页忘了改链接"。
   2026-10-13 全量迁移：18 个旧页全部迁入，仅 index/world/classes 之外全部一次收编。
   带查询串的页（talent?c、dungeon?d）query 形态与旧站一致，页面内自行消费。
   items.html 不是旧页：物品库是新站独有页（旧站已冻结不加功能），借这张表让导航
   走内部路由并正确高亮——旧站没有这个文件，不会被任何旧链接命中。 */
export const MIGRATED = {
  'index.html': '/',
  'world.html': '/world',
  'classes.html': '/classes',
  'talent.html': '/talent',
  'chooser.html': '/chooser',
  'legacy.html': '/legacy',
  'races.html': '/races',
  'dungeons.html': '/dungeons',
  'dungeon.html': '/dungeon',
  'raids.html': '/raids',
  'systems.html': '/systems',
  'professions.html': '/professions',
  'glossary.html': '/glossary',
  'timeline.html': '/timeline',
  'skills.html': '/skills',
  'achievements.html': '/achievements',
  'updates.html': '/updates',
  'rank.html': '/rank',
  'provenance.html': '/provenance',
  'items.html': '/items'
};

const routes = [
  { path: '/', name: 'home', component: HomePage, meta: { title: '《魔兽世界：无限》中文资料' } },
  { path: '/world', name: 'world', component: WorldPage, meta: { title: '世界：区域、稀有与书' } },
  { path: '/classes', name: 'classes', component: ClassesPage, meta: { title: '职业：三系、技能变化与可选种族' } },
  { path: '/talent', name: 'talent', component: TalentPage, meta: { title: '天赋计算器' } },
  { path: '/chooser', name: 'chooser', component: ChooserPage, meta: { title: '选职业问答' } },
  { path: '/legacy', name: 'legacy', component: LegacyPage, meta: { title: '传承专长与挑战' } },
  { path: '/races', name: 'races', component: RacesPage, meta: { title: '种族与职业组合' } },
  { path: '/dungeons', name: 'dungeons', component: DungeonsPage, meta: { title: '副本手册' } },
  { path: '/dungeon', name: 'dungeon', component: DungeonPage, meta: { title: '副本详情' } },
  { path: '/raids', name: 'raids', component: RaidsPage, meta: { title: '团队副本名单' } },
  { path: '/systems', name: 'systems', component: SystemsPage, meta: { title: '系统与新区域' } },
  { path: '/professions', name: 'professions', component: ProfessionsPage, meta: { title: '专业与配方' } },
  { path: '/glossary', name: 'glossary', component: GlossaryPage, meta: { title: '中英术语速查' } },
  { path: '/timeline', name: 'timeline', component: TimelinePage, meta: { title: '上线与 Beta 时间表' } },
  { path: '/skills', name: 'skills', component: SkillsPage, meta: { title: '技能书' } },
  { path: '/achievements', name: 'achievements', component: AchievementsPage, meta: { title: '成就目录' } },
  { path: '/updates', name: 'updates', component: UpdatesPage, meta: { title: '最新动态' } },
  { path: '/rank', name: 'rank', component: RankPage, meta: { title: '职业资料完整度排行' } },
  { path: '/provenance', name: 'provenance', component: ProvenancePage, meta: { title: '溯源与覆盖率' } },
  // 新站独有页：数据来自 src/data/items.json（21,077 件全量名录）
  { path: '/items', name: 'items', component: ItemsPage, meta: { title: '物品库' } },
  // 全部迁完后这里只兜住旧书签里可能残留的其它地址
  { path: '/:all(.*)', name: 'unmigrated', component: Unmigrated, meta: { title: '这页还没迁过来' } }
];

const router = createRouter({
  // hash 模式：旧站是纯文件部署，换成 history 模式就得要求托管方配 rewrite；
  // 迁移期两套页面混着跳，少一个部署前提就少一类线上事故。
  history: createWebHashHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved || { top: 0 }
});

router.afterEach((to) => {
  document.title = (to.meta && to.meta.title ? to.meta.title + ' · ' : '') + '无限资料站';
});

export default router;
