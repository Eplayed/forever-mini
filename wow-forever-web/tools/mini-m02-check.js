#!/usr/bin/env node
/* M02（素材上线 + 职业技能速查 + 掉落反查）· 微信开发者工具端的回归脚本
   跑法（与 mini-m01-check.js 同一套工具链）：
     1) "/Applications/wechatwebdevtools.app/Contents/MacOS/cli" auto --project <仓库绝对路径>/for-mini --auto-port 9421
     2) NODE_PATH=<miniprogram-automator 的 node_modules> node wow-forever-web/tools/mini-m02-check.js
   与 M01 那条的区别：这一条**直连真 bucket 的 beta**，因为 M02 要验的就是
   "素材层与两个新分片在真环境里能不能被界面用上"，用本地假 OSS 测等于没测。
   截图一律先落到 /tmp 再拷进 for-mini/docs/screenshots/——开发者工具开着 compileHotReLoad，
   往 for-mini/ 里写文件会热重载把小程序打回首页，制造一片假红。
   退出码 0 = 全绿。 */
const fs = require('fs');
const path = require('path');
const https = require('https');
const MPmod = require('miniprogram-automator/out/MiniProgram');
const MiniProgram = MPmod.default || MPmod;
MiniProgram.prototype.checkVersion = async () => true;
const automator = require('miniprogram-automator');

const REPO = '/Users/zhangyajun/Documents/project/wow-forever';
const SHOT = '/tmp/m02-shots';
const results = [];
const log = (name, pass, info) => {
  results.push({ name, pass: !!pass, info: info === undefined ? '' : String(info) });
  process.stdout.write((pass ? '  ✓ ' : '  ✗ ') + name + (info ? '  → ' + String(info).slice(0, 220) : '') + '\n');
};
const T = (p, ms, l) => Promise.race([p, new Promise((_, r) => setTimeout(() => r(new Error('TMO ' + l)), ms))]);
let mp;
async function call(label, fn, tries) {
  let last;
  for (let i = 0; i < (tries || 3); i += 1) {
    try { return await T(Promise.resolve().then(fn), 30000, label); } catch (e) { last = e; await new Promise((r) => setTimeout(r, 700)); }
  }
  log('链路抖动：' + label, false, last && last.message);
  return null;
}
/* 本机 automator 偶发丢回包（同一命令重发就好），所以默认重试 4 次 */
const ev = (fn, ...a) => call('evaluate', () => mp.evaluate(fn, ...a), 4);
const shot = (name) => call('shot', async () => {
  if (!fs.existsSync(SHOT)) fs.mkdirSync(SHOT, { recursive: true });
  await mp.screenshot({ path: path.join(SHOT, name + '.png') });
  return fs.statSync(path.join(SHOT, name + '.png')).size;
});
/* 素材是不是真的在 bucket 上：只看状态码与 Content-Type，不看界面猜 */
function head(url) {
  return new Promise((resolve) => {
    const req = https.get(url, (res) => {
      res.resume();
      resolve({ code: res.statusCode, type: res.headers['content-type'] || '' });
    });
    req.on('error', (e) => resolve({ code: 0, err: e.message }));
    req.setTimeout(15000, () => { req.destroy(); resolve({ code: 0, err: 'TMO' }); });
  });
}
/* 导航的"等"放在 Node 侧，不放在小程序侧：掉落反查那一页 onLoad 要同步拼 1018 件物品，
   主线程忙的时候在页面里 setTimeout 再回话的 evaluate 会超时（实测稳定卡在这一步），
   于是断言读到的是上一秒的状态。发完导航 → Node 睡一会儿 → 再单独查当前路由。 */
async function goto(url, ms) {
  await ev((u) => { wx.reLaunch({ url: u, fail: () => {} }); return 1 }, url);
  await new Promise((r) => setTimeout(r, ms || 6000));
  return ev((u) => {
    const c = getCurrentPages().pop();
    return c ? c.route + '|' + JSON.stringify(c.data.loaded === undefined ? '' : c.data.loaded) : 'none';
  }, url);
}

