import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

// useRoute 在页面里读了三次 query（q/c/w/to），测试不挂真路由，给一个空 query 的桩
vi.mock('vue-router', () => ({ useRoute: () => ({ query: {}, path: '/updates' }) }));

import UpdatesPage from '../src/pages/UpdatesPage.vue';
import { forget } from '../src/lib/data.js';

/* 这份小样本是**手搓的**，不是从 changes.json 抄的——为的是把两个字段刻意拧开：
   kind 只有 talent/spell，changeKind 才有 added/modified/…，
   上一版格子数的是 kind、筛的是 changeKind，所以除「全部类别」外全是 0。
   期望值全部由下面这几行手算，不许用生产函数的输出反推（那等于自己给自己判卷）。 */
const ITEMS = [
  { id: 1, classId: 'hunter', kind: 'talent', changeKind: 'added', nameCn: '野兽控制', tree: '野兽控制', changeCn: '新增' },
  { id: 2, classId: 'hunter', kind: 'talent', changeKind: 'modified', nameCn: '瞄准射击', tree: '射击', changeCn: '改动' },
  { id: 3, classId: 'hunter', kind: 'spell', changeKind: 'added', nameCn: '宠物快乐', tree: '', changeCn: '新增' },
  { id: 4, classId: 'mage', kind: 'talent', changeKind: 'removed', nameCn: '寒冰箭', tree: '冰霜', changeCn: '移除' },
  { id: 5, classId: 'mage', kind: 'spell', changeKind: 'unchanged', nameCn: '奥术智慧', tree: '', changeCn: '未变' },
  { id: 6, classId: 'priest', kind: 'talent', changeKind: 'renamed', nameCn: '恢复', tree: '神圣', changeCn: '改名' },
  { id: 7, classId: 'priest', kind: 'spell', changeKind: 'moved', nameCn: '治疗之环', tree: '', changeCn: '换层或换系' },
  { id: 8, classId: 'priest', kind: 'talent', changeKind: 'unchanged', nameCn: '渐隐术', tree: '暗影', changeCn: '未变' },
  // 第九类：不在旧的那张写死的六项名单里。以前这种条目没有格子，
  // 「全部类别」和六格之和差 15 条，玩家把每格点一遍也筛不到它们。
  { id: 9, classId: 'mage', kind: 'spell', changeKind: 'baseline', nameCn: '奥术光辉', tree: '', changeCn: '基线' }
];
// 手算：按 changeKind 数（不是 kind）
const BY_CHG = ITEMS.reduce((a, x) => (a[x.changeKind] = (a[x.changeKind] || 0) + 1, a), {});
const CLASSES = [{ id: 'hunter', cn: '猎人' }, { id: 'mage', cn: '法师' }, { id: 'priest', cn: '牧师' }];

const DATA = {
  'data/changes.json': { items: ITEMS },
  'data/timeline.json': { items: [] },
  'data/releases.json': { items: [] },
  'data/classes.json': { classes: CLASSES },
  'data/scale.json': { scale: {} }
};

function stubFetch() {
  vi.stubGlobal('fetch', (u) => {
    const key = String(u).replace(/^\/+/, '');
    return Promise.resolve({ ok: key in DATA, status: key in DATA ? 200 : 404,
      json: () => Promise.resolve(DATA[key] || {}) });
  });
}

async function page() {
  Object.keys(DATA).forEach(forget);       // 模块级缓存跨用例留着，每个用例都从空缓存起
  const w = mount(UpdatesPage, { attachTo: document.body });
  await flushPromises();
  await w.vm.$nextTick();
  await new Promise((r) => setTimeout(r, 0));
  await flushPromises();
  return w;
}
const chips = (w) => w.findAll('.kchip').map((d) => ({
  k: d.attributes('data-k'),
  n: parseInt(d.find('b').text(), 10)
}));
const cnt = (w) => parseInt(w.find('#ccnt').text(), 10);

beforeEach(() => { vi.unstubAllGlobals(); stubFetch(); });

