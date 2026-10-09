import { describe, it, expect } from 'vitest';
import { scoreName, searchRun, searchGroups, itemLink, groupLink, queryString, KIND_ORDER, GROUP_SHOWN } from '../src/lib/search.js';

// 假索引按 src/data/search.json 的字段顺序：[类型, 名称, 归属, 附加参数, 分级]
const KINDS = {
  cls: ['职业', 'talent.html', ''],
  tal: ['天赋', 'talent.html', 'q'],
  rare: ['稀有精英', 'world.html', 'q'],
  dun: ['副本', 'dungeons.html', ''],
  rec: ['配方', 'professions.html', 'q'],
  chg: ['客户端改动', 'updates.html', 'q']
};
const IDX = [
  ['tal', '预知', '战士 · 防护', 'c=warrior', 'L1'],
  ['tal', '预知', '萨满祭司 · 增强', 'c=shaman', 'L2'],
  ['chg', '预知', '战士 · 改动', 'c=warrior', 'L0'],
  ['rare', '咆鼻', '莫高雷', 't=rares', 'L0'],
  ['rec', '潜行者52型', '工程学 · 无限新增', 'p=engineering', 'L0'],
  ['rec', '潜行者的皮带', '制皮 · 无限新增', 'p=leatherworking', 'L0'],
  ['dun', '领主大厅', '无限新增 · 13-18', 'd=hall-of-thanes', 'L0'],
  ['cls', '潜行者', '53 个天赋节点', 'c=rogue', 'L3']
];

describe('搜索打分与排序', () => {
  it('完全同名排最前，其次前缀，再次包含', () => {
    expect(scoreName('潜行', '潜行')).toBe(0);
    expect(scoreName('潜行者的皮带', '潜行')).toBe(1);
    expect(scoreName('工程潜行器', '潜行')).toBe(2);
    expect(scoreName('别的', '潜行')).toBe(-1);
  });
  it('空词不返回任何结果，避免把整份索引当命中列出来', () => {
    expect(searchRun(IDX, '')).toEqual([]);
    expect(searchRun(IDX, '   ')).toEqual([]);
    expect(searchRun(null, '潜行')).toEqual([]);
  });
  it('命中按「同名 → 板块顺序 → 名字长度」排，同名的两条天赋谁先谁后固定', () => {
    const hits = searchRun(IDX, '预知');
    expect(hits.map((h) => h[2])).toEqual(['战士 · 防护', '萨满祭司 · 增强', '战士 · 改动']);
    expect(hits.every((h) => KIND_ORDER.indexOf(h[0]) >= 0)).toBe(true);
  });
});

describe('结果分组', () => {
  it('同板块合到一组，组内最多列 5 条，组头给这一类的总条数', () => {
    const many = [];
    for (let i = 0; i < 8; i++) many.push(['rec', '药水' + i, '炼金术', '', 'L0']);
    const r = searchGroups(many.concat(IDX), '药水', KINDS);
    expect(r.groups.length).toBe(1);
    expect(r.groups[0].all).toBe(8);
    expect(r.groups[0].show.length).toBe(GROUP_SHOWN);
    expect(r.total).toBe(8);
  });
  it('板块顺序由 KIND_ORDER 决定：职业在天赋前，配方在营点前', () => {
    const g = searchGroups(IDX, '潜行', KINDS).groups.map((x) => x.k);
    expect(g).toEqual(['cls', 'rec']);
  });
});

describe('跳转目标', () => {
  it('附加参数在前、关键词在后，中文词按 URL 编码', () => {
    expect(queryString('t=rares', 'q', '咆鼻')).toBe('?t=rares&q=%E5%92%86%E9%BC%BB');
    // talent.html 还没迁到新站，所以这里必须是完整的旧站文件链接
    expect(itemLink(KINDS, ['tal', '预知', '战士 · 防护', 'c=warrior', 'L1']).href)
      .toContain('talent.html?c=warrior&q=%E9%A2%84%E7%9F%A5');
  });
  it('没有关键词的板块（副本用 d=）只带附加参数，不留空问号', () => {
    const l = itemLink(KINDS, ['dun', '领主大厅', '无限新增', 'd=hall-of-thanes', 'L0']);
    expect(l.href).toContain('dungeons.html?d=hall-of-thanes');
    expect(l.href.indexOf('?d=hall-of-thanes?')).toBe(-1);
  });
  it('已迁的页走路由并带 query，没迁的链回旧站文件', () => {
    expect(itemLink(KINDS, ['rare', '咆鼻', '莫高雷', 't=rares', 'L0']).to).toBe('/world');
    expect(itemLink(KINDS, ['rare', '咆鼻', '莫高雷', 't=rares', 'L0']).query).toEqual({ t: 'rares', q: '咆鼻' });
    expect(itemLink(KINDS, ['tal', '预知', '战士 · 防护', 'c=warrior', 'L1']).href)
      .toContain('talent.html?c=warrior&q=%E9%A2%84%E7%9F%A5');
  });
  it('组头那条"进去看全部"同样按板块生成，不认识的类型不会炸', () => {
    expect(groupLink(KINDS, { page: 'talent.html', param: 'q' }, '潜行').href).toContain('talent.html?q=%E6%BD%9C%E8%A1%8C');
    expect(itemLink({}, ['???', 'x', '', '', 'L3']).href).toContain('index.html');
  });
});
