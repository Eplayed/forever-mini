#!/usr/bin/env node
/* OSS 分发层的自测：正向 + 反向 + 写授权 + 客户端契约
   ------------------------------------------------------------------
   为什么要有这份文件：门禁判据自己也会错（2026-10-15/10-18 各踩过一次），
   所以每个卡口都要有一条"喂坏数据必须红"的反例，而不是只跑一遍绿的。
   跑法：node wow-forever-web/tools/oss-release-test.js
   退出码非 0 就是不通过。

   本轮（R1）硬约束：全程不碰网络、不碰真 bucket。
     · 进程一启动就设 WOW_OSS_OFFLINE=1，oss-release.js 里的真 transport 一旦被调用直接抛错；
     · 所有 upload/rollback/clean/verify 都跑在内存假 OSS 上（假凭证 FAKEKEYID）；
     · 假凭证文件写在系统临时目录， PoE 那条线的真 .env 只被"来源判定"读取，从不发请求。 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');
const crypto = require('crypto');

process.env.WOW_OSS_OFFLINE = '1';

const REPO = path.resolve(__dirname, '..', '..');
const TOOL = path.join(REPO, 'wow-forever-web', 'tools', 'oss-release.js');
const EXPORT_TOOL = path.join(REPO, 'wow-forever-web', 'tools', 'export-mini.js');
const REAL_SRC_DATA = path.join(REPO, 'wow-forever-web', 'src', 'data');
const MINI_SERVICE = path.join(REPO, 'for-mini', 'services', 'oss-manifest.js');
const MINI_ROOT = path.join(REPO, 'for-mini');

const ossTool = require(TOOL);
const md5u = (buf) => crypto.createHash('md5').update(buf).digest('hex').toUpperCase();

let pass = 0;
let fail = 0;
const ok = (name, cond, extra) => {
  if (cond) { pass += 1; process.stdout.write('  ✓ ' + name + '\n'); return; }
  fail += 1;
  process.stdout.write('  ✗ ' + name + (extra ? '  → ' + extra : '') + '\n');
};
/* 每条反例独立成 step：模块缺函数/抛错也只红这一条，不连带把后面的用例全 skip 掉 */
async function step(name, condFn, extra) {
  const tell = typeof extra === 'function' ? await extra() : (extra || '');
  try {
    ok(name, !!(await condFn()), tell);
  } catch (e) {
    ok(name, false, '抛出 ' + e.message);
  }
}

/* 夹具 = 一个迷你仓库：src/data 逐文件符号链接到真源（talents 等目录整体链，
   upstream 不参与导出所以不链），preview 由真 export-mini.js 现生成。
   这样"改源"与"只改 preview"是两件事，能分别测：前者换 buildId，后者必须被对拍拦下。 */
function regen(dir) {
  cp.execFileSync('node', [path.join(dir, 'wow-forever-web', 'tools', 'export-mini.js')], {
    encoding: 'utf8',
    env: Object.assign({}, process.env, { WOW_SNAPSHOT_CROSSCHECK: 'off' })   /* 坏数据夹具要能构造出来；对拍本身另测 */
  });
}
function freshFixture(label) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ossfix-' + label + '-'));
  const web = path.join(dir, 'wow-forever-web');
  fs.mkdirSync(path.join(web, 'tools'), { recursive: true });
  fs.copyFileSync(EXPORT_TOOL, path.join(web, 'tools', 'export-mini.js'));
  fs.copyFileSync(path.dirname(EXPORT_TOOL) + '/oss-release.js', path.join(web, 'tools', 'oss-release.js'));
  /* 导出层要读禁词表；夹具里少拷这一个文件，regen 会以 ENOENT 的形式红，看不出真正的原因 */
  fs.copyFileSync(path.dirname(EXPORT_TOOL) + '/copy-banned.json', path.join(web, 'tools', 'copy-banned.json'));
  fs.mkdirSync(path.join(web, 'src', 'data'), { recursive: true });
  /* 素材层从 <仓库>/src/img 读图。夹具不链这一个目录的话，用夹具里的工具构建
     会得到"1117 张全缺"，反例就会因为错误的原因变红——链上它才是同一份素材。 */
  fs.symlinkSync(path.join(REPO, 'wow-forever-web', 'src', 'img'), path.join(web, 'src', 'img'));
  fs.readdirSync(REAL_SRC_DATA).forEach((f) => {
    if (f === 'upstream') return;
    fs.symlinkSync(path.join(REAL_SRC_DATA, f), path.join(web, 'src', 'data', f));
  });
  regen(dir);
  return dir;
}
const previewOf = (dir) => path.join(dir, 'for-mini', 'oss-preview');
const srcOf = (dir) => path.join(dir, 'wow-forever-web', 'src');
function patchSource(dir, file, fn, noRegen) {
  const target = path.join(dir, 'wow-forever-web', 'src', 'data', file);
  const j = JSON.parse(fs.readFileSync(fs.realpathSync(target), 'utf8'));
  fn(j);
  try { fs.unlinkSync(target); } catch (e) { /* 已经是真文件 */ }
  fs.writeFileSync(target, JSON.stringify(j, null, 1));
  if (noRegen) { patchPreview(dir, file, fn); return; }   /* 导出层自己就会拒绝这种源 */
  regen(dir);
}
function patchPreview(dir, file, fn) {
  const p = path.join(previewOf(dir), file);
  const j = JSON.parse(fs.readFileSync(p, 'utf8'));
  fn(j);
  fs.writeFileSync(p, JSON.stringify(j, null, 1));
}

function fixtureEnv(dir) {
  return {
    WOW_MINI_PREVIEW: previewOf(dir),
    WOW_MINI_BUILD: path.join(dir, 'oss-build'),
    WOW_SITE_SRC: srcOf(dir),
    WOW_OSS_OFFLINE: '1'
  };
}

/* 默认跑仓库里那份工具；传 tool 参数可以跑夹具里自己那份拷贝
   （测"改生成器必须换 buildId"时必须要用夹具的拷贝，否则改的是没被执行的文件） */
function runBuild(envDir, extraArgs, tool) {
  const res = cp.spawnSync('node', [tool || TOOL, 'build', '--env', 'beta'].concat(extraArgs || []), {
    encoding: 'utf8',
    env: Object.assign({}, process.env, fixtureEnv(envDir))
  });
  return { rc: res.status, out: (res.stdout || '') + (res.stderr || ''), envDir };
}

function readManifest(dir) {
  return JSON.parse(fs.readFileSync(path.join(dir, 'oss-build', 'beta', 'manifest.json'), 'utf8'));
}

function withEnv(extra, fn) {
  const saved = {};
  Object.keys(extra).forEach((k) => {
    saved[k] = process.env[k];
    if (extra[k] === null) delete process.env[k];
    else process.env[k] = extra[k];
  });
  const restore = () => Object.keys(saved).forEach((k) => {
    if (saved[k] === undefined) delete process.env[k]; else process.env[k] = saved[k];
  });
  return Promise.resolve().then(fn).then(
    (v) => { restore(); return v; },
    (e) => { restore(); throw e; }
  );
}

/* ---------- 内存假 OSS ---------- */
function fakeOss() {
  const st = { objs: new Map(), counts: { PUT: 0, DELETE: 0, GET: 0, HEAD: 0 }, failPutAt: 0, failListAfter: 0, clock: 0 };
  st.writes = () => st.counts.PUT + st.counts.DELETE;
  st.get = (key) => (st.objs.has(key) ? st.objs.get(key).buf : null);
  st.set = (key, buf, cacheControl, contentType, disposition) => st.objs.set(key, {
    buf, cacheControl: cacheControl || 'public, max-age=60, must-revalidate',
    contentType: contentType || '', contentDisposition: disposition || '',
    lastModified: new Date(st.clock += 1000).toUTCString()
  });
  const res = (statusCode, headers, body) => ({ statusCode, headers: headers || {}, body: body || Buffer.alloc(0) });
  st.transport = (method, bucket, region, pq, body, headers) => {
    if (pq.indexOf('/?') === 0) {
      const q = new URLSearchParams(pq.slice(2));
      const prefix = q.get('prefix') || '';
      st.counts.GET += 1;
      if (st.failListAfterDeletes && st.counts.DELETE > 0) return Promise.resolve(res(500, {}, Buffer.from('<Error><Code>Injected</Code></Error>')));
      if (st.failListAfter && st.counts.GET <= st.failListAfter) return Promise.resolve(res(500, {}, Buffer.from('<Error><Code>Injected</Code></Error>')));
      const keys = Array.from(st.objs.keys()).filter((k) => k.indexOf(prefix) === 0);
      const xml = '<?xml version="1.0"?><ListBucketResult><IsTruncated>false</IsTruncated>'
        + keys.map((k) => '<Contents><Key>' + k + '</Key></Contents>').join('') + '</ListBucketResult>';
      return Promise.resolve(res(200, {}, Buffer.from(xml)));
    }
    const key = decodeURIComponent(pq.slice(1));
    if (method === 'PUT') {
      st.counts.PUT += 1;
      if (st.failPutAt && st.counts.PUT === st.failPutAt) return Promise.resolve(res(500, {}, Buffer.from('<Code>InjectedPutFailure</Code>')));
      st.set(key, body, headers && headers['Cache-Control'], headers && headers['Content-Type'],
        headers && headers['Content-Disposition']);
      return Promise.resolve(res(200, { etag: '"' + md5u(body) + '"' }));
    }
    if (method === 'DELETE') {
      st.counts.DELETE += 1;
      if (!st.objs.has(key)) return Promise.resolve(res(404, {}, Buffer.from('<Code>NoSuchKey</Code>')));
      st.objs.delete(key);
      return Promise.resolve(res(204));
    }
    const o = st.objs.get(key);
    if (!o) return Promise.resolve(res(404, {}, Buffer.from('<Code>NoSuchKey</Code>')));
    const h = { etag: '"' + md5u(o.buf) + '"', 'content-length': o.buf.length, 'cache-control': o.cacheControl,
      'content-type': o.contentType || '', 'content-disposition': o.contentDisposition || '', 'last-modified': o.lastModified };
    if (method === 'HEAD') { st.counts.HEAD += 1; return Promise.resolve(res(200, h)); }
    st.counts.GET += 1;
    return Promise.resolve(res(200, h, o.buf));
  };
  return st;
}

/* 四种凭证来源；cross 那条用临时文件冒充，免得测试依赖别的仓库里的一把真钥匙 */
const CRED_TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'osscreds-'));
const credFile = (name, id) => {
  const p = path.join(CRED_TMP, name);
  fs.writeFileSync(p, 'OSS_ACCESS_KEY_ID=' + id + '\nOSS_ACCESS_KEY_SECRET=FAKESECRET\nOSS_REGION=oss-cn-hangzhou\nOSS_BUCKET=fake-bucket\n');
  return p;
};
const F = credFile('wow-oss-env', 'FKEWOW1');
const L = credFile('local-env', 'FKEWOW2');
const X = credFile('poe-env', 'FKEPOE9');
const NO_MARK = {
  OSS_ACCESS_KEY_ID: null, OSS_ACCESS_KEY_SECRET: null, OSS_BUCKET: null, OSS_REGION: null,
  WOW_ALLOW_CROSS_CREDS: null, WOW_OSS_ENV: null, WOW_OSS_LOCAL_ENV: L, WOW_OSS_CROSS_ENV: X
};
const SOURCES = [
  { name: '环境变量', env: Object.assign({}, NO_MARK, { OSS_ACCESS_KEY_ID: 'FKEENV3', OSS_ACCESS_KEY_SECRET: 'FAKESECRET', OSS_BUCKET: 'fake-bucket' }) },
  { name: '$WOW_OSS_ENV 指定文件', env: Object.assign({}, NO_MARK, { WOW_OSS_ENV: F }) },
  { name: '仓库根本地凭证文件', env: Object.assign({}, NO_MARK) },
  { name: '自动兜底到 PoE 线 .env', env: Object.assign({}, NO_MARK, { WOW_OSS_LOCAL_ENV: path.join(CRED_TMP, 'missing'), WOW_OSS_CROSS_ENV: X }) }
];
const WRITE_CMDS = [
  { name: 'upload', call: (t) => t.cmdUpload('beta', { dryRun: false, yesRelease: false }) },
  { name: 'rollback', call: (t) => t.cmdRollback('beta', { to: 'aaaaaaaaaaaa', yesRelease: false }) },
  { name: 'clean', call: (t) => t.cmdClean('beta', { yesClean: true, yesRelease: false }) }
];

