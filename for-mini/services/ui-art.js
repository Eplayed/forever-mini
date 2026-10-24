const service = require('./forever-data')
const oss = require('./oss-manifest')

/* 三个 tab 页共用的那张页面底图（站主 2026-10-23 指定官方天裔那张，位置 top 居中）。
   地址走 meta.uiArt.tabBg 下发，真源在 wow-forever-web/app/data/ui-art.json——页面各自抄路径的话，
   换一张图要改三个页面，漏一个就是三页底图不一样。
   取不到批次（断网首用）时 assetUrl 返回空串，页面整个不渲染这两层，回落原来的纯色版式。 */
function tabBg() {
  return service.loadMeta().then((r) => ({
    url: oss.assetUrl(r.batch, ((r.data || {}).uiArt || {}).tabBg),
    source: r.source
  }))
}

module.exports = { tabBg }
