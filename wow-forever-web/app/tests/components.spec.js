import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import LevelPill from '../src/components/LevelPill.vue';
import IconCell from '../src/components/IconCell.vue';
import ClassTile from '../src/components/ClassTile.vue';
import CovBar from '../src/components/CovBar.vue';
import ZoneMap from '../src/components/ZoneMap.vue';
import ZoneCard from '../src/components/ZoneCard.vue';
import SourceList from '../src/components/SourceList.vue';
import HlText from '../src/components/HlText.vue';

describe('LevelPill', () => {
  // 2026-10-12 用户决定：内容页只留标题与数据，分级徽标不上页面（出处集中在溯源页）。
  // 这两条钉的是"不许再画回去"，不是徽标长什么样——纯函数的映射由 fmt.spec 管。
  it('内容页不渲染分级徽标', () => {
    expect(mount(LevelPill, { props: { level: 'L2' } }).text()).toBe('');
    expect(mount(LevelPill, { props: { level: 'L2' } }).find('.pill').exists()).toBe(false);
  });
  it('脏等级也不会漏出一个空壳', () => {
    expect(mount(LevelPill, { props: { level: 'x' } }).text()).toBe('');
  });
});

describe('IconCell', () => {
  it('有键时叠本地官方图，无键时只有自绘块', () => {
    const withImg = mount(IconCell, { props: { iconKey: 'inv_misc_book_12', seed: 1, cn: '书' } });
    expect(withImg.find('img').attributes('src')).toContain('inv_misc_book_12.jpg');
    const noImg = mount(IconCell, { props: { iconKey: '', seed: 'x', cn: '书' } });
    expect(noImg.find('img').exists()).toBe(false);
    expect(noImg.find('svg').exists()).toBe(true);
  });
  it('图读不出来时撤掉 img、露出自绘块，不留空白也不产生失败请求', async () => {
    const w = mount(IconCell, { props: { iconKey: 'inv_missing_key', seed: 'x', cn: '斧' } });
    await w.find('img').trigger('error');
    expect(w.find('img').exists()).toBe(false);
    expect(w.find('svg text').text()).toBe('斧');
  });
  it('small 只改尺寸类名', () => {
    expect(mount(IconCell, { props: { small: true, seed: 'a', cn: 'a' } }).classes()).toContain('sm');
  });
});

describe('ClassTile', () => {
  it('用职业色画渐变与首字，img 不带类名（与旧站 tileWrap 一致）', () => {
    const w = mount(ClassTile, { props: { classId: 'hunter', cn: '猎人', iconKey: 'class_hunter' } });
    expect(w.find('rect').attributes('stroke')).toBe('#aad372');
    expect(w.find('text').text()).toBe('猎');
    expect(w.find('img').classes()).toEqual([]);
  });
});

describe('CovBar', () => {
  // 覆盖率条属于"讲我们数据质量"的东西，2026-10-12 起不上内容页（见 src/lib/prov.js）
  it('内容页不渲染覆盖率条', () => {
    const w = mount(CovBar, { props: { cov: { L0: 366, L1: 114, L2: 360, L3: 2, total: 842 } } });
    expect(w.find('.cov').exists()).toBe(false);
    expect(w.text()).toBe('');
  });
});

describe('ZoneMap', () => {
  it('有本地小地图时按数据百分比摆标记点', () => {
    const w = mount(ZoneMap, {
      props: { mapFile: 'img/art/maps/1412.webp', mapId: 1412, mark: { x: 32.7, y: 64.5 }, alt: '莫高雷' }
    });
    expect(w.find('img').attributes('alt')).toBe('莫高雷的区域小地图');
    expect(w.find('.zmark').attributes('style')).toContain('left: 32.7%');
    // 素材出处角标不上内容页了（2026-10-12），但图与标记点照旧
    expect(w.text()).not.toContain('本地转存');
  });
  it('客户端没切图时给地图编号与说明，不放假图', () => {
    const w = mount(ZoneMap, { props: { mapFile: '', mapId: 2548, alt: '河林' } });
    expect(w.find('img').exists()).toBe(false);
    expect(w.classes()).toContain('none');
    expect(w.text()).toContain('地图编号 2548');
    expect(w.text()).not.toContain('没有切出小地图');
  });
  it('图坏了也退回文字态', async () => {
    const w = mount(ZoneMap, { props: { mapFile: 'img/art/maps/9999.webp', mapId: 9999, alt: 'x' } });
    await w.find('img').trigger('error');
    expect(w.find('.zmap.none').exists()).toBe(true);
  });
});

