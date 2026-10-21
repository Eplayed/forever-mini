#!/usr/bin/env node
/* 无限资料小程序 · OSS 分发层
   ------------------------------------------------------------------
   方案照搬 PoE 那条线（bucket 与「manifest 指针 + 逻辑键 + 索引/详情两级加载」），
   但把它踩过的三个坑一次修掉：
     1) PoE 是「直接覆盖同名文件」→ 传到一半失败，线上就是新清单配旧数据。
        这里改成先写不可变批次目录 builds/{buildId}/，全部校验通过后才最后换
        一份 manifest.json 指针；指针没换之前用户读到的还是上一批完整数据。
     2) PoE 的 manifest 拿不到就静默回退硬编码旧地址 → 用户读到旧数据还不显示。
        这里批次路径里带 buildId，客户端按清单里记的服务器 ETag 逐文件比对
        （见下方 integrity 段：入口文件比指针给的 ETag，按需分片比索引条目给的 ETag），
        对不上就整条当失败降级，并在界面标 live/cache/snapshot，不许静默。
     3) PoE 把「构建时间」当「数据更新时间」显示。
        这里清单里根本没有生成时间字段（2026-10-21 R1 改的：同 buildId 必须逐字节恒定，
        否则"不可变批次"每次重跑都会被自己的时间戳覆写一遍），数据的核对时间看
        factDates 和每条的 provenance，发布时刻看对象的服务端 Last-Modified。

   buildId 只由内容指纹决定：同一份基底重跑两次得到同一个目录、同样字节。
   零第三方依赖：OSS V1 签名自己用 node:crypto 算（本仓库没有 package.json，
   不给 tools/ 引 npm 依赖）。

   子命令
     node tools/oss-release.js build --env beta
     node tools/oss-release.js upload --env beta [--dry-run]
     node tools/oss-release.js verify --env beta
     node tools/oss-release.js list --env beta
     node tools/oss-release.js rollback --env beta --to <buildId>
     node tools/oss-release.js clean --env beta --yes-clean

   写授权（2026-10-21 R1 收紧，站主口径）
     upload / rollback / clean 是写 bucket 的动作，**不论凭证从哪来**，都必须显式带
     环境变量 WOW_ALLOW_CROSS_CREDS=1 才执行；只读（list / verify / --dry-run / build）
     不需要。目的不是区分钥匙归属，而是逼着每条写命令都被人工点过一次头。
     release 环境在此之上还要 --yes-release，clean 还要 --yes-clean。
   凭证解析顺序：环境变量 → $WOW_OSS_ENV → 仓库根 .oss-env → ../p2-database/auto_browser/.env
   仓库根不在小程序目录里，所以这份文件不可能被微信打包器带进代码包；
   for-mini/.oss-env 一律拒绝使用（.gitignore 挡不住打包）。密钥不入库、不打印。 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const cp = require('child_process');

const REPO = path.resolve(__dirname, '..', '..');
const WEB = path.resolve(__dirname, '..');
const MINI = path.join(REPO, 'for-mini');
const EXPORT_TOOL = path.join(__dirname, 'export-mini.js');

/* 路径每次调用现读，测试才能在同一进程里换夹具目录 */
const previewDir = () => process.env.WOW_MINI_PREVIEW || path.join(MINI, 'oss-preview');
const buildRoot = () => process.env.WOW_MINI_BUILD || path.join(MINI, 'oss-build');
const siteSrc = () => process.env.WOW_SITE_SRC || path.join(WEB, 'src');
const siteData = () => path.join(siteSrc(), 'data');
const localCredPath = () => process.env.WOW_OSS_LOCAL_ENV || path.join(REPO, '.oss-env');
const crossCredPath = () => process.env.WOW_OSS_CROSS_ENV || path.join(REPO, '..', 'p2-database', 'auto_browser', '.env');

const SCHEMA_VERSION = 1;
const PRODUCT = 'wow-forever-mini';
const NAMESPACES = { beta: 'wow/beta/v1', release: 'wow/release/v1' };
const DEFAULT_BUCKET = 'poe2-all-class';
const DEFAULT_REGION = 'oss-cn-hangzhou';
const WRITE_MARK = 'WOW_ALLOW_CROSS_CREDS';

/* 单文件体积上限：超了就是分片粒度错了，宁可构建失败也别把大文件推给手机 */
const BUDGET_KB = {
  manifest: 8,
  bundle: 64,
  'dungeons/index': 40,
  meta: 8,
  glossary: 200,
  detail: 32,
  loot: 64
};

/* 批次里暂时不往下发的字段：素材没上 OSS，界面拿到站内路径只会 404，
   所以这一层主动摘掉并在 manifest.droppedFields 里交代，不装作数据没有这项。 */
const DROPPED_DETAIL_FIELDS = [
  { field: 'art', reason: '客户端原画素材本轮没有传到 OSS，站内相对路径在小程序里打不开' },
  { field: 'bosses[].portrait', reason: '首领头像是站内 img/art/ 下的相对路径，素材批次没发，先摘掉' }
];
const ASSET_NOTE = 'drops[].iconKey 只是图标键，图标文件没有传到 OSS；界面要用图标得先发素材批次，拿不到就自绘，不许热链站内路径。';

const IMUTABLE_CACHE = 'public, max-age=31536000, immutable';
const POINTER_CACHE = 'public, max-age=60, must-revalidate';

const sha256 = (buf) => crypto.createHash('sha256').update(buf).digest('hex');
const md5Hex = (buf) => crypto.createHash('md5').update(buf).digest('hex').toUpperCase();
const md5B64 = (buf) => crypto.createHash('md5').update(buf).digest('base64');
const kb = (b) => (b / 1024).toFixed(1);
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const writeBuf = (p, buf) => {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, buf);
};
const dump = (obj) => Buffer.from(JSON.stringify(obj, null, 1) + '\n', 'utf8');
const isOfficial = (list) => (list || []).some((s) => String(s.type || '').indexOf('official') === 0 || String(s.type || '') === 'datamine_cn');

/* ---------- 1. 把 oss-preview 的三份成品切成一个批次 ---------- */

function collectFactDates(records) {
  const dates = [];
  let without = 0;
  records.forEach((rec) => {
    const own = (rec.provenance || []).map((p) => p.checkedAt).filter(Boolean).sort();
    if (!own.length) { without += 1; return; }
    own.forEach((d) => dates.push(d));
  });
  dates.sort();
  return {
    min: dates.length ? dates[0] : null,
    max: dates.length ? dates[dates.length - 1] : null,
    distinct: dates.length ? new Set(dates).size : 0,
    recordsWithoutDate: without
  };
}

/* 索引条目里就带详情/掉落的 ETag 与字节：客户端取分片时不必先下载 files.json
   才能校验（一次校验多一个 25 KB 请求不值得）。 */
function indexEntry(d) {
  return {
    id: d.id,
    kind: d.kind,
    nameCn: d.nameCn || null,
    nameEn: d.nameEn || null,
    nameCnConflict: d.nameCnConflict || null,
    levelRange: d.levelRange || null,
    levelRangeOfficial: d.levelRangeOfficial || null,
    faction: d.faction || null,
    zoneCn: d.zoneCn || null,
    partySize: d.partySize || null,
    partySizeAlt: d.partySizeAlt || null,
    sizeClaim: d.sizeClaim || null,
    level: d.level || 'L3',
    bossCount: (d.bosses || []).length,
    dropCount: (d.drops || []).length,
    hasRoute: (d.route || []).length > 0,
    detailPath: 'dungeons/detail/' + d.id + '.json',
    lootPath: 'dungeons/loot/' + d.id + '.json'
  };
}

