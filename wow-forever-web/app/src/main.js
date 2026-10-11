import { createApp } from 'vue';
import App from './App.vue';
import router from './router.js';

/* 迁移期共用旧站这一份样式文件：设计令牌、组件状态、断点只有一处定义，
   新旧两站的对拍才有意义。等全部页面迁完，再按组件拆成 scoped style。 */
import '../../src/css/tokens.css';   // 设计令牌单一事实源（含自托管字体 @font-face）
import '../../src/css/app.css';

createApp(App).use(router).mount('#app');
