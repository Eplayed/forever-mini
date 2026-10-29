<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <!-- 与旧站 talent() 逐块对齐：职业切换条 → banner → .tpanel（tbg / thead / tlegend / ttabs /
       三棵树 / cmpbox / tfoot）。主卡不带 .cdhead：旧站天赋页第一批就单独排版，
       decoratePageHead() 在这页找不到 h1.pt 而跳过（UI.md 3.29），页面唯一的 H1 是树面板里的「XX 天赋」。 -->
  <template v-else-if="ready">
    <div class="card" style="padding-bottom:0">
      <div class="classbar">
        <button v-for="x in CLS" :key="x.id" class="cls" :class="{ on: x.id === cid }" :data-c="x.id"
                style="min-width:78px" @click="pick(x.id)">
          <div class="ic"><ClassTile :class-id="x.id" :cn="x.cn" :icon-key="x.iconKey" /></div>
          <div class="n">{{ x.cn }}</div>
        </button>
      </div>
    </div>

    <div v-if="bannerKind === 'none'" class="banner">这个职业还没有天赋数据。</div>
    <div v-else-if="bannerKind === 'pool'" class="banner"><button class="ghost" id="demo" @click="loadDemo">载入演示数据</button></div>
    <div v-else-if="bannerKind === 'demo'" class="banner gray">当前是<b>演示结构</b>，节点名与位置都不是游戏数据。<button class="ghost" id="back" @click="backReal">回到真实数据</button></div>
    <div v-else-if="bannerKind === 'stats'" class="banner">本职业 {{ counts.tcnt }} 个天赋：与经典旧世相比<b class="ok">{{ counts.chg.added }} 个新增</b>、<b class="caution">{{ counts.chg.modified }} 个改动</b>、{{ counts.chg.moved }} 个换层、{{ counts.chg.unchanged }} 个未变；{{ counts.vcnt }} 个名称与官网中文一致<template v-if="counts.ccnt">，<b class="alert">{{ counts.ccnt }} 个译名有两个叫法</b></template><template v-if="gate">。层级点数门槛：第 2 层起需在本系累计 {{ gate }} 点</template>。</div>

    <div class="tpanel">
      <div v-if="cband" class="tbg"><img :src="assetUrl(cband)" alt="" loading="lazy" @error="onArtBad"></div>
      <div class="thead">
        <h1 class="title">{{ (clsObj.cn || '') }} 天赋</h1>
        <span class="pts">剩余 <b>{{ remaining }}</b>/{{ R.totalPoints }}</span>
        <input type="search" id="tq" class="tqs" placeholder="搜天赋名" :value="searchQ" @input="onQ">
        <button class="ghost" id="cmp" :aria-pressed="cmpOpen ? 'true' : 'false'" @click="toggleCompare">与经典旧世对比</button>
        <span class="dim mono" id="sel"></span>
      </div>
      <div class="tlegend"><span><i class="lg added"></i>新增</span><span><i class="lg modified"></i>改动</span>
        <span><i class="lg moved"></i>换层</span><span><i class="lg unchanged"></i>未变</span></div>
      <div class="ttabs">
        <button v-for="(t, ti) in trees" :key="t.id || ti" :data-tab="ti" :class="{ on: ti === active }"
                :title="treeTip(t) || null" @click="active = ti">{{ t.nameCn || '' }}<i v-if="t.nameConflict && t.nameAlt" class="cfl" aria-hidden="true"></i></button>
      </div>

      <template v-if="trees.length">
        <div class="trees">
          <div v-for="tv in treeViews" :key="tv.ti" class="tree" :class="['t' + (tv.ti % 3), { hide: narrow && tv.ti !== active }]"
               :data-tree="tv.ti">
            <span v-if="treeBg(tv.ti)" class="tbg" aria-hidden="true" :style="{ backgroundImage: 'url(' + treeBg(tv.ti) + ')' }"></span>
            <h3><span :title="treeTip(tv.t) || null">{{ tv.t.nameCn || '' }}<i v-if="tv.t.nameConflict && tv.t.nameAlt" class="cfl" aria-hidden="true"></i> <span class="dim mono">{{ tv.t.nameEn || '' }}</span></span>
              <button class="ghost" :data-clear="tv.ti" style="font-size:11px;padding:2px 6px" @click="clearTree(tv.ti)">清空</button></h3>
            <div class="hint">已投 {{ tv.sp }} 点 · {{ tv.count }} 个天赋 · {{ nextGate(tv.t) }}</div>

            <template v-if="tv.rows">
              <div v-for="(row, ri) in tv.rows" :key="ri" class="row" :style="{ gridTemplateColumns: 'repeat(' + tv.cols + ',1fr)' }">
                <template v-for="(n, ci) in row" :key="ci">
                  <div v-if="n" class="node" :class="nodeCls(n, tv.t, false)" :data-n="n.id" :data-t="tv.ti"
                       :title="tips[n.id]" role="button" tabindex="0" :aria-label="labelOf(n)"
                       :aria-pressed="state[n.id] ? 'true' : 'false'" :style="hlStyle(n)"
                       @click="onNodeClick(tv.ti, n.id)" @contextmenu.prevent="act(tv.ti, n.id, 'sub')"
                       @keydown="nodeKey($event, tv.ti, n.id)"
                       @touchstart="tpStart(tv.ti, n.id)" @touchmove="tpCancel" @touchcancel="tpCancel" @touchend="tpCancel">
                    <span class="ico-wrap">
                      <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">
                        <rect width="28" height="28" rx="4" :fill="ph(n).fill" :stroke="ph(n).stroke" />
                        <text x="14" y="19" text-anchor="middle" font-size="12" :fill="ph(n).text"
                              font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ ph(n).letter }}</text>
                      </svg>
                      <img v-if="n.iconKey && !gone[n.id]" class="ico" :src="iconUrl(n.iconKey)" alt="" loading="lazy" @error="hideIco(n.id)">
                    </span>
                    <i v-if="n.level === 'L2'" class="flag"></i><i v-if="n.nameVerified" class="vok"></i><i v-if="n.nameConflict" class="cfl"></i>
                    <span class="nm">{{ n.nameCn || n.nameEn || '' }}</span>
                    <span class="rank">{{ state[n.id] || 0 }}/{{ n.maxRanks == null ? '?' : n.maxRanks }}</span>
                  </div>
                  <div v-else></div>
                </template>
              </div>
            </template>
            <div v-else class="flow">
              <div v-for="n in tv.t.nodes" :key="n.id" class="node" :class="nodeCls(n, tv.t, true)" :data-n="n.id" :data-t="tv.ti"
                   :title="tips[n.id]" role="button" tabindex="0" :aria-label="labelOf(n)"
                   :aria-pressed="state[n.id] ? 'true' : 'false'" :style="hlStyle(n)"
                   @click="onNodeClick(tv.ti, n.id)" @contextmenu.prevent="act(tv.ti, n.id, 'sub')"
                   @keydown="nodeKey($event, tv.ti, n.id)"
                   @touchstart="tpStart(tv.ti, n.id)" @touchmove="tpCancel" @touchcancel="tpCancel" @touchend="tpCancel">
                <span class="ico-wrap">
                  <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">
                    <rect width="28" height="28" rx="4" :fill="ph(n).fill" :stroke="ph(n).stroke" />
                    <text x="14" y="19" text-anchor="middle" font-size="12" :fill="ph(n).text"
                          font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ ph(n).letter }}</text>
                  </svg>
                  <img v-if="n.iconKey && !gone[n.id]" class="ico" :src="iconUrl(n.iconKey)" alt="" loading="lazy" @error="hideIco(n.id)">
                </span>
                <i v-if="n.level === 'L2'" class="flag"></i><i v-if="n.nameVerified" class="vok"></i><i v-if="n.nameConflict" class="cfl"></i>
                <span class="nm">{{ n.nameCn || n.nameEn || '' }}</span>
                <span class="rank">{{ state[n.id] || 0 }}/{{ n.maxRanks == null ? '?' : n.maxRanks }}</span>
              </div>
            </div>

            <svg v-if="lines[tv.ti] && lines[tv.ti].length" class="tlines" aria-hidden="true">
              <line v-for="(l, li) in lines[tv.ti]" :key="li" :x1="l.x1" :y1="l.y1" :x2="l.x2" :y2="l.y2" />
            </svg>
          </div>
        </div>
      </template>
      <div v-else-if="pool.length" style="padding:16px">
        <h3 style="margin-bottom:8px">天赋名 {{ pool.length }} 条</h3>
        <div class="pool"><span v-for="(p, pi) in pool" :key="pi" class="term" :data-copy="p.nameCn" @click="copyTerm(p.nameCn)">{{ p.nameCn }}</span></div>
      </div>
      <div v-else class="empty">这个职业还没有天赋条目。</div>

      <!-- 展开收起动效（motion.css 的 unfold）：外层只做"行长不开"，所以它不能带
           border/padding——否则关掉以后会留下一条 1px 的金线当尾巴。长相都还在 .cmpbox 上。 -->
      <Transition name="unfold">
        <div v-show="cmpOpen" class="cmp-clip"><div class="cmpbox wf-in" id="cmpbox">
        <p v-if="cmpLoading" class="dim">对照在载入…</p>
        <template v-else-if="cmpRows.length">
          <h3>与经典旧世逐条对照 · {{ cmpRows.length }} 条</h3>
          <div v-for="e in cmpRows" :key="e.id" class="cmprow">
            <b>{{ e.name || '' }}</b>
            <span v-if="e.tag" class="tag">{{ e.tag }}</span>
            <span v-if="e.condition" class="dim mono">{{ e.condition }}</span>
            <div v-if="e.changeNote">{{ String(e.changeNote).replace(/^改动摘要：/, '') }}</div>
            <div v-if="(e.ranks || []).length" class="cmp-ranks">
              <template v-for="(rk, ri) in e.ranks" :key="ri"><span class="dim mono">{{ rk.label }}</span> {{ rk.text }}<br v-if="ri < e.ranks.length - 1"></template>
            </div>
          </div>
        </template>
        </div></div>
      </Transition>

      <div class="tfoot">
        <label class="dim">等级 <span class="mono" id="lvv">{{ lv }}</span></label>
        <input type="range" min="10" max="60" value="60" id="lv" aria-label="按角色等级筛选可用天赋" v-model.number="lv">
        <button id="mode" class="ghost" @click="toggleMode">{{ mode === 'add' ? '当前：加点' : '当前：减点' }}</button>
        <button id="copy" class="ghost" @click="copyPlan">复制方案</button>
        <button id="share" class="ghost" @click="sharePlan">分享链接</button>
        <button id="reset" class="ghost" @click="resetPlan">重置</button>
        <span class="sp">{{ describeStr }}</span>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 天赋计算器 · 与旧站 src/talent.html + app.js 的 talent() + src/js/talent.js 逐块对齐。
   引擎（加点/减点/级联/门槛/前置/编解码）从旧站逐行搬进本文件，不许引用旧站全局。
   数据一律 lib/data.js load() 现取；占位色块复用 lib/glyph.js 的 tileStyle（与旧站
   Glyph.talentTile 同一套 FNV 算法，已逐行比对一致，不抄两份）。
   方案存储：localStorage key 与旧站完全同款（'wfs.build.' + 职业id），分享码旧站放在
   location.hash，新站是 hash 路由（#/talent），改放 query 参数 p 承载，编解码同款。 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { assetUrl, load } from '../lib/data.js';
