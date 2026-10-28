#!/usr/bin/env node
/* 数据校验与覆盖率卡口：不通过就退出码非 0，防止把没核实的数据当成品发出去 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'app', 'data');
const errs = [];
const warns = [];
const datamineOnly = [];
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8'));

function isOfficial(src) {
  const t = src.type || '';
  // datamine_cn = 客户端解包出来的游戏内中文名（经第三方站转述），2026-10-08 决策算 L0 支撑
  return t.indexOf('official') === 0 || t === 'datamine_cn';
}
function checkRecord(kind, rec, sourcesField) {
  const srcs = rec[sourcesField || 'provenance'] || [];
  const lvl = rec.level || 'L3';
  if (lvl === 'L0' && !srcs.some(isOfficial)) {
    errs.push(`${kind} ${rec.id}：标 L0 但没有任何官方来源`);
  }
  // 中文名的 L0 可以由官方中文页支撑，也可以由客户端解包支撑（2026-10-08 用户决策）；
  // 只有英文官方页的算 L1
  const cn = rec.cn || rec.nameCn;
  const cnBacked = srcs.some(function (x) { return x.type === 'official_cn' || x.type === 'datamine_cn'; });
  if (lvl === 'L0' && cn && !cnBacked) {
    errs.push(`${kind} ${rec.id}：中文名「${cn}」标 L0，但既没有 official_cn 也没有 datamine_cn 来源（英文官方页只能算 L1）`);
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
    // 客户端解包来源必须可回查：没 url 或没抓取日期，等于一句没法验证的断言
    if (t === 'datamine_cn') {
      if (!u) errs.push(`${kind} ${rec.id || ''}：datamine_cn 没有 url，无法回查`);
      else if (!/wclbox\.com|wowclassicforever\.info/.test(u)) errs.push(`${kind} ${rec.id || ''}：datamine_cn 指向未知的解包站 ${u}`);
      if (!s.checkedAt) errs.push(`${kind} ${rec.id || ''}：datamine_cn 缺抓取日期`);
    }
    // datamine_en = 客户端表里的英文原文（经第三方客户端数据站取回）。
    // 它只算 L1：不是暴雪域名，也不像 datamine_cn 那样是中文定名的依据，所以不进 isOfficial。
    if (t === 'datamine_en') {
      if (!u) errs.push(`${kind} ${rec.id || ''}：datamine_en 没有 url，无法回查`);
      else if (!/wago\.tools/.test(u)) errs.push(`${kind} ${rec.id || ''}：datamine_en 指向未知的客户端数据站 ${u}`);
      if (!s.checkedAt) errs.push(`${kind} ${rec.id || ''}：datamine_en 缺取回日期`);
    }
  });
  if (lvl === 'L0' && !srcs.some((s) => s.type === 'official_cn') && srcs.some((s) => s.type === 'datamine_cn')) {
    datamineOnly.push(`${kind} ${rec.id || ''}`);
  }
  const FAN = /^https?:\/\/(www\.)?(wowhead|foreverchanges|wowclassicforever)/i;
  // 粉丝站链接可以作"人工参照"并存，但不能是 L0 的支撑：有官方中文来源时才允许留 L0
  const cnOrMine = srcs.some((x) => x.type === 'official_cn' || x.type === 'datamine_cn');
  if (lvl === 'L0' && srcs.some((x) => FAN.test(x.url || '')) && !cnOrMine) {
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
    (d.bosses || []).forEach((b) => {
      scanNoPercent('dungeon', b, d.id);
      if (!b.nameCn) errs.push(`dungeon ${d.id}：首领缺中文名`);
    });
    (d.drops || []).forEach((x, i) => {
      scanNoPercent('drop', x, d.id + '/drop' + i);
      if (!x.itemId || !/^\d+$/.test(String(x.itemId))) errs.push(`dungeon ${d.id}：第 ${i} 条掉落缺物品 ID`);
      if (!x.nameCn) errs.push(`dungeon ${d.id}：第 ${i} 条掉落缺中文名`);
      if (x.level === 'L0') errs.push(`dungeon ${d.id}：第 ${i} 条掉落标了 L0——上游掉落是按经典旧世推的，只能 L2`);
      if (x.iconKey && !fs.existsSync(path.join(ROOT, '..', 'img', 'icons', x.iconKey + '.jpg'))) {
        warns.push(`dungeon ${d.id}：掉落图标 ${x.iconKey} 本地没有，界面退回自绘块`);
      }
    });
    if ((d.drops || []).length && !d.lootNote) warns.push(`dungeon ${d.id}：有掉落却没写上来源说明（lootNote）`);
    // 客户端排队表对账带回来的四个数：要么合规格，要么就是没对上，不许留半成品
    [['partySize', d.partySize], ['partySizeAlt', d.partySizeAlt]].forEach(([k, v]) => {
      if (v === null || v === undefined) return;
      if (!Number.isInteger(v) || v < 1 || v > 40) errs.push(`dungeon ${d.id}：${k}=${v} 不像人数上限（应为 1–40 的整数）`);
    });
    if (d.partySizeAlt && d.partySize === d.partySizeAlt) {
      errs.push(`dungeon ${d.id}：人数上限与另一种说法写成同一个数，那就不该并列摆出来`);
    }
    if (d.levelRangeClient && !/^\d+-\d+$/.test(String(d.levelRangeClient))) {
      errs.push(`dungeon ${d.id}：levelRangeClient=「${d.levelRangeClient}」不是「最低-最高」的写法`);
    }
    if (d.levelRangeClient && d.levelRange &&
      String(d.levelRange).replace(/[–—~]/g, '-') === String(d.levelRangeClient)) {
      errs.push(`dungeon ${d.id}：等级区间客户端与本站已经一致了，还留着另一种说法，界面上会自相矛盾`);
    }
    // 2026-10-13 站主决定等级区间按参考站的副本卡片定稿：界面上只摆一个数，
    // 定稿前官方公告那个数留在 levelRangeOfficial 里（撤掉分歧不等于扔掉另一个数）。
    // 这条校验保证那个"留档"是真留了东西：留一个和现在一样的数，就是装样子。
    if (d.levelRangeOfficial !== undefined && d.levelRangeOfficial !== null) {
      const off = String(d.levelRangeOfficial).replace(/[–—~]/g, '-');
      if (!/^\d+-\d+$/.test(off)) {
        errs.push(`dungeon ${d.id}：levelRangeOfficial=「${d.levelRangeOfficial}」不是「最低-最高」的写法`);
      }
      if (off === String(d.levelRange || '').replace(/[–—~]/g, '-')) {
        errs.push(`dungeon ${d.id}：定稿前那个数与本站采用的数一样，levelRangeOfficial 是空留档，删掉`);
      }
    }
    if (d.nameEnClient && d.nameEn && d.nameEnClient === d.nameEn) {
      errs.push(`dungeon ${d.id}：英文名另一种说法与本站写的同一个词`);
    }
    if (d.clientActivityId !== null && d.clientActivityId !== undefined &&
      d.clientActivityId !== '' && !Number.isInteger(d.clientActivityId)) {
      errs.push(`dungeon ${d.id}：clientActivityId=${d.clientActivityId} 不是整数`);
    }
    if (d.clientAltIds !== null && d.clientAltIds !== undefined &&
      !(Array.isArray(d.clientAltIds) && d.clientAltIds.every((v) => Number.isInteger(v)))) {
      errs.push(`dungeon ${d.id}：clientAltIds 要写成整数数组或留空`);
    }
    scanIcons('dungeon', d, d.id);
    checkRecord('dungeon', d);
  });
});
const ids = [].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || []).map((d) => d.id);
if (new Set(ids).size !== ids.length) errs.push('dungeons：存在重复 id');

/* ---------- 副本任务（2026-10-13 站主定：wclbox 为准，wclbox 没有的按 wowhead 来） ----------
   这份单独一个文件（dungeon-quests.json），不塞进 dungeons.json：副本详情页才用得到，
   列表页与新站都不读它，没必要让每次加载都背上这 230 KB。 */
const dqs = read('dungeon-quests.json');
const dqIds = new Set(ids);
let dqN = 0;
Object.keys(dqs.dungeons || {}).forEach((did) => {
  if (!dqIds.has(did)) { errs.push(`dungeon-quests：${did} 在 dungeons.json 里没有这座本`); return; }
  const e = dqs.dungeons[did];
  (e.quests || []).forEach((y, i) => {
    dqN += 1;
    if (!y.nameCn) errs.push(`dungeon-quests ${did} 第 ${i + 1} 条：没有任务名`);
    ['xp', 'questLevel', 'reqLevel'].forEach((k) => {
      if (y[k] !== null && y[k] !== undefined && !Number.isInteger(y[k])) {
        errs.push(`dungeon-quests ${did}/${y.nameCn}：${k}=「${y[k]}」不是整数`);
      }
    });
    // 两源不一致必须两边都留着：留了 xpAlt 就得同时说明它来自哪
    if (y.xpAlt !== undefined && y.xpAlt === y.xp) {
      errs.push(`dungeon-quests ${did}/${y.nameCn}：xpAlt 与本站取的数一样，那是装样子，删掉`);
    }
    if (y.xpAlt !== undefined && !y.xpAltFrom) {
      errs.push(`dungeon-quests ${did}/${y.nameCn}：留了另一个经验值却没写它来自哪份资料`);
    }
    if (!y.source) errs.push(`dungeon-quests ${did}/${y.nameCn}：没写这条是从哪份资料来的`);
    // 红线：掉落与任务一律不许出现概率
    if (/%/.test(JSON.stringify(y))) errs.push(`dungeon-quests ${did}/${y.nameCn}：出现了百分号，本站不写概率`);
  });
  (e.questItems || []).forEach((y) => {
    if (!y.itemCn) errs.push(`dungeon-quests ${did}：任务物品有一条没有物品名`);
    if (/%/.test(JSON.stringify(y))) errs.push(`dungeon-quests ${did}/${y.itemCn}：任务物品里出现了百分号`);
  });
  if (!(e.provenance || []).length) errs.push(`dungeon-quests ${did}：一条任务都没有出处记录`);
  (e.provenance || []).forEach((p) => {
    if (!p.url) errs.push(`dungeon-quests ${did}：出处没带链接`);
    if (!p.checkedAt) errs.push(`dungeon-quests ${did}：出处没带核对日期`);
  });
});
if ((dqs.meta || {}).counts && dqs.meta.counts.quests !== dqN) {
  errs.push(`dungeon-quests：meta.counts.quests=${dqs.meta.counts.quests} 与实际 ${dqN} 条不一致`);
}
const noQuest = ids.filter((i) => { const e = (dqs.dungeons || {})[i] || {}; return !(e.quests || []).length; });
// 这一段跑在 `const scale = {}` 之前，直接写 scale 会踩暂时性死区（node --check 查不出来，
// 一跑就 ReferenceError）。先收到 var 里，等 scale 建好再挂上去。
var DQ_TOTAL = dqN;
var DQ_DUNGEONS = Object.keys(dqs.dungeons || {}).filter((k) => ((dqs.dungeons[k] || {}).quests || []).length).length;
warns.push(`副本任务：${dqN} 条 / ${DQ_DUNGEONS} 座有记录，`
  + `${noQuest.length} 座两份资料都没有（多为无限新增本，这条本身就是结论）`);

/* ---------- 副本坐标（2026-10-19 站主定：从 DF 那份插件只取"入口在哪"与"首领在副本里的哪儿"） ----------
   单独一个文件（dungeon-geo.json），只有副本详情页读得到，列表页不背这份。
   卡三件事：坐标必须在 0–100、首领名必须是这座本真有的那一条（不许凭空多出一个名字）、
   没有那张底图时必须明确标 noMap——否则页面上会出现"有个点却画不出图"这种半句话。 */
const geo = read('dungeon-geo.json');
const geoArtMaps = new Set(Object.keys(JSON.parse(fs.readFileSync(path.join(ROOT, 'art.json'), 'utf8')).maps || {}));
const geoBossNames = {};
[].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || [])
  .forEach((d) => { geoBossNames[d.id] = new Set((d.bosses || []).map((b) => b.nameCn)); });
let geoEntry = 0, geoBossRows = 0, geoBossPts = 0, geoNoMap = 0, geoMapped = 0;
let geoMapGame = 0, geoMapDrawn = 0;
Object.keys(geo.dungeons || {}).forEach((did) => {
  if (!ids.includes(did)) errs.push(`dungeon-geo：${did} 在 dungeons.json 里没有这座本`);
  const e = geo.dungeons[did] || {};
  const en = e.entry;
  if (en) {
    geoEntry += 1;
    const bad = [[en.x, 'x'], [en.y, 'y']].filter((p) => !(p[0] >= 0 && p[0] <= 100));
    if (bad.length) errs.push(`dungeon-geo ${did}：入口坐标 ${en.x},${en.y} 不在 0–100`);
    if (!en.mapId) errs.push(`dungeon-geo ${did}：入口没带地图号，等于没说这组百分比是对着哪张图`);
    if (!en.zone) errs.push(`dungeon-geo ${did}：入口没写在哪片区域`);
    if (en.mapFile && !geoArtMaps.has(String(en.mapId))) {
      errs.push(`dungeon-geo ${did}：mapFile 与地图号对不上（${en.mapId} → ${en.mapFile}）`);
    }
    if (!en.mapFile && !en.noMap) errs.push(`dungeon-geo ${did}：本地没那张图却没标 noMap`);
    if (en.mapFile && en.noMap) errs.push(`dungeon-geo ${did}：既有 mapFile 又标 noMap`);
    if (en.noMap) geoNoMap += 1;
  }
  if (e.bossMap && !fs.existsSync(path.join(ROOT, '..', e.bossMap))) {
    errs.push(`dungeon-geo ${did}：bossMap 指向的文件不存在（${e.bossMap}）——整目录可删这条要能成立`);
  }
  if (e.bossMap) {
    geoMapped += 1;
    // 底图分两类记（游戏里那张图的截图 / 插件作者自绘），不分类就等于把官方的图说成别人画的
    if (e.bossMapKind === 'game-capture') geoMapGame += 1;
    else if (e.bossMapKind === 'addon-drawn') geoMapDrawn += 1;
    else errs.push(`dungeon-geo ${did}：bossMap 没标是游戏截图还是作者自绘（bossMapKind=「${e.bossMapKind}」）`);
  }
  Object.keys(e.bossPos || {}).forEach((bn) => {
    if (!(geoBossNames[did] || new Set()).has(bn)) {
      errs.push(`dungeon-geo ${did}：首领「${bn}」不在这座本的名单里，不许凭空多一个名字`);
    }
    geoBossRows += 1;      // 按首领条数算；一只首领可能给好几个刷新点，点数在下面单独数
    (e.bossPos[bn] || []).forEach((p, i) => {
      geoBossPts += 1;
      if (!(p.x >= 0 && p.x <= 100) || !(p.y >= 0 && p.y <= 100)) {
        errs.push(`dungeon-geo ${did}/${bn} 第 ${i + 1} 个点：${p.x},${p.y} 不在 0–100`);
      }
    });
  });
  if (!(e.provenance || []).length) errs.push(`dungeon-geo ${did}：没有出处记录`);
  (e.provenance || []).forEach((p) => {
    if (!p.url) errs.push(`dungeon-geo ${did}：出处没带来源`);
    if (!p.checkedAt) errs.push(`dungeon-geo ${did}：出处没带核对日期`);
  });
});
// 红线：这一份里不许出现任何概率措辞，也不许混进对方的讲解句子（百分号是最容易漏的信号）
if (/%/.test(JSON.stringify(geo.dungeons || {}))) errs.push('dungeon-geo：坐标文件里出现了百分号');
if ((geo.meta || {}).counts && geo.meta.counts.bossRows !== geoBossRows) {
  errs.push(`dungeon-geo：meta.counts.bossRows=${geo.meta.counts.bossRows} 与实际 ${geoBossRows} 条不一致`);
}
// 两类底图必须自洽：分起来的座数要等于能画点的座数，也要等于 meta.counts 里写的那两个数
if (geoMapGame + geoMapDrawn !== geoMapped) {
  errs.push(`dungeon-geo：底图分类加起来 ${geoMapGame}+${geoMapDrawn} 不等于能画点的 ${geoMapped} 座`);
}
if ((geo.meta || {}).counts && (geo.meta.counts.bossMapGame !== geoMapGame
  || geo.meta.counts.bossMapDrawn !== geoMapDrawn)) {
  errs.push(`dungeon-geo：meta.counts 写的底图分类 ${geo.meta.counts.bossMapGame}/${geo.meta.counts.bossMapDrawn} `
    + `与实际 ${geoMapGame}/${geoMapDrawn} 不一致`);
}
// 底图是第三方插件带的加工品，每张必须能在 manifest 里查到"哪家插件、哪个版本、哪天取的、哪一类"
if (geoMapped > 0) {
  const dmapManifestPath = path.join(ROOT, '..', 'img', 'art', 'dungeonmaps', 'manifest.json');
  if (!fs.existsSync(dmapManifestPath)) {
    errs.push(`dungeon-geo：${geoMapped} 座在画点，但底图目录没有 manifest.json——第三方素材不留来源是红线`);
  } else {
    const dmRaw = JSON.parse(fs.readFileSync(dmapManifestPath, 'utf8'));
    const dmf = dmRaw.files || {};
    Object.keys(geo.dungeons || {}).forEach((did) => {
      const e = geo.dungeons[did] || {};
      if (!e.bossMap) return;
      const rec = dmf[did] || {};
      ['addon', 'addonVersion', 'fetched', 'origin'].forEach((k) => {
        if (!rec[k]) errs.push(`dungeon-geo ${did}：底图在 manifest 里的记录缺 ${k}`);
      });
      if (rec.file && rec.file !== e.bossMap) {
        errs.push(`dungeon-geo ${did}：成品写的底图 ${e.bossMap} 与 manifest 的 ${rec.file} 不是同一张`);
      }
      // 页面预留位置靠的比例必须等于真实像素——游戏截图是 512² 方的，自绘那几张是 640×427 横的，
      // 统一写死 512/512 会把加载完那一下抖动留在最该看清的图上
      const px = rec.pixels || [];
      if (px.length === 2 && px[0] && px[1]) {
        if (!e.bossMapRatio) {
          errs.push(`dungeon-geo ${did}：底图是 ${px[0]}×${px[1]}，成品却没带 bossMapRatio，页面只能猜比例`);
        } else if (e.bossMapRatio !== `${px[0]}/${px[1]}`) {
          errs.push(`dungeon-geo ${did}：bossMapRatio=${e.bossMapRatio} 与 manifest 记的 ${px[0]}×${px[1]} 不符`);
        }
      }
    });
    if (!(dmRaw.policy || '').includes('删')) {
      errs.push('dungeon-geo：底图 manifest 没写"整目录删掉即回退"这条退路');
    }
  }
}
var GEO_ENTRY = geoEntry;
var GEO_BOSS_ROWS = geoBossRows;
var GEO_BOSS_PTS = geoBossPts;
warns.push(`副本坐标：入口 ${geoEntry} 座（本地缺那张区域图的 ${geoNoMap} 座）· `
  + `首领位置 ${geoBossRows} 条首领 / ${geoBossPts} 个点，其中 ${geoMapped} 座有内部底图可画点`
  + `（游戏内地图的截图 ${geoMapGame} 座、插件作者自绘 ${geoMapDrawn} 座）（快照里名字对不上、没进成品的另计）`);

