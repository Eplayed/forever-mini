import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { raidUnlockLeft, raidCalendarDays, RAID_UNLOCK_AT } from '../src/lib/fmt.js';

const DATA_ROOT = path.resolve(__dirname, '..', 'data');

describe('12 月 10 日首批团本倒计时与官宣数据档案', () => {
  it('raidUnlockLeft 与 raidCalendarDays 在 2026-11-25 算得 15 天，过 12-10 07:00 归零', () => {
    const nov25 = Date.parse('2026-11-25T16:00:00+08:00');
    expect(raidCalendarDays(nov25, '2026-12-10')).toBe(15);
    const left = raidUnlockLeft(nov25);
    expect(left.d).toBe(14);
    expect(left.ms).toBeGreaterThan(0);

    const dec10Morning = RAID_UNLOCK_AT + 1000;
    expect(raidCalendarDays(dec10Morning, '2026-12-10')).toBe(0);
    expect(raidUnlockLeft(dec10Morning).ms).toBe(0);
  });

  it('raid-launch.json 覆盖三座首发团本（10/20/40 人）且奥妮克希亚双阵营门任务各 11 步', () => {
    const rl = JSON.parse(fs.readFileSync(path.join(DATA_ROOT, 'raid-launch.json'), 'utf8'));
    const dg = JSON.parse(fs.readFileSync(path.join(DATA_ROOT, 'dungeons.json'), 'utf8'));
    const allIds = new Set([].concat(dg.newDungeons, dg.classicDungeons, dg.raids).map((x) => x.id));

    expect(rl.unlockDate).toBe('2026-12-10');
    expect(rl.resetCycle).toBe('每周重置');
    expect(rl.raids.map((r) => [r.id, r.partySize, r.attunementRequired])).toEqual([
      ['barrow-deeps', 10, false],
      ['hyjal-summit', 20, false],
      ['onyxias-lair', 40, true]
    ]);
    expect(rl.onyxiaAttunement.itemName).toBe('龙火护符');
    expect(rl.onyxiaAttunement.alliance.length).toBe(11);
    expect(rl.onyxiaAttunement.horde.length).toBe(11);
    rl.onyxiaAttunement.alliance.concat(rl.onyxiaAttunement.horde).forEach((st) => {
      if (st.dungeonId) expect(allIds.has(st.dungeonId)).toBe(true);
    });
  });
});
