import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import {
  buildCtx, encode, decode, validate, add, remove, canAdd, clearTree, cascadeBlockers,
  totalSpent, treeSpent, spentByTree, applyChecks, challengeIndex, rewardTrack,
  visibleGrid, linkSegments, SCHEMA
} from '../src/lib/legacy-plan.js';

/* 全部用真数据（app/data/legacy.json）跑，不造替身：这一页最容易出事的就是
   "引擎按想象写、数据其实是另一个形状"。2026-10-23 客户端把树从 4×4 排成 5×5、
   并且给每条挑战标了 special，这两件事都是拿真数据才看得出来的。 */
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, '../../app/data/legacy.json'), 'utf8'));
const ctx = buildCtx(DATA);
const P = (n) => 'legacy-perk-' + n;
/* 三棵树里各挑一组真实存在的格子（名字来自数据，测试只认 id） */
const ENTRY = P('working-overtime');        // 专业·0 门槛·上限 5
const ENTRY2 = P('bountiful-harvest');      // 专业·0 门槛·上限 5
const MID = P('bartering');                 // 专业·5 门槛·上限 2
const DEEP = P('dedicated-study');          // 专业·10 门槛·前置 以物易物·上限 1
const OTHER = P('well-rested');             // 冒险·0 门槛·上限 5

describe('引擎读到的事实与数据一致（不写死）', () => {
  it('上限、门槛取值、专长数都从 meta 与 perks 现取', () => {
    expect(ctx.cap).toBe(DATA.meta.rules.launchSpendingCap);
    expect(ctx.gates).toEqual(DATA.meta.rules.treePointGates.values);
    expect(ctx.perks.length).toBe(DATA.meta.counts.perks);
    expect(ctx.byId[DEEP].treePointsRequired).toBe(10);
    expect(ctx.byId[MID].treePointsRequired).toBe(5);
    expect(ctx.byId[ENTRY].treePointsRequired).toBe(0);
  });
  it('常规与特殊是分开数的，特殊那条不并进常规', () => {
    const idx = challengeIndex(ctx);
    expect(idx.regular.length).toBe(DATA.meta.counts.challengesRegular);
    expect(idx.special.length).toBe(DATA.meta.counts.challengesSpecial);
    expect(idx.special.map((x) => String(x.id))).toEqual(DATA.meta.counts.specialIds);
  });
});

describe('加点判定：门槛、前置、上限、总额', () => {
  it('0 门槛的入口格直接能点', () => {
    expect(canAdd(ctx, {}, ENTRY).ok).toBe(true);
  });
  it('5 门槛的格子在本树没投满 5 点前点不了', () => {
    const r = canAdd(ctx, {}, MID);
    expect(r.ok).toBe(false);
    expect(r.reason).toContain('投满 5 点');
    expect(canAdd(ctx, { [ENTRY]: 5 }, MID).ok).toBe(true);
  });
  it('10 门槛的格子还要看前置：投满 10 点但没点前置，照样不行', () => {
    const s = { [ENTRY]: 5, [ENTRY2]: 5 };
    expect(treeSpent(ctx, s, 'crafting')).toBe(10);
    const r = canAdd(ctx, s, DEEP);
    expect(r.ok).toBe(false);
    expect(r.reason).toContain(ctx.byId[MID].nameCn);   // 说清要点哪一格，不说"前置不满足"这种术语
    expect(canAdd(ctx, Object.assign({}, s, { [MID]: 1 }), DEEP).ok).toBe(true);
  });
  it('点满层数之后再加要说"已经点满"', () => {
    expect(add(ctx, { [ENTRY]: 5 }, ENTRY).msg).toContain('已经点满 5 层');
  });
  it('总点数到上限就停，且提示是"先退掉别处的点"', () => {
    const s = { [ENTRY]: 5, [ENTRY2]: 5, [MID]: 2, [DEEP]: 1, [OTHER]: 3 };
    expect(totalSpent(s)).toBe(ctx.cap);
    const r = canAdd(ctx, s, P('thrill-of-adventure'));
    expect(r.ok).toBe(false);
    expect(r.reason).toContain(String(ctx.cap));
    expect(r.reason).toContain('退掉');
  });
  it('另一棵树的点数不算进本树门槛（门槛只看本树）', () => {
    expect(treeSpent(ctx, { [P('thrill-of-adventure')]: 5 }, 'crafting')).toBe(0);
    expect(canAdd(ctx, { [P('thrill-of-adventure')]: 5 }, MID).ok).toBe(false);
  });
});

