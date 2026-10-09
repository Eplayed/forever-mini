import { describe, it, expect } from 'vitest';
import {
  hlParts, levelRangeText, byDate, launchLeft, pillLevel, PILL_NAME, typeLabel, lvStart
} from '../src/lib/fmt.js';

describe('搜索高亮拆片段', () => {
  it('没有关键词时整段不高亮', () => {
    expect(hlParts('强化英勇打击', '')).toEqual([{ t: '强化英勇打击', hit: false }]);
  });
  it('命中处切成片段，大小写不敏感', () => {
    expect(hlParts('Rank 2 强化', 'rank')).toEqual([
      { t: 'Rank', hit: true }, { t: ' 2 强化', hit: false }
    ]);
  });
  it('返回的是片段而不是 HTML 字符串——不给注入留口子', () => {
    const raw = '<img src=x onerror=alert(1)>';
    const out = hlParts(raw, 'img');
    expect(JSON.stringify(out)).not.toContain('<mark>');   // 不产出 HTML 字符串
    expect(out.map((p) => p.t).join('')).toBe(raw);        // 拼回去仍是原文，交给 Vue 转义
  });
});

describe('等级区间读数', () => {
  it('正常区间', () => {
    expect(levelRangeText({ levelRange: [4, 12] })).toBe('4–12 级');
  });
  it('上下限相同只显示一个数', () => {
    expect(levelRangeText({ levelRange: [10, 10] })).toBe('10 级');
  });
  it('[null,null] 不能读成 "null–null"，要落到 levelStatus', () => {
    expect(levelRangeText({ levelRange: [null, null], levelStatus: '客户端暂时没给出区域等级' }))
      .toBe('客户端暂时没给出区域等级');
    expect(lvStart({ levelRange: [null, null] })).toBe(99);
  });
  it('缺字段时给破折号而不是崩', () => {
    expect(levelRangeText({})).toBe('—');
    expect(levelRangeText(undefined)).toBe('—');
  });
});

describe('时间表排序', () => {
  it('真日期倒序，"待定/择期"排最后', () => {
    const rows = [{ date: '择期' }, { date: '2026-09-13' }, { date: '待定' }, { date: '2026-11-05' }]
      .sort(byDate).map((x) => x.date);
    expect(rows).toEqual(['2026-11-05', '2026-09-13', '待定', '择期']);
  });
});

describe('倒计时与分级', () => {
  it('距上线按 +08:00 的 11-05 零点算', () => {
    const a = launchLeft(Date.parse('2026-10-09T00:00:00+08:00'));
    expect(a.d).toBe(27);            // 10-09 零点 → 11-05 零点 = 整 27 天
    expect(a.h).toBe(0);
  });
  it('上线时间过了不出现负数', () => {
    expect(launchLeft(Date.parse('2027-01-01T00:00:00+08:00'))).toEqual({ d: 0, h: 0 });
  });
  it('未知等级一律落到 L3，不猜', () => {
    expect(pillLevel('L0')).toBe('L0');
    expect(pillLevel('L9')).toBe('L3');
    expect(pillLevel(undefined)).toBe('L3');
    expect(PILL_NAME.L2).toBe('待实测');
  });
  it('来源类型有中文名，未知类型原样显示', () => {
    expect(typeLabel('datamine_cn')).toBe('客户端解包');
    expect(typeLabel('weird_type')).toBe('weird_type');
  });
});