import { tileStyle, iconUrl } from '../lib/glyph.js';
import { specArt } from '../lib/art.js';
import ClassTile from '../components/ClassTile.vue';

/* ================= 天赋树引擎（逐行搬自旧站 src/js/talent.js · window.TalentEngine） ================= */
function defaults(rules) {
  return {
    totalPoints: rules && rules.totalPoints ? rules.totalPoints : 51,
    tierUnlockCost: rules && rules.tierUnlockCost ? rules.tierUnlockCost : null
  };
}
function index(trees) {
  var map = {};
  trees.forEach(function (t) {
    t.nodes.forEach(function (n) { map[n.id] = { node: n, tree: t }; });
  });
  return map;
}
function ranksOf(state, id) { return state[id] || 0; }
function treeSpent(tree, state) {
  return tree.nodes.reduce(function (a, n) { return a + ranksOf(state, n.id); }, 0);
}
function spent(state, trees) {
  return trees.reduce(function (a, t) { return a + treeSpent(t, state); }, 0);
}
function tierOpen(tree, state, node, r) {
  if (!r.tierUnlockCost || node.tier === null || node.tier === undefined) return true;
  var need = r.tierUnlockCost[node.tier] || 0;
  return treeSpent(tree, state) >= need;
}
function hasTiers(tree) {
  return !!(tree && tree.nodes && tree.nodes.length && tree.nodes[0].tier !== null && tree.nodes[0].tier !== undefined);
}
function reqMissing(node, state) {
  return (node.requires || []).filter(function (id) { return ranksOf(state, id) < 1; });
}
function canAdd(tree, state, node, r, allTrees) {
  if (node.maxRanks === null || node.maxRanks === undefined) return { ok: false, why: '该天赋点数上限未核实' };
  if (ranksOf(state, node.id) >= node.maxRanks) return { ok: false, why: '已达上限 ' + node.maxRanks + ' 点' };
  if (!tierOpen(tree, state, node, r)) return { ok: false, why: '本系需先投满 ' + (r.tierUnlockCost[node.tier] || 0) + ' 点解锁第 ' + (node.tier + 1) + ' 层' };
  var miss = reqMissing(node, state);
  if (miss.length) return { ok: false, why: '前置未点：' + miss.join('、') };
  if (spent(state, allTrees || [tree]) >= r.totalPoints) return { ok: false, why: '可用点数已用尽（共 ' + r.totalPoints + ' 点）' };
  return { ok: true };
}
function add(trees, state, node, fileRules) {
  var t = trees.filter(function (x) { return x.nodes.some(function (n) { return n.id === node.id; }); })[0];
  if (!t) return { state: state, msg: '未知节点' };
  var r = defaults(fileRules || t.rules);
  var c = canAdd(t, state, node, r, trees);
  if (!c.ok) return { state: state, msg: c.why };
  var s = Object.assign({}, state); s[node.id] = ranksOf(state, node.id) + 1;
  return { state: s, msg: null };
}
function dependents(tree, id) {
  var out = [];
  tree.nodes.forEach(function (n) {
    if ((n.requires || []).indexOf(id) >= 0) { out.push(n); out = out.concat(dependents(tree, n.id)); }
  });
  return out;
}
function remove(trees, state, node) {
  if (ranksOf(state, node.id) < 1) return { state: state, msg: '该天赋尚未加点' };
  var s = Object.assign({}, state);
  s[node.id] = ranksOf(state, node.id) - 1;
  var dropped = [];
  trees.forEach(function (t) {
    dependents(t, node.id).forEach(function (d) {
      var miss = reqMissing(d, s);
      if (miss.length && ranksOf(s, d.id) > 0) {
        s[d.id] = 0; dropped.push(d.nameCn || d.nameEn || d.id);
      }
    });
  });
  return { state: s, msg: dropped.length ? '已级联清空：' + dropped.join('、') : null };
}
/* 编码：每系按节点顺序取点数（0-9），系间用 - 分隔 */
function encode(trees, state) {
  return trees.map(function (t) {
    return t.nodes.map(function (n) { return Math.min(ranksOf(state, n.id), 9).toString(36); }).join('');
  }).join('-');
}
function decode(str, trees) {
  var state = {}, bad = 0;
  if (!str) return { state: state, bad: 0 };
  var parts = String(str).split('-');
  trees.forEach(function (t, ti) {
    var s = parts[ti] || '';
    t.nodes.forEach(function (n, ni) {
      var v = parseInt(s.charAt(ni) || '0', 36);
      if (isNaN(v)) { v = 0; bad++; }
      var max = n.maxRanks === null || n.maxRanks === undefined ? 0 : n.maxRanks;
      if (v > max) { v = max; bad++; }
      if (v > 0) state[n.id] = v;
    });
  });
  return { state: state, bad: bad };
}
function tiers(tree) {
  var max = -1;
  tree.nodes.forEach(function (n) { if (n.tier > max) max = n.tier; });
  var out = [];
  for (var t = 0; t <= max; t++) {
    out.push(tree.nodes.filter(function (n) { return n.tier === t; })
      .sort(function (a, b) { return a.column - b.column; }));
  }
  return out;
}
function describe(trees, state) {
  return trees.map(function (t) {
    return t.nameCn + ' ' + treeSpent(t, state);
  }).join(' / ');
}

