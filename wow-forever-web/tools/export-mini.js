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

function tally(levels) {
  const t = { L0: 0, L1: 0, L2: 0, L3: 0, total: levels.length };
  levels.forEach((l) => {
    if (t[l] === undefined) l = 'L3';
    t[l] += 1;
  });
  return t;
}

const glossary = read('glossary.json');
const meta = read('meta.json');
const dungeons = read('dungeons.json');
const systems = read('systems.json');
const classes = read('classes.json');

const dungeonList = (dungeons.newDungeons || []).concat(dungeons.classicDungeons || [], dungeons.raids || []);
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

const writeSnapshot = (name, obj) => {
  const body = '/* 自动生成，勿手改：node wow-forever-web/tools/export-mini.js */\nmodule.exports = ' + JSON.stringify(obj, null, 1) + ';\n';
  fs.writeFileSync(path.join(SNAP_DIR, name), body);
  return Buffer.byteLength(body, 'utf8');
};

const gBytes = writeSnapshot('forever-glossary-snapshot.js', miniGlossary);
const mBytes = writeSnapshot('forever-meta-snapshot.js', miniMeta);
const kb = (b) => (b / 1024).toFixed(1) + ' KB';

if (gBytes + mBytes > SNAPSHOT_BUDGET_KB * 1024) {
  console.error(`✗ 快照体积 ${kb(gBytes + mBytes)} 超过主包预算 ${SNAPSHOT_BUDGET_KB} KB，减少 SNAPSHOT_TERMS 或精简字段`);
  process.exit(1);
}

console.log(`导出完成 → ${path.relative(process.cwd(), MINI)}`);
console.log(`  oss-preview/glossary.json  ${kb(fs.statSync(path.join(OSS_DIR, 'glossary.json')).size)}（${glossary.items.length} 条）`);
console.log(`  oss-preview/dungeons.json  ${kb(fs.statSync(path.join(OSS_DIR, 'dungeons.json')).size)}（${dungeonList.length} 本）`);
console.log(`  oss-preview/meta.json      ${kb(fs.statSync(path.join(OSS_DIR, 'meta.json')).size)}`);
console.log(`  快照词条 ${snapshotItems.length} 条，合计 ${kb(gBytes + mBytes)}（预算 ${SNAPSHOT_BUDGET_KB} KB）`);
console.log(`  覆盖率 L0 ${coverage.L0} / L1 ${coverage.L1} / L2 ${coverage.L2} / L3 ${coverage.L3}（共 ${coverage.total}）`);
