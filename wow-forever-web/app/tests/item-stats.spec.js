import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { armorLineKind, parseStatLine, sumStatLines } from '../src/lib/item-stats.js';

/* 2026-10-19 Q01A：配装页基础护甲漏算。
   下面所有期望值都是照原始属性行人工列出来再加的（加法写在 VERIFY-armor-sum-2026-10-19.md），
   没有用 lib 里的正则算过一遍再抄进来——两边同源于同一个错就是那次事故的成因。 */

describe('基础护甲的三种写法都要计入', () => {
  it('"90 护甲"（#9509 浸油护腿，2026-10-19 之前就是这条被漏掉）', () => {
    expect(parseStatLine('90 护甲')).toEqual({ key: '护甲', value: 90 });
    expect(armorLineKind('90 护甲')).toBe('base');
  });
  it('"90点护甲" 与 "90 点护甲"（点前后都可以有空格）', () => {
    expect(parseStatLine('90点护甲')).toEqual({ key: '护甲', value: 90 });
    expect(parseStatLine('90 点护甲')).toEqual({ key: '护甲', value: 90 });
  });
  it('"护甲值 90"', () => {
    expect(parseStatLine('护甲值 90')).toEqual({ key: '护甲', value: 90 });
  });
  it('同一部位多条基础护甲行按加法累计', () => {
    expect(sumStatLines([['84点护甲'], ['90 护甲'], ['护甲值 74']])).toEqual({ 护甲: 248 });
  });
});

describe('加成的护甲、百分比与效果句不许算进基础护甲', () => {
  const NOT_BASE = [
    ['+90 护甲加成', '加成行不是这件装备的基础护甲'],
    ['+60 护甲', '额外护甲（#1486 树皮夹克那一类）'],
    ['-100 护甲', '罚值（#273646 被咬过一半的靴子）'],
    ['装备：受到的火焰伤害提高10%。', '装备效果句'],
    ['装备： +46 护甲', '装备效果句里的护甲'],
    ['（2）套装：+9 护甲。', '套装效果句'],
    ['使用：护甲值提高50点，持续10秒。', '使用句'],
    ['装备： 使你的宠物的护甲值提高30%。', '百分比句'],
    ['魔暴龙护甲（0/2）', '外观收集计数行，不是属性'],
    ['需要 阿拉索联军 - 崇敬', '需求行'],
    ['护甲值 74 点', '写法不在这三种里 → 宁可不计，交给落档断言报警'],
  ];
  NOT_BASE.forEach(([line, why]) => {
    it(`${line} —— ${why}`, () => {
      expect(parseStatLine(line)).toBe(null);
      expect(armorLineKind(line) === 'base').toBe(false);
    });
  });
  it('护甲加成与罚值不会污染力量那一类（+N 力量仍然要计）', () => {
    expect(parseStatLine('+13 耐力')).toEqual({ key: '耐力', value: 13 });
    expect(parseStatLine('13 耐力')).toBe(null);
  });
});

describe('猎人 PvE 联盟那一套：逐件手算的合计', () => {
  /* 原样抄自 src/data/items-detail.json（2026-10-19，bis.json 的 hunter / alliance 16 格）。
     手算期望：护甲 84+78+25+102+43+56+63+90+74=615
               敏捷 10+8+11+8+14+6+8+9+14+8+7+5+10=118
               耐力 13+5+7+2+6+6+8+7+5+6+3=68
               力量 5 ／ 智力 6+3=9 ／ 精神 4
     修之前页面只有 525（少了 "90 护甲" 这一条）。 */
  const DOLL = [
    ['84点护甲', '+10 敏捷', '+13 耐力'],
    ['唯一', '颈部', '+8 敏捷', '+5 耐力'],
    ['78点护甲', '+11 敏捷', '+5 力量'],
    ['25点护甲', '+8 敏捷', '+7 耐力'],
    ['102点护甲', '+14 敏捷'],
    ['43点护甲', '+6 敏捷', '+2 耐力'],
    ['56点护甲', '+8 敏捷'],
    ['63点护甲', '+9 敏捷', '+6 智力', '+4 精神', '+6 耐力'],
    ['90 护甲', '+14 敏捷', '+6 耐力', '装备：受到的火焰伤害提高10%。'],
    ['拾取后绑定', '唯一', '脚 皮甲', '护甲值 74', '+8 耐力', '+8 敏捷',
     '需要 阿拉索联军 - 崇敬', '装备：略微提高移动速度。'],
    ['手指', '+7 耐力', '+7 敏捷'],
    ['手指', '+5 敏捷', '+5 耐力', '装备： +15 攻击强度'],
    ['装备唯一：战斗护符 （1）', '饰品', '+6 耐力', '需要 阿拉索联军 - 友善',
     '使用： 吸收278到338点物理伤害，持续15秒。 (3分钟冷却时间)'],
    ['装备唯一', '饰品', '装备： 每5秒恢复2点法力值', '使用： 使目标狼人昏迷4秒。 (5分钟冷却时间)'],
    ['39 - 60 伤害', '速度 2.80', '每秒伤害 17.7', '+10 敏捷', '+3 智力',
     '装备：+32 法术强度', '装备：你受到的所有移动限制效果的持续时间缩短10%。'],
    ['35 - 66伤害 速度 2.80', '（每秒伤害18.0）', '+3 耐力', '需要 藏宝海湾 - 尊敬',
     '装备： +9 攻击强度'],
  ];
  it('六项读数等于手算结果', () => {
    expect(sumStatLines(DOLL)).toEqual({
      护甲: 615, 敏捷: 118, 耐力: 68, 力量: 5, 智力: 9, 精神: 4,
    });
  });
});

describe('全库落档：任何带"护甲"的行都必须有一个已知的身份', () => {
  /* 这条盯的是"写法漂移"。2026-10-19 的漏算是静默少加，没人报错；
     以后库里出现第四种基础护甲写法，这里会红并把原句列出来，而不是悄悄不计。 */
  const KNOWN = ['base', 'bonus', 'effect', 'collect'];
  /* 基底文件在 wow-forever-web/src/data/（全线唯一那份）。
     vitest 在 jsdom 环境下 import.meta.url 不是 file:，所以按 cwd 往上找，
     从 app/ 或 wow-forever-web/ 起跑都能命中同一个文件。 */
  const cands = [];
  for (let d = process.cwd(), i = 0; i < 5; i++, d = path.dirname(d)) {
    cands.push(path.join(d, 'src', 'data', 'items-detail.json'));
  }
  const file = cands.filter((p) => fs.existsSync(p))[0];
  if (!file) throw new Error('找不到 src/data/items-detail.json，试过：' + cands.join(' / '));
  const det = JSON.parse(fs.readFileSync(file, 'utf8')).items;
  const shapes = {};
  Object.keys(det).forEach((id) => {
    (det[id].st || []).forEach((l) => {
      const s = String(l).trim();
      if (s.indexOf('护甲') < 0) return;
      const k = armorLineKind(s);
      if (KNOWN.indexOf(k) < 0) {
        const key = k + ' | ' + s.replace(/[0-9]+/g, 'N');
        shapes[key] = (shapes[key] || 0) + 1;
      }
    });
  });
  it('没有落不进档的护甲行', () => {
    const bad = Object.keys(shapes).sort();
    if (bad.length) console.error('未归档的护甲写法：', JSON.stringify(shapes, null, 1));
    expect(bad).toEqual([]);
  });
  it('真的出现新写法时这条闸会响（正向对照）', () => {
    expect(armorLineKind('90 护甲点数')).toBe('other');
    expect(armorLineKind('护甲 90')).toBe('other');
  });
});
