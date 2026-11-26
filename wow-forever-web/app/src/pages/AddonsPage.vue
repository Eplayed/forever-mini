<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="G">
    <section class="card addon-hero">
      <div class="kicker">FREE ADDONS DIRECTORY</div>
      <h1 class="pt">无限服免费插件目录</h1>
      <p class="note">{{ boundaries }}</p>
      <div class="addon-bar">
        <div class="picks" role="group" aria-label="按用途筛选插件">
          <button v-for="c in cats" :key="c" type="button" class="pick"
                  :class="{ on: cat === c }" @click="cat = c">
            <b>{{ c }}</b>
            <span class="mono">{{ countOf(c) }}</span>
          </button>
        </div>
        <input type="search" v-model="q" class="addon-q" placeholder="搜插件名、作者或用途" aria-label="搜插件名、作者或用途">
      </div>
    </section>

    <section v-if="filtered.length" class="addon-grid">
      <article v-for="a in filtered" :key="a.id" class="card addon-card" data-forge-spot>
        <div class="addon-top">
          <span class="addon-cat" :class="{ self: a.category === '站长自研' }">{{ a.category || '实用辅助' }}</span>
          <span class="dim mono">{{ a.checkedAt }}</span>
        </div>
        <h2 class="addon-name">{{ a.name }}</h2>
        <div class="addon-author dim">作者：<b>{{ a.author }}</b></div>
        <p class="addon-use">{{ a.use }}</p>
        <div class="addon-foot">
          <span class="addon-ch">{{ a.channel || '请前往正规免费插件平台获取' }}</span>
          <a v-if="a.url" class="cta" :href="a.url" target="_blank" rel="noopener noreferrer">原帖地址 →</a>
        </div>
      </article>
    </section>
    <div v-else class="card empty">没有匹配的插件条目。</div>
  </template>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { load } from '../lib/data.js';

const G = ref(null);
const err = ref('');
const cat = ref('全部');
const q = ref('');

function boot() {
  err.value = '';
  load('data/guide.json')
    .then((d) => { G.value = d || { meta: {}, addons: [] }; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
onMounted(boot);

const addons = computed(() => (G.value && Array.isArray(G.value.addons) ? G.value.addons : []));
const boundaries = computed(() => ((G.value && G.value.meta && G.value.meta.boundaries)
  || '插件为第三方作者作品，与本站无关，安装与使用风险自负。'));

const cats = computed(() => {
  const out = ['全部'];
  addons.value.forEach((a) => {
    const c = a.category || '实用辅助';
    if (out.indexOf(c) < 0) out.push(c);
  });
  return out;
});

function countOf(c) {
  if (c === '全部') return addons.value.length;
  return addons.value.filter((a) => (a.category || '实用辅助') === c).length;
}

const filtered = computed(() => {
  const kw = q.value.trim().toLowerCase();
  return addons.value.filter((a) => {
    if (cat.value !== '全部' && (a.category || '实用辅助') !== cat.value) return false;
    if (!kw) return true;
    const hay = [a.name, a.author, a.use, a.channel, a.category].join(' ').toLowerCase();
    return hay.indexOf(kw) >= 0;
  });
});
</script>

<style scoped>
.addon-hero {
  display: flex;
  flex-direction: column;
  gap: var(--s3);
}
.addon-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--s3);
}
.addon-q {
  min-width: 220px;
  flex: 0 1 280px;
}
.addon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: var(--s4);
  margin-top: var(--s4);
}
.addon-card {
  display: flex;
  flex-direction: column;
  gap: var(--s2);
  margin: 0;
}
.addon-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
}
.addon-cat {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  color: var(--gold-hi);
  background: var(--gold-glow);
  border: 1px solid var(--gold-line);
}
.addon-cat.self {
  color: var(--ink-on-bright);
  background-color: var(--gold);
  background-image: linear-gradient(135deg, var(--gold-hi), var(--gold));
  border-color: var(--gold-hi);
}
.addon-name {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: 19px;
  color: var(--txt-title);
}
.addon-author {
  font-size: 12.5px;
}
.addon-author b {
  color: var(--txt);
}
.addon-use {
  margin: 4px 0 auto;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--txt-dim);
}
.addon-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s2);
  padding-top: var(--s3);
  margin-top: var(--s2);
  border-top: 1px solid var(--gold-line-soft);
  font-size: 12px;
}
.addon-ch {
  color: var(--gold);
}
</style>
