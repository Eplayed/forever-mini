<template>
  <span class="liw" :class="{ sm: small }">
    <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">
      <rect width="28" height="28" rx="4" :fill="ph.fill" :stroke="ph.stroke" />
      <text x="14" y="19" text-anchor="middle" font-size="12" :fill="ph.text"
            font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ ph.letter }}</text>
    </svg>
    <img v-if="iconKey && !broken" class="lico" :class="{ bad: broken }" :src="src" alt="" loading="lazy"
         @error="broken = true">
  </span>
</template>

<script setup>
/* 图标格：自绘块垫底 + 本地官方图盖面。图取不到时不渲染 img，
   旧站靠 onerror 改类名（会先闪一次 404），这里等价但不产生失败请求。 */
import { computed, ref, watch } from 'vue';
import { tileStyle, iconUrl } from '../lib/glyph.js';

const props = defineProps({
  iconKey: { type: String, default: '' },
  seed: { type: [String, Number], default: '' },
  cn: { type: String, default: '' },
  small: { type: Boolean, default: false }
});
const broken = ref(false);
const src = computed(() => (props.iconKey ? iconUrl(props.iconKey) : ''));
const ph = computed(() => tileStyle(props.seed || props.cn, props.cn));
watch(() => props.iconKey, () => { broken.value = false; });
</script>
