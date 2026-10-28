/* 猎人宠物那一页的纯函数单测（2026-10-28 开这一页时建）。
   正反例都钉：0 不许显示成空、勾了"只看新增"必须真的变少、
   下拉里不许出现选了必然为空的家族、点技能名/家族名这两条路都要真的筛出东西。 */
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { describe, expect, it } from 'vitest';
import { modText, cdText, filterFamilies, filterSkills, familyOptions, skillChips } from '../src/lib/pets.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const pets = JSON.parse(readFileSync(resolve(HERE, '../data/pets.json'), 'utf8'));
const FAMS = pets.families;
const SKILLS = pets.skills;

describe('modText 三项修正的显示', () => {
  it('0 显示成 0，不留空（留空会被读成没数据）', () => {
    expect(modText(0)).toBe('0');
  });
  it('正负都带符号，负号用全角那一档', () => {
    expect(modText(10)).toBe('+10');
    expect(modText(-2)).toBe('−2');
  });
  it('真缺值才写待实测', () => {
    expect(modText(null)).toBe('待实测');
    expect(modText(undefined)).toBe('待实测');
  });
});

describe('cdText 冷却的显示', () => {
  it('0 是"不用冷却"，不是"没写"（0 与缺值是两回事）', () => {
    expect(cdText(0)).toBe('不用冷却');
    expect(cdText(null)).toBe('待实测');
  });
  it('有秒数就带单位', () => {
    expect(cdText(6)).toBe('6 秒');
  });
});

describe('filterFamilies 家族表筛选', () => {
  it('不打字不勾选时是全量', () => {
    expect(filterFamilies(FAMS, {}).length).toBe(FAMS.length);
  });
  it('中文名能搜到', () => {
    const got = filterFamilies(FAMS, { q: '狼' });
    expect(got.length).toBeGreaterThan(0);
    expect(got.some((x) => x.name === '狼')).toBe(true);
  });
  it('英文名大小写不敏感', () => {
    expect(filterFamilies(FAMS, { q: 'fox' }).map((x) => x.nameEn)).toContain('Fox');
    expect(filterFamilies(FAMS, { q: 'FOX' }).length)
      .toBe(filterFamilies(FAMS, { q: 'fox' }).length);
  });
  it('勾「只看无限新增」真的变少，且剩下的每条都是新增', () => {
    const only = filterFamilies(FAMS, { onlyNew: true });
    expect(only.length).toBeLessThan(FAMS.length);
    expect(only.length).toBe(pets.meta.counts.familiesNew);
    expect(only.every((x) => x.isNew)).toBe(true);
  });
});

describe('filterSkills 技能表筛选', () => {
  it('按家族筛：每一条被筛出来的技能都真写着那一族', () => {
    const one = FAMS.find((f) => (f.skills || []).length);
    const got = filterSkills(SKILLS, { fam: one.name });
    expect(got.length).toBeGreaterThan(0);
    expect(got.every((s) => (s.families || []).includes(one.name))).toBe(true);
  });
  it('搜一个不存在的词，两张表都空——空态由页面负责，这里只保证不剩东西', () => {
    expect(filterSkills(SKILLS, { q: 'zzz-不可能存在' }).length).toBe(0);
    expect(filterFamilies(FAMS, { q: 'zzz-不可能存在' }).length).toBe(0);
  });
  it('新增筛选与家族筛选能叠加', () => {
    const one = SKILLS.find((s) => (s.families || []).length > 1);
    const fam = one.families[0];
    const all = filterSkills(SKILLS, { fam });
    const only = filterSkills(SKILLS, { fam, onlyNew: true });
    expect(only.length).toBeLessThanOrEqual(all.length);
    expect(only.every((s) => s.isNew)).toBe(true);
  });
});

describe('familyOptions 下拉的名单', () => {
  it('只列技能表里真出现过的族，选了不会必然为空', () => {
    const opts = familyOptions(FAMS, SKILLS);
    const used = new Set();
    SKILLS.forEach((s) => (s.families || []).forEach((n) => used.add(n)));
    expect(opts.length).toBe(used.size);
    opts.forEach((n) => {
      expect(used.has(n)).toBe(true);
      expect(FAMS.some((f) => f.name === n)).toBe(true);
    });
  });
  it('技能表清空时下拉也空（不放一堆选了没用的选项）', () => {
    expect(familyOptions(FAMS, [])).toEqual([]);
  });
});

describe('skillChips 家族行上的技能条', () => {
  it('每条都有名字，且数量与数据里的一致', () => {
    FAMS.forEach((f) => {
      const c = skillChips(f);
      expect(c.length).toBe((f.skills || []).length);
      c.forEach((x) => expect(x.name).toBeTruthy());
    });
  });
  it('家族写的技能名都能在技能表里找到（两边不是各说各话）', () => {
    const ids = new Set(SKILLS.map((s) => s.spellId));
    FAMS.forEach((f) => (f.skills || []).forEach((s) => expect(ids.has(s.id)).toBe(true)));
  });
});

describe('这份数据自身的边界', () => {
  it('家族与技能各自按「新增排前面」，页面上那一条不会藏在中间', () => {
    // 两张表分别查：拼在一起查会在"家族末尾→技能开头"那道缝上误报
    [FAMS, SKILLS].forEach((arr) => {
      arr.forEach((x, i) => {
        if (i && arr[i - 1].isNew === false && x.isNew === true) {
          throw new Error('新增的条目落在了非新增后面');
        }
      });
    });
  });
  it('一条技能要么挂到至少一个族，要么写明是哪个族号对不上', () => {
    SKILLS.forEach((s) => {
      const ok = (s.families || []).length > 0 || (s.familyMissingIds || []).length > 0;
      expect(ok).toBe(true);
    });
  });
  it('有 iconKey 的家族，图标文件名都落在 img/icons 那一层（不热链）', () => {
    FAMS.forEach((f) => {
      if (f.iconKey) expect(f.iconKey).toMatch(/^[a-z0-9_]+$/);
    });
  });
});
