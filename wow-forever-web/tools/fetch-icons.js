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
/* 两个脚本写同一份清单：这个只管天赋键，fetch-icons.py 管全站引用到的键。
   谁跑都不许把对方的记录盖掉——2026-10-10 实测过一起事故：跑完天赋线，
   manifest 从「2012 张 + 每批来源」缩成「359 张」，历史整段没了。
   所以这里读回旧清单、只替换自己那一批（scope: talents），总数按目录实数算。 */
const mfPath = path.join(IMG, 'manifest.json');
const today = new Date().toISOString().slice(0, 10);
let mf = {};
if (fs.existsSync(mfPath)) { try { mf = JSON.parse(fs.readFileSync(mfPath, 'utf8')) || {}; } catch (e) { mf = {}; } }
const batches = (Array.isArray(mf.batches) ? mf.batches : []).filter((b) => b && b.scope !== 'talents');
batches.push({ scope: 'talents', at: today, needed: names.length, ok: ok, missing: miss });
const files = fs.readdirSync(IMG).filter((f) => f.endsWith('.jpg')).length;
const missing = Array.from(new Set([].concat.apply([], batches.map((b) => b.missing || b.unavailable || [])))).sort();
fs.writeFileSync(mfPath, JSON.stringify({
  source: CDN, format: '56x56 jpg', fetchedAt: today,
  total: files, ok: files, missing: missing,
  note: mf.note || '图标文件名取自上游结构化数据或第三方资料站的事实性标识符，图片一律从暴雪官方 CDN 取回本地留存，页面不热链。属游戏美术素材：如需整体下线，删除本目录即可回退到自绘占位图标。',
  batches: batches
}, null, 1));
console.log('图标：需要 ' + names.length + ' ｜ 成功 ' + ok + ' ｜ 失败 ' + miss.length +
  ' ｜ 目录共 ' + files + ' 张（清单按批次累计）');
if (miss.length) console.log('  缺：' + miss.slice(0, 15).join(', '));
