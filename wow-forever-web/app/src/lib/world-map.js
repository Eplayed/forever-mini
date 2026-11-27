/* world-map.js —— 无限地图（仿 OpenMap 无缝画布）纯逻辑引擎
   1. 分类体系对齐 OpenMap Townsfolk.lua（LOD 缩放门槛）+ 本站稀有/书籍/营地/副本/传承书籍；
   2. 把 world-atlas.json、world.json、map-npcs.json、legacy-books.json 归一为统一世界坐标点集；
   3. 视口裁剪 + 分层 LOD 过滤，确保上千个点位在 60fps 下流畅缩放拖拽。 */

const DONE_KEY = 'wow_forever_v1_world_done';

export const MAP_GROUPS = [
  { key: 'collect', label: '收集与探索' },
  { key: 'mobs', label: '怪物与首领' },
  { key: 'travel', label: '副本与交通' },
  { key: 'npc', label: '城镇 NPC' }
];

export const MAP_CATEGORIES = [
  // 收集与探索（默认全不选，由玩家按需打勾筛选）
  { key: 'legacy_book', group: 'collect', label: '传承书籍', glyph: '传', icon: 'img/icons/inv_misc_book_11.jpg', minZoom: 0.45, checkable: true, defaultOn: false },
  { key: 'book', group: 'collect', label: '图书馆书籍', glyph: '书', icon: 'img/icons/inv_misc_book_07.jpg', minZoom: 0.9, checkable: true, defaultOn: false },
  { key: 'camp', group: 'collect', label: '舒适睡袋营地', glyph: '营', icon: 'img/icons/inv_camelot_camping_welcomingcampfire.jpg', minZoom: 0.5, checkable: false, defaultOn: false },
  // 怪物与首领
  { key: 'rare', group: 'mobs', label: '稀有精英（含掉落）', glyph: '★', icon: 'img/icons/inv_misc_head_dragon_01.jpg', minZoom: 0.9, checkable: true, defaultOn: false },
  // 副本与交通（严格区分联盟/部落/中立飞行点 + 船只/飞艇/空艇航线点）
  { key: 'dungeon', group: 'travel', label: '副本与团本入口', glyph: '本', icon: 'img/icons/spell_arcane_portalstormwind.jpg', minZoom: 0.45, checkable: false, defaultOn: false },
  { key: 'transport', group: 'travel', label: '航线点（船/飞艇/空艇）', glyph: '港', icon: 'img/icons/inv_misc_spyglass_02.jpg', minZoom: 0.45, checkable: false, defaultOn: false },
  { key: 'flight_a', group: 'travel', label: '联盟飞行点', glyph: '盟', icon: 'img/icons/ability_hunter_eagleeye.jpg', minZoom: 0.85, checkable: false, defaultOn: false },
  { key: 'flight_h', group: 'travel', label: '部落飞行点', glyph: '部', icon: 'img/icons/ability_hunter_pet_bat.jpg', minZoom: 0.85, checkable: false, defaultOn: false },
  { key: 'flight_n', group: 'travel', label: '中立飞行点', glyph: '中', icon: 'img/icons/ability_hunter_aspectoftheironhawk.jpg', minZoom: 0.85, checkable: false, defaultOn: false },
  // 城镇 NPC（对齐 OpenMap Townsfolk.lua 分级门槛 + 真实游戏内图标：炉石/铁砧/金币/拍卖槌/信封等）
  { key: 'innkeeper', group: 'npc', label: '旅店老板', glyph: '宿', icon: 'img/icons/inv_misc_rune_01.jpg', minZoom: 1.35, checkable: false, defaultOn: false },
  { key: 'repair', group: 'npc', label: '修理', glyph: '修', icon: 'img/icons/inv_blacksmith_anvil.jpg', minZoom: 1.55, checkable: false, defaultOn: false },
  { key: 'vendor', group: 'npc', label: '商人', glyph: '商', icon: 'img/icons/inv_misc_bag_08.jpg', minZoom: 1.85, checkable: false, defaultOn: false },
  { key: 'banker', group: 'npc', label: '银行职员', glyph: '银', icon: 'img/icons/inv_misc_coin_02.jpg', minZoom: 1.35, checkable: false, defaultOn: false },
  { key: 'auctioneer', group: 'npc', label: '拍卖师', glyph: '拍', icon: 'img/icons/inv_hammer_20.jpg', minZoom: 1.35, checkable: false, defaultOn: false },
  { key: 'mailbox', group: 'npc', label: '邮箱', glyph: '邮', icon: 'img/icons/inv_letter_15.jpg', minZoom: 1.55, checkable: false, defaultOn: false },
  { key: 'classTrainer', group: 'npc', label: '职业训练师', glyph: '职', icon: 'img/icons/inv_misc_book_09.jpg', minZoom: 1.55, checkable: false, defaultOn: false },
  { key: 'profTrainer', group: 'npc', label: '专业训练师', glyph: '专', icon: 'img/icons/inv_misc_gear_01.jpg', minZoom: 1.85, checkable: false, defaultOn: false },
  { key: 'stable', group: 'npc', label: '兽栏管理员', glyph: '兽', icon: 'img/icons/ability_hunter_beasttaming.jpg', minZoom: 1.55, checkable: false, defaultOn: false },
  { key: 'spirit', group: 'npc', label: '灵魂医者', glyph: '灵', icon: 'img/icons/spell_holy_divinespirit.jpg', minZoom: 1.15, checkable: false, defaultOn: false },
  { key: 'otherNpc', group: 'npc', label: '骑术 / 公会', glyph: '杂', icon: 'img/icons/ability_mount_ridinghorse.jpg', minZoom: 1.85, checkable: false, defaultOn: false }
];