// 客户端队伍查找器条目：单独一份文件（打进小程序会把座数带歪），界面在副本页并列显示
const qu = read('queue.json');
const qMeta = qu.meta || {};
if (!/^\d+\.\d+\.\d+\.\d+$/.test(String(qMeta.build || ''))) {
  errs.push(`queue：meta.build=「${qMeta.build}」不像客户端版本号，取回时没读到版本`);
}
if (!/wago\.tools/.test(String(qMeta.source || ''))) {
  errs.push(`queue：meta.source 必须指向客户端数据站，现在是「${qMeta.source}」`);
}
if (!qMeta.generatedAt) errs.push('queue：缺取回日期');
const qIdx = {};
let qUnlisted = 0;
(qu.items || []).forEach((x) => {
  const k = String(x.activityId);
  if (qIdx[k]) errs.push(`queue：活动号 ${k} 出现两次（${qIdx[k]} 与 ${x.nameEn}）`);
  qIdx[k] = x.nameEn;
  if (!x.nameEn) errs.push(`queue ${x.activityId}：缺英文原名`);
  if (['dungeon', 'raid'].indexOf(x.kind) < 0) errs.push(`queue ${x.activityId}：kind=${x.kind}`);
  if (!/^\d+-\d+$/.test(String(x.levelRange || ''))) errs.push(`queue ${x.activityId}：等级区间写法不对「${x.levelRange}」`);
  if (x.partySize !== null && (!Number.isInteger(x.partySize) || x.partySize < 1)) {
    errs.push(`queue ${x.activityId}：人数上限不对「${x.partySize}」`);
  }
  if (x.matchedId && ids.indexOf(x.matchedId) < 0) {
    errs.push(`queue ${x.activityId}：说对上了本站的「${x.matchedId}」，副本名单里没有这一座`);
  }
  if (!x.matchedId) qUnlisted += 1;
  const p = (x.provenance || [])[0] || {};
  if (p.type !== 'datamine_en' || !p.checkedAt) errs.push(`queue ${x.activityId}：来源没记成客户端数据表 + 取回日期`);
});
if (qMeta.counts && qMeta.counts.total !== (qu.items || []).length) {
  errs.push(`queue：meta.counts.total 写 ${qMeta.counts.total}，实际 ${(qu.items || []).length} 条——手抄的数会漂，改成现算`);
}
if (qMeta.counts && qMeta.counts.unlisted !== qUnlisted) {
  errs.push(`queue：meta.counts.unlisted 写 ${qMeta.counts.unlisted}，实际 ${qUnlisted} 条`);
}
// 两份文件必须互相认得：副本条目记了活动号，队列里就得有这一条；反之亦然
[].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || []).forEach((d) => {
  if (d.clientActivityId && !qIdx[String(d.clientActivityId)]) {
    errs.push(`dungeon ${d.id}：记了活动号 ${d.clientActivityId}，排队条目里却没有这一条`);
  }
});
Object.keys(qIdx).forEach((k) => {
  const row = (qu.items || []).filter((x) => String(x.activityId) === k)[0];
  if (row && row.matchedId) {
    const d = [].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || [])
      .filter((y) => y.id === row.matchedId)[0];
    // 同一座在表里可以有多条（比如黑暗深渊既有 5 人条目又有 10 人条目），
    // 主号与其余活动号都要认得，否则两份文件就在各说各话
    const known = [String(d && d.clientActivityId)].concat((d && d.clientAltIds) || []).map(String);
    if (d && known.indexOf(k) < 0) {
      errs.push(`queue/dungeon 对不上：${row.nameEn} 指向 ${row.matchedId}，但那座本记的活动号是 ${d.clientActivityId}／${(d.clientAltIds || []).join('、')}`);
    }
  }
});

// 团本页：客户端的队伍查找器里有哪些团队条目、参考站自述了哪几座，两边对得上几个
const raidRows = (qu.items || []).filter((x) => x.kind === 'raid');
const raidNames = {};
raidRows.forEach((x) => { (raidNames[x.nameEn] = raidNames[x.nameEn] || []).push(x); });
const claimed = (dg.raids || []).filter((r) => r.sizeClaim);
const bothSides = (dg.raids || []).filter((r) => r.clientActivityId).map((r) => r.id);
raidRows.forEach((x) => {
  if (!x.difficultyId && x.difficultyId !== 0) {
    errs.push(`queue ${x.activityId}：没记条目号，同名两条就没法说清是两种规模还是两个入口`);
  }
});
claimed.forEach((r) => {
  if (!/^\d+$/.test(String(r.sizeClaim))) errs.push(`raid ${r.id}：自报规模「${r.sizeClaim}」不是个数`);
  if (r.partySize && String(r.partySize) !== String(r.sizeClaim)) {
    warns.push(`raid ${r.id}：参考站说 ${r.sizeClaim} 人、客户端排队条目写 ${r.partySize} 人，界面上两个都要摆`);
  }
});
if (!(dg.raids || []).length) errs.push('dungeons：团本一段是空的，团本页会没内容');
// 规模数字先算着，等下面 scale 定义好再挂上去（在这之前访问 scale 会直接崩）
const raidStats = {
  entries: raidRows.length,
  names: Object.keys(raidNames).length,
  claimed: claimed.length,
  matched: bothSides.length,
  named: (dg.raids || []).filter((r) => r.nameCn).length,
  dungeonVariants: raidRows.filter((x) => x.matchedId && x.matchedId !== 'onyxias-lair'
    && [].concat(dg.newDungeons || [], dg.classicDungeons || []).some((y) => y.id === x.matchedId)).length
};
console.log('团本：客户端排队条目 ' + raidStats.entries + ' 条 / ' + raidStats.names +
  ' 个名字，参考站自述 ' + raidStats.claimed + ' 座，两边都对得上的 ' + raidStats.matched +
  ' 座，有中文名的 ' + raidStats.named + ' 座');

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
  if (datamineOnly.length) {
  warns.push('L0 只有客户端解包支撑（官方中文页没覆盖到）的记录 ' + datamineOnly.length + ' 条：' +
    datamineOnly.slice(0, 8).join('、') + (datamineOnly.length > 8 ? ' 等' : ''));
}
console.log('图标映射 ' + Object.keys(got).length + ' 条，本地图标文件 ' +
    fs.readdirSync(path.join(ROOT, '..', 'img', 'icons')).filter((f) => f.endsWith('.jpg')).length + ' 张');
}

// 客户端原画索引：art.json 里每个路径都要真的在仓库里（整目录可删，删了必须只影响视觉）
const artPath = path.join(ROOT, 'art.json');
if (fs.existsSync(artPath)) {
  const art = JSON.parse(fs.readFileSync(artPath, 'utf8'));
  ['classes', 'dungeons', 'maps', 'races', 'factions', 'factionCities', 'bosses', 'gen'].forEach((k) => {
    Object.keys(art[k] || {}).forEach((id) => {
      if (!fs.existsSync(path.join(ROOT, '..', art[k][id]))) {
        errs.push(`art.json：${k}/${id} 指向的文件不存在（${art[k][id]}）`);
      }
    });
  });
  // 真实整人模型必须精确匹配套装、阵营、种族与导出时的物品快照。
  const real = art.bisRealModels || {};
  if (real.items && real.items.length) {
    if (real.origin !== 'client-derived') errs.push('bisRealModels：来源类型不对');
    const sets = JSON.parse(fs.readFileSync(path.join(ROOT, 'bis.json'), 'utf8')).sets || [];
    const seen = new Set();
    (real.items || []).forEach((m) => {
      const key = `${m.setId}/${m.faction}`;
      if (m.placementVerdict !== 'PASS') errs.push(`bisRealModels：${key} 附件位置未验收通过`);
      if (seen.has(key)) errs.push(`bisRealModels：重复 ${key}`);
      seen.add(key);
      const set = sets.find((s) => s.id === m.setId);
      if (!set || !['alliance', 'horde'].includes(m.faction)) errs.push(`bisRealModels：未知套装或阵营 ${key}`);
      if (set && ['alliance', 'horde'].includes(m.faction)) {
        const race = (rc.races || []).find((x) => x.id === m.raceId);
        if (!race || race.faction !== m.faction || !(race.classes || []).includes(set.cls) || m.bodyType !== 'male') {
          errs.push(`bisRealModels：${key} 种族/职业/体型不匹配`);
        }
        const canon = (rows) => (rows || []).map((x) => [x.slot, x.cell || 1, x.item]);
        if (JSON.stringify(canon(m.dollSnapshot)) !== JSON.stringify(canon(set.doll[m.faction]))) {
          errs.push(`bisRealModels：${key} 全套物品与导出时快照不一致`);
        }
        const expected = m.visibleItems || {};
        const actual = Object.fromEntries((set.doll[m.faction] || [])
          .filter((x) => Object.prototype.hasOwnProperty.call(expected, x.slot))
          .map((x) => [x.slot, x.item]));
        const sorted = (o) => JSON.stringify(Object.entries(o).sort((a, b) => a[0].localeCompare(b[0])));
        if (Object.keys(expected).length < 9 || sorted(actual) !== sorted(expected)) {
          errs.push(`bisRealModels：${key} 可见装备与导出时的配装名单不一致`);
        }
        const weapons = m.displayWeaponItems || [];
        if (!weapons.length || weapons.some((x) => !['主手', '副手', '远程'].includes(x.slot)
          || !(set.doll[m.faction] || []).some((d) => d.slot === x.slot && d.item === x.item))) {
          errs.push(`bisRealModels：${key} 展示武器与配装名单不一致`);
        }
        if (m.visibleWeaponItemId && !weapons.some((x) => x.item === m.visibleWeaponItemId)) {
          errs.push(`bisRealModels：${key} 旧展示武器字段与新清单不一致`);
        }
      }
      if (!/^img\/models\/real\/[a-z0-9-]+\.glb$/.test(m.file || '')) {
        errs.push(`bisRealModels：${key} 文件路径不在独立真实模型目录`); return;
      }
      const file = path.join(ROOT, '..', m.file);
      if (!fs.existsSync(file)) { errs.push(`bisRealModels：${key} 文件不存在`); return; }
      const raw = fs.readFileSync(file);
      if (raw.length !== m.bytes || raw.subarray(0, 4).toString() !== 'glTF') {
        errs.push(`bisRealModels：${key} GLB 长度或格式不符`);
      }
      const hash = require('crypto').createHash('sha256').update(raw).digest('hex');
      if (hash !== m.sha256) errs.push(`bisRealModels：${key} SHA-256 不符`);
    });
  }
  console.log('客户端原画：职业背景 ' + Object.keys(art.classes || {}).length +
    ' 张 / 副本 ' + Object.keys(art.dungeons || {}).length + ' 张 / 区域小地图 ' +
    Object.keys(art.maps || {}).length + ' 张 / 种族头像 ' + Object.keys(art.races || {}).length +
    ' 张 / 阵营徽标 ' + Object.keys(art.factions || {}).length + ' 张 / 首领头像 ' +
    Object.keys(art.bosses || {}).length + ' 张');
  // 首领身上挂的头像路径同样要真在仓库里：删掉 art 目录必须只影响视觉，不能让页面出裂图
  [].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || []).forEach((d) => {
    (d.bosses || []).forEach((b) => {
      if (b.portrait && !fs.existsSync(path.join(ROOT, '..', b.portrait))) {
        errs.push(`dungeons：${d.id}/${b.id} 的头像文件不存在（${b.portrait}）`);
      }
    });
  });
} else {
  warns.push('art.json 缺失：客户端原画全部退回自绘（跑 tools/fetch-art.py 可补）');
}

// 首页与溯源页要的规模数字，边校验边收集，最后统一写进 scale.json（单一来源，不手抄）
const scale = {};
scale.dungeonQuests = DQ_TOTAL;
scale.dungeonGeoEntry = GEO_ENTRY;      // 有入口坐标的座数
scale.dungeonGeoBoss = GEO_BOSS_ROWS;   // 有位置的首领条数
scale.dungeonGeoBossPoints = GEO_BOSS_PTS;  // 点数（一只首领可能给好几个）
scale.dungeonQuestDungeons = DQ_DUNGEONS;

// 专业：配方与采集点的口径检查（数据全部来自客户端解包转述）
const profPath = path.join(ROOT, 'professions.json');
let profOut = null;
if (fs.existsSync(profPath)) {
  const pf = JSON.parse(fs.readFileSync(profPath, 'utf8'));
  profOut = pf;
  const pids = new Set();
  (pf.professions || []).forEach((p) => {
    if (pids.has(p.id)) errs.push(`professions：id 重复 ${p.id}`);
    pids.add(p.id);
    if (!p.nameCn) errs.push(`professions ${p.id}：缺中文名`);
    if (!(p.provenance || []).length) errs.push(`professions ${p.id}：无来源记录`);
    if (p.unparsed && !p.note) errs.push(`professions ${p.id}：标了未解析却没写原因`);
    if (!p.unparsed && !(p.recipes || []).length && !(p.nodes || []).length) {
      errs.push(`professions ${p.id}：既没配方也没采集点，又没标未解析——那是抓漏了`);
    }
    /* 采集点这一层的列映射钉一道（2026-10-27 来源复核记的已知错）：
       钓鱼的源表是「稳定上钩 / 开始咬钩 / 区域」三段，抓取层当年按采集点列序硬套，
       成品里 6 行的名字就成了 25、75 这种光数字、"开始咬钩"落到"可得"栏。
       现在合并层按列头重认成 tier；这条断言钉的是**别再退回那个形状**——
       名字是纯数字、或 tier 少了两个字段，都直接拦红。 */
    (p.nodes || []).forEach((x, i) => {
      const nm = String(x.nameCn || '');
      if (x.kind === 'tier') {
        if (x.reliableAt === null || x.reliableAt === undefined || !x.biteFrom) {
          errs.push(`professions ${p.id} 第 ${i} 段：tier 少了稳定上钩或开始咬钩，页面会空一格`);
        }
      } else if (/^\d+(\.\d+)?$/.test(nm)) {
        errs.push(`professions ${p.id} 第 ${i} 个采集点的名字是纯数字「${nm}」——列映射又错位了`);
      }
      if (!nm) errs.push(`professions ${p.id} 第 ${i} 个采集点没有名字`);
    });
    (p.recipes || []).forEach((x, i) => {
      if (!x.itemId || !/^\d+$/.test(String(x.itemId))) errs.push(`professions ${p.id} 第 ${i} 条配方缺物品 ID`);
      if (!x.nameCn) errs.push(`professions ${p.id} 第 ${i} 条配方缺名称`);
      scanNoPercent('recipe', x, p.id + '/' + (x.nameCn || i));
      // 来源那一层（商人 / 图纸掉落）是 XR 并进来的，字段形状与出处标记一起钉：
      // 商人必须是游戏内专名（不带句子标点），srcFrom 只许 xr，截断计数必须是整数
      if (x.srcFrom !== undefined && x.srcFrom !== 'xr') {
        errs.push(`professions ${p.id}/${x.nameCn || i}：srcFrom 只能是 xr（现在 ${x.srcFrom}）`);
      }
      [['vendors', 'name'], ['formulaDrops', 'npc']].forEach(([key, nameField]) => {
        (x[key] || []).forEach((v) => {
          if (!v || !v[nameField]) { errs.push(`professions ${p.id}/${x.nameCn || i}：${key} 里有一条没有名字`); return; }
          const nm = String(v[nameField]);
          if (/[。；;]/.test(nm)) errs.push(`professions ${p.id}/${x.nameCn || i}：${key} 的名字像句子（${nm.slice(0, 20)}）`);
          if (/%/.test(nm)) errs.push(`professions ${p.id}/${x.nameCn || i}：${key} 里出现百分号（红线）`);
        });
        if (x[key] && !x.srcFrom) errs.push(`professions ${p.id}/${x.nameCn || i}：有 ${key} 却没标 srcFrom`);
      });
      ['vMore', 'dMore'].forEach((k) => {
        if (x[k] !== undefined && (!Number.isInteger(x[k]) || x[k] < 1)) {
          errs.push(`professions ${p.id}/${x.nameCn || i}：${k} 必须是正整数`);
        }
      });
    });
    (p.nodes || []).forEach((x, i) => {
      if (!x.nameCn) errs.push(`professions ${p.id} 第 ${i} 个采集点缺名称`);
      scanNoPercent('node', x, p.id + '/' + (x.nameCn || i));
    });
    checkRecord('professions', p);
  });
  const pr = (pf.professions || []).reduce((s, p) => s + (p.recipes || []).length, 0);
  const pn = (pf.professions || []).reduce((s, p) => s + (p.nodes || []).length, 0);
  const pnew = (pf.professions || []).reduce((s, p) => s + ((p.counts || {}).newRecipes || 0), 0);
  const allRec = (pf.professions || []).reduce((s, p) => s.concat(p.recipes || []), []);
  const pv = allRec.filter((x) => (x.vendors || []).length).length;
  const pd = allRec.filter((x) => (x.formulaDrops || []).length).length;
  scale.profVendors = pv; scale.profDrops = pd;
  // 合并脚本自报的两个数与实际逐条对数：对不上就是"快照与成品不是同一次合并跑出来的"
  const xp = (pf.meta || {}).xrProf || {};
  if (!Object.keys(xp).length) {
    warns.push('professions.meta.xrProf 缺失：配方那一层的商人与图纸掉落没并进来（跑 tools/merge-prof-sources.py）');
  } else {
    if (xp.withVendors !== pv) errs.push(`professions：meta.xrProf.withVendors 记 ${xp.withVendors} · 实数 ${pv}`);
    if (xp.withDrops !== pd) errs.push(`professions：meta.xrProf.withDrops 记 ${xp.withDrops} · 实数 ${pd}`);
  }
  console.log('专业 ' + (pf.professions || []).length + ' 个 / 配方 ' + pr + ' 条（无限新增 ' + pnew +
    '）/ 采集点 ' + pn + ' 个 · 带来源商人 ' + pv + ' 条 · 带图纸掉落 ' + pd + ' 条');
  scale.professions = (pf.professions || []).length;
  scale.recipes = pr; scale.recipesNew = pnew; scale.gatherNodes = pn;
}

