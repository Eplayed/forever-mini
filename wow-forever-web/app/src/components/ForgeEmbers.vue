<template>
  <canvas ref="cv" class="forge-embers" :class="{ 'forge-embers-full': fullscreen }" aria-hidden="true"></canvas>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps({
  count: { type: Number, default: 54 },
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

  const total = Math.max(10, Math.min(72, props.count));
  const sparks = Array.from({ length: total }, (_, idx) => {
    const bright = idx % 5 === 0;
    return {
      x: Math.random() * w,
      y: Math.random() * h,
      r: bright ? (1.5 + Math.random() * 1.4) : (0.75 + Math.random() * 1.35),
      vx: (Math.random() - 0.32) * (bright ? 0.55 : 0.35),
      vy: -(bright ? (0.55 + Math.random() * 0.95) : (0.24 + Math.random() * 0.62)),
      a: bright ? (0.48 + Math.random() * 0.38) : (0.18 + Math.random() * 0.38),
      phase: Math.random() * Math.PI * 2,
      hue: bright ? (34 + Math.random() * 14) : (24 + Math.random() * 20)
    };
  });

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
    frame += 0.025;
    ctx.clearRect(0, 0, w, h);
    for (let i = 0; i < sparks.length; i++) {
      const s = sparks[i];
      s.x += s.vx + Math.sin(s.y * 0.012 + s.phase) * 0.28;
      s.y += s.vy;
      if (s.y < -12) {
        s.y = h + 12;
        s.x = Math.random() * w;
      }
      if (s.x > w + 12) s.x = -12;
      if (s.x < -12) s.x = w + 12;
      const flicker = 0.78 + 0.22 * Math.sin(frame * 2.1 + s.phase);
      const alpha = s.a * flicker;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = 'hsla(' + s.hue.toFixed(0) + ',96%,66%,' + alpha.toFixed(2) + ')';
      ctx.shadowBlur = s.r * 5.5;
      ctx.shadowColor = 'hsla(' + s.hue.toFixed(0) + ',96%,54%,0.85)';
      ctx.fill();
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
