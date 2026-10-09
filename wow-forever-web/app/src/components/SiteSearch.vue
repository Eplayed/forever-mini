<template>
  <div class="gsearch" role="search">
    <input id="gs" ref="box" type="search" autocomplete="off" aria-controls="gres"
           :aria-expanded="open ? 'true' : 'false'"
           aria-label="全站搜索：天赋、改动、术语、副本、区域、配方、种族"
           :placeholder="'搜天赋、副本、区域、配方、种族特长（共 ' + total + ' 条）'"
           v-model="q" @input="onType" @keydown="onKey">
    <p class="gsex">
      <button v-for="x in SAMPLES" :key="x[0]" type="button" class="gsx"
              :title="x[1]" @click="pick(x[0])">{{ x[0] }}</button>
      <span class="dim">只搜名称与归属，不搜攻略说法，也不搜别人站的正文。</span>
    </p>
    <div id="gres" ref="list" class="gres" :hidden="!open">
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
            <em v-if="r.it[4] && r.it[4] !== 'L0'" class="lv" :class="r.it[4]">{{ PILL_NAME[r.it[4]] }}</em>
          </component>
        </div>
        <p v-if="groups.length" class="gsl dim mono">命中 {{ hitTotal }} 条，这里先列 {{ shownCount }} 条</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { load } from '../lib/data.js';
import { hlParts, PILL_NAME } from '../lib/fmt.js';
import { GROUP_SHOWN, itemLink, searchGroups, groupLink } from '../lib/search.js';

const props = defineProps({ total: { type: Number, default: 0 } });

// 示例词：给不知道搜什么的人一个起点，都是索引里真有的名字
const SAMPLES = [
  ['潜行', '同一个词在改动清单和配方里都有'],
  ['领主大厅', '副本名'],
  ['咆鼻', '稀有精英'],
  ['舒适的睡袋', '世界页的营点']
];

const q = ref('');
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
onMounted(() => document.addEventListener('click', outside));
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