// 缺图登记：界面会退回自绘块，但"缺哪些"必须是登记过的，不能靠 404 现场发现
const gapPath = path.join(ROOT, 'icon-gaps.json');
if (fs.existsSync(gapPath)) {
  const gp = JSON.parse(fs.readFileSync(gapPath, 'utf8'));
  /* 2026-10-20 W01：原来这里只查一个方向（登记说缺、其实本地有），
     所以 10-16 之后新引用的 spell_warlock_demonsoul 没登记也照样构建通过，
     页面上悄悄退成字母块。现在两个方向一起查——"引用且本地没有"必须正好等于登记集合，
     漏登记、过期登记、没人引用的死条目都算失败。判定逻辑只在 build-icon-map.py 里一份，
     这里调它，不再抄第二套扫描规则（抄一份就会和它漂）。 */
  try {
    const cp = require('child_process');
    cp.execSync('python3 "' + path.join(__dirname, 'build-icon-map.py') + '" --check',
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    const out = String((e && (e.stdout || e.stderr)) || e.message || e).trim();
    if (/No such file|not found|Permission denied/i.test(out)) {
      warns.push('icon-gaps：拿不到 python3 / build-icon-map.py，这一轮没做双向比对');
    } else {
      out.split('\n').filter((l) => l.trim())
        .forEach((line) => errs.push(/^icon-gaps：/.test(line) ? line : 'icon-gaps：' + line));
    }
  }
  warns.push('缺图登记 ' + (gp.keys || []).length + ' 个图标键（官方 CDN 没有这些文件，界面退回自绘块），' +
    '按文件：' + Object.keys(gp.byFile || {}).map((f) => f + ' ' + gp.byFile[f]).join(' / '));
} else {
  errs.push('icon-gaps.json 缺失：跑 python3 tools/build-icon-map.py 生成缺图登记');
}

// 世界线：区域 / 稀有精英 / 书籍 / 睡袋（全部来自 _shuju 数据包整形）
const worldPath = path.join(ROOT, 'world.json');
let worldOut = null;
if (fs.existsSync(worldPath)) {
  const w = JSON.parse(fs.readFileSync(worldPath, 'utf8'));
  worldOut = w;
  const imgOK = (f) => !f || fs.existsSync(path.join(ROOT, '..', f));
  const zoneNames = new Set((w.zones || []).map((z) => z.nameCn));
  // 城市与地下城内的大陆也算"区域名"（书籍会放在铁炉堡这类主城），取客户端地图清单里的区域名做全集
  (w.maps || []).forEach((m) => (m.zoneNames || []).forEach((n) => zoneNames.add(n)));
  if ((w.meta || {}).mapIdMismatch && w.meta.mapIdMismatch.length) {
    errs.push('world：mapId 两套来源对不上（paint 与稀有/书籍分组），先查上游是否改版：' + w.meta.mapIdMismatch.join('、'));
  }
  const ids = new Set();
  const uniq = (kind, id) => {
    if (ids.has(kind + '|' + id)) errs.push(`world ${kind}：id 重复 ${id}`);
    ids.add(kind + '|' + id);
  };
  if (!(w.zones || []).length) errs.push('world：一个区域都没有，等于抓空了');
  (w.zones || []).forEach((z) => {
    uniq('zone', z.id);
    if (!z.nameCn) errs.push(`world zone ${z.id}：缺中文名`);
    if (!Array.isArray(z.levelRange) || z.levelRange.length !== 2) errs.push(`world zone ${z.id}：等级区间不是两个数`);
    else if (z.levelRange[0] !== null && z.levelRange[0] > z.levelRange[1]) errs.push(`world zone ${z.id}：等级区间倒挂 ${z.levelRange}`);
    else if (z.levelRange.indexOf(null) >= 0 && !z.levelStatus) errs.push(`world zone ${z.id}：等级缺一半却没写 levelStatus，界面会显示 null–null`);
    if (!/(东部王国|卡利姆多|无限新增)/.test(z.continentCn || '')) errs.push(`world zone ${z.id}：不属于任何大陆`);
    if (z.mapFile && !imgOK(z.mapFile)) errs.push(`world zone ${z.id}：小地图文件不存在（${z.mapFile}）`);
    checkRecord('world zone', z);
  });
  // 上游"怎样去新区域"清单里的名字必须都能在区域表里找到，漏一个就是合并时重复建表或丢了
  const newN = (w.zones || []).filter((z) => z.isNew);
  if (!newN.length) errs.push('world：一个无限新增区域都没有，合并时把上游的新区域清单弄丢了');
  if (newN.some((z) => !z.flightNote)) errs.push('world：标了新增却没写飞行路线状态，界面没法交代"怎么去"');
  (w.rares || []).forEach((r) => {
    uniq('rare', r.id);
    if (!r.nameCn) errs.push(`world rare ${r.id}：缺中文名`);
    if (r.zone && !zoneNames.has(r.zone)) errs.push(`world rare ${r.id}：所属区域「${r.zone}」不在区域清单里`);
    if (!r.mark && !r.world) errs.push(`world rare ${r.id}：既没图上百分比坐标也没世界坐标，等于没位置`);
    if (r.mapFile && !imgOK(r.mapFile)) errs.push(`world rare ${r.id}：小地图文件不存在（${r.mapFile}）`);
    (r.drops || []).forEach((d, i) => {
      if (!/^\d+$/.test(String(d.itemId || ''))) errs.push(`world rare ${r.id} 第 ${i} 件掉落缺物品 ID`);
      if (!d.nameCn) errs.push(`world rare ${r.id} 第 ${i} 件掉落缺名称`);
      scanNoPercent('world drop', d, r.id + '/' + i);
    });
    checkRecord('world rare', r);
  });
  const regionSum = (w.rareRegions || []).reduce((a, x) => a + (x.count || 0), 0);
  if (regionSum !== (w.rares || []).length) {
    errs.push(`world：地区汇总合计 ${regionSum} 与稀有明细 ${(w.rares || []).length} 不一致`);
  }
  (w.books || []).forEach((b) => {
    uniq('book', b.id);
    if (!b.nameCn) errs.push(`world book ${b.id}：缺中文名`);
    // 主城（铁炉堡这类）不在大陆区域表里，但客户端给了单独一张图，按 zoneKind 放行
    if (b.zone && b.zoneKind !== 'city' && !zoneNames.has(b.zone)) {
      errs.push(`world book ${b.id}：所在区域「${b.zone}」不在区域清单里，也没标成主城`);
    }
    if (!b.mark && !b.world) errs.push(`world book ${b.id}：标了在册却没有坐标`);
    if (b.mapFile && !imgOK(b.mapFile)) errs.push(`world book ${b.id}：小地图文件不存在（${b.mapFile}）`);
    checkRecord('world book', b);
  });
  (w.booksMissing || []).forEach((b) => { if (!b.nameCn) errs.push('world booksMissing：缺中文名'); });
  (w.bookRewards || []).forEach((r, i) => {
    if (!r.title) errs.push(`world bookReward ${i}：缺称号`);
    if (!(r.items || []).length && !r.noReward) errs.push(`world bookReward ${i}：有门槛没有奖励，又没标注未采集`);
    (r.items || []).forEach((x) => {
      if (!/^\d+$/.test(String(x.itemId || ''))) errs.push(`world bookReward ${i}：奖励缺物品 ID`);
    });
  });
  if (!(w.librarians || []).length) errs.push('world：图书管理员一条都没有，书籍上交环节说不清楚');
  (w.librarians || []).forEach((l) => { if (!l.nameCn) errs.push('world librarian：缺中文名'); });
  const bt = w.bagTool || {};
  if (bt.bag && !/^\d+$/.test(String(bt.bag.itemId || ''))) errs.push('world 睡袋：物品 ID 缺失');
  if (bt.paramsLevel && bt.paramsLevel !== 'L2') errs.push('world 睡袋：机制数值没实测过，分级必须是 L2');
  (bt.camps || []).forEach((c, i) => {
    (c.places || []).forEach((p, j) => {
      if (!p.zone) errs.push(`world 营地 ${i}-${j}：缺所在区域`);
      if (p.mapFile && !imgOK(p.mapFile)) errs.push(`world 营地 ${i}-${j}：小地图文件不存在（${p.mapFile}）`);
    });
  });
  // 没转存成功的图标要能数得出来：界面靠它决定贴图还是自绘块
  const noIcon = [];
  [w.rares, w.books, (w.rareSets || []).map((s) => s.pieces), (w.bookRewards || []).map((r) => r.items)]
    .reduce((a, l) => a.concat(l || []), []).forEach((x) => {
      (x.drops || [x]).forEach((d) => {
        if (d && d.iconKey && !fs.existsSync(path.join(ROOT, '..', 'img', 'icons', d.iconKey + '.jpg'))) noIcon.push(d.iconKey);
      });
    });
  if (noIcon.length) warns.push(`world：${noIcon.length} 个图标键官方 CDN 取不到（多是无限新增装备），界面退回自绘块：` +
    Array.from(new Set(noIcon)).slice(0, 6).join('、'));
  const bagIcon = (w.rares || []).concat(w.books).filter((x) => x.mapFile).length;
  scale.zones = (w.zones || []).length; scale.newZones = newN.length;
  scale.rares = (w.rares || []).length; scale.raresUnplaced = (w.raresUnplaced || []).length;
  scale.books = (w.books || []).length; scale.clientMaps = (w.maps || []).length;
  console.log('世界：区域 ' + (w.zones || []).length + '（含无限新增 ' + newN.length + '）· 稀有 ' +
    (w.rares || []).length + '（带掉落 ' + (w.rares || []).filter((r) => (r.drops || []).length).length +
    '，未定位 ' + (w.raresUnplaced || []).length + '）· 书籍 ' + (w.books || []).length +
    '（未定位 ' + (w.booksMissing || []).length + '）· 小地图 ' + bagIcon + ' 条引用');
} else {
  warns.push('world.json 缺失：世界页只显示区域与稀有的空态（跑 tools/merge-world.js 生成）');
}

// 报告
function tally(arr) {
  const t = { L0: 0, L1: 0, L2: 0, L3: 0 };
  arr.forEach((l) => { t[l] === undefined ? t.L3++ : t[l]++; });
  return t;
}
const worldLevels = worldOut
  ? [].concat((worldOut.zones || []).map((x) => x.level || 'L3'),
    (worldOut.newZones || []).map((x) => x.level || 'L3'),
    (worldOut.rares || []).map((x) => x.level || 'L3'),
    (worldOut.books || []).map((x) => x.level || 'L3'))
  : [];
const pubLevels = [].concat(gl.items.map((x) => x.level || 'L3'),
  [].concat(dg.newDungeons, dg.classicDungeons, dg.raids).map((d) => d.level || 'L3'), worldLevels);
// 天赋节点必须计入总覆盖率，否则 L0 占比会虚高
let talentNodes = 0, talentVerified = 0, talentLevels = [], talentTreeConflict = 0;
const perClassNodes = {};
fs.readdirSync(path.join(ROOT, 'talents')).forEach((f) => {
  if (f.charAt(0) === '_') return;
  const t = JSON.parse(fs.readFileSync(path.join(ROOT, 'talents', f), 'utf8'));
  const cid = f.replace(/\.json$/, '');
  perClassNodes[cid] = 0;
  (t.trees || []).forEach((tr) => {
    // 树级分歧也要计数：2026-10-12 实测有 3 处（奇袭/刺杀、暗影/暗影魔法、元素战斗/元素）。
    // 以前只数节点级，两个解包源收敛成一个叫法之后溯源页写着"0 分歧"，
    // 而树名还在打架——那是把"没记录"当成"没问题"。
    if (tr.nameConflict && tr.nameAlt) talentTreeConflict++;
    tr.nodes.forEach((n) => {
      talentNodes++; talentLevels.push(n.level || 'L3'); perClassNodes[cid]++;
      if (n.nameVerified) talentVerified++;
    });
  });
});
// classes.json 的 talentCount 是手抄的，抄漏过两次（战士写 54 实际 56、德鲁伊写 52 实际 53），
// 而首页职业条与职业页都直接显示它。天赋文件才是真相：对不上就别让它上页面。
(cl.classes || []).forEach((c) => {
  const n = perClassNodes[c.id];
  if (n === undefined) {
    if (c.talentCount) errs.push(`classes ${c.id}：写着 talentCount ${c.talentCount}，但没有 talents/${c.id}.json`);
    return;
  }
  if (c.talentCount !== n) {
    errs.push(`classes ${c.id}：talentCount 写的是 ${c.talentCount}，talents/${c.id}.json 里实际有 ${n} 个节点`);
  }
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
// 改动清单：只许有名称与类别，出现任何句子字段就是抓取阶段没删干净
const chPath = path.join(ROOT, 'changes.json');
let chItems = [];
if (fs.existsSync(chPath)) {
  const ch = JSON.parse(fs.readFileSync(chPath, 'utf8'));
  chItems = ch.items || [];
  const banned = ['rank_texts', 'rankTexts', 'summary', 'forever_note', 'foreverNote',
    'uncertainties', 'tooltip', 'description'];
  const leaked = chItems.filter((x) => banned.some((k) => k in x));
  if (leaked.length) {
    errs.push(`changes：${leaked.length} 条带着句子字段回来了，抓取阶段没删干净（${banned.join('/')}）`);
  }
  const chIds = new Set();
  chItems.forEach((x) => {
    if (chIds.has(x.id)) errs.push(`changes：id 重复 ${x.id}`);
    chIds.add(x.id);
    if (!x.nameCn) errs.push(`changes ${x.id}：缺中文名`);
    if (!x.classId) errs.push(`changes ${x.id}：缺职业`);
    if (x.kind !== 'talent' && x.kind !== 'spell') errs.push(`changes ${x.id}：kind 不是 talent/spell`);
    if (!x.changeKind) errs.push(`changes ${x.id}：缺改动类别`);
    scanNoPercent('change', x, x.id);
    checkRecord('change', x);
  });
  const U = (ch.meta || {}).upstreamCounts || {};
  const cnt = (f) => chItems.filter(f).length;
  const mine = {
    all: chItems.length,
    spells: cnt((x) => x.kind === 'spell'),
    changed: cnt((x) => x.changeKind !== 'unchanged'),
    newTalents: cnt((x) => x.kind === 'talent' && x.changeKind === 'added'),
    changedTalents: cnt((x) => x.kind === 'talent' && (x.changeKind === 'modified' || x.changeKind === 'moved')),
    removedTalents: cnt((x) => x.kind === 'talent' && x.changeKind === 'removed'),
    spellsChanged: cnt((x) => x.kind === 'spell' && x.changeKind !== 'unchanged')
  };
  Object.keys(mine).forEach((k) => {
    if (U[k] !== undefined && U[k] !== mine[k]) {
      errs.push(`changes：${k} 本站数出 ${mine[k]}，上游自报 ${U[k]}，抄漏或抄重了`);
    }
  });
  scale.changes = chItems.length;
  scale.changesTalents = cnt((x) => x.kind === 'talent');
  scale.changesSpells = mine.spells;
  scale.changesNew = mine.newTalents;
  scale.changesModified = mine.changedTalents;   // 改动 + 移位，与来源站自报的 306 同口径
  scale.changesSpellsChanged = mine.spellsChanged;   // 法术里真有过变化的那 256 条（420 是全部法术条目）
  scale.changesRemoved = mine.removedTalents;
  console.log('改动清单 ' + chItems.length + ' 条（新增天赋 ' + mine.newTalents + ' / 改动天赋 ' +
    mine.changedTalents + ' / 移除 ' + mine.removedTalents + ' / 法术有变 ' + mine.spellsChanged +
    '），与上游自报计数逐项一致');
} else {
  warns.push('changes.json 缺失：动态页只余时间线与变更日志（跑 tools/merge-changes.js 生成）');
}

// 职业资料完整度排行：不另建一份手抄表，全部从现有数据派生
const rank = {};
function rk(id) {
  if (!id) return null;
  if (!rank[id]) rank[id] = { classId: id, official: 0, datamine: 0, total: 0 };
  return rank[id];
}
function hasOfficial(x) {
  return (x.provenance || []).some((p) => p.type === 'official_cn');
}
gl.items.forEach((x) => {
  const b = rk(x.classId);
  if (!b) return;
  b.total++;
  if (hasOfficial(x)) b.official++; else b.datamine++;
});
(JSON.parse(fs.readFileSync(path.join(ROOT, 'abilities.json'), 'utf8')).items || []).forEach((x) => {
  const b = rk(x.classId);
  if (!b) return;
  b.total++;
  if (hasOfficial(x)) b.official++; else b.datamine++;
});
chItems.forEach((x) => {
  const b = rk(x.classId);
  if (!b) return;
  b.total++; b.datamine++;
});
fs.readdirSync(path.join(ROOT, 'talents')).forEach((f) => {
  if (f.charAt(0) === '_' || !f.endsWith('.json')) return;
  const t = JSON.parse(fs.readFileSync(path.join(ROOT, 'talents', f), 'utf8'));
  const b = rk(t.classId || f.slice(0, -5));
  if (!b) return;
  (t.trees || []).forEach((tr) => (tr.nodes || []).forEach((n) => {
    b.total++;
    if (n.nameVerified) b.official++; else b.datamine++;
  }));
});
const rankList = Object.keys(rank).map((k) => {
  const r = rank[k];
  r.share = r.total ? Math.round((r.official / r.total) * 1000) / 10 : 0;
  return r;
}).sort((a, b) => b.official - a.official || b.total - a.total);
rankList.forEach((r, i) => { r.place = i + 1; });
if (rankList.length !== 9) warns.push('职业完整度排行只有 ' + rankList.length + ' 个职业有数据');
scale.classRank = rankList;

// ---------- 传承（Legacy）：专长树 + 65 个挑战 ----------
// 口径与改动清单一致：只许有名称与数值结构，出现任何效果说明句子就是抓取阶段没删干净。
const lgPath = path.join(ROOT, 'legacy.json');
let legacyOut = null;
if (fs.existsSync(lgPath)) {
  const lg = JSON.parse(fs.readFileSync(lgPath, 'utf8'));
  legacyOut = lg;
  const LM = lg.meta || {};
  const rules = LM.rules || {};
  const counts = LM.counts || {};
  const LTEXT = ['rank_texts', 'rankTexts', 'unranked_effect', 'unrankedEffect', 'effectRank',
    'faq', 'answer', 'claim', 'tooltip', 'description', 'summary'];
  const lLeaked = [];
  (function walk(node, where) {
    if (Array.isArray(node)) { node.forEach((x, i) => walk(x, where + '#' + i)); return; }
    if (!node || typeof node !== 'object') return;
    Object.keys(node).forEach((k) => {
      if (LTEXT.indexOf(k) >= 0) lLeaked.push(where + '.' + k);
      walk(node[k], where + '.' + k);
    });
  })({ perks: lg.perks, challenges: lg.challenges, rewards: lg.rewards, trees: lg.trees }, 'legacy');
  if (lLeaked.length) {
    errs.push('legacy：' + lLeaked.length + ' 处带着效果句子回来了，抓取阶段没删干净（' + lLeaked.slice(0, 4).join('、') + '）');
  }

  const perkIds = new Set();
  const treeIds = new Set((lg.trees || []).map((t) => t.id));
  (lg.perks || []).forEach((p) => {
    if (perkIds.has(p.id)) errs.push(`legacy perk：id 重复 ${p.id}`);
    perkIds.add(p.id);
    if (!p.nameCn) errs.push(`legacy perk ${p.id}：缺中文名`);
    if (!p.treeId || !treeIds.has(p.treeId)) errs.push(`legacy perk ${p.id}：所属树 ${p.treeId} 不在清单里`);
    if (!(p.maxRank >= 1)) errs.push(`legacy perk ${p.id}：层数上限缺失或为 0`);
    if (p.row === undefined || p.col === undefined) errs.push(`legacy perk ${p.id}：没有槽位坐标`);
    if (p.prerequisite && !perkIds.has(p.prerequisite) && !(lg.perks || []).some((q) => q.id === p.prerequisite)) {
      errs.push(`legacy perk ${p.id}：前置指向不存在的专长 ${p.prerequisite}`);
    }
    scanNoPercent('legacy perk', p, p.id);
    checkRecord('legacy perk', p);
  });
  (lg.trees || []).forEach((t) => {
    const real = (t.slots || []).filter((x) => !x.empty);
    const unknown = real.filter((x) => x.unknown);
    const named = real.filter((x) => !x.unknown);
    if (real.length !== 9) errs.push(`legacy tree ${t.id}：${real.length} 个槽位，客户端树里每棵是 9 个`);
    if (!t.nameCn) errs.push(`legacy tree ${t.id}：缺中文系名`);
    named.forEach((x) => {
      if (!perkIds.has(x.perk)) errs.push(`legacy tree ${t.id}：槽位里的 ${x.perk} 在专长表里没有明细`);
    });
    unknown.forEach((x) => {
      if (!/^unknown-/.test(String(x.perk))) errs.push(`legacy tree ${t.id}：未公开槽位的 id 不像未公开（${x.perk}）`);
    });
    (t.links || []).forEach((l) => {
      [l.from, l.to].forEach((id) => {
        if (!perkIds.has(id) && !/^unknown-/.test(String(id))) {
          errs.push(`legacy tree ${t.id}：前置连线指向对不上任何专长槽位（${id}）`);
        }
      });
    });
  });
  const lchIds = new Set();
  let lchN = 0, lchSum = 0;
  const declaredVariants = new Set((rules.pointVariants || []).flatMap((v) => (v.ids || []).map(String)));
  (lg.challenges || []).forEach((c) => {
    if (!c.nameCn) errs.push('legacy challenge 分类：缺中文名');
    (c.items || []).forEach((x) => {
      lchN++;
      lchSum += Number(x.points) || 0;
      if (!/^\d+$/.test(String(x.id || ''))) errs.push(`legacy challenge ${x.nameCn}：缺数字 id`);
      if (lchIds.has(x.id)) errs.push(`legacy challenge：id 重复 ${x.id}`);
      lchIds.add(x.id);
      if (!x.nameCn) errs.push(`legacy challenge ${x.id}：缺名称`);
      if (!x.requirement) errs.push(`legacy challenge ${x.id}：没有完成条件，这条等于空壳`);
      // 每条挑战的点数以明细为准；与"每项 N 点"不一样的那些，必须在 meta.rules.pointVariants
      // 里逐条声明过——两个说法都留在数据里，但不许静默摆着一个没交代的偏差。
      if (x.points !== rules.pointPerChallenge && !declaredVariants.has(String(x.id))) {
        errs.push(`legacy challenge ${x.id}：点数 ${x.points} 既不等于规则的「每项 ${rules.pointPerChallenge} 点」，也没在 pointVariants 里声明`);
      }
      scanNoPercent('legacy challenge', x, x.id);
      checkRecord('legacy challenge', x);
    });
  });
  if (counts.challenges !== lchN) errs.push(`legacy：挑战明细数出 ${lchN}，meta 写着 ${counts.challenges}`);
  // 客户端给的这个合计是"点数之和"而不是"条数"（每项都是 1 点时两者相等，所以历史上没暴露过）
  if (LM.counts.upstreamChallengeTotal !== undefined &&
    LM.counts.upstreamChallengeTotal !== lchSum) {
    errs.push(`legacy：${lchN} 项挑战的点数合计 ${lchSum}，客户端给的合计 ${LM.counts.upstreamChallengeTotal}，抄漏或抄重了`);
  }
  if (rules.rulesConflict && !declaredVariants.size && rules.clientRulePointPerChallenge === rules.pointPerChallenge) {
    errs.push('legacy：写了点数说法冲突，却没声明任何偏差条目');
  }
  if ((LM.counts.perks || 0) !== (lg.perks || []).length) errs.push('legacy：专长条数与 meta 对不上');
  if ((LM.counts.slots || 0) !== (lg.perks || []).length + (lg.unknownSlots || []).length) {
    errs.push('legacy：槽位数 ≠ 专长数 + 未公开数，树与明细脱节了');
  }
  // ---- 2026-10-23：常规挑战与测试参与记录分账 / 树节点门槛 / 旧值留档 ----
  const lchAll = (lg.challenges || []).reduce((a, c) => a.concat(c.items || []), []);
  const lreg = lchAll.filter((x) => !x.special), lspec = lchAll.filter((x) => x.special);
  if (LM.counts.challengesRegular + LM.counts.challengesSpecial !== LM.counts.challenges) {
    errs.push(`legacy：常规 ${LM.counts.challengesRegular} + 特殊 ${LM.counts.challengesSpecial} ≠ 条目总数 ${LM.counts.challenges}`);
  }
  if (lreg.length !== LM.counts.challengesRegular || lspec.length !== LM.counts.challengesSpecial) {
    errs.push(`legacy：分账与明细数出的一致不上（明细里常规 ${lreg.length}、特殊 ${lspec.length}）`);
  }
  if (lreg.some((x) => x.points !== rules.pointPerChallenge)) {
    errs.push('legacy：标成常规的挑战里有点数不是「每项基准值」的——分账依据就这一条，不能漂');
  }
  if (lspec.some((x) => x.points === rules.pointPerChallenge)) {
    errs.push('legacy：标成特殊的记录点数却和常规一样，那条不该算特殊');
  }
  if ((LM.counts.specialIds || []).slice().sort().join() !== lspec.map((x) => String(x.id)).sort().join()) {
    errs.push('legacy：meta.counts.specialIds 与明细里标了 special 的对不上');
  }
  const regSum = lreg.reduce((a, x) => a + (Number(x.points) || 0), 0);
  if (regSum !== LM.counts.challengePointsRegular) {
    errs.push(`legacy：常规点数合计数出 ${regSum}，meta 写 ${LM.counts.challengePointsRegular}`);
  }
  if (LM.counts.officialChallengeTotal !== regSum) {
    errs.push(`legacy：常规挑战 ${regSum} 点与官方六类合计 ${LM.counts.officialChallengeTotal} 点不等——分账漂了`);
  }
  (lg.challenges || []).forEach((c) => {
    if (c.officialPoints == null) { errs.push(`legacy：分组「${c.nameCn}」没记官方给的类别点数`); return; }
    const n2 = (c.items || []).filter((x) => !x.special).length;
    if (n2 !== c.officialPoints) {
      errs.push(`legacy：分组「${c.nameCn}」常规 ${n2} 条，官方页那一类写 ${c.officialPoints} 点`);
    }
  });
  // 门槛：只认 0/5/10；没有名字的槽位不许带门槛；0 门槛那几格要真能攒够点开最高门槛的那格
  const GATE_OK = [0, 5, 10];
  (lg.perks || []).forEach((p) => {
    if (GATE_OK.indexOf(p.treePointsRequired) < 0) {
      errs.push(`legacy perk ${p.id}：本树门槛是 ${p.treePointsRequired}，不在 0/5/10 里`);
    }
  });
  (lg.trees || []).forEach((t) => {
    const real = (t.slots || []).filter((s) => !s.empty);
    const byId = {};
    (lg.perks || []).forEach((p) => { byId[p.id] = p; });
    real.filter((s) => /^unknown-/.test(String(s.perk))).forEach((s) => {
      if (s.gate != null) errs.push(`legacy tree ${t.id}：未公开槽位带了门槛 ${s.gate}，没名字就不该有门槛`);
    });
    const gates = real.map((s) => s.gate).filter((g) => g != null);
    const top = Math.max.apply(null, gates.concat([0]));
    const atZero = real.filter((s) => s.gate === 0)
      .reduce((a, s) => a + ((byId[s.perk] || {}).maxRank || 0), 0);
    if (atZero < top) {
      errs.push(`legacy tree ${t.id}：0 门槛那几格一共只能投 ${atZero} 点，点不开门槛 ${top} 的那格——门槛语义或数据漂了`);
    }
  });
  // 旧值留档：每条 history 必须带它出自哪个客户端版本与哪天核对的，不然"保留旧值"是空话
  [].concat(lg.perks || [], lchAll, lg.trees || []).forEach((x) => {
    (x.history || []).forEach((h) => {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(h.checkedAt || '')) || !h.atClientBuild) {
        errs.push(`legacy ${x.id}：history 里 ${h.field} 没记出处版本或核对日`);
      }
      if (h.from === undefined) errs.push(`legacy ${x.id}：history 记了变化却没留旧值`);
    });
  });
  if (!(vh => vh && vh.length >= 1)((LM.versionHistory || [])) ||
    LM.versionHistory.slice(-1)[0].clientBuild !== LM.clientBuild) {
    errs.push('legacy：版本轨迹缺失或最后一条不是当前客户端版本');
  }
  if (!rules.unlock || !rules.unlockUpstream) {
    errs.push('legacy：开放条件只剩一种说法（官方那句与转述那句要都留着）');
  }
  if (!rules.unlockSource || !/^\d{4}-\d{2}-\d{2}$/.test(String(rules.unlockCheckedAt || ''))) {
    errs.push('legacy：开放条件没记官方地址与核对日');
  }
  let lastAt = 0;
  (lg.rewards || []).forEach((r, i) => {
    if (!(r.at > lastAt)) errs.push(`legacy reward ${i}：门槛 ${r.at} 没有比上一档高`);
    lastAt = r.at;
    if (!r.nameCn) errs.push(`legacy reward ${i}：缺名称`);
    if (!/^\d+$/.test(String(r.itemId || ''))) errs.push(`legacy reward ${i}：缺物品 ID`);
    checkRecord('legacy reward', r);
  });
  if (!(rules.pointPerChallenge >= 1)) errs.push('legacy：每挑战点数缺失，规则没法交代');
  if (!(rules.launchSpendingCap >= 1 && rules.launchEarnableTotal >= rules.launchSpendingCap)) {
    errs.push(`legacy：首发上限 ${rules.launchSpendingCap} 与可得合计 ${rules.launchEarnableTotal} 说不通`);
  }
  if (!rules.unlock) errs.push('legacy：没写这套系统什么时候开放');
  if (!(LM.notCollected || []).length) errs.push('legacy：没有「这一页没有的」清单，缺口没交代');
  scale.legacy = {
    perks: (lg.perks || []).length, slots: LM.counts.slots || 0,
    unknown: (lg.unknownSlots || []).length, challenges: lchN, rewards: (lg.rewards || []).length,
    cap: rules.launchSpendingCap, total: rules.launchEarnableTotal
  };
  console.log('传承：专长 ' + scale.legacy.perks + ' 个（另有 ' + scale.legacy.unknown +
    ' 个槽位未公开）· 挑战 ' + lchN + ' 项（每项 ' + rules.pointPerChallenge + ' 点，首发上限 ' +
    rules.launchSpendingCap + '）· 进度奖励 ' + scale.legacy.rewards + ' 档');
} else {
  warns.push('legacy.json 缺失：传承页只显示空态（跑 tools/scrape-wclbox-legacy.py + tools/merge-legacy.js 生成）');
}

// ---------- 物品名录（物品线一期） ----------
// 单源 L0（wclbox 转述客户端解包，同 datamine_cn 口径）：清单级五件套，无描述文案。
// 禁词扫描会自动覆盖这个文件（上面的 readdirSync），这里只查结构一致性与规模快照。
const itPath = path.join(ROOT, 'items.json');
if (fs.existsSync(itPath)) {
  const it = JSON.parse(fs.readFileSync(itPath, 'utf8'));
  const its = it.items || [];
  if (its.length !== (it.meta.counts || {}).total) {
    errs.push(`items：物品条数 ${its.length} 与 meta.counts.total ${it.meta.counts.total} 对不上`);
  }
  const itIds = new Set(its.map((x) => x.id));
  if (itIds.size !== its.length) errs.push(`items：物品 id 重复 ${its.length - itIds.size} 个`);
  const stBad = its.filter((x) => ['new', 'changed', 'same', 'missing', 'rebuilt'].indexOf(x.status) < 0).length;
  if (stBad) errs.push(`items：status 越界 ${stBad} 条（只允许 new/changed/same/missing）`);
  const noIcon = its.filter((x) => !x.iconKey).length;
  if (noIcon) warns.push(`items：${noIcon} 件没有图标文件名（缺图要走 icon-gaps 自绘占位，不猜图）`);
  // srv = 第二来源（测试服逐件探针，2026-10-21 A03）：只许 absent/present/没有这个字段。
  // 它不覆盖 status，两条腿并排存；对不上的条数如实数出来上溯源页，不静默取舍。
  const srvBad = its.filter((x) => x.srv !== undefined && ['absent', 'present'].indexOf(x.srv) < 0);
  if (srvBad.length) errs.push(`items：srv 越界 ${srvBad.length} 条（只允许 absent/present，如 ${String(srvBad[0].srv)}）`);
  const srvAbsent = its.filter((x) => x.srv === 'absent').length;
  const srvPresent = its.filter((x) => x.srv === 'present').length;
  const srvConflict = its.filter((x) => x.srv && ((x.srv === 'absent') !== (x.status === 'missing'))).length;
  const metaSrv = (it.meta || {}).srv || {};
  if (metaSrv.absent !== srvAbsent || metaSrv.present !== srvPresent || metaSrv.conflict !== srvConflict) {
    errs.push(`items：meta.srv 与实数不一致（meta ${JSON.stringify(metaSrv)} / 实算 ` +
      `${JSON.stringify({ absent: srvAbsent, present: srvPresent, conflict: srvConflict })}）——` +
      '这条是防 merge-items 改了口径却忘了同步 meta，或者反过来');
  }
  scale.items = its.length;
  scale.itemsSrvAbsent = srvAbsent;
  scale.itemsSrvPresent = srvPresent;
  scale.itemsSrvConflict = srvConflict;
  scale.itemsNew = (it.meta.counts || {}).new || 0;
  console.log('物品名录：' + its.length + ' 件（无限新增 ' + scale.itemsNew + '）·抓取日 ' + (it.meta.fetched || '缺失') +
    '·测试服探针：查不到 ' + srvAbsent + ' / 确认有 ' + srvPresent + '（与名录状态相反 ' + srvConflict + ' 件）');
} else {
  warns.push('items.json 缺失：物品库页将空态（跑 tools/scrape-wclbox-items.py + tools/merge-items.py 生成）');
}

// ---------- 物品详情（物品线二批：方案 A + W2-3 全量后重排层级，2026-10-15 站主拍板） ----------
// 独立文件只有详情抽屉懒加载，不进 search.json、不进小程序导出。字段全部事实性
// （属性/卖价/出处），描述正文与概率不收；禁词扫描自动覆盖本文件，这里查结构。
// 属性与卖价取值顺序：无限测试版客户端解包 > Beta 实测掉落转述 > 社区整理稿。
const itdPath = path.join(ROOT, 'items-detail.json');
if (fs.existsSync(itdPath)) {
  const itd = JSON.parse(fs.readFileSync(itdPath, 'utf8'));
  const itdItems = itd.items || {};
  const ids = Object.keys(itdItems);
  // 名录在这里干两件事：当 id 白名单，也当"这件在无限客户端里到底还有没有"的状态来源
  const baseList = JSON.parse(fs.readFileSync(itPath, 'utf8')).items;
  const baseIds = new Set(baseList.map((x) => x.id));
  const baseStatus = {};
  baseList.forEach((x) => { baseStatus[x.id] = x.status; });
  const unknown = ids.filter((id) => !baseIds.has(Number(id)));
  if (unknown.length) errs.push(`items-detail：${unknown.length} 个 id 不在 items.json 名录里（如 ${unknown.slice(0, 3).join('、')}）`);
  const SRC_WHITELIST = ['dungeon', 'quest'];
  const ST_FROM = ['wclbox', 'gi', 'xr'];
  const SELL_FROM = ['wclbox', 'xr'];
  let badSt = 0, badSell = 0, badSrc = 0, rateHit = 0, badStFrom = 0, badSellFrom = 0;
  let flavor = 0, missingAsForever = 0, badUse = 0;
  for (const id of ids) {
    const r = itdItems[id] || {};
    if (r.st !== undefined && (!Array.isArray(r.st) || r.st.some((s) => typeof s !== 'string'))) badSt++;
    // 教益句是一段一句的纯文本，且必须是去过引号的原文（带引号就是风味句漏进来了）
    if (r.use !== undefined && (typeof r.use !== 'string' || /^[“"]|[”"]$/.test(r.use.trim()))) badUse++;
    // 2026-10-20 A02：这一层的来源从两个变成三个。教学句以前只有 GI/XR 两份带，
    // 白名单就写了 gi/xr；XR 66 起合并层按"内容"而不是"有没有引号"分这一档，
    // wclbox 那份 st 里的「使用：教你学会施放X」也归到了 use 段——它本来就是这三个来源之一
    // （stFrom 的白名单一直含 wclbox）。**实质判据没放宽**：仍然要求 use 是不带引号的一句话，
    // 仍然要求来源是这三个真源之一，凭空冒出来的 key 一样过不了。
    if (r.useFrom !== undefined && ST_FROM.indexOf(r.useFrom) < 0) badUse++;
    if (r.sell !== undefined && (typeof r.sell !== 'string' || /%/.test(r.sell))) badSell++;
    if (r.src !== undefined && SRC_WHITELIST.indexOf(r.src) < 0) badSrc++;
    if (/掉率|掉落概率/.test(JSON.stringify(r))) rateHit++;
    if (r.stFrom !== undefined && ST_FROM.indexOf(r.stFrom) < 0) badStFrom++;
    if (r.sellFrom !== undefined && SELL_FROM.indexOf(r.sellFrom) < 0) badSellFrom++;
    // 红线：tooltip 里"整行被引号包住"的那种风味框（"血色十字军领袖之剑"）不是事实字段。
    // 只拦整行引号——"使用：为角色解锁“炼金师”头衔"这类功能句里的引号是内容本身，不能误删。
    // wclbox 抓取阶段已按 .wp-flavor 丢过，GI/XR 两份是 2026-10-16 才在这条闸上被发现夹了 142 行，
    // 合并层同样剔除，这里做第二道闸（上游快照仍留着原文，删除可回退）。
    (r.st || []).forEach((s) => { if (/^[“"](.*)[”"]$/.test(s.trim())) flavor += 1; });
    // 名录标「无限中没有」的那些件，属性只能来自实测/社区稿；拿经典侧的数值冒充无限的数是编造。
    if (r.stFrom === 'wclbox' && baseStatus[Number(id)] === 'missing') missingAsForever += 1;
  }
  if (badSt) errs.push(`items-detail：${badSt} 条 st 不是字符串数组`);
  if (badUse) errs.push(`items-detail：${badUse} 条 use/useFrom 不对（use 要是不带引号的一句话，useFrom 只能是 wclbox/gi/xr 之一）`);
  if (badSell) errs.push(`items-detail：${badSell} 条 sell 不是字符串或含百分号`);
  if (badSrc) errs.push(`items-detail：${badSrc} 条 src 越界（只允许 dungeon/quest）`);
  if (badStFrom) errs.push(`items-detail：${badStFrom} 条 stFrom 越界（只允许 wclbox/gi/xr）`);
  if (badSellFrom) errs.push(`items-detail：${badSellFrom} 条 sellFrom 越界（只允许 wclbox/xr）`);
  if (flavor) errs.push(`items-detail：${flavor} 行属性里带中文引号（那是风味描述，红线不收）`);
  if (missingAsForever) errs.push(`items-detail：${missingAsForever} 件名录标「无限中没有」却按无限解包取属性`);
  if (rateHit) errs.push(`items-detail：${rateHit} 条出现掉率措辞（红线）`);
  const c = (itd.meta || {}).counts || {};
  if (ids.length !== c.total) errs.push(`items-detail：条数 ${ids.length} 与 meta.counts.total ${c.total} 对不上`);
  const nSt = ids.filter((id) => itdItems[id].st).length;
  if (nSt !== c.st) errs.push(`items-detail：属性条数 ${nSt} 与 meta.counts.st ${c.st} 对不上`);
  const nSell = ids.filter((id) => itdItems[id].sell).length;
  if (nSell !== c.sell) errs.push(`items-detail：卖价条数 ${nSell} 与 meta.counts.sell ${c.sell} 对不上`);
  const nUse = ids.filter((id) => itdItems[id].use).length;
  if (nUse !== c.use) errs.push(`items-detail：教益句 ${nUse} 件与 meta.counts.use ${c.use} 对不上`);
  const nWb = ids.filter((id) => itdItems[id].stFrom === 'wclbox').length;
  if (c.stWb === undefined && nWb === 0) {
    errs.push('items-detail：这份还是只有两份插件源的旧版（W2-3 全量没进来）——'
      + '跑 tools/scrape-wclbox-items-detail.py 再跑 tools/merge-items-detail.py 重生成');
  } else if (nWb !== c.stWb) {
    errs.push(`items-detail：按无限解包取属性的 ${nWb} 件与 meta.counts.stWb ${c.stWb} 对不上`);
  }
  console.log('物品详情：' + ids.length + ' 件（属性 ' + nSt + '：无限解包 ' + c.stWb + ' / 实测 ' + c.stGi
    + ' / 社区稿 ' + c.stXr + ' · 教益句 ' + nUse + ' · 卖价 ' + nSell + ' · 出处 ' + c.src
    + ' · 数值真不同留档 ' + c.conflicts + ' · 只是写法不同 ' + c.formatOnly
    + ' · 名录外孤儿 ' + c.orphans + '）·懒加载不改列表页');
} else {
  warns.push('items-detail.json 缺失：物品库详情抽屉将是空态（跑 tools/extract-addon-items-detail.py + tools/scrape-wclbox-items-detail.py + tools/merge-items-detail.py 生成）');
}

// ---------- 法术书（M1-A，2026-10-16 站主定"以插件为准"后的第一条新板块） ----------
// 名字与状态的口径来自参考站对无限测试版客户端的转述（按 2026-10-08 的定档算 L0，可逐字回查）；
// 两份插件只回填每级 spellId 与学习等级，它们的描述字段在抽取阶段就没落盘。
// 这里查结构与红线：句子不进名字、两说要留档、来源必须可点回。
// 稀有（M1-C）：GI 补进来的那些必须自己说清单源身份，不许混进 L0
(list0 => {
  if (!list0) return;
  const l1 = list0.filter((r) => r.level === 'L1');
  const badL1 = l1.filter((r) => !(r.provenance || []).some((p) => p.type === 'addon'));
  const badLv = list0.filter((r) => ['L0', 'L1', 'L2'].indexOf(r.level) < 0);
  const pct = list0.filter((r) => /%|掉率|概率/.test(JSON.stringify(r.drops || [])));
  if (badLv.length) errs.push(`世界：${badLv.length} 条稀有的分级越界（只允许 L0/L1/L2）`);
  if (badL1.length) errs.push(`世界：${badL1.length} 条 L1 稀有没标"只有插件一家说过"的来源`);
  if (pct.length) errs.push(`世界：${pct.length} 条稀有的掉落里出现百分号或掉率措辞（红线）`);
})((worldOut || {}).rares || null);

// 法术书与成就的清单要在下面的搜索索引里再派生一遍，这里留个出口给索引段用
let spellList = [];
const spellsPath = path.join(ROOT, 'spells.json');
// 合法图标文件名，与 tools/fetch-icons.py 的 KEY_RE、merge-achievements.py 的 ICON_OK_RE 同一条
const ICON_OK = /^[a-z0-9_]{3,64}$/;
if (fs.existsSync(spellsPath)) {
  const sp = JSON.parse(fs.readFileSync(spellsPath, 'utf8'));
  const list = sp.spells || [];
  spellList = list;
  const classIds = new Set((read('classes.json').classes || []).map((c) => c.id));
  const STATES = ['same', 'changed', 'new', 'removed', 'renamed'];
  const RELATIONS = ['talent', 'race', 'earlier', 'baseline'];
  const badName = [], badClass = [], badProv = [], badState = [], badAlt = [], badRank = [], pct = [], badIcon = [];
  const seenIds = new Set();
  let dupIds = 0;
  list.forEach((r, i) => {
    if (!r.name || /[。！？]|\bTODO\b/.test(r.name)) badName.push(r.name || '(空名)');
    if (/%/.test(String(r.name))) pct.push(r.name);
    if (!classIds.has(r.classId)) badClass.push(r.id);
    if (!(r.provenance || []).length || r.provenance.some((p) => !p.url || !p.checkedAt)) badProv.push(r.id);
    // 来源 URL 必须是真地址：写成 /fashu/<职业> 这种模板，玩家点不开、逐字回查也跑不动
    if ((r.provenance || []).some((p) => /[<>]/.test(String(p.url || '')))) badProv.push(r.id + ':模板链接');
    if (r.state != null && STATES.indexOf(r.state) < 0) badState.push(r.id);
    if (r.relation != null && RELATIONS.indexOf(r.relation) < 0) badState.push(r.id);
    // 四态与来历是两族标签：同一条既"有改动"又"天赋技能"说明抓取层把 class 归错族了
    if (r.state != null && r.relation != null) badState.push(r.id + '(两族都有)');
    if (r.ranksAlt !== undefined && r.ranksAlt === r.ranks) badAlt.push(r.id + ':ranks');
    if (r.learnAlt !== undefined && r.learnAlt === r.learnLevel) badAlt.push(r.id + ':learn');
    if (r.ranks != null && !Number.isInteger(r.ranks)) badRank.push(r.id);
    // 图标键就是拼进 <img src> 的文件名：带空格或斜杠的键每次访问稳定 404，还会让两栈的图数对不上
    if (r.iconKey != null && !ICON_OK.test(String(r.iconKey))) badIcon.push(r.id + ':' + r.iconKey);
    (r.spellRanks || []).forEach((k) => {
      if (!Number.isInteger(k.spellId)) badRank.push(r.id + '#id');
    });
    if (seenIds.has(r.id)) dupIds += 1;
    seenIds.add(r.id);
  });
  if (badName.length) errs.push(`spells：${badName.length} 条名字不合规（空或带句子标点，例：${badName.slice(0, 2).join('、')}）`);
  if (pct.length) errs.push(`spells：${pct.length} 条名字里带百分号（那不是名称该有的东西）`);
  if (badClass.length) errs.push(`spells：${badClass.length} 条 classId 不在 classes.json 里（${badClass.slice(0, 3).join('、')}）`);
  if (badProv.length) errs.push(`spells：${badProv.length} 条没有可回查的来源（要带 url + 抓取日期）`);
  if (badState.length) errs.push(`spells：${badState.length} 条状态/来历越界或两族混填（${badState.slice(0, 3).join('、')}）`);
  if (badAlt.length) errs.push(`spells：${badAlt.length} 条"另一说"与主值相同，那不算分歧（${badAlt.slice(0, 3).join('、')}）`);
  if (badRank.length) errs.push(`spells：${badRank.length} 条等级数字段不是整数（${badRank.slice(0, 3).join('、')}）`);
  if (badIcon.length) errs.push(`spells：${badIcon.length} 条图标键不可能是文件名（${badIcon.slice(0, 3).join('、')}）`);
  if (dupIds) errs.push(`spells：${dupIds} 条 id 重复`);
  const c = (sp.meta || {}).counts || {};
  if (c.total !== list.length) errs.push(`spells：条数 ${list.length} 与 meta.counts.total ${c.total} 对不上`);
  const byClass = {};
  list.forEach((r) => { byClass[r.classId] = (byClass[r.classId] || 0) + 1; });
  if (JSON.stringify(Object.keys(byClass).sort().map((k) => [k, byClass[k]]))
    !== JSON.stringify(Object.keys(c.byClass || {}).sort().map((k) => [k, c.byClass[k]]))) {
    errs.push('spells：分职业条数与 meta.counts.byClass 对不上');
  }
  const stSum = STATES.reduce((a, k) => a + (c.byState && c.byState[k] || 0), 0);
  if (stSum + (c.byState ? c.byState.null || 0 : 0) !== list.length) {
    errs.push(`spells：状态计数合计 ${stSum + (c.byState ? c.byState.null || 0 : 0)} 与总条数 ${list.length} 对不上`);
  }
  scale.spells = list.length;
  console.log('法术书：' + list.length + ' 条 / ' + Object.keys(byClass).length + ' 职业（带每级编号 '
    + c.withId + ' · 等级数两说 ' + c.ranksAlt + ' · 起学等级两说 ' + c.learnAlt
    + ' · 插件都没对上 ' + c.noPluginMatch + '）·定名档 L0 可回查');
} else {
  warns.push('spells.json 缺失：法术书那一块会空着（跑 tools/scrape-wclbox-spells.py + tools/merge-spells.py 生成）');
}

// ---------- 成就（M1-B，2026-10-16） ----------
// 目录来自插件那份 211 条；能升到 L0 的只有参考站端点也给出、且中文名逐字相同的那些。
// 成就描述整句两份都不落（抽取阶段删），这里再钉一道：描述进了成品就是构建失败。
// DEV_MARK 与 tools/merge-achievements.py 的 DEV_RE 是同一条规则，两边各留一份是为了互相验证：
// "标了 devOnly 但名字里没有开发标记"这种错只有两处规则一致才不会误伤，改一边立刻红。
const DEV_MARK = /hidden|unused|tracking achievement|beta survey|\bbeta\b/i;
let achList = [];
const achPath = path.join(ROOT, 'achievements.json');
if (fs.existsSync(achPath)) {
  const ach = JSON.parse(fs.readFileSync(achPath, 'utf8'));
  const list = ach.achievements || [];
  achList = list;
  const lvCount = { L0: 0, L1: 0 };
  const bad = [], badProv = [], dupId = [], sentence = [];
  const seen = new Set();
  list.forEach((r) => {
    if (!r.name || !r.achId) bad.push(r.id || String(r.achId));
    // 短号是界面筛选与搜索跳转的落点，缺一条就等于那一类在页面上筛不到
    if (!r.gid) bad.push((r.id || '?') + ' 缺 gid');
    // devOnly 只许标在"客户端没给中文名 + 名字带开发标记"的行上：
    // 标错了就是把一条真成就从玩家眼前藏掉，这种错界面上永远看不出来，只能在这里拦。
    if (r.devOnly === true) {
      if (/[\u4e00-\u9fff]/.test(String(r.name || ''))) bad.push(r.id + ' 标 devOnly 但有中文名');
      else if (!DEV_MARK.test(String(r.name || ''))) bad.push(r.id + ' 标 devOnly 但名字没有开发标记');
    } else if (r.devOnly !== undefined) bad.push((r.id || '?') + ' devOnly 取值不是 true');
    if (r.iconKey != null && !ICON_OK.test(String(r.iconKey))) bad.push(r.id + ' 图标键不合法:' + r.iconKey);
    if (r.level === 'L0') lvCount.L0 += 1; else if (r.level === 'L1') lvCount.L1 += 1;
    else bad.push((r.id || '?') + ' 分级越界:' + r.level);
    // L0 必须是两源都给且名字一致——只有插件一家的，无论多像都不许升
    const provs = r.provenance || [];
    if (!provs.length || provs.some((p) => !p.url || !p.checkedAt)) badProv.push(r.id);
    if (r.level === 'L0' && !(provs.length >= 2)) badProv.push((r.id || '?') + ' 升 L0 但只有一处来源');
    if (r.nameAlt && r.nameAlt === r.name) bad.push(r.id + ' nameAlt 与主值相同');
    if (/[。；]/.test(String(r.name)) || /掉率|掉落概率/.test(JSON.stringify(r))) sentence.push(r.id);
    if (seen.has(r.id)) dupId.push(r.id);
    seen.add(r.id);
  });
  const c = (ach.meta || {}).counts || {};
  if (c.total !== list.length) errs.push(`achievements：条数 ${list.length} 与 meta.counts.total ${c.total} 对不上`);
  if (c.l0 !== lvCount.L0 || c.l1 !== lvCount.L1) {
    errs.push(`achievements：分级计数（记 L0 ${c.l0}/L1 ${c.l1} · 实数 L0 ${lvCount.L0}/L1 ${lvCount.L1}）对不上`);
  }
  const topSum = Object.keys(c.byTop || {}).reduce((a, k) => a + c.byTop[k], 0);
  if (topSum !== list.length) errs.push(`achievements：分大类合计 ${topSum} 与总条数 ${list.length} 对不上`);
  // 下拉与页面上的读数是两件事：groups[].count 对得上源侧自报，groups[].shown 才是屏幕上看到的。
  // 这两套数任何一处对不上，玩家就会看到"大类写 60、翻出来只有 51"这种自相矛盾的页面。
  const gs = c.groups || [];
  const devRows = list.filter((r) => r.devOnly === true);
  if (c.devOnly !== devRows.length) {
    errs.push(`achievements：meta.counts.devOnly 记 ${c.devOnly} · 实数 ${devRows.length} 条开发埋点`);
  }
  if (c.shown !== list.length - devRows.length) {
    errs.push(`achievements：meta.counts.shown 记 ${c.shown} · 应为 ${list.length - devRows.length}`);
  }
  if (!gs.length) errs.push('achievements：meta.counts.groups 缺失，成页面的大类筛选无从建起');
  if (gs.reduce((a, x) => a + (x.count || 0), 0) !== list.length) {
    errs.push('achievements：groups 的 count 合计与总条数对不上');
  }
  if (gs.reduce((a, x) => a + (x.shown || 0), 0) !== list.length - devRows.length) {
    errs.push('achievements：groups 的 shown 合计与页面应列出的条数对不上');
  }
  if (gs.some((x) => !x.gid || !x.top)) errs.push('achievements：groups 里有缺 gid/top 的大类');
  const gidSeen = new Set(gs.map((x) => x.gid));
  const orphanGid = list.filter((r) => !gidSeen.has(r.gid)).length;
  if (orphanGid) errs.push(`achievements：${orphanGid} 条的 gid 不在 groups 里（点进那一类会筛空）`);
  // 缺图登记：noIcon 是"这一条没图标、界面走自绘块"的条数，badIcon 是"上游给的键根本不像文件名、
  // 被丢掉"的条数。这两个数飘了就说明合并脚本与成品不是同一份逻辑跑出来的。
  const noIconRows = list.filter((x) => !x.iconKey).length;
  if (c.noIcon !== noIconRows) errs.push(`achievements：meta.counts.noIcon 记 ${c.noIcon} · 实数 ${noIconRows}`);
  if ((c.badIcon || 0) > noIconRows) errs.push('achievements：badIcon 比缺图条数还多，自相矛盾');
  if (bad.length) errs.push(`achievements：${bad.length} 条结构不合规（如 ${bad.slice(0, 3).join('、')}）`);
  if (badProv.length) errs.push(`achievements：${badProv.length} 条来源不可回查或缺 checkedAt（如 ${badProv.slice(0, 2).join('、')}）`);
  if (sentence.length) errs.push(`achievements：${sentence.length} 条夹了句子或掉率措辞（红线）`);
  if (dupId.length) errs.push(`achievements：${dupId.length} 条 id 重复`);
  scale.achievements = list.length;
  console.log('成就：' + list.length + ' 条 / ' + Object.keys(c.byTop || {}).length + ' 大类（L0 两源互证 '
    + lvCount.L0 + ' · L1 单源待回查 ' + lvCount.L1 + ' · 页面列出 ' + (list.length - devRows.length)
    + '，开发埋点 ' + devRows.length + ' 条不列）·描述整句两份都不落');
} else {
  warns.push('achievements.json 缺失：成就会空着（跑 tools/scrape-wclbox-achievements.py + tools/merge-achievements.py 生成）');
}

// ---------- 猎人宠物（2026-10-28 站主拍板开这一页，源是 GI 0.5.6 的 PetData.lua） ----------
// 这份只有两层：家族 ↔ 宠物技能。它**不是**逐只宠物的名录（哪只在哪个区域、几级、要不要特殊条件，
// 源里就没有），所以卡口盯的是"别让它看起来像名录"：家族数、技能数、两边连线数都要和自报的对得上。
// 三条硬线：① 只许 L1（一家插件转述，没逐行回客户端表、没进游戏验）；② 不许夹成句描述
// （插件里 dcn/den 那种技能说明文字在抽取阶段就该丢，这里再钉一道）；③ iconKey 有值就必须本地有图。
const petsPath = path.join(ROOT, 'pets.json');
let petsOut = null;
if (fs.existsSync(petsPath)) {
  const pets = JSON.parse(fs.readFileSync(petsPath, 'utf8'));
  petsOut = pets;
  const pf = pets.families || [], ps = pets.skills || [], pc = (pets.meta || {}).counts || {};
  const pErr = [];
  if (pc.families !== pf.length) pErr.push(`记 ${pc.families} · 实数 ${pf.length}`);
  if (pc.skills !== ps.length) pErr.push(`技能记 ${pc.skills} · 实数 ${ps.length}`);
  const linkSum = pf.reduce((n, r) => n + ((r.skills || []).length), 0);
  if (pc.links !== linkSum) pErr.push(`家族↔技能连线记 ${pc.links} · 实数 ${linkSum}`);
  const pNewF = pf.filter((r) => r.isNew).length, pNewS = ps.filter((r) => r.isNew).length;
  if (pc.familiesNew !== pNewF) pErr.push(`新增家族记 ${pc.familiesNew} · 实数 ${pNewF}`);
  if (pc.skillsNew !== pNewS) pErr.push(`新增技能记 ${pc.skillsNew} · 实数 ${pNewS}`);
  const famSeen = new Set(), skSeen = new Set();
  const noIcon = [];
  (pf.concat(ps)).forEach((r) => {
    const isFam = !!r.famId;
    if (!r.id || (isFam ? famSeen : skSeen).has(r.id)) {
      pErr.push(`${r.id || '(缺 id)'} 这一条 id 重复或缺`);
      (isFam ? famSeen : skSeen).add(r.id);
    }
    (isFam ? famSeen : skSeen).add(r.id);
    if (!r.name || !r.nameEn) pErr.push(`${r.id}：名字缺一边`);
    if (r.level !== 'L1') pErr.push(`${r.id}：分级是 ${r.level}，这份只许 L1（一家插件转述，未回查）`);
    const pv = r.provenance || [];
    if (!pv.length || !pv[0].url || !pv[0].checkedAt) pErr.push(`${r.id}：来源不可回查或缺核对日`);
    if (isFam) {
      if (typeof r.dmgMod !== 'number' || typeof r.armorMod !== 'number' || typeof r.hpMod !== 'number') {
        pErr.push(`${r.id}：三项修正是空的话要写 0，不能缺字段（缺和"不偏"是两回事）`);
      }
      (r.skills || []).forEach((s) => {
        if (!ps.some((x) => x.spellId === s.id)) pErr.push(`${r.name} 写了技能 ${s.nameEn}，但技能表里没有这条`);
      });
    } else {
      if (!Array.isArray(r.families)) pErr.push(`${r.id}：families 缺失，这条挂不到任何族上`);
      if ((r.families || []).length === 0 && (r.familyMissingIds || []).length === 0) {
        pErr.push(`${r.name}：哪个族都不会用，又没说家族号对不上——两头都没交代`);
      }
    }
    if (r.iconKey && !fs.existsSync(path.join(ROOT, '..', 'img', 'icons', r.iconKey + '.jpg'))) {
      noIcon.push(r.iconKey);
    }
    // 成句文案（插件里的 dcn/den）不许混进来。判据用句号/分号/逗号和"造成…点伤害"这类措辞，
    // **不用感叹号与问号**：宠物技能里真有一条叫「归我了！」（英文原文也是 "Mine!"），
    // 拿 ！ 当句子会把正经名字拦下来——这条是加了判据时踩到才发现的。
    const text = [r.name, r.nameEn].filter(Boolean).join(' ');
    if (/[。；;]/.test(text) || /造成.*点(伤害|治疗)/.test(text)) pErr.push(`${r.id}：名字里夹了句子（红线）`);
  });
  if (noIcon.length) pErr.push(`${noIcon.length} 条 iconKey 本地没图（如 ${noIcon.slice(0, 3).join('、')}）`);
  if (pc.familiesIconless !== pf.filter((r) => r.iconMissing).length) {
    pErr.push(`缺图家族记 ${pc.familiesIconless} · 实数 ${pf.filter((r) => r.iconMissing).length}`);
  }
  if (pErr.length) errs.push('pets：' + pErr.slice(0, 6).join('；') + (pErr.length > 6 ? ` 等 ${pErr.length} 条` : ''));
  scale.pets = pf.length;
  scale.petSkills = ps.length;
  console.log('宠物：家族 ' + pf.length + ' 个（无限新增 ' + pNewF + '）· 技能 ' + ps.length
    + ' 条（新增 ' + pNewS + '）· 两边连线 ' + linkSum + ' 条 · 全部 L1（一家插件转述，未回查）');
} else {
  warns.push('pets.json 缺失：宠物这一格空着（跑 tools/extract-gi-pets.py + tools/merge-pets.py 生成）');
}

// ---------- 配装名单（2026-10-16 站主拍板走 C 方案，红线例外条款见仓库根 AGENTS.md 第五节） ----------
// 这份数据只存"哪件装备在哪个部位、按什么顺序"，数值与名称一律回 items.json 查。
// 卡口因此盯四件事：① 名单里的物品 ID 必须都在我们名录里（否则页面上就是空白格）；
// ② 每套必须带 url + 抓取日（红线要求能回查是哪家列的）；③ 整份文件不许出现掉率与百分比
// （参考站那一栏原文里有"掉率约 0.3%"，抓取阶段已丢，这里再钉一道，防合并脚本改回去）；
// ④ 分级只许 L1——只有一家资料站列过，没人逐字核过"推荐对不对"，不许自己升 L0。
const bisPath = path.join(ROOT, 'bis.json');
let bisSets = [];
if (fs.existsSync(bisPath)) {
  const bis = JSON.parse(fs.readFileSync(bisPath, 'utf8'));
  bisSets = bis.sets || [];
  const baseIds = new Set(JSON.parse(fs.readFileSync(itPath, 'utf8')).items.map((x) => x.id));
  const bErr = [], bMiss = new Set(), bSeen = new Set();
  const clsOf = {};
  bisSets.forEach((s) => {
    if (!s.id || bSeen.has(s.id)) bErr.push('套装 id 缺失或重复:' + s.id);
    bSeen.add(s.id);
    if (!s.cls || !s.clsCn || !s.mode) bErr.push((s.id || '?') + ' 缺 cls/clsCn/mode');
    if (!/^https:\/\//.test(String(s.url || ''))) bErr.push((s.id || '?') + ' 没有可回查的 url');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(s.fetched || ''))) bErr.push((s.id || '?') + ' fetched 不是日期');
    if (!s.level) bErr.push((s.id || '?') + ' 没写等级段');
    (clsOf[s.cls] = clsOf[s.cls] || []).push(s.mode);
    const ids = [];
    ['alliance', 'horde'].forEach((f) => {
      const d = (s.doll || {})[f] || [];
      if (f === 'alliance' && !d.length) bErr.push((s.id || '?') + ' 联盟纸娃娃是空的');
      d.forEach((c) => { if (!c.slot) bErr.push((s.id || '?') + ' 有格子没有部位名'); ids.push(c.item); });
      Object.keys((s.alts || {})[f] || {}).forEach((k) => {
        ((s.alts[f] || {})[k] || []).forEach((i) => ids.push(i));
      });
      ((s.enchants || {})[f] || []).forEach((e) => { ids.push(e.item); if (!e.slots || !e.slots.length) bErr.push((s.id || '?') + ' 附魔没写贴哪个部位'); });
      ((s.consumables || {})[f] || []).forEach((i) => ids.push(i));
    });
    ids.forEach((i) => { if (!baseIds.has(i)) bMiss.add(i); });
  });
  if (bMiss.size) bErr.push(bMiss.size + ' 个物品 ID 不在 items.json 名录里（如 ' + Array.from(bMiss).slice(0, 5).join('、') + '）');
  if (Object.keys(clsOf).length !== 9) bErr.push('职业数 ' + Object.keys(clsOf).length + '，应该是 9 个');
  if (bisSets.length < 30) bErr.push('套数 ' + bisSets.length + '，比参考站自报的 38 少太多，像是抓漏了');
  const blob = JSON.stringify(bis);
  if (/掉率|掉落概率/.test(blob)) bErr.push('配装名单里出现掉率措辞（红线：掉落不写百分比）');
  const pct = blob.match(/\d+(?:\.\d+)?%/);
  if (pct) bErr.push('配装名单里出现百分比 ' + pct[0] + '（红线同上）');
  if ((bis.meta || {}).level_grading !== 'L1') bErr.push('配装线分级必须是 L1（只有一家列过），现在是 ' + (bis.meta || {}).level_grading);
  const c = (bis.meta || {}).counts || {};
  if (c.sets !== bisSets.length) bErr.push(`bis：套数 ${bisSets.length} 与 meta.counts.sets ${c.sets} 对不上`);
  // ---- 第二份名单（meta.alt）----
  // 只查结构与自报数对不对，**不查里面每件装备在不在我们名录里**：对面提了而我们没有的那件
  // （实测 1 件 #9395）本来就该留着，界面上标"本站名录里没有"，不能在这里被当成脏数据抹掉。
  const alt = (bis.meta || {}).alt;
  if (alt) {
    const ac = alt.counts || {};
    let aCells = 0, aRows = 0, aSame = 0, aDiff = 0, aNone = 0;
    bisSets.forEach((s) => {
      ['alliance', 'horde'].forEach((f) => {
        const doll = (s.doll || {})[f] || [];
        aCells += doll.length;
        const seen = new Set();
        ((s.alt || {})[f] || []).forEach((r) => {
          aRows += 1;
          if (r.same) aSame += 1; else aDiff += 1;
          if (!(r.item > 0) || !Array.isArray(r.top)) bErr.push((s.id || '?') + ' 第二份名单有一格缺 item 或 top');
          if (seen.has(r.slot + '-' + r.cell)) bErr.push((s.id || '?') + ' 第二份名单同一格出现两次：' + r.slot + ' ' + r.cell);
          seen.add(r.slot + '-' + r.cell);
          if (!doll.some((x) => x.slot === r.slot && x.cell === r.cell))
            bErr.push((s.id || '?') + ' 第二份名单有一格在纸娃娃上找不到：' + r.slot + ' ' + r.cell);
        });
        doll.forEach((x) => { if (!seen.has(x.slot + '-' + x.cell)) aNone += 1; });
      });
    });
    if (aRows !== ac.slots || aSame !== ac.same || aDiff !== ac.diff || aNone !== ac.notListed)
      bErr.push(`第二份名单的数与逐格重算不符：重算 比 ${aRows} / 一致 ${aSame} / 分歧 ${aDiff} / 没列 ${aNone}`
        + `，meta.alt.counts 记的是 ${ac.slots} / ${ac.same} / ${ac.diff} / ${ac.notListed}`);
    if (aCells !== ac.dollCells) bErr.push(`第二份名单：纸娃娃总格数重算 ${aCells}，记的 ${ac.dollCells}`);
    if (aRows + aNone !== aCells) bErr.push(`第二份名单：比了 ${aRows} + 没列 ${aNone} ≠ 总格数 ${aCells}`);
    if (alt.grade !== 'L1') bErr.push('第二份名单必须按 L1 留档（有两家不等于可以升档），现在是 ' + alt.grade);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(alt.fetched || ''))) bErr.push('第二份名单没写抓取日期');
    if (String(alt.srcSha256 || '').length !== 64) bErr.push('第二份名单没记源文件 sha256（回不去原件就没法复核）');
    scale.bisAltRows = aRows;
    console.log('第二份名单：' + aRows + ' 格做了对照 / 一致 ' + aSame + ' / 分歧 ' + aDiff
      + ' / 另一家没列 ' + aNone + '（L1，两份并列、不裁决）');
  }
  if (bErr.length) errs.push('配装名单：' + bErr.slice(0, 6).join(' ｜ ') + (bErr.length > 6 ? ` …共 ${bErr.length} 条` : ''));
  scale.bisSets = bisSets.length;
  scale.bisClasses = Object.keys(clsOf).length;
  scale.bisItems = (c.items || 0);
  console.log('配装名单：' + bisSets.length + ' 套 / ' + scale.bisClasses + ' 职业 / 等级段 '
    + ((bis.meta || {}).level || '?') + ' 级 / 用到 ' + scale.bisItems + ' 件装备'
    + '（L1，与本站名录逐条对平：分歧 ' + (c.nameConflicts || 0) + ' / ' + (c.slotMismatch || 0)
    + ' 处；另有第二份名单并列展示，见「第二份名单」那行）');
} else {
  warns.push('bis.json 缺失：配装页会空着（跑 tools/scrape-wclbox-bis.py + tools/merge-bis.py 生成）');
}

