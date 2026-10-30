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
/* 开关的"线上那一份"放在项目外：回归要演"拧一下开关"，但往 for-mini/ 里写会触发
   compileHotReLoad，把小程序打回首页（2026-10-27 踩过）。假 OSS 支持 FAKE_OSS_FLAGS_FILE 覆写。 */
const LIVE_FLAGS = '/tmp/m01-flags-live.json';
/* 假 OSS 的访问流水（同样写在项目外）：数的是"这一页到底发了几次请求"。
   2026-10-30 接真实 3D 那条硬要求——进配装页一个模型请求都不许发、点「查看 3D」只取一次清单——
   只能这么证；在页面里自己数等于让被试对象自己报数。 */
const OSS_HITS = '/tmp/m01-oss-hits.log';
const hitsClear = () => { try { fs.writeFileSync(OSS_HITS, ''); } catch (e) {} };
const hitsOf = (pat) => {
  let lines = [];
  try { lines = fs.readFileSync(OSS_HITS, 'utf8').split('\n'); } catch (e) { return []; }
  return lines.filter((l) => l && pat.test(l));
};
/* 每种模式换一个新端口＝一个新 URL 空间。
   模拟器会照 Cache-Control 把批次文件缓存住（真线上也该这样），
   同一 URL 换内容它是看不到的；不换端口做"篡改/新版本"场景就会读到上一轮缓存，测的是缓存不是校验。 */
