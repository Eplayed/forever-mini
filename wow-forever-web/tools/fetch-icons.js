#!/usr/bin/env node
/* 从暴雪官方图标 CDN 下载天赋图标到本地 src/img/icons/，并生成清单。
   图标文件名只是客户端资源标识符；图片由官方 CDN 提供，本地留存供站点引用。 */
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const DATA = path.join(ROOT, 'src', 'data');
const IMG = path.join(ROOT, 'src', 'img', 'icons');
const CDN = 'https://render.worldofwarcraft.com/us/icons/56/';
const CLS = ['hunter', 'druid', 'priest', 'warrior', 'paladin', 'shaman', 'mage', 'warlock', 'rogue'];

const want = {};
CLS.forEach((c) => {
  const f = path.join(DATA, 'talents', c + '.json');
  if (!fs.existsSync(f)) return;
  JSON.parse(fs.readFileSync(f, 'utf8')).trees.forEach((t) => t.nodes.forEach((n) => { if (n.iconKey) want[n.iconKey] = 1; }));
});
const names = Object.keys(want).sort();
fs.mkdirSync(IMG, { recursive: true });
let ok = 0; const miss = [];
names.forEach((k) => {
  const out = path.join(IMG, k + '.jpg');
  if (fs.existsSync(out) && fs.statSync(out).size > 500) { ok++; return; }
  let good = false;
  for (let i = 0; i < 2 && !good; i++) {
    try {
      const code = cp.execFileSync('curl', ['-s', '--max-time', '25', '-o', out, '-w', '%{http_code}', CDN + k + '.jpg'], { encoding: 'utf8' });
      good = code === '200' && fs.existsSync(out) && fs.statSync(out).size > 500;
    } catch (e) { good = false; }
  }
  if (good) ok++; else { miss.push(k); if (fs.existsSync(out)) fs.unlinkSync(out); }
});
fs.writeFileSync(path.join(IMG, 'manifest.json'), JSON.stringify({
  source: CDN, format: '56x56 jpg', fetchedAt: new Date().toISOString().slice(0, 10),
  total: names.length, ok: ok, missing: miss,
  note: '图标文件名取自上游结构化数据的资源标识符，图片来自暴雪官方 CDN。属游戏美术素材：如需整体下线，删除本目录即可回退到占位图标。'
}, null, 1));
console.log('图标：需要 ' + names.length + ' ｜ 成功 ' + ok + ' ｜ 失败 ' + miss.length);
if (miss.length) console.log('  缺：' + miss.slice(0, 15).join(', '));