// ---------- 全站搜索索引 ----------
// 首页那一个搜索框要能搜到所有板块。条目全部从上面已经校验过的数据派生，
// 不另建第二份真相；只收「名称 + 归属」，任何描述性句子都不进索引——
// 第三方转述的原文句子本站不复制，天赋效果原文也不进（红线）。
const SK = {
  tal: ['天赋', 'talent.html', 'q'],
  chg: ['客户端改动', 'updates.html', 'q'],
  term: ['中英术语', 'glossary.html', 'q'],
  abl: ['技能四态', 'skills.html', 'q'],
  // 2026-10-16 M2：法术书（495 条）与成就目录（211 条）进索引。跳转各带自己的归属参数
  // （法术带 c=职业、成就带 g=大类），这样同名条目（两个职业都有「反击」）不会并成一条。
  spl: ['法术书', 'skills.html', 'q'],
  ach: ['成就', 'achievements.html', 'q'],
  // 2026-10-28 猎人宠物那一页：家族与技能分两类，搜「狼」与搜「突进」落到同一页的不同筛选上
  pfam: ['宠物家族', 'pets.html', 'q'],
  psk: ['宠物技能', 'pets.html', 'q'],
  // 2026-10-13 副本线加了"每座本一页"（dungeon.html?d=<本>）：搜到一座本或一个首领，
  // 直接落到那一座的整页，不再落到列表页等人在一堆卡里自己找。
  // 跳转参数仍由条目自己带（见下面 sPush），这里只换落在哪一页。
  dun: ['副本', 'dungeon.html', ''],
  boss: ['副本首领', 'dungeon.html', ''],
  rdd: ['团本', 'raids.html', 'q'],
  zone: ['区域', 'world.html', 'q'],
  rare: ['稀有精英', 'world.html', 'q'],
  bok: ['书籍', 'world.html', 'q'],
  camp: ['睡袋与营地', 'world.html', 'q'],
  prof: ['专业', 'professions.html', ''],
  rec: ['配方', 'professions.html', 'q'],
  gnd: ['采集点', 'professions.html', 'q'],
  // 种族特长页那张跨种族全表已撤（2026-10-12 用户反馈），所以词条直接落到所属种族那一行
  tra: ['种族特长', 'races.html', ''],
  race: ['种族', 'races.html', ''],
  lpg: ['传承专长', 'legacy.html', 'q'],
  lch: ['传承挑战', 'legacy.html', 'q'],
  // 职业词条跳职业页（2026-10-12 起每职业一页），带着职业号落到那一页上
  cls: ['职业', 'classes.html', '']
};
const clsCn = {};
(cl.classes || []).forEach((c) => { clsCn[c.id] = c.cn; });
const SIDX = [];
const SBY = new Map();
// 一条 = [类型, 名称, 归属副标题, 跳转附加参数, 分级]，字段顺序写进 meta.fields。
// 同名且跳转也相同的条目（同一职业技能在两个系里、同一个配方两个专业都能做）合并成一条，
// 副标题把两边的归属都列出来——搜索结果里出现两行一模一样跳过去的东西只会让人以为页面坏了。
const sPush = (k, n, s, x, l) => {
  if (!n) return;
  const key = k + '|' + String(n) + '|' + (x || '');
  const cur = SBY.get(key);
  if (cur) {
    if (s && cur.subs.indexOf(String(s)) < 0) cur.subs.push(String(s));
    // 两个来源分级不一样时取更差的那个，别因为合并把"待实测"说成"已核"
    if (String(l || 'L3') > cur.l) cur.l = String(l || 'L3');
    return;
  }
  SBY.set(key, { k: k, n: String(n), subs: s ? [String(s)] : [], x: x || '', l: String(l || 'L3') });
};
const sFinish = () => {
  SBY.forEach((e) => {
    let s = e.subs.join(' / ');
    if (e.subs.length > 2) s = e.subs.slice(0, 2).join(' / ') + ' 等 ' + e.subs.length + ' 处';
    SIDX.push([e.k, e.n, s, e.x, e.l]);
  });
};

