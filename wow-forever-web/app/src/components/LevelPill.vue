<template>
  <!-- 分级徽标不上内容页（2026-10-12 用户决定，见 lib/prov.js）：出处与分级集中在溯源页说 -->
  <span v-if="SHOW_PROV" class="pill" :class="lv">{{ name }}</span>
</template>

<script setup>
/* L0–L3 徽标：除颜色外必须带文字（红线），未知等级一律落到 L3 而不是猜。
   2026-10-12 起只在溯源页渲染；数据层照旧每条带 level，build-data 的卡口没放松。 */
import { computed } from 'vue';
import { pillLevel, PILL_NAME } from '../lib/fmt.js';
import { SHOW_PROV } from '../lib/prov.js';

const props = defineProps({ level: { type: String, default: 'L3' } });
const lv = computed(() => pillLevel(props.level));
const name = computed(() => PILL_NAME[lv.value]);
</script>
