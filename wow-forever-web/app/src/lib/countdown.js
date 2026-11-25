/* 倒计时：顶栏 chip 与首页读数共用。
   开服前显示开服倒计时；开服后自动接力 2026-12-10 首批团本首次开放倒计时，避免长期停在 0 天 00:00:00。 */
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { LAUNCH_AT, RAID_UNLOCK_AT, launchLeft, raidUnlockLeft } from './fmt.js';

function snapshot(now) {
  const t = now === undefined ? Date.now() : now;
  if (t < LAUNCH_AT) {
    return { phase: 'launch', left: launchLeft(t), label: '距上线', targetDay: '2026-11-05' };
  }
  if (t < RAID_UNLOCK_AT) {
    const r = raidUnlockLeft(t);
    return { phase: 'raid', left: { d: r.d, h: r.h, m: r.m, s: r.s }, label: '距首批团本', targetDay: '2026-12-10' };
  }
  return { phase: 'open', left: { d: 0, h: 0, m: 0, s: 0 }, label: '首批团本已开放', targetDay: '2026-12-10' };
}

export function useCountdown() {
  const init = snapshot();
  const left = ref(init.left);
  const phase = ref(init.phase);
  const label = ref(init.label);
  const targetDay = ref(init.targetDay);
  let timer = null;
  const tick = () => {
    const s = snapshot();
    left.value = s.left;
    phase.value = s.phase;
    label.value = s.label;
    targetDay.value = s.targetDay;
  };
  const start = () => {
    if (timer) return;
    timer = setInterval(tick, 1000);
  };
  const stop = () => {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  };
  onMounted(start);
  onBeforeUnmount(stop);
  return { left, phase, label, targetDay, start, stop };
}
