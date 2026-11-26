<template>
  <canvas ref="cv" class="forge-embers" :class="{ 'forge-embers-full': fullscreen }" aria-hidden="true"></canvas>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps({
  count: { type: Number, default: 96 },
  fullscreen: { type: Boolean, default: false }
});

const cv = ref(null);
let rafId = 0;
let ro = null;
let onWinResize = null;

function reduced() {
  return typeof window === 'undefined'
    || !window.matchMedia
    || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

onMounted(() => {
  const canvas = cv.value;
  if (!canvas || reduced()) return;
  let ctx = null;
  try {
    ctx = canvas.getContext('2d');
  } catch (_) {
    return;
  }
  if (!ctx) return;

  let w = 0;
  let h = 0;
  const resize = () => {
    if (props.fullscreen) {
      w = Math.max(1, Math.round(window.innerWidth || 1440));
      h = Math.max(1, Math.round(window.innerHeight || 900));
    } else {
      const rect = canvas.getBoundingClientRect();
      w = Math.max(1, Math.round(rect.width || canvas.offsetWidth || 1100));
      h = Math.max(1, Math.round(rect.height || canvas.offsetHeight || 460));
    }
    canvas.width = w;
    canvas.height = h;
  };
  resize();

  const areaTarget = props.fullscreen ? Math.round((w * h) / 14500) : props.count;
  const total = Math.max(72, Math.min(130, Math.max(props.count, areaTarget)));

  const makeSpark = (randomY) => {
    const tier = Math.random();
    const bright = tier > 0.72;
    const mid = tier > 0.32 && tier <= 0.72;
    return {
      x: Math.random() * w,
      y: randomY ? Math.random() * h : h + 8 + Math.random() * 40,
      r: bright ? (2.1 + Math.random() * 1.5) : mid ? (1.4 + Math.random() * 1.1) : (1.0 + Math.random() * 0.8),
      vx: (Math.random() - 0.32) * (bright ? 0.65 : 0.42),
      vy: -(bright ? (0.65 + Math.random() * 1.15) : mid ? (0.42 + Math.random() * 0.8) : (0.25 + Math.random() * 0.55)),
      a: bright ? (0.72 + Math.random() * 0.26) : mid ? (0.50 + Math.random() * 0.34) : (0.34 + Math.random() * 0.32),
      bright,
      phase: Math.random() * Math.PI * 2,
      hue: bright ? (34 + Math.random() * 14) : (22 + Math.random() * 22)
    };
  };

  const sparks = Array.from({ length: total }, () => makeSpark(true));

  if (props.fullscreen) {
    onWinResize = resize;
    window.addEventListener('resize', onWinResize, { passive: true });
  } else if (typeof window.ResizeObserver === 'function') {
    ro = new window.ResizeObserver(resize);
    ro.observe(canvas);
  }

  let frame = 0;
  const draw = () => {
    rafId = window.requestAnimationFrame(draw);
    if (document.hidden) return;
    frame += 0.032;
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < sparks.length; i++) {
      const s = sparks[i];
      const sway = Math.sin(s.y * 0.014 + s.phase) * 0.38;
      const dx = s.vx + sway;
      s.x += dx;
      s.y += s.vy;
      if (s.y < -18) {
        sparks[i] = makeSpark(false);
        continue;
      }
      if (s.x > w + 18) s.x = -14;
      if (s.x < -18) s.x = w + 14;
      const flicker = 0.72 + 0.28 * Math.sin(frame * 2.6 + s.phase);
      const alpha = Math.min(1, s.a * flicker);

      // 柔和余烬尾迹
      if (s.bright) {
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(s.x - dx * 4.5, s.y - s.vy * 4.5);
        ctx.strokeStyle = 'hsla(' + s.hue.toFixed(0) + ',98%,62%,' + (alpha * 0.36).toFixed(2) + ')';
        ctx.lineWidth = s.r * 0.9;
        ctx.lineCap = 'round';
        ctx.stroke();
      }

      // 火星发光外晕
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = 'hsla(' + s.hue.toFixed(0) + ',98%,66%,' + alpha.toFixed(2) + ')';
      ctx.shadowBlur = s.bright ? 18 : 11;
      ctx.shadowColor = 'hsla(' + s.hue.toFixed(0) + ',100%,54%,0.95)';
      ctx.fill();

      // 熔金高亮点核心
      if (s.bright) {
        ctx.shadowBlur = 0;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,246,214,' + Math.min(1, alpha + 0.1).toFixed(2) + ')';
        ctx.fill();
      }
    }
  };
  rafId = window.requestAnimationFrame(draw);
});

onBeforeUnmount(() => {
  if (rafId) window.cancelAnimationFrame(rafId);
  if (ro) ro.disconnect();
  if (onWinResize) window.removeEventListener('resize', onWinResize);
});
</script>
