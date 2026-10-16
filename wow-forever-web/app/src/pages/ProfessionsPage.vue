<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="doc">
    <!-- 主卡：与旧站 professions() 的 set() 产出对齐（cdhead 板块图是 decoratePageHead 补的，
         这里直接摆出来）。这一页是唯一拿图标当板块图的页：官方 CDN 转存的专业总表图。
         2026-10-12 站主决定：页首那句讲"配方数据从哪来、本站红线不碰什么"的说明已删，
         出处集中在溯源页（provenance.html）；这一页只留专业数、配方数这些读数与表。 -->
    <div class="card">
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">专业与配方</h1>
      </div>
      <div class="stats" style="margin-top:12px">
        <div class="stat"><b>{{ ps.length }}</b>个专业</div>
        <div class="stat"><b>{{ sumRecipes }}</b>条配方</div>
        <div class="stat"><b>{{ sumNew }}</b>条无限新增</div>
        <div class="stat"><b>{{ sumNodes }}</b>个采集点</div>
      </div>
      <div class="picks">
        <button v-for="p in ps" :key="p.id" class="pick" :class="{ on: p.id === selId }"
                :data-p="p.id" @click="selId = p.id">
          <b>{{ p.nameCn }}</b><span class="dim mono">{{ p.counts.recipes || p.counts.nodes }}</span>
        </button>
      </div>
    </div>

    <!-- 选中专业的表：与旧站 draw() 产出的 head + body 逐块对齐。
         这一页的任务是"我这点技能能做什么、下一步要什么"：配方按技能橙点分四箱，
         材料画成条——"要 20 个草"和"只要 1 个矿"得一眼看出来不一样。 -->
    <div id="pbody">
      <div class="card">
        <!-- h2 里三段的间隔空格与旧站逐字一致（元素间的换行空白会被模板编译器吞掉，必须同行） -->
        <h2>{{ sel.nameCn }} <span v-if="sel.nameEn" class="dim mono">{{ sel.nameEn }}</span> <span class="dim">{{ sel.kind === 'gather' ? '采集' : '制作' }}</span></h2>
        <div class="field">
          <input v-model="q" type="search" placeholder="搜制成品或材料名">
          <input v-model="lv" type="number" min="1" max="300" placeholder="我的技能 1–300" class="lv">
          <button type="button" class="pick tog" :class="{ on: onlyNew }"
                  :aria-pressed="onlyNew ? 'true' : 'false'" @click="onlyNew = !onlyNew">只看无限新增</button>
          <span class="dim mono">{{ shownRecipes.length + shownNodes.length }} 条</span>
        </div>
      </div>

      <!-- 空态要说清为什么空，那句话在 professions.json 的 note 里，不在代码里另写一遍 -->
      <div v-if="sel.unparsed" class="card">
        <div class="empty">{{ sel.note || '这一版还没拆出可列的条目。' }}</div>
      </div>

      <div v-if="shownNodes.length" class="card">
        <h2>采集点 · {{ shownNodes.length }}</h2>
        <div class="scrollx">
          <table class="entab">
            <thead><tr><th class="ich">图标</th><th>{{ nodeHeadLabel }}</th><th>可得</th><th>最多区域</th><th>技能</th></tr></thead>
            <tbody>
              <tr v-for="(n, i) in shownNodes" :key="n.nameCn + '-' + i">
                <td class="ich"><IconCell :icon-key="n.iconKey || ''" :seed="n.nameCn" :cn="n.nameCn" /></td>
                <td><HlText :text="n.nameCn" :q="q" /></td>
                <td class="dim">{{ (n.yields || []).join('、') }}</td>
                <td class="dim">{{ n.zone || '—' }}</td>
                <td><span v-if="!n.skill" class="dim">—</span><span v-else class="sk"><i
                  v-for="s in skList(n.skill)" :key="s.k" class="sk-t" :class="'sk-' + s.k"
                  :title="s.cn + '色起点'">{{ s.cn }}<b>{{ n.skill[s.k] }}</b></i></span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="shownRecipes.length" class="card">
        <h2>配方 · {{ shownRecipes.length }} 条</h2>
        <template v-for="b in bands" :key="b.label">
          <template v-if="b.rows.length">
            <h3 class="rbandh">{{ b.label }} <b class="mono">{{ b.rows.length }}</b></h3>
            <div class="scrollx">
              <table class="entab">
                <thead><tr><th class="ich">制成品</th><th>材料</th><th>技能</th><th>来源</th></tr></thead>
                <tbody>
                  <tr v-for="(x, i) in b.rows" :key="x.itemId + '-' + i">
                    <td>
                      <IconCell :icon-key="x.iconKey || ''" :seed="x.itemId" :cn="x.nameCn" small />
                      <span :class="'q' + (x.quality || 0)"><HlText :text="x.nameCn" :q="q" /></span>
                      <span v-if="x.isNew" class="tag">新</span>
                      <span class="dim mono"> #{{ x.itemId }}</span>
                    </td>
                    <td class="mats">
                      <template v-if="(x.mats || []).length">
                        <i class="mbar" aria-hidden="true"><s :style="{ width: matPct(x) + '%' }"></s></i>
                        <span v-for="(m, j) in x.mats" :key="j" class="mat"><IconCell
                          :icon-key="m.iconKey || ''" :seed="m.nameCn" :cn="m.nameCn" small />{{ m.nameCn }}<b
                          class="mono">×{{ m.count }}</b></span>
                      </template>
                      <span v-else class="dim">无需材料</span>
                    </td>
                    <td><span v-if="!x.skill" class="dim">—</span><span v-else class="sk"><i
                      v-for="s in skList(x.skill)" :key="s.k" class="sk-t" :class="'sk-' + s.k"
                      :title="s.cn + '色起点'">{{ s.cn }}<b>{{ x.skill[s.k] }}</b></i></span></td>
                    <td class="dim"><template v-if="srcLines(x).length"><template
                        v-for="(l, i) in srcLines(x)" :key="i"><br v-if="i">{{ l }}</template></template><template
                        v-else>—</template></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </template>
      </div>

      <div v-if="!shownNodes.length && !shownRecipes.length && !sel.unparsed" class="card">
        <div class="empty">这个专业没有匹配条目，试试放宽搜索或技能等级。</div>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 专业与配方 · 与旧站 src/js/app.js 的 professions() 逐块对齐。
   数据全部从 src/data/professions.json 现取，一个字段都不写死；
   掉落/产出只写数据里有的名称，没有百分比（全站红线）。
   2026-10-12 站主决定：讲"技能四档怎么读、材料条怎么比长短"与逐条来源的段落已删，
   出处集中在溯源页（provenance.html），这里只留配方表与采集点表。 */
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import IconCell from '../components/IconCell.vue';
import HlText from '../components/HlText.vue';

