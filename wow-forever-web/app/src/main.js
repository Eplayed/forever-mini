import { createApp } from 'vue';
import App from './App.vue';
import router from './router.js';

/* 全站样式三层，都只在这一个文件里引入：令牌 → 组件基线 → 新站视觉层。
   令牌是单一事实源（docs/UI.md 的令牌表对着它写），改色值/断点只改这里引的那几个文件。 */
import './styles/tokens.css';   // 设计令牌单一事实源（含自托管字体 @font-face）
import './styles/app.css';
/* 新站专用视觉层：只有这一站加载。 */
import './styles/board.css';

createApp(App).use(router).mount('#app');