/* ================= 页面状态（对应旧站 tstate） ================= */
const LS = 'wfs.build.';   // 与旧站 app.js 同一款前缀：方案按 'wfs.build.' + 职业id 存
const route = useRoute();
const router = useRouter();

const CLS = ref([]);
const ART = ref({});
const file = ref(null);
const demoOnly = ref(false);
const state = ref({});
const mode = ref('add');
const active = ref(0);
const searchQ = ref('');
const lv = ref(60);
const err = ref('');
const gone = ref({});          // 图取不到就不占位（新站惯例：不产生重复失败请求）
const cmpOpen = ref(false);
const cmpLoading = ref(false);
const cmpData = ref(null);
const narrow = ref(false);
const lines = ref([]);         // 每棵树的前置连线坐标（渲染后量出来再画，同旧站 drawLinks）

const cid = computed(() => String(route.query.c || '') || 'hunter');
const clsObj = computed(() => CLS.value.filter((x) => x.id === cid.value)[0] || {});
const trees = computed(() => (file.value && file.value.trees) || []);
const pool = computed(() => (file.value && file.value.namePool) || []);
const R = computed(() => defaults(file.value && file.value.rules));
const ready = computed(() => CLS.value.length > 0 && file.value !== null);
const remaining = computed(() => Math.max(0, R.value.totalPoints - spent(state.value, trees.value)));
const describeStr = computed(() => describe(trees.value, state.value));
/* 旧站 banner 的门槛读数取顶层 f.tierUnlockCost（多数职业没有这个顶层字段，句子就不出现），
   引擎用的才是 rules.tierUnlockCost——两处不是一回事，照旧站原样分头取。 */