const lvRangeTxt = (r) => {
  const a = r.levelRange || [];
  if (a[0] === null || a[0] === undefined) return r.levelStatus || '等级未定';
  if (a[1] === null || a[1] === undefined || a[1] === a[0]) return a[0] + ' 级';
  return a[0] + '–' + a[1] + ' 级';
};

fs.readdirSync(path.join(ROOT, 'talents')).forEach((f) => {
  if (f.charAt(0) === '_' || !f.endsWith('.json')) return;
  const t = JSON.parse(fs.readFileSync(path.join(ROOT, 'talents', f), 'utf8'));
  const cid = t.classId || f.slice(0, -5);
  (t.trees || []).forEach((tr) => (tr.nodes || []).forEach((n) => {
    sPush('tal', n.nameCn, (clsCn[cid] || cid) + ' · ' + (tr.nameCn || ''), 'c=' + cid, n.level);
  }));
});
chItems.forEach((x) => {
  sPush('chg', x.nameCn, (clsCn[x.classId] || x.classId) + ' · ' + (x.changeCn || ''),
    'c=' + x.classId + (x.kind === 'spell' ? '&w=spell' : ''), x.level);
});
gl.items.forEach((x) => {
  sPush('term', x.cn, x.en || (clsCn[x.classId] || '其他词条'), '', x.level);
});
(ab.items || []).forEach((x) => {
  sPush('abl', x.name, clsCn[x.classId] || x.classId, '', x.level);
});
// 法术书：一条一行，归属写「职业 · 系」。只带名称与归属，任何 tooltip 句子都不进索引（红线）。
spellList.forEach((r) => {
  sPush('spl', r.name, (clsCn[r.classId] || r.classId) + ' · ' + (r.tab || '系未标'),
    'c=' + r.classId, r.level);
});
// 成就：短号 gid 由 merge-achievements.py 写在数据里（界面与索引用同一个号，不各写一份映射）。
// devOnly 那几条（客户端里的开发埋点、问卷、已废弃条目）不进索引——玩家搜不到不该存在的东西。
achList.filter((r) => !r.devOnly).forEach((r) => {
  sPush('ach', r.name, (r.top || '') + ' · ' + (r.cat || ''), 'g=' + (r.gid || 'other'), r.level);
});
[].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || []).forEach((d) => {
  const kindCn = d.kind === 'raid' ? '团队副本' : d.kind === 'new' ? '无限新增' : '经典本';
  sPush('dun', d.nameCn || d.nameEn, kindCn + ' · ' + (d.levelRange || '区间未定'), 'd=' + d.id, d.level);
  (d.bosses || []).forEach((b) => {
    // 带上首领自己的编号：落地后详情页会滚到那个首领那一栏，不用人在整页里再找一次
    sPush('boss', b.nameCn || b.nameEn, d.nameCn || d.nameEn || '', 'd=' + d.id + '&b=' + b.id, b.level);
  });
});
// 团本条目进索引：客户端里的名字是英文原文，本站还没有中文名，搜英文要能跳进来
Object.keys(raidNames).sort().forEach((nm) => {
  const list = raidNames[nm];
  const sizes = [];
  list.forEach((x) => { if (x.partySize && sizes.indexOf(x.partySize) < 0) sizes.push(x.partySize); });
  const matched = list.filter((x) => x.matchedId)[0];
  // 跳转参数留空：板块表里 rdd 已经声明用 q 带名字，这里再写一遍会拼出两个 q=
  sPush('rdd', nm, (sizes.length ? sizes.join('/') + ' 人' : '人数未标') +
    ' · ' + (matched ? '本站已有条目' : '还没有名单'), '', 'L1');
});
(dg.raids || []).forEach((r) => {
  if (!r.nameEn) return;
  sPush('rdd', r.nameEn, '参考站自述 ' + (r.sizeClaim || '?') + ' 人 · 中文名未公布',
    '', r.level || 'L2');
});
if (worldOut) {  // 睡袋本身也是一条可搜的名称（营点是地标名，容易搜不到）
  const sbbag = (worldOut.bagTool || {}).bag;
  if (sbbag) {
    sPush('camp', sbbag.nameCn, '睡袋 · ' + (sbbag.itemLevel ? sbbag.itemLevel + ' 级物品' : '等级未采'),
      't=bag', (worldOut.bagTool || {}).paramsLevel || 'L2');
  }
  (worldOut.zones || []).forEach((z) => {
    sPush('zone', z.nameCn, z.continentCn + ' · ' + lvRangeTxt(z), 't=zones', z.level);
  });
  (worldOut.rares || []).forEach((r) => {
    sPush('rare', r.nameCn, r.zone || '区域未定', 't=rares', r.level);
  });
  (worldOut.raresUnplaced || []).forEach((r) => {
    sPush('rare', r.nameCn, '没有坐标记录', 't=rares', 'L3');
  });
  (worldOut.books || []).forEach((b) => {
    sPush('bok', b.nameCn, b.zone || '区域未定', 't=books', b.level);
  });
  ((worldOut.bagTool || {}).camps || []).forEach((c) => {
    (c.places || []).forEach((p) => {
      sPush('camp', p.landmark || p.whereCn, p.zone || '区域未定', 't=bag', p.level || 'L2');
    });
  });
}
if (profOut) {
  (profOut.professions || []).forEach((p) => {
    const cnt = (p.counts || {}).recipes;
    sPush('prof', p.nameCn, (p.kind === 'craft' ? '制造专业' : '采集专业') + ' · ' +
      (cnt === undefined ? '配方数未采' : cnt + ' 条配方'), 'p=' + p.id, p.level);
    (p.recipes || []).forEach((x) => {
      sPush('rec', x.nameCn, p.nameCn + (x.isNew ? ' · 无限新增' : ''), 'p=' + p.id, x.level || p.level);
    });
    (p.nodes || []).forEach((x) => {
      sPush('gnd', x.nameCn, p.nameCn, 'p=' + p.id, x.level || p.level);
    });
  });
}
const facCn = {};
(rc.factions || []).forEach((x) => { facCn[x.id] = x.nameCn; });
(rc.races || []).forEach((r) => {
  // 天裔的两个子族官方就叫"塑风者天裔/高阶会天裔"，不必再前缀"天裔·"
  const sub = r.subgroup ? r.subgroup.nameCn || r.subgroup.label || '' : '';
  const nm = sub && sub.indexOf(r.nameCn) >= 0 ? sub : (sub ? r.nameCn + '·' + sub : r.nameCn);
  sPush('race', nm, (facCn[r.faction] || r.faction || '阵营未定') + ' · ' +
    (r.classes || []).length + ' 个职业可选', 'r=' + r.faction + '-' + r.id, r.level);
  (r.traits || []).concat(r.subgroup ? r.subgroup.traits || [] : []).forEach((t) => {
    // 带上种族号：种族页那张跨种族全表撤了，点搜索结果要直接落到这个种族的详情上
    sPush('tra', t.name, nm, 'r=' + r.faction + '-' + r.id, r.level);
  });
});
(cl.classes || []).forEach((c) => {
  sPush('cls', c.cn, (c.talentCount || 0) + ' 个天赋节点', 'c=' + c.id, c.nameLevel);
});
if (legacyOut) {
  (legacyOut.perks || []).forEach((x) => {
    sPush('lpg', x.nameCn, '传承 · ' + (x.treeCn || '') + ' · 最多 ' + (x.maxRank || '?') + ' 层', '', 'L0');
  });
  (legacyOut.challenges || []).forEach((grp) => (grp.items || []).forEach((x) => {
    sPush('lch', x.nameCn, '传承挑战 · ' + (grp.nameCn || '') +
      (x.sub ? ' · ' + x.sub : ''), '', x.level);
  }));
}

