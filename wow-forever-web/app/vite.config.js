import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';

// base './' 是为了让 dist 能挂在任意子路径下与旧站并存（迁移期线上同时有两套页面）。
// 数据与素材不在这里配 publicDir：那两份是 ../src/data 与 ../src/img，
// 由 tools/app-assets.py 显式同步进 app/public/，避免把旧站的 14 个 html 一起卷进构建产物。
export default defineConfig({
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
