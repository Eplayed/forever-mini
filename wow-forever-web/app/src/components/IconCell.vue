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
/* 图标格：自绘块垫底 + 本地官方图盖面。
   2026-10-20 W01 更正这条注释（原来写"不产生失败请求"，与实现不符）：
   img 照样会发出去，是请求失败（error）之后才把 img 撤掉、只留自绘块——
   所以它避免的是"页面上挂一个破图"，不是"避免一次 404"。
   已知缺图不再发请求要靠 icon-gaps.json 那份登记，但那只查得到"登记过的"；
   未知失败（新漏抓、文件被删）必须仍然能被发现，所以这里不改成按清单预判。
   回归脚本 site-check 的 404 白名单读的就是那份登记。 */
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
