<template>
  <div class="card">
    <p class="dim">正在打开这一页…</p>
    <a class="cta" :href="target">点这里打开 →</a>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { NAV, legacyUrl } from '../lib/nav.js';

/* 还没迁到新站的地址不摆"迁移中"的告示牌——那是在跟用户解释我们的工程进度，不是他要看的东西。
   认得出的页直接送到有内容的那一份；认不出的回首页。 */
const FILES = NAV.reduce((a, g) => a.concat(g.file ? [g.file] : (g.items || []).map((it) => it.file)), []);

const route = useRoute();
const want = String(route.params.all || '') + '.html';
const target = computed(() => legacyUrl(FILES.indexOf(want) >= 0 ? want : 'index.html'));

onMounted(() => { window.location.replace(target.value); });
</script>