describe('退点：会打断后续就阻止，绝不静默清掉别的点', () => {
  const full = { [ENTRY]: 5, [ENTRY2]: 5, [MID]: 1, [DEEP]: 1 };
  it('退掉前置那一格会让 10 门槛那格悬空 → 阻止，且 state 原样返回', () => {
    const r = remove(ctx, full, MID);
    expect(r.msg).toContain('不能退');
    expect(r.state).toBe(full);
    expect(r.msg).toContain(ctx.byId[DEEP].nameCn);
  });
  it('退点数导致本树跌破门槛 → 同样阻止并点名是哪一格要几点', () => {
    const s = { [ENTRY]: 4, [MID]: 1 };
    const r = remove(ctx, s, ENTRY);
    expect(r.msg).toContain('不能退');
    expect(r.msg).toMatch(/不够它要的 5 点/);
    expect(r.msg).toContain(ctx.byId[MID].nameCn);
  });
  it('没人依赖的点可以正常退', () => {
    const r = remove(ctx, { [ENTRY]: 2 }, ENTRY);
    expect(r.msg).toBe('');
    expect(r.state[ENTRY]).toBe(1);
  });
  it('退到 0 的格子从方案里消失，不留 0 点键', () => {
    const r = remove(ctx, { [ENTRY]: 1, [ENTRY2]: 2 }, ENTRY);
    expect(r.msg).toBe('');
    expect(r.state[ENTRY]).toBeUndefined();
    expect(Object.prototype.hasOwnProperty.call(r.state, ENTRY)).toBe(false);
  });
  it('一份本就不成立的方案能被 cascadeBlockers 逐条挑出来', () => {
    const bad = cascadeBlockers(ctx, { [DEEP]: 1 }, null);
    expect(bad.length).toBeGreaterThan(0);
    expect(bad.join()).toContain('前置');
  });
  it('整棵清空是安全的：同树互相依赖的点一起走，不留悬空', () => {
    const next = clearTree(ctx, full, 'crafting');
    expect(spentByTree(ctx, next).crafting).toBe(0);
    expect(cascadeBlockers(ctx, next, full)).toEqual([]);
  });
});

describe('方案码：只装格子层数与版本，回来必须能对上', () => {
  const s = { [ENTRY]: 5, [ENTRY2]: 5, [MID]: 2, [DEEP]: 1 };
  it('编解码往返一致', () => {
    const code = encode(ctx, s);
    expect(code.startsWith('v' + SCHEMA)).toBe(true);
    expect(decode(ctx, code).state).toEqual(s);
    expect(decode(ctx, code).bad).toBe(false);
  });
  it('空方案也编得出来、解得回去', () => {
    expect(encode(ctx, {})).toBe('v' + SCHEMA);
    expect(decode(ctx, 'v' + SCHEMA).state).toEqual({});
  });
  it('方案码里不许有挑战编号或个人勾选记录', () => {
    const withChecks = Object.assign({}, s);
    const code = encode(ctx, withChecks);
    DATA.challenges.forEach((g) => g.items.forEach((x) => {
      expect(code).not.toContain(String(x.id));
    }));
  });
  it('未知格子：报出来、不认，但其余照收', () => {
    const r = decode(ctx, 'v' + SCHEMA + ':' + ENTRY.replace('legacy-perk-', '') + '.2,nope.3');
    expect(r.bad).toBe(true);
    expect(r.errors.join()).toContain('这一版没有的格子');
    expect(r.state[ENTRY]).toBe(2);
  });
  it('超层数：按上限收，并说明按几层收的', () => {
    const r = decode(ctx, 'v' + SCHEMA + ':working-overtime.99');
    expect(r.state[ENTRY]).toBe(5);
    expect(r.errors.join()).toContain('按 5 层收');
  });
  it('版本不对：整串不认，不做"猜着解"', () => {
    const r = decode(ctx, 'v9:' + ENTRY.replace('legacy-perk-', '') + '.2');
    expect(r.bad).toBe(true);
    expect(r.state).toEqual({});
    expect(r.errors.join()).toContain('第 9 版');
  });
  it('垃圾串不炸', () => {
    ['', 'abc', 'v', ':', 'v1:.'.repeat(3)].forEach((x) => {
      expect(() => decode(ctx, x)).not.toThrow();
    });
  });
  it('方案本身不成立（超上限、前置为 0、门槛不够）时 validate 逐条报', () => {
    const bad = { [DEEP]: 1 };
    const v = validate(ctx, bad);
    expect(v.ok).toBe(false);
    expect(v.errors.join()).toContain('前置');
    const over = {};
    over[ENTRY] = 5; over[ENTRY2] = 5; over[MID] = 2; over[DEEP] = 1;
    over[P('well-rested')] = 5; over[P('thrill-of-adventure')] = 5;
    expect(totalSpent(over)).toBeGreaterThan(ctx.cap);
    expect(validate(ctx, over).errors.join()).toContain('上限');
  });
});

