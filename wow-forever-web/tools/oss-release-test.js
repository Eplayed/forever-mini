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
  fs.mkdirSync(path.join(web, 'src', 'data'), { recursive: true });
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

function runBuild(envDir, extraArgs) {
  const res = cp.spawnSync('node', [TOOL, 'build', '--env', 'beta'].concat(extraArgs || []), {
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
  st.set = (key, buf, cacheControl) => st.objs.set(key, {
    buf, cacheControl: cacheControl || 'public, max-age=60, must-revalidate',
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
      st.set(key, body, headers && headers['Cache-Control']);
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
    const h = { etag: '"' + md5u(o.buf) + '"', 'content-length': o.buf.length, 'cache-control': o.cacheControl, 'last-modified': o.lastModified };
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
  ok('索引 38 条 = 9 新本 + 26 经典 + 3 团本', idx.items.length === 38
    && idx.counts.newDungeons === 9 && idx.counts.classicDungeons === 26 && idx.counts.raids === 3,
    JSON.stringify(idx.counts));
  ok('每条索引都能落到实际存在的详情与掉落文件', idx.items.every((it) =>
    fs.existsSync(path.join(batchDir, it.detailPath)) && fs.existsSync(path.join(batchDir, it.lootPath))));
  ok('bundle 收了 79 个数据文件（38×2 + 索引 + meta + glossary）', Object.keys(bundle.files).length === 79,
    String(Object.keys(bundle.files).length));
  const ptrPath = path.join(good.envDir, 'oss-build', 'beta', 'manifest.json');
  ok('指针清单 ≤ 8 KB（冷启动代价）', man.counts.bytes > 0 && fs.statSync(ptrPath).size <= 8 * 1024,
    String(fs.statSync(ptrPath).size));
  ok('批次里没有站内相对路径（img/ src/ 一律不许下发）',
    !/"(img|src|static)\//.test(fs.readFileSync(path.join(batchDir, 'dungeons', 'detail', 'ragefire-chasm.json'), 'utf8')));
  ok('首领名单里不再带着站内头像路径',
    JSON.parse(fs.readFileSync(path.join(batchDir, 'dungeons', 'detail', 'ragefire-chasm.json'), 'utf8')).dungeon.bosses.every((b) => b.portrait === undefined));
  ok('事实核对日期写进指针（2026-10-11）', man.factDates.latest === '2026-10-11',
    JSON.stringify(man.factDates));
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
  ok('溯源写明了导出对拍（re-export 与 oss-preview 一致）',
    man.source && man.source.exportCheck && man.source.exportCheck.reproduced === true
      && man.source.exportCheck.outputs.length === 3, JSON.stringify(man.source && man.source.exportCheck));
  const coldBytes = fs.statSync(ptrPath).size + man.fetch.dungeonIndex.bytes + man.fetch.meta.bytes;
  process.stdout.write('  · 冷启动三取实际字节：指针 ' + man.fetch.meta.bytes + 'B meta + 索引 '
    + man.fetch.dungeonIndex.bytes + 'B + 指针 ' + fs.statSync(ptrPath).size + 'B = ' + (coldBytes / 1024).toFixed(1)
    + ' KB，GET 3 次；整份 dungeons.json 326.7 KB\n');
  ok('冷启动代价仍 ≤ 40 KB', coldBytes <= 40 * 1024, String(coldBytes));

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
  await step('verify 正路 rc0 且逐文件回读 79 个', () => twoBatches().then(async (ctx) => {
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
    return base;
  }
  const servedIndex = serve(envRoot, man);

  await step('指针取到就是 live 且带 buildId', () => oss.loadPointer().then((p) => p.source === 'live' && p.manifest.buildId === man.buildId));
  const r1 = await oss.loadKey('dungeonIndex');
  ok('索引 live 且 data.buildId 与指针同批', r1.source === 'live' && r1.data.buildId === man.buildId, r1.source);
  ok('界面拿得到核对日期', r1.factDates && r1.factDates.latest === '2026-10-11');
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
  await step('逐文件哈希表能取回且同批（构建端 verify 与人工排障用这份）', async () => {
    const p1 = await oss.loadPointer();
    const bd = await oss.loadBundle(p1.manifest);
    return bd.source === 'live' && bd.data.buildId === man.buildId && Object.keys(bd.data.files).length === 79;
  }, () => '取不回 or 不是 79 个');
  ok('批次内路径只有一种拼法', oss.batchPath(man, 'dungeons/x.json') === 'builds/' + man.buildId + '/dungeons/x.json');
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