export const CAT_BY_KEY = Object.fromEntries(MAP_CATEGORIES.map((c) => [c.key, c]));

export function defaultEnabledMap() {
  const out = {};
  MAP_CATEGORIES.forEach((c) => { out[c.key] = !!c.defaultOn; });
  return out;
}

export function zoneToWorld(rect, px, py) {
  if (!rect || px == null || py == null) return null;
  const x = Number(px);
  const y = Number(py);
  if (Number.isNaN(x) || Number.isNaN(y)) return null;
  return {
    wx: Math.round((rect[0] + rect[2] * (x / 100)) * 10) / 10,
    wy: Math.round((rect[1] + rect[3] * (y / 100)) * 10) / 10
  };
}

function normFaction(raw) {
  const s = String(raw || '').trim();
  if (s === 'A' || s === 'Alliance' || s === '联盟') return 'A';
  if (s === 'H' || s === 'Horde' || s === '部落') return 'H';
  return 'N';
}

function lvLabel(range) {
  if (Array.isArray(range) && range[0] != null) {
    return range[1] && range[1] !== range[0] ? `${range[0]}–${range[1]} 级` : `${range[0]} 级`;
  }
  return '';
}

export function normalizeMapPins(atlas, world, npcsData, legacyData) {
  const zones = (atlas && atlas.zones) || [];
  const zByMid = {};
  const zByName = {};
  zones.forEach((z) => {
    zByMid[String(z.mapId)] = z;
    zByName[z.nameCn] = z;
  });

  const pins = [];

  // 1. 副本与团本入口
  ((atlas && atlas.dungeons) || []).forEach((d) => {
    const z = zByMid[String(d.mapId)];
    if (!z) return;
    const pos = zoneToWorld(z.rect, d.x, d.y);
    if (!pos) return;
    pins.push({
      id: 'dun:' + d.slug,
      cat: 'dungeon',
      name: d.nameCn,
      en: d.nameEn || '',
      zone: d.zone || z.nameCn,
      mapId: String(d.mapId),
      x: d.x,
      y: d.y,
      wx: pos.wx,
      wy: pos.wy,
      faction: 'N',
      level: lvLabel(d.levelRange) || (d.isRaid ? '60 级团本' : ''),
      tag: d.isRaid ? '团队副本' : '地下城',
      isRaid: !!d.isRaid,
      isNew: !!d.isNew,
      slug: d.slug,
      rows: d.isRaid ? [['入口类型', '团队副本入口']] : [['入口类型', '5 人地下城入口']],
      drops: [],
      search: `${d.nameCn} ${d.nameEn || ''} ${d.zone || z.nameCn} ${d.isRaid ? '团本' : '副本'}`.toLowerCase()
    });
  });

  // 2. 稀有精英（来自 world.json，含完整掉落）
  ((world && world.rares) || []).forEach((r, idx) => {
    const mid = String(r.mapId || '');
    const z = zByMid[mid] || zByName[r.zone];
    if (!z || !r.mark || r.mark.x == null || r.mark.y == null) return;
    const pos = zoneToWorld(z.rect, r.mark.x, r.mark.y);
    if (!pos) return;
    const drops = r.drops || [];
    const dropNames = drops.map((x) => x.nameCn || '').join(' ');
    pins.push({
      id: 'rare:' + (r.id || idx),
      cat: 'rare',
      name: r.nameCn || r.nameEn || '稀有',
      en: r.nameEn || '',
      zone: r.zone || z.nameCn,
      mapId: String(z.mapId),
      x: Number(r.mark.x),
      y: Number(r.mark.y),
      wx: pos.wx,
      wy: pos.wy,
      faction: 'N',
      level: lvLabel(r.levelRange),
      tag: r.kind === 'rare-elite' ? '稀有精英' : '稀有',
      isNew: !!r.isNew,
      drops,
      rows: drops.length ? [['掉落记录', `${drops.length} 件装备`]] : [['掉落记录', '暂无掉落记录']],
      search: `${r.nameCn || ''} ${r.nameEn || ''} ${r.zone || z.nameCn} ${dropNames} 稀有`.toLowerCase()
    });
  });

  // 3. 图书馆书籍（来自 world.json）
  ((world && world.books) || []).forEach((b, idx) => {
    const mid = String(b.mapId || '');
    const z = zByMid[mid] || zByName[b.zone];
    if (!z || !b.mark || b.mark.x == null || b.mark.y == null) return;
    const pos = zoneToWorld(z.rect, b.mark.x, b.mark.y);
    if (!pos) return;
    pins.push({
      id: 'book:' + (b.itemId || b.id || idx),
      cat: 'book',
      name: b.nameCn || b.nameEn || '书籍',
      en: b.nameEn || '',
      zone: b.zone || z.nameCn,
      mapId: String(z.mapId),
      x: Number(b.mark.x),
      y: Number(b.mark.y),
      wx: pos.wx,
      wy: pos.wy,
      faction: 'N',
      level: b.afterLevel ? `${b.afterLevel} 级后` : '图书馆书籍',
      tag: '图书馆书籍',
      isNew: !!b.forever,
      drops: [],
      rows: [
        ['容器', b.container || '—'],
        ['位置', b.place || '—'],
        ['物品编号', b.itemId ? `#${b.itemId}` : '—']
      ],
      search: `${b.nameCn || ''} ${b.nameEn || ''} ${b.zone || z.nameCn} ${b.container || ''} ${b.place || ''} 书籍`.toLowerCase()
    });
  });

  // 4. 舒适睡袋营地（来自 world.json）
  const camps = ((world && world.bagTool && world.bagTool.camps) || []).reduce((a, c) => a.concat(c.places || []), []);
  camps.forEach((c, idx) => {
    const mid = String(c.mapId || '');
    const z = zByMid[mid] || zByName[c.zone];
    if (!z || !c.mark || c.mark.x == null || c.mark.y == null) return;
    const pos = zoneToWorld(z.rect, c.mark.x, c.mark.y);
    if (!pos) return;
    const label = c.landmark ? `${c.zone} · ${c.landmark}` : `${c.zone}营地`;
    pins.push({
      id: 'camp:' + idx,
      cat: 'camp',
      name: label,
      en: '',
      zone: c.zone || z.nameCn,
      mapId: String(z.mapId),
      x: Number(c.mark.x),
      y: Number(c.mark.y),
      wx: pos.wx,
      wy: pos.wy,
      faction: 'N',
      level: '休息营地',
      tag: '睡袋营地',
      isNew: false,
      drops: [],
      rows: [
        ['地标', c.landmark || '—'],
        ['方位', c.whereCn || '—']
      ],
      search: `${c.zone || ''} ${c.landmark || ''} ${c.whereCn || ''} 睡袋 营地`.toLowerCase()
    });
  });

  // 5. 传承书籍（来自 legacy-books.json 扩展真源）
  ((legacyData && legacyData.books) || []).forEach((lb, idx) => {
    const mid = String(lb.mapId || lb.uiMapId || '');
    const z = zByMid[mid] || zByName[lb.zone];
    if (!z || lb.x == null || lb.y == null) return;
    const pos = zoneToWorld(z.rect, lb.x, lb.y);
    if (!pos) return;
    const rows = [];
    if (lb.legacyTree) rows.push(['传承分支', lb.legacyTree]);
    if (lb.unlockNote) rows.push(['关联传承', lb.unlockNote]);
    if (lb.itemId) rows.push(['物品编号', `#${lb.itemId}`]);
    if (lb.level) rows.push(['数据分级', lb.level]);
    pins.push({
      id: 'lbook:' + (lb.id || idx),
      cat: 'legacy_book',
      name: lb.nameCn || lb.nameEn || '传承书籍',
      en: lb.nameEn || '',
      zone: lb.zone || z.nameCn,
      mapId: String(z.mapId),
      x: Number(lb.x),
      y: Number(lb.y),
      wx: pos.wx,
      wy: pos.wy,
      faction: normFaction(lb.faction),
      level: lb.legacyTree || '传承书籍',
      tag: '传承书籍',
      isNew: true,
      drops: [],
      rows,
      search: `${lb.nameCn || ''} ${lb.nameEn || ''} ${lb.zone || z.nameCn} ${lb.legacyTree || ''} ${lb.unlockNote || ''} 传承书籍`.toLowerCase()
    });
  });

  // 6. 航线停靠点（船只码头 / 飞艇塔 / 空艇港）
  const transportIcons = {
    boat: 'img/icons/inv_misc_spyglass_02.jpg',
    zeppelin: 'img/icons/ability_skyreach_four_wind.jpg',
    airship: 'img/icons/achievement_guild_ridelikethewind.jpg'
  };
  ((atlas && atlas.transports) || []).forEach((tr) => {
    if (tr.wx == null || tr.wy == null) return;
    const fac = normFaction(tr.faction);
    const dests = (tr.destinations || []).map((d, i) => [i === 0 ? '直达航线' : '另通往', d]);
    pins.push({
      id: tr.id,
      cat: 'transport',
      transportKind: tr.kind,
      iconOverride: transportIcons[tr.kind] || transportIcons.boat,
      name: tr.name,
      en: tr.routeName || '',
      zone: tr.zone || '海域港口',
      mapId: String(tr.mapId || '947'),
      x: Number(tr.x || 50),
      y: Number(tr.y || 50),
      wx: Number(tr.wx),
      wy: Number(tr.wy),
      faction: fac,
      level: tr.kindCn || '航线点',
      tag: `${tr.kindCn || '航线点'} · ${fac === 'A' ? '联盟' : (fac === 'H' ? '部落' : '中立')}`,
      isNew: tr.kind === 'airship',
      drops: [],
      rows: [['航线', tr.routeName || '—']].concat(dests),
      search: `${tr.name} ${tr.routeName || ''} ${tr.zone || ''} ${(tr.destinations || []).join(' ')} 航线 码头 船 飞艇 空艇`.toLowerCase()
    });
  });

  // 7. 城镇 NPC 与区分阵营的飞行管理员（来自 map-npcs.json + 无限新增鸟点）
  ((npcsData && npcsData.pins) || []).forEach((n, idx) => {
    const mid = String(n.m || '');
    const z = zByMid[mid];
    if (!z || n.x == null || n.y == null) return;
    const fac = normFaction(n.f);
    let catKey = n.c;
    if (catKey === 'flight') {
      catKey = fac === 'A' ? 'flight_a' : (fac === 'H' ? 'flight_h' : 'flight_n');
    }
    const catMeta = CAT_BY_KEY[catKey];
    if (!catMeta) return;
    const pos = zoneToWorld(z.rect, n.x, n.y);
    if (!pos) return;
    const rows = [];
    if (n.fp) rows.push(['飞行点', n.fp]);
    if (n.p) rows.push(['专业', n.p]);
    if (n.id) rows.push(['NPC 编号', `#${n.id}`]);
    pins.push({
      id: `npc:${mid}:${n.id || idx}:${catKey}`,
      cat: catKey,
      name: n.n || n.e || catMeta.label,
      en: n.e || '',
      zone: z.nameCn,
      mapId: mid,
      x: Number(n.x),
      y: Number(n.y),
      wx: pos.wx,
      wy: pos.wy,
      faction: fac,
      level: catMeta.label,
      tag: catMeta.label,
      isNew: !!z.isNew,
      drops: [],
      rows,
      search: `${n.n || ''} ${n.e || ''} ${n.fp || ''} ${n.p || ''} ${z.nameCn} ${catMeta.label} ${catKey.startsWith('flight') ? '飞行点 鸟点 飞行管理员' : ''}`.toLowerCase()
    });
  });

  // 补充无限新增区域（海加尔山 / 河林）专属飞行管理员
  ((atlas && atlas.extraFlights) || []).forEach((ef) => {
    const fac = normFaction(ef.faction);
    const catKey = fac === 'A' ? 'flight_a' : (fac === 'H' ? 'flight_h' : 'flight_n');
    const catMeta = CAT_BY_KEY[catKey];
    if (!catMeta || ef.wx == null || ef.wy == null) return;
    pins.push({
      id: `eflight:${ef.id}`,
      cat: catKey,
      name: ef.nameCn,
      en: ef.nameEn || '',
      zone: ef.zone || '无限新域',
      mapId: String(ef.mapId || '2482'),
      x: Number(ef.x || 50),
      y: Number(ef.y || 50),
      wx: Number(ef.wx),
      wy: Number(ef.wy),
      faction: fac,
      level: catMeta.label,
      tag: catMeta.label,
      isNew: true,
      drops: [],
      rows: [['飞行点', ef.nameCn], ['节点编号', `#${ef.id}`]],
      search: `${ef.nameCn} ${ef.nameEn || ''} ${ef.zone || ''} ${catMeta.label} 飞行点 鸟点`.toLowerCase()
    });
  });

  return pins;
}

