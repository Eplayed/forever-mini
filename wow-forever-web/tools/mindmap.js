#!/usr/bin/env node
/* 生成《无限》项目思维导图：读内嵌树 → 左右两侧 SVG 布局 → 输出 HTML + Markdown 大纲 */
const fs = require('fs');
const path = require('path');

const TREE = {
  name: '魔兽无限\n中文资料项目', note: 'WoW: Forever · 2026-11-05 上线', color: '#e0a96d', children: [
    { name: '产品定位', color: '#6fa8ff', children: [
      { name: '静态资料 + 开荒工具', children: [{ name: '副本手册 / 开荒清单' }, { name: '配装·路线·术语后补' }] },
      { name: '个人主体小程序', children: [{ name: '类目：工具-信息查询' }, { name: '零 UGC（无评论无投稿）' }] },
      { name: '明确不做', children: [{ name: '角色查询（国服无接口）' }, { name: 'DPS / 评分排行' }, { name: '付费与内购' }, { name: '读账号与战斗日志' }] }
    ] },
    { name: '合规与门槛', color: '#4caf72', children: [
      { name: '备案 1–20 工作日＝关键路径', children: [{ name: 'W1 必须提交' }, { name: '个人只需身份证件' }] },
      { name: '资讯/游戏类目不对个人开放' },
      { name: '名称避开商标词', children: [{ name: '不用 魔兽/WoW/暴雪' }, { name: '冲突后果：改名+下架' }] },
      { name: '个体工商户只解锁支付与投流', children: [{ name: '不解锁社区与名额' }, { name: '变更主体会停访问' }] },
      { name: '流量主 UV≥500，无主体门槛' }
    ] },
    { name: '时间窗', color: '#d9a13b', children: [
      { name: '国际服 Beta 2026-09-17' },
      { name: '国服 Beta 2026-10-06（388 礼包）' },
      { name: '全球上线 2026-11-05' },
      { name: '上线后 48 小时强制重核' }
    ] },
    { name: '数据源', color: '#b48ad6', children: [
      { name: '官方中文站（可自动化）', children: [{ name: '职业深度解析＝译名权威' }, { name: '在线修正＝改动报警器' }, { name: 'Beta 公告 / 座谈会' }] },
      { name: '官方英文站（可自动化）', children: [{ name: '9 新本官方名单' }, { name: 'forever 页结构化数据' }] },
      { name: '人工参照，禁止搬数据', children: [{ name: 'Wowhead /forever 专区' }, { name: 'wowclassicforever.info' }, { name: 'foreverchanges.pro' }] },
      { name: '旁证：17173 蓝贴转载' },
      { name: '开放数据 cmangos GPL', children: [{ name: '只取 1.12 中文译名' }, { name: '不取掉落与数值' }] },
      { name: '实测：B站 ASR + 关键帧 OCR' },
      { name: '第三方天赋数据挖掘（fengshen/nieyi）', children: [
        { name: '470 节点：名/系/上限/部分前置' }, { name: '89 条名与官网一致' }, { name: '行列坐标不可信，未采用' }] },
      { name: '拿不到：NGA/抖音/微博/Reddit' }
    ] },
    { name: '数据治理', color: '#7fd1c9', children: [
      { name: '完整度 L0–L3 全站可见' },
      { name: '两源一致才进正文' },
      { name: '冲突清单显式展示', children: [{ name: '领主大厅 vs 诸王大厅' }, { name: "Whelgar's vs Excavation Site" }] },
      { name: '覆盖率卡口，不达标即失败' },
      { name: '掉落不写百分比' },
      { name: '缺数据不机翻、不编造' }
    ] },
    { name: '已交付', color: '#e08a6d', children: [
      { name: '三份文档', children: [{ name: 'plan 定位与红线' }, { name: 'workflow 采编流程' }, { name: 'sources 源盘点' }] },
      { name: '数据基底工作台', children: [{ name: 'forever-seed.json' }, { name: '查询+核对+导出' }] },
      { name: '资料站项目', children: [{ name: 'PRD / UI 规范 / 参考站对照' }, { name: '七页纯静态实现' }, { name: '473 天赋节点 + 358 图标' }, { name: '每页自动列未确认项' }, { name: 'build-data 校验器' }] }
    ] },
    { name: '小程序产线', color: '#8fa8ff', children: [
      { name: '新账号，不与流放助手共用' },
      { name: 'OSS 前缀 wow/{env} 隔离' },
      { name: '独立上传脚本与 manifest' },
      { name: '图标转存自有备案域名' },
      { name: '每本一个 JSON，可整本重写' }
    ] },
    { name: '待决与缺口', color: '#c9564a', children: [
      { name: 'D1 小程序名字（卡备案起跑）' },
      { name: 'D2 是否自己打 Beta' },
      { name: '天赋层级与列位仍缺', children: [{ name: '唯一可靠来源＝客户端或实测' }, { name: '前置链仅 66/470 条' }, { name: '英文原名与描述未入库' }] },
      { name: '五职业官方中文稿尚未发布' },
      { name: '团本 3 座已入库（待官方证实）' },
      { name: 'BOSS 技能与掉落全缺' },
      { name: '新物品图标 CDN 未验证' },
      { name: '关键帧 OCR 能力未验证' },
      { name: '中文竞品未摸底（pigtogo 等）' }
    ] }
  ]
};