describe('最新动态 · 类别计数与筛选结果同一把尺子（W02）', () => {
  it('默认态：每个格子的数就是按 changeKind 手算的数，不是恒 0', async () => {
    const w = await page();
    const c = Object.fromEntries(chips(w).map((x) => [x.k, x.n]));
    expect(c.all).toBe(9);
    expect(c.added).toBe(BY_CHG.added);          // 手算 2
    expect(c.modified).toBe(BY_CHG.modified);    // 手算 1
    expect(c.removed).toBe(BY_CHG.removed);      // 手算 1
    expect(c.moved).toBe(BY_CHG.moved);          // 手算 1
    expect(c.renamed).toBe(BY_CHG.renamed);      // 手算 1
    expect(c.unchanged).toBe(BY_CHG.unchanged);  // 手算 2
    expect(Object.values(c).every((n) => n > 0)).toBe(true);
    // 格子必须盖全：各类别之和 = 全部类别，不然总有几条筛不到（差 15 条那种）
    expect(Object.entries(c).filter(([k]) => k !== 'all')
      .reduce((a, [, n]) => a + n, 0)).toBe(c.all);
    w.unmount();
  });

  it('数据里冒出来的新类别自动多一格，标签用条目自带的那个词', async () => {
    const w = await page();
    const labels = w.findAll('.kchip').map((d) => d.text());
    const b = w.find('.kchip[data-k="baseline"]');
    expect(b.exists()).toBe(true);
    expect(b.text()).toContain('基线');          // 取的是 changeCn，不是页面另写一份
    await b.trigger('click');
    await flushPromises();
    expect(cnt(w)).toBe(1);
    expect(w.find('#chbody tbody tr td:nth-child(2)').text()).toContain('奥术光辉');
    w.unmount();
    expect(labels.length).toBe(8);               // 全部类别 + 数据里七种类别
  });

  it('点任意格子，表头报的条数等于格子上那个数', async () => {
    const w = await page();
    for (const x of chips(w)) {
      await w.find(`.kchip[data-k="${x.k}"]`).trigger('click');
      await flushPromises();
      expect(cnt(w)).toBe(x.n);
    }
    w.unmount();
  });

  it('叠上职业与"只看天赋"后，格子的数跟着变，点下去仍然对得上', async () => {
    const w = await page();
    await w.find('.pick[data-c="priest"]').trigger('click');
    await w.find('#cw').setValue('talent');
    await flushPromises();
    // 手算：priest 且 kind=talent 的只有 id6(renamed)、id8(unchanged)
    const c = Object.fromEntries(chips(w).map((x) => [x.k, x.n]));
    expect(c.all).toBe(2);
    expect(c.renamed).toBe(1);
    expect(c.unchanged).toBe(1);
    expect(c.added).toBe(0);
    for (const x of chips(w)) {
      await w.find(`.kchip[data-k="${x.k}"]`).trigger('click');
      await flushPromises();
      expect(cnt(w)).toBe(x.n);
    }
    w.unmount();
  });

  it('搜一个不存在的词：格子全归零、表头 0 条、空态文案在', async () => {
    const w = await page();
    await w.find('#cq').setValue('根本没有这个名字');
    await flushPromises();
    expect(chips(w).every((x) => x.n === 0)).toBe(true);
    expect(cnt(w)).toBe(0);
    expect(w.find('.empty').exists()).toBe(true);
    expect(w.find('.boardwrap').exists()).toBe(false);
    w.unmount();
  });

  it('职业格子的数同样跟着类别与搜索走（不是恒等于该职业全量）', async () => {
    const w = await page();
    const before = w.find('.pick[data-c="hunter"] span').text();
    expect(parseInt(before, 10)).toBe(3);        // 手算：hunter 三条
    await w.find('.kchip[data-k="added"]').trigger('click');
    await flushPromises();
    expect(parseInt(w.find('.pick[data-c="hunter"] span').text(), 10)).toBe(2);   // 新增两条
    expect(parseInt(w.find('.pick[data-c="mage"] span').text(), 10)).toBe(0);
    // 「全职业」这一格也跟着放开职业这一维：等于当前类别命中的 2 条，不是列表全量 8
    expect(parseInt(w.find('.pick[data-c=""] span').text(), 10)).toBe(2);
    w.unmount();
  });
});
