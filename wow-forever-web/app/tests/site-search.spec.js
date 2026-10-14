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

// 全量迁移后所有板块都走路由：stub 把 { to, query } 渲染成可断言的 href（#/路径?query）
const ROUTER = { global: { stubs: { RouterLink: {
  props: ['to'],
  computed: {
    href() {
      const t = this.to;
      if (t && typeof t === 'object') {
        const q = Object.keys(t.query || {}).map((k) => k + '=' + encodeURIComponent(t.query[k])).join('&');
        return '#' + (t.path || '') + (q ? '?' + q : '');
      }
      return t;
    }
  },
  template: '<a :href="href"><slot /></a>'
} } } };

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
  it('跳转目标：全量迁移后所有页都走站内路由并带上编码后的词', async () => {
    const w = mount(SiteSearch, { props: { total: 4 }, ...ROUTER });
    await w.find('input').setValue('咆鼻');          // world.html → router-link
    await flushPromises();
    expect(w.findAll('.gsr').length).toBe(1);
    expect(w.find('.gsr').text()).toContain('莫高雷');
    expect(w.find('.gsr').attributes('href'))
      .toContain('#/world?t=rares&q=%E5%92%86%E9%BC%BB');
    await w.find('input').setValue('潜行者52型');     // professions.html 已迁 → 站内路由
    await flushPromises();
    expect(w.find('.gsr').attributes('href'))
      .toContain('/professions?p=engineering&q=%E6%BD%9C%E8%A1%8C%E8%80%8552%E5%9E%8B');
    w.unmount();
  });
  it('搜索结果不再挂分级文字（2026-10-12：内容页只留标题与数据）', async () => {
    const w = mount(SiteSearch, { props: { total: 4 }, ...ROUTER });
    await w.find('input').setValue('潜行者');
    await flushPromises();
    expect(w.findAll('.gsr').length).toBeGreaterThan(0);
    expect(w.find('.gsr .lv').exists()).toBe(false);
    expect(w.find('.gsr').text()).not.toContain('缺数据');
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
