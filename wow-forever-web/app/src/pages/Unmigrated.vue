<template>
  <div class="card">
    <p class="dim">正在打开这一页…</p>
    <a class="cta" :href="target">点这里打开 →</a>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { MIGRATED } from '../router.js';

/* 认得出的旧文件名（races.html 这种）直接送到它在新站的那一页，认不出的回首页。
   两条都走 router.replace，**留在站内**：以前这里是 window.location.replace(legacyUrl(...))，
   在"旧站同源挂根目录"那种部署法下没问题，2026-10-20 发到 GitHub Pages 的 /<仓库名>/ 之后
   它把人甩到了主机根，服务器回一页 GitHub 的 "Site not found"——点了错地址等于离开本站。
   这一页存在的意义是"别给玩家看空白页"，不是"把玩家送去旧站"。 */
const route = useRoute();
const router = useRouter();
// catch-all 抓到的就是整段路径：#/races.html 时 params.all 已经是 "races.html"，
// 再拼一次 .html 就永远查不到（老代码正是这么写的，所以这条分支从来没生效过）。
const raw = String(route.params.all || '');
const want = /\.html$/i.test(raw) ? raw : raw + '.html';
const to = MIGRATED[want] || '/';
const target = computed(() => '#' + to);

onMounted(() => { router.replace(to); });
</script>