const gate = computed(() => (((file.value || {}).tierUnlockCost) || []).filter((v) => v).join(' / '));
const cband = computed(() => (ART.value.classes || {})[cid.value] || '');
const bannerKind = computed(() => {
  const f = file.value || {};
  if (f.structureStatus === 'none') return 'none';
  if (!trees.value.length) return pool.value.length ? 'pool' : 'empty';
  if (f.structureStatus === 'demo') return 'demo';
  return 'stats';
});
const counts = computed(() => {
  let tcnt = 0, vcnt = 0, ccnt = 0;
  const chg = { added: 0, modified: 0, moved: 0, unchanged: 0 };
  trees.value.forEach((t) => (t.nodes || []).forEach((n) => {
    tcnt++; if (n.nameVerified) vcnt++; if (n.nameConflict) ccnt++;
    if (chg[n.changeState] !== undefined) chg[n.changeState]++;
  }));
  return { tcnt, vcnt, ccnt, chg };
});

/* 三棵树渲染数据：层级网格（.row，按列数补空格）或无层级的 .flow 宽格 */
const treeViews = computed(() => trees.value.map((t, ti) => {
  const cols = maxCol(t) + 1;
  const rows = hasTiers(t) ? tiers(t).map((row) => slotsOf(row, cols)) : null;
  return { t, ti, cols, rows, sp: treeSpent(t, state.value), count: (t.nodes || []).length };
}));

