<template>
  <div id="top" class="top">
    <div class="in">
      <div class="brand">无限<span>资料站</span></div>
      <nav class="main" aria-label="主导航">
        <template v-for="g in NAV" :key="g.t">
          <!-- 直接入口：已迁走 router-link，未迁走旧站链接 -->
          <router-link v-if="g.file && linkFor(g.file).to" :to="linkFor(g.file).to" :class="{ on: activeFor(g.file) }">{{ g.t }}</router-link>
          <a v-else-if="g.file" :href="linkFor(g.file).href" :class="{ on: activeFor(g.file) }">{{ g.t }}</a>

          <div v-else class="nd" :class="{ open: open === g.t }">
            <button type="button" class="ndb" :class="{ on: groupOn(g) }"
                    aria-haspopup="true" :aria-expanded="open === g.t ? 'true' : 'false'"
                    @click.stop="toggle(g.t)">
              {{ g.t }}<span class="cr" aria-hidden="true">▾</span>
            </button>
            <div class="ndp" role="menu">
              <template v-for="it in g.items" :key="it.file">
                <router-link v-if="linkFor(it.file).to" role="menuitem" :to="linkFor(it.file).to"
                             :class="{ on: activeFor(it.file) }">
                  <b>{{ it.t }}</b><span>{{ it.d }}</span>
                </router-link>
                <a v-else role="menuitem" :href="linkFor(it.file).href" :class="{ on: activeFor(it.file) }">
                  <b>{{ it.t }}</b><span>{{ it.d }}</span>
                </a>
              </template>
            </div>
          </div>
        </template>
      </nav>
      <div class="chip mono" id="lchip">距上线 {{ left.d }} 天 {{ clockText(left) }}</div>
    </div>
  </div>

  <main id="main" class="wrap"><slot /></main>

  <footer id="foot">
    <div class="in" v-if="foot">
      <span>{{ foot.disclaimer }}</span>
      <span>数据口径：<span class="mono">{{ foot.build }}</span>，核对于 <span class="mono">{{ foot.checkedAt }}</span></span>
      <span>词条覆盖率（不含天赋节点）L0 {{ foot.L0 }} / L1 {{ foot.L1 }} / L2 {{ foot.L2 }} / L3 {{ foot.L3 }}，共 {{ foot.pubTotal }} 条</span>
      <span class="dim">{{ stackNote }}</span>
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

const route = useRoute();
const open = ref('');
const { left } = useCountdown();
const foot = ref(null);
const stackNote = '本页跑在新站（Vue 3）上，未迁的页面仍在旧站。';

/* 高亮只看一件事：这个入口指向的旧文件，是否正好对应当前已迁路由 */
function activeFor(file) {
  const l = linkFor(file);
  return !!l.to && l.to === route.path;
}
function groupOn(g) {
  return (g.items || []).some((it) => activeFor(it.file));
}
function toggle(t) { open.value = open.value === t ? '' : t; }
function closeAll() { open.value = ''; }
function onDocClick() { closeAll(); }
function onKey(e) { if (e.key === 'Escape') closeAll(); }

onMounted(() => {
  document.addEventListener('click', onDocClick);
  document.addEventListener('keydown', onKey);
  Promise.all([load('data/meta.json'), load('data/scale.json')])
    .then(([m, s]) => {
      const sc = s.scale;
      foot.value = {
        disclaimer: m.disclaimer, build: m.dataBaseline.build, checkedAt: m.dataBaseline.checkedAt,
        L0: sc.pubCoverage.L0, L1: sc.pubCoverage.L1, L2: sc.pubCoverage.L2, L3: sc.pubCoverage.L3,
        pubTotal: sc.pubTotal
      };
    })
    .catch(() => { /* 页脚拿不到数据不影响正文，与旧站行为一致 */ });
});
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick);
  document.removeEventListener('keydown', onKey);
});
</script>
