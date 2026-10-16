<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="L">
    <!-- 主卡：与旧站 legacy() 的 set() 产出对齐（cdhead 板块图是 decoratePageHead 补的，这里直接摆出来）。
         2026-10-12 站主决定：这一页只留机制本身（怎么拿点、点数合计、解锁条件）与表格，
         讲数据出自哪份解包、每层效果为什么不复制、点数两说怎么取舍那几段已删，
         出处与缺口集中在溯源页（provenance.html）。 -->
    <div class="card">
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">传承专长与传承挑战</h1>
      </div>
      <p class="dim">完成传承挑战拿传承点数，用点数在三棵传承树里点永久专长（账号级，不随角色重置）。<b
        class="mono">{{ total }}</b> 项挑战的点数合计 <b class="mono">{{ rules.launchEarnableTotal || '?' }}</b>
        点，首发上限 <b class="mono">{{ rules.launchSpendingCap || '?' }}</b> 点；{{ rules.unlock || '' }}</p>
      <div class="stats">
        <div class="stat"><b>{{ cnt.perks }}</b>个专长有明细</div>
        <div class="stat"><b>{{ cnt.unknownSlots }}</b>格还没公开</div>
        <div class="stat"><b>{{ total }}</b>项挑战</div>
        <div class="stat"><b>{{ cnt.rewards }}</b>档进度奖励</div>
      </div>
      <div class="picks">
        <button v-for="t in trees" :key="t.id" type="button" class="pick" :class="{ on: tree === t.id }"
                :data-t="t.id" @click="tree = t.id">
          <b>{{ t.nameCn }}</b><span class="dim mono">{{ t.slots.filter((x) => !x.empty).length }}</span>
        </button>
      </div>
    </div>

    <!-- 三棵专长树：格子按客户端里的位置摆（rows × cols 逐格），空格/未公开格/专长格三种形态 -->
    <div class="ltreewrap">
      <div class="card ltreecard" id="ltree">
        <template v-if="curTree">
          <h2>{{ curTree.nameCn }}<span class="dim mono">{{ nKnown }} 个专长<template v-if="nUnk"> · {{ nUnk }} 格未公开</template></span></h2>
          <div class="lgrid">
            <template v-for="cell in gridCells" :key="cell.k">
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
                </span>
                <span class="nm">{{ perkOf(cell).nameCn }}</span>
              </button>
              <div v-else class="lslot unk"><b>?</b></div>
            </template>
          </div>
        </template>
        <div v-else class="empty">这棵树还没收录。</div>
      </div>
      <div id="ldet">
        <div v-if="!openPerk" class="card leempty"><h2>点一个专长看细节</h2></div>
        <div v-else class="card ldetail">
          <h2>{{ openPerk.nameCn }} <span class="dim mono">最多 {{ openPerk.maxRank == null ? '未核实' : openPerk.maxRank + ' 层' }}</span></h2>
          <div class="lmeta">
            <span>属于：<b>{{ openPerk.treeCn }}</b></span>
            <span>位置：第 {{ openPerk.row + 1 }} 排第 {{ openPerk.col + 1 }} 列</span>
            <span>前置：<b v-if="openPerk.prerequisiteCn">{{ openPerk.prerequisiteCn }}</b><span v-else class="dim">没有前置</span></span>
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

    <div id="lch">
      <template v-for="blk in challengeBlocks" :key="blk.c.nameCn">
        <!-- 组头不写"每项 N 点"：客户端明细里 65 项各给 1 点、有一项给 16 点，
             统一说"每项 1 点"就是假的。逐条点数在表格最后一列，组头只给合计。 -->
        <div class="card lchgrp">
          <h2>{{ blk.c.nameCn }}<span class="dim mono">{{ blk.rows.length }}<template v-if="blk.rows.length !== blk.c.items.length"> / {{ blk.c.items.length }}</template> 项 · 合计 {{ blk.sum }} 点</span></h2>
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
      </template>
      <div v-if="!shownChallenges" class="card">
        <div class="empty">这个关键词下没有挑战，换个说法试试（比如"25 级""烹饪""军衔"）。</div>
      </div>
    </div>

    <div class="card">
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
/* 传承（Legacy）：三棵专长树 + 65 项挑战 · 与旧站 src/js/app.js 的 legacy() 逐块对齐。
   数据从 src/data/legacy.json 现取；点数逐条按客户端明细写（多数 1 点、一项 16 点），
   组头只给合计；每层效果说明是别人转述的文本，本站不存也不显示（红线）。 */
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import { tileStyle, iconUrl } from '../lib/glyph.js';
import IconCell from '../components/IconCell.vue';
import HlText from '../components/HlText.vue';

/* 页首板块图：与首页图标轨「传承」那一格同一张本地原画（站内同一板块同一张脸）。
   必须走 JS 常量而不是模板里的静态 src——public 下的路径不在 Vite 构建图里。 */
const HEAD_ART = 'img/art/races/skyborne.webp';

const L = ref(null);
const err = ref('');
const tree = ref('');
const open = ref('');
const q = ref('');
const broken = ref({});
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
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

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
const nKnown = computed(() => (curTree.value ? curTree.value.slots.filter((x) => !x.empty && !x.unknown).length : 0));
const nUnk = computed(() => (curTree.value ? curTree.value.slots.filter((x) => x.unknown).length : 0));
/* 树格按 rows × cols 逐格摆，缺格子的坐标补空格——与旧站 treeGrid() 同一遍双重循环 */
const gridCells = computed(() => {
  const t = curTree.value;
  const out = [];
  if (!t) return out;
  for (let row = 0; row < t.rows; row++) {
    for (let col = 0; col < t.cols; col++) {
      const s = t.slots.filter((x) => x.row === row && x.col === col)[0] || { empty: true };
      out.push({ k: row + '-' + col, s: s });
    }
  }
  return out;
});
const openPerk = computed(() => perkById.value[open.value] || null);

function perkOf(cell) { return perkById.value[cell.s.perk] || null; }
function toggle(id) { open.value = open.value === id ? '' : id; }
function tileOf(cell) { const p = perkOf(cell); return tileStyle(p.id, p.nameCn); }

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
</script>