/* 每个节点的悬停说明（旧站拼在 title 属性里，搜索高亮也按这段文本匹配） */
const tips = computed(() => {
  const out = {}, st = state.value, r = R.value;
  trees.value.forEach((t) => (t.nodes || []).forEach((n) => {
    const rk = st[n.id] || 0;
    const can = canAdd(t, st, n, r, trees.value);
    out[n.id] = [n.nameCn || '未命名', n.nameEn, rk + '/' + (n.maxRanks === null ? '?' : n.maxRanks),
      n.nameAlt ? '另一来源译作「' + n.nameAlt + '」，待定稿' : '',
      n.nameVerified ? '名称与官网中文一致' : '名称待实测',
      can.ok ? (mode.value === 'add' ? '点击加 1 点（右键或长按减点）' : '点击减 1 点') : can.why
    ].filter(Boolean).join(' ｜ ');
  }));
  return out;
});

/* 与经典旧世逐条对照（按需加载，结构与旧站 compareHtml 一致） */
const cmpRows = computed(() => {
  const nodes = (cmpData.value && cmpData.value.nodes) || {};
  return Object.keys(nodes)
    .filter((id) => nodes[id].changeNote || (nodes[id].ranks || []).length)
    .map((id) => Object.assign({ id }, nodes[id]));
});