const ROW = 26, PAD_X = 10, GAP_Y = 8, GAP_X = 30, FONT = [15, 13, 12, 11.5];
function w(n, d) {
  const lines = n.name.split('\n');
  const max = Math.max.apply(null, lines.map(function (l) {
    let c = 0; for (const ch of l) c += ch.charCodeAt(0) > 255 ? 1 : 0.55; return c;
  }));
  return Math.ceil(max * FONT[Math.min(d, 3)] * 1.02) + PAD_X * 2;
}
function hgt(n) {
  if (!n.children || !n.children.length) return ROW;
  return n.children.reduce(function (a, c) { return a + hgt(c); }, 0) + (n.children.length - 1) * GAP_Y;
}
function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }

/* 1) 分侧与纵向：前 4 支向右，其余向左 */
const kids = TREE.children;
const right = kids.slice(0, 4), left = kids.slice(4);
function layoutY(n, side, depth, y) {
  const self = hgt(n);
  n.y = y + self / 2; n.d = depth; n.side = side;
  if (n.children) {
    let cy = y;
    n.children.forEach(function (c) { layoutY(c, side, depth + 1, cy); cy += hgt(c) + GAP_Y; });
  }
}
let yr = 0, yl = 0;
right.forEach(function (k) { yr += hgt(k) + GAP_Y; });
left.forEach(function (k) { yl += hgt(k) + GAP_Y; });
const totalH = Math.max(yr, yl);
let cy = (totalH - yr) / 2;
right.forEach(function (k) { layoutY(k, 1, 1, cy); cy += hgt(k) + GAP_Y; });
cy = (totalH - yl) / 2;
left.forEach(function (k) { layoutY(k, -1, 1, cy); cy += hgt(k) + GAP_Y; });
TREE.d = 0; TREE.y = totalH / 2; TREE.side = 0;

/* 2) 横向：按「每侧每层的最宽节点」分列，避免深层压到父节点 */
const colW = { 1: {}, '-1': {} };
function collect(n) {
  colW[n.side][n.d] = Math.max(colW[n.side][n.d] || 0, w(n, n.d));
  (n.children || []).forEach(collect);
}
right.forEach(collect); left.forEach(collect);
function prefix(side) {
  const m = colW[side], ds = Object.keys(m).map(Number).sort(function (a, b) { return a - b; });
  const acc = {}; let s = 0;
  ds.forEach(function (d) { acc[d] = s; s += m[d] + GAP_X; });
  return acc;
}
const preR = prefix(1), preL = prefix('-1');
const rootW = w(TREE, 0), rootH = 54;
const rightSpan = Object.keys(preR).reduce(function (a, d) { return Math.max(a, preR[d] + colW[1][d]); }, 0) + GAP_X;
const leftSpan = Object.keys(preL).reduce(function (a, d) { return Math.max(a, preL[d] + colW[-1][d]); }, 0) + GAP_X;
const rootX = leftSpan + GAP_X + rootW / 2;
function place(n) {
  if (n.d === 0) n.x = rootX - rootW / 2;
  else if (n.side > 0) n.x = rootX + rootW / 2 + preR[n.d];
  else n.x = rootX - rootW / 2 - preL[n.d] - w(n, n.d);
  (n.children || []).forEach(place);
}
place(TREE);
const total = totalH;

