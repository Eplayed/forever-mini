import { describe, it, expect, beforeEach } from 'vitest';
import {
  MAP_CATEGORIES,
  defaultEnabledMap,
  zoneToWorld,
  normalizeMapPins,
  filterVisiblePins,
  buildWayCommand,
  buildShareHash,
  loadDoneSet,
  saveDoneSet
} from '../src/lib/world-map.js';

describe('Infinite Map engine (world-map.js)', () => {
  const sampleAtlas = {
    meta: { canvas: { w: 2400, h: 1660 } },
    zones: [
      { mapId: '1413', nameCn: '贫瘠之地', rect: [470, 520, 240, 160], continent: 'kal', isNew: false },
      { mapId: '1429', nameCn: '艾尔文森林', rect: [1470, 1080, 210, 140], continent: 'ek', isNew: false }
    ],
    dungeons: [
      { slug: 'wailing-caverns', nameCn: '哀嚎洞穴', nameEn: 'Wailing Caverns', isRaid: false, isNew: false, levelRange: [15, 24], mapId: '1413', x: 46, y: 36 }
    ]
  };
  const sampleWorld = {
    rares: [
      { id: 'r1', nameCn: '断矛', nameEn: 'Dishu', zone: '贫瘠之地', mapId: '1413', mark: { x: 52, y: 31 }, levelRange: [20, 20], drops: [{ itemId: 1001, nameCn: '测试装备', quality: 3 }] }
    ],
    books: [
      { id: 'b1', itemId: 203755, nameCn: '研究日志', zone: '艾尔文森林', mapId: '1429', mark: { x: 65.4, y: 70.1 }, container: '图书馆书籍', place: '阿祖拉之塔' }
    ],
    bagTool: {
      camps: [{ places: [{ zone: '艾尔文森林', mapId: '1429', mark: { x: 30, y: 60 }, landmark: '闪金镇' }] }]
    }
  };
  const sampleNpcs = {
    pins: [
      { m: '1413', x: 51, y: 30, c: 'flight', f: 'H', n: '德弗拉克', fp: '十字路口' },
      { m: '1429', x: 43, y: 65, c: 'vendor', f: 'A', n: '商人甲', id: 99 }
    ]
  };
  const sampleLegacy = {
    books: [
      { id: 'lb1', nameCn: '传承测试卷', zone: '艾尔文森林', mapId: '1429', x: 50, y: 50, faction: 'N', legacyTree: '探索', level: 'L2' }
    ]
  };

  beforeEach(() => {
    try { window.localStorage.removeItem('wow_forever_v1_world_done'); } catch (_) {}
  });

  it('maps zone percentage coordinates onto stitched world canvas coordinates', () => {
    const pos = zoneToWorld([470, 520, 240, 160], 50, 25);
    expect(pos).toEqual({ wx: 590, wy: 560 });
  });

  it('normalizes dungeons, rares, library books, camps, NPCs, and legacy books into unified pins', () => {
    const pins = normalizeMapPins(sampleAtlas, sampleWorld, sampleNpcs, sampleLegacy);
    expect(pins.length).toBe(7);
    const cats = new Set(pins.map((p) => p.cat));
    expect(cats.has('dungeon')).toBe(true);
    expect(cats.has('rare')).toBe(true);
    expect(cats.has('book')).toBe(true);
    expect(cats.has('camp')).toBe(true);
    expect(cats.has('flight_h')).toBe(true);
    expect(cats.has('vendor')).toBe(true);
    expect(cats.has('legacy_book')).toBe(true);
  });

  it('applies OpenMap-style zoom LOD, faction filter, viewport culling, and selectedId override', () => {
    const pins = normalizeMapPins(sampleAtlas, sampleWorld, sampleNpcs, sampleLegacy);
    const enabled = defaultEnabledMap();
    // 默认全不选，让用户自行打勾筛选
    expect(Object.values(enabled).every((v) => v === false)).toBe(true);
    // 手动勾选全部图层后验证 LOD / 阵营 / 视口裁剪
    Object.keys(enabled).forEach((k) => { enabled[k] = true; });

    // Low zoom (0.6x): dungeon (0.45), camp (0.5), and legacy_book (0.45) survive LOD; rare/vendor stay hidden
    const far = filterVisiblePins(pins, { enabled, scale: 0.6, lod: true });
    expect(far.map((p) => p.cat).sort()).toEqual(['camp', 'dungeon', 'legacy_book']);

    // High zoom (3.6x) with Alliance faction: hides Horde flight master
    const closeA = filterVisiblePins(pins, { enabled, scale: 3.6, lod: true, faction: 'A' });
    expect(closeA.some((p) => p.cat === 'flight_h')).toBe(false);
    expect(closeA.some((p) => p.cat === 'vendor')).toBe(true);

    // Viewport culling filters out Eastern Kingdoms when looking only at Kalimdor
    const kalOnly = filterVisiblePins(pins, {
      enabled, scale: 3.6, lod: true,
      viewBounds: { x0: 400, y0: 450, x1: 800, y1: 750 }
    });
    expect(kalOnly.every((p) => p.mapId === '1413')).toBe(true);
    expect(kalOnly.length).toBe(3);

    // Selected pin always stays visible regardless of LOD or category toggle
    const sel = pins.find((p) => p.cat === 'vendor');
    enabled.vendor = false;
    const withSel = filterVisiblePins(pins, { enabled, scale: 0.6, lod: true, selectedId: sel.id });
    expect(withSel.some((p) => p.id === sel.id)).toBe(true);
  });

  it('builds /way commands, share hashes, and persists check-off progress', () => {
    const pins = normalizeMapPins(sampleAtlas, sampleWorld, sampleNpcs, sampleLegacy);
    const rare = pins.find((p) => p.cat === 'rare');
    expect(buildWayCommand(rare)).toBe('/way 贫瘠之地 52.0 31.0 断矛');
    expect(buildShareHash(rare)).toContain('#/world?map=1413');
    expect(buildShareHash(rare)).toContain('pin=rare%3Ar1');

    const s = new Set(['lbook:lb1', 'book:203755']);
    saveDoneSet(s);
    const loaded = loadDoneSet();
    expect(loaded.has('lbook:lb1')).toBe(true);
    expect(loaded.has('book:203755')).toBe(true);
    expect(MAP_CATEGORIES.some((c) => c.key === 'legacy_book' && c.checkable)).toBe(true);
    expect(MAP_CATEGORIES.every((c) => typeof c.icon === 'string' && c.icon.startsWith('img/icons/'))).toBe(true);
    const inn = MAP_CATEGORIES.find((c) => c.key === 'innkeeper');
    expect(inn && inn.icon).toBe('img/icons/inv_misc_rune_01.jpg');
  });
});