/* ================= 加载与还原 ================= */
function boot() {
  err.value = '';
  /* 旧站还并发请求了 glossary.json，但 tstate.gloss 从未被天赋页读到，这里不再空发这一枪。 */
  Promise.all([load('data/classes.json'), load('data/art.json').catch(() => ({}))])
    .then((rs) => { CLS.value = rs[0].classes || []; ART.value = rs[1] || {}; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
function loadTree(c) {
  load('data/talents/' + c + '.json').then((f) => { file.value = f; demoOnly.value = false; restore(c, f); })
    .catch(() => {
      file.value = { classId: c, structureStatus: 'none', dataVersion: '—', trees: [], namePool: [],
        note: '尚未收录该职业的天赋数据' };
      demoOnly.value = true; state.value = {};
    });
}
function restore(c, f) {
  const saved = store(LS + c) || String(route.query.p || '');
  const dec = decode(saved, f.trees || []);
  state.value = dec.state;
  if (dec.bad && saved) toast('方案与当前数据版本不完全匹配，已按可识别部分还原');
}
function store(key, val) {
  try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); return null; }
  catch (e) { toast('本机存储不可用，方案仅本次有效'); return null; }
}

/* ================= 交互（对应旧站 bindTalent / act / clearTree） ================= */
function pick(id) {
  /* 与旧站 location.href = 'talent.html?c=..' 一致：切职业只带 c，tree/q 方案码都不带走 */
  if (id !== cid.value) router.replace({ path: '/talent', query: { c: id } });
}
function act(ti, id, force) {
  const f = file.value; if (!f) return;
  const t = (f.trees || [])[+ti]; if (!t) return;
  const n = t.nodes.filter((x) => x.id === id)[0];
  if (!n) return;
  const m = force || mode.value;
  const res = m === 'add' ? add(f.trees, state.value, n, f.rules) : remove(f.trees, state.value, n);
  if (res.msg) toast(res.msg);
  if (res.state !== state.value) { state.value = res.state; persist(); }
}
function clearTree(ti) {
  const t = (file.value.trees || [])[ti]; if (!t) return;
  const s = Object.assign({}, state.value);
  t.nodes.forEach((n) => { delete s[n.id]; });
  state.value = s; persist(); toast('已清空 ' + t.nameCn);
}
function persist() { store(LS + cid.value, encode(trees.value || [], state.value)); }
function resetPlan() { state.value = {}; persist(); }
function toggleMode() { mode.value = mode.value === 'add' ? 'sub' : 'add'; }
function textBuild() {
  const f = file.value, out = [f.classId || cid.value];
  (f.trees || []).forEach((t) => {
    out.push('## ' + t.nameCn + ' ' + treeSpent(t, state.value) + ' 点');
    t.nodes.forEach((n) => {
      const rk = state.value[n.id] || 0;
      if (rk) out.push('- ' + (n.nameCn || '（未核实名）') + (n.nameEn ? ' / ' + n.nameEn : '') + ' ' + rk + '/' + n.maxRanks);
    });
  });
  return out.join('\n');
}
function copyPlan() { copyText(textBuild(), '方案文本'); }
function sharePlan() {
  /* 旧站把方案码放在 location.hash（?c=..#编码）；新站是 hash 路由，改放 query 参数 p，
     编码算法与 localStorage key 都不变。跳完再取 location.href，链接即可分享。 */
  const code = encode(trees.value || [], state.value);
  router.replace({ path: '/talent', query: { c: cid.value, p: code } })
    .then(() => copyText(location.href, '分享链接'));
}
function loadDemo() {
  load('data/talents/_demo.json').then((f) => {
    file.value = f;
    const code = String(route.query.p || '');
    state.value = code ? decode(code, f.trees).state : {};
  });
}
function backReal() { loadTree(cid.value); }
function onQ(e) { searchQ.value = e.target.value; }
/* 长按即减点；记时间戳吞掉手指抬起后浏览器补发的 click（与旧站同一套守卫） */
let lpTimer = null;
let lastLongPress = 0;
function tpStart(ti, id) {
  tpCancel();
  lpTimer = setTimeout(() => {
    lpTimer = null;
    lastLongPress = Date.now();
    act(ti, id, 'sub');
  }, 500);
}
function tpCancel() { if (lpTimer) { clearTimeout(lpTimer); lpTimer = null; } }
function onNodeClick(ti, id) {
  if (Date.now() - lastLongPress < 700) return;
  act(ti, id);
}
function nodeKey(e, ti, id) {
  if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); act(ti, id); }
  else if (e.key === 'Backspace' || e.key === 'Delete') { e.preventDefault(); act(ti, id, 'sub'); }
}