function detailRecord(d) {
  const out = {};
  Object.keys(d).forEach((k) => {
    if (k === 'drops') return;
    if (DROPPED_DETAIL_FIELDS.some((x) => x.field === k)) return;
    out[k] = d[k];
  });
  if (Array.isArray(out.bosses)) {
    out.bosses = out.bosses.map((b) => {
      const o = {};
      Object.keys(b).forEach((k) => { if (k !== 'portrait') o[k] = b[k]; });
      return o;
    });
  }
  out.dropCount = (d.drops || []).length;
  out.lootPath = 'dungeons/loot/' + d.id + '.json';
  return out;
}

/* 导出产物 ↔ 基底对拍：在临时目录里把真源重导一遍，逐字节比 oss-preview。
   不这么办的话，指针溯源写的是 A（src/data 的哈希），发出去的却是 B（有人手改过的
   oss-preview），两边一致只证明一致，不证明它来自基底。 */
function reExportCompare() {
  const rels = ['meta.json', 'glossary.json', 'dungeons.json'];
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ossxchk-'));
  try {
    const web = path.join(tmp, 'wow-forever-web');
    fs.mkdirSync(path.join(web, 'tools'), { recursive: true });
    fs.copyFileSync(EXPORT_TOOL, path.join(web, 'tools', 'export-mini.js'));
    /* 导出层自己也有一道对拍（索引快照 ↔ 分发层索引），要把这份工具一起拷过去，
       否则临时目录里的 export-mini.js 会因为找不到参照而直接拒绝跑。 */
    fs.copyFileSync(path.join(__dirname, 'oss-release.js'), path.join(web, 'tools', 'oss-release.js'));
    fs.symlinkSync(siteSrc(), path.join(web, 'src'));
    let exportErr = '';
    try {
      cp.execFileSync('node', [path.join(web, 'tools', 'export-mini.js')], {
        encoding: 'utf8', maxBuffer: 8 * 1024 * 1024,
        /* 这道对拍只管"字节：源 → 导出产物"，快照↔索引那层一致性由 export-mini 自己在正式导出时查
           （oss-release-test.js 的 3·5 节直接测它）。这里关掉是为了让坏数据的红字
           由分发层自己的卡口报出来，而不是被上游那层的错误信息盖掉——归因比多跑一遍重要。 */
        env: Object.assign({}, process.env, { WOW_SNAPSHOT_CROSSCHECK: 'off' })
      });
    } catch (e) {
      const t = String(e.stderr || e.stdout || e.message || '');
      exportErr = t.split('\n').filter((x) => x.trim().indexOf('✗') === 0 || x.indexOf('失败') >= 0).slice(0, 3).join(' / ');
    }
    const outDir = path.join(tmp, 'for-mini', 'oss-preview');
    const diffs = [];
    const outputs = [];
    if (exportErr) return { diffs: ['基底重导出被导出层拒绝（源本身就不合规）：' + exportErr], outputs, tool: 'wow-forever-web/tools/export-mini.js' };
    if (!fs.existsSync(outDir)) return { diffs: ['重导出没有产出 oss-preview（export-mini.js 没跑成）'], outputs, tool: 'wow-forever-web/tools/export-mini.js' };
    rels.forEach((rel) => {
      const freshP = path.join(outDir, rel);
      const hereP = path.join(previewDir(), rel);
      if (!fs.existsSync(freshP) || !fs.existsSync(hereP)) { diffs.push(rel + '：一边不存在'); return; }
      const a = fs.readFileSync(freshP);
      const b = fs.readFileSync(hereP);
      outputs.push({ rel: 'oss-preview/' + rel, bytes: b.length, sha256: sha256(b) });
      if (!a.equals(b)) diffs.push(rel + '（重导出 ' + sha256(a).slice(0, 12) + ' ≠ 现有 ' + sha256(b).slice(0, 12) + '）');
    });
    return { diffs, outputs, tool: 'wow-forever-web/tools/export-mini.js' };
  } finally {
    cp.execSync('rm -rf ' + JSON.stringify(tmp));
  }
}

