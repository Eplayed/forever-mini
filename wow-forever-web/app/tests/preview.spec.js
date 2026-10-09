import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { gridCells, countStates, nodeLabel, nodeFile, calcFile, treeOf } from '../src/lib/preview.js';
import TalentPreview from '../src/components/TalentPreview.vue';

// 假预览数据按 src/data/talent-preview.json 的字段顺序：[行, 列, 名称, 图标键, 上限, 改动状态]
const PV = {
  classes: {
    warrior: {
      cn: '战士',
      trees: [
        { n: '武器', nodes: [[0, 1, '强化英勇打击', 'ability_rogue_ambush', 3, 'modified'],
                             [1, 0, '穿刺', null, 2, 'added'],
                             [3, 3, '愤怒掌控', 'inv_x', 1, 'unchanged']] },
        { n: '狂暴', nodes: [[0, 0, '嗜血', 'inv_y', 1, 'moved']] },
        { n: '防护', nodes: [[0, 0, '盾牌 mastery', 'inv_z', 5, '']] }
      ]
    }
  }
};
const CLASSES = [{ id: 'warrior', cn: '战士', talentCount: 54, iconKey: 'class_warrior' }];

describe('预览网格', () => {
  it('按行优先铺满 4 列，空格补 null，格子总数 = 行数 × 4', () => {
    const cells = gridCells(PV.classes.warrior.trees[0]);
    expect(cells.length).toBe(16);                     // 最大行号 3 → 4 行 × 4 列
    expect(cells.filter((c) => c === null).length).toBe(13);
    expect(cells[0 * 4 + 1][2]).toBe('强化英勇打击');   // 第 0 行第 1 列
    expect(cells[1 * 4 + 0][2]).toBe('穿刺');           // 第 1 行第 0 列
    expect(cells[3 * 4 + 3][2]).toBe('愤怒掌控');       // 最后一行最后一列
  });
  it('空树与缺数据都不炸', () => {
    expect(gridCells(null)).toEqual([]);
    expect(countStates(null)).toEqual([]);
    expect(treeOf(PV, 'mage', 0)).toBeNull();
  });
  it('状态计数只数真有的，顺序固定：新增 → 改动 → 换层 → 未变 → 没有对照结果', () => {
    const st = countStates(PV.classes.warrior.trees[0]);
    expect(st.map((x) => [x.label, x.n])).toEqual([['新增', 1], ['改动', 1], ['未变', 1]]);
    expect(st.reduce((a, x) => a + x.n, 0)).toBe(3);
    const withNone = countStates(PV.classes.warrior.trees[2]);
    expect(withNone.map((x) => x.label)).toEqual(['没有对照结果']);
  });
});

describe('跳转与读数', () => {
  it('节点名带上限与改动状态，缺上限写未核实', () => {
    expect(nodeLabel([0, 1, '强化英勇打击', 'i', 3, 'modified']))
      .toBe('强化英勇打击，上限 3 层；与经典旧世相比：改动');
    expect(nodeLabel([0, 1, '某天赋', null, null, ''])).toContain('上限 未核实');
    expect(nodeLabel([0, 1, '某天赋', null, 2, ''])).toContain('没有对照结果');
  });
  it('跳计算器的链接带职业、哪一系与天赋名，中文按 URL 编码', () => {
    expect(nodeFile('warrior', 2, '盾牌 mastery')).toBe(
      'talent.html?c=warrior&tree=2&q=%E7%9B%BE%E7%89%8C%20mastery');
    expect(calcFile('warrior', 0)).toBe('talent.html?c=warrior&tree=0');
  });
});

describe('TalentPreview 组件', () => {
  const ROUTER = { global: { stubs: { RouterLink: { props: ['to'], template: '<a><slot /></a>' } } } };

  it('默认看第一个职业的第一系，格子数 = 数据里的节点 + 空格', () => {
    const w = mount(TalentPreview, { props: { preview: PV, classes: CLASSES }, ...ROUTER });
    expect(w.findAll('.pnode').length).toBe(3);
    expect(w.findAll('.pempty').length).toBe(13);
    expect(w.findAll('.pvpicks .pick').length).toBe(3);
    expect(w.find('.pvpicks .pick.on').text()).toContain('武器');
    expect(w.find('.stripc.on').text()).toContain('战士');
    w.unmount();
  });
  it('点系切换树，点职业切换职业', async () => {
    const w = mount(TalentPreview, { props: { preview: PV, classes: CLASSES }, ...ROUTER });
    await w.findAll('.pvpicks .pick')[1].trigger('click');
    expect(w.findAll('.pnode').length).toBe(1);
    expect(w.find('.pv .pnode').text()).toContain('嗜');        // 自绘块的首字
    expect(w.find('.cta').text()).toContain('狂暴');
    w.unmount();
  });
  it('每个格子都是进计算器的链接，标题写着这格是什么', () => {
    const w = mount(TalentPreview, { props: { preview: PV, classes: CLASSES }, ...ROUTER });
    const n = w.find('.pnode');
    expect(n.attributes('href')).toContain('talent.html?c=warrior&tree=0&q=');
    expect(n.attributes('aria-label')).toBe('强化英勇打击，上限 3 层；与经典旧世相比：改动');
    expect(n.classes()).toContain('chg-modified');
    w.unmount();
  });
  it('数据没到位时不炸，只给空树提示', () => {
    const w = mount(TalentPreview, { props: { preview: { classes: {} }, classes: [] }, ...ROUTER });
    expect(w.findAll('.pnode').length).toBe(0);
    expect(w.find('.cta').text()).toContain('完整计算器');
    w.unmount();
  });
});
