<template>
  <template v-for="(p, i) in parts" :key="i"><mark v-if="p.hit">{{ p.t }}</mark><template v-else>{{ p.t }}</template></template>
</template>

<script setup>
/* 搜索高亮：拆片段渲染，不拼 HTML、不用 v-html。
   旧站 D.hl 是把 <mark> 拼进字符串再 innerHTML，等于给每条数据开了个注入面。 */
import { computed } from 'vue';
import { hlParts } from '../lib/fmt.js';

const props = defineProps({ text: { type: [String, Number], default: '' }, q: { type: String, default: '' } });
const parts = computed(() => hlParts(props.text, props.q));
</script>
