import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import SiteSearch from '../src/components/SiteSearch.vue';
import { forget } from '../src/lib/data.js';

// 假索引就是 src/data/search.json 的字段顺序，只放几条真出现过的名字
const FAKE = {
  meta: {
    kinds: {
      cls: ['职业', 'talent.html', ''],
      rare: ['稀有精英', 'world.html', 'q'],
      rec: ['配方', 'professions.html', 'q'],
      chg: ['客户端改动', 'updates.html', 'q']
    }
  },
  items: [
    ['cls', '潜行者', '53 个天赋节点', 'c=rogue', 'L3'],
    ['chg', '潜行', '潜行者 · 未变', 'c=rogue&w=spell', 'L0'],
    ['rec', '潜行者52型', '工程学 · 无限新增', 'p=engineering', 'L0'],
    ['rare', '咆鼻', '莫高雷', 't=rares', 'L0']
  ]
};

function stubFetch(map) {
  vi.stubGlobal('fetch', (u) => {
    const key = String(u).replace(/^\/+/, '');
    if (map[key] === undefined) {
      return Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({}) });
    }
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(map[key]) });
  });
}

const ROUTER = { global: { stubs: { RouterLink: { props: ['to'], template: '<a><slot /></a>' } } } };

describe('SiteSearch 全站搜索框', () => {
  beforeEach(() => { forget('data/search.json'); stubFetch({ 'data/search.json': FAKE }); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('没输入前结果区是隐藏的，不占屏', () => {
    const w = mount(SiteSearch, { props: { total: 4202 }, ...ROUTER });
    expect(w.find('#gres').attributes('hidden')).toBeDefined();
    expect(w.find('input').attributes('aria-label')).toContain('全站搜索');
    expect(w.find('input').attributes('placeholder')).toContain('4202');
    w.unmount();
  });
  it('输入后按板块分组，同名那条排最前', async () => {
    const w = mount(SiteSearch, { props: { total: 4 }, ...ROUTER });
    await w.find('input').setValue('潜行');
    await flushPromises();
    const groups = w.findAll('.gsh b').map((n) => n.text());
    expect(groups).toEqual(['职业', '客户端改动', '配方']);
    expect(w.findAll('.gsr').length).toBe(3);
    expect(w.find('.gsr b').text()).toBe('潜行者');
    expect(w.text()).toContain('命中 3 条');
    w.unmount();
  });
  it('跳转目标：已迁的页走站内路由，没迁的链回旧站文件并带上编码后的词', async () => {
    const w = mount(SiteSearch, { props: { total: 4 }, ...ROUTER });
    await w.find('input').setValue('咆鼻');          // world.html 已迁 → router-link
    await flushPromises();
    expect(w.findAll('.gsr').length).toBe(1);
    expect(w.find('.gsr').text()).toContain('莫高雷');
    await w.find('input').setValue('潜行者52型');     // professions.html 未迁 → 旧站链接
    await flushPromises();
    expect(w.find('.gsr').attributes('href'))
      .toContain('professions.html?p=engineering&q=%E6%BD%9C%E8%A1%8C%E8%80%8552%E5%9E%8B');
    w.unmount();
  });
  it('分级不是 L0 的结果除颜色外还带文字（红线：不靠颜色承载信息）', async () => {
    const w = mount(SiteSearch, { props: { total: 4 }, ...ROUTER });
    await w.find('input').setValue('潜行者');
    await flushPromises();
    const lv = w.find('.gsr .lv');
    expect(lv.text()).toBe('缺数据');
    expect(lv.classes()).toContain('L3');
    w.unmount();
  });
  it('搜不到时直说没有，不硬凑结果', async () => {
    const w = mount(SiteSearch, { props: { total: 4 }, ...ROUTER });
    await w.find('input').setValue('不存在的词');
    await flushPromises();
    expect(w.findAll('.gsr').length).toBe(0);
    expect(w.find('#gres').text()).toContain('索引里没有');
    w.unmount();
  });
  it('示例词点了就当真搜一遍', async () => {
    const w = mount(SiteSearch, { props: { total: 4 }, ...ROUTER });
    await w.findAll('.gsx')[2].trigger('click');      // 咆鼻
    await flushPromises();
    expect(w.find('input').element.value).toBe('咆鼻');
    expect(w.findAll('.gsr').length).toBe(1);
    w.unmount();
  });
});
