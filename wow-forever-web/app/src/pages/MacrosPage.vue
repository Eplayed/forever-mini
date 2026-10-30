<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">宏命令</h1></div>
      <!-- 这句口径整条读数据里的 meta.pageNote（第三方整理 / 免费 / 本站未逐条实测），
           页面不另抄一份——抄了就会有"改了源忘了改页面"那一天。 -->
      <p class="note">{{ note }}</p>

      <div class="picks" role="group" aria-label="换一个职业">
        <button v-for="c in classOpts" :key="c.id" type="button" class="pick"
                :class="{ on: c.id === cls }" :data-c="c.id" :aria-pressed="c.id === cls ? 'true' : 'false'"
                @click="pickClass(c.id)"><b>{{ c.name }}</b><span class="dim mono">{{ c.n }}</span></button>
      </div>

      <!-- 用途分组只出这个职业真有的组：放一颗点了必然为空的芯片，比不放更坏。
           再点同一颗回"这一职业全部"。 -->
      <div v-if="groupOpts.length > 1" class="picks mc-groups" role="group" aria-label="按用途筛这一职业的宏">
        <button type="button" class="pick" :class="{ on: !grp }" data-g=""
                :aria-pressed="!grp ? 'true' : 'false'" @click="pickGroup('')">全部 <b class="mono">{{ inClass.length }}</b></button>
        <button v-for="g in groupOpts" :key="g.group" type="button" class="pick"
                :class="{ on: grp === g.group }" :data-g="g.group" :aria-pressed="grp === g.group ? 'true' : 'false'"
                @click="pickGroup(g.group)">{{ g.group }} <b class="mono">{{ g.n }}</b></button>
      </div>

      <div class="field">
        <input type="search" id="mq" placeholder="搜宏名、说明或宏里的法术名" :value="q" @input="onQ"
               aria-label="在宏命令里搜索">
        <label class="mc-lv">我现在的等级
          <input type="number" id="mlv" min="1" max="60" step="1" v-model="level" aria-label="按你的等级滤掉还没学会的宏">
        </label>
        <span class="dim mono" id="mcnt">{{ countText }}</span>
      </div>
    </div>

    <!-- 一条宏一张卡：宏正文用 <pre> 原样摆（换行、分号、[mod:shift] 这些是宏语法不是文案），
         复制出去的字符串与页面上看到的逐字相同——这条由门禁量，不靠眼看。 -->
    <template v-for="sec in sections" :key="sec.group">
      <div class="band mc-band"><b>{{ sec.group }}</b><span class="dim mono">{{ sec.rows.length }} 条</span></div>
      <div class="mcgrid">
        <div v-for="m in sec.rows" :key="m.id" class="mc card">
          <div class="mc-h">
            <b class="mc-t"><HlText :text="m.title" :q="q" /></b>
            <span v-if="m.foreverNew" class="tag">《无限》新技能</span>
            <span v-if="m.rankMarker" class="tag mc-rank">带等级标记</span>
          </div>
          <div class="mc-m">{{ m.className }} · {{ levelText(m) }}</div>
          <p v-if="m.note" class="mc-n">{{ m.note }}</p>
          <pre class="mc-b" :data-m="m.id" v-text="m.body"></pre>
          <button type="button" class="ghost mc-copy" :data-copy="m.id"
                  :aria-label="'复制这条宏：' + m.title">复制宏</button>
        </div>
      </div>
    </template>

    <div v-if="!shown.length" class="card empty">
      这一筛没有匹配的宏。
      <template v-if="q.trim() && otherHits.length">
        换个词，或者去别的职业看：<button v-for="o in otherHits" :key="o.id" type="button"
          class="ghost mc-jump" :data-c="o.id" @click="pickClass(o.id)">{{ o.name }} {{ o.n }} 条</button>
      </template>
      <template v-else>换个词，或把上面那个等级放宽一点。</template>
    </div>
  </template>
</template>

