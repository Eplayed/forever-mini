import { createApp } from 'vue';
import App from './App.vue';
import router from './router.js';

/* 全站样式三层，都只在这一个文件里引入：令牌 → 组件基线 → 新站视觉层。
   令牌是单一事实源（docs/UI.md 的令牌表对着它写），改色值/断点只改这里引的那几个文件。 */
import './styles/tokens.css';   // 设计令牌单一事实源（含自托管字体 @font-face）
import './styles/app.css';
/* 新站专用视觉层：只有这一站加载。 */
import './styles/board.css';
/* 交互动效层：只写"状态之间怎么过渡"，不写长相（路由切换、展开收起、面板切换、按压）。
   单独一层是为了"整轮要撤回就删这一个文件"，规格见 docs/PLAN-网页交互动效-2026-10-29.md。 */
import './styles/motion.css';

createApp(App).use(router).mount('#app');