const PORT_BASE = 9300 + (process.pid % 40) * 3;
const MODE_PORT = { normal: PORT_BASE, tamper: PORT_BASE + 1, tamperindex: PORT_BASE + 2, min99: PORT_BASE + 3 };
let PORT = PORT_BASE;
const man = JSON.parse(fs.readFileSync(path.join(BUILD, 'manifest.json'), 'utf8'));
const OSS_ORIGIN = 'https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com';
/* 五人本座数从本批索引现读：列表页默认筛五人本，断言要拿它当期望值 */
const IDX0 = JSON.parse(fs.readFileSync(path.join(BUILD, 'builds', man.buildId, 'dungeons', 'index.json'), 'utf8'));
const FIVE_N = IDX0.items.filter((i) => i.partySize === 5).length;
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
  fs.copyFileSync(path.join(BUILD, 'flags.json'), LIVE_FLAGS);
  const p = cp.spawn('node', [SERVER], { env: Object.assign({}, process.env, { FAKE_OSS_MODE: mode, FAKE_OSS_PORT: String(PORT), FAKE_OSS_NOCACHE: '1', FAKE_OSS_FLAGS_FILE: LIVE_FLAGS, FAKE_OSS_LOG: OSS_HITS }) });
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
      dropGroups: (d.dropGroups || []).map((g) => ({ boss: g.boss, rows: (g.rows || []).map((r) => ({ itemId: r.itemId, q: r.q, quality: r.quality, name: r.name })) })),
      highlightDrop: d.highlightDrop,
      detailSource: d.detailSource, conflict: d.conflict, id: d.id, cacheHint: d.source, cacheHit: d.cacheHit,
      counts: d.counts, cov: (d.covList || []).length, wip: (d.wip || []).length, meta: d.meta ? { counts: d.meta.counts } : null
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

  /* ---------- A. 断网等价场景：指针取不到 → 主包快照 ----------
     以前这一段是"直连真 bucket，赌 beta 是空的"。beta 一旦有批次（M02 已发），
     这四条就全变成假红——门禁的前提不该是"线上还没东西"。
     改成把取数地址指到一个必然 404 的前缀：拿不到指针这件事与 beta 有没有数据无关。 */
  process.stdout.write('\nA. 指针取不到（地址指到一个空前缀）→ 主包快照兜底\n');
  await setOrigin(OSS_ORIGIN + '/m01-no-such-namespace');
  await clearStore();
  await nav('/pages/home/index');
  let s = (await snap()) || {};
  /* 首页现在只用一条顶条说"没连上"（玩家面不再印 sourceText/核对日期），
     所以这里断言 offline 标记为真——顶条由 wx:if 渲染，截图里看得见。 */
  log('首页：线上取不到 → offline 标记为真（顶条提示由界面渲染）', s && s.offline === true, JSON.stringify({ off: s && s.offline }));
  await shot('a1-home-snapshot');

  await nav('/pages/dungeons/index');
  s = (await snap()) || {};
  /* 新 IA 默认落在五人本，全量 38 座在快照里、切「全部」才列全 */
  log('列表页：38 座全在主包快照里，默认五人本、切全部才列全', /快照/.test(String(s && s.sourceText)) && s.all === 38 && s.list === FIVE_N && !s.buildId,
    JSON.stringify({ src: s.sourceText, all: s.all, list: s.list, five: FIVE_N, b: s.buildId }));
  /* 2026-10-22 站主定的玩家面规矩：聚合数、缺口自述、可信度筛选一律不上界面。
     门禁反过来守这条——页面上再长出 count / routeMissing / levels 就是回归。 */
  log('列表页不再挂聚合数与可信度筛选（玩家面规矩）',
    s.kinds.every((k) => k.count === undefined) && (s.levels || []).length === 0 && s.routeMissing === undefined,
    JSON.stringify({ kinds: s.kinds, levels: s.levels, rm: s.routeMissing }));
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
  /* 不抄日期字面量：这一批的核对日期由数据决定，本地清单说什么就是什么 */
  log('列表页：核对日期用 factDates 不是构建时间', s.factLatest === man.factDates.latest,
    '页面 ' + s.factLatest + ' / 清单 ' + man.factDates.latest);
  await shot('b1-dungeons-live');

  await nav('/pages/dungeon/index?id=ragefire-chasm');
  s = (await snap()) || {};
  log('详情页：wx.request 拿得到 ETag，校验通过后显示真内容', s && s.needOnline === false && (s.bosses || []).length === 4 && (s.drops || []).length > 0,
    JSON.stringify({ bosses: s && (s.bosses || []).length, drops: (s.drops || []).length, src: s && s.detailSource }));
  log('详情页：首领/掉落里没有站内图片路径', !/(img|src)\//.test(JSON.stringify(s.bosses) + JSON.stringify(s.drops)), '');
  log('详情页：掉落不出现百分比', !/\d+(\.\d+)?\s*%/.test(JSON.stringify(s.drops)), '');
  /* 来源这一节 2026-10-23 从玩家页撤了（站主指令：详情页不要"来源"这块）。
     撤的是界面，不是记录——逐条来源必须仍在分片里，网页端与审计都靠它，
     所以这条断言改成读批次文件，而不是读页面 data。 */
  log('详情页：不再摆"来源"这一节', (s.prov || []).length === 0 && !/来源/.test(String(s.rows.map((r) => r.k).join())), '');
  const detShard = JSON.parse(fs.readFileSync(path.join(BUILD, 'builds/' + B + '/dungeons/detail/ragefire-chasm.json'), 'utf8'));
  const provRows = (detShard.dungeon.provenance || []);
  log('分片里：每条来源仍能追回去（类型 + 地址），没核对日期的照实是空',
    provRows.length > 0 && provRows.every((x) => !!x.type && !!x.url),
    JSON.stringify(provRows.map((x) => x.type + '/' + (x.checkedAt || 'null'))));

  /* 玩家面规矩：关键信息只留"这座本是什么"的四行事实，
     首领/掉落的计数行与方法论行（掉落口径）已下线——下面两节本来就把内容列出来了。 */
  log('详情页：关键信息只有等级/阵营/位置/人数四行，不带计数与方法论',
    (s.rows || []).length === 4
      && ['可进入等级', '阵营', '位置', '队伍人数'].every((k) => (s.rows || []).some((r) => r.k === k))
      && !(s.rows || []).some((r) => /首领|掉落|口径/.test(r.k)),
    JSON.stringify((s.rows || []).map((r) => r.k)));
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
  /* 三座无限新增本的首领一张脸都没有（源站自己标 data-unknown，2026-10-23 重探仍 0/15）。
     界面不许摆一个写"没有这张头像"的虚线空框——那看着像坏了；交给 icon-cell 回落自绘块。 */
  log('详情页：新本首领没有头像时走自绘回落，页面不再摆"没有这张头像"那句',
    (s.bosses || []).length === 4 && (s.bosses || []).every((b) => b.portraitUrl === ''),
    JSON.stringify((s.bosses || []).map((b) => b.portraitUrl)));
  const faceWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/dungeon/index.wxml'), 'utf8');
  log('详情页：首领一律一个 icon-cell，缺图由组件回落（不留碎图也不留空框）',
    /boss-face/.test(faceWxml) && !/没有这张头像/.test(faceWxml) && !/face-none/.test(fs.readFileSync(path.join(REPO, 'for-mini/pages/dungeon/index.wxss'), 'utf8')), '');

  /* —— 掉落排序与装备详情（2026-10-23 站主指令）—— */
  await nav('/pages/dungeon/index?id=ragefire-chasm');
  s = (await snap()) || {};
  const RANK = { 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6 };
  const unsorted = (s.dropGroups || []).filter((g) => {
    const v = g.rows.map((r) => (r.q === '' || r.q === undefined ? -1 : RANK[r.q]));
    for (let i = 1; i < v.length; i += 1) if (v[i] > v[i - 1]) return true;
    return false;
  });
  log('详情页：每个首领组内按稀有度从高往下排', (s.dropGroups || []).length > 0 && unsorted.length === 0,
    JSON.stringify((s.dropGroups || []).map((g) => g.rows.map((r) => r.q))));
  log('详情页：品质档名与颜色同源（每行带档名与档数，颜色由 .q-<档> 上）',
    (s.dropGroups || []).every((g) => g.rows.every((r) => /普通|优秀|精良|史诗|传说/.test(r.quality))),
    JSON.stringify((((s.dropGroups || [])[0] || {}).rows || []).map((r) => r.quality)));
  await shot('b5-drops-sorted');

  const itemPage = await (async () => {
    await ev(() => {
      const p = getCurrentPages().pop();
      const g = (p.data.dropGroups || [])[0];
      const row = g.rows.filter((r) => !!r.itemId)[0];
      p.onOpenItem({ currentTarget: { dataset: { item: row.itemId, dungeon: p.data.id } } });
      return row.itemId;
    });
    await new Promise((r) => setTimeout(r, 9000));
    return ev(() => {
      const p = getCurrentPages().pop();
      const d = p.data || {};
      return { route: p.route, id: d.itemId, name: d.name, q: d.q, qt: d.qualityText, st: (d.st || []).length, s0: String(((d.st || [])[0] || {}).t || '').slice(0, 12), ilvl: d.ilvl, type: d.type, sell: d.sell, boss: d.boss, dg: d.dungeon, need: d.needOnline, off: d.offline };
    });
  })();
  log('点一件装备：真的换到一个独立页面（不是就地展开）', /pages\/item\/index/.test(String(itemPage.route)) && !!itemPage.id, JSON.stringify(itemPage));
  log('装备详情：名单里的名字/品质/首领与数值侧的属性行/装等/类型都在',
    !!itemPage.name && !!itemPage.boss && itemPage.st > 0 && !!itemPage.type && itemPage.need === false,
    JSON.stringify(itemPage));
  log('装备详情：品质档名与列表那一行是同一套叫法（两屏不许各写一份）',
    /普通|优秀|精良|史诗|传说/.test(String(itemPage.qt)), String(itemPage.qt));
  await shot('b6-item-detail');
  const backFromItem = await ev(() => { wx.navigateBack(); return 1 });
  await new Promise((r) => setTimeout(r, 2500));
  log('装备详情返回副本详情：返回栈在（不是只能重开）', backFromItem === 1, '');

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
      n: p.data.list.length, ids: p.data.list.map((x) => x.id), kw: p.data.kw
    }), 500));
  }), 4);
  log('搜「怒焰」：只剩怒焰裂谷', searchRes && searchRes.n === 1 && searchRes.ids[0] === 'ragefire-chasm', JSON.stringify(searchRes));
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
  log('筛「团本」：只剩三座团本，chip 上不挂条数', raidRes && raidRes.n === 3 && raidRes.active === 'raid'
    && raidRes.kinds.every((k) => k.count === undefined), JSON.stringify(raidRes.kinds));
  await shot('e2-filter-raid');

  const favRes = await call('收藏', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.onKind({ currentTarget: { dataset: { kind: 'all' } } });
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
        recent: wx.getStorageSync('wow_forever_v1_recent_dungeons') });
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
  log('断网有缓存：标离线缓存且默认五人本仍在', s && /离线缓存/.test(String(s.sourceText)) && s.list === FIVE_N && s.offline === true, JSON.stringify({ src: s.sourceText, n: s.list, five: FIVE_N }));
  await shot('f1-offline-cache');

  const ov = await call('量溢出', () => mp.evaluate(() => ({ sw: document.body.scrollWidth, cw: document.body.clientWidth })), 3);
  log('模拟器视口内不横向溢出', ov && ov.sw <= ov.cw + 1, JSON.stringify(ov));

  await stopServer();
  /* ---------- G. H01 首页流式卡片与三 tab ---------- */
  process.stdout.write('\nG. 首页重做（流式卡片入口）与三 tab 结构\n');
  await setOrigin(await startServer('normal'));
  await clearStore();
  await nav('/pages/home/index');
  s = (await snap()) || {};
  const homeCards = await call('首页入口', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    return { go: ['goDungeons', 'goClasses', 'goLoots', 'goGuide'].filter((f) => typeof p[f] === 'function').length,
      glossary: typeof p.goGlossary, counts: p.data.counts, cov: p.data.covList, wip: p.data.wip, fact: p.data.factDate, build: p.data.buildId };
  }), 3);
  /* 2026-10-22 站主重排：入口卡固定四张 副本/职业/掉落查询/指南，中英速查按指令撤出首页 */
  log('首页四个入口卡处理器都在（副本/职业/掉落查询/指南）', homeCards && homeCards.go === 4, JSON.stringify(homeCards));
  log('首页不再有中英速查入口', homeCards && homeCards.glossary === 'undefined', String(homeCards && homeCards.glossary));
  log('首页不出现计数、覆盖率、缺口清单、核对日期与批次号（玩家面规矩）',
    homeCards && homeCards.counts === undefined && (homeCards.cov || []).length === 0
      && (homeCards.wip || []).length === 0 && homeCards.fact === undefined && homeCards.build === undefined,
    JSON.stringify(homeCards));
  /* 版式（两张卡并排、chip 排成一行）不在这里断言：本机的 evaluate 落在 app 服务上下文，
     拿不到 querySelector；这类"看起来对不对"由截图 + 站主眼睛判，脚本只保证数据与导航。 */
  await shot('g1-home-cards');
  const tabCheck = await call('点副本卡', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.goDungeons();
    let n = 0;
    const t = setInterval(() => {
      const r = getCurrentPages().pop();
      n += 1;
      if ((r && r.route === 'pages/dungeons/index') || n > 16) { clearInterval(t); res({ route: r && r.route, depth: getCurrentPages().length }); }
    }, 300);
  })), 3);
  log('首页点「副本随手查」真的切到了副本 tab', tabCheck && tabCheck.route === 'pages/dungeons/index' && tabCheck.depth === 1, JSON.stringify(tabCheck));
  await nav('/pages/dungeon/index?id=ragefire-chasm');
  const backCheck = await call('详情页返回列表', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onBack();
    let n = 0;
    const t = setInterval(() => {
      const r = getCurrentPages().pop();
      n += 1;
      if ((r && r.route === 'pages/dungeons/index') || n > 16) { clearInterval(t); res({ route: r && r.route, depth: getCurrentPages().length }); }
    }, 300);
  })), 3);
  log('详情页「回到副本列表」用 switchTab 打得开 tab 页（redirectTo 会静默失败）',
    backCheck && backCheck.route === 'pages/dungeons/index' && backCheck.depth === 1, JSON.stringify(backCheck));
  await call('回首页', () => mp.evaluate(() => new Promise((res) => {
    wx.switchTab({ url: '/pages/home/index' });
    let n = 0;
    const t = setInterval(() => {
      const r = getCurrentPages().pop();
      n += 1;
      if ((r && r.route === 'pages/home/index') || n > 16) { clearInterval(t); res(1); }
    }, 300);
  })), 3);
  s = (await snap()) || {};
  log('看过一座本之后，首页「继续」里有它（读页面 data，不读 DOM）', s.route === 'pages/home/index' && s.recent >= 1, JSON.stringify({ r: s.recent }));
  await shot('g2-home-recent-rail');

  /* 签名动作用像素量，不靠眼睛：切角铭牌真渲染出来时，
     卡片顶边往下的最右像素必须逐步外移（右上角被切掉一块），直角版不会动。
     判据按"位移 ÷ 卡宽"算，不按像素数算——截图缩放每次可能不一样（同一天拍出过 285 / 570 / 664 三种宽），
     写死像素数的门禁会假红。切角是 CSS 定值 10px、卡宽约 334px，比值恒定 0.015~0.021，直角版是 0。
     2026-10-24 改成量几何，不再按颜色认卡片。这张卡是"按颜色找"第三次被带偏的地方：
     第一次是背景图压暗后整屏接近 --panel（量到 cut=-37），第二次是卡片上玻璃面色，
     第三次是玻璃顶部那条乳白反光——它把卡片上沿十几像素染亮，探针就从切角之前错位，比值 0.0149→0。
     现在分工是：卡片在哪由 DOM 说（`.cd` 的 rect），角有没有被切由像素说。 */
  const PY_CORNER = [
    'import sys',
    'from PIL import Image',
    'import numpy as np',
    'A = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(float)',
    'B = np.asarray(Image.open(sys.argv[2]).convert("RGB")).astype(float)',
    'W = int(A.shape[1])',
    'sc = W / float(sys.argv[3])',
    '# 截图含状态栏与导航条，rect 的 y 是视口坐标：两帧只在底图那一段不一样，',
    '# 第一处"整行都有差"的行就是视口第 0 行',
    'd = np.abs(A - B).mean(axis=2)',
    'wide = (d > 8).sum(axis=1)',
    'off = next((y for y in range(60, 400) if wide[y] > W * 0.9), 0)',
    'bg = np.array([int(x) for x in sys.argv[4:7]], float)',
    'y0 = off + int(round(float(sys.argv[7]) * sc)) - 4',
    'nb = (np.abs(B[:, :, :] - bg).max(axis=2) > 6)',
    'rows = {}',
    '# 只在 DOM 报的那一行往下 60 像素的窗口里找；每行取"不是页底色"的最长一段连续像素',
    'for y in range(max(0, y0), min(B.shape[0], y0 + 60)):',
    '    idx = np.flatnonzero(nb[y])',
    '    if idx.size < 120: continue',
    '    brk = np.flatnonzero(np.diff(idx) > 1)',
    '    segs = np.split(idx, brk + 1)',
    '    seg = max(segs, key=len)',
    '    if len(seg) > 120 and seg[0] > 6 and seg[-1] < W - 6: rows[y] = (int(seg[0]), int(seg[-1]))',
    'ys = sorted(rows)',
    'if not ys: print("none 0 0 0"); raise SystemExit',
    'top = ys[0]',
    'base = top + 14',
    'while base not in rows and base < ys[-1]: base += 1',
    'print("%d %d %d %d" % (top, rows[base][1] - rows[top][1], rows[base][1] - rows[base][0], W))'
  ].join('\n');
  /* 页底色仍然从 app.wxss 现读，不写字面量（写死过一次，换令牌当场假红） */
  const appCss = fs.readFileSync(path.join(REPO, 'for-mini/app.wxss'), 'utf8');
  const bM = appCss.match(/--bg:\s*#([0-9a-fA-F]{6})/);
  if (!bM) {
    log('切角探针拿不到 --bg 令牌，拒绝用旧的字面量继续量', false, 'app.wxss 里没有这个令牌');
  }
  const bgHex = bM ? parseInt(bM[1], 16) : 0;
  const bgRgb = [(bgHex >> 16) & 255, (bgHex >> 8) & 255, bgHex & 255];
  /* 卡片位置与视口标定要在"底图还开着"的时候量（.pagebg 是 wx:if 出来的） */
  const plate = await call('量卡片位置', () => mp.evaluate(() => new Promise((res) => {
    const q = wx.createSelectorQuery();
    q.select('.cd').boundingClientRect();
    q.select('.pagebg').boundingClientRect();
    q.exec((r) => res({ card: r[0], bg: r[1] }));
  })), 2);
  await call('关掉底图再量切角', () => mp.evaluate(() => {
    getCurrentPages().pop().setData({ bgUrl: '' });
    return 1;
  }), 2);
  await new Promise((r) => setTimeout(r, 2200));
  await shot('g1b-home-cards-flatbg');
  const corner = await call('量切角', () => new Promise((resolve) => {
    if (!plate || !plate.card || !plate.bg) { resolve(null); return; }
    cp.execFile('python3', ['-c', PY_CORNER,
      path.join(SHOT_DIR, 'g2-home-recent-rail.png'), path.join(SHOT_DIR, 'g1b-home-cards-flatbg.png'),
      String(plate.bg.width)].concat(bgRgb.map(String)).concat([String(plate.card.top)]),
      { encoding: 'utf8' }, (err, out) => {
      const t = String(out || '').trim();
      if (err || !/\d+ \d+ \d+ \d+$/.test(t)) { resolve(null); return; }
      const [top, cut, width, w] = t.split(' ').map(Number);
      resolve({ top, cut, cardWidth: width, shotWidth: w, ratio: width ? cut / width : 0 });
    });
  }), 2);
  log('切角铭牌真的渲染出来了（右上角斜边让最右像素往外移，直角版比值为 0）',
    !!corner && corner.ratio >= 0.01 && corner.ratio <= 0.045, JSON.stringify(corner));

  /* ---------- H. 配装页（2026-10-26 站主：把网页那条 BiS 线做进小程序） ---------- */
  process.stdout.write('\nH. 配装页：名单能取到、阵营与套能真切、备选与"两家"并列在\n');
  await nav('/pages/bis/index');
  const bis = await call('读配装页', () => mp.evaluate(() => {
    const p = getCurrentPages().pop(); const d = p.data || {};
    const txt = []
      .concat(d.rows || [], d.enchants || [], d.consumables || [], d.slotRows || [])
      .map((x) => [x.name, x.src, (x.st || []).join('|')].join(' '));
    return {
      route: p.route, cls: d.cls, setId: d.setId, fac: d.fac, sourceText: d.sourceText,
      classes: (d.classes || []).length, sets: (d.setList || []).length,
      sumSig: (d.sum || []).map((x) => x.k + x.v).join('+'),
      rows: (d.rows || []).length, head: ((d.rows || [])[0] || {}).name || '',
      sum: (d.sum || []).length, nodes: (d.nodes || []).length,
      disclaimer: (d.meta || {}).disclaimer || '', fetched: d.fetched || '',
      host: d.sourceHost || '', unavailable: !!d.unavailable, needOnline: !!d.needOnline,
      noName: (d.rows || []).filter((r) => r.missing).length,
      srcSample: ((d.rows || []).filter((r) => r.src)[0] || {}).src || '',
      cmp: (d.rows || []).map((r) => r.cmp).join(','),
      text: txt.join(' ')
    };
  }), 3);
  log('配装页打得开：9 个职业、这一套 16 个部位以上、属性合计有数',
    bis && bis.route === 'pages/bis/index' && bis.classes === 9 && bis.rows >= 16 && bis.sum >= 1,
    JSON.stringify(bis && { cls: bis.cls, classes: bis.classes, rows: bis.rows, sum: bis.sum }));
  log('口径那一句与核对日、来源域名都在页面上（红线：不冒充官方结论）',
    !!bis && /不是官方结论/.test(bis.disclaimer) && /^\d{4}-\d{2}-\d{2}$/.test(bis.fetched)
      && /wclbox/.test(bis.host), JSON.stringify(bis && { f: bis.fetched, h: bis.host }));
  /* 取数状态要说真话：sourceLabel 收的是整个结果对象而不是 source 字符串，
     传错参数不会报错，只会永远显示"没取到数据"——2026-10-27 发完 beta 走真页才发现这条。 */
  log('配装页的取数状态说真话（线上取到了就不许写"没取到数据"）',
    !!bis && /实时|缓存/.test(String(bis.sourceText)), JSON.stringify({ src: bis && bis.sourceText }));
  log('装备名回本站物品库查出来了（不是 #编号），来源那一列也还原成了中文',
    !!bis && bis.head.length > 1 && !/^#/.test(bis.head) && /副本|技能|需要|制造|商人|任务/.test(bis.srcSample),
    JSON.stringify(bis && { head: bis.head, src: bis.srcSample.slice(0, 40) }));
  log('这一页没有打包快照：取数走线上，取不到时页面自己说"还没有/要联网"，不半截显示',
    !!bis && (!bis.unavailable || !bis.rows), JSON.stringify(bis && { un: bis.unavailable, on: bis.needOnline }));
  log('"两家怎么说"逐格带角标（一致/分歧/没列），本站不裁决',
    !!bis && /^[a-z,]+$/.test(bis.cmp) && bis.cmp.indexOf('none') < 0 || /same|diff/.test(bis.cmp || ''),
    String(bis && bis.cmp).slice(0, 60));
  const bisHorde = await call('换部落', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.pickFac({ currentTarget: { dataset: { fac: 'horde' } } });
    const d = p.data;
    return { fac: d.fac, facCn: d.facCn, head: ((d.rows || [])[0] || {}).name || '',
      sum: (d.sum || []).length, sumSig: (d.sum || []).map((x) => x.k + x.v).join('+') };
  }), 3);
  /* 有些套两个阵营本来就列同一件装备（战士 PvE 的头部就是同一顶），所以判据是
     "头部那件或属性合计至少有一处跟着变"——两个都没变才是只换了标题没换内容。 */
  log('切阵营真的换了内容（头部那件或属性合计跟着变，不是只改标题）',
    !!bisHorde && bisHorde.fac === 'horde' && bisHorde.facCn === '部落'
      && (bisHorde.head !== bis.head || bisHorde.sumSig !== bis.sumSig),
    JSON.stringify({ all: [bis.head, bis.sumSig], horde: [bisHorde && bisHorde.head, bisHorde && bisHorde.sumSig] }));
  const bisPop = await call('开备选', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.openSlot({ currentTarget: { dataset: { slot: '头部', cell: 1 } } });
    const d = p.data;
    return { slot: d.slot, n: (d.slotRows || []).length, head: d.slotHead,
      theirs: d.slotTheirs && d.slotTheirs.cn, st: ((d.slotRows || [])[0] || {}).st || [] };
  }), 3);
  log('点一个部位弹出这个部位的备选（含属性行与"另一家列的第一件"）',
    !!bisPop && bisPop.n >= 1 && /头部/.test(bisPop.head) && (bisPop.st || []).length > 0
      && /一致|分歧|没列/.test(String(bisPop.theirs)), JSON.stringify(bisPop));
  const bis3d = await call('开占位模型', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.toggle3d();
    const d = p.data;
    return { live: d.live3d, nodes: (d.nodes || []).length, unmapped: d.unmappedText || '' };
  }), 3);
  log('占位人台一件一块，没格子的部位照实列出不硬塞',
    !!bis3d && bis3d.live === true && bis3d.nodes >= 10, JSON.stringify(bis3d));

  /* ---------- 真实 3D（2026-10-30 C 段）----------
     这台模拟器起不了 xr-frame（探针那一轮实测：空场景都不发 ready），
     所以这里钉得住的是"发没发请求、取的是不是当前这一套这一阵营、失败有没有回原画并说明"，
     画面那一半只能由真机回答——不许拿"请求数对了"冒充"玩家看得见模型"。 */
  await call('关掉占位模型回原画', () => mp.evaluate(() => { getCurrentPages().pop().toggle3d(); return 1; }), 2);
  hitsClear();
  const mv = await call('进页后先数一遍模型请求', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { on: d.modelOn, src: d.modelSrc, setId: d.setId, fac: d.fac, state: d.modelState };
  }), 2);
  log('没点「查看 3D」之前：模型清单与模型对象都是 0 次请求、组件没挂、src 为空',
    hitsOf(/bis\/models\/index\.json|assets\/models\/real\//).length === 0
      && !!mv && mv.on === false && !mv.src && mv.state === 'idle', JSON.stringify(mv));
  await call('点「查看 3D」', () => mp.evaluate(() => { getCurrentPages().pop().showModel(); return 1; }), 1);
  await new Promise((r) => setTimeout(r, 1500));
  const m1 = await call('取完之后看页面状态', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { on: d.modelOn, src: d.modelSrc, state: d.modelState, text: d.modelText, err: d.modelErr, setId: d.setId, fac: d.fac };
  }), 2);
  const idxHits = hitsOf(/bis\/models\/index\.json/);
  log('点一次只取一次清单（不进页就取、或把 76 条都拉一遍都不行）',
    idxHits.length === 1, idxHits.join(' | ').slice(0, 120));
  log('取到的正是当前 setId+faction 那一条，文件名带成品哈希、走 https 或本地假 OSS 的 real 目录',
    !!m1 && m1.on === true && new RegExp('/assets/models/real/' + m1.setId + '-' + m1.fac + '-[0-9a-f]{12}\\.glb$').test(String(m1.src)),
    JSON.stringify(m1));
  log('清单没被改过：这一套的名单与登记逐格对得上（对不上会直接回原画并报"逐格没对上"）',
    !!m1 && m1.state !== 'bad' && !/逐格没对上|没有登记/.test(String(m1.err)), String(m1 && m1.err).slice(0, 160));
  const glbHits = hitsOf(/assets\/models\/real\//);
  process.stdout.write('  · 模型对象请求 ' + glbHits.length + ' 次（这台模拟器起不了 xr-frame，真机那一侧才作数）\n');
  await call('在飞的请求还没回来时切阵营', () => mp.evaluate(() => {
    /* 阵营从页面自己读：mp.evaluate 的闭包看不见外层变量（写这一段时撞过一次
       "Uncaught m1 is not defined"——那条红是脚本自己的错，不是页面的） */
    const p = getCurrentPages().pop();
    const here = p.data.fac;
    p.showModel();
    p.pickFac({ currentTarget: { dataset: { fac: here === 'horde' ? 'alliance' : 'horde' } } });
    return 1;
  }), 1);
  await new Promise((r) => setTimeout(r, 1500));
  const m2 = await call('切完之后再数一次', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { on: d.modelOn, src: d.modelSrc, fac: d.fac };
  }), 2);
  log('迟到的那一份不盖掉刚选中的那一套：切阵营后场景是拆掉的、src 清空',
    !!m2 && m2.on === false && !m2.src, JSON.stringify(m2));
  const m3 = await call('演一次取不到（失败分支）', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.showModel();
    p.modelFail('这一套没有登记的真实模型');
    const d = p.data;
    return { on: d.modelOn, state: d.modelState, err: d.modelErr, art: d.stageUrl, rows: (d.rows || []).length, sum: (d.sum || []).length };
  }), 2);
  log('失败就回职业原画并写「3D 暂不可用」＋原因，名单与属性合计一条不少',
    !!m3 && m3.on === false && m3.state === 'bad' && /没有登记/.test(String(m3.err))
      && !!m3.art && m3.rows >= 10 && m3.sum >= 1, JSON.stringify(m3));
  const m4 = await call('演一次"几何在、贴图没数到"', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.teardownModel();
    p.setData({ modelOn: true, modelState: 'loading' });
    p.onModelStatus({ detail: { state: 'geometry', meshes: 20, tex: 0, noTex: 20, detail: 'mat:alpha,beta' } });
    const d = p.data;
    return { on: d.modelOn, state: d.modelState, detail: d.modelDetail, err: d.modelErr };
  }), 2);
  await new Promise((r) => setTimeout(r, 800));
  const m5 = await call('量不到贴图那一格过一会儿再看', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { on: d.modelOn, state: d.modelState };
  }), 2);
  log('贴图尺子量空了也不许把画面藏掉、不许冒充成功那一句（2026-10-30 真机就是被这条误判藏起来的）',
    !!m4 && m4.on === true && m4.state === 'geometry' && /画出来|数到/.test(String(m4.detail)) && !m4.err
      && !!m5 && m5.on === true && m5.state === 'geometry', JSON.stringify({ m4: m4, m5: m5 }));
  await call('收掉这一格', () => mp.evaluate(() => { getCurrentPages().pop().hideModel(); return 1; }), 1);
  const bis3dWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/bis/index.wxml'), 'utf8');
  log('真实模型的 caption「游戏角色与装备的静态预览，拖动可旋转」只在成功态那一格里出现',
    /modelState === 'ok'/.test(bis3dWxml) && /游戏角色与装备的静态预览，拖动可旋转/.test(bis3dWxml), '');
  const appJson = JSON.parse(fs.readFileSync(path.join(REPO, 'for-mini/app.json'), 'utf8'));
  const packCfg = JSON.parse(fs.readFileSync(path.join(REPO, 'for-mini/project.config.json'), 'utf8'));
  log('临时探针路由已从正式 app.json 撤掉，探针目录也不进包（正式包里没有 model-probe）',
    appJson.pages.indexOf('pages/model-probe/index') < 0
      && (packCfg.packOptions.ignore || []).some((x) => x.value === 'pages/model-probe')
      && !(packCfg.packOptions.ignore || []).some((x) => /models/.test(String(x.value))),
    JSON.stringify(appJson.pages.length));
  await shot('h1-bis-page');
  await call('回到占位开着的画面', () => mp.evaluate(() => 1), 1);
  log('配装页渲染文字里没有百分比与强度评价词（红线）',
    !!bis && !/\d+(\.\d+)?\s*%/.test(bis.text) && !/秒伤|DPS|权重/.test(bis.text),
    String(bis && bis.text).slice(0, 80));
  const bisWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/bis/index.wxml'), 'utf8');
  log('占位那句话（「不是游戏里的样子」）仍在：真实模型只在自己成功态那一格说话，两种模式各说各的',
    /占位模型/.test(bisWxml) && /不是游戏里的样子/.test(bisWxml) && /modelState === 'ok'/.test(bisWxml), '');
  const homeWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/home/index.wxml'), 'utf8');
  log('首页有整宽的配装入口卡（站主：核心功能，必须醒目），且排在四张小卡前面',
    /class="bis-card/.test(homeWxml) && /bindtap="goBis"/.test(homeWxml)
      && homeWxml.indexOf('bis-card') < homeWxml.indexOf('class="grid"'), '');


  /* ---------- I. 远程功能开关（2026-10-27 站主："暂时先不公开，想公开了不用发版就能公开"） ----------
     两阶段：① 线上（本地假 OSS 那份 flags.json）关着 → 首页没入口、直接进页只说"还没开放"且不取数；
     ② 只改 flags.json 这一个文件（代码一行不动）→ 重进就出现。
     阶段之间对页面代码文件求哈希，证明"放开这一页没改过代码"。 */
  process.stdout.write('\nI. 远程开关：关着看不见，只改 flags.json 就出现（代码一行没动）\n');
  const crypto01 = require('crypto');
  const sha01 = (p) => crypto01.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 12);
  /* 改的就是假 OSS 供出去的那一份（项目外），代码与批次数据一个字节都不动 */
  const FLAGS_FILE = LIVE_FLAGS;
  const CODE_FILES = ['pages/professions/index.js', 'pages/professions/index.wxml', 'pages/home/index.js',
    'pages/home/index.wxml', 'services/features.js', 'data/flags-local.js', 'app.json'];
  const codeBefore = CODE_FILES.map((f) => f + '=' + sha01(path.join(REPO, 'for-mini', f))).join(' ');
  const flags0 = JSON.parse(fs.readFileSync(FLAGS_FILE, 'utf8'));
  log('这一批带开关对象（与指针同一档，改它不发版）',
    flags0.product === 'wow-forever-mini-flags' && flags0.env === 'beta'
      && flags0.features.professions.on === false && flags0.features.bis.on === true
      && (flags0.policy || []).length >= 3, JSON.stringify(flags0.counts));

  await clearStore();
  await nav('/pages/professions/index');
  const off = await call('读关着的页', () => mp.evaluate(() => {
    const p = getCurrentPages().pop(); const d = p.data || {};
    return { route: p.route, locked: !!d.locked, lockName: d.lockName || '', loaded: !!d.loaded,
      chips: (d.chips || []).length, hasSel: !!d.sel, meta: !!d.meta, sourceText: d.sourceText || '' };
  }), 3);
  log('开关关着时直接进这一页：只说"还没开放"，一个数据请求都不发（没取到数据＝真的没去取）',
    !!off && off.route === 'pages/professions/index' && off.locked === true && off.loaded === false
      && off.chips === 0 && off.hasSel === false && off.meta === false,
    JSON.stringify(off));
  log('关着的页念得出这一页叫什么（不是"出错了"那种含糊话）',
    !!off && off.lockName === '专业与配方', JSON.stringify(off && off.lockName));
  await nav('/pages/home/index');
  const homeOff = await call('读首页（关）', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data || {};
    return { open: !!d.openProfessions, art: (d.cardBg || {}).professions === undefined ? null : !!d.cardBg.professions };
  }), 3);
  log('首页此时没有「专业与配方」入口卡（关着整块不渲染，不留空白格）',
    !!homeOff && homeOff.open === false, JSON.stringify(homeOff));

  /* 只动"线上"那一份开关（项目外那个文件）：等价于跑一次 flags --env beta */
  const flipped = JSON.parse(fs.readFileSync(FLAGS_FILE, 'utf8'));
  flipped.features.professions.on = true;
  fs.writeFileSync(FLAGS_FILE, JSON.stringify(flipped, null, 1) + '\n');
  process.stdout.write('    → 把本地那份 flags.json 的 professions 拧成 true（模拟线上改开关，代码一行没动）\n');
  await nav('/pages/home/index');
  const homeOn = await call('读首页（开）', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data || {};
    return { open: !!d.openProfessions };
  }), 3);
  const codeAfter = CODE_FILES.map((f) => f + '=' + sha01(path.join(REPO, 'for-mini', f))).join(' ');
  log('拧开之后首页入口卡自己出现了，而且代码一个字节都没变（这就是"不用发版"）',
    !!homeOn && homeOn.open === true && codeBefore === codeAfter,
    codeBefore === codeAfter ? '代码哈希一致' : '代码哈希变了：' + codeBefore + ' vs ' + codeAfter);

  /* ---------- J. 专业与配方页（对齐网页 ProfessionsPage.vue） ---------- */
  process.stdout.write('\nJ. 专业页：13 个专业能切、三个筛选项真生效、分箱与材料条在\n');
  await nav('/pages/professions/index');
  const pf = await call('读专业页', () => mp.evaluate(() => new Promise((res) => {
    setTimeout(() => {
      const p = getCurrentPages().pop(); const d = p.data || {};
      res({ route: p.route, locked: !!d.locked, chips: (d.chips || []).length, selId: d.selId || '',
        selName: (d.sel || {}).nameCn || '', stats: d.stats || {}, total: d.totalRecipes,
        shown: d.shown, rest: d.rest, bands: (d.bands || []).map((b) => b.label + ':' + b.count + '/' + b.rows.length).join(' '),
        nodeHead: d.nodeHead, nodes: (d.nodeRows || []).length, sourceText: d.sourceText || '',
        bandNote: d.bandNote || '', headUrl: d.headUrl || '',
        row0: ((d.bands || [])[0] || {}).rows ? ((((d.bands || [])[0] || {}).rows || [])[0] || {}) : {},
        text: []
          .concat(...((d.bands || []).map((b) => b.rows || [])), d.nodeRows || [])
          .map((x) => [x.name, (x.mats || []).map((m) => m.name + m.count).join(' '), (x.srcLines || []).join(' ')]
            .concat(x.yields ? [x.yields] : []).join(' ')).join(' | ') });
    }, 1200);
  })), 3);
  log('开关开了就直接进得来：13 个专业、页头读数与板块图都在',
    !!pf && pf.route === 'pages/professions/index' && pf.locked === false && pf.chips === 13
      && pf.stats.professions === 13 && pf.stats.recipes > 1900 && /^http/.test(pf.headUrl),
    JSON.stringify(pf && { chips: pf.chips, stats: pf.stats }));
  log('取数状态说真话（线上取到了就不许写"没取到数据"）',
    !!pf && /实时|缓存/.test(String(pf.sourceText)), JSON.stringify(pf && pf.sourceText));
  log('默认这个专业有配方、按橙点分了箱，且一屏只画 60 行（其余点按钮往下走）',
    !!pf && pf.total > 60 && pf.shown === 60 && pf.rest === pf.total - 60
      && /学徒 · 1–75/.test(pf.bands) && /大师 · 226–300/.test(pf.bands),
    JSON.stringify(pf && { total: pf.total, shown: pf.shown, bands: pf.bands }));
  log('分箱那句解释随数据下发（页面不自己写一份），并交代了兜底那一箱',
    !!pf && /橙色起点/.test(pf.bandNote) && /不静默吞条目/.test(pf.bandNote), String(pf && pf.bandNote).slice(0, 60));
  const pf0 = (pf && pf.row0) || {};
  log('一行配方给全：名字、品质色档、材料带数量、技能四档、来源',
    !!pf0.name && typeof pf0.q === 'number' && (pf0.skList || []).length >= 1
      && (pf0.mats || []).length >= 1 && pf0.matPct >= 6 && pf0.matPct <= 100,
    JSON.stringify({ name: pf0.name, q: pf0.q, mats: (pf0.mats || []).length, sk: (pf0.skList || []).length, pct: pf0.matPct }));
  const pfMore = await call('再显示 60 条', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.loadMore();
    setTimeout(() => { const d = p.data || {}; res({ shown: d.shown, rest: d.rest, total: d.totalRecipes }); }, 500);
  })), 3);
  log('「再显示 60 条」真的往下放（不是个摆设按钮）',
    !!pfMore && pfMore.shown === 120 && pfMore.rest === pfMore.total - 120, JSON.stringify(pfMore));
  const pfLv = await call('填我的技能等级', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    const before = p.data.totalRecipes;
    p.onLevel({ detail: { value: '10' } });
    setTimeout(() => res({ before, after: p.data.totalRecipes, lv: p.data.lv }), 500);
  })), 3);
  log('「我的技能 1–300」真在筛（按橙点档收，结果数跟着变小）',
    !!pfLv && pfLv.lv === '10' && pfLv.after < pfLv.before, JSON.stringify(pfLv));
  const pfQ = await call('搜一个材料名', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onLevel({ detail: { value: '' } });
    p.onSearch({ detail: { value: '宁神花' } });
    setTimeout(() => {
      const d = p.data || {};
      res({ total: d.totalRecipes, hit: (d.bands || []).every((b) => (b.rows || []).every((r) =>
        /宁神花/.test(r.name + ' ' + (r.mats || []).map((m) => m.name).join(' ')))) });
    }, 500);
  })), 3);
  log('搜索框同时命中制成品名与材料名（不是只搜标题）',
    !!pfQ && pfQ.total > 0 && pfQ.total < pfMore.total && pfQ.hit === true, JSON.stringify(pfQ));
  const pfMat = await call('只搜材料名', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onSearch({ detail: { value: '空瓶' } });
    setTimeout(() => {
      const d = p.data || {};
      const rows = []
      ;(d.bands || []).forEach((b) => (b.rows || []).forEach((r) => rows.push(r)))
      res({ total: d.totalRecipes,
        noneNamed: rows.filter((r) => /空瓶/.test(r.name)).length,
        allHave: rows.every((r) => (r.mats || []).some((m) => /空瓶/.test(m.name))) });
    }, 500);
  })), 3);
  log('搜"空瓶"命中的全是材料里有它的配方（这些配方名字里没这个词）',
    !!pfMat && pfMat.total > 0 && pfMat.noneNamed === 0 && pfMat.allHave === true, JSON.stringify(pfMat));
  const pfNone = await call('搜一个不存在的词', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onSearch({ detail: { value: '这个词一定搜不到zzz' } });
    setTimeout(() => { const d = p.data || {}; res({ total: d.totalRecipes, nodes: (d.nodeRows || []).length }); }, 500);
  })), 3);
  const pfWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/professions/index.wxml'), 'utf8');
  log('筛到 0 条时走空态那一卡（条件就是"配方 0 且采集点 0 且不是拆不出条目那一档"）',
    !!pfNone && pfNone.total === 0
      && /没有匹配条目[\s\S]{0,40}!totalRecipes && !nodeRows.length && !sel.unparsed/.test(
        pfWxml.replace(/\s+/g, ' ').replace('<view class="card" wx:if="{{', '{{'))
      || /没有匹配条目/.test(pfWxml) && /!totalRecipes && !nodeRows.length && !sel.unparsed/.test(pfWxml),
    JSON.stringify(pfNone));
  const pfNew = await call('只看无限新增', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.onSearch({ detail: { value: '' } });
    setTimeout(() => {
      const all = p.data.totalRecipes;
      p.toggleNew();
      setTimeout(() => {
        const d = p.data || {};
        res({ all, after: d.totalRecipes, on: !!d.onlyNew,
          allNew: (d.bands || []).every((b) => b.rows.every((r) => r.isNew)) });
      }, 500);
    }, 400);
  })), 3);
  log('「只看无限新增」真在筛，且筛出来的每一条都带"新"角标',
    !!pfNew && pfNew.on === true && pfNew.after > 0 && pfNew.after < pfNew.all && pfNew.allNew === true,
    JSON.stringify(pfNew));
  const pfGather = await call('切到草药学', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    if (p.data.onlyNew) p.toggleNew();
    p.pickProf({ currentTarget: { dataset: { id: 'herbalism' } } });
    setTimeout(() => {
      const d = p.data || {};
      res({ selId: d.selId, selName: (d.sel || {}).nameCn, nodeHead: d.nodeHead, nodes: (d.nodeRows || []).length,
        total: d.totalRecipes, first: ((d.nodeRows || [])[0] || {}).name || '', yields: ((d.nodeRows || [])[0] || {}).yields || '' });
    }, 1500);
  })), 3);
  log('采集类专业：表头叫「草药点」、列的是采集点，配方 0 条也不硬凑',
    !!pfGather && pfGather.selId === 'herbalism' && pfGather.nodeHead === '草药点'
      && pfGather.nodes === 30 && pfGather.total === 0 && pfGather.first.length > 1,
    JSON.stringify(pfGather && { head: pfGather.nodeHead, nodes: pfGather.nodes, first: pfGather.first }));
  /* 草药点那 30 行"可得的就只有它自己"，那一行现在不显示（2026-10-27 实拍里每行都在重复名字）。
     判据反过来：采完就重复的那格必须是空，切到采矿（一种矿出好几种料）才该有这一行。 */
  log('「可得」只在与采集点同名时省掉，采矿那种一矿多料照旧列全',
    !!pfGather && pfGather.yields === '',
    JSON.stringify(pfGather && { yields: pfGather.yields }));
  const pfMine = await call('切到采矿看可得列', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.pickProf({ currentTarget: { dataset: { id: 'mining' } } });
    setTimeout(() => {
      const d = p.data || {};
      const first = (d.nodeRows || [])[0] || {};
      res({ nodes: (d.nodeRows || []).length, total: d.totalRecipes, first: first.name, yields: first.yields });
    }, 1500);
  })), 3);
  log('采矿：13 个矿点 + 15 条配方都在，"可得"列出一矿多料',
    !!pfMine && pfMine.nodes === 13 && pfMine.total === 15 && /、/.test(pfMine.yields || ''),
    JSON.stringify(pfMine));
  const pfCamp = await call('切到野营（拆不出条目那一档）', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.pickProf({ currentTarget: { dataset: { id: 'camping' } } });
    setTimeout(() => {
      const d = p.data || {};
      res({ selId: d.selId, unparsed: !!(d.sel || {}).unparsed, note: (d.sel || {}).note || '',
        total: d.totalRecipes, nodes: (d.nodeRows || []).length });
    }, 1500);
  })), 3);
  log('野营那一档照实说"还没拆出条目"，那句话取自数据里的 note（不在代码里另编）',
    !!pfCamp && pfCamp.unparsed === true && /没.*拆|还没/.test(pfCamp.note) && pfCamp.total === 0,
    JSON.stringify(pfCamp));
  const pfAlch = await call('切回炼金看来源行', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    p.pickProf({ currentTarget: { dataset: { id: 'alchemy' } } });
    setTimeout(() => {
      const d = p.data || {};
      const rows = []
      ;(d.bands || []).forEach((b) => (b.rows || []).forEach((r) => rows.push(r)))
      res({ selId: d.selId, total: d.totalRecipes, shown: d.shown,
        srcs: rows.map((r) => (r.srcLines || []).join(' ')).filter(Boolean),
        text: rows.map((r) => [r.name, (r.mats || []).map((m) => m.name).join(' '),
          (r.srcLines || []).join(' ')].join(' ')).join(' | ') });
    }, 1500);
  })), 3);
  log('来源那一格还原成中文（训练师 / 商人：名字（区域） / 图纸掉落：…），掉率一个字都不写',
    !!pfAlch && pfAlch.srcs.length > 0
      && pfAlch.srcs.join(' ').indexOf('训练师') >= 0, JSON.stringify((pfAlch && pfAlch.srcs.slice(0, 2)) || []));
  log('专业页渲染出来的文字里没有百分比与强度评价词（红线）',
    !!pfAlch && !/\d+(\.\d+)?\s*%/.test(pfAlch.text) && !/秒伤|DPS|权重|更好|优于|性价比/.test(pfAlch.text),
    String(pfAlch && pfAlch.text).slice(0, 80));
  await shot('p1-professions');
  await nav('/pages/home/index');
  await shot('p2-home-with-professions-entry');
  /* mp.screenshot 的返回值不是路径（别拿它当证据），要看文件真落盘了没有 */
  const pfShots = ['p1-professions.png', 'p2-home-with-professions-entry.png']
    .filter((f) => fs.existsSync(path.join(SHOT_DIR, f)));
  log('两张实拍落盘（专业页 + 首页带入口）', pfShots.length === 2, JSON.stringify(pfShots));

  /* 收尾：把本地那份开关恢复成"关着"——站主 2026-10-27 的口径是先不公开，
     测试借道拧开一次，跑完必须还原，否则下一次回归看到的线上状态就是被测试改过的 */
  fs.writeFileSync(FLAGS_FILE, JSON.stringify(flags0, null, 1) + '\n');
  log('测后把 flags.json 还原成基线（professions 关着），代码文件哈希与测前一致',
    JSON.parse(fs.readFileSync(FLAGS_FILE, 'utf8')).features.professions.on === false
      && CODE_FILES.map((f) => f + '=' + sha01(path.join(REPO, 'for-mini', f))).join(' ') === codeBefore, '');
  /* 静态：颜色只在 app.wxss 定义，页面 wxss 里不许有裸色值 */
  const MINI = '/Users/zhangyajun/Documents/project/wow-forever/for-mini/';
  const rawColor = [];
  ['pages/home/index.wxss', 'pages/dungeons/index.wxss', 'pages/dungeon/index.wxss', 'pages/glossary/index.wxss',
    'pages/classes/index.wxss', 'pages/class/index.wxss', 'pages/guide/index.wxss',
    /* 新页一律进这份名单：以前只列了老页，配装页那种"页面自己写裸色值"就漏过去了 */
    'pages/bis/index.wxss', 'pages/professions/index.wxss', 'pages/item/index.wxss',
    'pages/spells/index.wxss', 'pages/loots/index.wxss'].forEach((f) => {
    const t = fs.readFileSync(MINI + f, 'utf8');
    (t.match(/#[0-9a-fA-F]{3,8}\b|rgba?\(/g) || []).forEach((c) => rawColor.push(f + ' ' + c));
  });
  log('全部页面级 wxss 里没有裸色值（颜色只在 app.wxss）', rawColor.length === 0, rawColor.slice(0, 4).join(' | '));
  const appjson = JSON.parse(fs.readFileSync(MINI + 'app.json', 'utf8'));
  /* 2026-10-22 站主重排：tab 三格给 首页/副本/职业；中英速查降成首页卡（navigateTo） */
  log('tabBar 三个一级入口：首页 / 副本 / 职业',
    appjson.tabBar.list.length === 3 && appjson.tabBar.list.map((x) => x.pagePath).join(',') === 'pages/home/index,pages/dungeons/index,pages/classes/index',
    JSON.stringify(appjson.tabBar.list.map((x) => x.pagePath)));
  const pcfg = JSON.parse(fs.readFileSync(MINI + 'project.config.json', 'utf8'));
  log('appid 已换成正式号（不再是 touristappid）', pcfg.appid === 'wxfd9a2b985a6cedc3', pcfg.appid);
  const ignored = (pcfg.packOptions && pcfg.packOptions.ignore || []).map((x) => x.value);
  log('内部文档与产物不进代码包（AGENTS.md / README.md / docs / oss-preview / oss-build / .oss-env 全排除）',
    ['AGENTS.md', 'README.md', 'docs', 'oss-preview', 'oss-build', '.oss-env'].every((v) => ignored.indexOf(v) >= 0),
    JSON.stringify(ignored));
  /* 代码包体积：按 packOptions 规则自算（本机 CLI 没有 code-analyze 命令，
     面板上的实测数要你在开发者工具「详情 → 基本信息」里看一眼核对） */
  /* 名单从 packOptions.ignore 现推，不再自己抄第二份：
     加一条排除（2026-10-30 的 tmp-model 那种 1.4 MB 探针样本）只要改工程配置，
     这里跟着变小；自己抄一份就会"配置排了、体积还算着"，或者反过来假红。 */
  const skipDirs = { node_modules: 1, dist: 1, miniprogram_npm: 1 };
  const skipFiles = {};
  (pcfg.packOptions && pcfg.packOptions.ignore || []).forEach((x) => {
    if (x.type === 'folder') skipDirs[x.value] = 1
    else skipFiles[x.value] = 1
  });
  ['project.config.json', 'project.private.config.json', '.gitignore'].forEach((v) => { skipFiles[v] = 1; });
  let pkgBytes = 0;
  (function walk(dir) {
    fs.readdirSync(dir, { withFileTypes: true }).forEach((e) => {
      if (e.name.startsWith('.')) return;
      const p = path.join(dir, e.name);
      if (e.isDirectory()) { if (!skipDirs[e.name]) walk(p); return; }
      if (!skipFiles[e.name]) pkgBytes += fs.statSync(p).size;
    });
  })(MINI);
  process.stdout.write('  · 自算代码包 ' + (pkgBytes / 1024).toFixed(1) + ' KB（主包上限 2 MB）\n');
  log('代码包体积在预算内（< 512 KB）', pkgBytes < 512 * 1024, (pkgBytes / 1024).toFixed(1) + ' KB');

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