function buildBatch(env, opts) {
  const errors = [];
  const ns = NAMESPACES[env];
  const prev = previewDir();
  const glossarySrc = path.join(prev, 'glossary.json');
  const metaSrc = path.join(prev, 'meta.json');
  const dungeonsSrc = path.join(prev, 'dungeons.json');
  [glossarySrc, metaSrc, dungeonsSrc].forEach((p) => {
    if (!fs.existsSync(p)) errors.push('缺少导出产物 ' + path.relative(REPO, p) + '，先跑 node tools/export-mini.js');
  });
  if (errors.length) return { errors };

  const glossary = readJson(glossarySrc);
  const miniMeta = readJson(metaSrc);
  const dungeons = readJson(dungeonsSrc);
  const list = [].concat(dungeons.newDungeons || [], dungeons.classicDungeons || [], dungeons.raids || []);

  /* —— 卡口（与根 AGENTS.md 第五条同一口径，导出这层再拦一次） —— */
  if (!list.length) errors.push('副本 0 条');
  const ids = list.map((d) => d.id);
  if (new Set(ids).size !== ids.length) errors.push('副本 id 有重复');
  ids.forEach((id) => {
    if (!/^[a-z0-9][a-z0-9-]*$/.test(id)) errors.push('副本 id ' + id + ' 含不能作为文件名的字符');
  });
  list.forEach((d) => {
    if (d.level === 'L0' && !isOfficial(d.provenance)) errors.push('副本 ' + d.id + '：标 L0 但没有官方/解包来源');
    if (!d.nameEn && !d.nameCn) errors.push('副本 ' + d.id + '：中英文名都为空');
    if (/\d+(\.\d+)?\s*%/.test(JSON.stringify(d.drops || []))) errors.push('副本 ' + d.id + '：掉落里出现百分比');
  });
  (glossary.items || []).forEach((x) => {
    if (x.level === 'L0' && !isOfficial(x.provenance)) errors.push('词条 ' + x.id + '：标 L0 但没有官方/解包来源');
  });

  const srcFiles = ['glossary.json', 'meta.json', 'dungeons.json'].map((f) => {
    const abs = path.join(siteData(), f);
    if (!fs.existsSync(abs)) { errors.push('找不到基底文件 src/data/' + f); return null; }
    const buf = fs.readFileSync(abs);
    return { rel: 'src/data/' + f, bytes: buf.length, sha256: sha256(buf) };
  }).filter(Boolean);

  /* —— 与真源对拍：这一批必须能由 src/data 重导出得到 —— */
  let exportCheck = null;
  if (!(opts && opts.skipExportCheck)) {
    const chk = reExportCompare();
    if (chk.diffs.length) {
      chk.diffs.forEach((d) => errors.push('导出产物与基底不配套，构建拒绝：' + d + '；先跑 node tools/export-mini.js 再 build'));
      return { errors };
    }
    exportCheck = { tool: chk.tool, reproduced: true, note: '构建时在临时目录用同一份 src/data 重跑了一遍 export-mini.js，三份导出产物逐字节相同。', outputs: chk.outputs };
  }

  let commit = null;
  try {
    commit = cp.execSync('git -C ' + REPO + ' rev-parse --short HEAD', { encoding: 'utf8' }).trim();
  } catch (e) { commit = null; }

  if (errors.length) return { errors };

  /* —— 内容指纹 → buildId（与时间无关，重跑同源必得同一个 id） ——
     meta/glossary 来自 export-mini.js 的产物，只在外层加身份字段（schemaVersion/product/kind/buildId），
     业务字段一个不动；其余是本层生成的壳。九个身份字段让客户端不用算哈希也能认出混版。 */
  const entries = [];
  const pushObj = (key, relPath, obj, info) => { entries.push(Object.assign({ key, relPath, path: relPath, obj }, info)); };

  pushObj('meta', 'meta.json', Object.assign({ schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'batch-meta' }, miniMeta),
    { records: 1, budget: 'meta', facts: collectFactDates([miniMeta]) });
  pushObj('glossary', 'glossary.json', Object.assign({ schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'glossary' }, glossary),
    { records: (glossary.items || []).length, budget: 'glossary', facts: collectFactDates(glossary.items || []) });

  const indexObj = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    kind: 'dungeon-index',
    counts: {
      total: list.length,
      newDungeons: (dungeons.newDungeons || []).length,
      classicDungeons: (dungeons.classicDungeons || []).length,
      raids: (dungeons.raids || []).length
    },
    note: dungeons.meta ? dungeons.meta.note : '',
    lootDisclaimer: dungeons.meta ? dungeons.meta.lootDisclaimer : '',
    notCollected: { route: list.length - list.filter((d) => (d.route || []).length).length },
    items: list.map(indexEntry)
  };
  pushObj('dungeonIndex', 'dungeons/index.json', indexObj, {
    records: list.length, budget: 'dungeons/index', facts: collectFactDates(list)
  });

  list.forEach((d) => {
    const det = { schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'dungeon-detail', source: 'wow-forever-web/src/data/dungeons.json', dungeon: detailRecord(d) };
    pushObj('dungeonDetail:' + d.id, 'dungeons/detail/' + d.id + '.json', det, {
      records: 1, budget: 'detail', facts: collectFactDates([d])
    });
    const loot = {
      schemaVersion: SCHEMA_VERSION, product: PRODUCT, kind: 'dungeon-loot', dungeonId: d.id,
      level: d.level || 'L3', lootNote: d.lootNote || null, drops: d.drops || []
    };
    pushObj('dungeonLoot:' + d.id, 'dungeons/loot/' + d.id + '.json', loot, {
      records: (d.drops || []).length, budget: 'loot', facts: collectFactDates([d])
    });
  });

  const byKey = {};
  entries.forEach((e) => { byKey[e.key] = e; });
  entries.forEach((e) => {
    e.preBuf = e.buf || dump(e.obj);
    e.contentSha = sha256(e.preBuf);
  });
  const digest = entries.slice().sort((a, b) => (a.path < b.path ? -1 : 1)).map((e) => e.path + ':' + e.contentSha).join('\n');
  const buildId = sha256(Buffer.from(PRODUCT + '|' + SCHEMA_VERSION + '|' + digest, 'utf8')).slice(0, 12);

  /* 先给所有生成的分片注入 buildId，再算详情/掉落的最终字节给索引当校验值，
     最后统一出 buf/bytes/sha256/etag——这一步没有随机因素，重跑必得同样字节。 */
  entries.forEach((e) => { if (e.obj) e.obj.buildId = buildId; });
  indexObj.items.forEach((it) => {
    const dBuf = dump(byKey['dungeonDetail:' + it.id].obj);
    const lBuf = dump(byKey['dungeonLoot:' + it.id].obj);
    it.detailEtag = md5Hex(dBuf);
    it.detailBytes = dBuf.length;
    it.lootEtag = md5Hex(lBuf);
    it.lootBytes = lBuf.length;
  });

  entries.forEach((e) => {
    if (!e.buf) e.buf = dump(e.obj);
    e.bytes = e.buf.length;
    e.sha256 = sha256(e.buf);
    e.etag = md5Hex(e.buf);
    e.cacheControl = IMUTABLE_CACHE;
    if (/"(img|src|static)\//.test(e.buf.toString('utf8'))) {
      errors.push('文件 ' + e.path + ' 里还留着站内相对路径（img/ 或 src/ 开头），小程序打不开，必须先摘掉');
    }
    const limit = BUDGET_KB[e.budget] || 0;
    if (limit && e.bytes > limit * 1024) {
      errors.push('文件 ' + e.path + ' 体积 ' + kb(e.bytes) + ' KB 超预算 ' + limit + ' KB');
    }
  });

  /* 指针清单要小到可以在冷启动时随手取：79 个文件的逐条哈希不塞在这里，
     放进批次内的 files.json（路径带 buildId，永不变，可以硬缓存）。 */
  const bundle = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    buildId,
    kind: 'batch-files',
    note: '这一批每个文件的 SHA-256、ETag、字节数与条数。正常取数不必下载它：入口文件的校验值在指针里，详情/掉落的在索引条目里。',
    cacheControl: IMUTABLE_CACHE,
    files: {}
  };
  entries.forEach((e) => {
    bundle.files[e.key] = { path: e.path, sha256: e.sha256, etag: e.etag, bytes: e.bytes, records: e.records, facts: e.facts };
  });
  const bundleBuf = dump(bundle);
  const bundlePath = 'builds/' + buildId + '/files.json';

  const pickFile = (key) => entries.filter((e) => e.key === key)[0];
  const shared = (e) => ({ path: 'builds/' + buildId + '/' + e.path, sha256: e.sha256, etag: e.etag, bytes: e.bytes, records: e.records });
  const mins = [];
  const maxs = [];
  entries.forEach((e) => { if (e.facts.min) mins.push(e.facts.min); if (e.facts.max) maxs.push(e.facts.max); });
  mins.sort();
  maxs.sort();
  const detailFacts = collectFactDates(list);

  const manifest = {
    schemaVersion: SCHEMA_VERSION,
    product: PRODUCT,
    env,
    namespace: ns,
    buildId,
    /* 这里刻意没有任何时间字段：同一 buildId 的清单必须逐字节恒定，
       否则"不可变批次"会被自己每次重建的时间戳覆写，回滚位的字节一致性也就没意义了。
       发布时刻看对象的服务端 Last-Modified 与本地 oss-build/{env}/last-upload.json。 */
    timeNote: '本清单没有生成时间字段（同 buildId 必须字节恒定）。数据何时核对看 factDates 与每条 provenance；这批何时发布看对象的服务端 Last-Modified。',
    minClientSchemaVersion: 1,
    source: {
      commit,
      inputs: srcFiles,
      inputsNote: '这里哈希的是站点基底 src/data 的原件；批次文件由 export-mini.js 从这些原件派生，构建时已在临时目录重导一遍并逐字节对拍（见 exportCheck）。',
      exportCheck
    },
    counts: {
      dungeons: list.length,
      terms: (glossary.items || []).length,
      files: entries.length + 2,
      bytes: entries.reduce((s, e) => s + e.bytes, 0) + bundleBuf.length
    },
    factDates: {
      min: mins.length ? mins[0] : null,
      latest: maxs.length ? maxs[maxs.length - 1] : null,
      dungeonDetail: detailFacts,
      note: '取数据里 provenance.checkedAt 的真实日期；null 表示这批里还有条目没有核对日期，界面要写「未记录」。'
    },
    droppedFields: DROPPED_DETAIL_FIELDS,
    assetNote: ASSET_NOTE,
    integrity: {
      method: 'etag',
      clientChecks: [
        '指针里 fetch.* 与 bundle 都带 ETag + bytes：入口三文件（meta / glossary / dungeons/index）按指针给的值校验',
        '索引每条自带 detailEtag / detailBytes / lootEtag / lootBytes：进详情、看掉落时按索引给的值校验，不必先取 files.json',
        '这一批的每个文件都带 buildId / product / schemaVersion / kind（副本类分片还带所属副本 id），客户端五项齐验：etag、bytes、buildId、kind、id',
        '分片路径由条目里的 id 现推并与 detailPath/lootPath 比对，对不上就不发请求——写坏一条路径也走不出 builds/{buildId}/',
        '任一项不符就整条当失败，走缓存或打包快照并在界面标出来，不许拿对不上内容的数据当实时'
      ],
      whatItIsNot: '这是"取回的字节是不是清单里那一份"的传输/存储完整性校验（比对服务器自己算的 MD5 ETag），不是抗伪造的内容签名，也不保证上游没写错事实——事实靠 provenance 与红线卡口。',
      serverSide: '逐文件 SHA-256 由构建端算、写进 files.json，并由 `verify` 子命令在发布后逐个回读比对。',
      trustRoot: '指针 manifest.json 自己不做哈希自证：它是信任根，靠 HTTPS + bucket 权限 + max-age=60 的新鲜度。'
    },
    pointer: { key: ns + '/manifest.json', cacheControl: POINTER_CACHE },
    fetch: { meta: shared(pickFile('meta')), glossary: shared(pickFile('glossary')), dungeonIndex: shared(pickFile('dungeonIndex')) },
    bundle: { path: bundlePath, sha256: sha256(bundleBuf), etag: md5Hex(bundleBuf), bytes: bundleBuf.length }
  };

  if (manifest.counts.bytes && Buffer.byteLength(JSON.stringify(manifest, null, 1)) > BUDGET_KB.manifest * 1024) {
    errors.push('指针清单超过 ' + BUDGET_KB.manifest + ' KB，冷启动代价太大，把明细挪进 bundle');
  }
  if (bundleBuf.length > BUDGET_KB.bundle * 1024) errors.push('files.json 超过 ' + BUDGET_KB.bundle + ' KB');
  if (errors.length) return { errors };
  return { errors: [], buildId, ns, entries, manifest, bundleBuf, bundlePath };
}