if (petsOut) {
  (petsOut.families || []).forEach((x) => {
    sPush('pfam', x.name, '宠物家族 · ' + x.nameEn + ' · 会 ' + (x.skills || []).length + ' 条',
      '', x.level);
  });
  (petsOut.skills || []).forEach((x) => {
    const f = x.families || [];
    sPush('psk', x.name, '宠物技能 · ' + (f.length
      ? (f.length > 2 ? f.slice(0, 2).join('、') + ' 等 ' + f.length + ' 族' : f.join('、'))
      : '能用它的族还没对上') + ' · ' + (x.ranks || '?') + ' 级', '', x.level);
  });
}

sFinish();
// 搜索的板块顺序表只有新站那一份（app/src/lib/search.js 的 KIND_ORDER）。
// 漏一个板块不是"顺序不同"，是那一类条目在索引里但搜不出来——分组按这张表列，不在表里的静默丢掉。
const searchJsPath = path.resolve(__dirname, '..', 'app', 'src', 'lib', 'search.js');
const orderM = fs.existsSync(searchJsPath)
  ? fs.readFileSync(searchJsPath, 'utf8').match(/KIND_ORDER\s*=\s*\[([\s\S]*?)\]/)
  : null;
if (!orderM) {
  errs.push('app/src/lib/search.js：找不到搜索的板块顺序表 KIND_ORDER，搜索的分组无从排起');
} else {
  const listed = (orderM[1].match(/'[a-z]+'/g) || []).map((s) => s.replace(/'/g, ''));
  const missing = Object.keys(SK).filter((k) => listed.indexOf(k) < 0);
  if (missing.length) errs.push('KIND_ORDER 缺板块：' + missing.join('、') + '（这些板块的条目在索引里但搜不出来）');
  const stale = listed.filter((k) => !(k in SK));
  if (stale.length) warns.push('KIND_ORDER 里有索引中不存在的板块：' + stale.join('、'));
}
// 条目自带的跳转参数不许和板块声明的重复，否则拼出来的链接有两个 q=，目标页只认第一个
SIDX.forEach((it) => {
  const param = (SK[it[0]] || [])[2];
  if (param && String(it[3] || '').split('&').some((kv) => kv.split('=')[0] === param)) {
    errs.push(`搜索索引 ${it[0]}「${it[1]}」：条目自己带了 ${param}=，板块也声明了 ${param}=，跳过去会有两个同名参数`);
  }
});
// 索引自身的卡口：名字里混进句子、页面不存在、类型没登记，都是数据出问题的信号
// "页面在不在"问的是新站路由表（MIGRATED），不是磁盘上有没有那个 html——旧站已经删了，
// 按文件名找页面会永远找不到，而真正会漏的是"路由加了、这张表没加"。
const routerSrc = fs.readFileSync(path.resolve(__dirname, '..', 'app', 'src', 'router.js'), 'utf8');
const migM = routerSrc.match(/export const MIGRATED = \{([\s\S]*?)\n\};/);
if (!migM) errs.push('app/src/router.js：找不到 MIGRATED 表，搜索索引的跳转目标无从核对');
const PAGES = new Set(migM ? [...migM[1].matchAll(/'([^']+)'\s*:\s*'([^']+)'/g)].map((m) => m[1]) : []);
const seenSid = new Set();
SIDX.forEach((it) => {
  const k = it[0], n = it[1], s = it[2];
  if (!SK[k]) errs.push(`search：类型 ${k} 没在 SK 里登记`);
  if (n.length > 40) errs.push(`search：名称太长像句子（${k} ${n.slice(0, 24)}…）`);
  if (s.length > 44) errs.push(`search：副标题太长像句子（${k} ${n} → ${s.slice(0, 24)}…）`);
  const idu = k + '|' + n + '|' + it[3];
  if (seenSid.has(idu)) errs.push(`search：合并后仍有重复 ${k} ${n}`);
  seenSid.add(idu);
});
// 「数据里有 N 条、索引里一条都没派生出来」是 M1 那批最容易犯的错：数据落地了、门禁读了它，
// 页面与搜索忘了接。这里按「名称 + 跳转参数」去重后逐类对数，差一条就失败。
[['spl', spellList, (r) => 'c=' + r.classId],
 ['ach', achList.filter((r) => !r.devOnly), (r) => 'g=' + (r.gid || 'other')],
 ['pfam', (petsOut && petsOut.families) || [], () => ''],
 ['psk', (petsOut && petsOut.skills) || [], () => '']].forEach(([k, src, extraOf]) => {
  if (!src.length) return;
  const exp = new Set(src.map((r) => k + '|' + r.name + '|' + extraOf(r))).size;
  const got = SIDX.filter((it) => it[0] === k).length;
  if (exp !== got) {
    errs.push(`search：${k} 数据侧去重后应有 ${exp} 条，索引里只有 ${got} 条（页面或索引没接上）`);
  }
});
Object.keys(SK).forEach((k) => {
  if (PAGES.size && !PAGES.has(SK[k][1])) {
    errs.push(`search：${k} 指向的页面 ${SK[k][1]} 不在新站路由表里`);
  }
  if (!SIDX.some((it) => it[0] === k)) warns.push(`search：类型 ${k} 一条都没有，页面或数据可能没接上`);
});
const sidPath = path.join(ROOT, 'search.json');
fs.writeFileSync(sidPath, JSON.stringify({
  meta: {
    generatedAt: new Date().toISOString().slice(0, 10),
    method: 'tools/build-data.js 从已校验的数据派生，别手抄也别另建',
    fields: ['类型', '名称', '归属副标题', '跳转附加参数', '分级'],
    kinds: SK,
    note: '首页全站搜索用。只收名称与归属，不含任何描述句子；缺数据的地方显示"待实测"。'
  },
  items: SIDX
}));
scale.search = SIDX.length;
console.log('全站搜索索引 ' + SIDX.length + ' 条 / ' + Object.keys(SK).length + ' 类 → app/data/search.json（' +
  Math.round(fs.statSync(sidPath).size / 1024) + ' KB）');

// ---------- 首页只读天赋树预览的轻量数据 ----------
// 首页不该为了预览把九份 43 KB 的天赋文件全拉下来，所以这里只留画一棵树要的六个字段。
// 它是派生件，不许手改；节点总数必须与 talentNodes 对得上，对不上就是哪里漏了。
const pvClasses = {};
let pvNodes = 0;
fs.readdirSync(path.join(ROOT, 'talents')).forEach((f) => {
  if (f.charAt(0) === '_' || !f.endsWith('.json')) return;
  const t = JSON.parse(fs.readFileSync(path.join(ROOT, 'talents', f), 'utf8'));
  const cid = t.classId || f.slice(0, -5);
  pvClasses[cid] = {
    cn: t.classNameCn || cid,
    trees: (t.trees || []).map((tr) => ({
      n: tr.nameCn || '',
      nodes: (tr.nodes || []).map((nd) => {
        pvNodes++;
        return [nd.tier, nd.column, nd.nameCn || nd.nameEn || '', nd.iconKey || '',
          nd.maxRanks === undefined ? null : nd.maxRanks, nd.changeState || ''];
      })
    }))
  };
});
const pvPath = path.join(ROOT, 'talent-preview.json');
fs.writeFileSync(pvPath, JSON.stringify({
  meta: {
    generatedAt: new Date().toISOString().slice(0, 10),
    method: 'tools/build-data.js 从 app/data/talents/*.json 派生，别手抄也别手改',
    fields: ['行', '列', '名称', '图标键', '上限层数', '与经典旧世相比的改动状态'],
    note: '首页那棵只读预览树用的轻量数据；加点与前置判定仍在天赋计算器里，那里读完整文件。'
  },
  classes: pvClasses
}));
scale.talentPreview = pvNodes;
if (pvNodes !== talentNodes) {
  errs.push('talent-preview：收了 ' + pvNodes + ' 个节点，但天赋树里一共 ' + talentNodes + ' 个，首页预览会少画格子');
}
const pvClassN = (cl.classes || []).length;
if (Object.keys(pvClasses).length !== pvClassN) {
  errs.push('talent-preview：只有 ' + Object.keys(pvClasses).length + ' 个职业，classes.json 里有 ' + pvClassN + ' 个');
}
Object.keys(pvClasses).forEach((cid) => {
  const ts = pvClasses[cid].trees;
  if (ts.length !== 3) errs.push('talent-preview ' + cid + '：' + ts.length + ' 棵树，应为 3 系');
  ts.forEach((tr) => { if (!tr.n) errs.push('talent-preview ' + cid + '：有一棵树没有系名'); });
});
console.log('天赋预览数据 ' + pvNodes + ' 个节点 / ' + Object.keys(pvClasses).length +
  ' 个职业 → app/data/talent-preview.json（' + Math.round(fs.statSync(pvPath).size / 1024) + ' KB）');

// 上线日期只许有 meta.json 一处真相：前端那个 LAUNCH_AT 对不上就会两处打脸
const metaJson = read('meta.json');
const fmtPath = path.resolve(__dirname, '..', 'app', 'src', 'lib', 'fmt.js');
if (!fs.existsSync(fmtPath)) {
  errs.push('找不到 app/src/lib/fmt.js：新站倒计时没处取上线日期');
} else {
  const mFmt = /LAUNCH_AT = Date\.parse\('([^']+)'\)/.exec(fs.readFileSync(fmtPath, 'utf8'));
  if (!mFmt) errs.push('app/src/lib/fmt.js：找不到 LAUNCH_AT，新站倒计时没处取日期');
  else if (mFmt[1].slice(0, 10) !== metaJson.launch) {
    errs.push(`上线日期不一致：meta.json 写 ${metaJson.launch}，新站 fmt.js 是 ${mFmt[1].slice(0, 10)}`);
  }
}

// 「本站更新」是人工写的玩家向说明（网页只读这一份，git 那份在 docs/CHANGELOG-DEV.md）。
// 每条必须能回查：写清日期、标题、板块标签与对应提交号，提交号在仓库里找不到就是编的。
const relPath = path.join(ROOT, 'releases.json');
if (fs.existsSync(relPath)) {
  const rel = read('releases.json');
  const items = rel.items || [];
  if (!items.length) errs.push('releases：一条更新说明都没有，动态页那块会空着');
  let known = null;
  let fullShas = null;
  try {
    const cp = require('child_process');
    // 短号长度是 git 按本地仓库对象数临时定的（同一个仓库重新克隆就可能从 7 位变 8 位），
    // 所以这里不按 %h 比字符串——那样换台机器就满屏"提交找不到"。改成拿完整号做前缀匹配：
    // 台账里写 7 位还是 8 位都能回查，前提是它真在这条历史里。
    fullShas = cp.execSync('git log --pretty=format:%H', {
      cwd: path.join(ROOT, '..', '..'), encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']
    }).trim().split('\n');
    known = new Set(fullShas);
  } catch (e) {
    warns.push('releases：拿不到 git 历史，这一轮没核对提交号是否真存在');
  }
  items.forEach((x, i) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(x.date || '')) errs.push(`releases #${i}：日期不是 YYYY-MM-DD`);
    if (!x.title || x.title.length > 130) errs.push(`releases #${i}：标题缺失或超过 130 字`);
    if (!(x.tags || []).length) errs.push(`releases #${i}：没有板块标签`);
    if (!x.commit) errs.push(`releases #${i}：没写对应提交，等于一句没法回查的话`);
    else if (!/^[0-9a-f]{7,40}$/.test(x.commit)) errs.push(`releases #${i}：提交号「${x.commit}」不成个号（要 7 位以上十六进制）`);
    else if (known && !known.has(x.commit) && !fullShas.some((s) => s.indexOf(x.commit) === 0))
      errs.push(`releases #${i}：提交 ${x.commit} 在仓库里找不到`);
  });
  scale.releases = items.length;
  /* 导航角标不手写：拿「本站更新」里最新一天的标签当"本版新增"，往前再数三天当"近期更新"。
     口径相对最新一条算，不掺"今天"，所以同一份数据重跑出来的 scale.json 是一样的。 */
  const relDays = [...new Set(items.map((x) => x.date))].sort().reverse();
  const newest = relDays[0];
  const recent3 = relDays.slice(1, 4);
  scale.navNew = [...new Set(items.filter((x) => x.date === newest).flatMap((x) => x.tags || []))];
  // 只做「本版新增」一种角标：试算过，"近期更新"会同时命中 16 个导航项里的 8 个，
  // 满排都是标记就等于没有标记。要加回来得先想清楚上限怎么定。
  if (recent3.length > 3) warns.push('releases：近三天有更新的板块标签 ' +
    [...new Set(items.filter((x) => recent3.includes(x.date)).flatMap((x) => x.tags || []))].length +
    ' 个，暂未做成角标');
  console.log('本站更新 ' + items.length + ' 条（每条带提交号，可回查）');
} else {
  warns.push('releases.json 缺失：动态页的「本站更新」会是空的');
}

