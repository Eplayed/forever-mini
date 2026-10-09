<template>
  <span class="liw t" :class="mod ? mod : null">
    <svg viewBox="0 0 40 40" aria-hidden="true">
      <defs>
        <linearGradient :id="st.gradId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" :stop-color="st.color" stop-opacity=".32" />
          <stop offset="1" stop-color="#12151a" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="6" :fill="'url(#' + st.gradId + ')'" :stroke="st.color" stroke-opacity=".5" />
      <text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" :fill="st.color"
            font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ st.letter }}</text>
    </svg>
    <!-- 与旧站 Glyph.tileWrap 一致：这张 img 本来就没有类名，坏了才加 .bad（CSS 用 .liw > img.bad） -->
    <img v-if="iconKey && !broken" :src="src" alt="" loading="lazy" @error="broken = true">
  </span>
</template>

<script setup>
/* 职业方块：职业色渐变 + 中文首字，有本地官方图标时盖在上面。与旧站 Glyph.classTile 同一套配色。 */
import { computed, ref, watch } from 'vue';
import { classStyle, iconUrl } from '../lib/glyph.js';

const props = defineProps({
  classId: { type: String, required: true },
  cn: { type: String, default: '' },
  iconKey: { type: String, default: '' },
  mod: { type: String, default: '' }
});
const broken = ref(false);
const st = computed(() => classStyle(props.classId, props.cn));
const src = computed(() => (props.iconKey ? iconUrl(props.iconKey) : ''));
watch(() => props.iconKey, () => { broken.value = false; });
</script>
