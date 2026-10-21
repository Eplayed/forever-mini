#!/usr/bin/env node
/* M01 副本随手查 · 微信开发者工具端的回归脚本（可重跑）
   怎么跑：
     1) "/Applications/wechatwebdevtools.app/Contents/MacOS/cli" auto --project <仓库绝对路径>/for-mini --auto-port 9421
     2) NODE_PATH=<miniprogram-automator 所在 node_modules> node wow-forever-web/tools/mini-m01-check.js
        （本机用的是 npx 缓存里的那份：~/.npm/_npx/<hash>/node_modules）
     3) 退出码 0 = 全绿；截图落在 for-mini/docs/screenshots/m01-2026-10-21/
   它测什么：A 真 bucket 空批次 → 主包快照；B 本地假 OSS（tools/oss-fake-server.js，真 HTTP + 真 ETag）→ live 全链路；
   C 分片/索引被改一个字段 → 客户端拒绝并降级；D 契约版本比客户端新 → 提示更新；E 搜索/筛选计数/收藏/跳转/最近看过；F 断网有缓存 → 离线缓存。
   不测什么：真实点击（本机 automator 拿不到页面元数据，交互是调用页面自己的事件处理器 + 合成事件对象），
   以及真机（iOS/Android）上的域名白名单与缓存行为。这两条记在验证文件的"没验到的"里。
   注意：截图必须先落到项目目录之外再拷进去——开发者工具开着 compileHotReLoad，
   往 for-mini/ 里写文件会触发热重载，把小程序打回首页，制造一片假红。
   ------------------------------------------------------------------
/* M01 小程序端验证（微信开发者工具模拟器 + 本地假 OSS）
   跑法：NODE_PATH=<automator 的 node_modules> node /tmp/mp-m01c.js
   链路：页面代码原样跑在模拟器里；网络由 tools/oss-fake-server.js 按真 HTTP 语义供（含 ETag 头）。
   页面状态读的是页面实例自己的 data；交互是调用页面自己的事件处理器（合成事件对象），
   WXML 绑定本身要人工点一遍——记在验证文件的"没验到的"里。 */
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const MPmod = require('miniprogram-automator/out/MiniProgram');
const MiniProgram = MPmod.default || MPmod;
MiniProgram.prototype.checkVersion = async () => true;   /* IDE 版本字段取不到，跳过握手（工具链问题） */
const automator = require('miniprogram-automator');

const REPO = '/Users/zhangyajun/Documents/project/wow-forever';
const BUILD = path.join(REPO, 'for-mini/oss-build/beta');
/* 截图先落到项目外：开发者工具开着 compileHotReLoad，往 for-mini/ 里写文件会触发热重载，
   热重载把小程序打回首页，于是"导航后路由没到位"全是假红。跑完再拷进 docs/screenshots/。 */
const SHOT_DIR = '/tmp/m01-shots';
const SHOT_TARGET = path.join(REPO, 'for-mini/docs/screenshots/m01-2026-10-21');
const SERVER = path.join(REPO, 'wow-forever-web/tools/oss-fake-server.js');
/* 每种模式换一个新端口＝一个新 URL 空间。
   模拟器会照 Cache-Control 把批次文件缓存住（真线上也该这样），
   同一 URL 换内容它是看不到的；不换端口做"篡改/新版本"场景就会读到上一轮缓存，测的是缓存不是校验。 */
const PORT_BASE = 9300 + (process.pid % 40) * 3;
const MODE_PORT = { normal: PORT_BASE, tamper: PORT_BASE + 1, tamperindex: PORT_BASE + 2, min99: PORT_BASE + 3 };
let PORT = PORT_BASE;
const man = JSON.parse(fs.readFileSync(path.join(BUILD, 'manifest.json'), 'utf8'));
const B = man.buildId;