async function main() {
  mp = await T(automator.connect({ wsEndpoint: 'ws://127.0.0.1:9421' }), 30000, 'connect');
  await ev(() => { try { wx.clearStorageSync() } catch (e) {} return 1 });

  process.stdout.write('\nA. 职业技能速查（真 beta 批次）\n');
  await goto('/pages/spells/index', 8000);
  const grid = await ev(() => {
    const d = getCurrentPages().pop().data;
    return { loaded: d.loaded, n: (d.classes || []).length, src: d.sourceText, build: d.buildId, err: d.errorText,
      icons: (d.classes || []).map((c) => c.iconUrl), counts: (d.classes || []).map((c) => c.count) };
  });
  /* "实时数据（本机缓存，没重新下载）"也是 live：批次是当前批，只是字节没重下 */
  log('职业名单 9 条且来自实时数据', grid.loaded && grid.n === 9 && String(grid.src).indexOf('实时数据') === 0, JSON.stringify({ n: grid.n, src: grid.src, err: grid.err }));
  log('九个职业图标地址都落在 assets/icons/ 下（不是站内 img/）',
    grid.icons.every((u) => /^https?:\/\/.+\/assets\/icons\/class_[a-z]+\.jpg$/.test(String(u))), String(grid.icons[0]));
  const badIcon = [];
  for (const u of grid.icons) {
    const r = await head(u);
    if (r.code !== 200 || r.type.indexOf('image/') !== 0) badIcon.push(u.split('/').pop() + '→' + r.code + '/' + r.type);
  }
  log('职业图标在 bucket 上真取得到（200 + image/*）', badIcon.length === 0, badIcon.slice(0, 3).join(','));
  const sum = grid.counts.reduce((a, b) => a + b, 0);
  log('职业条数加起来是 498（名单与分片同源）', sum === 498, String(sum));
  await shot('a1-spells-grid');

  const one = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.selectClass('priest').then(() => {
      const d = p.data;
      res({ cls: d.classId, total: d.total, groups: (d.groups || []).map((g) => g.tab + ':' + g.rows.length),
        need: d.needOnline, err: d.errorText, icon: (d.list || [])[0] ? (d.list || [])[0].iconUrl : '' });
    });
  }));
  log('点开牧师只取这一片，56 条按三个系分组', one.cls === 'priest' && one.total === 56 && one.groups.length === 3 && !one.err, JSON.stringify(one));
  const rIcon = await head(one.icon);
  log('技能图标在 bucket 上真取得到', rIcon.code === 200 && rIcon.type.indexOf('image/') === 0, one.icon.split('/').pop() + '→' + rIcon.code);
  await shot('a2-spells-priest');
  const filtered = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: '治疗' } });
    setTimeout(() => res({ shown: (p.data.list || []).length, total: p.data.total,
      all: (p.data.list || []).every((x) => String(x.name).indexOf('治疗') >= 0), kw: p.data.kw }), 700);
  }));
  log('在职业内搜索只留命中的行', filtered.shown > 0 && filtered.shown < filtered.total && filtered.all, JSON.stringify(filtered));
  const nomatch = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: 'zzz不存在' } });
    setTimeout(() => res((p.data.list || []).length), 600);
  }));
  log('搜不到时列表为空（界面走"没有匹配"卡，不拿全量充数）', nomatch === 0, String(nomatch));
  await ev(() => { getCurrentPages().pop().onKw({ detail: { value: '' } }); return 1 });
  const opened = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    const x = (p.data.list || [])[0];
    p.setData({ expandedId: x.id });
    setTimeout(() => {
      const y = (p.data.groups || []).reduce((a, g) => a.concat(g.rows), []).filter((s) => s.id === p.data.expandedId)[0];
      res({ id: y.id, ranks: y.ranks.length, prov: y.prov.length, lvl: y.level });
    }, 700);
  }));
  log('展开一条能看到逐级学习等级与来源记录', opened.ranks > 0 && opened.prov > 0, JSON.stringify(opened));
  await shot('a3-spells-open');

  process.stdout.write('\nB. 掉落反查（真 beta 批次）\n');
  await goto('/pages/loots/index', 10000);
  const lb = await ev(() => {
    const d = getCurrentPages().pop().data;
    return { loaded: d.loaded, total: d.total, itemCount: d.itemCount, src: d.sourceText, err: d.errorText, build: d.buildId };
  });
  log('掉落表取回且行数/物品数与首页同源（1050 / 1018）',
    lb.loaded && lb.total === 1050 && lb.itemCount === 1018 && !lb.err, JSON.stringify(lb));
  const rose = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: '红玫瑰' } });
    setTimeout(() => {
      const x = (p.data.list || [])[0];
      p.setData({ expandedId: x ? x.id : '' });
      setTimeout(() => res(x ? { name: x.name, q: x.qualityText, srcs: x.sources.map((s) => s.dungeon + '/' + s.boss), icon: x.iconUrl } : null), 500);
    }, 900);
  }));
  log('按名字反查：一束红玫瑰归并出四座本与各自首领',
    !!rose && rose.srcs.length === 4 && rose.q === '良好', JSON.stringify(rose && rose.srcs));
  if (rose) {
    const rr = await head(rose.icon);
    log('掉落物品图标在 bucket 上真取得到', rr.code === 200 && rr.type.indexOf('image/') === 0, String(rr.code));
  }
  await shot('b1-loots-rose');
  const byId = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: '274286' } });
    setTimeout(() => res((p.data.list || []).map((x) => x.name)), 800);
  }));
  log('按物品编号也能查到', byId.length === 1 && byId[0] === '杜根·挽锤的头颅', JSON.stringify(byId));
  const none = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: 'zzz不存在' } });
    setTimeout(() => res((p.data.list || []).length), 700);
  }));
  log('查不到就是查不到（空态卡，不编一个相近的）', none === 0, String(none));
  const disc = await ev(() => { const d = getCurrentPages().pop().data; return { disc: d.disclaimer, note: d.qualityNote } });
  log('页面带着"本站不写掉落几率"与品质四档说明', /不写|几率/.test(disc.disc) && /史诗/.test(disc.note), disc.disc.slice(0, 60));

  process.stdout.write('\nC. 入口与结构\n');
  await goto('/pages/home/index', 7000);
  const home = await ev(() => {
    const p = getCurrentPages().pop();
    const d = p.data;
    return { counts: d.counts, hasSpells: typeof p.goSpells === 'function', hasLoots: typeof p.goLoots === 'function',
      tab: (wx.getStorageSync('__noop') || '') };
  });
  log('首页四个入口的数字都来自 meta.counts（不是写死）',
    home.counts.dungeons === 38 && home.counts.spells === 498 && home.counts.lootRows === 1050 && home.counts.terms > 0, JSON.stringify(home.counts));
  log('技能与掉落两个入口的处理器在（页面不是 tab 页，必须 navigateTo）', home.hasSpells && home.hasLoots);
  const navOk = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.goLoots();
    setTimeout(() => { const cur = getCurrentPages().pop(); res({ route: cur.route, n: getCurrentPages().length }) }, 3500);
  }));
  log('从首页点"掉落反查"真的进得去（不是点了没反应）', navOk.route === 'pages/loots/index' && navOk.n === 2, JSON.stringify(navOk));
  const back = await ev(() => new Promise((res) => {
    wx.navigateBack({ success: () => setTimeout(() => res(getCurrentPages().pop().route), 2500) });
  }));
  log('返回回到首页（返回栈没被 switchTab 打散）', back === 'pages/home/index', String(back));
  await shot('c1-home');

  process.stdout.write('\nD. 规范与包体\n');
  const files = ['pages/spells/index.wxss', 'pages/loots/index.wxss'];
  const raw = [];
  files.forEach((f) => {
    const t = fs.readFileSync(path.join(REPO, 'for-mini', f), 'utf8');
    (t.match(/#[0-9a-fA-F]{3,8}\b/g) || []).forEach((c) => raw.push(f + ' ' + c));
    (t.match(/rgba?\(/g) || []).forEach(() => raw.push(f + ' rgba()'));
  });
  log('两个新页的样式里没有裸色值（颜色一律走 app.wxss 令牌）', raw.length === 0, raw.slice(0, 4).join(','));
  const appJson = JSON.parse(fs.readFileSync(path.join(REPO, 'for-mini/app.json'), 'utf8'));
  log('tabBar 仍是三项，新页走二级页面不挤占 tab', appJson.tabBar.list.length === 3
    && appJson.pages.indexOf('pages/spells/index') >= 0 && appJson.pages.indexOf('pages/loots/index') >= 0,
    JSON.stringify(appJson.pages));
  const snapBytes = ['forever-glossary-snapshot.js', 'forever-meta-snapshot.js', 'forever-dungeon-snapshot.js']
    .reduce((s, f) => s + fs.statSync(path.join(REPO, 'for-mini/data', f)).size, 0);
  log('主包快照仍 ≤ 60 KB（技能与掉落没往主包塞）', snapBytes <= 60 * 1024, (snapBytes / 1024).toFixed(1) + ' KB');
  const ban = JSON.parse(fs.readFileSync(path.join(REPO, 'wow-forever-web/tools/copy-banned.json'), 'utf8'));
  const hits = [];
  ['pages/spells/index.wxml', 'pages/loots/index.wxml'].forEach((f) => {
    /* 只扫玩家看得见的文字：先把标签与属性整段去掉，
       不然 class="todo" 这种样式名会被禁词表当成页面上的词命中 */
    const t = fs.readFileSync(path.join(REPO, 'for-mini', f), 'utf8').replace(/<[^>]*>/g, ' ');
    ban.patterns.forEach((p) => { if (new RegExp(p.re, 'i').test(t)) hits.push(f + ' 命中 ' + p.re) });
  });
  log('两个新页的界面文字没有内部词（禁词表同一把尺子）', hits.length === 0, hits.slice(0, 3).join(','));

  const bad = results.filter((r) => !r.pass);
  process.stdout.write('\n通过 ' + (results.length - bad.length) + ' / ' + results.length
    + (bad.length ? ' · 未过：' + bad.map((b) => b.name).join('、') : '') + '\n');
  fs.writeFileSync('/tmp/mp-m02-results.json', JSON.stringify({ results }, null, 1));
  await mp.disconnect();
  process.exit(bad.length ? 1 : 0);
}

main().catch((e) => {
  process.stdout.write('\n脚本异常：' + (e && e.stack ? e.stack : e) + '\n');
  fs.writeFileSync('/tmp/mp-m02-results.json', JSON.stringify({ results }, null, 1));
  if (mp) mp.disconnect();
  process.exit(2);
});
