<template>
  <div id="top" class="top">
    <div class="in">
      <router-link class="brand" to="/">无限<span>资料站</span></router-link>
      <div class="chip mono" id="lchip">距上线 {{ left.d }} 天 {{ clockText(left) }}</div>
    </div>
    <!-- 两级常驻：一级是分组标签（不可点），二级项全部平铺，说明收进 title -->
    <nav class="main" aria-label="主导航">
      <div class="in">
        <template v-for="g in NAV" :key="g.t">
          <component v-if="g.file" :is="linkFor(g.file).to ? 'router-link' : 'a'" v-bind="linkFor(g.file)"
                     class="nl" :class="{ on: activeFor(g.file) }" :title="g.d">{{ g.t }}<i v-if="isNavNew(g.t)" class="nb new"
                       title="这一版新开了这一页" aria-label="这一版新开了这一页">新</i></component>
          <span v-else class="ngrp" :class="{ hit: groupOn(g) }">
            <b class="ngt">{{ g.t }}</b>
            <component v-for="it in g.items" :key="it.file"
                       :is="linkFor(it.file).to ? 'router-link' : 'a'" v-bind="linkFor(it.file)"
                       class="nl" :class="{ on: activeFor(it.file) }" :title="it.d">{{ it.t }}<i v-if="isNavNew(it.t)" class="nb new"
                         title="这一版新开了这一页" aria-label="这一版新开了这一页">新</i></component>
          </span>
        </template>
      </div>
    </nav>
  </div>

  <main id="main" class="wrap" ref="mainEl"><slot /></main>

  <footer id="foot">
    <div class="in" v-if="foot">
      <span>{{ foot.disclaimer }}</span>
      <span>数据来源版本：<span class="mono">{{ foot.build }}</span>，核对于 <span class="mono">{{ foot.checkedAt }}</span></span>
      <span>资料覆盖率（不含天赋）L0 {{ foot.L0 }} / L1 {{ foot.L1 }} / L2 {{ foot.L2 }} / L3 {{ foot.L3 }}，共 {{ foot.pubTotal }} 条</span>
    </div>
  </footer>
  <div id="toast"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { NAV, linkFor } from '../lib/nav.js';
import { clockText } from '../lib/fmt.js';
import { useCountdown } from '../lib/countdown.js';
import { load } from '../lib/data.js';
import { applyRails } from '../lib/rails.js';

const route = useRoute();
const { left } = useCountdown();
const foot = ref(null);
const mainEl = ref(null);
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
        disclaimer: m.disclaimer, build: m.dataBaseline.build, checkedAt: m.dataBaseline.checkedAt,
        L0: sc.pubCoverage.L0, L1: sc.pubCoverage.L1, L2: sc.pubCoverage.L2, L3: sc.pubCoverage.L3,
        pubTotal: sc.pubTotal
      };
    })
    .catch(() => { /* 页脚拿不到数据不影响正文，与旧站行为一致 */ });
});
onBeforeUnmount(() => { if (railObs) railObs.disconnect(); });
</script>