/* ================= 渲染辅助 ================= */
function maxCol(t) { return (t.nodes || []).reduce((m, n) => (n.column > m ? n.column : m), 0); }
function slotsOf(row, cols) {
  const out = [];
  for (let i = 0; i < cols; i++) out.push(null);
  row.forEach((n) => { if (n.column >= 0 && n.column < cols) out[n.column] = n; });
  return out;
}
function nextGate(t) {
  if (!R.value.tierUnlockCost) return '层级门槛未核实';
  const sp = treeSpent(t, state.value);
  for (let i = 0; i < R.value.tierUnlockCost.length; i++) if (sp < R.value.tierUnlockCost[i]) return '再投 ' + (R.value.tierUnlockCost[i] - sp) + ' 点解锁第 ' + (i + 1) + ' 层';
  return '全部层已解锁';
}
function treeTip(t) {
  return t && t.nameConflict && t.nameAlt
    ? '这一系有两个叫法：官方中文写「' + (t.nameCn || '') + '」，另一来源译作「' + (t.nameAlt || '') + '」，待定稿' : null;
}
function nodeCls(n, t, wide) {
  const rk = state.value[n.id] || 0;
  const can = canAdd(t, state.value, n, R.value, trees.value);
  return [wide ? 'wide' : '', rk ? 'on' : '', (!can.ok && rk === 0) ? 'lock' : '',
    n.nameConflict ? 'conf' : '', n.changeState ? 'chg-' + n.changeState : ''];
}
function labelOf(n) {
  const rk = state.value[n.id] || 0;
  return (n.nameCn || n.nameEn || '未命名天赋') + '，已点 ' + rk + ' / 上限 ' + (n.maxRanks == null ? '未核实' : n.maxRanks);
}
function ph(n) { return tileStyle(n.id, n.nameCn); }
function hideIco(id) { gone.value = Object.assign({}, gone.value, { [id]: true }); }
function onArtBad(e) { e.target.className = 'bad'; }
function treeBg(ti) { return specArt(ART.value, cid.value, ti); }
const qv = computed(() => searchQ.value.trim().toLowerCase());
function hlStyle(n) {
  return qv.value && String(tips.value[n.id] || '').toLowerCase().indexOf(qv.value) >= 0
    ? { outline: '2px solid var(--warn)' } : null;
}
function toggleCompare() {
  cmpOpen.value = !cmpOpen.value;
  if (!cmpOpen.value || cmpData.value) return;
  cmpLoading.value = true;
  load('data/talent-text/' + cid.value + '.json')
    .then((t) => { cmpData.value = t; cmpLoading.value = false; })
    .catch(() => { cmpData.value = { nodes: {} }; cmpLoading.value = false; });
}

