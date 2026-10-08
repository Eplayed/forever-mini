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
  // 中文名的 L0 只能由官方中文页支撑；英文官方页算 L1
  const cn = rec.cn || rec.nameCn;
  if (lvl === 'L0' && cn && !srcs.some(function (x) { return x.type === 'official_cn'; })) {
    errs.push(`${kind} ${rec.id}：中文名「${cn}」标 L0 但没有 official_cn 来源（英文官方页只能算 L1）`);
  }
  if (lvl === 'L0' && !cn && rec.nameEn) {
    errs.push(`${kind} ${rec.id}：只有官方英文内容却标 L0，按分级定义应标 L1`);
  }
  if (lvl === 'L0' && !rec.checkedAt && !srcs.some((s) => s.checkedAt)) {
    warns.push(`${kind} ${rec.id}：L0 但缺核对日期`);
  }
  // 来源类型与域名必须对得上：粉丝站标成 official_cn 等于把第三方口径冒充官方口径
  srcs.forEach((s) => {
    const t = s.type || '', u = s.url || '';
    if (!u) return;
    if (t === 'official_cn' && !/wow\.blizzard\.cn/.test(u)) {
      errs.push(`${kind} ${rec.id || ''}：official_cn 指向非官方中文域名 ${u}`);
    }
    if (t === 'official_en' && !/blizzard\.(com|cn)/.test(u)) {
      errs.push(`${kind} ${rec.id || ''}：official_en 指向非暴雪域名 ${u}`);
    }
    if ((t === 'fan_db' || t === 'media_cn') && /wow\.blizzard\.cn/.test(u)) {
      errs.push(`${kind} ${rec.id || ''}：官方中文页被标成 ${t}，来源分级写错了`);
    }
  });
  const FAN = /^https?:\/\/(www\.)?(wowhead|foreverchanges|wowclassicforever)/i;
  // 粉丝站链接可以作"人工参照"并存，但不能是 L0 的支撑：有官方中文来源时才允许留 L0
  if (lvl === 'L0' && srcs.some((x) => FAN.test(x.url || '')) && !srcs.some((x) => x.type === 'official_cn')) {
    errs.push(`${kind} ${rec.id}：L0 只靠粉丝站来源支撑`);
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

// 系统卡片
const sy = read('systems.json');
(sy.groups || []).forEach((g) => {
  (g.items || []).forEach((x) => {
    if (!x.id) errs.push(`systems/${g.id}：卡片缺 id`);
    if (!x.nameCn && !x.nameEn) errs.push(`systems ${x.id}：中英文名都没有`);
    if (!(x.provenance || []).length) errs.push(`systems ${x.id}：无来源记录`);
    checkRecord('systems', x);
    scanNoPercent('systems', x, x.id);
  });
});
const sysIds = [];
(sy.groups || []).forEach((g) => (g.items || []).forEach((x) => sysIds.push(x.id)));
if (new Set(sysIds).size !== sysIds.length) errs.push('systems：存在重复卡片 id');

// 职业与天赋
const cl = read('classes.json');
if (cl.classes.length !== 9) errs.push(`classes：职业数 ${cl.classes.length}，应为 9`);
cl.classes.forEach((c) => {
  if (!c.id || !c.cn) errs.push(`class ${c.id}：缺字段`);
  if (c.iconKey && !fs.existsSync(path.join(ROOT, '..', 'img', 'icons', c.iconKey + '.jpg'))) {
    errs.push(`class ${c.id}：iconKey ${c.iconKey} 本地没有文件，跑 tools/fetch-icons.py 补`);
  }
  checkRecord('class', c);
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

// 本站观点类数据：问答与方法说明，防止被当成官方口径
const ch = read('chooser.json');
const classIds = new Set(cl.classes.map((c) => c.id));
if (ch.meta && ch.meta.kind !== 'site-opinion') errs.push('chooser.json：必须标 kind=site-opinion，问答结论不是官方推荐');
const qSeen = {};
(ch.questions || []).forEach((q) => {
  if (!q.id || !q.q) errs.push(`chooser：题目缺 id 或题干 ${q.id || '?'}`);
  if (qSeen[q.id]) errs.push(`chooser：题目 id 重复 ${q.id}`);
  qSeen[q.id] = 1;
  if (!(q.options || []).length) errs.push(`chooser ${q.id}：没有选项`);
  const oSeen = {};
  (q.options || []).forEach((o) => {
    if (oSeen[o.id]) errs.push(`chooser ${q.id}：选项 id 重复 ${o.id}`);
    oSeen[o.id] = 1;
    const keys = Object.keys(o.weight || {});
    if (!keys.length) errs.push(`chooser ${q.id}/${o.id}：没有任何职业权重`);
    if (!o.label) errs.push(`chooser ${q.id}/${o.id}：缺选项文案`);
    keys.forEach((cid) => { if (!classIds.has(cid)) errs.push(`chooser ${q.id}/${o.id}：权重指向未知职业 ${cid}`); });
  });
});
if (Object.keys(qSeen).length < 5) errs.push(`chooser：题目只有 ${Object.keys(qSeen).length} 道，少于 5 道不足以归类`);
const me = read('method.json');
if (!(me.steps || []).length) errs.push('method.json：缺方法说明条目');
(me.steps || []).forEach((x) => { if (!x.title || !x.body) errs.push(`method：说明「${x.title || '?'}」缺标题或正文`); });
if (!me.recheck || !me.onError) errs.push('method.json：缺「错了怎么办」或「何时重核」说明');

// 译名体检的人工判定清单：每条必须可回查，否则等于开后门
const aePath = path.join(ROOT, 'audit-exceptions.json');
if (fs.existsSync(aePath)) {
  const ae = JSON.parse(fs.readFileSync(aePath, 'utf8'));
  const glIds = new Set(gl.items.map((x) => x.id));
  (ae.items || []).forEach((e) => {
    if (!e.id || !glIds.has(e.id)) errs.push(`audit-exceptions：${e.id} 不在词条表里，判定记录成孤儿`);
    ['verdict', 'quote', 'reason', 'decidedAt', 'url'].forEach((k) => {
      if (!e[k]) errs.push(`audit-exceptions ${e.id}：缺 ${k}，判定必须留痕`);
    });
    if (e.verdict === 'keep-L0') {
      const rec = gl.items.filter((x) => x.id === e.id)[0];
      if (rec && rec.level !== 'L0') errs.push(`audit-exceptions ${e.id}：判 keep-L0 但词条不是 L0`);
    }
  });
}

// 上线时间表：日期与原文引用都要可查
const tl = read('timeline.json');
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
(tl.items || []).forEach((x) => {
  if (!x.id || !x.title || !x.what) errs.push(`timeline ${x.id || '?'}：缺 id/标题/说明`);
  if (x.date !== '待定' && x.date !== '择期' && !DATE_RE.test(x.date || '')) errs.push(`timeline ${x.id}：日期「${x.date}」不是 YYYY-MM-DD 也不是待定/择期`);
  if (!['L0', 'L1', 'L2', 'L3'].includes(x.level)) errs.push(`timeline ${x.id}：level 非法 ${x.level}`);
  const ps = x.provenance || [];
  if (!ps.length) errs.push(`timeline ${x.id}：无来源`);
  ps.forEach((pr) => {
    if (pr.type === 'official_cn' && !pr.quote) errs.push(`timeline ${x.id}：官方中文条目缺原文引用 quote`);
    if (pr.type === 'official_cn' && pr.url && pr.url.indexOf('wow.blizzard.cn') < 0) errs.push(`timeline ${x.id}：official_cn 指向非官方中文域名`);
    if (pr.type === 'site-promise' && x.level === 'L0') errs.push(`timeline ${x.id}：本站承诺不能标 L0`);
  });
});
if (tl.meta && tl.meta.timezoneConflict && !tl.meta.timezoneConflict.ours) errs.push('timeline：时区冲突说明缺 ours 字段');

// 技能四态：只允许官方中文整句支撑，名称必须出现在引用里
const ab = read('abilities.json');
const STATE_OK = ['new', 'changed', 'removed', 'renamed'];
const abIds = new Set();
(ab.items || []).forEach((x) => {
  if (abIds.has(x.id)) errs.push(`abilities：条目 id 重复 ${x.id}`);
  abIds.add(x.id);
  if (!classIds.has(x.classId)) errs.push(`abilities ${x.id}：职业 ${x.classId} 不在 classes.json 里`);
  if (STATE_OK.indexOf(x.state) < 0) errs.push(`abilities ${x.id}：状态「${x.state}」非法（只许新增/改动/移除/改名）`);
  if (!x.name || !x.quote) errs.push(`abilities ${x.id}：缺名称或原句`);
  if (x.name && x.quote && x.quote.indexOf(x.name) < 0) errs.push(`abilities ${x.id}：名称「${x.name}」不在原句里，疑似串行`);
  if (x.level === 'L0' && !(x.provenance || []).some((pr) => pr.type === 'official_cn' && pr.quote)) {
    errs.push(`abilities ${x.id}：标 L0 却没有 official_cn 原文引用`);
  }
});
if ((ab.items || []).some((x) => x.state === 'unchanged')) errs.push('abilities：出现"未变"条目——官方没写过，不许凭沉默生成');

// 种族：矩阵与特长只能出自官方中文页，特长名必须原样出现在它自己的整句里
const rc = read('races.json');
const facIds = new Set((rc.factions || []).map((f) => f.id));
const raceIds = new Set();
(rc.races || []).forEach((x) => {
  if (raceIds.has(x.id)) errs.push(`races：id 重复 ${x.id}`);
  raceIds.add(x.id);
  if (!x.nameCn) errs.push(`races ${x.id}：缺中文名`);
  if (!facIds.has(x.faction)) errs.push(`races ${x.id}：阵营 ${x.faction} 不在 factions 里`);
  if (!(x.classes || []).length) errs.push(`races ${x.id}：可选职业为空——官方矩阵没有空行，空着就是解析漏了`);
  (x.classes || []).forEach((cid) => { if (!classIds.has(cid)) errs.push(`races ${x.id}：职业 ${cid} 不在 classes.json 里`); });
  const all = (x.traits || []).concat((x.subgroup && x.subgroup.traits) || []);
  if (!all.length) errs.push(`races ${x.id}：一条特长都没有，官方页每个种族小标题下都有列表`);
  all.forEach((t) => {
    if (!t.name || !t.quote) errs.push(`races ${x.id}：特长缺名称或整句`);
    if (t.name && t.quote && t.quote.indexOf(t.name) < 0) errs.push(`races ${x.id}：特长「${t.name}」不在整句里，疑似串行`);
    if (t.iconKey && !fs.existsSync(path.join(ROOT, '..', 'img', 'icons', t.iconKey + '.jpg'))) {
      errs.push(`races ${x.id}/${t.name}：iconKey ${t.iconKey} 本地没有文件，跑 tools/fetch-icons.py 补`);
    }
  });
  checkRecord('races', x);
  if (x.iconKey && !fs.existsSync(path.join(ROOT, '..', 'img', 'icons', x.iconKey + '.jpg'))) {
    errs.push(`races ${x.id}：iconKey ${x.iconKey} 本地没有文件，跑 tools/fetch-icons.py 补`);
  }
});
if ((rc.classOrder || []).length !== 9) errs.push(`races：classOrder 是 ${(rc.classOrder || []).length} 列，矩阵应覆盖 9 个职业`);
(rc.classOrder || []).forEach((cid) => { if (!classIds.has(cid)) errs.push(`races：classOrder 指向未知职业 ${cid}`); });
(rc.newCombos || []).forEach((c) => {
  const q = ((c.provenance || [])[0] || {}).quote || '';
  if (c.label && q.indexOf(c.label) < 0) errs.push(`races：亮点组合「${c.label}」不在官方整句里`);
});
(rc.conflicts || []).forEach((cf) => {
  if (!cf.a || !cf.a.detail) errs.push(`races：冲突 ${cf.id} 的 a 方缺矩阵明细（官方表格没有整句，只能记明细）`);
  if (!cf.b || !cf.b.quote) errs.push(`races：冲突 ${cf.id} 的 b 方缺原文引用`);
  if (!cf.handling) errs.push(`races：冲突 ${cf.id} 没写处置`);
});
// 来源里出现的 quote 必须能回原文比对：带 quote 就得带 url，official_cn 就得是官方中文域名
function checkQuotes(kind, list) {
  (list || []).forEach((x) => {
    (x.provenance || []).forEach((pr) => {
      if (pr.quote && !pr.url) errs.push(`${kind} ${x.id || ''}：来源有 quote 却没 url，体检脚本无法回原文比对`);
      if (pr.type === 'official_cn' && pr.url && pr.url.indexOf('wow.blizzard.cn') < 0) {
        errs.push(`${kind} ${x.id || ''}：official_cn 指向非官方中文域名`);
      }
    });
  });
}
checkQuotes('races', rc.races);
checkQuotes('races/亮点组合', rc.newCombos);
// 词条表里的种族特长要么回填归属，要么明确进待办；孤儿 raceId 直接失败
gl.items.forEach((x) => {
  if (!x.raceId) return;
  if (!raceIds.has(x.raceId) && !Array.from(raceIds).some((id) => id.indexOf(x.raceId) === 0)) {
    errs.push(`glossary ${x.id}：raceId ${x.raceId} 在 races.json 里找不到`);
  }
});
const racialNoOwner = gl.items.filter((x) => x.kind === 'racial' && !x.raceId);
if (racialNoOwner.length) {
  warns.push(`glossary：${racialNoOwner.length} 条种族特长未回填 raceId（${racialNoOwner.slice(0, 5).map((x) => x.cn).join('、')}）`);
}

// 图标映射是派生产物：必须与 talents/*.json 一致，且每个键都能在本地找到文件
const icPath = path.join(ROOT, 'icons.json');
if (!fs.existsSync(icPath)) {
  errs.push('icons.json 缺失：跑 python3 tools/build-icon-map.py 生成');
} else {
  const ic = JSON.parse(fs.readFileSync(icPath, 'utf8'));
  const want = {};
  fs.readdirSync(path.join(ROOT, 'talents')).filter((f) => f.endsWith('.json') && f.charAt(0) !== '_')
    .sort().forEach((f) => {
      const t = JSON.parse(fs.readFileSync(path.join(ROOT, 'talents', f), 'utf8'));
      const cid = t.classId || f.slice(0, -5);
      (t.trees || []).forEach((tr) => (tr.nodes || []).forEach((n) => {
        if (n.iconKey && n.nameCn) want[cid + '|' + n.nameCn] = n.iconKey;
      }));
    });
  const rcForIcons = JSON.parse(fs.readFileSync(path.join(ROOT, 'races.json'), 'utf8'));
  (rcForIcons.races || []).forEach((x) => {
    const pool = (x.traits || []).concat((x.subgroup && x.subgroup.traits) || []);
    pool.forEach((t) => {
      if (t.iconKey && t.name) {
        want[x.id + '|' + t.name] = t.iconKey;
        if (x.id.indexOf('skyborne') === 0) want['skyborne|' + t.name] = t.iconKey;
      }
    });
  });
  const got = ic.map || {};
  Object.keys(want).forEach((k) => {
    if (got[k] !== want[k]) errs.push(`icons.json 与天赋数据不一致：${k} 应为 ${want[k]}（重跑 build-icon-map.py）`);
  });
  Object.keys(got).forEach((k) => {
    if (!(k in want)) errs.push(`icons.json 有天赋数据里不存在的键：${k}`);
    else if (!fs.existsSync(path.join(ROOT, '..', 'img', 'icons', got[k] + '.jpg'))) {
      errs.push(`icons.json：${k} 指向的本地图标缺失 img/icons/${got[k]}.jpg`);
    }
  });
  const dupN = ((ic.meta || {}).sameNameDifferentIcon || []).length;
  if (dupN) warns.push(`icons.json：${dupN} 处同职业同名挂了两个图标键，映射取后出现的那个（界面只用它做展示，不影响数据）`);
  console.log('图标映射 ' + Object.keys(got).length + ' 条，本地图标文件 ' +
    fs.readdirSync(path.join(ROOT, '..', 'img', 'icons')).filter((f) => f.endsWith('.jpg')).length + ' 张');
}

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
const rcTraitN = (rc.races || []).reduce((a, x) => a + (x.traits || []).length + (((x.subgroup && x.subgroup.traits) || []).length), 0);
console.log('种族 ' + (rc.races || []).length + ' 行 / 特长 ' + rcTraitN + ' 条 / 亮点组合 ' + (rc.newCombos || []).length +
  ' 组，全部出自国服官方中文公告；已回填种族归属的词条 ' + gl.items.filter((x) => x.raceId).length + ' 条');
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