describe('ZoneCard', () => {
  const z = { nameCn: '泽风岛', levelRange: [3, 12], faction: '争夺地带', rareCount: 8, bookCount: 0, isNew: true, flight: 'no-route', mapFile: '', mapId: 2521 };
  const pin = (n, kind) => ({
    key: 'k' + n, kind: kind || 'rare', pin: true, name: '怪' + n, en: '', x: 40 + n, y: 50 + n,
    mapFile: 'img/art/maps/2521.webp', mapId: 2521, tag: '稀有', isNew: false, level: '', coord: '', drops: [], rows: []
  });
  it('可点的是上面那行区域信息，并带上区域名钩子（整卡不是按钮：点位自己是按钮）', async () => {
    const w = mount(ZoneCard, { props: { z, seal: '新' } });
    expect(w.classes()).toContain('lk');
    expect(w.attributes('data-zone')).toBe('泽风岛');
    await w.find('.zhead').trigger('click');
    expect(w.emitted('open')[0]).toEqual(['泽风岛']);
    expect(w.text()).toContain('8 个稀有');
    // 「没有飞行路线」回答的是玩家会问的事（这块地方能不能飞），与旧站 zoneCard 同一句
    expect(w.text()).toContain('没有飞行路线');
  });
  it('卡里就是一套完整点位图：左图右列表，列表行数等于这一区的条目数', () => {
    const w = mount(ZoneCard, { props: { z, items: [pin(1), pin(2, 'book')] } });
    const dots = w.findAll('.zcard .zdot');
    expect(dots.length).toBe(2);
    // 2026-10-19 站主："一行 2 个，地图太小了。也是左右布局，左边是地图，右边是点位列表"
    // → 紧凑版（小图不带列表）整个撤掉，区域卡与稀有精英那一屏用同一版式
    expect(w.find('.zband').exists()).toBe(true);
    expect(w.findAll('.zcard .zband > .zlist > li > .zrow').length).toBe(2);
    dots.forEach((d) => expect(d.element.closest('.zhead')).toBeNull());
  });
  it('这一版没有数据的区域不可点，也不发 open，卡上不留占位句', async () => {
    const w = mount(ZoneCard, { props: { z: Object.assign({}, z, { rareCount: 0, bookCount: 0 }) } });
    expect(w.classes()).not.toContain('lk');
    await w.find('.zhead').trigger('click');
    expect(w.emitted('open')).toBeFalsy();
    // 旧站那一格是空 span，不写"这一版还没有数据"这种讲我们自己的话
    expect(w.find('.zcnt').text()).toBe('');
  });
});

describe('SourceList', () => {
  // 逐条来源不上内容页（2026-10-12 用户决定）：数据层照旧带 provenance，出处在溯源页集中说
  it('内容页不渲染来源块，也不留空壳', () => {
    const full = mount(SourceList, { props: { list: [{
      type: 'datamine_cn', url: 'https://wowforever.wclbox.com/xiyou', note: '客户端解包',
      checkedAt: '2026-10-09', quote: '咆鼻' }] } });
    expect(full.find('.src').exists()).toBe(false);
    expect(full.text()).toBe('');
    expect(mount(SourceList, { props: { list: [] } }).text()).toBe('');
  });
});

describe('HlText', () => {
  it('命中处用 <mark>，其余是纯文本', () => {
    const w = mount(HlText, { props: { text: '强化英勇打击', q: '英勇' } });
    expect(w.html()).toContain('<mark>英勇</mark>');
    expect(w.findAll('mark').length).toBe(1);
  });
});