function writeBatch(env, built) {
  const dir = path.join(buildRoot(), env, 'builds', built.buildId);
  built.entries.forEach((e) => writeBuf(path.join(dir, e.path), e.buf));
  writeBuf(path.join(dir, 'files.json'), built.bundleBuf);
  const manifestBuf = dump(built.manifest);
  writeBuf(path.join(dir, 'manifest.json'), manifestBuf);
  const pointer = path.join(buildRoot(), env, 'manifest.json');
  writeBuf(pointer, manifestBuf);
  return { dir, pointer, manifestBuf };
}

/* ---------- 2. 凭证、写授权闸与最小签名客户端（零依赖） ---------- */

/* 凭证来源只决定"用哪把钥匙"，不再决定"能不能写"。
   能不能写由 requireWriteGate 统一判：每条写命令都要显式 WOW_ALLOW_CROSS_CREDS=1。
   2026-10-21 踩过一次：自动兜底到 p2-database 的 .env，一次"试运行"的验证命令把 82 个对象真传上去了；
   同一天复核又指出「只在 crossProject=true 时检查标记」等于换个来源就绕过。 */
function loadCreds() {
  const picked = {};
  const set = (k, v) => { if (v && !picked[k]) picked[k] = v; };
  set('region', process.env.OSS_REGION);
  set('bucket', process.env.OSS_BUCKET);
  set('accessKeyId', process.env.OSS_ACCESS_KEY_ID);
  set('accessKeySecret', process.env.OSS_ACCESS_KEY_SECRET);
  let source = '环境变量';
  let crossProject = false;

  if (!picked.accessKeyId) {
    const miniCred = path.join(MINI, '.oss-env');
    if (fs.existsSync(miniCred)) picked.warnMiniCred = path.relative(REPO, miniCred);
    const candidates = [];
    if (process.env.WOW_OSS_ENV) candidates.push({ p: path.resolve(process.env.WOW_OSS_ENV), cross: false });
    candidates.push({ p: localCredPath(), cross: false });
    candidates.push({ p: crossCredPath(), cross: true });
    for (const c of candidates) {
      if (!fs.existsSync(c.p)) continue;
      const text = fs.readFileSync(c.p, 'utf8');
      const get = (k) => {
        const m = text.match(new RegExp('^' + k + '=(.*)$', 'm'));
        return m ? m[1].trim().replace(/^["']|["']$/g, '') : '';
      };
      if (get('OSS_ACCESS_KEY_ID') && get('OSS_ACCESS_KEY_SECRET')) {
        set('accessKeyId', get('OSS_ACCESS_KEY_ID'));
        set('accessKeySecret', get('OSS_ACCESS_KEY_SECRET'));
        set('region', get('OSS_REGION'));
        set('bucket', get('OSS_BUCKET'));
        source = (c.cross ? '（跨项目钥匙，仅只读默认）' : '') + path.relative(REPO, c.p);
        crossProject = c.cross;
        break;
      }
    }
  }
  picked.region = picked.region || DEFAULT_REGION;
  picked.bucket = picked.bucket || DEFAULT_BUCKET;
  picked.from = source;
  picked.crossProject = crossProject;
  picked.ok = !!(picked.accessKeyId && picked.accessKeySecret);
  return picked;
}

/* 唯一的写授权闸：所有会动 bucket 的命令都先过这里，没过就 rc1，
   一次远端请求都不发、一个本地批次文件都不落。 */
function requireWriteGate(cmd, env, opts) {
  const out = [];
  if (process.env[WRITE_MARK] !== '1') {
    out.push('✗ ' + cmd + ' 会写 bucket。凭证从哪来都一样，必须显式加环境变量 ' + WRITE_MARK + '=1 才执行（站主口径：每条写命令都要人工点头）。');
    out.push('  报备口径：先说清用哪把钥匙、写哪个前缀，再 ' + WRITE_MARK + '=1 node tools/oss-release.js ' + cmd + ' --env ' + env + ' …');
    out.push('  只读不受影响：build / list / verify / upload --dry-run 都不需要这个标记。');
    return out;
  }
  if (env === 'release' && !opts.yesRelease) {
    out.push('✗ release 是线上环境：除 ' + WRITE_MARK + '=1 外还要显式加 --yes-release。');
    return out;
  }
  if (cmd === 'clean' && !opts.yesClean) {
    out.push('✗ 删除是不可逆动作，加 --yes-clean 才执行。');
    return out;
  }
  return null;
}

let transport = null;
function ossRaw(method, bucket, region, keyOrQuery, body, headers) {
  if (process.env.WOW_OSS_OFFLINE === '1') {
    return Promise.reject(new Error('离线闸 WOW_OSS_OFFLINE=1：禁止真实网络请求（' + method + ' ' + bucket + '）'));
  }
  return new Promise((resolve, reject) => {
    const host = bucket + '.' + region + '.aliyuncs.com';
    const req = https.request(
      { host, method, path: keyOrQuery, headers: Object.assign({ Host: host }, headers || {}), timeout: 20000 },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ statusCode: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
      }
    );
    req.on('timeout', () => req.destroy(new Error('超时 20s: ' + method + ' ' + keyOrQuery)));
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}
const raw = (...args) => (transport ? transport(...args) : ossRaw(...args));
const setTransportForTest = (fn) => { transport = fn || null; };

function signPut(creds, key, body, extraHeaders) {
  const date = new Date().toUTCString();
  const type = 'application/json; charset=utf-8';
  const md5 = md5B64(body);
  const canon = Object.assign({ 'cache-control': extraHeaders['Cache-Control'] }, extraHeaders);
  const ossHeaders = Object.keys(canon)
    .filter((k) => k.indexOf('x-oss-') === 0)
    .sort()
    .map((k) => k + ':' + String(canon[k]).trim() + '\n')
    .join('');
  const sts = ['PUT', md5, type, date, ossHeaders + '/' + creds.bucket + '/' + key].join('\n');
  const sig = crypto.createHmac('sha1', creds.accessKeySecret).update(sts).digest('base64');
  return {
    'Content-Type': type,
    'Content-MD5': md5,
    Date: date,
    'Cache-Control': extraHeaders['Cache-Control'],
    Authorization: 'OSS ' + creds.accessKeyId + ':' + sig,
    'Content-Length': body.length
  };
}

function signGet(creds, pathWithQuery, resource) {
  const date = new Date().toUTCString();
  const sts = ['GET', '', '', date, '/' + creds.bucket + resource].join('\n');
  const sig = crypto.createHmac('sha1', creds.accessKeySecret).update(sts).digest('base64');
  return { Date: date, Authorization: 'OSS ' + creds.accessKeyId + ':' + sig };
}

const encKey = (key) => key.split('/').map(encodeURIComponent).join('/');
const pointerKey = (env) => NAMESPACES[env] + '/manifest.json';
const buildPrefix = (env, buildId) => NAMESPACES[env] + '/builds/' + buildId + '/';

function remotePointer(creds, env) {
  return raw('GET', creds.bucket, creds.region, '/' + encKey(pointerKey(env)), null, signGet(creds, '/' + encKey(pointerKey(env)), '/' + pointerKey(env)))
    .then((r) => (r.statusCode === 200 ? { json: JSON.parse(r.body.toString('utf8')), headers: r.headers, body: r.body } : null));
}

function remoteHead(creds, key) {
  return raw('HEAD', creds.bucket, creds.region, '/' + encKey(key), null, {})
    .then((r) => ({
      exists: r.statusCode === 200,
      etag: r.statusCode === 200 ? String(r.headers.etag || '').replace(/"/g, '').toUpperCase() : '',
      bytes: r.statusCode === 200 ? Number(r.headers['content-length'] || 0) : 0,
      lastModified: r.statusCode === 200 ? r.headers['last-modified'] : '',
      statusCode: r.statusCode
    }));
}

function listKeys(creds, prefix) {
  /* V1 签名的 CanonicalizedResource 只到 "/bucket/"：prefix / max-keys 是查询参数，
     不参与签名（把它们塞进签名串会得到 SignatureDoesNotMatch，实测踩过）。 */
  const q = '/?prefix=' + encodeURIComponent(prefix) + '&max-keys=1000';
  return raw('GET', creds.bucket, creds.region, q, null, signGet(creds, q, '/')).then((r) => {
    if (r.statusCode !== 200) return { ok: false, code: r.statusCode, text: r.body.toString('utf8').slice(0, 300) };
    const xml = r.body.toString('utf8');
    const keys = [];
    const re = /<Key>([^<]+)<\/Key>/g;
    let m;
    while ((m = re.exec(xml))) keys.push(m[1]);
    const truncated = /<IsTruncated>true<\/IsTruncated>/.test(xml);
    return { ok: true, keys, truncated };
  });
}

function signDelete(creds, key) {
  const date = new Date().toUTCString();
  const sts = ['DELETE', '', '', date, '/' + creds.bucket + '/' + key].join('\n');
  const sig = crypto.createHmac('sha1', creds.accessKeySecret).update(sts).digest('base64');
  return { Date: date, Authorization: 'OSS ' + creds.accessKeyId + ':' + sig };
}

function listBuilds(creds, env) {
  const prefix = NAMESPACES[env] + '/builds/';
  return listKeys(creds, prefix).then((r) => {
    if (!r.ok) return r;
    const ids = [];
    r.keys.forEach((k) => {
      const mm = k.replace(prefix, '').split('/')[0];
      if (mm && ids.indexOf(mm) < 0) ids.push(mm);
    });
    return { ok: true, objectCount: r.keys.length, buildIds: ids, truncated: r.truncated };
  });
}

/* ---------- 3. 子命令 ---------- */

function logLine(s) { process.stdout.write(s + '\n'); }

function credsHint(creds) {
  if (creds.warnMiniCred) {
    return '✗ 凭证文件放在小程序根目录（' + creds.warnMiniCred + '）。.gitignore 挡不住微信打包器，密钥会被打进代码包：请移到仓库根 .oss-env 或删除。';
  }
  return '✗ 没找到 OSS 凭证。给法三种：环境变量 OSS_ACCESS_KEY_ID/SECRET、$WOW_OSS_ENV 指向的文件、仓库根 .oss-env（不在小程序目录里）';
}

function cmdBuild(env, opts) {
  const built = buildBatch(env);
  if (built.errors.length) {
    built.errors.slice(0, 25).forEach((e) => logLine('✗ ' + e));
    logLine('构建失败：' + built.errors.length + ' 项不合规');
    return 1;
  }
  const out = writeBatch(env, built);
  const idx = built.entries.filter((e) => e.key === 'dungeonIndex')[0];
  const cold = out.manifestBuf.length + idx.bytes + built.manifest.fetch.meta.bytes;
  const flat = fs.statSync(path.join(previewDir(), 'dungeons.json')).size;
  const maxOf = (p) => kb(Math.max.apply(null, built.entries.filter((e) => e.key.indexOf(p) === 0).map((e) => e.bytes)));
  logLine('批次 ' + built.buildId + ' → ' + path.relative(REPO, out.dir));
  logLine('  数据文件 ' + built.entries.length + ' + files.json + manifest = ' + built.manifest.counts.files
    + ' 个 · 合计 ' + kb(built.manifest.counts.bytes) + ' KB · 指针 ' + pointerKey(env));
  logLine('  导出对拍：' + (built.manifest.source.exportCheck ? '三份产物与 src/data 重导出逐字节一致（' + built.manifest.source.exportCheck.tool + '）' : '已跳过（--skip-export-check）'));
  logLine('  冷启动三取：manifest ' + kb(out.manifestBuf.length) + ' + 索引 ' + kb(idx.bytes)
    + ' + meta ' + kb(built.manifest.fetch.meta.bytes) + ' = ' + kb(cold)
    + ' KB（' + (cold / 1024).toFixed(1) + ' KB / 3 次 GET；整份 dungeons.json 是 ' + kb(flat) + ' KB，省下 ' + Math.round((1 - cold / flat) * 100) + '%）');
  logLine('  单本详情上限 ' + maxOf('dungeonDetail:') + ' KB · 掉落上限 ' + maxOf('dungeonLoot:')
    + ' KB · files.json ' + kb(built.manifest.bundle.bytes) + ' KB');
  logLine('  校验值分布：入口三文件在指针里（ETag+bytes），详情/掉落随索引下发；files.json 只在构建端与 verify 用');
  logLine('  事实核对日期：最新 ' + (built.manifest.factDates.latest || '未记录') + '（清单内无生成时间字段，发布时刻看服务端 Last-Modified）');
  if (opts.checkIdentity) {
    const again = buildBatch(env);
    if (again.errors.length) { logLine('✗ 复算失败'); return 1; }
    const stableSame = again.buildId === built.buildId;
    const perFile = again.entries.filter((e, i) => e.sha256 !== built.entries[i].sha256).map((e) => e.path);
    const volatileOnly = Object.keys(again.manifest).filter((k) => JSON.stringify(again.manifest[k]) !== JSON.stringify(built.manifest[k]));
    const bytesSame = dump(again.manifest).equals(out.manifestBuf);
    logLine('  重跑同源：buildId ' + (stableSame ? '一致' : '不一致 ✗') + ' · 逐文件字节差异 ' + perFile.length
      + ' · manifest 变化字段 [' + volatileOnly.join(',') + '] · 指针清单字节' + (bytesSame ? '完全相同' : '不同 ✗'));
    if (!stableSame || !bytesSame || perFile.length || volatileOnly.length) {
      logLine('✗ 产物不可复现（同一 buildId 的清单必须逐字节恒定）');
      return 1;
    }
  }
  return 0;
}

async function cmdUpload(env, opts) {
  if (!opts.dryRun) {
    const gate = requireWriteGate('upload', env, opts);
    if (gate) { gate.forEach(logLine); return 1; }
  }
  let built = buildBatch(env);
  if (built.errors.length) {
    built.errors.slice(0, 25).forEach((e) => logLine('✗ ' + e));
    return 1;
  }
  const out = writeBatch(env, built);
  const creds = loadCreds();
  logLine('环境 ' + env + ' · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/'
    + ' · 凭证来源 ' + creds.from + (opts.dryRun ? '（--dry-run 只读远端，不写）' : '（已带 ' + WRITE_MARK + '=1）'));
  if (creds.warnMiniCred) { logLine('✗ ' + credsHint(creds)); return 1; }
  if (!opts.dryRun && !creds.ok) { logLine(credsHint(creds)); return 1; }

  const current = creds.ok ? await remotePointer(creds, env) : null;
  const remoteBuildId = current && current.json ? current.json.buildId : null;
  logLine('线上指针：' + (remoteBuildId ? '批次 ' + remoteBuildId + ' · 服务端上传时间 ' + (current.headers['last-modified'] || '未知') : '还没有（第一次发）'));
  if (remoteBuildId === built.buildId) logLine('  指针已指向这一批，下面的传输只是补齐缺件。');

  const targets = built.entries.map((e) => ({ key: buildPrefix(env, built.buildId) + e.path, buf: e.buf, label: e.path }));
  targets.push({ key: NAMESPACES[env] + '/' + built.bundlePath, buf: built.bundleBuf, label: 'files.json（逐文件哈希，verify 用）' });
  targets.push({ key: buildPrefix(env, built.buildId) + 'manifest.json', buf: out.manifestBuf, label: 'builds/manifest.json（批次自带，回滚位）' });

  let uploaded = 0;
  let unchanged = 0;
  const failed = [];
  const violations = [];
  for (const t of targets) {
    let head = { exists: false };
    if (creds.ok) head = await remoteHead(creds, t.key);
    if (head.exists && head.etag && head.etag === md5Hex(t.buf)) { unchanged += 1; continue; }
    if (head.exists) {
      violations.push(t.label + '：远端已存在但字节不同（远端 ETag ' + (head.etag || '?') + ' ≠ 本批 ' + md5Hex(t.buf) + '）');
      continue;
    }
    if (opts.dryRun) { uploaded += 1; logLine('  待传 ' + t.label + '  ' + kb(t.buf.length) + ' KB'); continue; }
    try {
      const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(t.key), t.buf, signPut(creds, t.key, t.buf, { 'Cache-Control': IMUTABLE_CACHE }));
      if (r.statusCode < 200 || r.statusCode >= 300) throw new Error('HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 200));
      const back = await remoteHead(creds, t.key);
      if (back.etag !== md5Hex(t.buf)) throw new Error('回读 ETag 不匹配');
      uploaded += 1;
    } catch (err) {
      failed.push(t.label + ' → ' + err.message);
    }
  }
  logLine('批次文件：传 ' + uploaded + ' · 内容未变跳过 ' + unchanged + ' · 失败 ' + failed.length + ' · 不可变冲突 ' + violations.length + ' / 共 ' + targets.length);
  if (opts.dryRun) {
    logLine('试运行结束，指针没动、没写任何文件。');
    return 0;
  }
  if (violations.length) {
    violations.slice(0, 10).forEach((v) => logLine('  ✗ ' + v));
    logLine('✗ builds/{buildId}/ 是不可变批次，同一路径内容不同绝不能覆盖——指针保持不动（线上仍是 ' + (remoteBuildId || '空') + '）。');
    logLine('  要么这一批被别处写过（查 bucket 日志），要么 buildId 撞了；先查清再发。');
    return 1;
  }
  if (failed.length) {
    failed.slice(0, 10).forEach((f) => logLine('  ✗ ' + f));
    logLine('✗ 批次没传齐，指针保持不动（线上仍是 ' + (remoteBuildId || '空') + '），不会有半批数据被读到。');
    return 1;
  }

  const ptr = pointerKey(env);
  const r = await raw('PUT', creds.bucket, creds.region, '/' + encKey(ptr), out.manifestBuf, signPut(creds, ptr, out.manifestBuf, { 'Cache-Control': POINTER_CACHE }));
  if (r.statusCode < 200 || r.statusCode >= 300) {
    logLine('✗ 换指针失败：HTTP ' + r.statusCode + ' ' + r.body.toString('utf8').slice(0, 300));
    return 1;
  }
  const after = await remotePointer(creds, env);
  const switched = !!after && Buffer.compare(after.body, out.manifestBuf) === 0 && after.json.buildId === built.buildId;
  logLine('指针 → ' + ptr + ' · 批次 ' + built.buildId + ' · ' + (switched ? '回读字节一致' : '回读字节不一致 ✗'));
  if (remoteBuildId && remoteBuildId !== built.buildId) {
    logLine('上一批 ' + remoteBuildId + ' 的文件还在 builds/ 目录里，回滚：node tools/oss-release.js rollback --env ' + env + ' --to ' + remoteBuildId);
  }
  writeBuf(path.join(buildRoot(), env, 'last-upload.json'), dump({
    at: new Date().toISOString(), env, buildId: built.buildId, uploaded, unchanged, failed: failed.length, previousBuildId: remoteBuildId,
    note: '这个时间戳是"本次上传动作"的本地记录，不进批次清单——批次清单必须对同一 buildId 逐字节恒定。'
  }));
  return switched ? 0 : 1;
}

async function cmdVerify(env) {
  const creds = loadCreds();
  const localPath = path.join(buildRoot(), env, 'manifest.json');
  if (!fs.existsSync(localPath)) { logLine('✗ 本地没有 ' + env + ' 批次，先跑 build'); return 1; }
  /* verify 全是匿名 GET（bucket 公共读），不需要密钥 */
  const localBuf = fs.readFileSync(localPath);
  const local = JSON.parse(localBuf.toString('utf8'));
  const ptrRemote = NAMESPACES[env] + '/manifest.json';
  const remote = await raw('GET', creds.bucket, creds.region, '/' + encKey(ptrRemote), null, {});
  if (remote.statusCode !== 200) { logLine('✗ 线上指针读不到：HTTP ' + remote.statusCode); return 1; }
  const bad = [];
  /* 清单里没有任何每次构建都变的字段了，所以这里比的是逐字节，不是"除时间外一致" */
  const ptr = JSON.parse(remote.body.toString('utf8'));
  if (Buffer.compare(remote.body, localBuf) !== 0) bad.push('线上指针与本批清单不是同一份字节（内容或 buildId 与本批不同）');
  const selfManifest = await raw('GET', creds.bucket, creds.region,
    '/' + encKey(buildPrefix(env, ptr.buildId) + 'manifest.json'), null, {});
  if (selfManifest.statusCode !== 200) bad.push('批次自带清单读不到 HTTP ' + selfManifest.statusCode + '，回滚位不可用');
  else if (sha256(selfManifest.body) !== sha256(remote.body)) bad.push('指针与批次自带清单不是同一份字节（rollback 会得到不一样的指针）');
  logLine('指针批次 ' + buildIdOf(ptr) + ' · 本地批次 ' + local.buildId + ' → ' + (ptr.buildId === local.buildId ? '同一批' : '不是同一批 ✗'));
  logLine('指针 Cache-Control：' + (remote.headers['cache-control'] || '未设置') + ' · 内容 ' + kb(remote.body.length) + ' KB · 服务端上传时间 ' + (remote.headers['last-modified'] || '未知'));

  const bundleRemote = NAMESPACES[env] + '/' + ptr.bundle.path;
  if (String(ptr.bundle.path).indexOf('builds/' + ptr.buildId + '/') !== 0) bad.push('指针里的 files.json 路径不在本批目录下');
  const bres = await raw('GET', creds.bucket, creds.region, '/' + encKey(bundleRemote), null, {});
  if (bres.statusCode !== 200) { logLine('✗ files.json 读不到 HTTP ' + bres.statusCode); return 1; }
  if (sha256(bres.body) !== ptr.bundle.sha256) bad.push('files.json 哈希与指针不符（可能是半批上传）');
  const bundle = JSON.parse(bres.body.toString('utf8'));
  let bytes = remote.body.length + bres.body.length;
  const keys = Object.keys(bundle.files);
  for (const k of keys) {
    const f = bundle.files[k];
    const r = await raw('GET', creds.bucket, creds.region, '/' + encKey(buildPrefix(env, ptr.buildId) + f.path), null, {});
    if (r.statusCode !== 200) { bad.push(k + ' HTTP ' + r.statusCode); continue; }
    bytes += r.body.length;
    if (sha256(r.body) !== f.sha256) bad.push(k + ' 哈希不符（线上 ' + sha256(r.body).slice(0, 12) + ' ≠ 清单 ' + f.sha256.slice(0, 12) + '）');
    else if (r.body.length !== f.bytes) bad.push(k + ' 字节不符 ' + r.body.length + ' ≠ ' + f.bytes);
    else if (String(r.headers.etag || '').replace(/"/g, '').toUpperCase() !== f.etag) bad.push(k + ' ETag 与清单不符（客户端按这个校验，必须一致）');
    else if (String(r.headers['cache-control'] || '') !== bundle.cacheControl) bad.push(k + ' Cache-Control 是 ' + (r.headers['cache-control'] || '未设置'));
  }
  ['meta', 'glossary', 'dungeonIndex'].forEach((k) => {
    const f = (ptr.fetch || {})[k];
    if (!f || !f.etag || !f.bytes) bad.push('指针的 fetch.' + k + ' 缺 etag/bytes，客户端无法校验');
  });
  logLine('逐文件回读 ' + keys.length + ' 个 · 整批下行 ' + kb(bytes) + ' KB · 问题 ' + bad.length);
  bad.slice(0, 20).forEach((b) => logLine('  ✗ ' + b));
  if (!bad.length) logLine('指针 = 批次自带清单（字节一致，回滚位可用）· 且与本批清单逐字节相同');
  logLine('事实核对日期：' + (ptr.factDates.min || '?') + ' → ' + (ptr.factDates.latest || '?'));
  return bad.length || ptr.buildId !== local.buildId ? 1 : 0;
}

function buildIdOf(m) { return (m && m.buildId) || '?'; }

async function cmdList(env) {
  const creds = loadCreds();
  const dir = path.join(buildRoot(), env, 'builds');
  const localIds = fs.existsSync(dir) ? fs.readdirSync(dir).filter((x) => !x.startsWith('.')) : [];
  logLine('本地 ' + env + ' 批次：' + (localIds.length ? localIds.join(', ') : '（还没有，先跑 build）'));
  logLine('只读查询 · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/ · 凭证来源 ' + creds.from + '（写操作仍需 ' + WRITE_MARK + '=1）');
  if (!creds.ok) { logLine('线上：没找到凭证，跳过列举'); return 0; }
  const res = await listBuilds(creds, env);
  if (!res.ok) { logLine('✗ 线上列举失败 HTTP ' + res.code + ' ' + res.text); return 1; }
  logLine('线上 ' + NAMESPACES[env] + '/builds/：' + (res.buildIds.length ? res.buildIds.join(', ') : '空') + '（对象 ' + res.objectCount + ' 个）');
  const ptr = await remotePointer(creds, env);
  logLine('线上指针指向：' + (ptr && ptr.json ? ptr.json.buildId + ' · ' + ptr.json.counts.files + ' 个文件 · 服务端上传时间 ' + (ptr.headers['last-modified'] || '未知') : '还没有'));
  return 0;
}

/* 回滚不是"把目标清单贴回指针"那么轻：半传批次的自带清单也可能存在，
   指过去就是把一批残缺数据变成线上数据。所以先把目标批次整批点清，再动指针。 */
async function verifyBatchForRollback(creds, env, to, manifest, selfRaw) {
  const problems = [];
  if (manifest.buildId !== to) problems.push('目标目录 builds/' + to + '/ 里的清单写的是 ' + manifest.buildId + '，与 --to 不符');
  if (manifest.env !== env) problems.push('该清单是 ' + manifest.env + ' 环境的，不能当 ' + env + ' 的指针');
  if (manifest.product !== PRODUCT) problems.push('该清单的 product 是 ' + manifest.product + '，不是本站的 ' + PRODUCT);
  if (manifest.schemaVersion !== SCHEMA_VERSION) problems.push('该清单的 schemaVersion 是 ' + manifest.schemaVersion + '，客户端只认 ' + SCHEMA_VERSION);
  if (manifest.namespace !== NAMESPACES[env]) problems.push('该清单的 namespace 是 ' + manifest.namespace + '，与 ' + env + ' 不符');
  const inBatch = (p) => String(p || '').indexOf('builds/' + to + '/') === 0;
  const root = buildPrefix(env, to);
  let bundle = null;
  if (!inBatch((manifest.bundle || {}).path)) problems.push('清单里的 files.json 路径不在 builds/' + to + '/ 下：' + (manifest.bundle || {}).path);
  else {
    const bres = await raw('GET', creds.bucket, creds.region, '/' + encKey(NAMESPACES[env] + '/' + manifest.bundle.path), null, {});
    if (bres.statusCode !== 200) problems.push('files.json 读不到 HTTP ' + bres.statusCode);
    else if (sha256(bres.body) !== manifest.bundle.sha256) problems.push('files.json 哈希与清单不符（这批没传齐或被改过）');
    else bundle = JSON.parse(bres.body.toString('utf8'));
    if (bundle && bundle.buildId !== to) problems.push('files.json 的 buildId 是 ' + bundle.buildId + '，与批次 ' + to + ' 不符');
  }
  Object.keys((manifest.fetch) || {}).forEach((k) => {
    if (!inBatch(manifest.fetch[k].path)) problems.push('fetch.' + k + ' 的路径越出本批目录：' + manifest.fetch[k].path);
    if (!manifest.fetch[k].etag || !manifest.fetch[k].bytes) problems.push('fetch.' + k + ' 缺 etag/bytes，客户端无法校验');
  });
  const checked = [];
  if (bundle) {
    for (const k of Object.keys(bundle.files)) {
      const f = bundle.files[k];
      /* files.json 里的 path 是批次内相对路径（与索引条目一致），拼 root 用；
         但绝对路径与 ../ 一律拒绝——拼出来的 key 越出 builds/{to}/ 就等于让这一批指到别处。 */
      if (/^(\.\.\/|\/|builds\/)/.test(String(f.path || ''))) { problems.push(k + ' 的路径越出本批目录：' + f.path); continue; }
      if (!f.sha256 || !f.etag || !f.bytes) { problems.push(k + ' 的清单项缺校验值'); continue; }
      const h = await remoteHead(creds, root + f.path);
      if (!h.exists) problems.push(k + ' 在远端不存在（HTTP ' + h.statusCode + '）——这一批是半批，不能激活');
      else if (String(h.etag) !== String(f.etag)) problems.push(k + ' 远端 ETag ' + h.etag + ' ≠ 清单 ' + f.etag);
      else if (h.bytes && h.bytes !== f.bytes) problems.push(k + ' 远端 ' + h.bytes + ' B ≠ 清单 ' + f.bytes + ' B');
      checked.push(k);
    }
    const self = await raw('GET', creds.bucket, creds.region, '/' + encKey(root + 'manifest.json'), null, {});
    if (self.statusCode !== 200) problems.push('批次自带清单读不到，回滚位不可用');
    else if (Buffer.compare(self.body, selfRaw) !== 0) problems.push('回滚途中自带清单字节变了');
  }
  return { problems, checked: checked.length };
}

async function cmdRollback(env, opts) {
  const gate = requireWriteGate('rollback', env, opts);
  if (gate) { gate.forEach(logLine); return 1; }
  if (!opts.to) { logLine('✗ rollback 要加 --to <buildId>（list 子命令能看有哪些批次）'); return 1; }
  if (!/^[a-f0-9]{12}$/.test(String(opts.to))) { logLine('✗ --to 要的是一个 12 位十六进制批次号，得到的是 ' + opts.to); return 1; }
  const creds = loadCreds();
  if (creds.warnMiniCred) { logLine(credsHint(creds)); return 1; }
  if (!creds.ok) { logLine(credsHint(creds)); return 1; }
  logLine('回滚 ' + env + ' · bucket ' + creds.bucket + ' · 前缀 ' + NAMESPACES[env] + '/ · 目标批次 ' + opts.to + '（凭证来源 ' + creds.from + '）');

  const key = buildPrefix(env, opts.to) + 'manifest.json';
  const r = await raw('GET', creds.bucket, creds.region, '/' + encKey(key), null, {});
  if (r.statusCode !== 200) { logLine('✗ 批次 ' + opts.to + ' 的自带清单读不到（HTTP ' + r.statusCode + '），不能指回去'); return 1; }
  let manifest;
  try { manifest = JSON.parse(r.body.toString('utf8')); } catch (e) { logLine('✗ 自带清单不是合法 JSON：' + e.message); return 1; }

  const v = await verifyBatchForRollback(creds, env, opts.to, manifest, r.body);
  logLine('目标批次核验：清单项 ' + v.checked + ' 个文件逐个查过 · 问题 ' + v.problems.length);
  if (v.problems.length) {
    v.problems.slice(0, 12).forEach((p) => logLine('  ✗ ' + p));
    logLine('✗ 这一批不完整或身份不对，指针不动（线上仍是原来的批次）。');
    return 1;
  }

  const ptr = pointerKey(env);
  const put = await raw('PUT', creds.bucket, creds.region, '/' + encKey(ptr), r.body, signPut(creds, ptr, r.body, { 'Cache-Control': POINTER_CACHE }));
  if (put.statusCode < 200 || put.statusCode >= 300) { logLine('✗ 回滚写指针失败 HTTP ' + put.statusCode); return 1; }
  const after = await raw('GET', creds.bucket, creds.region, '/' + encKey(ptr), null, {});
  const same = after.statusCode === 200 && Buffer.compare(after.body, r.body) === 0;
  logLine('指针已回到批次 ' + opts.to + ' · ' + (same ? '回读字节与自带清单完全一致' : '回读字节不一致 ✗')
    + ' · 文件 ' + (manifest.counts ? manifest.counts.files : '?') + ' 个');
  if (!same) logLine('✗ 回滚后的指针与自带清单不同字节，线上状态不可信，立刻人工介入。');
  return same ? 0 : 1;
}

/* 把某个环境的整个命名空间清空（发错了、或者要把内测批次撤下来时用）。
   指针和批次一起删，删完客户端只会走打包快照，所以要先在群里说一声。
   release 是线上：--yes-clean 只说明"我知道要删"，--yes-release 才说明"我知道删的是线上"。 */
async function cmdClean(env, opts) {
  const gate = requireWriteGate('clean', env, opts);
  if (gate) { gate.forEach(logLine); return 1; }
  const creds = loadCreds();
  if (creds.warnMiniCred) { logLine(credsHint(creds)); return 1; }
  if (!creds.ok) { logLine(credsHint(creds)); return 1; }
  const prefix = NAMESPACES[env] + '/';
  logLine('目标：bucket ' + creds.bucket + ' · 前缀 ' + prefix + ' · 凭证来源 ' + creds.from);
  const res = await listKeys(creds, prefix);
  if (!res.ok) { logLine('✗ 列举失败 HTTP ' + res.code + ' ' + res.text); return 1; }
  if (res.truncated) { logLine('✗ 对象超过 1000 个，这个命令只处理单页，先手工确认再删'); return 1; }
  logLine('将删除 bucket ' + creds.bucket + ' 前缀 ' + prefix + ' 下的 ' + res.keys.length + ' 个对象');
  let deleted = 0;
  const failed = [];
  for (const key of res.keys) {
    try {
      const r = await raw('DELETE', creds.bucket, creds.region, '/' + encKey(key), null, signDelete(creds, key));
      if (r.statusCode === 204 || r.statusCode === 200) deleted += 1;
      else failed.push(key + ' HTTP ' + r.statusCode);
    } catch (err) { failed.push(key + ' ' + err.message); }
  }
  const after = await listKeys(creds, prefix);
  failed.slice(0, 10).forEach((f) => logLine('  ✗ ' + f));
  if (!after.ok) {
    logLine('✗ 清完无法核验剩余对象（列举 HTTP ' + after.code + '）——已删 ' + deleted + '，必须人工确认 bucket ' + creds.bucket + ' 前缀 ' + prefix + ' 还剩什么。');
    return 1;
  }
  logLine('清后核验：bucket ' + creds.bucket + ' 前缀 ' + prefix + ' 已删 ' + deleted + ' · 失败 ' + failed.length + ' · 剩余 ' + after.keys.length + ' 个对象');
  return failed.length || after.keys.length > 0 ? 1 : 0;
}

/* ---------- 4. 入口 ---------- */

function parseArgs(argv) {
  const cmd = argv[0];
  const opts = { dryRun: false, yesRelease: false, yesClean: false, checkIdentity: false, skipExportCheck: false };
  let env = 'beta';
  for (let i = 1; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--env') { i += 1; env = argv[i]; }
    else if (a === '--to') { i += 1; opts.to = argv[i]; }
    else if (a === '--dry-run') opts.dryRun = true;
    else if (a === '--yes-release') opts.yesRelease = true;
    else if (a === '--yes-clean') opts.yesClean = true;
    else if (a === '--check-identity') opts.checkIdentity = true;
    else if (a === '--skip-export-check') opts.skipExportCheck = true;
    else { logLine('✗ 不认识的参数 ' + a); process.exit(2); }
  }
  if (['beta', 'release'].indexOf(env) < 0) { logLine('✗ --env 只认 beta 或 release'); process.exit(2); }
  return { cmd, env, opts };
}

function main() {
  const argv = process.argv.slice(2);
  if (!argv.length) {
    logLine('用法：node tools/oss-release.js <build|upload|verify|list|rollback|clean> --env beta|release'
      + ' [--dry-run] [--check-identity] [--yes-release] [--to <buildId>] [--yes-clean]');
    logLine('写命令（upload/rollback/clean）必须显式带环境变量 ' + WRITE_MARK + '=1；release 还要 --yes-release。');
    process.exit(2);
  }
  const { cmd, env, opts } = parseArgs(argv);
  return Promise.resolve()
    .then(() => {
      if (cmd === 'build') return cmdBuild(env, opts);
      if (cmd === 'upload') return cmdUpload(env, opts);
      if (cmd === 'verify') return cmdVerify(env);
      if (cmd === 'list') return cmdList(env);
      if (cmd === 'rollback') return cmdRollback(env, opts);
      if (cmd === 'clean') return cmdClean(env, opts);
      logLine('✗ 没有子命令 ' + cmd);
      return 2;
    })
    .then((rc) => {
      logLine('rc=' + rc);
      process.exit(rc);
    })
    .catch((err) => {
      logLine('✗ ' + (err && err.message ? err.message : err));
      logLine('rc=1');
      process.exit(1);
    });
}

if (require.main === module) main();

module.exports = {
  SCHEMA_VERSION,
  NAMESPACES,
  BUDGET_KB,
  DROPPED_DETAIL_FIELDS,
  WRITE_MARK,
  buildBatch,
  writeBatch,
  loadCreds,
  requireWriteGate,
  reExportCompare,
  listKeys,
  pointerKey,
  buildPrefix,
  encKey,
  md5Hex,
  localCredPath,
  crossCredPath,
  siteSrc,
  setTransportForTest,
  cmdBuild,
  cmdUpload,
  cmdVerify,
  cmdList,
  cmdRollback,
  cmdClean
};
