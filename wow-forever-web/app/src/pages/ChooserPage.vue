<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="D">
    <!-- 卡片头：chooser 在旧站 PAGE_HEAD_SEC 表里，set() 的 decoratePageHead() 会把 h1.pt
         换成 cdhead big + 板块原画（img/art/classes/paladin.webp），这里直接写等价结构。 -->
    <div class="card chead">
      <div class="mline">7 题 · 9 职业</div>
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">选职业问答</h1>
      </div>
    </div>

    <div class="card cstep">
      <div class="crow">
        <span class="dim mono">第 {{ Math.min(step + 1, total) }} / {{ total }} 题</span>
        <span class="sp"></span><button class="ghost" id="creset" @click="reset">重新开始</button>
      </div>
      <div class="cov">
        <i v-for="(qq, i) in qs" :key="qq.id" :class="answers[qq.id] ? (i < step ? 'L0' : 'L1') : 'L3'"
           :style="{ width: covWidth }" :title="qq.q"></i>
      </div>
    </div>

    <div class="csplit">
      <!-- 结果态：与旧站 drawChooser() 的 done 分支同构。这句不是说明文案，
           是红线要求的标注：按玩法归类，不冒充强度结论。 -->
      <template v-if="done">
        <div class="banner gray">下面是按你选的玩法归类的候选，<b>不是强度排行，也不代表哪个职业更强</b>。<template v-if="tied.length > 3">这次并列第一有 {{ tied.length }} 个职业，都算同样合适。</template></div>
        <div v-for="id in top" :key="id" class="card mcard">
          <div class="crow">
            <div class="ic lg"><ClassTile :class-id="id" :cn="cls(id).cn" :icon-key="cls(id).iconKey" mod="lg" /></div>
            <div style="flex:1">
              <h2 style="margin:0">{{ cls(id).cn }} <span class="dim mono">{{ cls(id).en || '' }}</span></h2>
              <div class="mbar"><i :style="{ width: donePct(live.score[id]) + '%' }"></i></div>
              <div class="dim">匹配度 {{ donePct(live.score[id]) }}%（{{ live.score[id] }} 分，本题库最高 {{ doneMax }} 分）</div>
            </div>
          </div>
          <ul v-if="(live.reasons[id] || []).length" class="list">
            <li v-for="(x, ri) in live.reasons[id]" :key="ri">{{ x }}</li>
          </ul>
          <!-- 2026-10-12 站主决定：这一页只留问答结果，讲本站天赋名核对进度的那句已删，出处见溯源页。 -->
          <component :is="talentProps(id).to ? 'router-link' : 'a'" v-bind="talentProps(id)" class="btn">看这个职业的天赋树 →</component>
        </div>
        <div class="card">
          <h2>其余候选</h2>
          <div class="pool">
            <span v-for="id in rest" :key="id" class="term">{{ cls(id).cn }} {{ live.score[id] }} 分</span>
          </div>
        </div>
      </template>
      <div v-else class="card cq">
        <div class="mline">已答 {{ answeredCount }} 题 · 还剩 {{ pool.length }} 个候选</div>
        <h2>{{ cur.q }}</h2>
        <p v-if="cur.hint" class="dim">{{ cur.hint }}</p>
        <div class="qopts">
          <button v-for="(o, i) in cur.options" :key="o.id" class="qopt" :class="{ on: answers[cur.id] === o.id }"
                  :data-o="o.id" @click="pick(o.id)">
            <span class="qi mono">{{ 'ABC'.slice(i, i + 1) }}</span>{{ o.label }}
          </button>
        </div>
        <div class="crow" style="margin-top:10px">
          <template v-if="step">
            <button class="ghost" id="cprev" @click="prev">← 上一题</button><span class="sp"></span>
          </template>
        </div>
      </div>

      <!-- 这一页的内容就是「9 个职业被 7 题逐步筛掉」，所以 9 个职业一直摆在屏幕上：
           答一题，掉出候选的变暗、领先的转金；进度就是「还剩几个候选」。 -->
      <aside class="cboard">
        <div class="mline">还在候选 <b>{{ pool.length }}</b> 个</div>
        <div class="ctiles">
          <div v-for="t in board" :key="t.id" class="ctile"
               :class="{ off: answeredCount && !t.s, lead: answeredCount && t.lead }">
            <span class="ci"><ClassTile :class-id="t.id" :cn="t.cn" :icon-key="t.iconKey" /></span>
            <b>{{ t.cn }}</b><em class="mono">{{ t.s }}</em>
            <span class="en dim">{{ t.en }}</span>
            <i class="cs"><s :style="{ width: t.pct + '%' }"></s></i>
          </div>
        </div>
      </aside>
    </div>
  </template>
</template>