describe('挑战勾选：只认数据里真有的编号，常规与特殊分账', () => {
  const idx = challengeIndex(ctx);
  const oneRegular = String(idx.regular[0].id);
  const oneSpecial = String(idx.special[0].id);
  it('勾一条常规给 1 点，勾那条测试参与记录给的是它自己标的点数', () => {
    expect(applyChecks(ctx, [oneRegular]).regularPoints).toBe(1);
    expect(applyChecks(ctx, [oneRegular]).specialPoints).toBe(0);
    const r = applyChecks(ctx, [oneSpecial]);
    expect(r.specialPoints).toBe(idx.special[0].points);
    expect(r.regularPoints).toBe(0);
    expect(r.regularDone).toBe(0);
  });
  it('本机存的旧编号在数据里找不到时：丢掉并回报，不把完成状态错给别的条目', () => {
    const r = applyChecks(ctx, [oneRegular, '99999999']);
    expect(r.kept).toEqual([oneRegular]);
    expect(r.dropped).toEqual(['99999999']);
    expect(r.regularPoints).toBe(1);
  });
  it('全勾完常规时点数等于数据里的常规合计，特殊那条另算', () => {
    const all = idx.items.map((x) => String(x.id));
    const r = applyChecks(ctx, all);
    expect(r.regularPoints).toBe(DATA.meta.counts.challengePointsRegular);
    expect(r.specialPoints).toBe(DATA.meta.counts.challengePointSum - DATA.meta.counts.challengePointsRegular);
  });
  it('坏输入（null、非数组、非数字）不炸', () => {
    [null, undefined, [], ['x'], [null], [1]].forEach((x) => {
      expect(() => applyChecks(ctx, x)).not.toThrow();
    });
  });
});

describe('奖励轨按点数算，不按挑战条数算', () => {
  it('每一档的 reached 与"还差几点"跟着勾选点数走', () => {
    const first = DATA.rewards[0].at;
    const t = rewardTrack(ctx, first - 1);
    expect(t[0].reached).toBe(false);
    expect(t[0].left).toBe(1);
    expect(rewardTrack(ctx, first)[0].reached).toBe(true);
    expect(rewardTrack(ctx, 999).every((x) => x.reached)).toBe(true);
    expect(rewardTrack(ctx, 0).every((x) => x.left === x.at)).toBe(true);
  });
  it('档数与数据一致，门槛从数据读', () => {
    const t = rewardTrack(ctx, 0);
    expect(t.length).toBe(DATA.meta.counts.rewards);
    expect(t.map((x) => x.at)).toEqual(DATA.rewards.map((x) => x.at));
  });
});

describe('5×5 的排布：全空的排与列收掉，编号仍用客户端真实行列', () => {
  const t = ctx.trees[0];
  const g = visibleGrid(t);
  it('收掉的是没有任何内容的排/列，收完比原网格小', () => {
    expect(g.rows.length).toBeLessThan(t.rows);
    expect(g.cols.length).toBeLessThan(t.cols);
    g.rows.forEach((r) => {
      expect(t.slots.some((s) => s.row === r && !s.empty)).toBe(true);
    });
  });
  it('没被收掉的排/列仍保持客户端里的先后顺序（不重排）', () => {
    expect(g.rows.slice().sort((a, b) => a - b)).toEqual(g.rows);
    expect(g.cols.slice().sort((a, b) => a - b)).toEqual(g.cols);
  });
  it('前置连线两端都能落到显示坐标上，一条不丢', () => {
    const seg = linkSegments(t, g);
    expect(seg.length).toBe(t.links.length);
    seg.forEach((x) => {
      expect(typeof x.a.row).toBe('number');
      expect(typeof x.b.col).toBe('number');
    });
  });
  it('三棵树都这样算得出来（不是只有第一棵恰好成立）', () => {
    ctx.trees.forEach((x) => {
      const gg = visibleGrid(x);
      expect(gg.rows.length).toBeGreaterThan(0);
      expect(linkSegments(x, gg).length).toBe(x.links.length);
    });
  });
});