/* ---------- 客户端桩：wx 五个 API + 带 ETag 的响应头 ---------- */
const net = { log: [], map: {} };
const store = {};
global.wx = {
  request(opt) {
    net.log.push(opt.url);
    const e = net.map[opt.url];
    if (e === undefined) { opt.fail(new Error('离线')); return; }
    opt.success({ statusCode: 200, data: e.data, header: e.header || {} });
  },
  getStorageSync(k) { return store[k] === undefined ? '' : store[k]; },
  setStorageSync(k, v) { store[k] = JSON.parse(JSON.stringify(v)); },
  removeStorageSync(k) { delete store[k]; },
  getStorageInfoSync() { return { keys: Object.keys(store) }; }
};
const clearStore = () => Object.keys(store).forEach((k) => { delete store[k]; });
const hitsTo = (needle) => net.log.filter((u) => u.indexOf(needle) >= 0).length;
const oss = require(MINI_SERVICE);

(async () => {
  /* ================= 1. 正向：真产物 ================= */
  process.stdout.write('正向：真产物能建批、结构完整、可逐字节复现\n');
  const good = runBuild(freshFixture('good'), ['--check-identity']);
  ok('build 退出码 0', good.rc === 0, good.out.slice(-400));
  const man = readManifest(good.envDir);
  const batchDir = path.join(good.envDir, 'oss-build', 'beta', 'builds', man.buildId);
  const idx = JSON.parse(fs.readFileSync(path.join(batchDir, 'dungeons', 'index.json'), 'utf8'));
  const bundle = JSON.parse(fs.readFileSync(path.join(batchDir, 'files.json'), 'utf8'));
  const builtAssets = {};
  /* 素材登记表（assets/index.json）是 `assets` 命令生成的，构建段里没有；
     这里以"仓库素材目录下这个文件在不在"为准——分发层登记的就是它。 */
  idx.items.filter((it) => it.art).forEach((it) => {
    builtAssets[it.art] = fs.existsSync(path.join(REPO, 'wow-forever-web', 'src', 'img', it.art));
  });
  ok('索引 38 条 = 9 新本 + 26 经典 + 3 团本', idx.items.length === 38
    && idx.counts.newDungeons === 9 && idx.counts.classicDungeons === 26 && idx.counts.raids === 3,
    JSON.stringify(idx.counts));
  ok('每条索引都能落到实际存在的详情与掉落文件', idx.items.every((it) =>
    fs.existsSync(path.join(batchDir, it.detailPath)) && fs.existsSync(path.join(batchDir, it.lootPath))));
  /* 列表页缩略图（M02 补）：art 进索引，值是相对 assets/ 的路径，缺的那座是 null 而不是空串 */
  const withArt = idx.items.filter((it) => it.art);
  ok('索引带 art 且是 assets 相对路径（37/38 有，缺的那座是 null 不是空串）',
    withArt.length === 37 && withArt.every((it) => /^art\/dungeons\/[a-z0-9-]+\.webp$/.test(it.art))
      && idx.items.filter((it) => !it.art).every((it) => it.art === null),
    withArt.length + ' / 38');
  ok('索引里的 art 都在素材层登记过（列表页要的图也发得出去）',
    withArt.every((it) => Object.prototype.hasOwnProperty.call(builtAssets, it.art)),
    '缺 ' + withArt.filter((it) => !Object.prototype.hasOwnProperty.call(builtAssets, it.art)).slice(0, 2).join(','));
  /* 界面底图（2026-10-22 首页配图）不挂在任何数据条目上，是界面自己引用的——
     这类"清单里的图"也必须进素材台账，否则线上就是卡上一片纯色，而构建一声不响。
     文件不在 → useAsset 会把它记进 assetMissing，下面那条"缺登记 0 条"当场红。 */
  const uiArtPack = JSON.parse(fs.readFileSync(path.join(REPO, 'wow-forever-web', 'src', 'data', 'ui-art.json'), 'utf8'));
  const uiRels = [];
  (function walkUi(node) {
    if (!node || typeof node !== 'object') return;
    Object.keys(node).forEach((k) => { if (k === 'path') uiRels.push(String(node[k]).replace(/^img\//, '')); else if (k !== 'meta') walkUi(node[k]); });
  })(uiArtPack);
  /* 2026-10-23：bg 从 home 那组挪到 tabs（三个 tab 页共用一张），条数由清单自己算，别再写死 */
  /* 条数从清单自己算（tabs.bg + 四张入口卡 = 5）：写死 5 的话，
     下次加一张卡就得先改门禁，那是把"会变的数"抄进不会变的地方。
     真正要拦的是"少了一张"——所以拿清单的 path 条数与导出层收到的条数对拍。 */
  const uiPaths = [];
  (function countPaths(node) {
    if (!node || typeof node !== 'object') return;
    Object.keys(node).forEach((k) => { if (k === 'path') uiPaths.push(1); else if (k !== 'meta') countPaths(node[k]); });
  })(uiArtPack);
  const uiMissing = uiRels.filter((r) => !fs.existsSync(path.join(REPO, 'wow-forever-web', 'src', 'img', r)));
  ok('界面底图清单逐张都在 src/img（' + uiPaths.length + ' 张），导出层一条没漏',
    uiPaths.length === 5 && uiRels.length === uiPaths.length && uiMissing.length === 0,
    JSON.stringify({ listed: uiRels.length, missing: uiMissing }));
  /* 条数按批次构成现算，不抄字面量：加一类分片（M02 的职业片）就把这里改成一个新数字，
     等于把"会变的数"抄进不会变的地方——下次再加一类就又是一条假红。 */
  /* 7 个入口（meta/glossary/副本索引/职业名单/掉落表/职业索引/指南）+ 副本×2 + 法术片 + 天赋片 */
  const expectFiles = 7 + idx.items.length * 2 + man.counts.spellClasses + man.counts.classes;
  ok('bundle 收了每个数据文件一条（7 入口 + 副本 ' + idx.items.length + '×2 + 法术片 ' + man.counts.spellClasses + ' + 天赋片 ' + man.counts.classes + '）',
    Object.keys(bundle.files).length === expectFiles,
    Object.keys(bundle.files).length + ' ≠ ' + expectFiles);
  const ptrPath = path.join(good.envDir, 'oss-build', 'beta', 'manifest.json');
  ok('指针清单不超 manifest 预算（入口从 3 个长到 7 个后预算 12 KB）',
    man.counts.bytes > 0 && fs.statSync(ptrPath).size <= ossTool.BUDGET_KB.manifest * 1024,
    String(fs.statSync(ptrPath).size));
  ok('批次里没有站内相对路径（img/ src/ 一律不许下发）',
    !/"(img|src|static)\//.test(fs.readFileSync(path.join(batchDir, 'dungeons', 'detail', 'ragefire-chasm.json'), 'utf8')));
  /* M02 起头像是"素材相对路径"，不再是摘掉——断言跟着换成更严的一条：
     值必须落在 assets/ 的相对路径里，站内 img/ 一个都不许出现。 */
  const detArt = JSON.parse(fs.readFileSync(path.join(batchDir, 'dungeons', 'detail', 'ragefire-chasm.json'), 'utf8')).dungeon;
  ok('首领头像改成了 assets 相对路径（不是站内 img/，也不再是 undefined）',
    detArt.bosses.every((b) => !b.portrait || /^art\/boss\w*\/[a-z0-9-]+\.webp$/.test(b.portrait))
      && detArt.bosses.some((b) => b.portrait), JSON.stringify(detArt.bosses.slice(0, 1)));
  ok('副本原画同样改成 assets 相对路径', /^art\/dungeons\/[a-z0-9-]+\.webp$/.test(String(detArt.art)), String(detArt.art));
  ok('整批数据文件里搜不到站内 img/ 路径',
    !fs.readdirSync(path.join(batchDir, 'dungeons', 'detail')).some((f) => /"(img|src)\//.test(fs.readFileSync(path.join(batchDir, 'dungeons', 'detail', f), 'utf8'))));
  /* 核对日期不抄字面量：指针里的 latest 必须等于这一批所有文件 facts.max 的最大值，
     且法术书那条线（2026-10-19 插件核对）要真的被算进来，不能被副本那批的旧日期盖住。 */
  const factsMax = Object.keys(bundle.files)
    .map((k) => (bundle.files[k].facts || {}).max).filter(Boolean).sort();
  const latestFacts = factsMax[factsMax.length - 1];
  ok('事实核对日期写进指针，且等于逐文件 facts 的最大值（含法术书那条线）',
    /^\d{4}-\d{2}-\d{2}$/.test(String(man.factDates.latest)) && man.factDates.latest === latestFacts
      && man.factDates.latest >= man.factDates.dungeonDetail.max,
    JSON.stringify({ latest: man.factDates.latest, latestFacts, dungeonDetail: man.factDates.dungeonDetail.max }));
  ok('route 缺口如实登记（38 本全没路线）', idx.notCollected.route === 38, JSON.stringify(idx.notCollected));
  ok('重跑同源：buildId 一致、逐文件 0 差异、manifest 无变化字段',
    good.out.indexOf('buildId 一致') >= 0 && good.out.indexOf('逐文件字节差异 0') >= 0 && good.out.indexOf('manifest 变化字段 []') >= 0,
    good.out.slice(-320));

  /* R1 新增：批次里不许有任何每次构建都变的字段，否则同 buildId 的清单会被重写 */
  await step('清单里没有 builtAt 等时间字段（同一 buildId 必须字节恒定）', () => {
    const t = JSON.stringify(man);
    return man.builtAt === undefined && !/"(builtAt|updatedAt|publishedAt|generatedAt)"/.test(t);
  }, () => JSON.stringify(Object.keys(man)));
  const again = runBuild(freshFixture('again'));
  ok('不同目录重跑同源：指针清单逐字节相同',
    again.rc === 0 && fs.readFileSync(path.join(again.envDir, 'oss-build', 'beta', 'manifest.json')).equals(fs.readFileSync(ptrPath)));
  const ptrDoc = fs.readFileSync(ptrPath, 'utf8');
  ok('指针里写清了客户端实际做的校验（etag），不再空口承诺逐文件 SHA',
    /etag/i.test(ptrDoc) && man.integrity && man.integrity.method === 'etag', ptrDoc.slice(0, 200));
  ok('指针入口文件都带 etag 与 bytes', ['meta', 'glossary', 'dungeonIndex'].every((k) =>
    man.fetch[k] && /^[0-9A-F]{32}$/.test(String(man.fetch[k].etag || '')) && man.fetch[k].bytes > 0),
    JSON.stringify(man.fetch));
  ok('索引每条自带详情/掉落的 etag（客户端不必为校验多取 files.json）',
    idx.items.every((it) => /^[0-9A-F]{32}$/.test(String(it.detailEtag || '')) && /^[0-9A-F]{32}$/.test(String(it.lootEtag || ''))
      && it.detailBytes > 0 && it.lootBytes > 0), JSON.stringify(idx.items[0]));
  /* 对拍本身：outputs 是"临时目录重跑 export-mini 后逐字节比过的那几份产物"，
     inputs 是它们各自的基底原件——**是一对多**（races.json + classes.json 合成 classes.json，
     dungeon-geo.json 并进 dungeons.json 的 geo 字段），所以比的是"两张名单各自齐全且带哈希"，
     不是条数相等。名单读 oss-release.js 导出的常量：加一份基底不用再回来改门禁。 */
  const REL = require(TOOL);
  const relSet = (arr, pre) => arr.map((x) => x.rel).filter((r) => r.indexOf(pre) === 0).sort().join(',');
  ok('溯源写明了导出对拍（' + REL.EXPORT_RELS.length + ' 份产物逐字节重导一致，'
      + REL.BASE_INPUTS.length + ' 份基底原件都带哈希）',
    man.source && man.source.exportCheck && man.source.exportCheck.reproduced === true
      && relSet(man.source.exportCheck.outputs, 'oss-preview/') === REL.EXPORT_RELS.map((f) => 'oss-preview/' + f).sort().join(',')
      && man.source.exportCheck.outputs.every((o) => o.sha256 && o.bytes > 0)
      && relSet(man.source.inputs, 'src/data/') === REL.BASE_INPUTS.map((f) => 'src/data/' + f).sort().join(',')
      && man.source.inputs.every((i) => i.sha256 && i.bytes > 0),
    JSON.stringify({ inputs: man.source.inputs.map((i) => i.rel), outputs: man.source.exportCheck.outputs.map((o) => o.rel) }));
  process.stdout.write('  · 副本首屏实际字节：meta ' + man.fetch.meta.bytes + 'B + 索引 '
    + man.fetch.dungeonIndex.bytes + 'B + 指针 ' + fs.statSync(ptrPath).size + 'B = '
    + ((fs.statSync(ptrPath).size + man.fetch.dungeonIndex.bytes + man.fetch.meta.bytes) / 1024).toFixed(1)
    + ' KB，GET 3 次；整份 dungeons.json 326.7 KB。技能与词条各算各的入口，取一页才多一次 GET\n');
  const coldBytes = fs.statSync(ptrPath).size + man.fetch.dungeonIndex.bytes + man.fetch.meta.bytes;
  /* 指针从 3 个入口长到 7 个（M02 技能/掉落、M03 职业/指南），每个入口约 0.4 KB，
     换来的是"取哪一页才校验哪一页"。44 KB 是 7 入口时代的冷启动上限，再涨就要把入口挪出指针。 */
  ok('副本首屏代价仍 ≤ 44 KB（指针变大就等于冷启动变慢）', coldBytes <= 44 * 1024, String(coldBytes));

  const CHANGE = runBuild(freshFixture('change'));
  patchSource(good.envDir, 'dungeons.json', (j) => { j.newDungeons[0].nameCn = '改了个名字'; });
  const changed = runBuild(good.envDir);
  ok('改一个字段 → buildId 变（旧批不会被当成同一批）',
    changed.rc === 0 && readManifest(good.envDir).buildId !== man.buildId,
    readManifest(good.envDir).buildId + ' vs ' + man.buildId);
  ok('改源之后的新批也自带 buildId，指针能认出混版',
    JSON.parse(fs.readFileSync(path.join(good.envDir, 'oss-build', 'beta', 'builds', readManifest(good.envDir).buildId, 'dungeons', 'index.json'), 'utf8')).buildId === readManifest(good.envDir).buildId);
  ok('未改源的另一次 build 与首次同 id', CHANGE.rc === 0 && readManifest(CHANGE.envDir).buildId === man.buildId,
    readManifest(CHANGE.envDir).buildId);

  /* ================= 2. 反向：数据坏值 ================= */
  process.stdout.write('\n反向：坏数据必须被卡住\n');
  const negatives = [
    { name: '副本标 L0 但没有官方/解包来源', patch: (j) => { j.newDungeons[0].level = 'L0'; j.newDungeons[0].provenance = [{ type: 'fan_db', url: 'https://x', checkedAt: null }]; }, expect: '标 L0 但没有官方/解包来源' },
    { name: '掉落里出现百分比（导出层与分发层同一条红线，两层都拦）', byExporter: true, patch: (j) => { j.classicDungeons[0].drops = [{ itemId: '1', nameCn: '某物', percent: '37.5%', level: 'L2' }]; }, expect: '百分比' },
    { name: '副本 id 重复', patch: (j) => { j.classicDungeons[1].id = j.classicDungeons[0].id; }, expect: '副本 id 有重复' },
    { name: '副本 id 带不能当文件名的字符', patch: (j) => { j.classicDungeons[0].id = '怒焰 裂谷'; }, expect: '含不能作为文件名的字符' },
    { name: '中英文名都为空', patch: (j) => { j.raids[0].nameCn = null; j.raids[0].nameEn = null; }, expect: '中英文名都为空' },
    { name: '站内路径漏进批次（首领备注里写 img/）', patch: (j) => { j.classicDungeons[0].bosses[0].note = 'img/art/bosses/x.webp'; }, expect: '站内相对路径' },
    { name: '单文件超体积预算（掉落塞到 70 KB）', patch: (j) => {
        const big = [];
        for (let i = 0; i < 900; i += 1) big.push({ itemId: String(100000 + i), nameCn: '凑长度的物品名凑长度的物品名', iconKey: 'inv_x', quality: 4, bossId: 'b', bossCn: '首领', level: 'L2' });
        j.classicDungeons[0].drops = big;
      }, expect: '超预算' }
  ];
  for (const t of negatives) {
    await step('反例：' + t.name, () => {
      const dir = freshFixture('neg');
      patchSource(dir, 'dungeons.json', t.patch, !!t.byExporter);
      const r = runBuild(dir);
      return r.rc !== 0 && r.out.indexOf(t.expect) >= 0 && (t.byExporter || r.out.indexOf('不配套') < 0);
    }, () => 'rc 与输出不符');
  }

  /* ================= 3. 反例：导出产物与基底不配套 ================= */
  process.stdout.write('\n反向：oss-preview 与 src/data 必须逐字节对得上\n');
  const drift = [
    { name: '只改 oss-preview 里第一本的名字（真源没改）', patch: (j) => { j.newDungeons[0].nameCn = '偷改的副本名'; } },
    { name: '只改 oss-preview 里某个副本的英文名', patch: (j) => { j.classicDungeons[0].nameEn = '被偷改的英文名'; } },
    { name: 'oss-preview 的 meta 覆盖率被手改', meta: true }
  ];
  for (const t of drift) {
    await step('反例：' + t.name + ' → 构建拒绝', () => {
      const dir = freshFixture('drift');
      if (t.patch) patchPreview(dir, 'dungeons.json', t.patch);
      else {
        const p = path.join(previewOf(dir), 'meta.json');
        const m = JSON.parse(fs.readFileSync(p, 'utf8'));
        m.coverage.L0 += 1;
        fs.writeFileSync(p, JSON.stringify(m, null, 1));
      }
      const r = runBuild(dir);
      return r.rc !== 0 && /不配套|重导出/.test(r.out);
    }, () => '没有拦下漂移');
  }

  await step('反例：只改生成器（内容一个没动）→ buildId 必须变（同 id 不同字节就是假不可变）', () => {
    const a = runBuild(freshFixture('gen-a'));
    const dirB = freshFixture('gen-b');
    const tp = path.join(dirB, 'wow-forever-web', 'tools', 'oss-release.js');
    const src = fs.readFileSync(tp, 'utf8');
    const patched = src.replace("    pointer: { key: ns + '/manifest.json', cacheControl: POINTER_CACHE },",
      "    probeField: 1,\n    pointer: { key: ns + '/manifest.json', cacheControl: POINTER_CACHE },");
    if (patched === src) return false;
    fs.writeFileSync(tp, patched);
    const b = runBuild(dirB, null, path.join(dirB, 'wow-forever-web', 'tools', 'oss-release.js'));
    const same = a.rc === 0 && b.rc === 0 && readManifest(a.envDir).buildId === readManifest(b.envDir).buildId;
    return a.rc === 0 && b.rc === 0 && !same;
  }, '生成器变了 buildId 却没变');

  /* ================= 3·5. 主包快照 ↔ 分发层索引 ================= */
  process.stdout.write('\n双向卡口：主包副本索引快照必须与分发层的索引逐字段一致\n');
  const runExport = (dir, check) => cp.spawnSync('node', [path.join(dir, 'wow-forever-web', 'tools', 'export-mini.js')], {
    encoding: 'utf8',
    env: Object.assign({}, process.env, { WOW_SNAPSHOT_CROSSCHECK: check ? 'on' : 'off' })
  });
  await step('正路：开着对拍跑导出，快照生成且两份产物逐字段一致', () => {
    const dir = freshFixture('xchk');
    const r = runExport(dir, true);
    return r.status === 0 && fs.existsSync(path.join(dir, 'for-mini', 'data', 'forever-dungeon-snapshot.js'))
      && fs.readFileSync(path.join(dir, 'for-mini', 'data', 'forever-dungeon-snapshot.js'), 'utf8').indexOf('hall-of-thanes') >= 0;
  }, '导出被拒或快照没生成');
  await step('反例：分发层的索引字段改一个名，导出层必须拒绝出快照', () => {
    const dir = freshFixture('xneg');
    const rp = path.join(dir, 'wow-forever-web', 'tools', 'oss-release.js');
    const t = fs.readFileSync(rp, 'utf8').replace('    partySize: d.partySize || null,', '    partySizeX: d.partySize || null,');
    if (t === fs.readFileSync(rp, 'utf8')) return false;
    fs.writeFileSync(rp, t);
    const r = runExport(dir, true);
    return r.status !== 0 && ((r.stdout || '') + (r.stderr || '')).indexOf('逐字段不一致') >= 0;
  }, '两边字段漂了却没人拦');
  await step('反例：索引快照与分发层条数对不上也要拒', () => {
    const dir = freshFixture('xcnt');
    const ep = path.join(dir, 'wow-forever-web', 'tools', 'export-mini.js');
    const t = fs.readFileSync(ep, 'utf8').replace('items: dungeonList.map(dungeonIndexEntry)', 'items: dungeonList.slice(0, 30).map(dungeonIndexEntry)');
    fs.writeFileSync(ep, t);
    const r = runExport(dir, true);
    return r.status !== 0 && ((r.stdout || '') + (r.stderr || '')).indexOf('逐字段不一致') >= 0;
  }, '少 8 本没人发现');
  await step('正路：仓库里三份主包快照合计不超 60 KB 预算', () => {
    const files = ['forever-glossary-snapshot.js', 'forever-meta-snapshot.js', 'forever-dungeon-snapshot.js'];
    const total = files.reduce((s, f) => s + fs.statSync(path.join(MINI_ROOT, 'data', f)).size, 0);
    process.stdout.write('  · 主包快照 ' + (total / 1024).toFixed(1) + ' KB（预算 60 KB）\n');
    return total <= 60 * 1024;
  }, '超预算');

  /* ================= 3·6. M02-2 技能分片 ================= */
  process.stdout.write('\nM02-2 技能分片：职业名单与九片法术必须自洽、可校验、不带描述类内容\n');
  const spIdx = JSON.parse(fs.readFileSync(path.join(batchDir, 'spells', 'classes.json'), 'utf8'));
  ok('职业名单 9 条，counts.total 等于各职业条数之和',
    spIdx.classes.length === 9 && spIdx.counts.classes === spIdx.classes.length
      && spIdx.counts.total === spIdx.classes.reduce((s, c) => s + c.count, 0), JSON.stringify(spIdx.counts));
  ok('每个职业的分片路径都由 classId 推出来，且文件真的在批次里',
    spIdx.classes.every((c) => c.shardPath === 'spells/class/' + c.classId + '.json'
      && fs.existsSync(path.join(batchDir, c.shardPath))), JSON.stringify(spIdx.classes.slice(0, 1)));
  ok('每个职业条目带齐三种校验值（etag 32 位十六进制 / md5 24 位 base64 / bytes）',
    spIdx.classes.every((c) => /^[0-9A-F]{32}$/.test(String(c.shardEtag))
      && /^[A-Za-z0-9+/]{22}==$/.test(String(c.shardMd5)) && c.shardBytes > 0),
    JSON.stringify(spIdx.classes[0]).slice(0, 160));
  const spShards = spIdx.classes.map((c) => {
    const buf = fs.readFileSync(path.join(batchDir, c.shardPath));
    return { c, buf, obj: JSON.parse(buf.toString('utf8')) };
  });
  ok('校验值对得上真实字节（名单说要 40 KB 就不能给 41 KB）',
    spShards.every((s) => s.buf.length === s.c.shardBytes && md5u(s.buf) === s.c.shardEtag));
  ok('片里条数与名单一致，且没有串职业',
    spShards.every((s) => s.obj.spells.length === s.c.count && s.obj.spells.every((x) => x.classId === s.c.classId)
      && s.obj.classId === s.c.classId));
  ok('每片都带批次身份五项（buildId/product/schemaVersion/kind/classId）',
    spShards.every((s) => s.obj.buildId === man.buildId && s.obj.product === 'wow-forever-mini'
      && s.obj.schemaVersion === 1 && s.obj.kind === 'spell-class'));
  ok('单片不超 64 KB 预算（手机上一次 GET 的代价）',
    spShards.every((s) => s.buf.length <= 64 * 1024), Math.max.apply(null, spShards.map((s) => s.buf.length)) + ' B');
  /* 图标查的是真仓库的 src/img（runBuild 跑的是仓库里的工具，素材层也从那里读），
     夹具目录里没有 img，别往 good.envDir 下找。 */
  ok('技能图标全登记进素材层，缺图 0 条',
    man.assets.missing === 0 && spShards.every((s) => s.obj.spells.filter((x) => x.iconKey)
      .every((x) => fs.existsSync(path.join(REPO, 'wow-forever-web', 'src', 'img', 'icons', x.iconKey + '.jpg')))),
    'missing ' + man.assets.missing);
  ok('分片里没有站内相对路径', !spShards.some((s) => /"(img|src|static)\//.test(s.buf.toString('utf8'))));
  ok('红线：分片里没有技能描述与循环建议类内容',
    !spShards.some((s) => /"(description|desc|tooltip|rotation|rankText|rankDescription)"\s*:/.test(s.buf.toString('utf8'))));
  ok('指针里 spellClasses 是第四个入口，带 bytes 与 md5',
    !!man.fetch.spellClasses && man.fetch.spellClasses.path.indexOf('builds/' + man.buildId + '/') === 0
      && man.fetch.spellClasses.bytes > 0 && !!man.fetch.spellClasses.md5, JSON.stringify(man.fetch.spellClasses || null));
  /* 反例改的是导出产物本身，并显式关掉对拍——不然先红的是"preview 与基底不配套"，
     测不到这一层自己的那条计数判据。 */
  const badPreview = (label, mutate) => {
    const dir = freshFixture(label);
    const p = path.join(dir, 'for-mini', 'oss-preview', 'spells.json');
    const j = JSON.parse(fs.readFileSync(p, 'utf8'));
    mutate(j);
    fs.writeFileSync(p, JSON.stringify(j, null, 1));
    return runBuild(dir, ['--skip-export-check']);
  };
  /* step() 的说明文字在判定之前就算好了，所以先把构建跑完再交给 step */
  const spcntRun = badPreview('spcnt', (j) => { j.classes[0].count += 1; });
  await step('反例：某职业实际条数与名单不符 → 构建拒绝',
    () => spcntRun.rc !== 0 && spcntRun.out.indexOf('头部写') >= 0,
    'rc=' + spcntRun.rc + ' ' + spcntRun.out.slice(-200));
  const sppathRun = badPreview('sppath', (j) => { j.classes[3].classId = '../evil'; });
  await step('反例：classId 拼成路径穿越 → 构建拒绝，不生成 ../ 路径',
    () => sppathRun.rc !== 0 && sppathRun.out.indexOf('不能当分片文件名') >= 0,
    'rc=' + sppathRun.rc + ' ' + sppathRun.out.slice(-200));

  /* ================= 3·7. M02-3 掉落反查表 ================= */
  process.stdout.write('\nM02-3 掉落反查：一张总表必须与副本索引逐条对得上，行不能错位\n');
  const lootTab = JSON.parse(fs.readFileSync(path.join(batchDir, 'loots', 'index.json'), 'utf8'));
  ok('列名固定六列（客户端按位置取值，少一列就会把首领序号当品质）',
    JSON.stringify(lootTab.cols) === JSON.stringify(['itemId', 'name', 'quality', 'iconKey', 'boss', 'level']),
    JSON.stringify(lootTab.cols));
  ok('表的行数与去重物品数等于副本索引里逐座相加的掉落条数',
    lootTab.counts.rows === idx.items.reduce((s, it) => s + it.dropCount, 0)
      && lootTab.counts.dungeons === idx.items.length, JSON.stringify(lootTab.counts));
  ok('每座本都能对回副本索引的同一条（id 与 dropCount 一致，不多不少）',
    lootTab.dungeons.every((d) => {
      const it = idx.items.filter((x) => x.id === d.id)[0];
      return !!it && it.dropCount === d.rows.length;
    }));
  ok('每行长度等于列数，且没有悬空的首领序号',
    lootTab.dungeons.every((d) => d.rows.every((r) => r.length === lootTab.cols.length
      && r[4] >= 0 && r[4] < d.bosses.length)));
  ok('每行都有 itemId（玩家复制过去要能查到）',
    lootTab.dungeons.every((d) => d.rows.every((r) => r[0] !== null && r[0] !== undefined && r[0] !== '')));
  ok('红线：整张表里没有掉落百分比', !/%\s|\d+(\.\d+)?\s*%/.test(JSON.stringify(lootTab.dungeons)));
  ok('整表 ≤ 192 KB（一次 GET 换"任何一件都能查"，再大就该切了）',
    fs.statSync(path.join(batchDir, 'loots', 'index.json')).size <= 192 * 1024,
    String(fs.statSync(path.join(batchDir, 'loots', 'index.json')).size));
  ok('表里出现的图标都在素材层（缺图 0 且反向卡口已过）', man.assets.missing === 0);
  ok('指针里 lootIndex 是第五个入口，带 md5 与 bytes',
    !!man.fetch.lootIndex && man.fetch.lootIndex.path === 'builds/' + man.buildId + '/loots/index.json'
      && man.fetch.lootIndex.bytes > 0 && !!man.fetch.lootIndex.md5, JSON.stringify(man.fetch.lootIndex || null));
  ok('首页数字与这张表同源（meta.counts 与 manifest.counts 两个数都相等）',
    man.counts.lootRows === lootTab.counts.rows && man.counts.lootItems === lootTab.counts.items,
    JSON.stringify({ m: man.counts, t: lootTab.counts }));
  const lootToolBad = (label, from, to, needle) => {
    const dir = freshFixture(label);
    const rp = path.join(dir, 'wow-forever-web', 'tools', 'oss-release.js');
    const src = fs.readFileSync(rp, 'utf8');
    if (src.indexOf(from) < 0) return { rc: -1, out: '夹具里找不到要改的那一行：' + from };
    fs.writeFileSync(rp, src.replace(from, to));
    /* 必须跑夹具里那份工具：runBuild 默认起的是仓库里的原件，改夹具副本不生效 */
    return runBuild(dir, ['--skip-export-check'], rp);
  };
  const badBoss = lootToolBad('lootboss',
    "        bosses.indexOf(x.bossCn || x.bossId || '未记首领'),",
    "        bosses.indexOf(x.bossCn || x.bossId || '未记首领') + 5,");
  await step('反例：首领序号越界 → 构建拒绝', () => badBoss.rc !== 0 && badBoss.out.indexOf('首领序号') >= 0,
    'rc=' + badBoss.rc + ' ' + badBoss.out.slice(-160));
  const badId = lootToolBad('lootid', '        x.itemId || null,', '        null,');
  await step('反例：行里缺 itemId → 构建拒绝', () => badId.rc !== 0 && badId.out.indexOf('缺 itemId') >= 0,
    'rc=' + badId.rc + ' ' + badId.out.slice(-160));
  const badCols = lootToolBad('lootcols', "  const LOOT_COLS = ['itemId', 'name', 'quality', 'iconKey', 'boss', 'level'];",
    "  const LOOT_COLS = ['itemId', 'name', 'quality', 'iconKey', 'boss'];");
  await step('反例：列名与行内容对不上 → 构建拒绝（客户端按位置取值，绝不能少列）',
    () => badCols.rc !== 0 && badCols.out.indexOf('列名却写了') >= 0,
    'rc=' + badCols.rc + ' ' + badCols.out.slice(-160));

  /* ================= 3·8. M03 职业/天赋/指南分片 ================= */
  process.stdout.write('\nM03 职业卡：种族矩阵、天赋分片、指南壳都要自洽\n');
  const clsIdx = JSON.parse(fs.readFileSync(path.join(batchDir, 'classes', 'index.json'), 'utf8'));
  ok('职业索引带 10 种族 9 职业，且与源文件条数一致',
    clsIdx.counts.races === 10 && clsIdx.counts.classes === 9
      && clsIdx.races.length === 10 && clsIdx.classes.length === 9, JSON.stringify(clsIdx.counts));
  ok('每个种族都带可选职业矩阵（职业卡第一屏靠它）',
    clsIdx.races.every((r) => Array.isArray(r.classes) && r.classes.length > 0
      && r.classes.every((cid) => clsIdx.classes.some((c) => c.classId === cid))));
  /* 2026-10-22 站主报"小程序里缺天裔的数据和图标"——真因不是没数据：天裔的 4 条特长
     一直在库里，只是挂在 subgroup.traits 上，而界面读顶层 traits。
     这两条把"归一化 + 图标接上"钉住，以后谁把 subgroup 那层改回只读顶层，当场红。 */
  const sky = clsIdx.races.filter((r) => String(r.id).indexOf('skyborne') === 0);
  ok('天裔两条都带 4 条特长（数从 subgroup 合成上来，traitVia 说清来路）',
    sky.length === 2 && sky.every((r) => r.traits.length === 4 && r.traitVia === 'subgroup'
      && r.traits.every((t) => t.name && t.effect) && !!r.subgroup && !!r.subgroup.nameCn),
    JSON.stringify(sky.map((r) => ({ id: r.id, n: r.traits.length, via: r.traitVia, sub: r.subgroup && r.subgroup.nameCn }))));
  ok('天裔两个子族的特长确实不同（共 3 条相同、各自留 1 条专属），不是复制粘贴',
    sky.length === 2 && JSON.stringify(sky[0].traits.map((t) => t.name)) !== JSON.stringify(sky[1].traits.map((t) => t.name)),
    JSON.stringify(sky.map((r) => r.traits.map((t) => t.name).join('/'))));
  ok('天裔种族小图标接上了、且登记进素材台账（官方 CDN 没这张，走站主授权的插件图）',
    sky.every((r) => r.portrait === 'art/raceicons/skyborne.webp'
      && fs.existsSync(path.join(REPO, 'wow-forever-web', 'src', 'img', r.portrait))),
    JSON.stringify(sky.map((r) => r.portrait)));
  ok('没有哪个种族的特长是空数组（空＝要么丢数据要么该降级，界面那句"还没核到"不许成为常态）',
    clsIdx.races.every((r) => r.traits.length > 0 || r.level === 'L2' || r.level === 'L3'),
    JSON.stringify(clsIdx.races.filter((r) => !r.traits.length).map((r) => r.id + ':' + r.level)));
  const talentShards = clsIdx.classes.filter((c) => c.shardPath);
  ok('九个职业都有天赋分片，路径由 classId 推出且文件在批次里',
    talentShards.length === 9 && talentShards.every((c) => c.shardPath === 'talents/class/' + c.classId + '.json'
      && fs.existsSync(path.join(batchDir, c.shardPath))), String(talentShards.length));
  /* 口径翻转（2026-10-22 站主："天赋树是模拟器的样子，可以模拟点击配置，和网页版那样的功能"）：
     M03 那条"刻意不下发 tierUnlockCost"随这条作废——网页端引擎本来就用这份数做加点判定，
     小程序要做同一个功能就必须拿到它。放松的只是"下发"，不是"怎么说"：
     界面上那句"按经典旧世推、无限服还没实测"仍然钉在 mini-m02-check 的 F 段里。 */
  ok('天赋分片带 rules（总点数与层级门槛），小程序模拟器与网页用同一份数',
    talentShards.every((c) => {
      const t = JSON.parse(fs.readFileSync(path.join(batchDir, c.shardPath), 'utf8'));
      return !!t.rules && t.rules.totalPoints > 0 && Array.isArray(t.rules.tierUnlockCost)
        && t.rules.tierUnlockCost.length === 7 && t.rules.tierUnlockCost[0] === 0;
    }), JSON.stringify((talentShards[0] || {}).classId));
  ok('天赋分片节点都带坐标与级数（界面按 tier/column 摆位）',
    talentShards.every((c) => {
      const t = JSON.parse(fs.readFileSync(path.join(batchDir, c.shardPath), 'utf8'));
      return t.trees.every((tr) => tr.nodes.every((n) => Number.isInteger(n.tier) && Number.isInteger(n.column) && n.maxRanks > 0));
    }));
  ok('天赋分片校验值对得上真实字节',
    talentShards.every((c) => {
      const buf = fs.readFileSync(path.join(batchDir, c.shardPath));
      return buf.length === c.shardBytes && md5u(buf) === c.shardEtag;
    }));
  const guideShard = JSON.parse(fs.readFileSync(path.join(batchDir, 'guide.json'), 'utf8'));
  ok('指南壳带红线边界那句话，且宏/插件是数组（空也合法：界面按有没有内容决定入口）',
    guideShard.kind === 'guide' && Array.isArray(guideShard.macros) && Array.isArray(guideShard.addons)
      && /免费/.test(String(guideShard.meta && guideShard.meta.boundaries)), JSON.stringify(Object.keys(guideShard)));
  ok('指针里 classIndex 与 guide 是第六、七个入口',
    !!man.fetch.classIndex && !!man.fetch.guide && man.fetch.classIndex.bytes > 0 && man.fetch.guide.bytes > 0);

  /* ================= 4. 写授权统一闸 ================= */
  process.stdout.write('\n写授权：每条写命令都要显式 WOW_ALLOW_CROSS_CREDS=1，与凭证来源无关\n');
  ok('oss-release.js 暴露了测试注入点与子命令函数',
    typeof ossTool.setTransportForTest === 'function' && typeof ossTool.cmdUpload === 'function'
    && typeof ossTool.cmdRollback === 'function' && typeof ossTool.cmdClean === 'function');

  for (const src of SOURCES) {
    for (const cmd of WRITE_CMDS) {
      await step('无标记：' + src.name + ' + ' + cmd.name + ' → rc1 且 PUT/DELETE=0', () => {
        const st = fakeOss();
        return withEnv(Object.assign({}, src.env, Object.assign({}, fixtureEnv(good.envDir), { WOW_MINI_BUILD: path.join(good.envDir, 'oss-build-guard') })), () => {
          ossTool.setTransportForTest(st.transport);
          return cmd.call(ossTool, st).then((rc) => {
            ossTool.setTransportForTest(null);
            if (rc === 0) return false;
            return st.writes() === 0;
          });
        });
      }, () => '被放行或发生了写入');
    }
    await step('标记只挡写：' + src.name + ' + upload --dry-run 允许（且 PUT=0）', () => {
      const st = fakeOss();
      return withEnv(Object.assign({}, src.env, Object.assign({}, fixtureEnv(good.envDir), { WOW_MINI_BUILD: path.join(good.envDir, 'oss-build-dry') })), () => {
        ossTool.setTransportForTest(st.transport);
        return ossTool.cmdUpload('beta', { dryRun: true, yesRelease: false }).then((rc) => {
          ossTool.setTransportForTest(null);
          return rc === 0 && st.counts.PUT === 0 && st.counts.DELETE === 0;
        });
      });
    }, () => '试运行被误拦或发生了写入');
  }

  await step('无标记时报错文案点明 WOW_ALLOW_CROSS_CREDS', () => {
    const st = fakeOss();
    const logs = [];
    const w = process.stdout.write.bind(process.stdout);
    process.stdout.write = (s) => { logs.push(s); return true; };
    return withEnv(Object.assign({}, SOURCES[0].env, Object.assign({}, fixtureEnv(good.envDir), { WOW_MINI_BUILD: path.join(good.envDir, 'oss-build-msg') })), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc) => {
        ossTool.setTransportForTest(null);
        process.stdout.write = w;
        return rc === 1 && logs.join('').indexOf('WOW_ALLOW_CROSS_CREDS') >= 0;
      });
    }).catch((e) => { process.stdout.write = w; throw e; });
  }, () => '文案没提标记');

  await step('带标记时 PoE 那把钥匙可以写（站主口径：共用 + 每条显式标记）', () => {
    const st = fakeOss();
    return withEnv(Object.assign({}, NO_MARK, fixtureEnv(good.envDir), {
      WOW_ALLOW_CROSS_CREDS: '1',
      WOW_OSS_LOCAL_ENV: path.join(CRED_TMP, 'missing'),
      WOW_OSS_CROSS_ENV: X,
      WOW_MINI_BUILD: path.join(good.envDir, 'oss-build-cross')
    }), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc) => {
        ossTool.setTransportForTest(null);
        return rc === 0 && st.counts.PUT > 0 && st.objs.has(ossTool.pointerKey('beta'));
      });
    });
  }, () => '带标记也没发出去');

  await step('只读命令（list）不需要标记', () => {
    const st = fakeOss();
    return withEnv(Object.assign({}, NO_MARK, { WOW_OSS_ENV: F }), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdList('beta').then((rc) => { ossTool.setTransportForTest(null); return rc === 0 && st.writes() === 0; });
    });
  }, () => '只读被误拦');

  await step('真 PoE 路径仍被标成跨项目（只读判定，不发请求）', () => {
    const saved = Object.assign({}, process.env);
    ['OSS_ACCESS_KEY_ID', 'OSS_ACCESS_KEY_SECRET', 'WOW_OSS_ENV', 'WOW_OSS_LOCAL_ENV', 'WOW_OSS_CROSS_ENV'].forEach((k) => { delete process.env[k]; });
    const c = ossTool.loadCreds(false);
    const r = c.ok === true && c.crossProject === true && String(c.from).indexOf('p2-database') >= 0;
    Object.keys(saved).forEach((k) => { process.env[k] = saved[k]; });
    return r;
  }, () => JSON.stringify(ossTool.loadCreds(false).from));

  await step('写闸在本地落盘之前：无标记时不生成 oss-build 目录', () => {
    const st = fakeOss();
    const dir = path.join(good.envDir, 'oss-build-order');
    fs.rmSync(dir, { recursive: true, force: true });
    return withEnv(Object.assign({}, SOURCES[0].env, Object.assign({}, fixtureEnv(good.envDir), { WOW_MINI_BUILD: dir })), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc) => {
        ossTool.setTransportForTest(null);
        return rc === 1 && !fs.existsSync(path.join(dir, 'beta', 'manifest.json'));
      });
    });
  }, () => '标记之前就把批次写到本地了');

  /* ================= 5. clean 的破坏面 ================= */
  process.stdout.write('\nclean：release 要两道确认，清后必须能核验\n');
  const seedClean = (env) => {
    const st = fakeOss();
    const prefix = ossTool.NAMESPACES[env] + '/';
    for (let i = 0; i < 5; i += 1) st.set(prefix + 'builds/aaaaaaaaaaaa/f' + i + '.json', Buffer.from('{}\n'));
    st.set(prefix + 'manifest.json', Buffer.from('{"buildId":"aaaaaaaaaaaa"}\n'));
    return st;
  };
  await step('反例：clean --env release --yes-clean 缺 --yes-release → rc1、DELETE=0', () => {
    const st = seedClean('release');
    return withEnv(Object.assign({}, NO_MARK, { WOW_ALLOW_CROSS_CREDS: '1', WOW_OSS_ENV: F }), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdClean('release', { yesClean: true, yesRelease: false }).then((rc) => {
        ossTool.setTransportForTest(null);
        return rc === 1 && st.counts.DELETE === 0 && st.objs.size === 6;
      });
    });
  }, () => '线上环境被单道确认就清了');
  await step('正路：clean --env release --yes-clean --yes-release → 删净、rc0', () => {
    const st = seedClean('release');
    return withEnv(Object.assign({}, NO_MARK, { WOW_ALLOW_CROSS_CREDS: '1', WOW_OSS_ENV: F }), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdClean('release', { yesClean: true, yesRelease: true }).then((rc) => {
        ossTool.setTransportForTest(null);
        return rc === 0 && st.counts.DELETE === 6 && st.objs.size === 0;
      });
    });
  }, () => '两道确认齐了反而删不掉');
  await step('clean 会打印 bucket 与前缀（清前一次、清后一次）', () => {
    const st = seedClean('release');
    const logs = [];
    const w = process.stdout.write.bind(process.stdout);
    process.stdout.write = (s) => { logs.push(s); return true; };
    return withEnv(Object.assign({}, NO_MARK, { WOW_ALLOW_CROSS_CREDS: '1', WOW_OSS_ENV: F }), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdClean('release', { yesClean: true, yesRelease: true }).then((rc) => {
        ossTool.setTransportForTest(null);
        process.stdout.write = w;
        const t = logs.join('');
        return /fake-bucket/.test(t) && (t.match(/wow\/release\/v1\//g) || []).length >= 2;
      });
    }).catch((e) => { process.stdout.write = w; throw e; });
  }, () => '没报清桶与前缀');
  await step('反例：清后无法核验 → rc≠0（不许报成删干净了）', () => {
    const st = seedClean('beta');
    st.failListAfterDeletes = true;
    return withEnv(Object.assign({}, NO_MARK, { WOW_ALLOW_CROSS_CREDS: '1', WOW_OSS_ENV: F }), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdClean('beta', { yesClean: true, yesRelease: false }).then((rc) => {
        ossTool.setTransportForTest(null);
        return rc !== 0;
      });
    });
  }, () => '核验失败却返回 0');
  await step('反例：残留对象没删净 → rc≠0', () => {
    const st = seedClean('beta');
    const real = st.transport;
    st.transport = (m, b, r, p, body, h) => {
      if (m === 'DELETE' && p.indexOf('/f0.json') >= 0) return Promise.resolve({ statusCode: 409, headers: {}, body: Buffer.from('blocked') });
      return real(m, b, r, p, body, h);
    };
    return withEnv(Object.assign({}, NO_MARK, { WOW_ALLOW_CROSS_CREDS: '1', WOW_OSS_ENV: F }), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdClean('beta', { yesClean: true, yesRelease: false }).then((rc) => {
        ossTool.setTransportForTest(null);
        return rc !== 0;
      });
    });
  }, () => '有残留却算成功');

  /* 凭证不能进小程序包 */
  const pc = JSON.parse(fs.readFileSync(path.join(MINI_ROOT, 'project.config.json'), 'utf8'));
  const ignored = (pc.packOptions && pc.packOptions.ignore || []).map((x) => x.value);
  ok('小程序打包排除 oss-build / oss-preview / data 之外不含凭证目录',
    ignored.indexOf('oss-build') >= 0 && ignored.indexOf('oss-preview') >= 0, JSON.stringify(ignored));
  await step('默认本地凭证文件不在小程序根目录里（.gitignore 挡不住微信打包器）', () => {
    const p = typeof ossTool.localCredPath === 'function' ? ossTool.localCredPath() : null;
    if (!p) return false;
    return path.relative(MINI_ROOT, p).startsWith('..');
  }, () => '凭证默认路径仍在 for-mini/ 里或没导出该常量');
  await step('for-mini/ 目录树下没有任何凭证文件', () => {
    const walk = (d, acc) => {
      fs.readdirSync(d, { withFileTypes: true }).forEach((e) => {
        if (e.name === 'node_modules' || e.name.startsWith('.')) return;
        const p = path.join(d, e.name);
        if (e.isDirectory()) { if (e.name !== 'oss-preview' && e.name !== 'oss-build') walk(p, acc); return; }
        if (/\.oss-env|\.env$/.test(e.name)) acc.push(p);
        else if (/\.(js|json)$/.test(e.name) && e.name !== 'project.config.json') {
          const t = fs.readFileSync(p, 'utf8');
          if (/OSS_ACCESS_KEY_SECRET\s*[:=]\s*["']?[A-Za-z0-9]{16,}/.test(t) && !/FAKE/.test(t)) acc.push(p);
        }
      });
      return acc;
    };
    const found = walk(MINI_ROOT, []);
    return found.length === 0;
  }, () => '找到 ' + MINI_ROOT + ' 内疑似凭证文件');

  /* ================= 6. 上传中途失败 / 不可变批次 ================= */
  process.stdout.write('\n上传：半批不切指针，同 buildId 不许覆写\n');
  const upEnv = (dir) => Object.assign({}, NO_MARK, fixtureEnv(dir), {
    WOW_ALLOW_CROSS_CREDS: '1', WOW_OSS_ENV: F,
    WOW_MINI_BUILD: path.join(dir, 'oss-build-up')
  });
  await step('半批上传失败 → 旧指针逐字节不变', () => {
    const dir = freshFixture('half');
    const st = fakeOss();
    return withEnv(upEnv(dir), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc1) => {
        if (rc1 !== 0) return false;
        const oldPtr = Buffer.from(st.get(ossTool.pointerKey('beta')));
        const oldId = JSON.parse(oldPtr.toString('utf8')).buildId;
        patchSource(dir, 'dungeons.json', (j) => { j.newDungeons[0].nameCn = '第二版名字'; });
        st.counts.PUT = 0;
        st.failPutAt = 3;
        return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc2) => {
          ossTool.setTransportForTest(null);
          const nowPtr = st.get(ossTool.pointerKey('beta'));
          return rc2 === 1 && Buffer.compare(oldPtr, nowPtr) === 0
            && JSON.parse(nowPtr.toString('utf8')).buildId === oldId;
        });
      });
    });
  }, () => '半批发出去了或指针被换');
  await step('远端同一路径内容不同 → 报警停发，不覆写', () => {
    const dir = freshFixture('immut');
    const st = fakeOss();
    return withEnv(upEnv(dir), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc1) => {
        if (rc1 !== 0) return false;
        const built = JSON.parse(st.get(ossTool.pointerKey('beta')).toString('utf8'));
        const victim = ossTool.buildPrefix('beta', built.buildId) + 'dungeons/index.json';
        const before = Buffer.from(st.get(victim));
        st.set(victim, Buffer.from(before.toString('utf8').replace('"product": "wow-forever-mini"', '"product": "tampered-by-someone"')), 'public, max-age=31536000, immutable');
        st.counts.PUT = 0;
        const tampered = Buffer.from(st.get(victim));
        return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc2) => {
          ossTool.setTransportForTest(null);
          return rc2 === 1 && st.counts.PUT === 0 && Buffer.compare(tampered, st.get(victim)) === 0
            && Buffer.compare(tampered, before) !== 0;
        });
      });
    });
  }, () => '把别人的字节盖掉了');
  await step('同 id 批次重复上传不重写任何文件（幂等）', () => {
    const dir = freshFixture('idemp');
    const st = fakeOss();
    return withEnv(upEnv(dir), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc1) => {
        if (rc1 !== 0) return false;
        st.counts.PUT = 0;
        return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false }).then((rc2) => {
          ossTool.setTransportForTest(null);
          return rc2 === 0 && st.counts.PUT <= 1;
        });
      });
    });
  }, () => '第二次上传重写了批次');

  /* ================= 7·5 素材通道（M02）================= */
  process.stdout.write('\n素材通道：图片不可变，但素材台账必须能重导\n');
  const asEnv = (dir) => Object.assign({}, NO_MARK, fixtureEnv(dir), {
    WOW_ALLOW_CROSS_CREDS: '1', WOW_OSS_ENV: F, WOW_MINI_BUILD: path.join(dir, 'oss-build-as')
  });
  const assetKeys = (st) => Array.from(st.objs.keys()).filter((k) => k.indexOf('/assets/') >= 0);
  const assetLifecycle = await (async () => {
    const dir = freshFixture('assets');
    const st = fakeOss();
    const ledKey = () => assetKeys(st).filter((k) => /\/assets\/index\.json$/.test(k))[0];
    return withEnv(asEnv(dir), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdAssets('beta', { dryRun: false }).then((rc1) => {
        if (rc1 !== 0) return { ok: false, why: '第一次发素材就 rc=' + rc1 };
        const keys = assetKeys(st);
        const imgs = keys.filter((k) => !/\/index\.json$/.test(k));
        const badType = imgs.filter((k) => {
          const want = /\.webp$/.test(k) ? 'image/webp' : /\.png$/.test(k) ? 'image/png' : 'image/jpeg';
          return st.objs.get(k).contentType !== want;
        });
        if (badType.length) return { ok: false, why: 'Content-Type 不对：' + badType[0] + ' → ' + st.objs.get(badType[0]).contentType };
        const badCache = imgs.filter((k) => st.objs.get(k).cacheControl.indexOf('immutable') < 0);
        if (badCache.length) return { ok: false, why: '图片没带 immutable：' + badCache[0] };
        if (st.objs.get(ledKey()).cacheControl.indexOf('max-age=60') < 0) return { ok: false, why: '台账的缓存头不是短缓存' };
        /* 素材要按"就地显示"发：默认域名会给对象挂 Content-Disposition: attachment，
           模拟器里的 <image> 照渲染、真机不一定，所以 inline 必须真的写进对象元数据 */
        const noDisp = imgs.filter((k) => st.objs.get(k).contentDisposition !== 'inline');
        if (noDisp.length) return { ok: false, why: noDisp.length + ' 张图没带 Content-Disposition: inline，例：' + noDisp[0] };
        st.counts.PUT = 0;
        return ossTool.cmdAssets('beta', { dryRun: false }).then((rc2) => {
          /* PUT 必须是 0：元数据比对只要写错（比如两边格式不同），每次发素材就会全量重传一遍 */
          if (rc2 !== 0 || st.counts.PUT !== 0) return { ok: false, why: '重发不幂等 rc=' + rc2 + ' PUT=' + st.counts.PUT };
          /* 素材集变小（这座本不再引用原画）：图片一张没动，只有台账要重写。
             这一条就是 2026-10-22 加技能图标时踩的坑——台账被当成不可变对象拦下，rc=1。 */
          patchSource(dir, 'dungeons.json', (j) => { j.newDungeons[0].art = null; });
          st.counts.PUT = 0;
          const before = Buffer.from(st.objs.get(ledKey()).buf);
          return ossTool.cmdAssets('beta', { dryRun: false }).then((rc3) => {
            const after = st.objs.get(ledKey()).buf;
            return {
              ok: rc3 === 0 && st.counts.PUT === 1 && Buffer.compare(before, after) !== 0,
              why: '台账重导：rc=' + rc3 + ' PUT=' + st.counts.PUT + ' 字节变了=' + (Buffer.compare(before, after) !== 0)
            };
          });
        });
      });
    }).finally(() => ossTool.setTransportForTest(null));
  })();
  ok('正路：按扩展名带 Content-Type、图片 immutable 一年、重发幂等、素材集变了台账能重导', assetLifecycle.ok, assetLifecycle.why);

  const assetImm = await (async () => {
    const dir = freshFixture('asimm');
    const st = fakeOss();
    return withEnv(asEnv(dir), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdAssets('beta', { dryRun: false }).then(() => {
        const victim = assetKeys(st).filter((k) => /\/icons\/.*\.jpg$/.test(k))[0];
        const before = Buffer.from(st.objs.get(victim).buf);
        st.set(victim, Buffer.from('有人换过这张图'), 'public, max-age=31536000, immutable', 'image/jpeg');
        const tampered = Buffer.from(st.objs.get(victim).buf);
        st.counts.PUT = 0;
        return ossTool.cmdAssets('beta', { dryRun: false }).then((rc) => ({
          ok: rc === 1 && st.counts.PUT === 0 && Buffer.compare(tampered, st.objs.get(victim).buf) === 0
            && Buffer.compare(tampered, before) !== 0,
          why: 'rc=' + rc + ' PUT=' + st.counts.PUT
        }));
      });
    }).finally(() => ossTool.setTransportForTest(null));
  })();
  ok('反例：同名图片远端字节不同 → 判冲突、一个字节都不覆写', assetImm.ok, assetImm.why);

  /* ================= 7. 回滚核实目标批次 ================= */
  process.stdout.write('\n回滚：先核目标批次完整，再动指针\n');
  async function twoBatches() {
    const dir = freshFixture('rb');
    const st = fakeOss();
    await withEnv(upEnv(dir), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false });
    });
    const a = JSON.parse(st.get(ossTool.pointerKey('beta')).toString('utf8'));
    patchSource(dir, 'dungeons.json', (j) => { j.newDungeons[0].nameCn = '回滚测试第二版'; });
    await withEnv(upEnv(dir), () => {
      ossTool.setTransportForTest(st.transport);
      return ossTool.cmdUpload('beta', { dryRun: false, yesRelease: false });
    });
    const b = JSON.parse(st.get(ossTool.pointerKey('beta')).toString('utf8'));
    ossTool.setTransportForTest(null);
    return { dir, st, a, b };
  }
  const rollbackTo = (ctx, to) => withEnv(upEnv(ctx.dir), () => {
    ossTool.setTransportForTest(ctx.st.transport);
    return ossTool.cmdRollback('beta', { to, yesRelease: false }).then((rc) => {
      ossTool.setTransportForTest(null);
      return rc;
    });
  });

  await step('正路：回滚到上一批 → 指针逐字节等于该批自带清单', () => twoBatches().then(async (ctx) => {
    const ptrBefore = Buffer.from(ctx.st.get(ossTool.pointerKey('beta')));
    const selfA = ctx.st.get(ossTool.buildPrefix('beta', ctx.a.buildId) + 'manifest.json');
    const rc = await rollbackTo(ctx, ctx.a.buildId);
    const ptrAfter = ctx.st.get(ossTool.pointerKey('beta'));
    return rc === 0 && Buffer.compare(Buffer.from(ptrAfter), Buffer.from(selfA)) === 0;
  }), () => '回滚没指到 A 批');
  await step('反例：目标批次缺一个详情文件 → 拒绝且指针字节不变', () => twoBatches().then(async (ctx) => {
    const ptrBefore = Buffer.from(ctx.st.get(ossTool.pointerKey('beta')));
    const firstId = JSON.parse(fs.readFileSync(path.join(previewOf(ctx.dir), 'dungeons.json'), 'utf8')).newDungeons[0].id;
    const victim = ossTool.buildPrefix('beta', ctx.a.buildId) + 'dungeons/detail/' + firstId + '.json';
    ctx.st.objs.delete(victim);
    const rc = await rollbackTo(ctx, ctx.a.buildId);
    return rc === 1 && Buffer.compare(ptrBefore, Buffer.from(ctx.st.get(ossTool.pointerKey('beta')))) === 0;
  }), () => '半批被激活了');
  await step('反例：目标批次 files.json 哈希与自带清单不符 → 拒绝', () => twoBatches().then(async (ctx) => {
    const ptrBefore = Buffer.from(ctx.st.get(ossTool.pointerKey('beta')));
    const k = ossTool.buildPrefix('beta', ctx.a.buildId) + 'files.json';
    const orig = Buffer.from(ctx.st.get(k));
    ctx.st.set(k, Buffer.from(orig.toString('utf8').replace('"cacheControl"', '"x":1,"cacheControl"')), 'public, max-age=31536000, immutable');
    const rc = await rollbackTo(ctx, ctx.a.buildId);
    ctx.st.set(k, orig, 'public, max-age=31536000, immutable');
    return rc === 1 && Buffer.compare(ptrBefore, Buffer.from(ctx.st.get(ossTool.pointerKey('beta')))) === 0;
  }), () => '哈希不符却回滚成功');
  await step('反例：--to 与该批清单里的 buildId 不一致 → 拒绝', () => twoBatches().then(async (ctx) => {
    const ptrBefore = Buffer.from(ctx.st.get(ossTool.pointerKey('beta')));
    const ghost = 'ffffffffffff';
    const bad = JSON.parse(ctx.st.get(ossTool.buildPrefix('beta', ctx.a.buildId) + 'manifest.json').toString('utf8'));
    bad.buildId = 'eeeeeeeeeeee';
    ctx.st.set(ossTool.buildPrefix('beta', ghost) + 'manifest.json', Buffer.from(JSON.stringify(bad, null, 1) + '\n'));
    const rc = await rollbackTo(ctx, ghost);
    return rc === 1 && Buffer.compare(ptrBefore, Buffer.from(ctx.st.get(ossTool.pointerKey('beta')))) === 0;
  }), () => '清单 ID 对不上也照指');
  await step('反例：目标批是另一个环境的清单 → 拒绝', () => twoBatches().then(async (ctx) => {
    const ptrBefore = Buffer.from(ctx.st.get(ossTool.pointerKey('beta')));
    const other = JSON.parse(ctx.st.get(ossTool.buildPrefix('beta', ctx.a.buildId) + 'manifest.json').toString('utf8'));
    other.env = 'release';
    other.namespace = 'wow/release/v1';
    ctx.st.set(ossTool.buildPrefix('beta', ctx.a.buildId) + 'manifest.json', Buffer.from(JSON.stringify(other, null, 1) + '\n'));
    const rc = await rollbackTo(ctx, ctx.a.buildId);
    return rc === 1 && Buffer.compare(ptrBefore, Buffer.from(ctx.st.get(ossTool.pointerKey('beta')))) === 0;
  }), () => '跨环境清单被当成指针');

  /* ================= 8. verify 收紧到字节 ================= */
  process.stdout.write('\n校验：指针必须是批次自带清单的逐字节副本\n');
  await step('verify 正路 rc0 且逐文件回读整批', () => twoBatches().then(async (ctx) => {
    const rc = await withEnv(upEnv(ctx.dir), () => {
      ossTool.setTransportForTest(ctx.st.transport);
      return ossTool.cmdVerify('beta').then((v) => { ossTool.setTransportForTest(null); return v; });
    });
    return rc === 0;
  }), () => 'verify 不绿');
  await step('反例：线上指针被改了 1 个字节 → verify 非 0', () => twoBatches().then(async (ctx) => {
    const k = ossTool.pointerKey('beta');
    const b = Buffer.from(ctx.st.get(k));
    ctx.st.set(k, Buffer.from(b.toString('utf8').replace('"schemaVersion": 1', '"schemaVersion": 2')), 'public, max-age=60, must-revalidate');
    return withEnv(upEnv(ctx.dir), () => {
      ossTool.setTransportForTest(ctx.st.transport);
      return ossTool.cmdVerify('beta').then((rc) => { ossTool.setTransportForTest(null); return rc !== 0; });
    });
  }), () => '指针被篡改却报绿');

  /* ================= 9. 客户端契约 ================= */
  process.stdout.write('\n契约：oss-manifest 的真实校验、缓存语义与版本信号\n');
  const envRoot = path.join(good.envDir, 'oss-build', 'beta');
  const batchRoot = path.join(envRoot, 'builds', man.buildId);
  const idxNeedle = '/' + man.fetch.dungeonIndex.path;
  const rawPut = (base, rel, buf) => { net.map[base + rel] = { data: JSON.parse(buf.toString('utf8')), header: { ETag: '"' + md5u(buf) + '"' } }; };
  function serve(root, m) {
    net.map = {};
    const base = oss.OSS_ORIGIN + '/' + oss.NAMESPACES[m.env] + '/';
    const readBuf = (rel) => fs.readFileSync(path.join(root, rel));
    net.map[oss.pointerUrl(m.env)] = { data: m, header: {} };
    rawPut(base, m.bundle.path, readBuf(m.bundle.path));
    Object.keys(m.fetch).forEach((k) => rawPut(base, m.fetch[k].path, readBuf(m.fetch[k].path)));
    idx.items.forEach((it) => {
      rawPut(base, 'builds/' + m.buildId + '/' + it.detailPath, readBuf('builds/' + m.buildId + '/' + it.detailPath));
      rawPut(base, 'builds/' + m.buildId + '/' + it.lootPath, readBuf('builds/' + m.buildId + '/' + it.lootPath));
    });
    /* 职业法术片与天赋片也要能被"取到"，否则契约测试只能测副本那两条路 */
    JSON.parse(readBuf('builds/' + m.buildId + '/spells/classes.json').toString('utf8')).classes.forEach((it) => {
      rawPut(base, 'builds/' + m.buildId + '/' + it.shardPath, readBuf('builds/' + m.buildId + '/' + it.shardPath));
    });
    JSON.parse(readBuf('builds/' + m.buildId + '/classes/index.json').toString('utf8')).classes
      .filter((it) => it.shardPath).forEach((it) => {
        rawPut(base, 'builds/' + m.buildId + '/' + it.shardPath, readBuf('builds/' + m.buildId + '/' + it.shardPath));
      });
    return base;
  }
  const servedIndex = serve(envRoot, man);

  await step('指针取到就是 live 且带 buildId', () => oss.loadPointer().then((p) => p.source === 'live' && p.manifest.buildId === man.buildId));
  const r1 = await oss.loadKey('dungeonIndex');
  ok('索引 live 且 data.buildId 与指针同批', r1.source === 'live' && r1.data.buildId === man.buildId, r1.source);
  ok('界面拿得到核对日期（与指针同一个值，不是写死的）',
    !!(r1.factDates && r1.factDates.latest === man.factDates.latest), JSON.stringify(r1.factDates));
  const r1b = await oss.loadKey('dungeonIndex');
  await step('同批第二次读：批次是当前批 → 仍算 live 并标 cacheHit，不再谎报"离线缓存"', () =>
    r1b.source === 'live' && r1b.cacheHit === true, JSON.stringify({ s: r1b.source, c: r1b.cacheHit }));
  ok('同批第二次读没有重复下载索引', hitsTo(idxNeedle) === 1, '索引被取了 ' + hitsTo(idxNeedle) + ' 次');

  const item = r1.data.items.filter((x) => x.id === 'ragefire-chasm')[0];
  let det = null; let loot = null;
  await step('点详情才取详情文件（' + item.detailBytes + ' B）', async () => {
    det = await oss.loadDungeonDetail(item, r1.batch);
    return det.source === 'live' && det.data.dungeon.id === 'ragefire-chasm';
  }, () => (det ? det.source : '抛出'));
  await step('掉落在再下一级', async () => {
    loot = await oss.loadDungeonLoot(item, r1.batch);
    return loot.source === 'live' && loot.data.drops.length > 0;
  }, () => (loot ? loot.source : '抛出'));
  ok('掉落没有百分比', !!loot && loot.data.drops.every((d) => !/\d+(\.\d+)?\s*%/.test(JSON.stringify(d))));

  /* —— M02-2 客户端契约：职业名单 → 单片，路径与校验值都从名单条目现推 —— */
  const spNeedle = '/' + man.fetch.spellClasses.path;
  const rsp = await oss.loadKey('spellClasses');
  ok('职业名单走指针就是 live', rsp.source === 'live' && rsp.data.buildId === man.buildId
    && rsp.data.classes.length === 9, rsp.source + ' / ' + (rsp.error && rsp.error.message));
  const spc = rsp.data.classes.filter((c) => c.classId === 'priest')[0];
  let spRes = null;
  await step('点一个职业才取那一片，取到的条数与名单说的一致', async () => {
    spRes = await oss.loadSpellClass(spc, rsp.batch);
    return spRes.source === 'live' && spRes.data.classId === 'priest' && spRes.data.spells.length === spc.count;
  }, () => (spRes ? spRes.source + ' ' + (spRes.error && spRes.error.message) : '抛出'));
  ok('只取了选中的那个职业，其余八片没下', hitsTo('/spells/class/') === 1, '取了 ' + hitsTo('/spells/class/') + ' 片');
  await step('同批第二次读同一职业 → cacheHit 且不重复下载', async () => {
    const again = await oss.loadSpellClass(spc, rsp.batch);
    return again.source === 'live' && again.cacheHit === true && hitsTo('/spells/class/') === 1;
  }, () => '又下了一遍');
  await step('反例：名单里的 shardPath 被改成路径穿越 → 不发请求', async () => {
    clearStore();
    const bad = Object.assign({}, spc, { shardPath: '../../../etc/passwd' });
    const r = await oss.loadSpellClass(bad, rsp.batch);
    const before = hitsTo('/spells/class/');
    return r.source === 'none' && !!r.integrityError && hitsTo('/spells/class/') === before;
  }, '坏路径照样发了请求');
  await step('反例：片里 classId 与请求的不是同一个（串包）→ 判失败', async () => {
    clearStore();
    const key = servedIndex + 'builds/' + man.buildId + '/spells/class/paladin.json';
    const orig = net.map[key];
    net.map[key] = { data: Object.assign({}, orig.data, { classId: 'priest' }), header: orig.header };
    const r = await oss.loadSpellClass(Object.assign({}, spc, {
      classId: 'paladin', shardPath: 'spells/class/paladin.json'
    }), rsp.batch);
    net.map[key] = orig;
    clearStore();
    return r.source === 'none' && !!r.integrityError && /ID 是 priest/.test(String(r.error && r.error.message));
  }, '串了职业还当正常数据返回');
  ok('职业名单本身只取了一次（换职业不重复下名单）', hitsTo(spNeedle) === 1, '取了 ' + hitsTo(spNeedle) + ' 次');
  const cr = await oss.loadKey('classIndex');
  await step('职业索引走指针就是 live，种族与职业条数自洽', () => cr.source === 'live'
    && cr.data.counts.races === cr.data.races.length && cr.data.counts.classes === cr.data.classes.length,
    () => (cr.error ? cr.error.message : cr.source));
  const wEntry = cr.data.classes.filter((c) => c.classId === 'warrior')[0];
  let tr = null;
  await step('点一个职业才取那份天赋树，节点坐标齐全', async () => {
    tr = await oss.loadTalentClass(wEntry, cr.batch);
    return tr.source === 'live' && tr.data.classId === 'warrior' && tr.data.trees.length === 3
      && tr.data.trees.every((t) => t.nodes.every((n) => Number.isInteger(n.tier)));
  }, () => (tr ? tr.source + ' ' + (tr.error && tr.error.message) : '抛出'));
  ok('只取了选中的那个职业的天赋，其余八份没下', hitsTo('/talents/class/') === 1, '取了 ' + hitsTo('/talents/class/') + ' 份');
  await step('反例：名单里天赋路径被改成路径穿越 → 不发请求', async () => {
    clearStore();
    const before = hitsTo('/talents/class/');
    const r = await oss.loadTalentClass(Object.assign({}, wEntry, { shardPath: '../../../etc/x' }), cr.batch);
    return r.source === 'none' && !!r.integrityError && hitsTo('/talents/class/') === before;
  }, '坏路径照样发了请求');
  const gr = await oss.loadKey('guide');
  await step('指南壳走指针就是 live，空内容也合法', () => gr.source === 'live'
    && Array.isArray(gr.data.macros) && Array.isArray(gr.data.addons),
    () => (gr.error ? gr.error.message : gr.source));
  const lr = await oss.loadKey('lootIndex');
  await step('掉落反查表走指针就是 live，行数是自洽的', () => lr.source === 'live'
    && lr.data.counts.rows === lr.data.dungeons.reduce((s, d) => s + d.rows.length, 0),
    () => (lr.error ? lr.error.message : lr.source));
  await step('反例：表被改成少一列（列名与行内容对不上）→ 客户端不当 live 端给界面', async () => {
    clearStore();
    const key = servedIndex + man.fetch.lootIndex.path;
    const orig = net.map[key];
    const cut = JSON.parse(JSON.stringify(orig.data));
    cut.cols = cut.cols.slice(0, 5);
    net.map[key] = { data: cut, header: orig.header };
    const r = await oss.loadKey('lootIndex');
    net.map[key] = orig;
    clearStore();
    return !!r.integrityError && r.source !== 'live';
  }, '结构不对仍报实时数据');
  await step('反例：线上字节被换（Content-MD5 与清单不符）→ 不当 live', async () => {
    clearStore();
    const key = servedIndex + man.fetch.spellClasses.path;
    const orig = net.map[key];
    net.map[key] = { data: orig.data, header: { 'Content-MD5': 'ZmFrZWZhYWtlZmFrZWZhYWtlZmE9PQ==', 'Content-Length': String(orig.data.length) } };
    const r = await oss.loadKey('spellClasses');
    net.map[key] = orig;
    clearStore();
    return !!r.integrityError && r.source !== 'live';
  }, 'MD5 对不上仍报 live');
  clearStore();
  await step('逐文件哈希表能取回且同批（构建端 verify 与人工排障用这份）', async () => {
    const p1 = await oss.loadPointer();
    const bd = await oss.loadBundle(p1.manifest);
    return bd.source === 'live' && bd.data.buildId === man.buildId
      && Object.keys(bd.data.files).length === man.counts.files - 2;
  }, () => '取不回或条数不等于本批数据文件数（counts.files 减 files.json 与 manifest）');
  ok('批次内路径只有一种拼法', oss.batchPath(man, 'dungeons/x.json') === 'builds/' + man.buildId + '/dungeons/x.json');
  const asb = { env: man.env, buildId: man.buildId, assets: man.assets };
  ok('素材地址只能落在 assets/ 下（art 与图标各一种拼法）',
    oss.assetUrl(asb, 'art/dungeons/ragefire-chasm.webp') === oss.OSS_ORIGIN + '/' + oss.NAMESPACES[man.env] + '/assets/art/dungeons/ragefire-chasm.webp'
      && oss.iconUrl(asb, 'inv_misc_head_dwarf_01').indexOf('/assets/icons/inv_misc_head_dwarf_01.jpg') > 0,
    oss.assetUrl(asb, 'art/dungeons/ragefire-chasm.webp'));
  ok('反例：素材路径带 ../ → 不拼', oss.assetUrl(asb, '../etc/passwd') === '');
  ok('反例：素材路径还是站内 img/ → 不拼（那是网页端地址，小程序必 404）',
    oss.assetUrl(asb, 'img/art/x.webp') === '' && oss.assetUrl(asb, 'http://evil/x.jpg') === '');
  ok('反例：图标键带路径分隔符 → 不拼', oss.iconUrl(asb, 'a/b') === '' && oss.iconUrl(asb, '') === '');
  ok('指针里的 assets 段说清了素材数量与缺失数（不是"没图"而是"这批引了 N 张、缺 M 张"）',
    man.assets && man.assets.count > 700 && man.assets.bytes > 0 && typeof man.assets.missing === 'number',
    JSON.stringify(man.assets && { c: man.assets.count, b: man.assets.bytes, m: man.assets.missing }));
  await step('loadKey 把批次上下文一起交给页面（详情不必另取 manifest）', () =>
    r1.batch && r1.batch.buildId === man.buildId && r1.batch.env === man.env && typeof r1.batch.factDates === 'object');
  await step('详情固定用索引那一批：中途换指针也不混版', () => {
    const other = JSON.parse(JSON.stringify(man));
    other.buildId = 'bbbbbbbbbbbb';
    other.bundle.path = other.bundle.path.replace(man.buildId, 'bbbbbbbbbbbb');
    Object.keys(other.fetch).forEach((k) => { other.fetch[k].path = other.fetch[k].path.replace(man.buildId, 'bbbbbbbbbbbb'); });
    net.map[oss.pointerUrl(other.env)] = { data: other, header: {} };
    return oss.loadDungeonDetail(item, r1.batch).then((d) => {
      net.map[oss.pointerUrl(other.env)] = { data: man, header: {} };
      return d.source === 'live' && d.buildId === man.buildId;
    });
  }, () => '换了指针就混版');
  await step('详情条目里藏 ../ 路径 → 拒绝请求，不发 URL', () => {
    const before = net.log.length;
    const evil = Object.assign({}, item, { detailPath: '../../../../etc/passwd' });
    return oss.loadDungeonDetail(evil, r1.batch).then((d) => net.log.length === before && d.source !== 'live');
  }, () => '越出批次目录也照取');

  /* —— 篡改一个字段但保持有效 JSON、buildId 也对：必须不返回 live —— */
  await step('反例：索引内容被改一个字段（buildId 没变）→ 不返回 live', () => {
    const rel = man.fetch.dungeonIndex.path;
    const url = servedIndex + rel;
    const tampered = JSON.parse(fs.readFileSync(path.join(envRoot, rel), 'utf8'));
    tampered.items[0].nameCn = '被改过的副本名';
    net.map[url] = { data: tampered, header: { ETag: '"' + md5u(Buffer.from(JSON.stringify(tampered, null, 1) + '\n')) + '"' } };
    clearStore();
    return oss.loadKey('dungeonIndex', { fallback: { items: [], meta: { snapshot: true } } }).then((r) => {
      serve(envRoot, man); clearStore();
      return r.source === 'snapshot' && r.integrityError === true;
    });
  }, () => '校验没生效');
  await step('反例：详情文件被改一个字段 → 不返回 live', () => {
    const rel = 'builds/' + man.buildId + '/' + item.detailPath;
    const url = servedIndex + rel;
    const tampered = JSON.parse(fs.readFileSync(path.join(envRoot, rel), 'utf8'));
    tampered.dungeon.bosses[0].nameCn = '被改过的首领名';
    net.map[url] = { data: tampered, header: { ETag: '"' + md5u(Buffer.from(JSON.stringify(tampered, null, 1) + '\n')) + '"' } };
    clearStore();
    return oss.loadDungeonDetail(item, r1.batch).then((r) => { serve(envRoot, man); clearStore(); return r.source !== 'live'; });
  }, () => '详情没校验');
  await step('反例：meta 少了 ETag 响应头 → 不返回 live', () => {
    const url = servedIndex + man.fetch.meta.path;
    const keep = net.map[url];
    net.map[url] = { data: keep.data, header: {} };
    clearStore();
    return oss.loadKey('meta', { fallback: { coverage: {} } }).then((r) => { net.map[url] = keep; clearStore(); return r.source !== 'live'; });
  }, () => '没有 ETag 也当实时');
  await step('反例：分片 kind/id 与请求不符 → 不返回 live', () => {
    const rel = 'builds/' + man.buildId + '/' + item.lootPath;
    const url = servedIndex + rel;
    const other = JSON.parse(fs.readFileSync(path.join(envRoot, 'builds/' + man.buildId + '/' + idx.items[1].lootPath), 'utf8'));
    net.map[url] = { data: other, header: { ETag: '"' + md5u(fs.readFileSync(path.join(envRoot, 'builds/' + man.buildId + '/' + idx.items[1].lootPath))) + '"' } };
    clearStore();
    return oss.loadDungeonLoot(item, r1.batch).then((r) => { serve(envRoot, man); clearStore(); return r.source !== 'live'; });
  }, () => '拿错本子的掉落也认了');

  /* —— 混版：指针指向不存在的批次 —— */
  const fake = JSON.parse(JSON.stringify(man));
  fake.buildId = 'ffffffffffff';
  fake.bundle.path = fake.bundle.path.replace(man.buildId, 'ffffffffffff');
  Object.keys(fake.fetch).forEach((k) => { fake.fetch[k].path = fake.fetch[k].path.replace(man.buildId, 'ffffffffffff'); });
  net.map[oss.pointerUrl(fake.env)] = { data: fake, header: {} };
  clearStore();
  const r2 = await oss.loadKey('dungeonIndex', { fallback: { items: [], meta: { snapshot: true } } });
  ok('指针批次与文件批次不一致 → 判失败并回退快照', r2.source === 'snapshot', r2.source);
  ok('回退时界面上有 source 可标，不静默', r2.source !== 'live' && !!r2.pointerSource);

  /* —— 断网语义 —— */
  serve(envRoot, man); clearStore();
  await oss.loadKey('dungeonIndex');
  net.map = {};
  const r3 = await oss.loadKey('dungeonIndex');
  await step('指针都取不到（真断网）但有本批缓存 → cache（这才叫离线降级）', () =>
    r3.source === 'cache' && r3.pointerSource === 'cache' && !!r3.data, JSON.stringify({ s: r3.source, p: r3.pointerSource }));

  serve(envRoot, man); clearStore(); net.map = {};
  const r4 = await oss.loadKey('dungeonIndex', { fallback: { items: [], meta: { snapshot: true } } });
  ok('断网且无缓存 → snapshot 且明说', r4.source === 'snapshot' && r4.data.meta.snapshot === true, r4.source);
  const r5 = await oss.loadKey('dungeonIndex');
  ok('断网且没有快照兜底 → none（不许假装有条目）', r5.source === 'none' && r5.data === null, r5.source);

  /* —— requiresUpdate / factDates 在四种状态下都得在 —— */
  const STATES = ['live', 'cache', 'snapshot', 'none'];
  await step('requiresUpdate / factDates / source 在四种状态下字段齐全（契约一致）', () => {
    const up = JSON.parse(JSON.stringify(man));
    up.minClientSchemaVersion = 99;
    serve(envRoot, up); clearStore();
    return oss.loadKey('dungeonIndex').then((a) => {
      const shapes = [{ r: a }];
      net.map = {};
      return oss.loadKey('dungeonIndex').then((b) => {
        const all = [a, b].concat([r4, r5]);
        return all.every((x) => x && x.requiresUpdate !== undefined
          && ('factDates' in x) && STATES.indexOf(x.source) >= 0);
      });
    });
  }, () => '某一级缺字段');
  await step('数据契约比客户端新 → requiresUpdate', () => oss.loadKey('dungeonIndex').then((x) => x.requiresUpdate === true),
    () => '升级信号丢了');
  await step('旧客户端命中缓存时也要看到升级提示', () => {
    clearStore();
    const up = JSON.parse(JSON.stringify(man));
    up.minClientSchemaVersion = 99;
    serve(envRoot, up);
    return oss.loadKey('dungeonIndex').then(() => oss.loadKey('dungeonIndex').then((x) =>
      x.requiresUpdate === true && x.cacheHit === true));
  }, () => '缓存命中把升级提示吃掉了');

  /* —— 坏指针要退回已有的好指针 —— */
  await step('反例：线上指针结构坏了但本地有好指针 → 用旧的并明说，不许当空数据', () => {
    serve(envRoot, man); clearStore();
    return oss.loadPointer().then(() => {
      const junk = JSON.parse(JSON.stringify(man));
      junk.fetch = null;
      net.map[oss.pointerUrl(junk.env)] = { data: junk, header: {} };
      return oss.loadKey('dungeonIndex', { fallback: { items: [] } }).then((r) =>
        r.source === 'cache' && r.buildId === man.buildId && !!r.data && r.pointerSource === 'invalid');
    });
  }, () => '坏指针把有缓存的用户打回快照');
  await step('指针字段非法（buildId 格式不对）→ 无缓存时报 invalid 并走快照', () => {
    clearStore();
    const junk = JSON.parse(JSON.stringify(man));
    junk.buildId = 'NOT-A-HASH';
    net.map[oss.pointerUrl(junk.env)] = { data: junk, header: {} };
    return oss.loadKey('dungeonIndex', { fallback: { items: [], meta: { snapshot: true } } }).then((r) => {
      serve(envRoot, man); clearStore();
      return r.source === 'snapshot' && r.pointerSource === 'invalid';
    });
  }, () => '非法指针被当成正常空数据');

  /* —— 旧批缓存回收 —— */
  clearStore();
  serve(envRoot, man);
  store[oss.cacheKey('dungeonIndex', 'aaaaaaaaaaaa')] = { data: 1, at: 1 };
  store[oss.cacheKey('glossary', 'bbbbbbbbbbbb')] = { data: 1, at: 1 };
  const pointerKeySaved = oss.CACHE_PREFIX + 'pointer@' + oss.ACTIVE_ENV;
  const otherEnvPointer = oss.CACHE_PREFIX + 'pointer@release';
  store[pointerKeySaved] = { manifest: man, at: Date.now() };
  store[otherEnvPointer] = { manifest: man, at: Date.now() };
  await oss.loadPointer();
  ok('换批后旧批缓存被清（storage 只有 10 MB）',
    store[oss.cacheKey('dungeonIndex', 'aaaaaaaaaaaa')] === undefined && store[oss.cacheKey('glossary', 'bbbbbbbbbbbb')] === undefined);
  ok('两个环境的指针缓存都没被当成旧批数据误删',
    store[pointerKeySaved] !== undefined && store[otherEnvPointer] !== undefined);
  ok('SOURCE_TEXT 四态都有中文说法，界面直接能用',
    oss.SOURCE_TEXT.live === '实时数据' && !!oss.SOURCE_TEXT.cache && !!oss.SOURCE_TEXT.snapshot && !!oss.SOURCE_TEXT.none,
    JSON.stringify(oss.SOURCE_TEXT));
  await step('界面一句话能说清"实时但省流量"与"离线降级"的区别', () =>
    typeof oss.sourceLabel === 'function' && /缓存/.test(oss.sourceLabel({ source: 'live', cacheHit: true }))
    && /离线/.test(oss.sourceLabel({ source: 'cache' })), () => '缺 sourceLabel');

  process.stdout.write('\n' + (fail ? '✗ ' : '') + '通过 ' + pass + ' / 失败 ' + fail + '\n');
  process.exit(fail ? 1 : 0);
})().catch((e) => {
  process.stdout.write('\n✗ 测试自身异常：' + (e && e.stack ? e.stack : e) + '\n');
  process.exit(1);
});
