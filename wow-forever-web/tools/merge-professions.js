#!/usr/bin/env node
/* 把 upstream/wclbox-professions.json 整形成 app/data/professions.json。
 * 专业这块我们没有自己的攒数据，所以这一步只做形状与口径：
 * 加来源、加"没采到的"清单、把每条配方/采集点的分级写明。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'app', 'data');
const up = JSON.parse(fs.readFileSync(path.join(ROOT, 'upstream', 'wclbox-professions.json'), 'utf8'));

const EN = { alchemy: 'Alchemy', blacksmithing: 'Blacksmithing', enchanting: 'Enchanting',
  engineering: 'Engineering', leatherworking: 'Leatherworking', tailoring: 'Tailoring',
  mining: 'Mining', herbalism: 'Herbalism', skinning: 'Skinning', cooking: 'Cooking',
  fishing: 'Fishing', 'first-aid': 'First Aid', camping: 'Camping' };

const professions = (up.professions || []).map((p) => {
  const recipes = p.recipes || [], nodes = p.nodes || [];
  return {
    id: p.id,
    nameCn: p.nameCn,
    nameEn: EN[p.id] || null,
    nameEnSource: EN[p.id] ? '英文名叫法取自那家资料站的网址用词，不是官方英文页的原词' : null,
    kind: p.kind,
    unparsed: !!p.unparsed,
    note: p.note || null,
    counts: {
      recipes: recipes.length,
      newRecipes: recipes.filter((x) => x.isNew).length,
      nodes: nodes.length
    },
    level: 'L0',
    levelNote: '配方、材料、数量与技能档位是客户端里的数据（经第三方转述）；来源方式（训练师等）同',
    recipes: recipes.map((x) => ({
      itemId: x.itemId, nameCn: x.nameCn, iconKey: x.iconKey || null, quality: x.quality || null,
      isNew: !!x.isNew, mats: x.mats || [], skill: x.skill || null, source: x.source || null,
      level: 'L0'
    })),
    /* 钓鱼那一张不是"采集点"，是**技能分段表**：源页的列是「稳定上钩 / 开始咬钩 / 区域」。
       抓取层当初按采集点的列序硬套，结果成品里 6 行的 nameCn 变成了 25/75/150 这种纯数字、
       "开始咬钩"落进了"可得"栏（2026-10-27 来源复核记的已知错，公开页上就是错的）。
       这里按列名重认一次：认得出那两个列头就整行改成 tier 形状，认不出仍走采集点老路，
       不靠"专业 id 是 fishing"这种硬编码——哪天源页改了列头，这里会退回原样而不是继续错。*/
    nodes: nodes.map((x) => {
      const c = x.columns || null;
      const isTier = !!(c && c['稳定上钩'] !== undefined && c['开始咬钩'] !== undefined);
      if (!isTier) {
        return {
          nameCn: x.nameCn, iconKey: x.iconKey || null, yields: x.yields || [],
          zone: x.zone || null, skill: x.skill || null, columns: c, level: 'L0'
        };
      }
      const reliable = Number(c['稳定上钩']);
      return {
        kind: 'tier',
        nameCn: '稳定上钩 ' + c['稳定上钩'] + ' 级',
        reliableAt: Number.isFinite(reliable) ? reliable : null,
        biteFrom: String(c['开始咬钩']),
        iconKey: null, yields: [],
        zone: x.zone || c['区域'] || null,
        skill: Number.isFinite(reliable) ? reliable : null,
        columns: c, level: 'L0'
      };
    }),
    provenance: p.provenance || []
  };
});

const payload = {
  meta: {
    generatedAt: up.meta.scrapedAt,
    kind: 'client-datamine',
    method: 'tools/scrape-wclbox-prof.py --write 抓 → tools/merge-professions.js 整形',
    sources: [{ url: up.meta.source, label: '新手盒子 · 魔兽世界无限数据库 专业页' }],
    took: up.meta.took,
    skipped: up.meta.skipped,
    notCollected: [
      '野营（camping）：那一页不是表格形式，条目这一版还没能拆出来；有页面但不编数据',
      '冲级路线与材料性价比建议：属攻略性质，本站红线不做',
      '商人青睐配方与专业专精选择建议：同上',
      '配方产物的装备属性与强度评价：不做强度排行'
    ]
  },
  professions: professions
};

fs.writeFileSync(path.join(ROOT, 'professions.json'), JSON.stringify(payload, null, 1) + '\n');
const r = professions.reduce((s, p) => s + p.counts.recipes, 0);
const n = professions.reduce((s, p) => s + p.counts.nodes, 0);
const nw = professions.reduce((s, p) => s + p.counts.newRecipes, 0);
console.log('已写 professions.json：%d 个专业 · 配方 %d（其中无限新增 %d）· 采集点 %d',
  professions.length, r, nw, n);
professions.filter((p) => p.unparsed).forEach((p) => console.log('  没解析出来的：' + p.id + ' ' + p.nameCn));
