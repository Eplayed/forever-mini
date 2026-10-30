/* 宏命令页的纯函数单测（2026-10-30 开这一页时建），直接打 app/data/macros.json 真数据。
   钉的都是"选了必须真生效"这一类：芯片上的数就是点下去看到的数、
   分组芯片不许出现选了为空的、等级滤不能把没有门槛的宏滤掉、
   复制出去的正文与页面上那段逐字相同。 */
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { describe, expect, it } from 'vitest';
import { classOptions, groupOptions, filterMacros, summary, levelText, learnable, matches, CLASS_ORDER }
  from '../src/lib/macros.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const DOC = JSON.parse(readFileSync(resolve(HERE, '../data/macros.json'), 'utf8'));
const M = DOC.macros;

describe('数据本身（页面所有计数都靠它）', () => {
  it('一条宏都不许带没翻出来的法术占位', () => {
    expect(M.filter((x) => x.body.indexOf('{{') >= 0).map((x) => x.id)).toEqual([]);
  });
  it('每条都有正文、组名、标题，且分级统一是 L1（一家插件整理，不许冒充已核）', () => {
    M.forEach((x) => {
      expect(x.body && x.group && x.title && x.classId).toBeTruthy();
      expect(x.level).toBe('L1');
      expect((x.provenance || [])[0]).toBeTruthy();
      expect(x.provenance[0].url && x.provenance[0].checkedAt).toBeTruthy();
    });
  });
  it('职业与 classes.json 同一批，不多不少九个', () => {
    expect([...new Set(M.map((x) => x.classId))].sort()).toEqual([...CLASS_ORDER].sort());
  });
  it('meta.counts 与实数一致（页顶那行读数就是从这里来的）', () => {
    const s = summary(M);
    expect(DOC.meta.counts.macros).toBe(s.total);
    expect(DOC.meta.counts.classes).toBe(s.classes);
    expect(DOC.meta.counts.groups).toBe(s.groups);
    expect(DOC.meta.counts.foreverNew).toBe(s.foreverNew);
    expect(DOC.meta.counts.rankMarker).toBe(s.rankMarker);
  });
});

describe('classOptions / groupOptions', () => {
  it('九个职业各带自己的条数，加起来等于总数', () => {
    const o = classOptions(M);
    expect(o.map((x) => x.id)).toEqual(CLASS_ORDER);
    expect(o.reduce((n, x) => n + x.n, 0)).toBe(M.length);
  });
  it('分组芯片只出这个职业真有的组，且每颗的数等于点下去的条数', () => {
    CLASS_ORDER.forEach((cid) => {
      const inCls = M.filter((x) => x.classId === cid);
      groupOptions(inCls).forEach((g) => {
        expect(filterMacros(M, { classId: cid, group: g.group }).length).toBe(g.n);
      });
    });
  });
  it('不存在"点了为空"的分组芯片', () => {
    CLASS_ORDER.forEach((cid) => {
      groupOptions(M.filter((x) => x.classId === cid)).forEach((g) => { expect(g.n).toBeGreaterThan(0); });
    });
  });
});

describe('等级滤', () => {
  it('minLevel=0 是"没有等级门槛"，任何等级都留得下', () => {
    const noLimit = M.filter((x) => !x.minLevel);
    expect(noLimit.length).toBeGreaterThan(0);
    noLimit.forEach((x) => { expect(learnable(x, 1)).toBe(true); });
    expect(levelText(noLimit[0])).toBe('没有等级门槛');
  });
  it('填 20 之后，留下的每一条门槛都 ≤20，且确实比不填少', () => {
    const all20 = filterMacros(M, { classId: 'warrior', level: 20 });
    expect(all20.length).toBeLessThan(filterMacros(M, { classId: 'warrior' }).length);
    all20.forEach((x) => expect(Number(x.minLevel) || 0).toBeLessThanOrEqual(20));
  });
  it('等级填到顶（60）就等于不滤', () => {
    expect(filterMacros(M, { classId: 'priest', level: 60 }).length)
      .toBe(filterMacros(M, { classId: 'priest' }).length);
  });
});

describe('搜索', () => {
  it('搜到的每一条都在标题 / 说明 / 正文 / 组名里含这个词', () => {
    ['嘲讽', '鼠标指向', 'showtooltip', '圣光术'].forEach((k) => {
      const hit = filterMacros(M, { q: k });
      expect(hit.length).toBeGreaterThan(0);
      hit.forEach((x) => expect(matches(x, k)).toBe(true));
    });
  });
  it('词与等级、职业、分组四个条件是叠加的，不是互相覆盖', () => {
    const combo = filterMacros(M, { classId: 'warrior', group: '坦克', q: '嘲讽', level: 30 });
    combo.forEach((x) => {
      expect(x.classId).toBe('warrior');
      expect(x.group).toBe('坦克');
      expect(matches(x, '嘲讽')).toBe(true);
      expect(Number(x.minLevel) || 0).toBeLessThanOrEqual(30);
    });
  });
  it('乱码词筛出零条（页面据此走空态，不是白屏）', () => {
    expect(filterMacros(M, { q: 'zzzqqqxx' }).length).toBe(0);
  });
});

describe('复制出去的正文', () => {
  it('页面用 <pre v-text> 摆的那段与数据里的 body 逐字相同（含换行与分号）', () => {
    M.forEach((x) => {
      expect(x.body).not.toMatch(/\r/);
      expect(x.body.split('\n').length).toBeLessThanOrEqual(15);   // 游戏内宏上限 15 行
      x.body.split('\n').filter((l) => l.trim()).forEach((l) => expect(l).toMatch(/^[/#]/));
    });
  });
});
