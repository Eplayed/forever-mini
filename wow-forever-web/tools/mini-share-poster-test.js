#!/usr/bin/env node
/**
 * 小程序「团长开荒一图流 / 刷本缺口卡 / 配装分享长图」定向单测（Node 直跑）
 * 验证：真数据聚合、副本图与装备图标挂载、分页折行、空/超长输入、零禁词/商标词、WXSS 零裸色、JS 语法无 ?. / ?? / const self = this
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const REPO = path.resolve(__dirname, '..', '..');
const MINI = path.join(REPO, 'for-mini');

const model = require(path.join(MINI, 'services', 'share-poster-model.js'));
const analytics = require(path.join(MINI, 'services', 'analytics.js'));
const dungeonSnap = require(path.join(MINI, 'data', 'forever-dungeon-snapshot.js'));

let passed = 0;
function ok(name, cond) {
  assert.strictEqual(Boolean(cond), true, 'FAIL: ' + name);
  passed += 1;
}

/* 1. 使用真实小程序分发层 bis/index.json（60 级 27 套团前 BiS + bis60Src）测试「团长开荒一图流」 */
const ossRoot = path.join(MINI, 'oss-build', 'beta');
const manifestPtr = JSON.parse(fs.readFileSync(path.join(ossRoot, 'manifest.json'), 'utf8'));
const batchId = manifestPtr.buildId || manifestPtr.batch;
const bisIndexPath = path.join(ossRoot, 'builds', batchId, 'bis', 'index.json');
const bisItemsPath = path.join(ossRoot, 'builds', batchId, 'bis', 'items.json');
const bisIndex = JSON.parse(fs.readFileSync(bisIndexPath, 'utf8'));
const bisItems = JSON.parse(fs.readFileSync(bisItemsPath, 'utf8'));
const ASSET_BASE = 'https://poe2-all-class.oss-cn-hangzhou.aliyuncs.com/wow/beta/v1/assets/';
const itemsMap = {};
for (const row of bisItems.items || []) {
  itemsMap[String(row[0])] = {
    id: row[0],
    name: row[1],
    q: row[2],
    ilvl: row[3],
    iconUrl: row[4] ? (ASSET_BASE + 'icons/' + row[4] + '.jpg') : ''
  };
}
const dungeonArtMap = model.buildDungeonArtMap(dungeonSnap.items || [], (art) => ASSET_BASE + art);

const bis60Sets = bisIndex.bis60Sets || [];
const bis60Src = bisIndex.bis60Src || {};
const raidSpec = model.buildRaidPrepOneSheet(bis60Sets, bis60Src, itemsMap, dungeonArtMap);

ok('团长开荒一图流命中真实 60 级 27 套数据', bis60Sets.length >= 27 && raidSpec.entries.length >= 8);
ok('团长开荒一图流去除了「副本：」前缀且无同名分裂', raidSpec.entries.every((e) => !e.title.includes('副本：')));
const uniqueRaidNames = new Set(raidSpec.entries.map((e) => e.title.split('  (')[0]));
ok('团长开荒一图流副本名称去重唯一', uniqueRaidNames.size === raidSpec.entries.length);
ok('团长开荒一图流全部副本挂载真实副本封面图', raidSpec.entries.every((e) => e.iconKind === 'dungeon' && e.iconUrl.includes('/art/dungeons/') && e.iconUrl.endsWith('.webp')));
ok('团长开荒一图流每行挂载核心装备真实图标', raidSpec.entries.every((e) => Array.isArray(e.miniIcons) && e.miniIcons.length > 0 && e.miniIcons.some((m) => m.url.includes('/icons/'))));
ok('团长开荒一图流标题与搜一搜底栏到位', raidSpec.badge === '团长开荒一图流' && raidSpec.footerBrand.includes('跑本无限助手'));
ok('团长开荒一图流带 L1 第三方说明句', raidSpec.note.includes('第三方资料'));

const raidPages = model.paginatePoster(raidSpec, 6);
ok('团长开荒一图流按 6 条/页分 2 页且保留图标字段', raidPages.length === 2 && raidPages[0].rows.length === 6 && raidPages[0].rows[0].iconUrl.endsWith('.webp') && raidPages[0].rows[0].miniIcons.length > 0);

/* 2. 测试单套配装分享卡与空输入兜底 */
const sampleSet = bis60Sets[0];
const setRows = (sampleSet.doll || []).map((d) => {
  const m = itemsMap[String(d[2])] || {};
  return { slotLabel: d[0], item: d[2], name: m.name || '', q: m.q || 3, ilvl: m.ilvl || '', iconUrl: m.iconUrl || '', src: bis60Src[String(d[2])] || '' };
});
const bisSpec = model.buildBisSetPoster({
  stageKey: '60',
  badge: '60级团前配装卡',
  title: sampleSet.clsCn + ' · ' + sampleSet.mode,
  rows: setRows
});
const bisPages = model.paginatePoster(bisSpec, 8);
ok('单套配装卡分页完整且覆盖全部部位', bisPages.reduce((s, p) => s + p.rows.length, 0) === setRows.length);
ok('单套配装卡保留真实装备图标 URL', bisSpec.entries.filter((e) => e.iconKind === 'item' && e.iconUrl.includes('/icons/')).length >= 10);

