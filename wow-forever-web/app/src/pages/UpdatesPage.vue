<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <!-- 与旧站 src/js/app.js 的 updates()（3243-3409 行）逐块对齐。
         主卡头：本页不在旧站 PAGE_HEAD_SEC 表里 → .cdhead.noart big（标题不带图），与速查页同一模式。
         2026-10-08 用户决策：「最新动态」只在网页放开（小程序不做），正常迁。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">最新动态</h1></div>
      <p class="dim">官方公告里的时间点、客户端里的职业改动、本站自己改了什么，三件事分开列。</p>
      <div class="stats readout">
        <div class="stat"><b>{{ tl.length }}</b>个官方时间点</div>
        <div class="stat"><b>{{ chItems.length }}</b>条客户端改动</div>
        <div class="stat"><b>{{ S.changesNew }}</b>个新增天赋</div>
        <div class="stat"><b>{{ S.changesRemoved }}</b>个移除天赋</div>
        <div class="stat"><b>{{ cl.length }}</b>条本站更新</div>
      </div>
      <!-- hash 路由下 href="#k0" 会吃掉 #/updates，点击拦下来手动滚，DOM 与旧站同构 -->
      <div class="picks utabs" role="group" aria-label="跳到本页三个板块">
        <a v-for="(t, i) in K" :key="t" class="pick" :href="'#k' + i" @click.prevent="jump('k' + i)"><b>{{ t }}</b><span class="dim">跳 ↓</span></a>
      </div>
    </div>

    <div class="card" id="k0">
      <h2>官方公告里的时间点</h2>
      <div v-for="(r, i) in tlRows" :key="r.x.id || i" class="flowrow" :class="r.cls"><b class="mono">{{ r.x.date }}</b><div><b>{{ r.x.title }}</b>{{ r.note ? ' ' : '' }}<span v-if="r.note" class="when mono">{{ r.note }}</span><p class="dim">{{ r.x.what }}</p></div></div>
    </div>

    <div class="card" id="k1">
      <h2>客户端改动清单 · {{ chItems.length }} 条</h2>
      <!-- 这四格与下面那行对照从首页搬来，放在它描述的那张表头上，才对得上「全部 965 条 vs 四格之和」。 -->
      <div class="four">
        <div><b>{{ S.changesNew }}</b><s>新增天赋</s></div>
        <div><b>{{ S.changesModified }}</b><s>改动天赋</s></div>
        <div><b>{{ S.changesRemoved }}</b><s>移除</s></div>
        <div><b>{{ S.changesSpellsChanged }}</b><s>法术有变</s></div>
      </div>
      <div class="kv"><span>这四格加起来比上面的 {{ chItems.length }} 少 {{ chItems.length - chgSum2 }} 条</span><b>{{ chItems.length }} = 天赋 {{ S.changesTalents }} + 法术 {{ chItems.length - S.changesTalents }}</b></div>
      <p class="dim">清单把 {{ chItems.length }} 条客户端条目都列了出来，其中 {{ chgSum2 }} 条在无限服真的动了（新增、改动、移除，或法术说明有变）；剩下的只是列进对照表、本身没变。</p>
      <div id="chbody">
        <div class="kchips" role="group" aria-label="按改动类别筛">
          <button v-for="x in CH_KINDS" :key="x[0]" type="button" class="kchip" :class="{ on: kind === x[0] }" :data-k="x[0]" :aria-pressed="kind === x[0] ? 'true' : 'false'" @click="kind = x[0]">{{ x[1] }} <b class="mono">{{ kindCount(x[0]) }}</b></button>
        </div>
        <div class="picks">
          <button type="button" class="pick" :class="{ on: !cls }" data-c="" @click="cls = ''"><b>全职业</b><span class="dim mono">{{ chItems.length }}</span></button>
          <button v-for="c in classes" :key="c.id" type="button" class="pick" :class="{ on: cls === c.id }" :data-c="c.id" @click="cls = c.id"><b>{{ c.cn }}</b><span class="dim mono">{{ clsCount(c.id) }}</span></button>
        </div>
        <div class="field">
          <select id="cw" v-model="what" aria-label="按天赋或法术筛">
            <option value="all">天赋 + 法术</option>
            <option value="talent">只看天赋</option>
            <option value="spell">只看法术</option>
          </select>
          <select id="ck" v-model="kind" aria-label="按改动类别筛">
            <option v-for="x in CH_KINDS" :key="x[0]" :value="x[0]">{{ x[1] }}</option>
          </select>
          <input type="search" id="cq" placeholder="搜天赋名或系名" :value="q" @input="onQ">
          <span class="dim mono" id="ccnt">{{ rows.length }} 条</span>
        </div>
        <div v-if="rows.length" class="boardwrap">
          <table class="board">
            <!-- 七列百分比合计正好 100%：table-layout:fixed 下只要指定宽度之和小于表宽，
                 浏览器就把富余按比例摊到每一列上，图标列会被撑到 81px、日期列 197px（实拍量出来）。
                 摊不掉，所以这里让百分比凑满 100%，富余全部留在名字列（它是阅读起点，宽一点不别扭）。 -->
            <colgroup><col style="width:4%"><col style="width:34%"><col style="width:10%"><col style="width:11%"><col style="width:12%"><col style="width:17%"><col style="width:12%"></colgroup>
            <thead><tr><th>图标</th><th>名称</th><th>职业</th><th>所在系</th><th>类型</th><th>改动</th><th>核到哪天</th></tr></thead>
            <tbody>
              <tr v-for="x in pageRows" :key="x.id">
                <td class="ich"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.nameCn" small /></td>
                <td><HlText :text="x.nameCn" :q="q" /><span v-if="x.oldNameCn" class="dim">（旧名 {{ x.oldNameCn }}）</span></td>
                <td>{{ cnOf[x.classId] || x.classId }}</td>
                <td class="dim">{{ x.tree || '—' }}</td>
                <td class="dim">{{ x.kind === 'spell' ? '法术' : '天赋' }}{{ x.maxRank ? ' ' : '' }}<span v-if="x.maxRank" class="mono">{{ x.maxRank }} 层</span></td>
                <td><span class="tag" :class="{ new: x.changeKind === 'added' }">{{ x.changeCn }}</span></td>
                <td class="mono dim dt">{{ x.discoveredAt || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="rows.length > 400" class="note">一次只列 400 条（当前命中 {{ rows.length }} 条），把职业或类别收紧一点再看其余的。</p>
        <div v-if="!rows.length" class="empty">这个筛选下没有条目。</div>
      </div>
    </div>

    <div class="card" id="k2">
      <h2>本站更新 · {{ cl.length }} 条</h2>
      <div v-for="(e, i) in cl" :key="e.commit || i" class="flowrow"><b class="mono">{{ e.date }}</b><div><b>{{ e.title }}</b><span class="chips"><span v-for="t in (e.tags || []).slice(0, 5)" :key="t" class="chipc">{{ t }}</span></span></div></div>
    </div>
  </template>
</template>

<script setup>
/* 最新动态：官方时间点 + 客户端改动清单 + 本站更新，与旧站 updates() 逐块对齐。
   数据一律 lib/data.js load() 现取；筛选、分组、排序逻辑照旧站逐行搬，文本逐字抄。 */
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import { byDate } from '../lib/fmt.js';
import HlText from '../components/HlText.vue';
import IconCell from '../components/IconCell.vue';

const CH_KINDS = [['all', '全部类别'], ['added', '新增'], ['modified', '改动'], ['moved', '换层或换系'],
  ['removed', '移除'], ['renamed', '改名'], ['unchanged', '未变']];
const K = ['官方时间点', '客户端改动', '本站更新'];

const route = useRoute();
const routeQ = String(route.query.q || '');

const d = ref(null);
const err = ref('');
const cls = ref('');
const what = ref('all');
const kind = ref('all');
const q = ref(routeQ);

function boot() {
  err.value = '';
  Promise.all([load('data/changes.json'), load('data/timeline.json'),
    load('data/releases.json'), load('data/classes.json'), load('data/scale.json')])
    .then((r) => {
      d.value = { ch: r[0] || {}, tl: ((r[1] || {}).items || []).slice().sort(byDate),
        cl: (r[2] || {}).items || [], classes: (r[3] || {}).classes || [], S: (r[4] || {}).scale || {} };
      // 搜索结果是带着职业与「天赋/法术」跳进来的，落地就停在那张表上
      const uc = String(route.query.c || ''), uw = String(route.query.w || '');
      if (d.value.classes.some((c) => c.id === uc)) cls.value = uc;
      if (uw === 'talent' || uw === 'spell') what.value = uw;
      if (routeQ) nextTick(scrollTok1);
      // 首页那两个「全部 N 个 →」以前是 updates.html#k0 这种旧站锚点，
      // 现在走 #/updates?to=k0，落地后滚到那一张卡（hash 路由里不能再嵌 '#'）
      const to = String(route.query.to || '');
      if (to) nextTick(() => {
        const el = document.getElementById(to);
        if (el && el.scrollIntoView) el.scrollIntoView({ block: 'start', behavior: 'smooth' });
      });
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
onMounted(boot);

/* 旧站整页重载每次都重读 URL；hash 路由同路径换 query 时组件复用（router-view 只按 path 做 key），
   这里补齐同一行为 */
watch(() => route.query, () => {
  if (!d.value) return;
  q.value = String(route.query.q || '');
  const uc = String(route.query.c || ''), uw = String(route.query.w || '');
  cls.value = d.value.classes.some((c) => c.id === uc) ? uc : '';
  what.value = (uw === 'talent' || uw === 'spell') ? uw : 'all';
  if (q.value) nextTick(scrollTok1);
});

function onQ(e) { q.value = e.target.value; }
/* 从首页搜索跳进来时直接滚到那张表，别让人自己找 */
function scrollTok1() {
  const k1 = document.getElementById('k1');
  if (k1 && k1.scrollIntoView) k1.scrollIntoView({ block: 'start' });
}
function jump(id) {
  const n = document.getElementById(id);
  if (n && n.scrollIntoView) n.scrollIntoView({ block: 'start' });
}

const chItems = computed(() => (d.value && d.value.ch.items) || []);
const tl = computed(() => (d.value && d.value.tl) || []);
const cl = computed(() => (d.value && d.value.cl) || []);
const classes = computed(() => (d.value && d.value.classes) || []);
const S = computed(() => (d.value && d.value.S) || {});
const cnOf = computed(() => {
  const m = {};
  classes.value.forEach((c) => { m[c.id] = c.cn; });
  return m;
});
/* 四格之和现算（与首页同一口径），不写死 */
const chgSum2 = computed(() => (S.value.changesNew || 0) + (S.value.changesModified || 0) +
  (S.value.changesRemoved || 0) + (S.value.changesSpellsChanged || 0));

/* 时间轴要能一眼看出「下一件是哪件」：只提亮最近的那一条。这一页时间轴是**倒序**排的
   （最近的日期在最上面），所以「下一件」按日期取还没发生里最早的那条，与排序方向无关。
   差多少天按今天现算，按 +08:00 的当日零点比。 */
const TODAY0 = new Date(new Date().toDateString()).getTime();
function tsOf(x) {
  return /^\d{4}-\d{2}-\d{2}$/.test(x.date || '') ? new Date(x.date + 'T00:00:00+08:00').getTime() : null;
}
const tlRows = computed(() => {
  const list = tl.value;
  let nextI = -1, nextT = 0;
  list.forEach((x, i) => {
    const t = tsOf(x);
    if (t === null || t < TODAY0) return;
    if (nextI < 0 || t < nextT) { nextI = i; nextT = t; }
  });
  return list.map((x, i) => {
    const t = tsOf(x);
    let st = { cls: '', note: '' };
    if (t !== null) {
      const dd = Math.round((t - TODAY0) / 86400000);
      if (i === nextI) st = { cls: 'near', note: dd === 0 ? '就是今天' : '还有 ' + dd + ' 天' };
      else if (dd < 0) st = { cls: 'past', note: '已过 ' + (-dd) + ' 天' };
      else st = { cls: '', note: '还有 ' + dd + ' 天' };
    }
    return { x: x, cls: st.cls, note: st.note };
  });
});

/* kchip 上的计数照旧站逐字：数的是 it.kind（talent/spell），与筛选项用的 changeKind 不是同一字段，
   结果只有「全部类别」非零——口径改了与旧站对不上，原样保留 */
function kindCount(k) {
  return k === 'all' ? chItems.value.length : chItems.value.filter((it) => it.kind === k).length;
}
function clsCount(id) { return chItems.value.filter((x) => x.classId === id).length; }

const rows = computed(() => {
  const kw = q.value.trim().toLowerCase();
  return chItems.value.filter((x) => {
    if (cls.value && x.classId !== cls.value) return false;
    if (what.value !== 'all' && x.kind !== what.value) return false;
    if (kind.value !== 'all' && x.changeKind !== kind.value) return false;
    if (kw && String(x.nameCn || '').toLowerCase().indexOf(kw) < 0 &&
      String(x.tree || '').toLowerCase().indexOf(kw) < 0) return false;
    return true;
  });
});
/* 一次只列 400 条 */
const pageRows = computed(() => rows.value.slice(0, 400));
</script>
