#!/usr/bin/env node
/* 把站点基底数据导出成小程序要用的两份产物：
   1) oss-preview/*.json  → 上传到 OSS wow/{env}/ 的内容（全量）
   2) data/forever-*-snapshot.js → 打进小程序主包的兜底快照（少量，结构必须与 OSS JSON 一致）
   快照超预算或数据不合规直接退出码非 0，防止把没核实的东西当成品发出去。 */
const fs = require('fs');
const path = require('path');

const WEB = path.resolve(__dirname, '..');
const DATA = path.join(WEB, 'src', 'data');
const MINI = path.resolve(WEB, '..', 'for-mini');
const OSS_DIR = path.join(MINI, 'oss-preview');
const SNAP_DIR = path.join(MINI, 'data');

const SNAPSHOT_TERMS = Number(process.argv[2] || 60);
const SNAPSHOT_BUDGET_KB = 60;

const read = (p) => JSON.parse(fs.readFileSync(path.join(DATA, p), 'utf8'));

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function isOfficial(list) {
  return (list || []).some((s) => (s.type || '').indexOf('official') === 0);
}

/* 客户端解包转述的中文名按 2026-10-08 站主定的口径直接算 L0，所以标 L0 时
   除了官方页，这类来源也算数（与 tools/build-data.js 同一口径，别在这儿放宽）。 */
function isL0Support(list) {
  return (list || []).some((s) => (s.type || '').indexOf('official') === 0 || s.type === 'datamine_cn');
}

function tally(levels) {
  const t = { L0: 0, L1: 0, L2: 0, L3: 0, total: levels.length };
  levels.forEach((l) => {
    if (t[l] === undefined) l = 'L3';
    t[l] += 1;
  });
  return t;
}

/* 导出层自己新写的说明文字也要过同一把尺子：基底里的字符串由 build-data.js 扫过，
   但这一层现编的句子（fieldNote 之类）没人扫，写错一个内部词就直接印到玩家手机上。 */
const BAN = JSON.parse(fs.readFileSync(path.join(WEB, 'tools', 'copy-banned.json'), 'utf8'));
function checkCopy(label, text) {
  const s = String(text || '');
  BAN.patterns.forEach((p) => {
    if (new RegExp(p.re, 'i').test(s)) errs.push(`${label}：命中禁词「${p.re}」（${p.why}）`);
  });
}

const glossary = read('glossary.json');
const meta = read('meta.json');
const dungeons = read('dungeons.json');
const systems = read('systems.json');
const classes = read('classes.json');
const spells = read('spells.json');

const dungeonList = (dungeons.newDungeons || []).concat(dungeons.classicDungeons || [], dungeons.raids || []);
const spellList = spells.spells || [];
const classIndex = classes.classes || [];
const classIds = classIndex.map((c) => c.id);

/* 分发层与小程序都按这一句解释列名，别在页面里另写一套 */
const SPELL_FIELD_NOTE = '级数＝这一系能学到几级；起学等级＝多少级学会；对照状态＝和经典旧世比是新增、改动还是改名。'
  + '每一级的学习等级在展开的「逐级」里。本站不放技能描述与循环建议。';
const talentFiles = fs.readdirSync(path.join(DATA, 'talents')).filter((f) => f !== '_demo.json' && f.endsWith('.json'));
const talentNodes = [];
talentFiles.forEach((f) => {
  const t = JSON.parse(fs.readFileSync(path.join(DATA, 'talents', f), 'utf8'));
  (t.trees || []).forEach((tree) => {
    (tree.nodes || []).forEach((n) => talentNodes.push(n));
  });
});

