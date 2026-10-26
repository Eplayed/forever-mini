import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { SLOT_NODE, gearNodes } from '../src/lib/bis-model.js';

/* 拿真 bis.json 跑：部位名单是上游给的，哪天多出一个没映射的部位，
   界面上就是"那一件在模型上没有"——这条测试负责在我们发现之前先红。 */
const BIS = JSON.parse(fs.readFileSync(path.join(__dirname, '../../app/data/bis.json'), 'utf8'));
const MANIFEST = JSON.parse(fs.readFileSync(
  path.join(__dirname, '../../app/img/models/manifest.json'), 'utf8'));
const GEAR_NODES = (MANIFEST.items[0] || {}).gearNodes || [];

const ALL_SLOTS = [...new Set(BIS.sets.flatMap((s) => s.doll.alliance.map((c) => c.slot)))];

describe('配装部位 → 模型节点', () => {
  it('38 套里出现过的每一个部位都映射得到（新增部位必须先加节点）', () => {
    const missing = ALL_SLOTS.filter((x) => !SLOT_NODE[x]);
    expect(missing).toEqual([]);
  });
  it('映射表里每个节点名在模型台账里真的存在（两边名字对不上就是白染）', () => {
    const want = Object.values(SLOT_NODE).flat();
    expect(want.filter((n) => GEAR_NODES.indexOf(n) < 0)).toEqual([]);
    // 台账里也不该有数据永远填不上的空节点
    expect(GEAR_NODES.filter((n) => want.indexOf(n) < 0)).toEqual([]);
  });
  it('戒指与饰品各两枚，按 cell 落到两个不同节点', () => {
    const doll = BIS.sets.filter((s) => s.id === 'warrior')[0].doll.alliance;
    const g = gearNodes(doll);
    expect(g.ring1.item).not.toBe(g.ring2.item);
    expect(g.trinket1.item).not.toBe(g.trinket2.item);
    expect(g.unmapped).toEqual([]);
  });
  it('每一套的每一格都能落到节点上，格数与节点数一致', () => {
    BIS.sets.forEach((s) => {
      ['alliance', 'horde'].forEach((f) => {
        const g = gearNodes(s.doll[f]);
        expect(g.unmapped).toEqual([]);
        expect(Object.keys(g).filter((k) => k !== 'unmapped').length).toBe(s.doll[f].length);
      });
    });
  });
  it('认不出的部位进 unmapped，不硬塞到别的格子上冒充', () => {
    const g = gearNodes([{ slot: '衬衫', cell: 1, item: 36 }]);
    expect(g.unmapped).toEqual(['衬衫']);
    expect(Object.keys(g).filter((k) => k !== 'unmapped')).toEqual([]);
  });
  it('缺 cell 时按第一格处理（上游哪天不写 cell 也不会崩）', () => {
    const g = gearNodes([{ slot: '戒指', item: 19517 }]);
    expect(g.ring1.item).toBe(19517);
    expect(g.ring2).toBeUndefined();
  });
});