/* 页首板块图：与首页图标轨「专业」那一格同一张图（站内同一板块同一张脸）。
   必须走 JS 常量而不是模板里的静态 src——public 下的路径不在 Vite 构建图里。 */
const HEAD_ART = 'img/icons/10prof_table_tailoring01.jpg';
/* 配方四箱：与旧站同一份分箱（按技能橙点，1–75 / 76–150 / 151–225 / 226–300） */
const BANDS = [[1, 75, '学徒 · 1–75'], [76, 150, '熟练 · 76–150'],
  [151, 225, '专家 · 151–225'], [226, 300, '大师 · 226–300']];

const doc = ref(null);
const err = ref('');
const selId = ref('');
const q = ref('');
const lv = ref('');
const onlyNew = ref(false);
const route = useRoute();

function boot() {
  err.value = '';
  load('data/professions.json')
    .then((d) => {
      doc.value = d;
      const want = String(route.query.p || '');
      const hit = ((d.professions || []).filter((p) => p.id === want))[0];
      selId.value = (hit || (d.professions || [])[0] || {}).id || '';
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
// 旧站支持 ?p=专业&q=关键词 直达（首页搜索带词跳进来），落地就该是筛好的样子
if (route.query.q) q.value = String(route.query.q);
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

const ps = computed(() => (doc.value && doc.value.professions) || []);
const sel = computed(() => ps.value.filter((p) => p.id === selId.value)[0] || ps.value[0] || null);
const sumRecipes = computed(() => ps.value.reduce((s, p) => s + p.counts.recipes, 0));
const sumNew = computed(() => ps.value.reduce((s, p) => s + p.counts.newRecipes, 0));
const sumNodes = computed(() => ps.value.reduce((s, p) => s + p.counts.nodes, 0));
const nodeHeadLabel = computed(() =>
  sel.value && sel.value.id === 'herbalism' ? '草药点' : sel.value && sel.value.id === 'fishing' ? '水域' : '采集点');

const kw = computed(() => q.value.trim().toLowerCase());
const lvNum = computed(() => { const n = parseInt(lv.value, 10); return isNaN(n) ? '' : n; });
/* 技能四档只列数据里有的色（橙/黄/绿/灰），顺序与旧站 skillCell 同一份表 */
const SK_KEYS = [['orange', '橙'], ['yellow', '黄'], ['green', '绿'], ['grey', '灰']];
function skList(sk) {
  return SK_KEYS.filter((x) => sk[x[0]] !== undefined).map((x) => ({ k: x[0], cn: x[1] }));
}
/* 来源那一格的三层信息，与旧站 srcCell 同一算法（各来自不同资料，缺哪层就不写哪层）：
   参考站给的类别 → 哪几个商人在哪卖这张图纸 → 图纸从谁身上掉。掉率是红线，源里也没有。 */
function srcLines(x) {
  const out = [];
  if (x.source) out.push(x.source);
  const vs = x.vendors || [];
  if (vs.length) {
    out.push('商人：' + vs.slice(0, 2).map((v) => v.name + (v.zone ? '（' + v.zone + '）' : '')).join('、')
      + (vs.length > 2 ? ' 等 ' + (vs.length + (x.vMore || 0)) + ' 处' : ''));
  }
  const ds = x.formulaDrops || [];
  if (ds.length) {
    out.push('图纸掉落：' + ds.slice(0, 2).map((d) => d.npc + (d.zone ? '（' + d.zone + '）' : '')).join('、')
      + (ds.length > 2 ? ' 等 ' + (ds.length + (x.dMore || 0)) + ' 处' : ''));
  }
  return out;
}
function learnable(sk) {
  if (!sk || lvNum.value === '') return true;
  return sk.orange <= lvNum.value;
}
const shownRecipes = computed(() => {
  const k = kw.value;
  return ((sel.value || {}).recipes || []).filter((x) => {
    if (onlyNew.value && !x.isNew) return false;
    if (!learnable(x.skill)) return false;
    if (!k) return true;
    return String(x.nameCn || '').toLowerCase().indexOf(k) >= 0 ||
      (x.mats || []).some((m) => String(m.nameCn || '').toLowerCase().indexOf(k) >= 0);
  });
});
const shownNodes = computed(() => {
  const k = kw.value;
  return ((sel.value || {}).nodes || []).filter((x) => !k ||
    String(x.nameCn || '').toLowerCase().indexOf(k) >= 0 ||
    (x.yields || []).join(' ').toLowerCase().indexOf(k) >= 0);
});

/* 材料条的长度基准是当前筛出的这批配方里总量最大的那条，与旧站同一算法 */
const maxMat = computed(() => Math.max.apply(null,
  shownRecipes.value.map((x) => (x.mats || []).reduce((a, m) => a + (m.count || 1), 0)).concat([1])));
function matPct(x) {
  const total = (x.mats || []).reduce((a, m) => a + (m.count || 1), 0);
  return Math.max(6, Math.round(total / maxMat.value * 100));
}
function inBand(x, b) {
  const o = (x.skill || {}).orange;
  return typeof o === 'number' && o >= b[0] && o <= b[1];
}
const bands = computed(() => {
  const out = BANDS.map((b) => ({ label: b[2], rows: shownRecipes.value.filter((x) => inBand(x, b)) }));
  // 分箱数与总数对不上就是逻辑漏了：四箱盖不住的进"技能档位没标出来"，不静默吞条目
  const rest = shownRecipes.value.filter((x) => !BANDS.some((b) => inBand(x, b)));
  if (rest.length) out.push({ label: '技能档位没标出来', rows: rest });
  return out;
});
</script>
