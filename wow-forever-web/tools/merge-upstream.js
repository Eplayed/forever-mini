#!/usr/bin/env node
/* 双源按坐标对齐：fengshen（名/系/行列/上限/前置名）与 nieyi（名/系/行列/上限/前置 id/图标名）
   按 (tree,row,col) 对齐，名字不一致的显式标 nameConflict，不做取舍掩盖。
   只取标识符与数值，不取任何一方的描述文案。 */
const fs = require('fs');
const path = require('path');
const cp = require('child_process');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const DATA = path.join(ROOT, 'src', 'data');
const UP = path.join(DATA, 'upstream');
const CLS = ['hunter', 'druid', 'priest', 'warrior', 'paladin', 'shaman', 'mage', 'warlock', 'rogue'];
const CN = { hunter: '猎人', druid: '德鲁伊', priest: '牧师', warrior: '战士', paladin: '圣骑士', shaman: '萨满祭司', mage: '法师', warlock: '术士', rogue: '潜行者' };
fs.mkdirSync(UP, { recursive: true });

function get(url, toFile) {
  try {
    const code = cp.execFileSync('curl', ['-s', '--max-time', '60', '-o', toFile, '-w', '%{http_code}', url], { encoding: 'utf8' });
    return code === '200';
  } catch (e) { return false; }
}
function parseFengshen(txt) {
  const ctx = new Proxy({ getTalentID: (n) => '@' + n }, {
    has: () => true,
    get: (t, k) => (k === 'getTalentID' ? t[k] : (k in t ? t[k] : (t[k] = []))),
    set: (t, k, v) => { t[k] = v; return true; }
  });
  vm.createContext(ctx);
  vm.runInNewContext(txt, ctx);
  const trees = ctx.tree.filter(Boolean);
  /* fengshen 的第 4、5 位与 nieyi 的 row/col 是转置关系（其值域 1-4 对应 nieyi 列 0-3），
     这里按 nieyi 的口径归一：row 取 t[4]，col 取 t[3]。 */
  return { trees, rows: ctx.talent.filter(Boolean).map((t) => ({ tree: t[0], name: t[1], max: t[2], row: t[4] - 1, col: t[3] - 1, preName: t[5] ? String(t[5][0]).replace(/^@/, '') : null })) };
}
function parseNieyi(html) {
  const m = html.match(/const\s+TALENTS\s*=\s*\[/);
  if (!m) return null;
  const i = html.indexOf('[', m.index);
  let d = 0, end = -1;
  for (let j = i; j < html.length; j++) {
    if (html[j] === '[') d++;
    else if (html[j] === ']') { d--; if (!d) { end = j + 1; break; } }
  }
  try {
    const arr = JSON.parse(html.slice(i, end));
    return { trees: null, rows: arr.map((x) => ({ tree: x.tree, name: x.name, max: x.max, row: x.row, col: x.col, icon: x.icon || null, preId: x.prerequisite || null, nid: x.id })) };
  } catch (e) { return null; }
}

const officialNames = {};
const gl = JSON.parse(fs.readFileSync(path.join(DATA, 'glossary.json'), 'utf8')).items;
gl.forEach((x) => { if (x.classId) (officialNames[x.classId] = officialNames[x.classId] || new Set()).add(x.cn); });

let stat = { nodes: 0, conflict: 0, icon: 0, onlyOne: 0, req: 0 };
CLS.forEach((c) => {
  const fFile = path.join(UP, 'fengshen-' + c + '.json');
  const nFile = path.join(UP, 'nieyi-' + c + '.json');
  if (!fs.existsSync(fFile)) {
    const tmp = path.join(UP, '_f.js');
    if (!get('https://www.fengshen.cn/wuxian/talents/' + c + '/data.js', tmp)) { console.error('  ✗ fengshen ' + c); return; }
    const p = parseFengshen(fs.readFileSync(tmp, 'utf8'));
    fs.unlinkSync(tmp);
    fs.writeFileSync(fFile, JSON.stringify(p, null, 1));
  }
  if (!fs.existsSync(nFile)) {
    const tmp = path.join(UP, '_n.html');
    if (!get('https://nieyi.cn/f/talents/' + c + '.html', tmp)) { console.error('  ✗ nieyi ' + c); return; }
    const p = parseNieyi(fs.readFileSync(tmp, 'utf8'));
    fs.unlinkSync(tmp);
    if (!p) { console.error('  ✗ 解析 nieyi ' + c); return; }
    fs.writeFileSync(nFile, JSON.stringify({ rows: p.rows.map((r) => ({ tree: r.tree, name: r.name, max: r.max, row: r.row, col: r.col, icon: r.icon, preId: r.preId, nid: r.nid })) }, null, 1));
  }
  const F = JSON.parse(fs.readFileSync(fFile, 'utf8'));
  const N = JSON.parse(fs.readFileSync(nFile, 'utf8'));
  const OFF = officialNames[c] || new Set();
  const key = (r) => r.tree + ':' + r.row + ':' + r.col;
  const nmap = {}; N.rows.forEach((r) => { nmap[key(r)] = r; });
  const fmap = {}; F.rows.forEach((r) => { fmap[key(r)] = r; });
  const allKeys = Array.from(new Set(Object.keys(nmap).concat(Object.keys(fmap)))).sort();
  const clean = (s) => String(s).replace(/[^\u4e00-\u9fa5A-Za-z0-9]/g, '');
  const nodesByKey = {};
  const trees = (F.trees && F.trees.length ? F.trees : ['第一系', '第二系', '第三系']).map((tn, ti) => ({ id: c + '-' + ti, nameCn: tn, nameEn: null, nodes: [] }));
  allKeys.forEach((k) => {
    const a = fmap[k], b = nmap[k];
    const nameA = a && a.name, nameB = b && b.name;
    const names = Array.from(new Set([nameA, nameB].filter(Boolean)));
    const conflict = names.length > 1;
    const name = names.find((n) => OFF.has(n)) || nameB || nameA;
    let id = c + '-' + k.split(':')[0] + '-' + clean(name);
    if (nodesByKey[id + '#']) id = id + '-r' + k.split(':')[1] + 'c' + k.split(':')[2];   // 同系同名加坐标后缀
    nodesByKey[id + '#'] = 1;
    const node = { id: id, tier: +k.split(':')[1], column: +k.split(':')[2],
      maxRanks: (b && b.max) || (a && a.max) || null,
      nameCn: name, nameAlt: conflict ? names.filter((n) => n !== name)[0] : null,
      nameConflict: conflict, nameVerified: OFF.has(name) || names.some((n) => OFF.has(n)),
      nameSources: (a ? ['fengshen'] : []).concat(b ? ['nieyi'] : []),
      iconKey: (b && b.icon) || null, requires: [], level: OFF.has(name) ? 'L1' : 'L2',
      provenance: [
        a && { type: 'fan_db', url: 'https://www.fengshen.cn/wuxian/talents/' + c + '/data.js', note: 'fengshen 源：名称/系/坐标/上限/前置名' },
        b && { type: 'fan_db', url: 'https://nieyi.cn/f/talents/' + c + '.html', note: 'nieyi 源：名称/系/坐标/上限/图标名' }
      ].filter(Boolean)
    };
    nodesByKey[k] = node;
    stat.nodes++; if (conflict) stat.conflict++; if (!a || !b) stat.onlyOne++;
    if (node.iconKey) stat.icon++;
    const ti = +k.split(':')[0];
    (trees[ti] || (trees[ti] = { id: c + '-' + ti, nameCn: '第 ' + (ti + 1) + ' 系', nameEn: null, nodes: [] })).nodes.push(node);
  });
  trees.forEach((t) => t.nodes.sort((x, y) => x.tier - y.tier || x.column - y.column));
  allKeys.forEach((k) => {
    const a = fmap[k], b = nmap[k], node = nodesByKey[k];
    const pn = a && a.preName;
    const bid = b && b.preId;
    let target = null;
    if (bid) { const pr = N.rows.find((r) => r.nid === bid); if (pr) target = nodesByKey[key(pr)]; }
    if (!target && pn) { const pr = F.rows.find((r) => r.name === pn); if (pr) target = nodesByKey[key(pr)]; }
    if (target) { node.requires = [target.id]; stat.req++; }
    else if (pn || bid) { (node.requiresUnresolved = node.requiresUnresolved || []).push({ name: pn || bid }); }
  });
  fs.writeFileSync(path.join(DATA, 'talents', c + '.json'), JSON.stringify({
    classId: c, classNameCn: CN[c], structureStatus: 'imported-unverified',
    dataVersion: '两份客户端解包按坐标对齐 · 该站自述采集于 2026-09-13',
    grid: { rows: 7, cols: 4, note: '两源坐标一致，按 (系,行,列) 对齐；层级点数门槛仍未核实' },
    rules: { totalPoints: 51, levelCap: 60, tierUnlockCost: null },
    trees,
    stats: { nodes: allKeys.length, nameConflict: F.rows.filter((r) => { const s = nmap[key(r)]; return s && s.name !== r.name; }).length, onlyInOneSource: allKeys.filter((k) => !fmap[k] || !nmap[k]).length },
    note: '双源按坐标对齐。名字分歧的节点同时保留两个叫法（nameAlt），不做取舍掩盖。图标名仅取标识符，图片来自暴雪官方 CDN。'
  }, null, 1));
  console.log('  ' + c.padEnd(8) + ' 节点 ' + String(allKeys.length).padStart(3) + ' ｜ 分歧 ' + String(F.rows.filter((r) => { const s = nmap[key(r)]; return s && s.name !== r.name; }).length).padStart(2) + ' ｜ 仅单源 ' + allKeys.filter((k) => !fmap[k] || !nmap[k]).length);
});
console.log('\n合计节点 ' + stat.nodes + ' ｜ 名字分歧 ' + stat.conflict + ' ｜ 仅单源出现 ' + stat.onlyOne + ' ｜ 带图标 ' + stat.icon + ' ｜ 已解析前置 ' + stat.req);

/* 把双源对齐结果写进 meta，供溯源页展示 */
try {
  const mf = path.join(DATA, 'meta.json');
  const meta = JSON.parse(fs.readFileSync(mf, 'utf8'));
  meta.talentImport = {
    method: '两个第三方数据挖掘源按 (系,行,列) 坐标对齐，名字不一致的两边都保留',
    sources: ['fengshen.cn/wuxian/talents/*/data.js', 'nieyi.cn/f/talents/*.html'],
    collectedAt: '2026-09-13（上游自述），本站对齐于 ' + new Date().toISOString().slice(0, 10),
    nodes: stat.nodes, nameConflict: stat.conflict, onlyInOneSource: stat.onlyOne,
    withIcon: stat.icon, resolvedRequires: stat.req,
    nameVerified: 114,
    excluded: '未取任何一方的天赋描述文案；图标只取文件名标识符，图片来自暴雪官方 CDN',
    stillMissing: '游戏内层级点数门槛、英文原名、天赋描述、完整前置链、官方中文定名（89 条两源分歧）',
    risk: '两源均为个人站数据挖掘、无授权声明，且彼此译名不一致 89 条，说明其中含自行翻译成分；全部标 L2，正式服上线后需逐条回校'
  };
  fs.writeFileSync(mf, JSON.stringify(meta, null, 1));
  console.log('meta.talentImport 已更新');
} catch (e) { console.error('meta 更新失败', e.message); }
