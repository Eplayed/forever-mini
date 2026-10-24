import { describe, it, expect, beforeEach } from 'vitest';
import { fnv, tileStyle, classStyle, raceStyle, iconUrl, CLASS_COLOR, firstChar } from '../src/lib/glyph.js';
import { linkFor, hrefOf, NAV } from '../src/lib/nav.js';
import { load, loadedKeys, forget, assetUrl } from '../src/lib/data.js';

describe('自绘占位图形', () => {
  it('同一 seed 永远得到同一色，不同 seed 会分开', () => {
    expect(fnv('咆鼻')).toBe(fnv('咆鼻'));
    expect(fnv('咆鼻')).not.toBe(fnv('夜啸'));
    expect(tileStyle('咆鼻', '咆鼻').hue).toBe(tileStyle('咆鼻', '咆鼻').hue);
  });
  it('首字取一个汉字，缺名给问号', () => {
    expect(tileStyle('x', '德鲁伊').letter).toBe('德');
    expect(firstChar('')).toBe('?');
  });
  it('未知职业回落到琥珀金，不返回 undefined', () => {
    expect(classStyle('paladin', '圣骑士').color).toBe(CLASS_COLOR.paladin);
    expect(classStyle('mystery', '？').color).toBe('#e0a96d');
  });
  it('阵营色：部落偏暖红、联盟偏冷蓝，同阵营内浮动不超过 ±8', () => {
    const h = raceStyle('a', 'horde', '兽人').hue;
    const b = raceStyle('b', 'horde', '亡灵').hue;
    expect(h).toBeGreaterThanOrEqual(0);
    expect(Math.abs(h - 8) <= 8 || h >= 352).toBe(true);
    expect(Math.abs(h - b) <= 16).toBe(true);
    expect(raceStyle('x', 'alliance', '人类').hue).toBeGreaterThan(180);
  });
  it('图标 URL 走本地路径并转义，绝不出现第三方域名', () => {
    const u = iconUrl('inv_misc_book_12');
    expect(u).toContain('img/icons/inv_misc_book_12.jpg');
    expect(u).not.toMatch(/^https?:/);
  });
});

describe('导航链接归属', () => {
  // 2026-10-24 旧站删除：这一站只有一个落点，linkFor 永远产出站内路由，
  // 不再有任何一条分支拼得出 .html 文件式地址（那种地址在托管方要么 404、
  // 要么被 SPA 兜底成"点了没反应"，2026-10-18 就是栽在这里）。
  it('认得的页一律走站内路由', () => {
    expect(linkFor('index.html')).toEqual({ to: '/' });
    expect(linkFor('dungeons.html')).toEqual({ to: '/dungeons' });
    expect(linkFor('talent.html?c=warrior&tree=2&q=%E7%9B%BE%E7%89%8C')).toEqual({
      to: { path: '/talent', query: { c: 'warrior', tree: '2', q: '盾牌' } }
    });
    // 没参数就给纯路径，不硬造一个空 query 对象（router-link 两种都吃，少一层更好读）
    expect(linkFor('dungeons.html')).toEqual({ to: '/dungeons' });
  });
  it('锚点折成 ?to=，由目标页自己滚', () => {
    expect(linkFor('races.html#traits')).toEqual({ to: { path: '/races', query: { to: 'traits' } } });
  });
  it('认不出的文件名交给 catch-all，绝不静默变成 .html 死链', () => {
    const l = linkFor('nope.html');
    expect(typeof l.to).toBe('string');
    expect(l.to).toBe('/nope.html');
    expect(hrefOf('nope.html')).toBe('#/nope.html');
  });
  it('导航结构里每个叶子都有标题与说明，且都落在站内路由上', () => {
    const leaves = NAV.reduce((a, g) => a.concat(g.file ? [g] : g.items), []);
    expect(leaves.length).toBeGreaterThanOrEqual(11);
    leaves.forEach((l) => {
      expect(l.t).toBeTruthy();
      const link = linkFor(l.file);
      expect(link.to).toBeTruthy();
      expect(JSON.stringify(link)).not.toMatch(/\.html/);
      expect(hrefOf(l.file)).toMatch(/^#\//);
    });
  });
});

describe('数据层', () => {
  beforeEach(() => { globalThis.__calls = []; });
  it('同一份 JSON 只请求一次', async () => {
    const real = globalThis.fetch;
    globalThis.fetch = async (u) => {
      globalThis.__calls.push(String(u));
      return { ok: true, json: async () => ({ scale: { zones: 44 } }) };
    };
    forget('data/scale.json');
    const [a, b] = await Promise.all([load('data/scale.json'), load('data/scale.json')]);
    expect(a).toBe(b);
    expect(globalThis.__calls.length).toBe(1);
    globalThis.fetch = real;
  });
  it('失败不缓存，重试会真的再打一次', async () => {
    const real = globalThis.fetch;
    let n = 0;
    globalThis.fetch = async () => { n += 1; if (n === 1) return { ok: false, status: 404 }; return { ok: true, json: async () => ({ ok: 1 }) }; };
    forget('data/whatever.json');
    await expect(load('data/whatever.json')).rejects.toThrow('404');
    const v = await load('data/whatever.json');
    expect(v.ok).toBe(1);
    expect(n).toBe(2);
    globalThis.fetch = real;
  });
  it('assetUrl 带 BASE_URL，挂子路径也不会指错', () => {
    expect(assetUrl('/data/world.json')).toBe(assetUrl('data/world.json'));
    expect(assetUrl('img/art/maps/1412.webp')).toContain('img/art/maps/1412.webp');
  });
  it('loadedKeys 能报出读过哪几份数据（对拍与排查用）', async () => {
    const real = globalThis.fetch;
    globalThis.fetch = async () => ({ ok: true, json: async () => ({}) });
    forget('data/meta.json');
    await load('data/meta.json');
    expect(loadedKeys()).toContain('meta.json');
    globalThis.fetch = real;
  });
});