<script setup>
/* 宏命令页 · 2026-10-30（站主："素材库中有魔兽无限的宏命令素材，先整理好数据，
   然后在网页端导航条添加宏命令入口，设计宏命令页面"）。
   数据整批 L1：一家第三方插件整理、本站没逐条进游戏试过，所以这一页只说
   "这条宏做什么、几级能用、粘进去是什么"，不排"哪个最好用"、不做输出顺序建议（红线：循环提示）。
   筛选与计数全在 lib/macros.js 的纯函数里，单测 app/tests/macros.spec.js 直接打这份真数据。 */
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { load } from '../lib/data.js';
import HlText from '../components/HlText.vue';
import { classOptions, groupOptions, filterMacros, summary, levelText, learnable, CLASS_ORDER } from '../lib/macros.js';

const d = ref(null);
const err = ref('');
const route = useRoute();
const router = useRouter();
const cls = ref(CLASS_ORDER.indexOf(String(route.query.c || '')) >= 0 ? String(route.query.c) : 'warrior');
const grp = ref(String(route.query.g || ''));
const q = ref(String(route.query.q || ''));
const level = ref(route.query.lv === undefined || route.query.lv === '' ? '' : Number(route.query.lv));

function boot() {
  err.value = '';
  load('data/macros.json').then((doc) => {
    if (!doc || !(doc.macros || []).length) { err.value = 'empty'; return; }
    d.value = doc;
  }).catch(() => { err.value = 'load'; });
}
onMounted(boot);

const all = computed(() => (d.value && d.value.macros) || []);
const note = computed(() => (d.value && d.value.meta && d.value.meta.pageNote) || '');
const sum = computed(() => summary(all.value));
/* 职业芯片的数：先把等级与搜索算进去，芯片上的数才是"点下去会看到几条"，
   不是这一职业的总数（放了个不生效的数，比不放更坏）。 */
/* 芯片上的数 = 点下去会看到的数，所以它跟着搜索与等级一起算（放了个不生效的数比不放更坏）。 */
const byClass = computed(() => filterMacros(all.value, { q: q.value, level: level.value }));
const classOpts = computed(() => classOptions(byClass.value));
const inClass = computed(() => byClass.value.filter((m) => m.classId === cls.value));
/* 这一职业的**全量**（没被任何条件筛过），读数行的分母与"滤掉几条"都以它为准。 */
const classAll = computed(() => all.value.filter((m) => m.classId === cls.value));
const groupOpts = computed(() => groupOptions(inClass.value));
const shown = computed(() => filterMacros(all.value,
  { classId: cls.value, group: grp.value, q: q.value, level: level.value }));
/* 选中的组在新筛法里不存在时自动清回"这一职业全部"——与区域卡图例筛选同一条口径：
   不许留一个"芯片还亮着、画面上一条都没有"的状态。搜索词把那个组的宏全筛掉时最容易撞上。 */
watch([groupOpts, grp], ([opts, g]) => {
  if (g && !opts.some((x) => x.group === g)) grp.value = '';
});
const sections = computed(() => groupOpts.value
  .map((g) => ({ group: g.group, rows: shown.value.filter((m) => m.group === g.group) }))
  .filter((s) => s.rows.length));
/* 「滤掉几条」只按等级这一条条件算，与搜索互不干扰——两个条件混在一个数里，
   玩家就没法从这句话推回自己为什么看不到某条宏。 */
const hiddenByLevel = computed(() => classAll.value.filter((m) => !learnable(m, level.value)).length);
const otherHits = computed(() => {
  if (!q.value.trim()) return [];
  const c = classOptions(filterMacros(all.value, { q: q.value, level: level.value }));
  return c.filter((x) => x.id !== cls.value && x.n > 0);
});
const countText = computed(() => {
  const parts = ['宏 ' + shown.value.length + ' / ' + classAll.value.length + ' 条'];
  parts.push('全站 ' + sum.value.total + ' 条');
  if (hiddenByLevel.value > 0) parts.push('学不会的滤掉 ' + hiddenByLevel.value + ' 条');
  return parts.join(' · ');
});

/* 选择同步进地址（?c=&g=&q=&lv=）：这一页的筛法要能直接发给别人，
   也和职业页 / 副本页同一套地址口径。
   selfSync 这个开关不是多余的：同一页里换查询串不会重挂组件（路由的 key 是 path），
   所以下面那个 watch 会看见我们自己 replace 出来的地址——不挡住的话，
   玩家正在输入的词会被"回填"成上一次的，光标跟着跳。 */
