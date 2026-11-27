<template>
  <canvas ref="cv" class="forge-embers" :class="{ 'forge-embers-full': fullscreen }" aria-hidden="true"></canvas>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps({
  count: { type: Number, default: 110 },
  fullscreen: { type: Boolean, default: false }
});

const cv = ref(null);
let rafId = 0;
let ro = null;
let onWinResize = null;

function fxDisabled() {
  return typeof document !== 'undefined'
    && document.documentElement.classList.contains('forge-fx-off');
}

onMounted(() => {
  const canvas = cv.value;
  if (!canvas) return;
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

  const areaTarget = props.fullscreen ? Math.round((w * h) / 12000) : props.count;
  const total = Math.max(88, Math.min(150, Math.max(props.count, areaTarget)));

  const makeSpark = (randomY) => {
    const tier = Math.random();
    const bright = tier > 0.68;
    const mid = tier > 0.28 && tier <= 0.68;
    return {
      x: Math.random() * w,
      y: randomY ? Math.random() * h : h + 10 + Math.random() * 44,
      r: bright ? (2.4 + Math.random() * 1.7) : mid ? (1.6 + Math.random() * 1.2) : (1.1 + Math.random() * 0.9),
      vx: (Math.random() - 0.30) * (bright ? 0.72 : 0.46),
      vy: -(bright ? (0.70 + Math.random() * 1.25) : mid ? (0.45 + Math.random() * 0.85) : (0.28 + Math.random() * 0.58)),
      a: bright ? (0.78 + Math.random() * 0.22) : mid ? (0.56 + Math.random() * 0.32) : (0.38 + Math.random() * 0.32),
      bright,
      phase: Math.random() * Math.PI * 2,
      hue: bright ? (34 + Math.random() * 14) : (20 + Math.random() * 24)
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
    if (document.hidden || fxDisabled()) {
      ctx.clearRect(0, 0, w, h);
      return;
    }
    frame += 0.034;
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < sparks.length; i++) {
      const s = sparks[i];
      const sway = Math.sin(s.y * 0.013 + s.phase) * 0.42;
      const dx = s.vx + sway;
      s.x += dx;
      s.y += s.vy;
      if (s.y < -20) {
        sparks[i] = makeSpark(false);
        continue;
      }
      if (s.x > w + 20) s.x = -16;
      if (s.x < -20) s.x = w + 16;
      const flicker = 0.74 + 0.26 * Math.sin(frame * 2.8 + s.phase);
      const alpha = Math.min(1, s.a * flicker);

      if (s.bright) {
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(s.x - dx * 5.2, s.y - s.vy * 5.2);
        ctx.strokeStyle = 'hsla(' + s.hue.toFixed(0) + ',100%,64%,' + (alpha * 0.42).toFixed(2) + ')';
        ctx.lineWidth = s.r * 0.95;
        ctx.lineCap = 'round';
        ctx.stroke();
      }

      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = 'hsla(' + s.hue.toFixed(0) + ',100%,68%,' + alpha.toFixed(2) + ')';
      ctx.shadowBlur = s.bright ? 20 : 12;
      ctx.shadowColor = 'hsla(' + s.hue.toFixed(0) + ',100%,54%,0.98)';
      ctx.fill();

      if (s.bright) {
        ctx.shadowBlur = 0;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * 0.46, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,248,220,' + Math.min(1, alpha + 0.1).toFixed(2) + ')';
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
