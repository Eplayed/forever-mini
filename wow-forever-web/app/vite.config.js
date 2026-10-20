import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

/* base 定成 './'（相对当前文档），不是 '/'。
   为什么：托管目标还没定（docs/OPS-deploy-domain-2026-10-19.md 是调研，不是已配置证据），
   而迁移期线上可能把新站挂在子路径下与旧站并存。写 '/' 时产物只能挂根目录——
   lib/data.js 的 assetUrl() 读的就是 import.meta.env.BASE_URL，base 不给 './' 的话
   数据与图标全部去根目录取，挂到 /wow/ 下就是"页面壳子开得到、里面全是空"。
   本站只有 hash 路由（文档路径永远是那个目录），所以相对路径不会像 history 路由那样
   在直达子页时算错父级；两种挂法都实测过，见 tools/pkg-verify.py。
   数据与素材不在这里配 publicDir：那两份是 ../src/data 与 ../src/img，
   由 tools/app-assets.py 显式同步进 app/public/，避免把旧站的 19 个 html 一起卷进构建产物。 */
export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') }
  },
  server: { port: 8820, host: '127.0.0.1' },
  preview: { port: 8821, host: '127.0.0.1' },
  build: { outDir: 'dist', emptyOutDir: true },
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.spec.js'],
    globals: false
  }
});
