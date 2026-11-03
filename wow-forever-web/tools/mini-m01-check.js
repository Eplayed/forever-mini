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

/* 仓库根从脚本自己的位置推，不写死绝对路径：写死过一次（/Users/zhangyajun/...），
   结果这条回归在 Windows 上直接 ENOENT 打不开（2026-11-01 撞见）。 */
const REPO = path.resolve(__dirname, '..', '..');
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
   2026-10-30 那条"进页一个模型请求都不许发"已被站主 2026-11-01 的"直接展示 3D"取代；
   2026-11-02 3D 整层撤掉、换成逐件 PNG 后，这里数的是"切一套/切一阵营最多取那一张图"
   ——仍只能这么证：在页面里自己数等于让被试对象自己报数。 */
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
  const p = cp.spawn('node', [SERVER], { env: Object.assign({}, process.env, { FAKE_OSS_MODE: mode, FAKE_OSS_PORT: String(PORT), FAKE_OSS_NOCACHE: '1', FAKE_OSS_FLAGS_FILE: LIVE_FLAGS, FAKE_OSS_LOG: OSS_HITS,
    /* 底图不在素材根（app/img）里，得单独指过去，否则模拟器这一格永远 404 退回原画，
       截图就看不出底图长什么样 */
    FAKE_OSS_POSTERS_DIR: path.join(BUILD, 'posters') }) });
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
     界面不许摆一个写"没有这张头像"的虚线空框——那看着像坏了；交给 icon-cell 回落自绘块。
     首领**个数从数据里读**，不写死：这座本跟着 11-01 那批客户端数据涨到 5 个，
     上一版这里钉的是"恰好 4 个"，数据一对、断言自己变红了（2026-11-02 撞到）。 */
  const htData = (() => {
    const pv = JSON.parse(fs.readFileSync(path.join(REPO, 'for-mini/oss-preview/dungeons.json'), 'utf8'));
    const all = ['newDungeons', 'classicDungeons', 'raids'].reduce((a, k) => a.concat(pv[k] || []), []);
    return all.filter((x) => x.id === 'hall-of-thanes')[0] || {};
  })();
  log('详情页：新本首领没有头像时走自绘回落，页面不再摆"没有这张头像"那句',
    (s.bosses || []).length === (htData.bosses || []).length && (s.bosses || []).every((b) => b.portraitUrl === ''),
    JSON.stringify({ want: (htData.bosses || []).length, got: (s.bosses || []).map((b) => b.portraitUrl) }));
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
    return { go: ['goDungeons', 'goClasses', 'goLoots', 'goMacros'].filter((f) => typeof p[f] === 'function').length,
      glossary: typeof p.goGlossary, counts: p.data.counts, cov: p.data.covList, wip: p.data.wip, fact: p.data.factDate, build: p.data.buildId };
  }), 3);
  /* 2026-10-22 站主重排：入口卡固定四张 副本/职业/掉落查询/指南；
     2026-11-02 站主把第四张换成宏命令（指南页还在 app.json 里，但首页不再给入口） */
  log('首页四个入口卡处理器都在（副本/职业/掉落查询/宏命令）', homeCards && homeCards.go === 4, JSON.stringify(homeCards));
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
      verdict: /两家一致|两家分歧|另一家没列/.test(txt.join(' ')),      text: txt.join(' ')
    };
  }), 3);
  log('配装页打得开：9 个职业、这一套 16 个部位以上、属性合计有数',
    bis && bis.route === 'pages/bis/index' && bis.classes === 9 && bis.rows >= 16 && bis.sum >= 1,
    JSON.stringify(bis && { cls: bis.cls, classes: bis.classes, rows: bis.rows, sum: bis.sum }));
  /* 2026-11-01 站主指令：页头那三句（口径句 / 来源与核对日 / L1 留档）从界面上撤下。
     撤的是出口，不是事实——数据层 meta 里这三条必须还在，否则这一页就成了"没有出处的名单"。
     所以两条一起判：渲染文字里不许再出现那三句，而 data 里三条一条不能少。 */
  log('页头三句已从界面撤下（站主 2026-11-01），但数据层一条没删',
    !!bis && !/不是官方结论|对着来源核过|按 L1 留档/.test(String(bis.text))
      && /不是官方结论/.test(bis.disclaimer) && /^\d{4}-\d{2}-\d{2}$/.test(bis.fetched)
      && /wclbox/.test(bis.host),
    JSON.stringify(bis && { f: bis.fetched, h: bis.host, 界面还有口径句: /不是官方结论/.test(String(bis.text)) }));
  /* 取数状态要说真话：sourceLabel 收的是整个结果对象而不是 source 字符串，
     传错参数不会报错，只会永远显示"没取到数据"——2026-10-27 发完 beta 走真页才发现这条。 */
  log('配装页的取数状态说真话（线上取到了就不许写"没取到数据"）',
    !!bis && /实时|缓存/.test(String(bis.sourceText)), JSON.stringify({ src: bis && bis.sourceText }));
  log('装备名回本站物品库查出来了（不是 #编号），来源那一列也还原成了中文',
    !!bis && bis.head.length > 1 && !/^#/.test(bis.head) && /副本|技能|需要|制造|商人|任务/.test(bis.srcSample),
    JSON.stringify(bis && { head: bis.head, src: bis.srcSample.slice(0, 40) }));
  log('这一页没有打包快照：取数走线上，取不到时页面自己说"还没有/要联网"，不半截显示',
    !!bis && (!bis.unavailable || !bis.rows), JSON.stringify(bis && { un: bis.unavailable, on: bis.needOnline }));
  /* 站主 2026-11-02：「两家一致／两家分歧／另一家没列」这几句判词从界面上全部撤掉。
     撤的是标签，不是事实——分发层那一份逐格比较（bis/set/*.json 的 alt[].state）一条没删，
     备选那一件照旧列出来，只是不再替玩家下"一致/分歧"这个结论。 */
  log('判词「两家一致／分歧／没列」已从整页界面撤干净（渲染文字里一条都不许出现）',
    !!bis && bis.verdict === false, String(bis && bis.verdict));
  const cmpCss = fs.readFileSync(path.join(REPO, 'for-mini/pages/bis/index.wxss'), 'utf8');
  const cmpWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/bis/index.wxml'), 'utf8');
  /* 分色这条要钉在令牌上，不钉截图：属性类走 --txt-dim、来源类走 --azure，
     而且来源不许再被"可点"那档抢走颜色（原来 .s-link 整行金色，蓝灰两档反而分不出来）。 */
  /* 分色这一档要钉住三件事：属性档与来源档确实不同、来源档不再被"可点"抢色，
     以及**来源档离六个品质色都要远**——上一版选了 --azure，量出它与稀有装备名 q3 #4aa3ff 只差 34，
     真机上"来源"那行被读成"又一个装备名"（站主原话"区分不明显"）。这条把那个教训变成算得出来的断言。 */
  log('装备属性与副本来源分两档（属性 --txt-muted / 来源 --gold + 一条左竖线），可点的那行不再整行改色',
    /\.s-meta \{[^}]*--txt-muted/.test(cmpCss) && /\.s-src \{[^}]*var\(--gold\)/.test(cmpCss)
      && /\.s-src \{[^}]*border-left/.test(cmpCss) && /\.p-st \{[^}]*--txt-muted/.test(cmpCss)
      && !/\.s-src \{[^}]*--azure/.test(cmpCss) && !/\.s-link \{[^}]*color:/.test(cmpCss)
      && !/class="cmp/.test(cmpWxml) && !/\.cmp\b/.test(cmpCss), '');
  const tokensCss = fs.readFileSync(path.join(REPO, 'for-mini/app.wxss'), 'utf8');
  const tok = (n) => {
    const m = new RegExp('--' + n + ':\\s*#([0-9a-f]{6})', 'i').exec(tokensCss);
    return m ? [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16)] : null;
  };
  const dist = (a, b) => (!a || !b) ? -1 : Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]);
  const srcC = tok('gold');
  const minQ = Math.min.apply(null, ['q0', 'q1', 'q2', 'q3', 'q4', 'q5'].map((k) => dist(srcC, tok(k))));
  log('来源档与六个品质色都拉开了（最小距离 ≥ 100 才算不撞名）',
    minQ >= 100, 'gold 与品质色的最小距离 = ' + minQ + '（azure 当年是 34）');
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
      theirs: d.slotTheirs || {}, st: ((d.slotRows || [])[0] || {}).st || [],
      cn: (d.slotTheirs || {}).cn, popText: String(d.slotHead) + ' ' + JSON.stringify(d.slotTheirs || {}) };
  }), 3);
  log('点一个部位弹出这个部位的备选（含属性行与另一份名单那一件）',
    !!bisPop && bisPop.n >= 1 && /头部/.test(bisPop.head) && (bisPop.st || []).length > 0
      && typeof bisPop.theirs.shown === 'boolean', JSON.stringify(bisPop));
  /* 弹层里也不许再出现那三个判词；那句前缀要说清"这是另一份名单列的"，
     不然玩家会以为它是本站推荐的第二件 */
  log('弹层里同样没有判词，且第二件那行说清了是谁列的',
    !!bisPop && !bisPop.cn && !/两家一致|两家分歧|另一家没列/.test(String(bisPop.popText)),
    JSON.stringify(bisPop && { cn: bisPop.cn, t: String(bisPop.popText).slice(0, 70) }));
  /* 2026-10-30 站主把「看占位模型」这颗按钮撤了（真实模型已经能在真机出画面），
     占位人台那一格连同 DOLL_LAYOUT / nodes / unmapped 一起从页面里删掉了。
     这里钉的是"删干净了、没留半截入口"，不再钉占位人台本身。 */
  const doll0 = await call('确认占位那一格已撤', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { live: d.live3d, nodes: d.nodes, toggle: typeof getCurrentPages().pop().toggle3d };
  }), 2);
  log('「看占位模型」入口与占位数据已从页面撤干净（不留点不到的按钮）',
    !!doll0 && doll0.live === undefined && doll0.nodes === undefined && doll0.toggle === 'undefined',
    JSON.stringify(doll0));

  /* ---------- 逐件底图（2026-11-02 站主："BIS 配装页装备展示全部替换成样图这样的，背景透明，根据职业装备来"）----------
     3D 那一层的组件、取数契约（services/bis-model.js）与相机链路整层删了，这一栏只剩一张
     按 <setId>|<阵营> 从分发层桥表指过来的透明底 PNG。这一格钉的是"指没指对、切了换没换、
     取不到有没有明说"；图上那个人穿得对不对，由构建时那五道闸与站主的眼睛负责，不由这里冒充。 */
  const ps = await call('看中间那一栏的字段', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { hasModelSrc: ('modelSrc' in d), hasAspect: ('stageAspect' in d),
      cls: d.cls, fac: d.fac, setId: d.setId, rows: (d.rows || []).length,
      src: d.posterSrc, state: d.posterState, text: d.posterText };
  }), 2);
  log('3D 那一层整层撤干净：data 里不再有 modelSrc/stageAspect，这一格只可能挂逐件图',
    !!ps && ps.hasModelSrc === false && ps.hasAspect === false && ps.rows >= 10, JSON.stringify(ps));
  const posterRe = (id, fac) => new RegExp('/assets/models/posters/' + id + '-' + fac + '-[0-9a-f]{12}\\.png$');
  log('进页就把当前 setId+阵营 那一张指上了（桥表里有就必须有，不等玩家点）',
    !!ps && ps.state === 'loading' && posterRe(ps.setId, ps.fac).test(String(ps.src)), JSON.stringify(ps));
  /* 桥表本身从页面内存里取：这一份是真从假 OSS 的指针批下来的一份，不是本地文件抄的 */
  const pl = await call('取索引里的底图桥表', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const link = (p.index || {}).posterLink || {};
    return { link: link, sets: ((p.index || {}).sets || []).map((s) => s.id) };
  }), 2);
  const rels = Object.keys((pl || {}).link || {});
  log('桥表每条都指向 models/posters/ 下带内容哈希的那一张，且那张真在发布目录里',
    rels.length > 0 && rels.every((k) => {
      const rel = String(pl.link[k]);
      if (!/^models\/posters\/[a-z0-9-]+-[0-9a-f]{12}\.png$/.test(rel)) return false;
      return fs.existsSync(path.join(BUILD, 'posters', rel.replace('models/posters/', '')));
    }), rels.length + ' 条');
  const noPoster = ((pl || {}).sets || []).reduce((acc, id) => {
    if (!pl.link[id + '|alliance']) acc.push(id + '|联盟');
    if (!pl.link[id + '|horde']) acc.push(id + '|部落');
    return acc;
  }, []);
  log('每一套的两个阵营都在桥表里（38 套 × 2 就该有 76 条；缺一条就是那一格只能显示"没有图"）',
    rels.length === ((pl || {}).sets || []).length * 2 && !noPoster.length,
    rels.length + '/' + (((pl || {}).sets || []).length * 2) + (noPoster.length ? ' 缺：' + noPoster.slice(0, 4).join('、') : ''));
  /* 数请求要从零起：进页已经取过当前那一张，这里只数"换一次阵营多花几个请求"。
     换阵营取的是另一件登记——旧的那一张必须立刻作废，画面上不许留着上一阵营那身。 */
  hitsClear();
  const ps2 = await call('换阵营', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const before = { fac: p.data.fac, src: p.data.posterSrc };
    p.pickFac({ currentTarget: { dataset: { fac: p.data.fac === 'horde' ? 'alliance' : 'horde' } } });
    return { before: before, after: { fac: p.data.fac, src: p.data.posterSrc, state: p.data.posterState } };
  }), 2);
  await new Promise((r) => setTimeout(r, 1200));
  log('换阵营后阵营真的翻了、指到的是另一阵营那一张（旧图不许继续挂着）',
    !!ps2 && ps2.before.fac !== ps2.after.fac && ps2.before.src !== ps2.after.src
      && new RegExp('-' + ps2.after.fac + '-[0-9a-f]{12}\\.png$').test(String(ps2.after.src)),
    JSON.stringify(ps2));
  const picHits = hitsOf(/assets\/models\/posters\//);
  const idxHits = hitsOf(/bis\/models\/index\.json/);
  log('切一次阵营只多取那一张图，不再取模型清单（3D 的清单链路已经整层删掉）',
    picHits.length <= 1 && idxHits.length === 0,
    '图 ' + picHits.length + ' 次 · 清单 ' + idxHits.length + ' 次');
  /* 换一套（不是换阵营）也要真的换图：这是站主那句"切换职业、切换别的装备能展示就好了"的正身 */
  const ps3 = await call('换到同一职业的另一套', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const other = (p.data.setList || []).filter((x) => x.id !== p.data.setId)[0];
    if (!other) return { skipped: true, n: (p.data.setList || []).length };
    const before = p.data.posterSrc;
    p.pickSet({ currentTarget: { dataset: { id: other.id } } });
    return { skipped: false, want: other.id, before: before, setIdNow: p.data.setId };
  }), 2);
  await new Promise((r) => setTimeout(r, 1800));
  const ps4 = await call('换完再看一眼那一格', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { setId: d.setId, fac: d.fac, src: d.posterSrc, state: d.posterState, rows: (d.rows || []).length };
  }), 2);
  log('换一套真的换成那一套那一张（不是把上一套的图留在屏上）',
    !ps3.skipped && !!ps4 && ps4.setId === ps3.want && ps4.src !== ps3.before
      && posterRe(ps4.setId, ps4.fac).test(String(ps4.src)) && ps4.rows >= 10,
    JSON.stringify({ ps3: ps3, ps4: ps4 }));
  /* 没有图那一档：桥表里没有这一格时必须直说，且名单/属性合计一条不少。
     这里演的是"分发层没登记"（键不在表里），不是"网络坏了"——界面上是两句分开的说。 */
  const m3 = await call('演一次桥表里没有这一格', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const keep = p.index.posterLink;
    p.index.posterLink = {};
    p.showPoster();
    const d = p.data;
    p.index.posterLink = keep;
    return { src: d.posterSrc, state: d.posterState, err: d.posterErr, text: d.posterText,
      hasModelSrc: ('modelSrc' in d), rows: (d.rows || []).length, sum: (d.sum || []).length };
  }), 2);
  log('桥表里没有这一格就直说「这一格没有可显示的图」＋原因，不拿任何别的图顶；名单与合计一条不少',
    !!m3 && m3.state === 'none' && !m3.src && /没有可显示的图/.test(String(m3.text))
      && /没给这一套/.test(String(m3.err)) && m3.hasModelSrc === false
      && m3.rows >= 10 && m3.sum >= 1, JSON.stringify(m3));
  await call('把这一张指回来', () => mp.evaluate(() => { getCurrentPages().pop().showPoster(); return 1; }), 1);
  /* 图是异步的：切走之后旧那张的 load 回调才回来，也不许改当前这一格的状态 */
  const m4 = await call('演一次迟到的 load 回调', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const cur = p.data.posterSrc;
    p._posterKey = '别的套|horde';
    p.onPosterLoad();
    const stale = { state: p.data.posterState, src: p.data.posterSrc };
    p._posterKey = p.data.setId + '|' + p.data.fac;
    p.onPosterLoad();
    const fresh = { state: p.data.posterState, src: p.data.posterSrc };
    return { cur: cur, stale: stale, fresh: fresh };
  }), 2);
  log('迟到的那一张不改当前状态，键对上了才说"已经取到"（画面与 setId+阵营 必须同人同套）',
    !!m4 && !!m4.cur && m4.stale.state === 'loading' && m4.stale.src === m4.cur
      && m4.fresh.state === 'ok' && m4.fresh.src === m4.cur, JSON.stringify(m4));
  /* 真取不到（断网、没发过、对象不在这个批）也要说清：图没了，名单与合计还在 */
  const m5 = await call('演一次取不到（binderror 分支）', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.onPosterError();
    const d = p.data;
    return { src: d.posterSrc, state: d.posterState, text: d.posterText, err: d.posterErr,
      rows: (d.rows || []).length, sum: (d.sum || []).length };
  }), 2);
  log('那一张取不到就明说取不到（不许留着空 src 假装还在加载），名单与合计照旧完整',
    !!m5 && m5.state === 'bad' && !m5.src && m5.text === '这一格没有可显示的图'
      && /取不到/.test(String(m5.err)) && m5.rows >= 10 && m5.sum >= 1, JSON.stringify(m5));
  const bis3dWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/bis/index.wxml'), 'utf8');
  /* 站主 2026-11-02 第二轮："这里文案去掉，只保留属性"——图那一格的说明句、属性合计那句注解、
     附魔与消耗品那句"本站没有第二处可以核对"全撤。撤的是界面出口：数据层 sumNote 与分发层
     disclaimer 一条没删（和 11-01 撤页头三句同一个口径）。这条从"必须有那句"翻成"那句不许回来"。 */
  log('图与属性合计那几句说明已从界面撤干净（站主 11-02），且不留半截出口',
    !/静态图，不能拖动/.test(bis3dWxml) && !/\{\{sumNote\}\}/.test(bis3dWxml)
      && !/本站没有第二处可以核对/.test(bis3dWxml) && !/本站不排强弱/.test(bis3dWxml)
      && /class="sum-v"/.test(bis3dWxml), '');
  await call('指回当前这一张（给下面那张截图用）', () => mp.evaluate(() => {
    getCurrentPages().pop().showPoster(); return 1;
  }), 1);
  await new Promise((r) => setTimeout(r, 900));
  const appJson = JSON.parse(fs.readFileSync(path.join(REPO, 'for-mini/app.json'), 'utf8'));
  const packCfg = JSON.parse(fs.readFileSync(path.join(REPO, 'for-mini/project.config.json'), 'utf8'));
  log('临时探针路由已从正式 app.json 撤掉，探针目录也不进包（正式包里没有 model-probe）',
    appJson.pages.indexOf('pages/model-probe/index') < 0
      && (packCfg.packOptions.ignore || []).some((x) => x.value === 'pages/model-probe')
      && !(packCfg.packOptions.ignore || []).some((x) => /models/.test(String(x.value))),
    JSON.stringify(appJson.pages.length));
  await shot('h1-bis-page');
  /* 站主 2026-11-02 要的是"属性与副本分色"，那是视觉主张——只钉 CSS 不够，得有一张看得见的那一屏。
     滚到「这一套一览」拍一张，再把弹层开着拍一张（弹层里属性行与来源行同屏，最容易比）。 */
  await call('滚到「这一套一览」', () => mp.evaluate(() => new Promise((r) => {
    /* 锚要选 .srow（第一行装备）：.bhead 在这一页出现两次（页头那一格也叫它），
       上一版按 .bhead 滚，拍到的还是上面那一屏（2026-11-02 实拍发现的）。
       也别用 wx.getPageScrollTop + boundingClientRect 自己算：这台的基础库里那条走的是 fail 分支，
       结果一格都没滚（15:22 那张又成了顶部）。选择器写法是官方支持的，直接用它，并把结果带出来。 */
    wx.pageScrollTo({ selector: '.srow', offsetTop: -60,
      success: () => r('ok'), fail: (e) => r('fail:' + ((e && e.errMsg) || '?')) });
    setTimeout(() => r('timeout'), 2500);
  })), 3);
  await new Promise((r) => setTimeout(r, 900));
  await shot('h2-bis-list');
  await call('开着弹层拍一张', () => mp.evaluate(() => {
    getCurrentPages().pop().openSlot({ currentTarget: { dataset: { slot: '头部', cell: 1 } } });
    return 1;
  }), 1);
  await new Promise((r) => setTimeout(r, 700));
  await shot('h3-bis-slot-pop');
  await call('关掉弹层并回到顶部', () => mp.evaluate(() => {
    getCurrentPages().pop().closeSlot();
    wx.pageScrollTo({ scrollTop: 0 });
    return 1;
  }), 1);
  await call('回到占位开着的画面', () => mp.evaluate(() => 1), 1);
  log('配装页渲染文字里没有百分比与强度评价词（红线）',
    !!bis && !/\d+(\.\d+)?\s*%/.test(bis.text) && !/秒伤|DPS|权重/.test(bis.text),
    String(bis && bis.text).slice(0, 80));
  /* ---------- 出处跳转（2026-11-01：点"副本：X"那行 → 副本详情页并高亮这一件）----------
     桥表 dropLink 由分发层现算（只收"这一行出处就写着某座副本"的），页面不解析显示文字。 */
  const jump = await call('找一行能跳的出处并点它', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const rows = (p.data.rows || []).filter((r) => r.go);
    const nogo = (p.data.rows || []).filter((r) => !r.go && r.src);
    if (!rows.length) return { found: 0, nogo: nogo.length };
    const hit = rows[0];
    p.goDungeon({ currentTarget: { dataset: { d: hit.go, item: String(hit.item) } } });
    return { found: rows.length, nogo: nogo.length, total: (p.data.rows || []).length,
      want: hit.go, item: String(hit.item) };
  }), 2);
  await new Promise((r) => setTimeout(r, 1200));
  const jumped = await call('看有没有真的跳到副本详情页', () => mp.evaluate(() => {
    const ps = getCurrentPages();
    const top = ps[ps.length - 1] || {};
    const d = top.data || {};
    return { depth: ps.length, route: top.route || '', id: d.id, hi: d.highlightDrop, notice: d.dropNotice };
  }), 2);
  log('有出处的行能跳到那座副本详情页，并把这一件带过去高亮（跳不过去的行本来就不渲染成可点）',
    !!jump && jump.found > 0 && !!jumped && jumped.route === 'pages/dungeon/index'
      && jumped.id === jump.want && String(jumped.hi) === String(jump.item),
    JSON.stringify({ jump: jump, got: jumped && { route: jumped.route, id: jumped.id, hi: jumped.hi } }));
  /* 提示要按"这件在本页掉落表里到底有没有"说：配装页的出处是参考站写的，
     本站掉落归属是另一份来源，两边不一致时那里没有可高亮的行，就不能假装高亮了 */
  log('副本页那句提示说清了来源，且没有把配装页来的玩家说成"从掉落反查过来"',
    !!jumped && /配装名单/.test(String(jumped.notice))
      && !/掉落反查/.test(String(jumped.notice)), String(jumped && jumped.notice).slice(0, 90));
  await call('跳回配装页', () => mp.evaluate(() => { wx.navigateBack(); return 1; }), 1);
  await new Promise((r) => setTimeout(r, 800));
  const bisWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/bis/index.wxml'), 'utf8');
  /* 判的是代码里有没有那些元素，不是注释里的字——2026-11-02 起这一栏只剩逐件图一种画面：
     3D 的挂载、按钮、相机那套，连同按种族那张底图回退，都不许留在页面代码里
     （留着就说明哪天又被"照旧"接回去，再接回去的正是这次删掉的那条链路） */
  log('页面里只剩逐件图一种画面：没有 3D 挂载与相机字段、没有「查看 3D／退出 3D」、没有按种族的底图回退',
    !/bindtap="toggle3d"/.test(bisWxml) && !/class="doll"/.test(bisWxml)
      && !/查看 3D|退出 3D/.test(bisWxml)
      && !/bindtap="showModel"|bindtap="hideModel"/.test(bisWxml)
      && !/<bis-3d|xr-scene|modelSrc|stageAspect|onModelStatus/.test(bisWxml)
      && /class="stage-art"/.test(bisWxml) && /mode="aspectFit"/.test(bisWxml), '');
  const homeWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/home/index.wxml'), 'utf8');
  /* 2026-11-03 站主照截图重排：整宽 bis-card 撤掉，BIS 改进两列格、换自绘盾牌图标，
     起名格紧随其后（也是自绘图标）。断言按新意图改写（不是删）：
     「bis-card」这个类不许再出现在首页——回来就说明整宽卡又被"照旧"接回去了。 */
  log('首页 BIS/起名是两列格里的图标卡（自绘图标 + 各自跳转），BIS 在起名与副本前，整宽 bis-card 不再存在',
    /bindtap="goBis"/.test(homeWxml) && /img\/home\/bis-icon\.png/.test(homeWxml)
      && /bindtap="goNamer"/.test(homeWxml) && /img\/home\/namer-icon\.png/.test(homeWxml)
      && homeWxml.indexOf('goBis') >= 0 && homeWxml.indexOf('goBis') < homeWxml.indexOf('goNamer')
      && homeWxml.indexOf('goBis') < homeWxml.indexOf('goDungeons')
      && !/bis-card/.test(homeWxml), '');


  /* ---------- I. 远程功能开关（2026-10-27 站主："暂时先不公开，想公开了不用发版就能公开"） ----------
     三段：① 基线（专业关、宏开）→ 关着的页只说"还没开放"且不取数，首页那张卡不在、宏那张在；
     ② 只改 flags.json 这一个文件把宏拧关 / 专业拧开 → 首页两张卡各自换位，代码一行没动；
     ③ 宏拧回开 → 首页第四格回来，且这一轮还没访问过宏页（P2 那段要求索引整轮只取一次）。
     阶段之间对页面代码文件求哈希，证明"拧开关没改过代码"。 */
  process.stdout.write('\nI. 远程开关：关着看不见，只改 flags.json 就出现（代码一行没动）\n');
  const crypto01 = require('crypto');
  const sha01 = (p) => crypto01.createHash('sha256').update(fs.readFileSync(p)).digest('hex').slice(0, 12);
  /* 改的就是假 OSS 供出去的那一份（项目外），代码与批次数据一个字节都不动 */
  const FLAGS_FILE = LIVE_FLAGS;
  const CODE_FILES = ['pages/professions/index.js', 'pages/professions/index.wxml',
    'pages/macros/index.js', 'pages/macros/index.wxml', 'pages/macros/index.wxss', 'pages/bis/index.js', 'pages/home/index.js',
    'pages/home/index.wxml', 'services/features.js', 'data/flags-local.js', 'app.json'];
  const codeBefore = CODE_FILES.map((f) => f + '=' + sha01(path.join(REPO, 'for-mini', f))).join(' ');
  const flags0 = JSON.parse(fs.readFileSync(FLAGS_FILE, 'utf8'));
  log('这一批带开关对象（与指针同一档，改它不发版）',
    flags0.product === 'wow-forever-mini-flags' && flags0.env === 'beta'
      && flags0.features.professions.on === false && flags0.features.bis.on === true
      && flags0.features.macros.on === true
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
  const homeOff = await call('读首页（专业关、宏开）', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data || {};
    return { open: !!d.openProfessions, macros: !!d.openMacros,
      art: (d.cardBg || {}).professions === undefined ? null : !!d.cardBg.professions };
  }), 3);
  log('首页此时没有「专业与配方」入口卡（关着整块不渲染，不留空白格），但「宏命令」卡在',
    !!homeOff && homeOff.open === false && homeOff.macros === true, JSON.stringify(homeOff));

  /* 只动"线上"那一份开关（项目外那个文件）：等价于跑一次 flags --env beta。
     先把 11-02 顶替「指南」进第四格的这张卡拧关，验的就是这一张的收回路径 */
  const flipped = JSON.parse(fs.readFileSync(FLAGS_FILE, 'utf8'));
  flipped.features.professions.on = true;
  flipped.features.macros.on = false;
  fs.writeFileSync(FLAGS_FILE, JSON.stringify(flipped, null, 1) + '\n');
  process.stdout.write('    → 把本地那份 flags.json 的 macros 拧成 false、professions 拧成 true（模拟线上改开关，代码一行没动）\n');
  await nav('/pages/home/index');
  const homeMacOff = await call('读首页（宏关）', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data || {};
    return { open: !!d.openProfessions, macros: !!d.openMacros };
  }), 3);
  log('宏命令拧关后首页第四格整块收掉（专业同时自己冒出来），代码一个字节都没变',
    !!homeMacOff && homeMacOff.macros === false && homeMacOff.open === true, JSON.stringify(homeMacOff));
  await nav('/pages/macros/index');
  const mOff = await call('宏开关关着直接进这一页', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    return { route: p.route, locked: p.data.locked, loaded: p.data.loaded, rows: (p.data.rows || []).length };
  }), 2);
  log('macros 关着：只说"这一页还没开放"，一个数据请求都不发',
    !!mOff && mOff.route === 'pages/macros/index' && mOff.locked === true && mOff.loaded === false && mOff.rows === 0
      && hitsOf(/macros\/index\.json/).length === 0, JSON.stringify(mOff));
  /* 恢复成"宏开着"：后面 P2 那一段要真进这一页取数，而且索引整轮只许取一次，
     所以这里只把开关拧回来，不再访问宏页 */
  const backOn = JSON.parse(fs.readFileSync(FLAGS_FILE, 'utf8'));
  backOn.features.macros.on = true;
  fs.writeFileSync(FLAGS_FILE, JSON.stringify(backOn, null, 1) + '\n');
  await nav('/pages/home/index');
  const homeOn = await call('读首页（都开）', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data || {};
    return { open: !!d.openProfessions, macros: !!d.openMacros };
  }), 3);
  const codeAfter = CODE_FILES.map((f) => f + '=' + sha01(path.join(REPO, 'for-mini', f))).join(' ');
  log('再拧回来两张卡都在（这就是"不用发版"），而且代码一个字节都没变',
    !!homeOn && homeOn.open === true && homeOn.macros === true && codeBefore === codeAfter,
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
      && pf.stats.professions === 13 && pf.stats.recipes > 1500 && /^http/.test(pf.headUrl),
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
  /* ---------- P2. 宏命令页（2026-10-30：网页那 245 条做进小程序） ---------- */
  await nav('/pages/macros/index');
  /* 扫的是界面，不是注释——注释里写着"红线：不收费"这种话，按字面扫就是自己抓自己 */
  const mWxml = fs.readFileSync(path.join(REPO, 'for-mini/pages/macros/index.wxml'), 'utf8')
    .replace(/<!--[\s\S]*?-->/g, '');
  const mOn = await call('拧开开关后重进宏页', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const d = p.data;
    return { route: d ? p.route : '', locked: d.locked, cls: d.cls, chips: (d.classes || []).length,
      icons: (d.classes || []).filter((c) => /^http/.test(String(c.iconUrl || ''))).length,
      rows: (d.rows || []).length, total: d.total, groups: (d.groups || []).length,
      dis: (d.meta || {}).disclaimer || '', stat: d.statText };
  }), 3);
  log('macros 拧开就出现（代码一行没动），九职业条每个都带图标，并且真的取到了这一职业那一片',
    !!mOn && mOn.locked === false && mOn.chips === 9 && mOn.icons === 9 && mOn.rows > 5 && mOn.cls === 'warrior',
    JSON.stringify(mOn || {}).slice(0, 200));
  /* 2026-11-02 站主指令：来源类界面出口全撤（页头口径句 / 每条"谁整理的"标 / 复制来源钮）。
     撤的是界面，不是记录——分发层 disclaimer 与分片 srcs 一条没删，网页端与审计都靠它，
     所以这两条从"必须有那句"翻成"数据层仍在、界面不许出现"（和 11-01 撤配装页三句同一口径）。 */
  log('口径句仍在数据层（不冒充实测、免费、不分发插件那句一条没删），但界面不再摆出来',
    !!mOn && /第三方插件整理/.test(String(mOn.dis)) && /没有逐条进游戏试过/.test(String(mOn.dis))
      && !/meta\.disclaimer/.test(mWxml), String(mOn && mOn.dis).slice(0, 80));
  log('索引只取一次、职业片按点到的那一片取（不是进页就把 9 片全拉下来）',
    hitsOf(/macros\/index\.json/).length === 1 && hitsOf(/macros\/set\//).length >= 1
      && hitsOf(/macros\/set\//).length < 9,
    JSON.stringify({ idx: hitsOf(/macros\/index\.json/).length, sets: hitsOf(/macros\/set\//).length }));
  const mSw = await call('切到德鲁伊', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    p.pickClass({ currentTarget: { dataset: { id: 'druid' } } });
    return 1;
  }), 1);
  await new Promise((r) => setTimeout(r, 1400));
  const mDruid = await call('德鲁伊那一片到了', () => mp.evaluate(() => {
    const d = getCurrentPages().pop().data;
    return { cls: d.cls, total: d.total, groups: (d.groups || []).length };
  }), 2);
  log('切职业换的是另一片（德鲁伊 36 条，比战士多），用途分组跟着这一片重算',
    !!mDruid && mDruid.cls === 'druid' && mDruid.total > 30 && mDruid.groups >= 2
      && hitsOf(/macros\/set\/druid/).length >= 1, JSON.stringify(mDruid));
  /* 关键词从这片第一条的标题里取——写死"姿态"的话，换个职业那片没这个词就是假红 */
  const mQ = await call('用第一条标题的头两个字搜，再清掉', () => mp.evaluate(() => new Promise((res) => {
    const p = getCurrentPages().pop();
    const all = p.data.total;
    const word = String((p.data.rows[0] || {}).title || '').slice(0, 2);
    p.onSearch({ detail: { value: word } });
    setTimeout(() => {
      const hit = p.data.total;
      p.clearFilters();
      setTimeout(() => res({ word: word, hit: hit, all: all, back: p.data.total, q: p.data.q, grp: p.data.grp }), 260);
    }, 260);
  })), 2);
  log('搜索框真在筛（标题/说明/宏正文都参与），清掉后条数回到该片全量',
    !!mQ && mQ.hit >= 1 && mQ.hit <= mQ.all && mQ.back === mQ.all && mQ.q === '' && mQ.grp === '', JSON.stringify(mQ));
  await shot('q1-macros-page');
  const mOpen = await call('点开一条宏', () => mp.evaluate(() => {
    const p = getCurrentPages().pop();
    const first = (p.data.rows || [])[0];
    if (!first) return null;
    p.openMacro({ currentTarget: { dataset: { id: first.id } } });
    const o = p.data.open || {};
    return { id: o.id, body: String(o.body || ''), grp: o.group,
      leaksSrc: ('srcName' in o) || ('srcChecked' in o) };
  }), 2);
  log('详情里宏正文原样带换行；来源与核对日不再进页面数据（2026-11-02 撤界面出口）',
    !!mOpen && mOpen.body.indexOf('\n') > 0 && !mOpen.leaksSrc, JSON.stringify(mOpen || {}).slice(0, 220));
  /* 界面撤了，记录还在：分片文件里每条宏的 srcs 照旧是"名字+网址+核对日期"，构建时红线没松 */
  const mSet = JSON.parse(fs.readFileSync(
    path.join(BUILD, 'builds', man.buildId, 'macros', 'set', 'warrior.json'), 'utf8'));
  log('分片文件里每条来源仍能追回去（名字 + 出处 + 核对日期；出处可以是插件仓库路径不一定是 http），网页端与审计靠它',
    Array.isArray(mSet.srcs) && mSet.srcs.length >= 1
      && mSet.srcs.every((s) => s && s.name && String(s.url || '').length > 3
        && /^\d{4}-\d{2}-\d{2}$/.test(String(s.date || ''))),
    JSON.stringify(mSet.srcs || []).slice(0, 160));
  log('宏这一页只有只读与复制：没有编辑器、没有执行、没有外链、没有收费字样',
    /复制宏文本/.test(mWxml) && !/<input[^>]*value="{{open.body/.test(mWxml)
      && !/web-view/.test(mWxml) && !/收费|会员|购买/.test(mWxml), '');
  log('来源类出口撤干净了：复制来源钮、谁整理的标、口径句、GearInsight 字样都不在界面',
    !/复制来源/.test(mWxml) && !/srcName/.test(mWxml) && !/openSrc/.test(mWxml)
      && !/GearInsight/.test(mWxml) && !/meta\.disclaimer/.test(mWxml), '');
  await shot('q2-macros-detail');
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
  const MINI = path.join(REPO, 'for-mini') + path.sep;
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
