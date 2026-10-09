<template>
  <div class="cov">
    <i v-for="s in segs" :key="s.k" :class="s.k" :style="{ width: s.w }" :title="s.title"></i>
  </div>
</template>

<script setup>
/* 覆盖率条：四段宽度按真实计数算，计数为 0 的那段不渲染（与旧站 t[k] ? '<i …>' : '' 一致）。
   旧站这里踩过一次坑——宽度除以 t.total，而调用方传的对象没带 total，四段加起来变成 8 倍条宽；
   这里 total 缺失时按四段之和兜底，不当 1 算。
   注意 v-for 与 v-if 不能写在同一个元素上（Vue 3 里 v-if 先算，拿不到循环变量），所以先算 segs。 */
import { computed } from 'vue';
import { PILL_NAME } from '../lib/fmt.js';

const props = defineProps({ cov: { type: Object, required: true } });
const KEYS = ['L0', 'L1', 'L2', 'L3'];

const segs = computed(() => {
  const sum = KEYS.reduce((a, k) => a + (props.cov[k] || 0), 0);
  const total = props.cov.total || sum || 1;
  return KEYS.filter((k) => (props.cov[k] || 0) > 0).map((k) => ({
    k: k,
    w: (props.cov[k] / total * 100).toFixed(2) + '%',
    title: PILL_NAME[k] + ' ' + props.cov[k] + ' 条'
  }));
});
</script>