/* ================= toast / 复制（与 GlossaryPage 同一套，含 execCommand 兜底） ================= */
function toast(msg) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('on');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('on'), 1800);
}
function copyFallback(text) {
  const ta = document.createElement('textarea');
  ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta); ta.select();
  try { document.execCommand('copy'); } catch (e) { /* 剪贴板不可用就算了 */ }
  document.body.removeChild(ta);
}
function copyText(text, label) {
  const done = () => toast('已复制：' + (label || String(text).slice(0, 12)));
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, () => { copyFallback(text); done(); });
  } else { copyFallback(text); done(); }
}
function copyTerm(t) { copyText(t); }

/* ================= 前置连线（同旧站 drawLinks：渲染完量出格子位置再画 SVG） ================= */
function drawLinks() {
  const root = document;
  const out = [];
  root.querySelectorAll('.tree[data-tree]').forEach((col) => {
    const ti = +col.getAttribute('data-tree');
    const t = trees.value[ti];
    if (!t) { out[ti] = []; return; }
    const box = col.getBoundingClientRect();
    const pos = {};
    col.querySelectorAll('.node[data-n]').forEach((n) => { pos[n.getAttribute('data-n')] = n; });
    const arr = [];
    (t.nodes || []).forEach((n) => {
      const to = pos[n.id]; if (!to) return;
      (n.requires || []).forEach((rid) => {
        const from = pos[rid]; if (!from) return;
        const a = from.getBoundingClientRect(), b = to.getBoundingClientRect();
        arr.push({ x1: +(a.left - box.left + a.width / 2).toFixed(1), y1: +(a.top - box.top + a.height / 2).toFixed(1),
          x2: +(b.left - box.left + b.width / 2).toFixed(1), y2: +(b.top - box.top + b.height / 2).toFixed(1) });
      });
    });
    out[ti] = arr;
  });
  lines.value = out;
}

/* ================= 生命周期与路由消费 ================= */
/* ?c= 选职业、?tree= 选树、?q= 高亮某天赋（首页天赋预览的格子就带这三个参数跳进来） */
watch(cid, (v) => {
  gone.value = {};
  active.value = 0;                 // 与旧站整页跳转一致：切职业不带旧 tab / 旧搜索词
  searchQ.value = String(route.query.q || '');
  const tt = parseInt(route.query.tree, 10);
  if (tt >= 0 && tt < 3) active.value = tt;
  if (v) loadTree(v);
}, { immediate: true });
/* 已在本页时又点了带 tree/q 的预览入口：单独接住这两个参数（不反向清空——
   分享链接的 router.replace 会摘掉它们，不能因此把当前 tab 与搜索词抹掉） */
watch(() => route.query.tree, (v) => {
  if (v === undefined || v === null) return;
  const tt = parseInt(v, 10);
  if (tt >= 0 && tt < 3) active.value = tt;
});
watch(() => route.query.q, (v) => { if (v !== undefined && v !== null) searchQ.value = String(v); });

function onResize() {
  const w = document.body.clientWidth < 861;
  if (w !== narrow.value) narrow.value = w;
}
onMounted(() => {
  boot();
  narrow.value = document.body.clientWidth < 861;
  window.addEventListener('resize', onResize);
});
onBeforeUnmount(() => window.removeEventListener('resize', onResize));
/* 树结构 / 当前系 / 窄屏任一变化后重画连线（位置不随加点变，无需盯 state） */
watch([ready, file, active, narrow], () => nextTick(drawLinks));
</script>