export function filterVisiblePins(pins, opts) {
  const {
    enabled = {},
    faction = 'all',
    hideDone = false,
    doneSet = null,
    lod = true,
    scale = 1,
    selectedId = '',
    viewBounds = null
  } = opts || {};

  const out = [];
  for (let i = 0; i < pins.length; i++) {
    const p = pins[i];
    const isSel = selectedId && p.id === selectedId;
    if (!isSel) {
      if (!enabled[p.cat]) continue;
      if (faction !== 'all' && p.faction !== 'N' && p.faction !== faction) continue;
      if (hideDone && doneSet && doneSet.has(p.id)) continue;
      const cm = CAT_BY_KEY[p.cat];
      if (lod && cm && scale < cm.minZoom) continue;
      if (viewBounds) {
        if (p.wx < viewBounds.x0 || p.wx > viewBounds.x1 || p.wy < viewBounds.y0 || p.wy > viewBounds.y1) {
          continue;
        }
      }
    }
    out.push(p);
  }
  return out;
}

export function buildWayCommand(pin) {
  if (!pin) return '';
  const x = Number(pin.x || 0).toFixed(1);
  const y = Number(pin.y || 0).toFixed(1);
  return `/way ${pin.zone} ${x} ${y} ${pin.name}`;
}

export function buildShareHash(pin) {
  if (!pin) return '#/world';
  const q = new URLSearchParams({
    map: String(pin.mapId),
    x: Number(pin.x || 0).toFixed(1),
    y: Number(pin.y || 0).toFixed(1),
    pin: String(pin.id)
  });
  return '#/world?' + q.toString();
}

export function loadDoneSet() {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return new Set();
    const raw = window.localStorage.getItem(DONE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr : []);
  } catch (_) {
    return new Set();
  }
}

export function saveDoneSet(setObj) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    window.localStorage.setItem(DONE_KEY, JSON.stringify(Array.from(setObj || [])));
  } catch (_) {}
}
