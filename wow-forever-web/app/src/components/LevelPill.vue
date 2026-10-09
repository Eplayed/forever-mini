<template>
  <span class="pill" :class="lv">{{ name }}</span>
</template>

<script setup>
/* L0–L3 徽标：除颜色外必须带文字（红线），未知等级一律落到 L3 而不是猜。 */
import { computed } from 'vue';
import { pillLevel, PILL_NAME } from '../lib/fmt.js';

const props = defineProps({ level: { type: String, default: 'L3' } });
const lv = computed(() => pillLevel(props.level));
const name = computed(() => PILL_NAME[lv.value]);
</script>