const emptyBis = model.buildBisSetPoster({ stageKey: '30', rows: [] });
ok('空配装输入有安全兜底提示', emptyBis.entries.length === 1 && emptyBis.entries[0].tag === '提示');

/* 3. 测试「我的冒险清单 · 今晚组队喊人卡」副本缩略条、装备图标与超长文本折行 */
const advSpec = model.buildAdventurePoster(
  [{ id: 'blackrock-depths', name: '黑石深渊' }, { id: 'stratholme-main-gate', name: '斯坦索姆正门' }],
  [{
    key: 'blackrock-depths',
    title: '黑石深渊',
    rows: [
      { id: '11815', name: '正义之手（超级长名字测试自动折行不断裂验证文本截断安全）', quality: 3, iconUrl: ASSET_BASE + 'icons/inv_jewelry_talisman_01.jpg', sources: [{ id: 'blackrock-depths', label: '黑石深渊 · 弗莱拉斯大使' }] },
      { id: '11726', name: '野蛮角斗士链甲', quality: 4, iconUrl: ASSET_BASE + 'icons/inv_chest_chain_15.jpg', sources: [{ id: 'blackrock-depths', label: '黑石深渊 · 竞技场' }] }
    ]
  }],
  dungeonArtMap
);
ok('冒险清单喊人卡包含跑本顺序与 2 件目标装备', advSpec.entries.length === 3 && advSpec.entries[0].tag === '跑本顺序');
ok('跑本顺序挂载全部计划副本封面缩略图', advSpec.entries[0].iconKind === 'route' && advSpec.entries[0].routeThumbs.length === 2 && advSpec.entries[0].routeThumbs.every((t) => t.artUrl.endsWith('.webp')));
ok('冒险清单装备行挂载装备图标与副本小徽标', advSpec.entries[1].iconKind === 'item' && advSpec.entries[1].iconUrl.includes('/icons/') && advSpec.entries[1].badgeIconUrl.endsWith('blackrock-depths.webp'));
const advPages = model.paginatePoster(advSpec, 8);
ok('超长装备名自动折行且不超 2 行上限', advPages[0].rows[1].titleLines.length === 2);

/* 4. 商标词红线扫描（海报输出文本禁止魔兽/暴雪/艾泽拉斯/WoW 主体词） */
const allPosterText = JSON.stringify([raidSpec, bisSpec, advSpec]);
const forbiddenBrand = ['魔兽', 'WoW', '艾泽拉斯'];
for (const word of forbiddenBrand) {
  ok('分享卡文案不含商标词：' + word, !allPosterText.includes(word));
}

/* 5. analytics.js 在无 wx 环境与模拟 wx 环境下均安全 */
ok('无 wx 环境 analytics.track 安全返回 false', analytics.track('poster_generate', { kind: 'raid_prep' }) === false);
let reported = null;
global.wx = { reportEvent: (name, obj) => { reported = { name, obj }; } };
ok('有 wx 环境 analytics.track 过滤非标量字段并上报', analytics.track('poster_save', { kind: 'raid_prep', ok: true, bad: { x: 1 } }) === true && reported.name === 'poster_save' && !('bad' in reported.obj));
delete global.wx;

/* 6. 静态守卫：新增组件 WXSS 零裸 #hex / rgba(，JS 零 ?. / ?? / const self = this */
const wxssFiles = [
  path.join(MINI, 'components', 'share-poster', 'index.wxss'),
  path.join(MINI, 'pages', 'adventure', 'index.wxss'),
  path.join(MINI, 'pages', 'bis', 'index.wxss')
];
for (const f of wxssFiles) {
  const txt = fs.readFileSync(f, 'utf8');
  ok(path.relative(MINI, f) + ' 零裸色 #hex / rgba(', !/#[0-9a-fA-F]{3,8}\b/.test(txt) && !/rgba\s*\(/.test(txt));
}
const jsFiles = [
  path.join(MINI, 'services', 'analytics.js'),
  path.join(MINI, 'services', 'share-poster-model.js'),
  path.join(MINI, 'services', 'adventure.js'),
  path.join(MINI, 'components', 'share-poster', 'index.js'),
  path.join(MINI, 'pages', 'adventure', 'index.js'),
  path.join(MINI, 'pages', 'bis', 'index.js'),
  path.join(MINI, 'pages', 'dungeon', 'index.js')
];
for (const f of jsFiles) {
  const txt = fs.readFileSync(f, 'utf8');
  ok(path.relative(MINI, f) + ' 无 ?. / ?? / const self = this', !/\?\./.test(txt) && !/\?\?/.test(txt) && !/const\s+self\s*=\s*this/.test(txt));
}

console.log(`MINI_SHARE_POSTER_OK (${passed}/${passed} passed, top1 dungeon: ${raidSpec.entries[0].title}, top1 art: ${raidSpec.entries[0].iconUrl.split('/').pop()})`);
