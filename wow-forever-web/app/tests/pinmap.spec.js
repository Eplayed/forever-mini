import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import PinMap from '../src/components/PinMap.vue';

/* 2026-10-20 W01-A：无图那一屏与"图请求失败"这两态的行为。
   归一化形状照 WorldPage/DungeonPage 传给 PinMap 的那份（kind/pin/x/y/mapFile/mapId/coord）。 */
function item(id, over) {
  return Object.assign({
    key: 'r' + id, kind: 'rare', pin: true, x: 30 + id, y: 40 + id,
    mapFile: 'img/art/maps/1426.webp', mapId: '1426', name: '点' + id, en: '',
    tag: '稀有', isNew: false, level: '30-39', coord: (30 + id) + '，' + (40 + id),
    rows: [], drops: [], hint: ''
  }, over || {});
}
const NOMAP = { mapFile: '', mapId: '2548', pin: false, x: null, y: null };

describe('PinMap 有图那一态', () => {
  it('渲染底图与点位，点数等于带坐标的条数', () => {
    const w = mount(PinMap, { props: { alt: '测试区域', items: [item(1), item(2)] } });
    expect(w.find('.zbig').exists()).toBe(true);
    expect(w.find('.zcanvas img').attributes('src')).toContain('img/art/maps/1426.webp');
    expect(w.findAll('.zdot').length).toBe(2);
    expect(w.findAll('.zrow').length).toBe(2);
    expect(w.find('.znomap').exists()).toBe(false);
  });
});

describe('PinMap 无图那一态（2026-10-20 W01 改成紧凑文本）', () => {
  /* fallbackMapId 是真实调用方给的那一份：ZoneCard 传 :fallback-map-id="z.mapId"。
     没有可画的点时，组件上的 mapId 就来自这个兜底值——编号沿用数据值，不新写句子。 */
  const props = { alt: '河林', items: [item(1, NOMAP), item(2, NOMAP)], fallbackMapId: '2548' };
  it('不渲染图框、一颗点都不画', () => {
    const w = mount(PinMap, { props: props });
    expect(w.find('.zbig').exists()).toBe(false);
    expect(w.find('.zcanvas').exists()).toBe(false);
    expect(w.findAll('.zdot').length).toBe(0);
  });
  it('只留数据值那一行（地图编号沿用传进来的值），列表信息一条不少', () => {
    const w = mount(PinMap, { props: props });
    expect(w.find('.znomap').exists()).toBe(true);
    expect(w.find('.znomap').text()).toBe('地图编号 2548');
    expect(w.findAll('.zrow').length).toBe(2);
    expect(w.findAll('.zrow')[0].text()).toContain('31，41');
  });
  it('整宽：无图时 .zband 带 nomap（列表不再被挤进右边 330px）', () => {
    expect(mount(PinMap, { props: props }).find('.zband').classes()).toContain('nomap');
  });
  it('调用方接管无图说明时（noMapLine=false）整块不渲染，不留空容器', () => {
    const w = mount(PinMap, { props: Object.assign({ noMapLine: false }, props) });
    expect(w.find('.zband').exists()).toBe(false);
    expect(w.text()).toBe('');
  });
});

describe('PinMap 底图请求失败', () => {
  it('失败就落回无图紧凑态，不摆一张破图', async () => {
    const w = mount(PinMap, { props: { alt: '测试区域', items: [item(1)] } });
    await w.find('.zcanvas img').trigger('error');
    expect(w.find('.zbig').exists()).toBe(false);
    expect(w.findAll('.zdot').length).toBe(0);
    expect(w.find('.znomap').text()).toBe('地图编号 1426');
  });
  it('换到另一组好图能恢复（原来一次失败会永久污染这块面板）', async () => {
    const w = mount(PinMap, { props: { alt: '测试区域', items: [item(1)] } });
    await w.find('.zcanvas img').trigger('error');
    expect(w.find('.zbig').exists()).toBe(false);
    await w.setProps({ items: [item(5, { mapId: '1427', mapFile: 'img/art/maps/1427.webp' })] });
    await nextTick();
    expect(w.find('.zbig').exists()).toBe(true);
    expect(w.find('.zcanvas img').attributes('src')).toContain('1427.webp');
    expect(w.findAll('.zdot').length).toBe(1);
  });
});
