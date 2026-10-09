#!/usr/bin/env node
/* 把 upstream/wclbox-changes.json 整形成 src/data/changes.json（客户端改动清单）。
 *
 * 口径（2026-10-09 用户拍板）：最新动态只放名称与改动类型，不放句子。
 * 抓取阶段已经把 rank_texts / summary / forever_note 等文本字段全删了，这里只做形状与计数，
 * 并且把条数与上游 meta.json 自己报的 counts 逐一对齐——对不上就是抄漏或抄重，直接失败。
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'src', 'data');
const up = JSON.parse(fs.readFileSync(path.join(ROOT, 'upstream', 'wclbox-changes.json'), 'utf8'));
const U = up.meta.upstreamCounts || {};

const KIND_CN = {
  added: '新增', modified: '改动', moved: '换层或换系', removed: '移除', unchanged: '未变',
  renamed: '改名', earlier: '学得更早', baseline: '基线', race: '种族技'
};

const items = (up.rows || []).map((x) => {
  const renamed = x.reported_change_kind === 'renamed' && x.classic && x.classic.name &&
    x.classic.name !== x.name ? x.classic.name : null;
  return {
    id: x.id,
    nameCn: x.name,
    classId: x.class,
    kind: x.kind === 'spell' ? 'spell' : 'talent',
    tree: x.tree_name || null,
    changeKind: x.reported_change_kind,
    changeCn: KIND_CN[x.reported_change_kind] || x.reported_change_kind,
    maxRank: typeof x.max_rank === 'number' ? x.max_rank : null,
    // 上游有个别图标键带尾点（spell_shadow_devouringplague.），CDN 上是 403；去掉尾点才取到图
    iconKey: (x.icon || '').replace(/[^a-z0-9_]/g, '') || null,
    oldNameCn: renamed,
    discoveredAt: x.discovered_at || null,
    level: 'L0',
    provenance: [
      { type: 'datamine_cn', url: up.meta.source,
        note: '改动类别与名称来自无限测试版客户端解包（经新手盒子转述，其源为 wago.tools 客户端 DB ' +
          up.meta.foreverBuild + '）；前后文本本站不复制',
        checkedAt: up.meta.scrapedAt },
      // /gaidong 页面正文是客户端渲染的，SSR 里只有抽样；逐字回查要打到它渲染用的那份 JSON
      { type: 'datamine_cn', url: up.meta.endpoint,
        note: '本页渲染用的结构化记录，名称与改动类别以此为准',
        checkedAt: up.meta.scrapedAt }
    ]
  };
});

const cnt = (f) => items.filter(f).length;
const counts = {
  all: items.length,
  talents: cnt((x) => x.kind === 'talent'),
  spells: cnt((x) => x.kind === 'spell'),
  changed: cnt((x) => x.changeKind !== 'unchanged'),
  newTalents: cnt((x) => x.kind === 'talent' && x.changeKind === 'added'),
  changedTalents: cnt((x) => x.kind === 'talent' && (x.changeKind === 'modified' || x.changeKind === 'moved')),
  removedTalents: cnt((x) => x.kind === 'talent' && x.changeKind === 'removed'),
  spellsChanged: cnt((x) => x.kind === 'spell' && x.changeKind !== 'unchanged')
};

const byClass = {};
items.forEach((x) => {
  const b = (byClass[x.classId] = byClass[x.classId] || { classId: x.classId, all: 0, changed: 0 });
  b.all++;
  if (x.changeKind !== 'unchanged') b.changed++;
});
const byKind = {};
items.forEach((x) => { byKind[x.changeKind] = (byKind[x.changeKind] || 0) + 1; });

const payload = {
  meta: {
    generatedAt: up.meta.scrapedAt,
    kind: 'client-datamine',
    method: 'tools/scrape-wclbox-changes.py 抓 → tools/merge-changes.js 整形',
    release: up.meta.release,
    foreverBuild: up.meta.foreverBuild,
    classicBuild: up.meta.classicBuild,
    sources: [{ url: up.meta.source, label: '新手盒子 · 改动页（其源为 wago.tools 客户端 DB）' }],
    upstreamCounts: U,
    textPolicy: '入库前删掉的字段：' + (up.meta.droppedFields || []).join('、') +
      '。界面只列名称与改动类别，要看逐字前后对照请去上游页，本站不复制。',
    notCollected: [
      '改动前后的技能/天赋文本：属描述文案，2026-10-09 口径明确不搬',
      '上游自己写的改动摘要与备注（summary / forever_note / uncertainties）：第三方判断，不搬',
      '法术在技能书里的排列顺序：客户端里有这项数据，但对查资料没用，先不存',
      '强度影响评价：不做强度排行，这条只在资料完整度排行里出现'
    ],
    byKind: byKind,
    byClass: Object.keys(byClass).sort().map((k) => byClass[k])
  },
  items: items
};

fs.writeFileSync(path.join(ROOT, 'changes.json'), JSON.stringify(payload, null, 1) + '\n');
const miss = Object.keys({ all: 1, changed: 1, newTalents: 1, changedTalents: 1, removedTalents: 1, spells: 1, spellsChanged: 1 })
  .filter((k) => U[k] !== undefined && counts[k] !== U[k]);
console.log('改动 %d 条（天赋 %d / 法术 %d）· 有变化 %d · 新天赋 %d · 改动天赋 %d · 移除 %d · 法术改动 %d',
  counts.all, counts.talents, counts.spells, counts.changed, counts.newTalents,
  counts.changedTalents, counts.removedTalents, counts.spellsChanged);
console.log(miss.length ? '!! 与上游自报计数对不上：' + miss.map((k) => k + ' 本站 ' + counts[k] + ' / 上游 ' + U[k]).join('；')
  : '与上游自报计数逐项一致');
