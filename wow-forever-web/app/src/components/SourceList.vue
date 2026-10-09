<template>
  <ul v-if="list && list.length" class="src">
    <li v-for="(s, i) in list" :key="i">
      <span class="st" :class="s.type">{{ typeLabel(s.type) }}</span>
      <a v-if="s.url" :href="s.url" target="_blank" rel="noopener">{{ host(s.url) }}</a>
      <span v-else class="dim">（无外部链接：本站自己的说明）</span>
      <span>{{ s.note || '' }}</span>
      <span v-if="s.checkedAt" class="dim">核对于 {{ s.checkedAt }}</span>
      <span v-if="s.quote" class="quote">原文：{{ s.quote }}</span>
    </li>
  </ul>
  <div v-else class="dim small">无来源记录</div>
</template>

<script setup>
/* 逐条来源：来源类型标签 + 可点开的域名路径 + 核对日期 +（有的话）官方原句。
   没有 url 时不能渲染空 <a>——旧站那样被无障碍审计抓到过。 */
import { typeLabel } from '../lib/fmt.js';

const props = defineProps({ list: { type: Array, default: () => [] } });
function host(u) {
  try {
    const x = new URL(u);
    return x.host + x.pathname.slice(0, 34) + (x.pathname.length > 34 ? '…' : '');
  } catch (e) { return u; }
}
</script>
