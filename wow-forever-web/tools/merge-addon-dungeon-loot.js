'use strict';

const fs = require('fs');
const path = require('path');

const dataRoot = path.resolve(__dirname, '..', 'app', 'data');
const read = (file) => JSON.parse(fs.readFileSync(path.join(dataRoot, file), 'utf8'));
const slug = (name) => String(name || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

function matchBoss(boss, row) {
  if (boss.npcId != null) return boss.npcId === row.npcId;
  if (boss.id === 'npc-' + row.npcId) return true;
  if ((boss.aliases || []).some((alias) => alias.npcId === row.npcId)) return true;
  const nameMatches = boss.nameCn === row.nameCn;
  const en = boss.npcNameEn || boss.encounterNameEn || boss.nameEn;
  return nameMatches && Boolean(row.nameEn) && (en ? en === row.nameEn : boss.id === slug(row.nameEn));
}

function mergeAddonDungeonLoot(doc) {
  const factsPath = 'upstream/df-drop-item-facts.json';
  if (!fs.existsSync(path.join(dataRoot, factsPath))) return;
  const snap = read('upstream/df-dungeon-loot.json');
  const facts = read(factsPath);
  const items = new Map(facts.items.map((item) => [
    item.id, { ...item, iconKey: (item.iconFile || '').replace(/\.jpg$/, '') }
  ]));
  for (const item of read('items.json').items) {
    if (item.name && item.status !== 'missing') items.set(item.id, item);
  }
  const roster = new Map(snap.dungeons.map((dungeon) => [dungeon.id, dungeon.bosses]));
  const iconRoot = path.resolve(dataRoot, '..', 'img', 'icons');
  const source = {
    type: 'addon', url: 'https://wx-wow.com/changelog.html', checkedAt: snap.meta.fetched,
    version: snap.meta.addonVersion, sourceFile: snap.meta.sourceFile,
    note: 'DungeonsForever 首领掉落归属，本站待实测。'
  };
  const itemSource = { type: 'datamine_cn', url: facts.meta.source, checkedAt: facts.meta.fetched };
  const unresolved = new Set();
  const missingItems = new Set();
  let covered = 0;
  for (const dungeon of [...doc.newDungeons, ...doc.classicDungeons, ...doc.raids]) {
    // 领主大厅另有逐条核对的掉落表。
    if (dungeon.id === 'hall-of-thanes') continue;
    const rows = (roster.get(dungeon.id) || []).filter((row) => Number.isInteger(row.npcId));
    if (!rows.length) continue;
    const canExtendRoster = dungeon.bosses.length > 0 && dungeon.bosses.every((boss) => Number.isInteger(boss.npcId));
    const drops = new Set(dungeon.drops.map((drop) => drop.bossId + '|' + drop.itemId));
    let touched = false;
    for (const row of rows) {
      const matches = dungeon.bosses.filter((boss) => matchBoss(boss, row));
      let boss = matches.length === 1 ? matches[0] : null;
      if (!matches.length && canExtendRoster && row.nameCn && row.nameEn &&
          !dungeon.bosses.some((entry) => entry.nameCn === row.nameCn || entry.nameEn === row.nameEn)) {
        boss = { id: 'npc-' + row.npcId, npcId: row.npcId, nameCn: row.nameCn, nameEn: row.nameEn,
          level: 'L2', note: null, portrait: null, provenance: [source] };
        dungeon.bosses.push(boss);
      }
      if (!boss) {
        unresolved.add(dungeon.id + '/' + row.npcId);
        continue;
      }
      boss.npcId ??= row.npcId;
      boss.nameEn ||= row.nameEn;
      for (const id of row.itemIds) {
        const key = boss.id + '|' + id;
        if (drops.has(key)) {
          covered += 1;
          touched = true;
          continue;
        }
        const item = items.get(id);
        if (!item?.name) {
          missingItems.add(id);
          continue;
        }
        const iconKey = item.iconKey && fs.existsSync(path.join(iconRoot, item.iconKey + '.jpg')) ? item.iconKey : null;
        dungeon.drops.push({ itemId: String(id), nameCn: item.name, iconKey, quality: item.quality ?? null,
          bossId: boss.id, bossCn: boss.nameCn, level: 'L2', from: 'df-forever' });
        drops.add(key);
        covered += 1;
        touched = true;
      }
    }
    if (!touched) continue;
    dungeon.provenance = (dungeon.provenance || []).filter((entry) =>
      !(entry.url === source.url && entry.version) && entry.url !== itemSource.url);
    dungeon.provenance.push(source, itemSource);
    dungeon.lootNote ||= '首领掉落来自无限服插件记录，本站待实测。';
  }
  doc.meta.addonLoot = { version: source.version, checkedAt: source.checkedAt, covered,
    unmatchedBosses: [...unresolved].sort(), missingItems: [...missingItems].sort((a, b) => a - b) };
  if (doc.meta.bossPortraits) {
    const bosses = [...doc.newDungeons, ...doc.classicDungeons, ...doc.raids].flatMap((dungeon) => dungeon.bosses);
    doc.meta.bossPortraits.total = bosses.length;
    doc.meta.bossPortraits.withPortrait = bosses.filter((boss) => boss.portrait).length;
  }
  console.log('插件 %s：覆盖 %d 条掉落归属，未匹配首领 %d 个，缺物品名称 %d 件。',
    source.version, covered, unresolved.size, missingItems.size);
}

if (require.main === module) {
  const output = path.join(dataRoot, 'dungeons.json');
  const doc = read('dungeons.json');
  mergeAddonDungeonLoot(doc);
  const temp = output + '.tmp';
  fs.writeFileSync(temp, JSON.stringify(doc, null, 1) + '\n');
  fs.renameSync(temp, output);
}

module.exports = mergeAddonDungeonLoot;
