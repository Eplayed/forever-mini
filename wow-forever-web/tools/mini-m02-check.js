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
    !!home.cd && home.cd.on === true && home.cd.to === META_SNAP.launch && home.cd.d > 0,
    JSON.stringify(home.cd));
  /* 站主二次指令："只到天，不再做具体的秒表逻辑" → 读数里不许再出现时:分:秒 */
  log('倒计时只到天：读数里没有秒表字段，界面也没有',
    home.cd && home.cd.clock === undefined && !/clock/.test(JSON.stringify(home.cd)),
    JSON.stringify(home.cd));
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

  process.stdout.write('\nF. 首页配图与天赋模拟器（2026-10-22 站主指令）\n');
  await goto('/pages/home/index', 7000);
  const art = await ev(() => { const d = getCurrentPages().pop().data; return { bg: d.bgUrl, cards: d.cardBg }; });
  const CARD_KEYS = ['dungeons', 'classes', 'loots', 'guide'];
  log('首页背景与四张卡都拼出了 assets 地址（路径由 meta.uiArt 下发，页面不各自抄）',
    /^https?:\/\//.test(String(art.bg)) && CARD_KEYS.every((k) => /^https?:\/\//.test(String(art.cards[k] || ''))),
    JSON.stringify(art.cards));
  const artUrls = [art.bg].concat(CARD_KEYS.map((k) => art.cards[k]));
  const artGot = [];
  for (let i = 0; i < artUrls.length; i += 1) {
    const u = String(artUrls[i] || '');
    /* 地址为空＝线上那批 meta 里还没有 uiArt（新批次没发），这要报红而不是把空串塞给 https.get */
    if (!/^https?:\/\//.test(u)) { artGot.push('空地址（线上批次没有 uiArt）'); continue; }
    const r = await head(u);
    artGot.push(r.code + ' ' + (r.type || r.err || ''));
  }
  /* 这条在发素材之前就该红：底图不在 bucket 上，玩家看到的是一片纯色而不是报错，
     而"数据拼得出地址"骗不过眼睛——所以查真地址，不查界面猜。 */
  log('五张底图在 bucket 上真取得到（200 + image/*）',
    artGot.every((g) => /^200 image\//.test(g)),
    artUrls.map((u, i) => (String(u).split('/v1/')[1] || '（空）') + '→' + artGot[i]).join(' | '));
  await shot('f1-home-art');
  /* 天裔（2026-10-22 站主报"小程序缺天裔的数据和图标"）：选德鲁伊，下面那一段里两条天裔
     必须各带 4 条特长、带子族名、图标走素材层那张插件图。这条查的是"界面真读到了"，
     不是库里有没有——数一直在，只是过去挂在 subgroup 那层没被读。 */
  const sky = await ev(() => {
    const p = getCurrentPages().pop();
    p.onPickClass({ currentTarget: { dataset: { id: 'druid' } } });
    return (p.data.races || []).filter((r) => String(r.id).indexOf('skyborne') === 0)
      .map((r) => ({ id: r.id, name: r.nameCn, sub: r.subCn, n: (r.traits || []).length,
        first: ((r.traits || [])[0] || {}).name, eff: ((r.traits || [])[0] || {}).effect, icon: r.iconUrl }));
  });
  log('首页选德鲁伊：两条天裔各有 4 条特长、带子族名与效果文字',
    sky.length === 2 && sky.every((r) => r.n === 4 && r.sub && r.first && r.eff), JSON.stringify(sky));
  const skyIconUrl = String((sky[0] || {}).icon || '');
  const skyIcon = /^https?:\/\//.test(skyIconUrl) ? await head(skyIconUrl) : { code: 0, type: '空地址' };
  log('天裔种族图标在 bucket 上真取得到（官方 CDN 没这张，用的是授权转存的那张小的）',
    /raceicons\/skyborne\.webp$/.test(skyIconUrl) && skyIcon.code === 200
      && String(skyIcon.type).indexOf('image/') === 0, 'HTTP ' + skyIcon.code + ' ' + (skyIcon.type || skyIcon.err || ''));
  await ev(() => { const p = getCurrentPages().pop(); p.onPickClass({ currentTarget: { dataset: { id: 'warrior' } } }); return 1 });


  await ev(() => { try { wx.removeStorageSync('wow_forever_v1_tbuild@warrior'); } catch (e) {} return 1 });
  await goto('/pages/class/index?classId=warrior', 9000);
  const sim0 = await ev(() => {
    const d = getCurrentPages().pop().data;
    const c = d.trees[0].rows[0].cells[0];
    const late = d.trees[0].rows[d.trees[0].rows.length - 1].cells[0];
    return { total: d.totalPoints, left: d.remaining, gate: d.gateNote, rows: d.trees[0].rows.length,
      treeName: d.trees[0].name,
      first: { id: c.id, name: c.name, ranks: c.ranks, max: c.max, can: c.can },
      late: { tier: late.tier, can: late.can, why: late.why } };
  });
  log('天赋页带 rules：总点数从分片读、门槛那句话写在屏幕上、开局 0 点',
    sim0.total > 0 && sim0.left === sim0.total && sim0.rows > 0 && sim0.first.ranks === 0
      && /门槛|未实测|未核实/.test(sim0.gate), JSON.stringify(sim0));
  log('深层格子开局点不动，且说得出为什么（层级门槛判定真的在跑）',
    sim0.late.can === false && /投满|要先点/.test(sim0.late.why), JSON.stringify(sim0.late));
  const add1 = await ev(() => {
    const p = getCurrentPages().pop();
    const c = p.data.trees[0].rows[0].cells[0];
    p.onTapNode({ currentTarget: { dataset: { id: c.id } } });
    const d = p.data;
    const n = d.trees[0].rows[0].cells[0];
    return { left: d.remaining, ranks: n.ranks, spent: d.spentText, code: d.buildCode };
  });
  log('点一下加一点：剩余点数减一、格上读数变 1/上限、那系计数跟着走',
    add1.left === sim0.total - 1 && add1.ranks === 1
      && add1.spent.indexOf(sim0.treeName + ' 1') === 0, JSON.stringify(add1));
  const pop = await ev(() => {
    const p = getCurrentPages().pop();
    const c = p.data.trees[0].rows[0].cells[0];
    p.onLongNode({ currentTarget: { dataset: { id: c.id } } });
    const q = p.data.pop;
    return q ? { name: q.name, ranks: q.ranks, max: q.max, tier: q.tier } : null;
  });
  log('长按开详情：名字、已点/上限、第几层都在', !!pop && pop.name === sim0.first.name
    && pop.ranks === 1 && String(pop.max) === String(sim0.first.max) && pop.tier === 0, JSON.stringify(pop));
  const back1 = await ev(() => {
    const p = getCurrentPages().pop();
    p.popRemove();
    const d = p.data;
    return { left: d.remaining, ranks: d.trees[0].rows[0].cells[0].ranks, pop: d.pop && d.pop.ranks };
  });
  log('详情里减一点：树上那一格与弹窗读数一起回到 0',
    back1.left === sim0.total && back1.ranks === 0 && back1.pop === 0, JSON.stringify(back1));
  const shared = await ev(() => {
    const p = getCurrentPages().pop();
    const c = p.data.trees[0].rows[0].cells[0];
    p.onTapNode({ currentTarget: { dataset: { id: c.id } } });
    p.onTapNode({ currentTarget: { dataset: { id: c.id } } });
    const s = p.onShareAppMessage();
    return { path: s.path, title: s.title, code: p.data.buildCode };
  });
  log('分享带这套配置的短码（与网页 encode 同格式：三系、每节点一位）',
    /classId=warrior&b=/.test(shared.path) && /^[0-9a-z]+-[0-9a-z]+-[0-9a-z]+$/.test(shared.code)
      && shared.code.charAt(0) === '2' && /2/.test(shared.title), JSON.stringify(shared));
  await shot('f2-talent-sim');

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
  const before = cd.state(cd.launchInstant(LAUNCH) - (3 * 86400000 + 4 * 3600000), LAUNCH);
  const today = cd.state(cd.launchInstant(LAUNCH) - 3600000, LAUNCH);
  const after = cd.state(cd.launchInstant(LAUNCH) + 1000, LAUNCH);
  log('倒计时：只给整天数（3 天 4 小时算 3 天），过点立刻 on=false（首页那块整块移除）',
    before.on === true && before.d === 3 && before.today === false && before.clock === undefined
      && after.on === false && after.reason === 'launched', JSON.stringify({ before, after }));
  log('倒计时：剩不到一个整天写"就在今天"，不写 0 天',
    today.on === true && today.d === 0 && today.today === true, JSON.stringify(today));
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
  const clsWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/classes/index.wxml'), 'utf8');
  /* —— 天赋引擎单测（纯函数，不连设备）：与网页端 TalentPage 同一套判定的回归面。
        用例是照网页那份引擎的行为写死的，任何一条变了就是两端会给不同的"能不能点"。 —— */
  const TE = require(path.join(REPO, 'for-mini/services/talent-engine.js'));
  const TT = [{ id: 'w0', nameCn: '武器', nodes: [
    { id: 'a', tier: 0, column: 0, maxRanks: 3, nameCn: '甲' },
    { id: 'b', tier: 1, column: 0, maxRanks: 1, nameCn: '乙', requires: ['a'] },
    { id: 'c', tier: 2, column: 0, maxRanks: 2, nameCn: '丙', requires: ['b'] },
    { id: 'd', tier: 0, column: 1, maxRanks: null, nameCn: '丁' }] }];
  const TR = TE.normalizeRules({ totalPoints: 4, tierUnlockCost: [0, 2, 5] });
  const nmOf = (id) => ({ a: '甲', b: '乙', c: '丙', d: '丁' }[id] || '');
  const t1 = TE.canAdd(TT[0], {}, TT[0].nodes[1], TR, TT, nmOf);
  const t2 = TE.canAdd(TT[0], { a: 2 }, TT[0].nodes[1], TR, TT, nmOf);
  const t3 = TE.canAdd(TT[0], { a: 1 }, TT[0].nodes[3], TR, TT, nmOf);
  const t4 = TE.canAdd(TT[0], { a: 1, b: 1, c: 2 }, TT[0].nodes[0], TR, TT, nmOf);
  const t5 = TE.remove(TT, { a: 1, b: 1 }, TT[0].nodes[0]);
  const code5 = TE.encode(TT, { a: 3, b: 1 });
  const dec5 = TE.decode(code5, TT);
  const over = TE.decode('9999', TT);
  log('引擎：层级门槛（第 2 层要本系 2 点）与总点数用尽都按网页同一套判',
    t1.ok === false && /投满 2 点/.test(t1.why) && t2.ok === true
      && t4.ok === false && /用完（共 4 点）/.test(t4.why), JSON.stringify([t1.why, t2.ok, t4.why]));
  log('引擎：maxRanks 没核实的节点不猜上限，直接说"还没核实"',
    t3.ok === false && /上限还没核实/.test(t3.why), String(t3.why));
  log('引擎：前置那句给天赋中文名，不把 warrior-0-重伤 这种编号印给玩家',
    /要先点：甲/.test(TE.canAdd(TT[0], {}, TT[0].nodes[1], TE.normalizeRules({ totalPoints: 4 }), TT, nmOf).why));
  log('引擎：减一点会级联清空靠它活着的天赋', /跟着清空：乙/.test(String(t5.msg)), String(t5.msg));
  log('引擎：编码↔解码回同一套，超上限的码被夹住并计数',
    code5 === '3100' && JSON.stringify(dec5.state) === JSON.stringify({ a: 3, b: 1 }) && dec5.bad === 0
      && over.state.a === 3 && over.state.d === undefined && over.bad > 0,
    JSON.stringify({ code5, dec: dec5.state, over: over.state, bad: over.bad }));

  /* —— tabBar 图标：微信要本地文件，缺一张就是 tab 上少个图标且不报错 —— */
  const tabErr = [];
  (appJson.tabBar.list || []).forEach((it) => {
    ['iconPath', 'selectedIconPath'].forEach((k) => {
      const rel = it[k];
      if (!rel) { tabErr.push(it.text + ' 缺 ' + k); return; }
      const abs = path.join(REPO, 'for-mini', rel);
      if (!fs.existsSync(abs)) { tabErr.push(it.text + ' 的 ' + rel + ' 文件不在包里'); return; }
      const b = fs.statSync(abs).size;
      if (b > 40 * 1024) tabErr.push(it.text + ' ' + rel + ' ' + b + 'B 超微信单张 40KB');
      if (b < 200) tabErr.push(it.text + ' ' + rel + ' 小得不像一张图');
    });
  });
  log('tabBar 三个入口都有本地图标与普通/选中两态（文件在包内且 ≤40KB）', tabErr.length === 0, tabErr.join(','));
  const genTool = fs.readFileSync(path.join(REPO, 'wow-forever-web/tools/gen-tabbar-icons.py'), 'utf8');
  log('tabBar 图标是脚本按令牌自绘的（生成器在仓库里，颜色读 app.wxss，不抄第三方素材）',
    /token\("txt-muted"\)/.test(genTool) && /token\("gold-hot"\)/.test(genTool) && !/魔兽|WoW|暴雪/.test(genTool));

  /* —— 首页底图：清单只有一处真源，页面与导出层都不许各写一份 —— */
  const uiPack = JSON.parse(fs.readFileSync(path.join(REPO, 'wow-forever-web/src/data/ui-art.json'), 'utf8'));
  const uiRels = [];
  (function walkUi(node) {
    if (!node || typeof node !== 'object') return;
    Object.keys(node).forEach((k) => { if (k === 'path') uiRels.push(node[k]); else walkUi(node[k]); });
  })(uiPack.home);
  const uiMiss = uiRels.filter((p) => p.indexOf('img/') !== 0 || !fs.existsSync(path.join(REPO, 'wow-forever-web', 'src', p)));
  const metaOut = JSON.parse(fs.readFileSync(path.join(REPO, 'for-mini/oss-preview/meta.json'), 'utf8'));
  const shipped = [((metaOut.uiArt || {}).bg || '')].concat(Object.keys(((metaOut.uiArt || {}).cards) || {}).map((k) => metaOut.uiArt.cards[k]));
  /* 官方宣传画是市场图，不是客户端原画——红线要求避开商标词，所以"画面里没有字和 logo"
     这件事必须落在 manifest 里，而不是靠下一个改图的人自己记得去看。 */
  const keyManifest = JSON.parse(fs.readFileSync(path.join(REPO, 'wow-forever-web/src/img/keyart/manifest.json'), 'utf8'));
  const keyItem = (keyManifest.items || []).filter((i) => i.kept !== false)[0] || {};
  log('首页背景那张官方宣传画登记齐全：来源是官方页、做过商标词自查、也记了"国服那张带字标所以不用"',
    /^https?:\/\//.test(String(keyItem.source || '')) && /blizzard|akamaihd/.test(String(keyItem.sourcePage || ''))
      && /无「魔兽|无字|不含/.test(String(keyItem.trademarkCheck || ''))
      && /字标|logo/.test(JSON.stringify(keyItem.rejected || {})) && !!keyItem.sha256,
    JSON.stringify({ source: keyItem.source, sha: String(keyItem.sha256 || '').slice(0, 8) }));
  log('界面底图清单齐全：本地都有文件，且原样进了 meta 分片（img/ 换成 assets 相对路径）',
    uiRels.length === 5 && uiMiss.length === 0 && shipped.length === 5
      && shipped.every((s) => s && s.indexOf('img/') !== 0), JSON.stringify({ uiRels, shipped, uiMiss }));
  /* 界面文字要先把 WXML 注释剥掉再比：注释里写"『查』『去查』这类字眼不要了"是给人看的说明，
     不是玩家看得见的字——上一版没剥注释，被自己写的注释判红了。 */
  const homeText = homeWxml.replace(/<!--[\s\S]*?-->/g, ' ');
  const clsText = clsWxml.replace(/<!--[\s\S]*?-->/g, ' ');
  log('首页不再出现「查」「去查」「去看」这类字样',
    !/>查</.test(homeText) && !/去查|去看/.test(homeText) && homeWxss.indexOf('.entry-go') < 0,
    '整张卡就是入口');
  log('职业页：职业用五列格（与首页同一份版式），组合改三列上下结构且没有"看这个职业"',
    /class="cls9"/.test(clsWxml) && /class="combo3"/.test(clsWxml) && !/看这个职业/.test(clsText)
      && fs.readFileSync(path.join(REPO, 'for-mini/app.wxss'), 'utf8').indexOf('.cls9') >= 0,
    '版式在 app.wxss 共用一份，两页不各写一套');

  /* 秒表撤了就要撤干净：模板里不再渲染，样式里也不留一段没人用的 .cd-clock */
  log('秒表撤干净了（模板不渲染 cd.clock，样式里也没有 .cd-clock 残留）',
    homeWxml.indexOf('cd.clock') < 0 && homeWxml.indexOf('cd-clock') < 0 && homeWxss.indexOf('.cd-clock') < 0,
    '只留天数与"就在今天"两种读数');
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
