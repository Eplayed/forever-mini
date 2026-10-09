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
  it('除颜色外一定带文字（红线：不靠颜色承载信息）', () => {
    const w = mount(LevelPill, { props: { level: 'L2' } });
    expect(w.classes()).toContain('pill');
    expect(w.classes()).toContain('L2');
    expect(w.text()).toBe('待实测');
  });
  it('脏等级落到 L3 而不是留空', () => {
    expect(mount(LevelPill, { props: { level: 'x' } }).text()).toBe('缺数据');
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
  it('四段宽度加起来等于 100%', () => {
    const w = mount(CovBar, { props: { cov: { L0: 366, L1: 114, L2: 360, L3: 2, total: 842 } } });
    const sum = w.findAll('i').reduce((a, i) => a + parseFloat(i.attributes('style').match(/([\d.]+)%/)[1]), 0);
    expect(Math.round(sum)).toBe(100);
  });
  it('缺 total 时按四段之和兜底（旧站这里就是没兜住才把条画爆的）', () => {
    const w = mount(CovBar, { props: { cov: { L0: 50, L1: 0, L2: 50, L3: 0 } } });
    expect(w.findAll('i').length).toBe(2);
    expect(w.findAll('i')[0].attributes('title')).toContain('已官方核实 50 条');
  });
  it('零计数不渲染段，避免 0 宽的假分段', () => {
    const w = mount(CovBar, { props: { cov: { L0: 10, L1: 0, L2: 0, L3: 0, total: 10 } } });
    expect(w.findAll('i').length).toBe(1);
  });
});

describe('ZoneMap', () => {
  it('有本地小地图时按数据百分比摆标记点', () => {
    const w = mount(ZoneMap, {
      props: { mapFile: 'img/art/maps/1412.webp', mapId: 1412, mark: { x: 32.7, y: 64.5 }, alt: '莫高雷' }
    });
    expect(w.find('img').attributes('alt')).toBe('莫高雷的区域小地图');
    expect(w.find('.zmark').attributes('style')).toContain('left: 32.7%');
    expect(w.text()).toContain('本地转存');
  });
  it('上游没切图时给 mapId 与说明，不放假图', () => {
    const w = mount(ZoneMap, { props: { mapFile: '', mapId: 2548, alt: '河林' } });
    expect(w.find('img').exists()).toBe(false);
    expect(w.classes()).toContain('none');
    expect(w.text()).toContain('mapId 2548');
  });
  it('图坏了也退回文字态', async () => {
    const w = mount(ZoneMap, { props: { mapFile: 'img/art/maps/9999.webp', mapId: 9999, alt: 'x' } });
    await w.find('img').trigger('error');
    expect(w.find('.zmap.none').exists()).toBe(true);
  });
});

describe('ZoneCard', () => {
  const z = { nameCn: '泽风岛', levelRange: [3, 12], faction: '争夺地带', rareCount: 8, bookCount: 0, isNew: true, flight: 'no-route', mapFile: '', mapId: 2521 };
  it('整卡可点并带上区域名钩子', async () => {
    const w = mount(ZoneCard, { props: { z, seal: '新' } });
    expect(w.classes()).toContain('lk');
    expect(w.attributes('data-zone')).toBe('泽风岛');
    await w.trigger('click');
    expect(w.emitted('open')[0]).toEqual(['泽风岛']);
    expect(w.text()).toContain('8 个稀有');
    expect(w.text()).toContain('客户端里还没有飞行路线');
  });
  it('这轮没采到东西的区域不可点，也不发 open', async () => {
    const w = mount(ZoneCard, { props: { z: Object.assign({}, z, { rareCount: 0, bookCount: 0 }) } });
    expect(w.classes()).not.toContain('lk');
    await w.trigger('click');
    expect(w.emitted('open')).toBeFalsy();
    expect(w.text()).toContain('本轮没采到东西');
  });
});

describe('SourceList', () => {
  it('没有 url 时不能渲染空链接（旧站被无障碍审计抓到过）', () => {
    const w = mount(SourceList, { props: { list: [{ type: 'site-note', note: '本站说明' }] } });
    expect(w.find('a').exists()).toBe(false);
    expect(w.text()).toContain('无外部链接');
  });
  it('有 url 才给可点开的来源，并带上核对日期与原句', () => {
    const w = mount(SourceList, { props: { list: [{
      type: 'datamine_cn', url: 'https://wowforever.wclbox.com/xiyou', note: '客户端解包',
      checkedAt: '2026-10-09', quote: '咆鼻'
    }] } });
    expect(w.find('a').attributes('rel')).toBe('noopener');
    expect(w.find('a').text()).toContain('wclbox.com');
    expect(w.text()).toContain('核对于 2026-10-09');
    expect(w.find('.quote').text()).toContain('原文：咆鼻');
  });
  it('空清单也要说明，不留空白块', () => {
    expect(mount(SourceList, { props: { list: [] } }).text()).toContain('无来源记录');
  });
});

describe('HlText', () => {
  it('命中处用 <mark>，其余是纯文本', () => {
    const w = mount(HlText, { props: { text: '强化英勇打击', q: '英勇' } });
    expect(w.html()).toContain('<mark>英勇</mark>');
    expect(w.findAll('mark').length).toBe(1);
  });
});
