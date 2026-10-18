<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="L">
    <!-- ① 主卡。2026-10-18 视觉与交互重做：只用我们自己采到的那份数据，
         每层效果说明仍然不存也不显示（那是别人转述的中文句子，红线不抄）。
         这一页只留机制本身（怎么拿点、点数合计、解锁条件）与三块内容。 -->
    <div class="card lge-head">
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">传承专长与传承挑战</h1>
      </div>
      <p class="dim lge-lead">完成传承挑战拿传承点数，用点数在三棵传承树里点永久专长（账号级，不随角色重置）。<b
        class="mono">{{ total }}</b> 项挑战的点数合计 <b class="mono">{{ rules.launchEarnableTotal || '?' }}</b>
        点，首发上限 <b class="mono">{{ rules.launchSpendingCap || '?' }}</b> 点；{{ rules.unlock || '' }}</p>
      <div class="lge-read">
        <span v-for="r in readout" :key="r.k"><b class="mono">{{ r.v }}</b>{{ r.k }}</span>
      </div>
      <!-- 三棵树改成胶囊切换：与导航带同一套语言，选中态填本树色 -->
      <div class="lge-tabs" role="tablist" aria-label="三棵传承树">
        <button v-for="(t, i) in trees" :key="t.id" type="button" role="tab" data-tg
                :data-t="t.id" :aria-selected="tree === t.id ? 'true' : 'false'"
                class="lge-tab" :class="['t' + i, { on: tree === t.id }]" @click="pickTree(t.id)">
          <b>{{ t.nameCn }}</b>
          <span class="mono">{{ knownOf(t) }} 格</span>
          <span v-if="unkOf(t)" class="mono dim">· 未公开 {{ unkOf(t) }}</span>
        </button>
      </div>
      <nav class="lge-anchor" aria-label="本页三段">
        <a v-for="a in ANCHORS" :key="a[0]" :href="hrefOf('legacy.html#' + a[0])"
           @click.prevent="goAnchor(a[0])">{{ a[1] }}</a>
      </nav>
    </div>

    <!-- ② 树 + 详情。格子仍按客户端里的 row × cols 摆（那是数据事实，不重排），
         但每一排左边补一个排号，"行"才有意义；空格与未公开格从此长得不一样。 -->
    <div class="ltreewrap">
      <div class="card ltreecard" id="ltree">
        <template v-if="curTree">
          <h2>{{ curTree.nameCn }}<span class="dim mono">{{ nKnown }} 个专长<template v-if="nUnk"> · {{ nUnk }} 格未公开</template></span></h2>
          <div class="lge-grid" :style="{ '--cols': curTree.cols }">
            <div v-for="r in gridRows" :key="r.row" class="lge-rowwrap">
              <span class="lge-rail mono">第{{ r.row + 1 }}排</span>
              <div class="lge-cells">
                <template v-for="cell in r.cells" :key="cell.k">
                  <div v-if="cell.s.empty" class="lslot none" aria-hidden="true"></div>
                  <div v-else-if="cell.s.unknown" class="lslot unk"><b>?</b><span class="dim">未公开</span></div>
                  <button v-else-if="perkOf(cell)" type="button" class="lslot" :class="{ on: open === perkOf(cell).id }"
                          :data-perk="perkOf(cell).id" :aria-pressed="open === perkOf(cell).id ? 'true' : 'false'"
                          @click="toggle(perkOf(cell).id)">
                    <span class="lcell">
                      <span class="ico-wrap">
                        <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">
                          <rect width="28" height="28" rx="4" :fill="tileOf(cell).fill" :stroke="tileOf(cell).stroke" />
                          <text x="14" y="19" text-anchor="middle" font-size="12" :fill="tileOf(cell).text"
                                font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ tileOf(cell).letter }}</text>
                        </svg>
                        <img v-if="perkOf(cell).iconKey && !broken[perkOf(cell).id]" class="ico"
                             :src="iconUrl(perkOf(cell).iconKey)" alt="" loading="lazy"
                             @error="broken[perkOf(cell).id] = true">
                      </span>
                      <span class="rk mono">{{ perkOf(cell).maxRank == null ? '?' : perkOf(cell).maxRank }} 层</span>
                      <em v-if="perkOf(cell).prerequisiteCn" class="lge-tag">有前置</em>
                    </span>
                    <span class="nm">{{ perkOf(cell).nameCn }}</span>
                  </button>
                  <div v-else class="lslot unk"><b>?</b></div>
                </template>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="empty">这棵树还没收录。</div>
      </div>

      <!-- 详情栏不再是一个空盒子：没选的时候说这一棵树，选了说这个专长 -->
      <div id="ldet">
        <div v-if="!openPerk" class="card ldetail">
          <h2>{{ curTree ? curTree.nameCn + '这一棵' : '三棵传承树' }}</h2>
          <div class="lge-read">
            <span v-for="r in treeReadout" :key="r.k"><b class="mono">{{ r.v }}</b>{{ r.k }}</span>
          </div>
          <ul class="lge-legend">
            <li><i class="lg lg-perk"></i>这一格有专长，点它看层数与前置</li>
            <li><i class="lg lg-unk"></i>有这一格，内容还没公开</li>
            <li><i class="lg lg-none"></i>这一排没有这个位置</li>
          </ul>
        </div>
        <div v-else class="card ldetail lge-perk">
          <div class="lge-prow">
            <span class="lge-pico">
              <svg viewBox="0 0 28 28" width="52" height="52" aria-hidden="true">
                <rect width="28" height="28" rx="4" :fill="tileOf2.id" :stroke="tileOf2.stroke" />
                <text x="14" y="19" text-anchor="middle" font-size="12" :fill="tileOf2.text"
                      font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ tileOf2.letter }}</text>
              </svg>
              <img v-if="openPerk.iconKey && !broken['d' + openPerk.id]" class="ico"
                   :src="iconUrl(openPerk.iconKey)" alt="" loading="lazy"
                   @error="broken['d' + openPerk.id] = true">
            </span>
            <div class="lge-ptitle">
              <h2>{{ openPerk.nameCn }}</h2>
              <div class="lge-ranks">
                <i v-for="k in rankDots" :key="k" class="rd"></i>
                <span class="mono">{{ maxRankTxt }}</span>
              </div>
            </div>
          </div>
          <div class="lmeta">
            <span>属于：<b>{{ openPerk.treeCn }}</b></span>
            <span>位置：第 {{ openPerk.row + 1 }} 排第 {{ openPerk.col + 1 }} 列</span>
            <span>前置：<button v-if="prereqPerk" type="button" class="lge-jump" data-jump
                                @click="selectPerk(prereqPerk.id)">{{ openPerk.prerequisiteCn }}</button>
              <b v-else-if="openPerk.prerequisiteCn">{{ openPerk.prerequisiteCn }}</b>
              <span v-else class="dim">没有前置</span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>传承挑战 · {{ total }} 项</h2>
      <!-- 点数说法从数据里自己长出来：多数挑战给 1 点、有一项给 16 点，写死"每项 1 点"就是假的 -->
      <p class="dim">{{ onesN }} 项各 1 点<template v-if="oddPts.length">，另有 {{ oddTxt }}</template>。</p>
      <div class="field">
        <input v-model="q" type="search" placeholder="搜挑战名、完成条件或归属">
        <span class="dim mono">{{ shownChallenges }} / {{ total }} 项</span>
      </div>
    </div>

    <!-- ③ 六组挑战改成可折叠：整页原来 4900 多像素，六张表连着铺没人滚得完。
         默认只展开第一组；一搜索就把命中的组全部展开（不让人先手动点开再找）。 -->
    <div id="lch">
      <template v-for="blk in challengeBlocks" :key="blk.c.id">
        <div class="card lchgrp" :class="{ closed: !isOn(blk.c.id) }">
          <button type="button" class="lchhead" data-blk :data-b="blk.c.id"
                  :aria-expanded="isOn(blk.c.id) ? 'true' : 'false'" @click="toggleBlock(blk.c.id)">
            <b>{{ blk.c.nameCn }}</b>
            <span class="dim mono">{{ blk.rows.length }}<template v-if="blk.rows.length !== blk.c.items.length"> / {{ blk.c.items.length }}</template> 项 · 合计 {{ blk.sum }} 点</span>
            <i class="lchcaret" aria-hidden="true"></i>
          </button>
          <div v-show="isOn(blk.c.id)" class="lchbody">
            <div v-if="(blk.c.subcategories || []).length" class="chips">
              <template v-for="s in blk.c.subcategories" :key="s">
                <span v-if="chipCount(blk.c, s)" class="chipc">{{ s }}<b class="mono">{{ chipCount(blk.c, s) }}</b></span>
              </template>
            </div>
            <div class="boardwrap">
              <table class="board ltab">
                <colgroup><col class="c-ico"><col style="width:26%"><col><col style="width:14%"><col class="c-num"></colgroup>
                <thead><tr><th class="c-ico">图标</th><th>挑战</th><th>完成条件</th><th>归属</th><th class="c-num">点数</th></tr></thead>
                <tbody>
                  <tr v-for="(x, i) in blk.rows" :key="x.id !== undefined ? x.id : i">
                    <td class="ich"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.nameCn" /></td>
                    <td><HlText :text="x.nameCn" :q="q" /><span class="dim mono">#{{ x.id }}</span></td>
                    <td class="dim"><HlText :text="x.requirement || '未记录'" :q="q" /></td>
                    <td class="dim">{{ x.sub || x.group || blk.c.nameCn }}</td>
                    <td class="mono">{{ x.points == null ? '—' : x.points }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </template>
      <div v-if="!shownChallenges" class="card">
        <div class="empty">这个关键词下没有挑战，换个说法试试（比如"25 级""烹饪""军衔"）。</div>
      </div>
    </div>

    <div class="card" id="lgr">
      <h2>攒到一定挑战数给的奖励 · {{ cnt.rewards }} 档</h2>
      <div class="boardwrap">
        <table class="board ltab">
          <colgroup><col class="c-ico"><col><col style="width:150px"><col class="c-id"></colgroup>
          <thead><tr><th class="c-ico">图标</th><th>奖励</th><th>需要的挑战数</th><th class="c-id">物品编号</th></tr></thead>
          <tbody>
            <tr v-for="x in rewards" :key="x.itemId">
              <td class="ich"><IconCell :icon-key="x.iconKey || ''" :seed="x.itemId" :cn="x.nameCn" /></td>
              <td>{{ x.nameCn }}</td>
              <td class="mono">{{ x.at }}</td>
              <td class="dim mono">#{{ x.itemId }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 传承（Legacy）：三棵专长树 + 66 项挑战 · 数据从 src/data/legacy.json 现取。
   每层效果说明是别人转述的文本，本站不存也不显示（红线）；这一轮重做只动版式与交互。 */
import { computed, nextTick, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import { tileStyle, iconUrl } from '../lib/glyph.js';
import { hrefOf } from '../lib/nav.js';
import IconCell from '../components/IconCell.vue';
import HlText from '../components/HlText.vue';

/* 页首板块图：与首页图标轨「传承」那一格同一张本地原画（站内同一板块同一张脸）。
   必须走 JS 常量而不是模板里的静态 src——public 下的路径不在 Vite 构建图里。 */
const HEAD_ART = 'img/art/races/skyborne.webp';
const ANCHORS = [['ltree', '传承树'], ['lch', '传承挑战'], ['lgr', '进度奖励']];

const L = ref(null);
const err = ref('');
const tree = ref('');
const open = ref('');
const q = ref('');
const broken = ref({});
const expanded = ref([]);
const route = useRoute();

function boot() {
  err.value = '';
  load('data/legacy.json')
    .then((d) => {
      L.value = d;
      const ts = d.trees || [];
      const qt = String(route.query.t || '');
      tree.value = ts.some((t) => t.id === qt) ? qt : ((ts[0] || {}).id || '');
      open.value = String(route.query.p || '');
      // 六组挑战默认只开第一组（整页原来 4900 多像素，六张表连着铺没人滚得完）
      expanded.value = [(((d.challenges || [])[0] || {}).id) || ''].filter(Boolean);
      let qq = String(route.query.q || '');
      // 从首页搜索带着专长名跳进来：直接展开那条并切到它所在的树，别让人自己找格子。
      // 只认全等，避免"搜索挑战时命中一个同名的专长"把下面的挑战筛选给抢掉。
      if (qq && !open.value) {
        const lk = qq.trim().toLowerCase();
        const hitp = (d.perks || []).filter((x) => String(x.nameCn || '').toLowerCase() === lk)[0];
        if (hitp) {
          open.value = hitp.id;
          tree.value = hitp.treeId || tree.value;
          qq = '';
        }
      }
      q.value = qq;
      scrollTo(String(route.query.to || ''));
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

/* 页内锚点：不许写 href="#ltree"——那是哈希路由，会把整条路由换掉（首页那批死链就是这么来的）。
   所以 href 走 hrefOf 出合法的 #/legacy?to=ltree，点击时 preventDefault 只做平滑滚动。 */
function scrollTo(id) {
  if (!id) return;
  nextTick(() => {
    const el = document.getElementById(id);
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'start', behavior: 'smooth' });
  });
}
function goAnchor(id) { scrollTo(id); }

const meta = computed(() => (L.value && L.value.meta) || {});
const rules = computed(() => meta.value.rules || {});
const cnt = computed(() => meta.value.counts || {});
const trees = computed(() => (L.value && L.value.trees) || []);
const perks = computed(() => (L.value && L.value.perks) || []);
const perkById = computed(() => {
  const m = {};
  perks.value.forEach((p) => { m[p.id] = p; });
  return m;
});
const challenges = computed(() => (L.value && L.value.challenges) || []);
const rewards = computed(() => (L.value && L.value.rewards) || []);
/* 点数说法要能从数据里自己长出来：明细里多数挑战给 1 点、有一项给 16 点 */
const allPts = computed(() => challenges.value.reduce((a, c) => a.concat(c.items || []), []));
const total = computed(() => allPts.value.length);
const onesN = computed(() => allPts.value.filter((x) => (x.points || 0) === 1).length);
const oddPts = computed(() => allPts.value.filter((x) => (x.points || 0) !== 1));
const oddTxt = computed(() => oddPts.value.map((x) => x.nameCn + ' 给 ' + x.points + ' 点').join('、'));

const curTree = computed(() => trees.value.filter((t) => t.id === tree.value)[0] || null);
const knownOf = (t) => (t.slots || []).filter((x) => !x.empty && !x.unknown).length;
const unkOf = (t) => (t.slots || []).filter((x) => x.unknown).length;
const nKnown = computed(() => (curTree.value ? knownOf(curTree.value) : 0));
const nUnk = computed(() => (curTree.value ? unkOf(curTree.value) : 0));
/* 主卡那排读数：四个数全部从数据算，一个都不手抄 */
const readout = computed(() => [
  { v: perks.value.length, k: '个专长有明细' },
  { v: (cnt.value.unknownSlots || 0), k: '格还没公开' },
  { v: total.value, k: '项挑战' },
  { v: (cnt.value.rewards || 0), k: '档进度奖励' }
]);
/* 详情栏默认态：这一棵树的读数（层数合计是"最多能点几层"，不是"要点几层"） */
const treeReadout = computed(() => {
  const t = curTree.value;
  if (!t) return [];
  const inTree = perks.value.filter((p) => p.treeId === t.id);
  const ranks = inTree.reduce((a, p) => a + (p.maxRank || 0), 0);
  const preN = inTree.filter((p) => p.prerequisiteCn).length;
  return [{ v: inTree.length, k: '个专长' }, { v: ranks, k: '层最多可点' },
    { v: preN, k: '个要先点前置' }];
});

/* 树格按 rows × cols 逐格摆，缺格子的坐标补空格——与旧站 treeGrid() 同一遍双重循环。
   这一轮改成按"排"分组，好给每一排左边挂排号。 */
const gridRows = computed(() => {
  const t = curTree.value;
  const out = [];
  if (!t) return out;
  for (let row = 0; row < t.rows; row++) {
    const cells = [];
    for (let col = 0; col < t.cols; col++) {
      const s = t.slots.filter((x) => x.row === row && x.col === col)[0] || { empty: true };
      cells.push({ k: row + '-' + col, s: s });
    }
    out.push({ row: row, cells: cells });
  }
  return out;
});
const openPerk = computed(() => perkById.value[open.value] || null);
const prereqPerk = computed(() => {
  const p = openPerk.value;
  if (!p || !p.prerequisite) return null;
  return perkById.value[p.prerequisite] || null;
});
const maxRankTxt = computed(() => {
  const p = openPerk.value;
  if (!p) return '';
  return p.maxRank == null ? '层数未核实' : '最多 ' + p.maxRank + ' 层';
});
const rankDots = computed(() => {
  const p = openPerk.value;
  return p && p.maxRank != null ? Math.min(p.maxRank, 8) : 0;
});

function perkOf(cell) { return perkById.value[cell.s.perk] || null; }
function toggle(id) { open.value = open.value === id ? '' : id; }
function selectPerk(id) {
  const p = perkById.value[id];
  if (!p) return;
  tree.value = p.treeId || tree.value;   // 前置可能在另一棵树：先切过去，不然选中一个看不见的格子
  open.value = id;
}
function pickTree(id) {
  tree.value = id;
  const p = perkById.value[open.value];
  if (p && p.treeId !== id) open.value = '';   // 换树时别把上一棵的选中态留在空栏里
}
function tileOf(cell) { const p = perkOf(cell); return tileStyle(p.id, p.nameCn); }
const tileOf2 = computed(() => {
  const p = openPerk.value;
  return p ? tileStyle(p.id, p.nameCn) : { fill: '', stroke: '', text: '', letter: '' };
});

const kw = computed(() => q.value.trim().toLowerCase());
function rowsOf(c) {
  const k = kw.value;
  if (!k) return c.items || [];
  return (c.items || []).filter((x) => (((x.nameCn || '') + ' ' + (x.requirement || '') + ' ' +
    (x.sub || '') + ' ' + (x.group || ''))).toLowerCase().indexOf(k) >= 0);
}
const challengeBlocks = computed(() => challenges.value.map((c) => {
  const rows = rowsOf(c);
  return { c: c, rows: rows, sum: rows.reduce((a, x) => a + (x.points || 0), 0) };
}).filter((b) => b.rows.length));
const shownChallenges = computed(() => challengeBlocks.value.reduce((a, b) => a + b.rows.length, 0));
function chipCount(c, s) { return (c.items || []).filter((x) => x.sub === s || x.group === s).length; }
/* 搜索时命中的组一律自动展开——不然"折叠"会把搜索结果藏起来，比不折叠更糟 */
function isOn(id) { return kw.value ? true : expanded.value.indexOf(id) >= 0; }
function toggleBlock(id) {
  const i = expanded.value.indexOf(id);
  if (i >= 0) expanded.value.splice(i, 1); else expanded.value.push(id);
}
</script>