function walk(n, f) { f(n); (n.children || []).forEach(function (c) { walk(c, f); }); }
const boxes = [], links = [];
walk(TREE, function (n) {
  const col = n.color || (n.parentColor || '#8b95a5');
  boxes.push(n);
  (n.children || []).forEach(function (c) {
    const pw = w(n, n.d), cw = w(c, c.d);
    const sx = c.side > 0 ? n.x + pw : n.x, ex = c.side > 0 ? c.x : c.x + cw;
    links.push('<path d="M' + sx + ',' + n.y + ' C' + (sx + (ex - sx) / 2) + ',' + n.y + ' ' +
      (ex - (ex - sx) / 2) + ',' + c.y + ' ' + ex + ',' + c.y + '" fill="none" stroke="' +
      (c.color || n.color || '#4a5260') + '" stroke-width="' + (c.d <= 1 ? 1.8 : 1) +
      '" opacity="' + (c.d >= 3 ? .38 : .62) + '"/>');
  });
});
let minX = Infinity, maxX = -Infinity;
boxes.forEach(function (n) {
  const bw = w(n, n.d);
  if (n.x < minX) minX = n.x;
  if (n.x + bw > maxX) maxX = n.x + bw;
});
const W = Math.ceil(maxX - minX) + 80, H = Math.ceil(total) + 100;
const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H +
  '" font-family="-apple-system,PingFang SC,Microsoft YaHei,sans-serif">' +
  '<rect width="' + W + '" height="' + H + '" fill="#0e1013"/>' +
  '<g transform="translate(' + (40 - minX) + ',40)">' + links.join('') +
  boxes.map(function (n) {
    const bw = w(n, n.d), bh = n.d === 0 ? rootH : 23;
    const col = n.color || '#8b95a5';
    return '<g><rect x="' + n.x + '" y="' + (n.y - bh / 2) + '" width="' + bw + '" height="' + bh +
      '" rx="' + (n.d === 0 ? 10 : 5) + '" fill="' + (n.d === 0 ? col : '#171a1f') +
      '" stroke="' + col + '" stroke-width="' + (n.d === 0 ? 2 : 1) + '"/>' +
      n.name.split('\n').map(function (ln, i, a) {
        return '<text x="' + (n.x + bw / 2) + '" y="' + (n.y + (i - (a.length - 1) / 2) * 16 + 4) +
          '" text-anchor="middle" font-size="' + (n.d === 0 ? 15 : FONT[Math.min(n.d, 3)]) +
          '" font-weight="' + (n.d <= 1 ? 600 : 400) + '" fill="' + (n.d === 0 ? '#1a1408' : '#e7e9ee') + '">' + esc(ln) + '</text>';
      }).join('') + '</g>';
  }).join('') + '</g></svg>';

const legend = TREE.children.map(function (c) {
  return '<i style="background:' + c.color + '"></i><span>' + esc(c.name) + '</span>';
}).join('');
const html = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width,initial-scale=1"><title>魔兽无限项目思维导图</title>' +
  '<style>body{margin:0;background:#0e1013;color:#e7e9ee;font:14px/1.6 -apple-system,PingFang SC,sans-serif}' +
  'h1{font-size:16px;margin:18px 24px 6px}p{margin:0 24px 10px;color:#98a1af;font-size:12.5px}' +
  '.lg{margin:0 24px 14px;font-size:12px;color:#98a1af}.lg i{display:inline-block;width:9px;height:9px;border-radius:2px;margin:0 4px 0 12px}' +
  '.box{overflow:auto;padding:0 24px 28px}svg{max-width:100%;height:auto}</style></head><body>' +
  '<h1>《魔兽无限》中文资料项目 · 思维导图</h1><p>生成于 2026-10-07 · 更新请改 tools/mindmap.js 里的 TREE 后重跑 node tools/mindmap.js</p>' +
  '<div class="lg">' + legend + '</div><div class="box">' + svg + '</div></body></html>';

const out1 = path.resolve(__dirname, '..', 'docs', 'mindmap.html');
fs.writeFileSync(out1, html);
let md = '# 魔兽无限项目思维导图（大纲）\n\n';
(function emit(n, d) {
  if (n.d === undefined && n !== TREE) return;
  md += '  '.repeat(n.d) + (n.d ? '- ' : '## ') + n.name.replace('\n', ' ') + (n.note ? '（' + n.note + '）' : '') + '\n';
  (n.children || []).forEach(function (c) { emit(c, n.d + 1); });
})(TREE, 0);
const out2 = path.resolve(__dirname, '..', 'docs', 'mindmap.md');
fs.writeFileSync(out2, md);
console.log('输出', out1, '|', out2, '| 画布', W + '×' + H, '| 节点数', (html.match(/<rect/g) || []).length - 1);
