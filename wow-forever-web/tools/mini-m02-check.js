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
    return { counts: d.counts, cov: d.covList, wip: d.wip, fact: d.factDate, build: d.buildId,
      hasLoots: typeof p.goLoots === 'function', hasGuide: typeof p.goGuide === 'function',
      /* 2026-10-22 首页改版要读的四段：倒计时 / 职业格 / 选中职业 / 可选种族与特长 */
      cd: d.cd, nClasses: (d.classes || []).length, activeClass: d.activeClass, activeName: d.activeName,
      raceIds: (d.races || []).map((r) => r.id),
      raceNoName: (d.races || []).filter((r) => !r.nameCn).length,
      traitAll: (d.races || []).reduce((s, r) => s + (r.traits || []).length, 0),
      traitNoName: (d.races || []).reduce((s, r) => s + (r.traits || []).filter((t) => !t.name).length, 0),
      traitWithEffect: (d.races || []).reduce((s, r) => s + (r.traits || []).filter((t) => t.effect).length, 0) };
  });
  log('掉落与指南两个入口的处理器在（两页都不是 tab，必须 navigateTo）', home.hasLoots && home.hasGuide);
  /* 玩家面规矩（2026-10-22 站主定）：首页不出现计数、覆盖率、缺口、核对日期、批次号 */
  log('首页不出现计数/覆盖率/缺口/核对日期/批次号',
    home.counts === undefined && (home.cov || []).length === 0 && (home.wip || []).length === 0
      && home.fact === undefined && home.build === undefined, JSON.stringify(home));
  /* —— 首页改版（2026-10-22 站主指令）：开服倒计时 → 四卡 → 职业格 → 可选种族与种族特长。
     期望值一律从主包职业快照现算，脚本里不抄"9 格 / 7 个种族"这种会变的数字。 */
  const CLASS_SNAP = require(path.join(REPO, 'for-mini/data/forever-class-snapshot.js'));
  const META_SNAP = require(path.join(REPO, 'for-mini/data/forever-meta-snapshot.js'));
  const expectRaces = (classId) => CLASS_SNAP.races.filter((r) => (r.classes || []).indexOf(classId) >= 0).map((r) => r.id);
  log('开服倒计时这块在，日期取主包 meta 的 launch（界面不写死日期）',
    !!home.cd && home.cd.on === true && home.cd.to === META_SNAP.launch
      && /^\d{2}:\d{2}:\d{2}$/.test(String(home.cd.clock)) && home.cd.d > 0, JSON.stringify(home.cd));
  log('职业格数量与主包职业快照一致',
    home.nClasses === CLASS_SNAP.classes.length && home.nClasses > 0, home.nClasses + ' vs ' + CLASS_SNAP.classes.length);
  log('默认选中的是战士', home.activeClass === 'warrior' && home.activeName === '战士', JSON.stringify({ c: home.activeClass, n: home.activeName }));
  log('战士的可选种族＝按矩阵算出来的那几个（界面不自己凑）',
    home.raceIds.join(',') === expectRaces('warrior').join(','), home.raceIds.join(','));
  log('种族特长带文字：每条有名、至少一条有效果说明',
    home.traitAll > 0 && home.traitNoName === 0 && home.traitWithEffect > 0,
    JSON.stringify({ n: home.traitAll, noName: home.traitNoName, eff: home.traitWithEffect }));
  log('缺图标的种族仍然成格（名字在，图交给组件自绘回落，不悄悄丢掉）',
    home.raceNoName === 0 && home.raceIds.length > 0, JSON.stringify({ noName: home.raceNoName, ids: home.raceIds }));
  const homePick = await ev(() => {
    const p = getCurrentPages().pop();
    p.onPickClass({ currentTarget: { dataset: { id: 'druid' } } });
    const d = p.data;
    return { route: getCurrentPages().pop().route, activeClass: d.activeClass,
      raceIds: (d.races || []).map((r) => r.id), depth: getCurrentPages().length };
  });
  log('点别的职业只换下面那段：不跳页、可选种族跟着换',
    homePick.route === 'pages/home/index' && homePick.depth === 1 && homePick.activeClass === 'druid'
      && homePick.raceIds.join(',') === expectRaces('druid').join(','), JSON.stringify(homePick));
  await shot('c0-home-countdown-class');
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

  process.stdout.write('\nE. M03 职业 tab / 天赋树 / 指南壳 / 反查跳转（真 beta 批次）\n');
  await goto('/pages/classes/index', 9000);
  const cls = await ev(() => {
    const d = getCurrentPages().pop().data;
    return { races: (d.races || []).length, classes: (d.classes || []).length, combos: (d.combos || []).length,
      loaded: d.loaded, src: d.sourceText, err: d.errorText,
      orc: (d.races || []).filter((r) => r.id === 'orc')[0] || null };
  });
  log('职业 tab：10 种族 9 职业，无限新增组合单列', cls.loaded && cls.races === 10 && cls.classes === 9 && cls.combos > 0,
    JSON.stringify({ r: cls.races, c: cls.classes, cb: cls.combos, err: cls.err }));
  log('种族带可选职业矩阵与特长（兽人能练六个职业）',
    !!cls.orc && (cls.orc.classList || []).length === 6 && (cls.orc.traits || []).length > 0,
    JSON.stringify(cls.orc && { n: cls.orc.classList && cls.orc.classList.length, t: cls.orc.traits && cls.orc.traits.length }));
  await shot('e1-classes');
  const tree = await ev(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onPickClass({ currentTarget: { dataset: { id: 'priest' } } });
    setTimeout(() => {
      const q = getCurrentPages().pop();
      const d = q.data;
      res({ route: q.route, trees: (d.trees || []).length, rows: d.trees && d.trees[0] ? d.trees[0].rows.length : 0,
        cells: d.trees && d.trees[0] && d.trees[0].rows[0] ? d.trees[0].rows[0].cells.length : 0,
        races: (d.races || []).length, name: d.nameCn, share: typeof q.onShareAppMessage === 'function' });
    }, 9000);
  }));
  log('职业详情：天赋树三系按 tier 行摆位，可选种族反查得到', tree.route === 'pages/class/index'
    && tree.trees === 3 && tree.rows === 7 && tree.cells > 0 && tree.races > 0 && tree.share,
    JSON.stringify(tree));
  await shot('e2-class-tree');
  await goto('/pages/guide/index', 8000);
  const guide = await ev(() => {
    const p = getCurrentPages().pop();
    const d = p.data || {};
    return { route: p.route, macros: (d.macros || []).length, addons: (d.addons || []).length,
      boundaries: String(d.boundaries || '').slice(0, 20), loaded: d.loaded };
  });
  log('指南页：内容空时只说一句实话，边界文案在', guide.route === 'pages/guide/index' && guide.loaded
    && guide.macros === 0 && guide.addons === 0 && /免费/.test(guide.boundaries), JSON.stringify(guide));
  await shot('e3-guide-empty');
  /* 一条长 evaluate 里塞三次导航 + 18 秒等待，本机 automator 会丢回包（实测稳定超时）。
     拆成"导航 → 短 evaluate → Node 侧等"，每步都短。 */
  await goto('/pages/loots/index', 9000);
  const picked = await ev(() => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: '红玫瑰' } });
    const x = (p.data.list || [])[0];
    return x ? { id: x.id, dungeon: x.sources[0].dungeonId } : null;
  });
  await new Promise((r) => setTimeout(r, 900));
  const picked2 = await ev(() => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: '红玫瑰' } });
    const x = (p.data.list || [])[0];
    if (x) p.onOpenDungeon({ currentTarget: { dataset: { id: x.sources[0].dungeonId, item: x.id } } });
    return x ? { id: x.id, dungeon: x.sources[0].dungeonId } : null;
  });
  await new Promise((r) => setTimeout(r, 9000));
  const jump = await ev(() => {
    const q = getCurrentPages().pop();
    const d = q.data;
    return { route: q.route, hl: d.highlightDrop, notice: String(d.dropNotice || '').slice(0, 12),
      groups: (d.dropGroups || []).length,
      hit: (d.dropGroups || []).some((g) => g.rows.some((r) => r.itemId === d.highlightDrop)) };
  });
  log('掉落反查点一座本：跳详情并把查的那件高亮', /pages\/dungeon\/index/.test(String(jump.route))
    && !!jump.hl && jump.hit && jump.groups > 0, JSON.stringify(jump));
  await shot('e4-jump-highlight');
  const mapShot = await ev(() => { const d = getCurrentPages().pop().data; return { map: !!d.mapUrl, drawn: d.mapDrawn, entry: d.mapEntry }; });
  log('副本详情带地图（底图或入口坐标至少一样，自绘会标示意图）', mapShot.map || !!mapShot.entry, JSON.stringify(mapShot));
  await shot('e5-detail-map');

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
  const snapBytes = ['forever-glossary-snapshot.js', 'forever-meta-snapshot.js', 'forever-dungeon-snapshot.js', 'forever-class-snapshot.js']
    .reduce((s, f) => s + fs.statSync(path.join(REPO, 'for-mini/data', f)).size, 0);
  log('主包快照仍 ≤ 60 KB（技能与掉落没往主包塞，职业只塞首页要用的字段）', snapBytes <= 60 * 1024, (snapBytes / 1024).toFixed(1) + ' KB');

  /* —— 首页改版四段的静态卡口（不靠设备，纯文件与纯函数）—— */
  const cd = require(path.join(REPO, 'for-mini/services/countdown.js'));
  const LAUNCH = '2026-11-05';
  const before = cd.state(cd.launchInstant(LAUNCH) - (3 * 86400000 + 4 * 3600000 + 5 * 60000 + 6000), LAUNCH);
  const after = cd.state(cd.launchInstant(LAUNCH) + 1000, LAUNCH);
  log('倒计时：开服前给天数与秒表，过点立刻 on=false（首页那块整块移除）',
    before.on === true && before.d === 3 && before.clock === '04:05:06'
      && after.on === false && after.reason === 'launched', JSON.stringify({ before, after }));
  log('倒计时：日期没核到时不硬造一个读数',
    cd.state(Date.now(), '').on === false && cd.state(Date.now(), undefined).reason === 'no-date');
  log('倒计时：目标时刻按北京时间 0 点算，与网页端 fmt.js 的 LAUNCH_AT 同一个瞬间',
    cd.launchInstant(LAUNCH) === Date.parse('2026-11-05T00:00:00+08:00'), String(cd.launchInstant(LAUNCH)));
  const homeWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/home/index.wxml'), 'utf8');
  const homeJs = fs.readFileSync(path.join(REPO, 'for-mini/pages/home/index.js'), 'utf8');
  const cdJs = fs.readFileSync(path.join(REPO, 'for-mini/services/countdown.js'), 'utf8');
  /* 站主原话："多出来不要使用横向滚动条"——整页只许"最近看过"那一处用 scroll-x */
  log('职业格不用横向滚动（全页只有一处 scroll-x，是"最近看过"那条轨）',
    (homeWxml.match(/scroll-x/g) || []).length === 1 && /class="cls9"/.test(homeWxml) && homeWxml.indexOf('cls9') < homeWxml.indexOf('rail'),
    String((homeWxml.match(/scroll-x/g) || []).length));
  log('首页四张入口卡：有指南卡，且没有中英速查卡',
    /goGuide/.test(homeWxml) && /entry-name">指南</.test(homeWxml)
      && !/中英速查/.test(homeWxml.replace(/<!--[\s\S]*?-->/g, ' ')) && !/goGlossary/.test(homeJs),
    '注释里提到"撤出首页"不算界面文字，所以这条先把注释剥掉再比');
  /* 日期只许来自 data/meta.json → 主包快照这一条链，界面与算法里都不许抄死值 */
  log('界面与倒计时模块里没有写死的开服日期（只认 meta 的 launch）',
    !/2026-11-\d\d/.test(homeJs) && !/2026-11-\d\d/.test(homeWxml) && !/2026-\d\d-\d\d/.test(cdJs.replace(/^\/\*[\s\S]*?\*\//, '')),
    'home.js / home.wxml / countdown.js 正文');
  log('种族特长与可选种族都要图标加文字（模板里两处都渲染 icon-cell 与名字）',
    /size="cls"/.test(homeWxml) && /size="md"/.test(homeWxml) && /size="sm"/.test(homeWxml)
      && /t\.effect/.test(homeWxml) && /还没核到，不猜/.test(homeWxml));
  /* 用了自定义组件却没在页面 json 里注册＝标签整个不渲染，而且不报错。
     2026-10-22 首页改版实拍就撞上这一次：职业格与种族格的数据都对，图标一格都没出来。
     所以这条按"页面 WXML 用了 icon-cell"逐个查 json 有没有注册，全站一起扫。 */
  const unregistered = fs.readdirSync(path.join(REPO, 'for-mini/pages')).filter((d) => {
    const wxml = path.join(REPO, 'for-mini/pages', d, 'index.wxml');
    const json = path.join(REPO, 'for-mini/pages', d, 'index.json');
    if (!fs.existsSync(wxml)) return false;
    if (fs.readFileSync(wxml, 'utf8').indexOf('<icon-cell') < 0) return false;
    if (!fs.existsSync(json)) return true;
    const j = JSON.parse(fs.readFileSync(json, 'utf8'));
    return !(j.usingComponents && j.usingComponents['icon-cell']);
  });
  log('每个用 icon-cell 的页面都在自己的 json 里注册了它', unregistered.length === 0, unregistered.join(','));
  const homeWxss = fs.readFileSync(path.join(REPO, 'for-mini/pages/home/index.wxss'), 'utf8');
  log('首页样式没有裸色值（改版新增的 .cd/.cls/.race/.trait 都吃令牌）',
    !/(#[0-9a-fA-F]{3,8}\b|rgba?\()/.test(homeWxss), (homeWxss.match(/#[0-9a-fA-F]{3,8}\b|rgba?\(/g) || []).slice(0, 3).join(','));

  const ban = JSON.parse(fs.readFileSync(path.join(REPO, 'wow-forever-web/tools/copy-banned.json'), 'utf8'));
  const hits = [];
  ['pages/spells/index.wxml', 'pages/loots/index.wxml', 'pages/home/index.wxml'].forEach((f) => {
    /* 只扫玩家看得见的文字：先把标签与属性整段去掉，
       不然 class="todo" 这种样式名会被禁词表当成页面上的词命中 */
    const t = fs.readFileSync(path.join(REPO, 'for-mini', f), 'utf8').replace(/<[^>]*>/g, ' ');
    ban.patterns.forEach((p) => { if (new RegExp(p.re, 'i').test(t)) hits.push(f + ' 命中 ' + p.re) });
  });
  log('技能/掉落/首页三页的界面文字没有内部词（禁词表同一把尺子）', hits.length === 0, hits.slice(0, 3).join(','));

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