/* —— 卡口：与 build-data.js 同一条红线，导出前先拦一次 —— */
const errs = [];
glossary.items.forEach((x) => {
  if (x.level === 'L0' && !isOfficial(x.provenance)) errs.push(`词条 ${x.id}：标 L0 但无官方来源`);
});
talentNodes.forEach((n) => {
  const s = JSON.stringify(n);
  if (/"iconKey"\s*:\s*"https?:/.test(s)) errs.push(`天赋 ${n.id}：iconKey 用了外链`);
});
dungeonList.forEach((d) => {
  if (/\d+(\.\d+)?\s*%/.test(JSON.stringify(d.drops || d))) errs.push(`副本 ${d.id}：出现百分比数值`);
});

/* —— 法术书（M02-2）：这一层只放行"名称 / 级数 / 起学等级 / 与经典对照状态"四类事实，
   描述正文与循环建议本来就不在基底里，这里再拦一次防止上游把它们抄进来 —— */
if (!spellList.length) errs.push('法术书 0 条，技能速查没有内容可发');
const spellIds = spellList.map((s) => s.id);
if (new Set(spellIds).size !== spellIds.length) errs.push('法术书 id 有重复');
spellList.forEach((s) => {
  if (classIds.indexOf(s.classId) < 0) errs.push(`法术 ${s.id}：classId ${s.classId} 不在 classes.json 里`);
  /* 法术 id 不进文件名（分片按职业切），但客户端拿它当展开态的 key，
     必须与 classId 对得上，且不能出现会撑坏 JSON 的字符 */
  if (String(s.id).indexOf(s.classId + '-') !== 0) errs.push(`法术 ${s.id}：id 前缀不是自己的 classId`);
  if (/["\\\n]/.test(String(s.id))) errs.push(`法术 ${s.id}：id 里有引号或换行`);
  if (s.level === 'L0' && !isL0Support(s.provenance)) errs.push(`法术 ${s.id}：标 L0 但没有官方/解包来源`);
  if (/^https?:/.test(String(s.iconKey || ''))) errs.push(`法术 ${s.id}：iconKey 用了外链`);
  const body = JSON.stringify(s);
  if (/"(description|desc|rankDescription|tooltip|rotation)"\s*:/.test(body)) errs.push(`法术 ${s.id}：出现了描述/循环类字段，技能速查不承载这些内容`);
});
classIds.forEach((id) => {
  if (!/^[a-z][a-z0-9_-]*$/.test(id)) errs.push(`职业 id ${id}：不能当分片文件名`);
  if (!spellList.some((s) => s.classId === id)) errs.push(`职业 ${id}：一条法术都没有，分片会是空的`);
});
/* 采集过程那句话（哪份脚本合的、第三方 upstream）只留在仓库里，不随分片上手机 */
checkCopy('spells.meta.pageNote', (spells.meta || {}).pageNote || '');
checkCopy('spells.meta.levelPolicy', (spells.meta || {}).levelPolicy || '');
checkCopy('导出层新写的列名说明', SPELL_FIELD_NOTE);
spellList.forEach((s) => checkCopy('法术 ' + s.id + ' 的名字', s.name));

const coverage = tally(
  glossary.items.map((x) => x.level)
    .concat(dungeonList.map((d) => d.level))
    .concat(talentNodes.map((n) => n.level))
);

const nameHit = talentNodes.filter((n) => n.nameVerified || (n.provenance || []).some((p) => (p.type || '') === 'official_cn')).length;

const miniMeta = {
  site: meta.site,
  disclaimer: meta.disclaimer,
  dataBaseline: meta.dataBaseline,
  launch: meta.launch,
  checkedAt: meta.checkedAt,
  source: 'wow-forever-web/src/data',
  coverage: coverage,
  counts: {
    terms: glossary.items.length,
    dungeons: dungeonList.length,
    spells: spellList.length,
    lootRows: dungeonList.reduce((s, d) => s + (d.drops || []).length, 0),
    lootItems: new Set(dungeonList.reduce((a, d) => a.concat((d.drops || []).map((x) => String(x.itemId || x.nameCn || ''))), [])).size,
    talentNodes: talentNodes.length,
    talentNameVerified: nameHit
  },
  openQuestions: (meta.openQuestions || []).slice(0, 6),
  rules: meta.rules
};

/* —— 快照挑选：优先 L0，按 kind / classId 分散，保证离线也有可搜内容 —— */
function pickSnapshot(items, limit) {
  const byGroup = {};
  items.forEach((x) => {
    const key = (x.classId || x.kind || 'other') + '|' + x.kind;
    if (!byGroup[key]) byGroup[key] = [];
    byGroup[key].push(x);
  });
  const picked = [];
  let round = 0;
  while (picked.length < limit) {
    let added = false;
    Object.keys(byGroup).forEach((key) => {
      const list = byGroup[key];
      if (list[round] && picked.length < limit) {
        picked.push(list[round]);
        added = true;
      }
    });
    if (!added) break;
    round += 1;
  }
  return picked.slice(0, limit);
}

const snapshotItems = pickSnapshot(glossary.items.slice().sort((a, b) => (a.level < b.level ? -1 : 1)), SNAPSHOT_TERMS);
const miniGlossary = {
  meta: {
    generatedAt: meta.checkedAt,
    note: glossary.meta ? glossary.meta.note : '',
    pending: (glossary.meta ? glossary.meta.pending : []) || [],
    snapshot: true,
    coverage: coverage
  },
  items: snapshotItems
};

/* —— 副本索引快照（M01）——
   38 本全放进主包：列表页断网也得有内容可搜，一份索引本来就 20 来 KB。
   字段与 tools/oss-release.js 的 indexEntry() **逐字段一致**（那边一改这边就要红），
   这样"离线读到的"与"联网读到的"是同一套字段，界面不必写两套判断。
   详情与掉落不打包：按 id 分片才装得下 38×2 份，主包预算是给索引的，
   断网点详情时界面必须说"详情需联网"，不许拿索引里的几个字段冒充完整详情。 */
function dungeonIndexEntry(d) {
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

const snapshotDungeonIndex = {
  schemaVersion: 1,
  product: 'wow-forever-mini',
  kind: 'dungeon-index',
  snapshot: true,
  counts: {
    total: dungeonList.length,
    newDungeons: (dungeons.newDungeons || []).length,
    classicDungeons: (dungeons.classicDungeons || []).length,
    raids: (dungeons.raids || []).length
  },
  note: dungeons.meta ? dungeons.meta.note : '',
  lootDisclaimer: dungeons.meta ? dungeons.meta.lootDisclaimer : '',
  notCollected: { route: dungeonList.length - dungeonList.filter((d) => (d.route || []).length).length },
  items: dungeonList.map(dungeonIndexEntry)
};

/* —— 法术书导出（M02-2）——
   oss-preview/spells.json 是给分发层切的原料，不进主包（主包 60 KB 预算已经给副本索引占了，
   498 条法术放不进去）。这里补一份"职业名单 + 每职业条数与系别"的头部，
   是为了让 oss-release 只读导出产物就能分片，不用绕过导出层去碰 src/data 原件。 */
function spellClassHead() {
  const byClass = {};
  spellList.forEach((s) => {
    const b = (byClass[s.classId] = byClass[s.classId] || { count: 0, tabs: {}, states: {} });
    b.count += 1;
    const t = s.tab || '未分类';
    b.tabs[t] = (b.tabs[t] || 0) + 1;
    if (s.state) b.states[s.state] = (b.states[s.state] || 0) + 1;
  });
  return classIndex.map((c) => {
    const b = byClass[c.id] || { count: 0, tabs: {}, states: {} };
    return {
      classId: c.id,
      nameCn: c.cn || null,
      nameEn: c.en || null,
      iconKey: c.iconKey || null,
      level: c.nameLevel || 'L3',
      count: b.count,
      tabs: Object.keys(b.tabs).map((k) => ({ name: k, count: b.tabs[k] })),
      states: b.states
    };
  }).filter((c) => c.count > 0);
}

const miniSpells = {
  meta: {
    generatedAt: (spells.meta || {}).generatedAt || null,
    source: 'wow-forever-web/src/data/spells.json',
    pageNote: (spells.meta || {}).pageNote || '',
    levelPolicy: (spells.meta || {}).levelPolicy || '',
    counts: Object.assign({}, (spells.meta || {}).counts, { exported: spellList.length }),
    /* 分发层与界面都按这一句解释列名，别在小程序里另写一套 */
    fieldNote: SPELL_FIELD_NOTE
  },
  classes: spellClassHead(),
  spells: spellList
};

if (errs.length) {
  errs.slice(0, 20).forEach((e) => console.error('✗ ' + e));
  console.error(`导出失败：${errs.length} 项不合规`);
  process.exit(1);
}

ensureDir(OSS_DIR);
ensureDir(SNAP_DIR);

fs.writeFileSync(path.join(OSS_DIR, 'glossary.json'), JSON.stringify(glossary, null, 1));
fs.writeFileSync(path.join(OSS_DIR, 'dungeons.json'), JSON.stringify(dungeons, null, 1));
fs.writeFileSync(path.join(OSS_DIR, 'meta.json'), JSON.stringify(miniMeta, null, 1));
fs.writeFileSync(path.join(OSS_DIR, 'spells.json'), JSON.stringify(miniSpells, null, 1));

/* 双向卡口：直接读 oss-release.js 的 indexEntry() 与刚生成的 oss-preview/dungeons.json 比一遍。
   两边一致只证明一致，所以这里比的是"快照能不能喂给线上那套取数逻辑"，
   分片路径与逐字段结构一旦对不上，构建就停在这里而不是等用户读到空字段。
   WOW_SNAPSHOT_CROSSCHECK=off 只给自测构造坏夹具用：发布链路绕不过去——
   oss-release build 会重新跑一遍带这道检查的导出，坏源照样在上一层就被拒。 */
if (process.env.WOW_SNAPSHOT_CROSSCHECK === 'off') {
  console.log('  （已跳过索引快照对拍：WOW_SNAPSHOT_CROSSCHECK=off，仅自测构造夹具用）');
} else if (fs.existsSync(path.join(OSS_DIR, 'dungeons.json'))) {
  let ossIndex = null;
  let ossCounts = null;
  const releasePath = path.join(WEB, 'tools', 'oss-release.js');
  if (!fs.existsSync(releasePath)) {
    console.error('✗ 找不到 tools/oss-release.js，索引快照没法对拍（这一条不许跳过：两边字段漂了界面才会读到空值）');
    errs.push('索引快照对拍缺席');
  } else {
  try {
    const release = require(releasePath);
    const built = release.buildBatch('beta', { skipExportCheck: true });
    if (!built.errors || !built.errors.length) {
      ossIndex = (built.entries.filter((e) => e.key === 'dungeonIndex')[0] || {}).obj;
      ossCounts = built.manifest.counts;
    } else {
      console.error(`✗ 分发层构建不通过，快照无参照可对拍：${built.errors.slice(0, 3).join('；')}`);
      errs.push('oss-release buildBatch 失败');
    }
  } catch (e) {
    console.error('✗ 对拍没跑起来：' + e.message);
    errs.push('索引快照对拍失败');
  }
  }
  if (ossIndex) {
    /* 比对逐字段一致的"内容层"：分发层会额外注入 buildId 与四份校验值（etag/bytes），
       那两个数与批次走，主包快照里没有批次号、也就不能有——所以比之前先把它摘掉，
       剩下的字段必须一模一样。 */
    /* 分发层会额外注入"随批次变"的校验字段（etag / md5 / bytes）。
       主包快照没有批次号，所以比之前把这些一律摘掉——按后缀匹配而不是列名单，
       下次分发层再加一种校验写法，这里不会静默漏掉。 */
    const strip = (it) => {
      const o = {};
      Object.keys(it).forEach((k) => { if (!/(Etag|Md5|Bytes)$/.test(k)) o[k] = it[k]; });
      return o;
    };
    const a = JSON.stringify(snapshotDungeonIndex.items);
    const b = JSON.stringify(ossIndex.items.map(strip));
    if (a !== b) errs.push('副本索引快照与 oss-release 的索引条目逐字段不一致（改字段要两边一起改）');
    if (ossIndex.items.some((it) => !it.detailEtag || !it.lootEtag || !it.detailBytes || !it.lootBytes
      || !it.detailMd5 || !it.lootMd5)) {
      errs.push('分发层索引条目缺 etag/bytes 校验值，客户端将无法校验详情与掉落');
    }
    if (snapshotDungeonIndex.items.some((it) => it.buildId !== undefined)) errs.push('主包快照不该带 buildId');
    if (snapshotDungeonIndex.counts.total !== ossIndex.counts.total) errs.push('副本索引快照条数与分发层不符');
    /* 首页那几个数字来自 meta 快照，掉落反查的表来自分发层现算——两边算法漂了，
       玩家就会看到"首页写 1050 条，点进去只有 1040 条" */
    if (!ossCounts) errs.push('拿不到分发层的 counts，掉落数字没法对拍');
    else if (ossCounts.lootRows !== miniMeta.counts.lootRows) {
      errs.push(`掉落条数两边不一致：主包 meta 写 ${miniMeta.counts.lootRows}，分发层算 ${ossCounts.lootRows}`);
    } else if (ossCounts.lootItems !== miniMeta.counts.lootItems) {
      errs.push(`去重后的物品数两边不一致：主包 meta 写 ${miniMeta.counts.lootItems}，分发层算 ${ossCounts.lootItems}`);
    }
  }
}

if (errs.length) {
  errs.slice(0, 20).forEach((e) => console.error('✗ ' + e));
  console.error(`导出失败：${errs.length} 项不合规（oss-preview 已更新，主包快照不更新，别把两份混着发）`);
  process.exit(1);
}

const writeSnapshot = (name, obj) => {
  const body = '/* 自动生成，勿手改：node wow-forever-web/tools/export-mini.js */\nmodule.exports = ' + JSON.stringify(obj, null, 1) + ';\n';
  fs.writeFileSync(path.join(SNAP_DIR, name), body);
  return Buffer.byteLength(body, 'utf8');
};

const gBytes = writeSnapshot('forever-glossary-snapshot.js', miniGlossary);
const mBytes = writeSnapshot('forever-meta-snapshot.js', miniMeta);
const dBytes = writeSnapshot('forever-dungeon-snapshot.js', snapshotDungeonIndex);
const snapBytes = gBytes + mBytes + dBytes;
const kb = (b) => (b / 1024).toFixed(1) + ' KB';

if (snapBytes > SNAPSHOT_BUDGET_KB * 1024) {
  console.error(`✗ 快照体积 ${kb(snapBytes)}（词条 ${kb(gBytes)} + meta ${kb(mBytes)} + 副本索引 ${kb(dBytes)}）超过主包预算 ${SNAPSHOT_BUDGET_KB} KB，减少 SNAPSHOT_TERMS 或精简字段`);
  process.exit(1);
}

console.log(`导出完成 → ${path.relative(process.cwd(), MINI)}`);
console.log(`  oss-preview/glossary.json  ${kb(fs.statSync(path.join(OSS_DIR, 'glossary.json')).size)}（${glossary.items.length} 条）`);
console.log(`  oss-preview/dungeons.json  ${kb(fs.statSync(path.join(OSS_DIR, 'dungeons.json')).size)}（${dungeonList.length} 本）`);
console.log(`  oss-preview/meta.json      ${kb(fs.statSync(path.join(OSS_DIR, 'meta.json')).size)}`);
console.log(`  oss-preview/spells.json    ${kb(fs.statSync(path.join(OSS_DIR, 'spells.json')).size)}（${spellList.length} 条 / ${miniSpells.classes.length} 职业，只走线上分片，不进主包）`);
console.log(`  快照词条 ${snapshotItems.length} 条 ${kb(gBytes)} · meta ${kb(mBytes)} · 副本索引 ${snapshotDungeonIndex.items.length} 本 ${kb(dBytes)}`);
console.log(`  主包快照合计 ${kb(snapBytes)}（预算 ${SNAPSHOT_BUDGET_KB} KB，用了 ${Math.round(snapBytes / (SNAPSHOT_BUDGET_KB * 1024) * 100)}%）`);
console.log(`  覆盖率 L0 ${coverage.L0} / L1 ${coverage.L1} / L2 ${coverage.L2} / L3 ${coverage.L3}（共 ${coverage.total}）`);