const results = [];
const log = (name, pass, info) => {
  results.push({ name, pass: !!pass, info: info === undefined ? '' : String(info) });
  process.stdout.write((pass ? '  ✓ ' : '  ✗ ') + name + (info ? '  → ' + String(info).slice(0, 240) : '') + '\n');
};
const T = (p, ms, l) => Promise.race([p, new Promise((_, r) => setTimeout(() => r(new Error('TMO ' + l)), ms))]);
let mp;
/* 本机的 automator 链路会偶发丢回包（同一命令重发就好），所以所有调用都带重试 */
async function call(label, fn, tries) {
  let last;
  for (let i = 0; i < (tries || 3); i += 1) {
    try { return await T(Promise.resolve().then(fn), 20000, label); }
    catch (e) { last = e; await new Promise((r) => setTimeout(r, 700)); }
  }
  log('链路抖动：' + label + '（重试 ' + (tries || 3) + ' 次仍失败）', false, last && last.message);
  return null;
}
const ev = (fn, ...a) => call('evaluate', () => mp.evaluate(fn, ...a));

const http = require('http');
function probeDetail() {
  return new Promise((resolve) => {
    const rel = 'builds/' + B + '/dungeons/detail/ragefire-chasm.json';
    const req = http.get('http://127.0.0.1:' + PORT + '/wow/beta/v1/' + rel, (res) => {
      let body = '';
      res.on('data', (d) => { body += d; });
      res.on('end', () => resolve({ mode: res.headers['x-fake-oss'], etag: res.headers.etag, tampered: /被改过/.test(body) }));
    });
    req.on('error', () => resolve({ mode: 'ERR' }));
    req.setTimeout(1500, () => { req.destroy(); resolve({ mode: 'TMO' }); });
  });
}
function probe() {
  return new Promise((resolve) => {
    const req = http.get('http://127.0.0.1:' + PORT + '/wow/beta/v1/manifest.json', (res) => {
      res.resume();
      resolve(res.statusCode);
    });
    req.on('error', () => resolve(0));
    req.setTimeout(1500, () => { req.destroy(); resolve(0); });
  });
}
let live = null;
async function stopServer() {
  if (live) { try { process.kill(live.pid, 'SIGKILL'); } catch (e) {} try { live.kill('SIGKILL'); } catch (e) {} live = null; }
  try { cp.execSync('pkill -9 -f oss-fake-server.js', { stdio: 'ignore' }); } catch (e) {}
  for (let i = 0; i < 25; i += 1) { if ((await probe()) === 0) return; await new Promise((r) => setTimeout(r, 300)); }
  log('端口 ' + PORT + ' 上还有东西在应答', false, 'probe=' + (await probe()));
}
async function startServer(mode) {
  await stopServer();
  const p = cp.spawn('node', [SERVER], { env: Object.assign({}, process.env, { FAKE_OSS_MODE: mode, FAKE_OSS_PORT: String(PORT), FAKE_OSS_NOCACHE: '1' }) });
  p.stderr.on('data', (d) => process.stdout.write('[fake-oss!] ' + String(d).slice(0, 200)));
  live = p;
  for (let i = 0; i < 25; i += 1) {
    if ((await probe()) === 200) {
      const head = await probeDetail();
      process.stdout.write('    → 假 OSS 模式 ' + mode + ' @' + PORT + ' · x-fake-oss=' + head.mode + ' · ETag=' + head.etag + '\n');
      return 'http://127.0.0.1:' + PORT;
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  log('假 OSS 起不来（模式 ' + mode + '）', false, '');
  return null;
}


async function main() {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  mp = await automator.connect({ wsEndpoint: 'ws://127.0.0.1:9421' });
  process.stdout.write('已连上开发者工具；线上批次 ' + B + ' 由本地假 OSS 供（真 HTTP + 真 ETag）\n');

  async function nav(url) {
    const expect = url.replace(/^\//, '').split('?')[0];
    const navRes = await call('reLaunch ' + url, () => mp.evaluate((u) => new Promise((res) => {
      wx.reLaunch({ url: u, success: () => res('ok'), fail: (e) => res('FAIL ' + JSON.stringify(e)) });
    }), url), 4);
    process.stdout.write('    → reLaunch ' + url + ' 回：' + String(JSON.stringify(navRes)).slice(0, 160) + '\n');
    let last = null;
    for (let i = 0; i < 14; i += 1) {
      last = await call('读路由', () => mp.evaluate(() => {
        const p = getCurrentPages().pop();
        return p ? { route: p.route, src: p.data ? p.data.sourceText : null, n: p.data ? (p.data.list || []).length : 0 } : null;
      }), 2);
      if (last && last.route === expect) { await new Promise((x) => setTimeout(x, 900)); return last; }
      await new Promise((x) => setTimeout(x, 700));
    }
    log('导航后路由没到位：' + url, false, '最后读到 ' + JSON.stringify(last));
    return null;
  }
  const snap = () => call('page.data', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    if (!p) return null;
    const d = p.data || {};
    return {
      route: p.route, sourceText: d.sourceText, offline: d.offline, requiresUpdate: d.requiresUpdate,
      kindsArr: d.kinds || [], levelsArr: d.levels || [],
      buildId: d.buildId, factLatest: d.factLatest, all: (d.all || []).length, list: (d.list || []).length,
      kinds: d.kinds || [], levels: d.levels || [], recent: (d.recent || []).length, routeMissing: d.routeMissing,
      dataFrom: d.dataFrom, needOnline: d.needOnline, notFound: d.notFound, title: d.title, nameMissing: d.nameMissing,
      bosses: d.bosses || [], drops: d.drops || [], prov: d.prov || [], rows: d.rows || [], bossEmpty: d.bossEmpty,
      detailSource: d.detailSource, conflict: d.conflict, id: d.id, cacheHint: d.source, cacheHit: d.cacheHit
    };
  }), 4);
  const shot = (name) => call('截图 ' + name, () => mp.screenshot({ path: path.join(SHOT_DIR, name + '.png') }), 2);
  const setOrigin = (v) => {
    curOrigin = v || '';
    return call('设 dev_origin', () => mp.evaluate((o) => {
      if (o) { wx.setStorageSync('wow_forever_v1_dev_origin', o); } else { wx.removeStorageSync('wow_forever_v1_dev_origin'); }
      return wx.getStorageSync('wow_forever_v1_dev_origin') || '已清';
    }, curOrigin));
  };
  let curOrigin = '';
  const clearStore = () => call('清 storage', () => mp.evaluate((o) => {
    try { wx.clearStorageSync(); } catch (e) {}
    if (o) { wx.setStorageSync('wow_forever_v1_dev_origin', o); }
    return wx.getStorageSync('wow_forever_v1_dev_origin') || '线上';
  }, curOrigin));

  /* ---------- A. 真线上状态：beta 命名空间里没有批次 ---------- */
  process.stdout.write('\nA. 不打本地假 OSS，直连真 bucket（那里 beta 是空的）\n');
  await setOrigin('');
  await clearStore();
  await nav('/pages/home/index');
  let s = (await snap()) || {};
  log('首页 meta：线上取不到 → 打包快照，界面标出来', /快照/.test(String(s && s.sourceText)) && s && s.offline === true, JSON.stringify(s && { src: s.sourceText }));
  await shot('a1-home-snapshot');

  await nav('/pages/dungeons/index');
  s = (await snap()) || {};
  log('列表页：38 座全在主包快照里，且不冒充实时', /快照/.test(String(s && s.sourceText)) && s.all === 38 && s.list === 38 && !s.buildId, JSON.stringify({ src: s.sourceText, all: s.all, b: s.buildId }));
  log('列表页：38 座 route 全缺如实登记', s.routeMissing === 38, String(s.routeMissing));
  log('列表页：分组计数与总数同一口径', s.kinds[0].count === 38 && s.kinds.slice(1).reduce((a, k) => a + k.count, 0) === 38, JSON.stringify(s.kinds));
  await shot('a2-dungeons-snapshot');

  await nav('/pages/dungeon/index?id=ragefire-chasm');
  s = (await snap()) || {};
  log('详情页：首用离线只给索引字段 + 明说详情需联网', s && s.needOnline === true && (s.bosses || []).length === 0 && !!s.title, JSON.stringify({ need: s && s.needOnline, t: s && s.title }));
  await shot('a3-detail-need-online');

  await nav('/pages/dungeon/index?id=no-such-dungeon');
  s = (await snap()) || {};
  log('详情页：不存在的 id 走"没收录"分支并给返回入口', s && s.notFound === true && /no-such-dungeon/.test(String(s.id)), JSON.stringify({ nf: s && s.notFound, id: s && s.id }));
  await shot('a4-detail-unknown-id');

  /* ---------- B. 本地假 OSS 供这一批：走 live ---------- */
  process.stdout.write('\nB. 本地假 OSS 供 ' + B + '（HTTP 头里带真 ETag）→ 走 live\n');
  await setOrigin(await startServer('normal'));
  await clearStore();
  await nav('/pages/dungeons/index');
  s = (await snap()) || {};
  log('列表页：指针 + 索引在线取到 → 实时数据', s && s.sourceText === '实时数据' && s.offline === false, JSON.stringify({ src: s.sourceText }));
  log('列表页：批次号来自指针、形制合法', new RegExp('^[a-f0-9]{12}$').test(String(s.buildId)), String(s.buildId));
  log('列表页：核对日期用 factDates 不是构建时间', s.factLatest === '2026-10-11', String(s.factLatest));
  await shot('b1-dungeons-live');

  await nav('/pages/dungeon/index?id=ragefire-chasm');
  s = (await snap()) || {};
  log('详情页：wx.request 拿得到 ETag，校验通过后显示真内容', s && s.needOnline === false && (s.bosses || []).length === 4 && (s.drops || []).length > 0,
    JSON.stringify({ bosses: s && (s.bosses || []).length, drops: (s.drops || []).length, src: s && s.detailSource }));
  log('详情页：首领/掉落里没有站内图片路径', !/(img|src)\//.test(JSON.stringify(s.bosses) + JSON.stringify(s.drops)), '');
  log('详情页：掉落不出现百分比', !/\d+(\.\d+)?\s*%/.test(JSON.stringify(s.drops)), '');
  log('详情页：每条来源带核对日期，缺的写"未记录"', (s.prov || []).length > 0 && (s.prov || []).every((x) => !!x.checkedAt), JSON.stringify((s.prov || [])[0]));
  log('详情页：关键信息行含等级与首领数', (s.rows || []).length >= 6, JSON.stringify((s.rows || []).slice(0, 3)));
  await shot('b2-detail-live');

  await nav('/pages/dungeon/index?id=barrow-deeps');
  s = (await snap()) || {};
  log('详情页：缺中文名显示"中文名待核"，标题退回英文', s && s.nameMissing === true && /Barrow|barrow/.test(String(s.title)), JSON.stringify({ t: s && s.title }));
  log('详情页：首领空数组写"没有记录"而不是 0 个', (s.bosses || []).length === 0 && /没有记录/.test(String(s.bossEmpty)), JSON.stringify({ e: s.bossEmpty }));
  await shot('b3-detail-missing-fields');

  await nav('/pages/dungeon/index?id=hall-of-thanes');
  s = (await snap()) || {};
  log('详情页：分歧名两个都留（领主大厅 / 另一说法诸王大厅）', /诸王大厅/.test(String(s.conflict)) && /领主大厅/.test(String(s.title)), JSON.stringify({ t: s.title, c: s.conflict }));
  await shot('b4-detail-conflict-name');

  await nav('/pages/dungeons/index');
  s = (await snap()) || {};
  log('二次打开：同批缓存命中仍算实时（不谎报离线缓存）', /实时数据（本机缓存/.test(String(s.sourceText)), JSON.stringify({ src: s.sourceText }));

  /* ---------- C. 篡改一个字段：ETag 拦下 ---------- */
  process.stdout.write('\nC. 假 OSS 把一个字段改了（ETag 随之变）→ 客户端必须拒绝这份内容\n');
  await setOrigin(await startServer('tamper'));
  await clearStore();
  await nav('/pages/dungeon/index?id=ragefire-chasm');
  s = (await snap()) || {};
  log('详情页：分片 ETag 与索引记的值对不上 → 这份内容不给看', s && s.needOnline === true && (s.bosses || []).length === 0, JSON.stringify({ need: s && s.needOnline, bosses: s && (s.bosses || []).length }));
  log('详情页：被改过的那个字确实没进界面', !/被改过/.test(JSON.stringify(s)), '');
  await shot('c1-integrity-block');

  await setOrigin(await startServer('tamperindex'));
  await clearStore();
  await nav('/pages/dungeons/index');
  s = (await snap()) || {};
  log('列表页：索引与指针校验值对不上 → 整批不显示，退回主包快照', /快照/.test(String(s.sourceText)) && s.dataFrom === 'snapshot' && s.all === 38,
    JSON.stringify({ src: s.sourceText, from: s.dataFrom, all: s.all, b: s.buildId }));
  await shot('c2-index-tamper-snapshot');

  /* ---------- D. 契约版本比客户端新 ---------- */
  process.stdout.write('\nD. 批次要求 minClientSchemaVersion=99 → 必须提示更新小程序\n');
  await stopServer();
  await setOrigin(await startServer('min99'));
  await clearStore();
  await nav('/pages/dungeons/index');
  s = (await snap()) || {};
  log('列表页：requiresUpdate 为真（顶条提示由界面渲染）', s && s.requiresUpdate === true, JSON.stringify({ u: s && s.requiresUpdate }));
  await shot('d1-schema-too-new');

  /* ---------- E. 搜索 / 筛选 / 收藏 / 列表进详情 ---------- */
  process.stdout.write('\nE. 搜索、筛选计数、收藏、跳转\n');
  await stopServer();
  await setOrigin(await startServer('normal'));
  await clearStore();
  await nav('/pages/dungeons/index');
  const searchRes = await call('搜索处理器', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: '怒焰' } });
    return new Promise((res) => setTimeout(() => res({
      n: p.data.list.length, ids: p.data.list.map((x) => x.id), all: p.data.kinds[0].count, kw: p.data.kw
    }), 500));
  }), 4);
  log('搜「怒焰」：只剩怒焰裂谷，「全部」计数同步为 1', searchRes && searchRes.n === 1 && searchRes.ids[0] === 'ragefire-chasm' && searchRes.all === 1, JSON.stringify(searchRes));
  await shot('e1-search');

  const raidRes = await call('筛团本', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.onKw({ detail: { value: '' } });
    p.onKind({ currentTarget: { dataset: { kind: 'raid' } } });
    return new Promise((res) => setTimeout(() => res({
      n: p.data.list.length, active: p.data.activeKind, kinds: p.data.kinds
    }), 500));
  }), 4);
  /* 分面计数的正确口径：同一维度里每个按钮＝"选它会得到几座"（不受本维度当前选择影响），
     受其它维度约束；所以选中的那个必须等于结果数，非选中的几个之和必须等于「全部」。 */
  log('筛「团本」：选中项计数 == 结果数，三类之和 == 「全部」', raidRes && raidRes.n === 3 && raidRes.active === 'raid'
    && raidRes.kinds.filter((k) => k.key === 'raid')[0].count === raidRes.n
    && raidRes.kinds.slice(1).reduce((a, k) => a + k.count, 0) === raidRes.kinds[0].count, JSON.stringify(raidRes));
  await shot('e2-filter-raid');

  const lvlRes = await call('筛 L0', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.onKind({ currentTarget: { dataset: { kind: 'all' } } });
    p.onLevel({ currentTarget: { dataset: { level: 'L0' } } });
    return new Promise((res) => setTimeout(() => res({
      n: p.data.list.length, pure: p.data.list.every((x) => x.level === 'L0'),
      sel: p.data.levels.filter((l) => l.key === 'L0')[0].count,
      sum: p.data.levels.slice(1).reduce((a, l) => a + l.count, 0), allCount: p.data.levels[0].count
    }), 500));
  }), 4);
  log('筛 L0：结果全是 L0、选中项计数 == 结果数、各可信度之和 == 全部', lvlRes && lvlRes.n > 0 && lvlRes.pure
    && lvlRes.sel === lvlRes.n && lvlRes.sum === lvlRes.allCount, JSON.stringify(lvlRes));

  const favRes = await call('收藏', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.onLevel({ currentTarget: { dataset: { level: 'all' } } });
    p.onFav({ currentTarget: { dataset: { id: 'ragefire-chasm' } } });
    return new Promise((res) => setTimeout(() => {
      p.onFavOnly();
      setTimeout(() => res({
        stored: wx.getStorageSync('wow_forever_v1_fav_dungeons'),
        n: p.data.list.length, ids: p.data.list.map((x) => x.id)
      }), 500);
    }, 400));
  }), 4);
  log('收藏后只看收藏：只剩这座，存储 key 在前缀内', favRes && String(JSON.stringify(favRes.stored)).indexOf('ragefire-chasm') >= 0
    && favRes.n === 1 && favRes.ids[0] === 'ragefire-chasm', JSON.stringify(favRes));
  await shot('e3-fav-only');

  const openRes = await call('列表进详情', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onFavOnly();
    p.onOpen({ currentTarget: { dataset: { id: 'ragefire-chasm' } } });
    setTimeout(() => {
      const q = getCurrentPages().pop();
      res({ route: q.route, id: q.data.id, bosses: (q.data.bosses || []).length, depth: getCurrentPages().length,
        recent: wx.getStorageSync('wow_forever_v1_recent_dungeons'), ptr: q.data.buildId });
    }, 3200);
  })), 4);
  log('列表点进详情：带 id 跳转并渲染 4 个首领', openRes && /pages\/dungeon\/index/.test(String(openRes.route)) && openRes.bosses === 4 && openRes.depth === 2, JSON.stringify(openRes));
  await shot('e4-detail-from-list');

  await call('回首页', () => mp.evaluate(() => new Promise((res) => {
    wx.switchTab({ url: '/pages/home/index', success: () => setTimeout(() => res(1), 1400), fail: () => res(0) });
  })), 3);
  s = (await snap()) || {};
  log('首页「最近查过的副本」记下这座本', s && s.route === 'pages/home/index' && s.recent >= 1, JSON.stringify({ r: s && s.recent }));
  await shot('e5-home-recent');
  await call('首页往下滚', () => mp.evaluate(() => new Promise((r) => {
    wx.pageScrollTo({ scrollTop: 620, success: () => r(1), fail: () => r(0) });
    setTimeout(() => r(1), 900);
  })), 2);
  await shot('e5b-home-recent-scrolled');

  /* ---------- F. 断网但有本批缓存 ---------- */
  process.stdout.write('\nF. 关掉假 OSS（连不上）→ 有本批缓存时是离线缓存\n');
  await stopServer();
  await nav('/pages/dungeons/index');
  s = (await snap()) || {};
  log('断网有缓存：标离线缓存且列表仍有 38 座', s && /离线缓存/.test(String(s.sourceText)) && s.list === 38 && s.offline === true, JSON.stringify({ src: s.sourceText, n: s.list }));
  await shot('f1-offline-cache');

  const ov = await call('量溢出', () => mp.evaluate(() => ({ sw: document.body.scrollWidth, cw: document.body.clientWidth })), 3);
  log('模拟器视口内不横向溢出', ov && ov.sw <= ov.cw + 1, JSON.stringify(ov));

  await stopServer();
  await setOrigin('');
  await clearStore();
  fs.mkdirSync(SHOT_TARGET, { recursive: true });
  fs.readdirSync(SHOT_DIR).forEach((f) => fs.copyFileSync(path.join(SHOT_DIR, f), path.join(SHOT_TARGET, f)));
  process.stdout.write('截图已拷到 ' + SHOT_TARGET + '（' + fs.readdirSync(SHOT_DIR).length + ' 张）\n');
  fs.writeFileSync('/tmp/mp-m01-results.json', JSON.stringify({ buildId: B, results }, null, 1));
  const bad = results.filter((r) => !r.pass);
  process.stdout.write('\n通过 ' + (results.length - bad.length) + ' / ' + results.length + (bad.length ? ' · 未过：' + bad.map((b) => b.name).join('、') : '') + '\n');
  await mp.disconnect();
  process.exit(bad.length ? 1 : 0);
}

main().catch((e) => {
  process.stdout.write('\n脚本异常：' + (e && e.stack ? e.stack : e) + '\n');
  fs.writeFileSync('/tmp/mp-m01-results.json', JSON.stringify({ results }, null, 1));
  process.exit(2);
});
