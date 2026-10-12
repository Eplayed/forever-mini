/* 出处与分级的显示开关（新站侧），与旧站 src/js/data.js 里的 SHOW_PROV 同一件事。
   2026-10-12 用户决定：内容页只留标题和数据，分级徽标 / 逐条来源 / 覆盖率条不上页面，
   全部集中在溯源页（provenance.html）说。
   溯源页目前还在旧站没迁过来，所以新站这边一律不渲染；迁过来那天把 SHOW_PROV 换成
   按路由判断（route.path === '/provenance'），两栈口径就重新对齐。
   别在内容页里手写 <span class="pill"> 或「来源」按钮——site-check 有反向断言会红。 */
export const SHOW_PROV = false;
