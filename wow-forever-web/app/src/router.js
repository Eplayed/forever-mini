import { createRouter, createWebHashHistory } from 'vue-router';
import HomePage from './pages/HomePage.vue';
import WorldPage from './pages/WorldPage.vue';
import Unmigrated from './pages/Unmigrated.vue';

/* 哪些旧页已经迁到新站：键是旧站的 html 文件名。
   导航与首页入口都查这张表决定走 router-link 还是链回旧站，避免"迁完一页忘了改链接"。 */
export const MIGRATED = {
  'index.html': '/',
  'world.html': '/world'
};

const routes = [
  { path: '/', name: 'home', component: HomePage, meta: { title: '《魔兽世界：无限》中文资料' } },
  { path: '/world', name: 'world', component: WorldPage, meta: { title: '世界：区域、稀有与书' } },
  // 还没迁的路径不 404，明确告诉用户这页在旧站上
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
