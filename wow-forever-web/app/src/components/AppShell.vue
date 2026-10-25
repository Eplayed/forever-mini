<template>
  <div id="top" ref="topEl" class="top">
    <!-- 第一行：品牌 + 全站搜索 + 上线读数。稿子里这排是「WOW / RETAIL / CLASSIC」版本页签，
         本站红线不许出现商标词，而且只有一款游戏，所以这一排放自己的东西，只借它的排印语法。 -->
    <div class="hd hd-top">
      <div class="in bar-flex">
        <router-link class="brand" to="/">无限<span>资料站</span></router-link>
        <form class="top-search" role="search" @submit.prevent="goSearch">
          <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true"><path d="M10 2a8 8 0 105.3 14.3l5 5 1.4-1.4-5-5A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z"/></svg>
          <input ref="qBox" type="search" v-model="qText" placeholder="搜全站词条、天赋、副本、配方"
                 aria-label="全站搜索：跳到首页搜索框并带上这个词">
          <button type="submit" class="gsgo">搜索</button>
        </form>
        <div class="chip mono" id="lchip">距上线 {{ left.d }} 天 {{ clockText(left) }}</div>
      </div>
    </div>
    <!-- 第二行：上下两级导航（2026-10-11 用户反馈"平铺看不清"）。
         每个分组是一块：组名在上（带组色短横），它的入口排在下；组间靠竖分隔。
         结构与旧站 shell() 逐字对齐，否则 app-parity 的类名集合会报差异。 -->
    <nav class="main" aria-label="主导航">
      <div class="in">
        <template v-for="(g, i) in NAV" :key="g.t">
          <span v-if="g.file" class="ngrp solo"><span class="ngi">
            <component :is="linkFor(g.file).to ? 'router-link' : 'a'" v-bind="linkFor(g.file)"
                       class="nl" :class="{ on: activeFor(g.file) }" :title="g.d">{{ g.t }}<i v-if="isNavNew(g.t)" class="nb new"
                       title="这一版新开了这一页" aria-label="这一版新开了这一页">新</i></component>
          </span></span>
          <span v-else class="ngrp" :class="['g' + i, { hit: groupOn(g) }]" role="group" :aria-label="g.t">
            <b class="ngt">{{ g.t }}</b>
            <span class="ngi">
              <component v-for="it in g.items" :key="it.file"
                         :is="linkFor(it.file).to ? 'router-link' : 'a'" v-bind="linkFor(it.file)"
                         class="nl" :class="{ on: activeFor(it.file) }" :title="it.d">{{ it.t }}<i v-if="isNavNew(it.t)" class="nb new"
                         title="这一版新开了这一页" aria-label="这一版新开了这一页">新</i></component>
            </span>
          </span>
        </template>
      </div>
    </nav>
  </div>

  <main id="main" class="wrap" ref="mainEl"><slot /></main>

  <footer id="foot">
    <div class="in" v-if="foot">
      <span>{{ foot.disclaimer }}</span>
      <!-- 原来这里挂一句全站版本号，但各板块核到的版本本来就不同（传承 70532、改动 70425、
           世界 70338），一句话必然是假数；逐板块的版本在溯源页那张表里，由规模快照现算。 -->
      <span>{{ foot.note }}</span>
      <span>资料覆盖率（不含天赋）L0 {{ foot.L0 }} / L1 {{ foot.L1 }} / L2 {{ foot.L2 }} / L3 {{ foot.L3 }}，共 {{ foot.pubTotal }} 条</span>
    </div>
  </footer>
  <div id="toast"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { NAV, linkFor } from '../lib/nav.js';
import { clockText } from '../lib/fmt.js';
import { useCountdown } from '../lib/countdown.js';
import { load } from '../lib/data.js';
import { applyRails } from '../lib/rails.js';

const route = useRoute();
const router = useRouter();
const { left } = useCountdown();
const foot = ref(null);
const mainEl = ref(null);
/* 顶栏搜索：这一行的框只负责把词带到首页的搜索框，不重复实现一遍索引匹配 */
const qText = ref('');
const qBox = ref(null);
function goSearch() {
  const v = qText.value.trim();
  router.push(v ? { path: '/', query: { q: v } } : { path: '/' });
}
/* 吸顶头部真实高度写回 --hd-h（与旧站 app.js syncHeaderH 同一件事）：
   锚点让位与吸顶表头都读它，头部高度由内容撑出来，写死常数一定会飘。 */
const topEl = ref(null);
let hdTimer = 0;
function syncHeaderH() {
  const t = topEl.value;
  if (!t) return;
  const h = Math.round(t.getBoundingClientRect().height);
  if (h) document.documentElement.style.setProperty('--hd-h', h + 'px');
}
function onWinResize() {
  clearTimeout(hdTimer);
  hdTimer = setTimeout(syncHeaderH, 120);
}
/* 来源轨：与旧站同一套规则，切路由/局部重渲染后补一次（已定级的卡跳过，重复调用无副作用） */
let railObs = null;
function refreshRails() { applyRails(mainEl.value); }

/* 高亮只看一件事：这个入口指向的旧文件，是否正好对应当前已迁路由 */
function activeFor(file) {
  const l = linkFor(file);
  return !!l.to && l.to === route.path;
}
function groupOn(g) {
  return (g.items || []).some((it) => activeFor(it.file));
}
/* 角标不手写：scale.navNew 由 build-data 从「本站更新」最新一天的标签派生，
   标签对不上导航项名字就不画。只此一种——"近期更新"会一次命中 16 项里的 8 项，满排都是标记等于没有 */
function isNavNew(label) {
  return ((scale.value || {}).navNew || []).indexOf(label) >= 0;
}
const scale = ref(null);

onMounted(() => {
  refreshRails();
  syncHeaderH();
  window.addEventListener('resize', onWinResize);
  if (window.MutationObserver && mainEl.value) {
    let queued = false;
    railObs = new MutationObserver(() => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(() => { queued = false; refreshRails(); });
    });
    railObs.observe(mainEl.value, { childList: true, subtree: true });
  }
  Promise.all([load('data/meta.json'), load('data/scale.json')])
    .then(([m, s]) => {
      const sc = s.scale;
      scale.value = sc;
      foot.value = {
        disclaimer: m.disclaimer, note: (m.dataBaseline || {}).note || '各板块的数据分别核对，版本与核对日期见溯源页',
        L0: sc.pubCoverage.L0, L1: sc.pubCoverage.L1, L2: sc.pubCoverage.L2, L3: sc.pubCoverage.L3,
        pubTotal: sc.pubTotal
      };
    })
    .catch(() => { /* 页脚拿不到数据不影响正文，与旧站行为一致 */ });
});
onBeforeUnmount(() => {
  if (railObs) railObs.disconnect();
  window.removeEventListener('resize', onWinResize);
  clearTimeout(hdTimer);
});
</script>
