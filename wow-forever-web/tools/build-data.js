#!/usr/bin/env node
/* 数据校验与覆盖率卡口：不通过就退出码非 0，防止把没核实的数据当成品发出去 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'src', 'data');
const errs = [];
const warns = [];
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));

function isOfficial(src) {
  return (src.type || '').indexOf('official') === 0;
}
function checkRecord(kind, rec, sourcesField) {
  const srcs = rec[sourcesField || 'provenance'] || [];
  const lvl = rec.level || 'L3';
  if (lvl === 'L0' && !srcs.some(isOfficial)) {
    errs.push(`${kind} ${rec.id}：标 L0 但没有任何官方来源`);
  }
  if (lvl === 'L0' && !rec.checkedAt && !srcs.some((s) => s.checkedAt)) {
    warns.push(`${kind} ${rec.id}：L0 但缺核对日期`);
  }
  if (srcs.some((s) => /^https?:\/\/(www\.)?(wowhead|foreverchanges|wowclassicforever)/i.test(s.url || '')) && lvl === 'L0') {
    errs.push(`${kind} ${rec.id}：粉丝站来源不能标 L0`);
  }
}
function scanNoPercent(kind, obj, id) {
  const s = JSON.stringify(obj || {});
  if (/\d+(\.\d+)?\s*%/.test(s)) errs.push(`${kind} ${id}：出现百分比数值，掉落禁止写概率`);
}
function scanIcons(kind, obj, id) {
  const s = JSON.stringify(obj || {});
  if (/"iconKey"\s*:\s*"https?:/.test(s)) errs.push(`${kind} ${id}：iconKey 用了外链`);
  if (/(src|url)="\s*http/.test(s) && /icon/i.test(s)) warns.push(`${kind} ${id}：疑似外链图标，需转存本地`);
}

// 术语
const gl = read('glossary.json');
const seenCn = {};
gl.items.forEach((x) => {
  if (!x.cn) errs.push(`glossary ${x.id}：缺中文名`);
  if (!x.kind) errs.push(`glossary ${x.id}：缺 kind`);
  if (!(x.provenance || []).length) errs.push(`glossary ${x.id}：无来源记录`);
  // 同名只在同一职业（或同为种族技能）范围内算重复：跨职业同名是游戏里的正常现象
  const key = (x.classId || 'racial') + '|' + x.cn;
  if (seenCn[key]) errs.push(`glossary：${x.classId || '种族'} 内词条重复「${x.cn}」（${seenCn[key]} 与 ${x.id}）`);
  seenCn[key] = x.id;
  checkRecord('glossary', x);
});

// 副本
const dg = read('dungeons.json');
['newDungeons', 'classicDungeons', 'raids'].forEach((k) => {
  (dg[k] || []).forEach((d) => {
    if (!d.nameEn && !d.nameCn) errs.push(`dungeon ${d.id}：中英文名都没有`);
    (d.bosses || []).forEach((b) => { scanNoPercent('dungeon', b, d.id); });
    scanIcons('dungeon', d, d.id);
    checkRecord('dungeon', d);
  });
});
const ids = [].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || []).map((d) => d.id);
if (new Set(ids).size !== ids.length) errs.push('dungeons：存在重复 id');

// 职业与天赋
const cl = read('classes.json');
if (cl.classes.length !== 9) errs.push(`classes：职业数 ${cl.classes.length}，应为 9`);
cl.classes.forEach((c) => {
  if (!c.id || !c.cn) errs.push(`class ${c.id}：缺字段`);
});
fs.readdirSync(path.join(ROOT, 'talents')).forEach((f) => {
  if (f.charAt(0) === '_') return;
  const t = JSON.parse(fs.readFileSync(path.join(ROOT, 'talents', f), 'utf8'));
  const nodeIds = {};
  (t.trees || []).forEach((tr) => {
    tr.nodes.forEach((n) => {
      if (nodeIds[n.id]) errs.push(`${f}：节点 id 重复 ${n.id}`);
      nodeIds[n.id] = 1;
      if (t.structureStatus === 'confirmed') {
        if (n.tier === undefined || n.column === undefined) errs.push(`${f} ${n.id}：已确认结构但缺层/列`);
        if (n.maxRanks === null || n.maxRanks === undefined) errs.push(`${f} ${n.id}：已确认结构但缺点数上限`);
      }
      (n.requires || []).forEach((r) => {
        if (!nodeIds[r] && !(tr.nodes || []).some((x) => x.id === r)) {
          errs.push(`${f} ${n.id}：前置 ${r} 不存在`);
        }
      });
      checkRecord(f, n);
      scanIcons(f, n, n.id);
      if (n.iconKey && !fs.existsSync(path.join(ROOT, '..', 'img', 'icons', n.iconKey + '.jpg'))) {
        errs.push(`${f} ${n.id}：iconKey ${n.iconKey} 在本地 img/icons 下不存在`);
      }
      if (n.nameConflict && !n.nameAlt) errs.push(`${f} ${n.id}：标了分歧却没有 nameAlt`);
    });
  });
});

// 报告
function tally(arr) {
  const t = { L0: 0, L1: 0, L2: 0, L3: 0 };
  arr.forEach((l) => { t[l] === undefined ? t.L3++ : t[l]++; });
  return t;
}
const pubLevels = [].concat(gl.items.map((x) => x.level || 'L3'),
  [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).map((d) => d.level || 'L3'));
// 天赋节点必须计入总覆盖率，否则 L0 占比会虚高
let talentNodes = 0, talentVerified = 0, talentLevels = [];
fs.readdirSync(path.join(ROOT, 'talents')).forEach((f) => {
  if (f.charAt(0) === '_') return;
  const t = JSON.parse(fs.readFileSync(path.join(ROOT, 'talents', f), 'utf8'));
  (t.trees || []).forEach((tr) => tr.nodes.forEach((n) => {
    talentNodes++; talentLevels.push(n.level || 'L3');
    if (n.nameVerified) talentVerified++;
  }));
});
const cov = tally(pubLevels.concat(talentLevels));
const pub = tally(pubLevels);
const total = pubLevels.length + talentLevels.length;

console.log('成品词条（术语+副本）：L0 ' + pub.L0 + ' / L2 ' + pub.L2 + ' / L3 ' + pub.L3 + '，共 ' + pubLevels.length + ' 条');
console.log('天赋节点 ' + talentNodes + ' 个，名称与官网中文一致 ' + talentVerified + ' 个（' +
  (talentVerified / Math.max(talentNodes, 1) * 100).toFixed(1) + '%），其余标 L2 待实测');

console.log('全站覆盖率：L0 ' + cov.L0 + ' / L1 ' + cov.L1 + ' / L2 ' + cov.L2 + ' / L3 ' + cov.L3 +
  '（共 ' + total + ' 条，L0 占 ' + (cov.L0 / total * 100).toFixed(1) + '%）');
warns.forEach((w) => console.log('  提示 ' + w));
if (errs.length) {
  console.error('\n校验失败 ' + errs.length + ' 项：');
  errs.forEach((e) => console.error('  ✗ ' + e));
  process.exit(1);
}
// 门槛只卡「成品词条」：天赋结构整体是第三方数据挖掘的 L2，不该混进来算比例
if (pub.L0 / Math.max(pubLevels.length, 1) < 0.5) {
  console.error('\n校验失败：成品词条 L0 占比 ' + (pub.L0 / Math.max(pubLevels.length, 1) * 100).toFixed(1) + '% 低于 50% 门槛，不能作为成品发布');
  process.exit(1);
}
console.log('校验通过');