let selfSync = false;
function sync() {
  const query = {};
  if (cls.value) query.c = cls.value;
  if (grp.value) query.g = grp.value;
  if (q.value.trim()) query.q = q.value.trim();
  if (level.value !== '' && Number.isFinite(Number(level.value))) query.lv = String(level.value);
  selfSync = true;
  router.replace({ path: '/macros', query });
}

/** 从地址读回状态：直接点开一条分享出来的 ?c=&g=&lv= 必须就是那个筛法。 */
function applyQuery() {
  const c = String(route.query.c || '');
  cls.value = CLASS_ORDER.indexOf(c) >= 0 ? c : cls.value;
  grp.value = String(route.query.g || '');
  q.value = String(route.query.q || '');
  const lv = route.query.lv;
  level.value = (lv === undefined || lv === '') ? '' : Number(lv);
}
watch(() => [route.query.c, route.query.g, route.query.q, route.query.lv], () => {
  if (selfSync) { selfSync = false; return; }
  applyQuery();
});
function pickClass(id) { cls.value = id; grp.value = ''; sync(); }
function pickGroup(g) { grp.value = (grp.value === g || !g) ? '' : g; sync(); }
let deb = null;
function onQ(e) { q.value = e.target.value; clearTimeout(deb); deb = setTimeout(sync, 250); }
watch(level, () => sync());

/* ---- 复制：与术语页 / 技能页同一行为（clipboard API + execCommand 兜底 + 1.8s 提示） ---- */
function toast(msg) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('on');
  clearTimeout(toast._h);
  toast._h = setTimeout(() => t.classList.remove('on'), 1800);
}
function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch (e) { /* 剪贴板不可用就算了 */ }
  document.body.removeChild(ta);
}
function copyText(text) {
  const done = () => toast('这条宏已复制，游戏里新建宏粘进去就行');
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, () => { fallbackCopy(text); done(); });
  } else { fallbackCopy(text); done(); }
}
/* 事件委托：245 张卡不挂 245 个监听，且 <pre> 里的正文与卡片是同一次渲染出来的，
   按 data-copy 找兄弟节点的 pre 就能拿到逐字相同的正文。 */
function onClick(e) {
  const btn = e.target.closest && e.target.closest('.mc-copy');
  if (!btn) return;
  const card = btn.closest('.mc');
  const pre = card && card.querySelector('.mc-b');
  if (!pre) return;
  copyText(pre.textContent);
}
onMounted(() => document.addEventListener('click', onClick));
</script>

<style scoped>
/* 卡片网格：列数写死而不是 auto-fit——auto-fit 在中间宽度会留一整格空格，
   看着像少了一条宏（这坑在首页那两条轨上栽过）。 */
.mcgrid { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:var(--s3); margin-bottom:var(--s4) }
.mc-band { margin-top:var(--s4) }
.mc { display:flex; flex-direction:column; gap:6px; padding:var(--s3) }
.mc-h { display:flex; flex-wrap:wrap; align-items:baseline; gap:6px }
.mc-t { font:700 14.5px/1.4 var(--font-display); color:var(--txt-title) }
.mc-m { font:11.5px var(--font-mono); letter-spacing:.04em; color:var(--txt-muted) }
.mc-n { margin:0; font-size:12.5px; line-height:1.55; color:var(--lead) }
.mc-b { margin:0; padding:8px 9px; background:var(--sunk); border:1px solid var(--line);
  font:12px/1.55 var(--font-mono); color:var(--txt); white-space:pre-wrap; word-break:break-word;
  user-select:all }
.mc-copy { align-self:flex-start; margin-top:2px }
.mc-rank { color:var(--txt-caution); border-color:var(--txt-caution) }
.mc-lv { display:inline-flex; align-items:center; gap:6px; font-size:12.5px; color:var(--txt-muted) }
.mc-lv input { width:64px }
.mc-jump { margin:0 4px }
@media (max-width:1080px) { .mcgrid { grid-template-columns:repeat(2, minmax(0, 1fr)) } }
@media (prefers-reduced-motion: reduce) { .mc, .mc-b, .mc-copy { transition:none } }
</style>