// ---------- 面向维护者的词不许进玩家看的正文与数据 ----------
// 词表在 tools/copy-banned.json，site-check.py 拿同一份扫渲染后的页面文字（两处一把尺子）。
const BAN = JSON.parse(fs.readFileSync(path.join(__dirname, 'copy-banned.json'), 'utf8'));
// 大小写敏感：不然 DOM 会命中 martyrdom、NaN 会命中 penance 这类标识符（栽过一次）
const BRES = BAN.patterns.map((x) => ({ re: new RegExp(x.re), why: x.why }));
const banClean = (v) => BAN.strip.reduce((a, t) => a.split(t).join(''), v);
const banHits = new Map();
function banScan(key, val, where) {
  if (BAN.skipKeys.indexOf(key) >= 0) return;
  if (typeof val === 'string') {
    const t = banClean(val);
    BRES.forEach((b) => {
      if (!b.re.test(t)) return;
      // 同一句话在 964 条记录里重复出现，只报一条，否则错误列表全是同一种错
      if (!banHits.has(val)) banHits.set(val, where + ' 命中 ' + b.re.source + ' —— ' + b.why);
    });
    return;
  }
  if (Array.isArray(val)) { val.forEach((x, i) => banScan(key, x, where + '#' + i)); return; }
  if (val && typeof val === 'object') {
    // meta 大多是工具元数据，但里面有几个键会直接渲染到页面上，只放行清单里那几个
    const keys = key === 'meta' ? (BAN.metaKeys || []) : Object.keys(val);
    keys.forEach((k) => banScan(k, val[k], where + '.' + k));
  }
}
fs.readdirSync(ROOT).forEach((f) => {
  if (!f.endsWith('.json')) return;
  banScan(f, read(f), f);
});
(BAN.dirs || []).forEach((d) => {
  const dir = path.join(ROOT, d);
  if (!fs.existsSync(dir)) return;
  fs.readdirSync(dir).forEach((f) => {
    if (!f.endsWith('.json') || f.charAt(0) === '_') return;
    banScan(d + '/' + f, JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')), d + '/' + f);
  });
});
Array.from(banHits.entries()).slice(0, 40).forEach(([v, w]) =>
  errs.push('禁词 ' + w + '：「' + v.slice(0, 70) + '」'));
console.log(banHits.size ? '禁词体检：' + banHits.size + ' 种说法命中（词表 tools/copy-banned.json）'
  : '禁词体检：数据文件干净');

// 规模快照：首页与溯源页显示的数字一律从这里来，避免页面里手抄一份和真实数据漂移
const dalls = [].concat(dg.newDungeons || [], dg.classicDungeons || [], dg.raids || []);
const noEn = dalls.filter((x) => !x.nameEn).map((x) => x.id);
if (noEn.length) warns.push(`副本条目还缺英文原名 ${noEn.length} 座：${noEn.join('、')}（客户端排队表里也对不上）`);
Object.assign(scale, {
  glossary: gl.items.length,
  classes: (JSON.parse(fs.readFileSync(path.join(ROOT, 'classes.json'), 'utf8')).classes || []).length,
  talentNodes: talentNodes,
  talentTreeConflict: talentTreeConflict,
  talentVerified: talentVerified,
  dungeons: dalls.length,
  dungeonsNew: (dg.newDungeons || []).length,
  bosses: dalls.reduce((a, x) => a + (x.bosses || []).length, 0),
  drops: dalls.reduce((a, x) => a + (x.drops || []).length, 0),
  // 副本线补齐程度：这三个数决定页面上还有几处"待补"，改数据后一定要重算，别手抄
  dungeonNameEn: dalls.filter((x) => x.nameEn).length,
  dungeonParty: dalls.filter((x) => x.partySize).length,
  dungeonRangeTwoSay: dalls.filter((x) => x.levelRangeClient).length,
  queueRows: (qu.items || []).length,
  queueUnlisted: qUnlisted,
  raids: raidStats,
  races: (rc.races || []).length,
  traits: rcTraitN,
  timeline: (JSON.parse(fs.readFileSync(path.join(ROOT, 'timeline.json'), 'utf8')).items || []).length,
  abilities: (JSON.parse(fs.readFileSync(path.join(ROOT, 'abilities.json'), 'utf8')).items || []).length,
  coverage: cov, coverageTotal: total,
  pubCoverage: pub, pubTotal: pubLevels.length
});
const scalePath = path.join(ROOT, 'scale.json');
/* 各板块的数据分别核到哪个版本（2026-10-25）。
   以前页脚挂一句全站"客户端 1.60.1.70338、核对于 2026-10-11"，而实际是传承 70532（10-23 核）、
   改动清单 70425、副本排队表 70532、世界 70338、物品名录抓取日 10-22——一句话写死就是发给玩家的假数，
   而且每核一个板块都得记得回来改它（传承那轮就漏了）。这里一律现读：谁自带版本字段就报谁。
   板块中文名只此一张表，**漏登记直接构建失败**（同 app-assets 那份 EXCLUDE 的教训：
   写死名单的毛病是每加一个板块都要记得回来补，忘了就静默少一行）。 */
const SECTION_CN = {
  'legacy.json': '传承',
  'changes.json': '客户端改动',
  'queue.json': '副本排队表',
  'world.json': '世界（区域与稀有）',
  'items.json': '物品名录',
  'art.json': '素材台账（客户端原画）',
  'bis.json': '配装名单',
  'pets.json': '猎人宠物'
};
// 触发条件只看"版本类"键：generatedAt 几乎每份数据都有（它是重算那天），
// 拿它当触发会把 24 份文件全拉进这张表，表就失去意义了。它只作日期的兜底。
// scrapedAt 是配装线记的"对着来源重抓那天"，与 fetched 同层，2026-10-26 补进来。
const VER_KEYS = ['clientBuild', 'foreverBuild', 'build', 'fetchedAt', 'fetched', 'checkedAt', 'scrapedAt'];
const dataVersions = [];
fs.readdirSync(ROOT).filter((f) => f.endsWith('.json')).forEach((f) => {
  let meta = null;
  try { meta = (JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8')) || {}).meta; } catch (e) { return; }
  if (!meta || typeof meta !== 'object') return;
  const hit = VER_KEYS.filter((k) => typeof meta[k] === 'string' && meta[k]);
  if (!hit.length) return;
  if (!SECTION_CN[f]) {
    errs.push(`数据版本表：${f} 自带版本字段（${hit.join('/')}）却没登记板块中文名，页脚与溯源页报不出人话`);
    return;
  }
  // 优先取"客户端版本号"那三个；legacy.json 的 build 是对方发布号（r-179…），不给玩家看
  const build = ['clientBuild', 'foreverBuild', 'build'].map((k) => meta[k]).filter((v) => typeof v === 'string' && !/^r-\d+$/.test(v))[0] || null;
  // 日期取"这一份成品最后一次对着来源重算"的那天：抓取日优先，没有就用生成日
  const at = ['fetchedAt', 'fetched', 'checkedAt', 'scrapedAt', 'generatedAt']
    .map((k) => (typeof meta[k] === 'string' ? meta[k].slice(0, 10) : null)).filter(Boolean)[0] || null;
  dataVersions.push({
    file: f, section: SECTION_CN[f], build: build, checkedAt: at,
    classic: typeof meta.classicBuild === 'string' ? meta.classicBuild : null
  });
});
Object.keys(SECTION_CN).forEach((f) => {
  if (!dataVersions.some((x) => x.file === f)) {
    warns.push(`数据版本表：${SECTION_CN[f]}（${f}）这一轮没读到版本字段，溯源页那一行会缺`);
  }
});
if (!dataVersions.length) errs.push('数据版本表一条都没派生出来：页脚与首页那颗徽标会没有数可显示');
// ---- 数据过期闸（站主 2026-10-26 定的天数：超 7 天提示、超 14 天拦红）----
// 这条**故意**随"今天"变：同一份数据放着不动才会红，重抓当天就绿——要的就是这个效果。
// 之前是四个洞：没人比较核对日与今天、页面只显第二份（插件）的日期、
// 门禁把日期抄成字面量、配装根本没进这张表（见 docs/EVAL-bis更新与3D模型-2026-10-26.md）。
const STALE_SOFT_DAYS = 7;
const STALE_HARD_DAYS = 14;
const now0 = Date.now();
dataVersions.forEach((x) => {
  if (!x.checkedAt) return;
  const days = Math.floor((now0 - new Date(x.checkedAt + 'T00:00:00').getTime()) / 86400000);
  x.daysSince = days;
  x.stale = days > STALE_HARD_DAYS ? 'red' : (days > STALE_SOFT_DAYS ? 'warn' : null);
  if (x.stale === 'red') {
    errs.push(`数据过期：${x.section} 这份是 ${x.checkedAt} 对着来源核的，距今 ${days} 天（硬线 ${STALE_HARD_DAYS} 天）。`
      + `重抓那一块（tools/refresh.sh 里有对应分支），或按流程改这条天数——别把日期手抄新一点糊过去。`);
  } else if (x.stale === 'warn') {
    warns.push(`数据快过期：${x.section}（${x.checkedAt} 核对，距今 ${days} 天；到 ${STALE_HARD_DAYS} 天会拦红）`);
  }
});
// 有客户端版本号的排前面、新的在上；只留了日期的（物品名录、素材台账）排在后面
dataVersions.sort((a, b) => (b.build ? 1 : 0) - (a.build ? 1 : 0)
  || String(b.build || '').localeCompare(String(a.build || ''))
  || String(a.section).localeCompare(String(b.section)));
scale.dataVersions = dataVersions;
// 界面（溯源页那张表）按这两个数决定标不标"已过期"，不在组件里另抄一份天数
scale.stalePolicy = { soft: STALE_SOFT_DAYS, hard: STALE_HARD_DAYS };
// 首页那颗徽标报"最新核到哪个客户端"，这个"最新"也现算，不在组件里挑
scale.newestBuild = dataVersions.map((x) => x.build).filter(Boolean).sort().slice(-1)[0] || null;
scale.newestSection = (dataVersions.filter((x) => x.build === scale.newestBuild)[0] || {}).section || null;
fs.writeFileSync(scalePath, JSON.stringify({
  meta: {
    generatedAt: new Date().toISOString().slice(0, 10),
    method: 'tools/build-data.js 校验时顺手算出来，别在页面里手抄这些数',
    note: '首页与溯源页的规模数字唯一来源。改数据后重跑 build-data.js 才会变。'
  },
  scale: scale
}, null, 1) + '\n');
console.log('规模快照 → app/data/scale.json（' + Object.keys(scale).length + ' 项）');
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
