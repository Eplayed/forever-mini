<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <!-- 主卡卡片头：时间表不在旧站 PAGE_HEAD_SEC 表里，走 cdhead 的 noart 形态（标题左侧蓝线，不放图）。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">上线与 Beta 时间表</h1></div>
      <div class="stats">
        <div class="stat"><b>{{ items.length }}</b>个时间点</div>
        <div class="stat"><b>{{ counts.done }}</b>已过</div>
        <div class="stat"><b>{{ counts.upcoming }}</b>待来</div>
        <div class="stat"><b>{{ items.length - counts.done - counts.upcoming }}</b>日期未定</div>
      </div>
    </div>

    <!-- 2026-10-12 站主决定：这一页只留时间点与两个官方日期本身，
         讲来源标注与分级口径的那两句已删，出处集中在溯源页（provenance.html）。 -->
    <div v-if="tz" class="card">
      <h2>上线日期为什么有两个说法</h2>
      <p class="dim">{{ tz.cn }}<br>{{ tz.en }}</p>
      <p>{{ tz.ours }}</p>
    </div>

    <div class="tl">
      <template v-for="r in view" :key="r.now ? '__now' : r.id">
        <div v-if="r.now" class="tlrow tl-now"><i class="tldot now" aria-hidden="true"></i>
          <div class="tl-body"><b class="mono">今天</b></div></div>
        <div v-else class="tlrow" :class="'tl-' + r.state">
          <i class="tldot" aria-hidden="true"></i>
          <div class="tl-date"><b class="mono">{{ r.date }}</b><span class="dim">{{ r.days }}</span></div>
          <div class="tl-body">
            <div class="tl-h">{{ r.title }} <span class="tag">{{ r.state }}</span></div>
            <p class="dim">{{ r.what }}</p>
          </div>
        </div>
      </template>
    </div>
  </template>
</template>

<script setup>
/* 上线时间表 · 与旧站 app.js timeline()（行 1222-1256）逐块对齐。
   顺序与旧站一致：不排序，按 timeline.json 的数组顺序渲染（旧站这一页没有 sort，
   fmt.js 的 byDate 是首页「最近动态」与动态页用的，这里用会倒序、反而不等价）；
   「已过/待来」分档计数用 lib/fmt.js 的 tlCounts，与旧站同一算法。 */
import { computed, onMounted, ref } from 'vue';
import { load } from '../lib/data.js';
import { tlCounts } from '../lib/fmt.js';

const d = ref(null);
const err = ref('');
const now = ref(0);

function boot() {
  err.value = '';
  load('data/timeline.json')
    .then((json) => { now.value = Date.now(); d.value = json; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

const items = computed(() => (d.value && d.value.items) || []);
const tz = computed(() => ((d.value && d.value.meta) || {}).timezoneConflict || null);
const counts = computed(() => tlCounts(items.value, now.value));

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const rows = computed(() => items.value.map((x) => {
  const t = DATE_RE.test(x.date || '') ? new Date(x.date + 'T00:00:00+08:00').getTime() : null;
  const state = t === null ? '未定' : (t <= now.value ? '已过' : '待来');
  const days = t === null ? '' : (t <= now.value
    ? '已过 ' + Math.round((now.value - t) / 86400000) + ' 天'
    : '还有 ' + Math.ceil((t - now.value) / 86400000) + ' 天');
  return { id: x.id, date: x.date, title: x.title, what: x.what, state: state, days: days };
}));
/* 轴的意义是"现在站在哪"：在第一个待来之前钉一格今天，没有待来就钉在末尾（与旧站同一规则） */
const view = computed(() => {
  const arr = rows.value.slice();
  const at = arr.findIndex((r) => r.state === '待来');
  const nowRow = { now: true };
  if (at >= 0) arr.splice(at, 0, nowRow); else arr.push(nowRow);
  return arr;
});
</script>