<script setup>
/* 选职业问答 · 与旧站 src/js/app.js 的 chooser()/chooserScores()/drawChooser()（行 1104-1218）逐块对齐。
   旧站状态对象 cstate 在这里拆成 ref：answers 每次整体换新对象驱动 computed 重算。
   结果卡出口走 linkFor('talent.html') + query { c: id }（与 ClassesPage 的 calcLink 同一套写法）。 */
import { computed, onMounted, ref } from 'vue';
import { load } from '../lib/data.js';
import { linkFor } from '../lib/nav.js';
import ClassTile from '../components/ClassTile.vue';

/* 卡片头的板块原画：chooser 在旧站 SEC_ART 表里对应这张（站内同一板块同一张脸）。
   走 JS 常量而不是模板字符串字面量，避免 Vite 去解析 public 下的路径。 */
const HEAD_ART = 'img/art/classes/paladin.webp';

const D = ref(null);
const err = ref('');
const answers = ref({});
const step = ref(0);

function boot() {
  err.value = '';
  /* 旧站还并发请求了 glossary.json，但 cstate.gloss 从未被页面读到，这里不再空发这一枪。 */
  Promise.all([load('data/chooser.json'), load('data/classes.json')])
    .then((rs) => { D.value = { qs: rs[0].questions || [], classes: rs[1].classes || [] }; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时重新拉一次

const qs = computed(() => (D.value && D.value.qs) || []);
const classes = computed(() => (D.value && D.value.classes) || []);
const total = computed(() => qs.value.length);
const answeredCount = computed(() => Object.keys(answers.value).length);
const done = computed(() => step.value >= total.value);
const cur = computed(() => qs.value[step.value] || {});
const covWidth = computed(() => ((100 / total.value).toFixed(2) + '%'));

/* 打分：与旧站 chooserScores() 同一算法——权重 ≥2 且选项带注的才进推荐理由 */
const live = computed(() => {
  const score = {}, reasons = {};
  classes.value.forEach((c) => { score[c.id] = 0; reasons[c.id] = []; });
  Object.keys(answers.value).forEach((qid) => {
    const q = qs.value.filter((x) => x.id === qid)[0];
    if (!q) return;
    const opt = q.options.filter((o) => o.id === answers.value[qid])[0];
    if (!opt) return;
    for (const cid in (opt.weight || {})) {
      if (!Object.prototype.hasOwnProperty.call(opt.weight, cid)) continue;
      const w = opt.weight[cid];
      if (score[cid] === undefined) score[cid] = 0;
      score[cid] += w;
      if (w >= 2 && opt.note && reasons[cid].indexOf(opt.note) < 0) reasons[cid].push(opt.note);
    }
  });
  return { score: score, reasons: reasons };
});

const ids = computed(() => classes.value.map((c) => c.id));
const maxScore = computed(() => Math.max.apply(null, ids.value.map((i) => live.value.score[i]).concat([0])));
const leadIds = computed(() => (maxScore.value ? ids.value.filter((i) => live.value.score[i] === maxScore.value) : []));
const pool = computed(() => ((answeredCount.value && maxScore.value)
  ? ids.value.filter((i) => live.value.score[i] > 0) : ids.value));

const ranked = computed(() => ids.value.slice().sort((a, b) => live.value.score[b] - live.value.score[a]));
const doneMax = computed(() => Math.max.apply(null, ranked.value.map((id) => live.value.score[id]).concat([1])));
const byId = computed(() => { const m = {}; classes.value.forEach((c) => { m[c.id] = c; }); return m; });
const top = computed(() => ranked.value.slice(0, 3));
const tied = computed(() => ranked.value.filter((id) => live.value.score[id] === doneMax.value));
const rest = computed(() => ranked.value.filter((id) => top.value.indexOf(id) < 0));

function cls(id) { return byId.value[id] || { id: id, cn: id }; }
function donePct(score) { return doneMax.value ? Math.round(score / doneMax.value * 100) : 0; }

const board = computed(() => ids.value.slice()
  .sort((a, b) => live.value.score[b] - live.value.score[a])
  .map((id) => {
    const c = classes.value.filter((x) => x.id === id)[0] || { id: id, cn: id };
    const s = live.value.score[id];
    return { id: id, cn: c.cn, en: c.en || '', iconKey: c.iconKey || '', s: s,
      lead: leadIds.value.indexOf(id) >= 0,
      pct: maxScore.value ? Math.round(s / maxScore.value * 100) : 0 };
  }));

function pick(oid) {
  const next = Object.assign({}, answers.value);
  next[cur.value.id] = oid;
  answers.value = next;
  step.value += 1;
  if (done.value) window.scrollTo(0, 0);
}
function reset() { answers.value = {}; step.value = 0; }
function prev() { step.value = Math.max(0, step.value - 1); }

function talentProps(id) {
  const l = linkFor('talent.html');
  return l.to ? { to: { path: l.to, query: { c: id } } }
    : { href: l.href + '?c=' + encodeURIComponent(id) };
}
</script>
