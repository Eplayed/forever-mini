<template>
  <!-- 与旧站首页那颗搜索框同一件（.gsearch.hs）：稿子里框里带一颗实心"立即搜索"，
       有结果就进第一条，没结果就只是把结果展开。 -->
  <div class="gsearch hs" role="search">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></svg>
    <input id="gs" ref="box" type="search" autocomplete="off" aria-controls="gres"
           :aria-expanded="open ? 'true' : 'false'"
           aria-label="全站搜索：天赋、法术、成就、改动、术语、副本、区域、配方、种族"
           :placeholder="'搜天赋、法术、成就、副本、区域、配方（共 ' + total + ' 条）'"
           v-model="q" @input="onType" @keydown="onKey">
    <button type="button" class="cta cta-gold" id="ggo" @click="go">立即搜索</button>
    <p class="gsex">
      <button v-for="x in SAMPLES" :key="x[0]" type="button" class="gsx"
              :title="x[1]" @click="pick(x[0])">{{ x[0] }}</button>
    </p>
    <!-- 结果层从 :hidden 改成 v-show + <Transition name="pop">：hidden 属性是硬开硬关，
         过渡挂不上去。这一层是 position:absolute + 内部滚动，不能套展开收起那套 grid，
         所以只淡入并轻抬 4px（规格见 docs/PLAN-网页交互动效-2026-10-29.md）。 -->
    <Transition name="pop">
    <div v-show="open" ref="list" class="gres" id="gres">
      <p v-if="busy" class="gsl">正在读索引…</p>
      <p v-else-if="empty" class="gsl">
        索引里没有叫「{{ q.trim() }}」的条目。本站按官方中文原名收录，别名与英文请进对应页面搜；也不搜攻略说法。
      </p>
      <template v-else>
        <div v-for="g in groups" :key="g.k">
          <div class="gsh">
            <b>{{ g.label }}</b>
            <component :is="g.link.to ? 'router-link' : 'a'" v-bind="g.link">
              {{ g.all > GROUP_SHOWN ? '这一类共 ' + g.all + ' 条，进去看全部 →' : g.all + ' 条 →' }}
            </component>
          </div>
          <component :is="r.link.to ? 'router-link' : 'a'" v-for="(r, i) in g.rows" :key="g.k + i"
                     class="gsr" v-bind="r.link">
            <b><template v-for="(p, j) in hlParts(r.it[1], q)" :key="j"><template v-if="p.hit"><mark>{{ p.t }}</mark></template><template v-else>{{ p.t }}</template></template></b>
            <span class="dim">{{ r.it[2] }}</span>
          </component>
        </div>
        <p v-if="groups.length" class="gsl dim mono">命中 {{ hitTotal }} 条，这里先列 {{ shownCount }} 条</p>
      </template>
    </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { load } from '../lib/data.js';
import { hlParts } from '../lib/fmt.js';
import { GROUP_SHOWN, itemLink, searchGroups, groupLink } from '../lib/search.js';

const props = defineProps({ total: { type: Number, default: 0 }, initial: { type: String, default: '' } });
const router = useRouter();

// 示例词：给不知道搜什么的人一个起点，都是索引里真有的名字
const SAMPLES = [
  ['潜行', '同一个词在改动清单和配方里都有'],
  ['领主大厅', '副本名'],
  ['咆鼻', '稀有精英'],
  ['舒适的睡袋', '世界页的营点']
];

const q = ref(props.initial || '');
const open = ref(false);
const busy = ref(false);
const box = ref(null);
const list = ref(null);
const idx = ref(null);
const kinds = ref({});

function outside(e) {
  if (!open.value) return;
  if (box.value && box.value.contains(e.target)) return;
  if (list.value && list.value.contains(e.target)) return;
  open.value = false;
}
onMounted(() => {
  document.addEventListener('click', outside);
  // 顶栏那颗搜索框跳过来会带 ?q=，这里接住：填进去并立刻出结果，不让人重打一遍
  if (q.value) onType();
});
onBeforeUnmount(() => document.removeEventListener('click', outside));

function ensureIdx() {
  if (idx.value) return Promise.resolve(idx.value);
  busy.value = true;
  return load('data/search.json')
    .then((j) => {
      kinds.value = j.meta.kinds;
      idx.value = j.items;
      return j.items;
    })
    .finally(() => { busy.value = false; });
}

const found = computed(() => {
  if (!q.value.trim() || !idx.value) return { groups: [], total: 0 };
  return searchGroups(idx.value, q.value, kinds.value);
});
const groups = computed(() => found.value.groups.map((g) => ({
  k: g.k,
  label: g.label,
  all: g.all,
  link: groupLink(kinds.value, g, q.value),
  rows: g.show.map((it) => ({ it, link: itemLink(kinds.value, it) }))
})));
const hitTotal = computed(() => found.value.total);
const shownCount = computed(() => groups.value.reduce((a, g) => a + g.rows.length, 0));
const empty = computed(() => !busy.value && !!q.value.trim() && !!idx.value && !groups.value.length);

function onType() {
  open.value = !!q.value.trim();
  if (!open.value) return;
  if (!idx.value) ensureIdx().catch(() => { open.value = false; });
}
function pick(w) {
  q.value = w;
  onType();
  if (box.value) box.value.focus();
}
/* 实心「立即搜索」：与旧站同一件事——有结果就进第一条，没结果就只是把结果展开。
   索引是懒加载的，第一次点要先等它到，否则永远"没有结果"。 */
function go() {
  if (!q.value.trim()) return;
  const jump = () => {
    const g = groups.value[0];
    if (!g || !g.rows.length) return;
    const l = g.rows[0].link;
    if (l.to) router.push(l.to); else window.location.href = l.href;
  };
  if (idx.value) { onType(); jump(); return; }
  onType();
  ensureIdx().then(jump).catch(() => { open.value = false; });
}
function onKey(e) {
  if (e.key === 'Escape') {
    q.value = '';
    open.value = false;
    e.target.blur();
    return;
  }
  if (e.key === 'ArrowDown') {
    const a = list.value && list.value.querySelector('.gsr');
    if (a) { a.focus(); e.preventDefault(); }
    return;
  }
  if (e.key === 'Enter') {
    // 直接点第一条：router-link 与旧站链接都走各自的默认行为，组件不必认识路由器
    const a = list.value && list.value.querySelector('.gsr');
    if (a) { e.preventDefault(); a.click(); }
  }
}
</script>
