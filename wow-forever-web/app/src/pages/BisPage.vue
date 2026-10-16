<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="P">
    <!-- 页头：口径这一句是红线要求的（2026-10-16 例外条款第 ② 条），不许删也不许改措辞方向 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">{{ meta.title }}</h1></div>
      <p class="note">这份名单由本站整理自第三方资料，不是官方结论，也没做模拟计算。
        每件装备的名字、装等、属性与图标都回本站物品库查，点装备名可以跳过去看详情。</p>
      <div class="pz-read">
        <span><b class="mono">{{ sets.length }}</b>套</span>
        <span><b class="mono">{{ meta.counts.classes }}</b>个职业</span>
        <span><b class="mono">{{ meta.level }}</b>级这一档</span>
        <span><b class="mono">{{ meta.counts.items }}</b>件装备</span>
        <span><b class="mono">{{ meta.counts.altRows }}</b>条同部位备选</span>
      </div>
      <div class="picks pz-cls">
        <button v-for="c in classes" :key="c.cls" type="button" class="pick"
                :class="{ on: cls === c.cls }" @click="pickClass(c.cls)">
          <b>{{ c.clsCn }}</b><span class="dim mono">{{ c.sets.length }}</span></button>
      </div>
    </div>

    <div class="card" v-if="cur">
      <div class="bhead">
        <h2 class="bt">{{ cur.clsCn }} · {{ cur.mode }}</h2>
        <span class="bn">{{ doll.length }} 个部位 · 点任意一个看这个部位还能换什么</span>
      </div>
      <div class="picks pz-mode">
        <button v-for="s in classSets" :key="s.id" type="button" class="pick"
                :class="{ on: setId === s.id }" @click="setId = s.id"><b>{{ s.mode }}</b></button>
        <span class="pz-sep"></span>
        <button v-for="f in FACS" :key="f[0]" type="button" class="pick"
                :class="{ on: fac === f[0] }" @click="fac = f[0]"><b>{{ f[1] }}</b></button>
      </div>

      <div class="pz-two">
        <!-- 2D 纸娃娃：站主 2026-10-16 定的呈现方式（3D 人物没有素材来源，见 docs/EVAL-bis-2026-10-16.md） -->
        <div class="pzdoll" role="group" aria-label="各部位首选装备">
          <button v-for="c in doll" :key="c.slot + '-' + c.cell" type="button" class="pzcell"
                  :class="{ on: sel === c.slot }" @click="sel = c.slot">
            <IconCell :icon-key="ic(c.item)" :seed="c.item" :cn="nm(c.item)" small />
            <span class="pzslot">{{ c.slot }}</span>
            <b class="pzname" :class="'q' + (qo(c.item) || 0)">{{ nm(c.item) }}</b>
            <span class="pzil mono">{{ il(c.item) }}</span>
          </button>
        </div>

        <div class="pzside">
          <h3>{{ sel }}：这一套选的是它，往下是同部位备选</h3>
          <div class="boardwrap">
            <table class="board pztab" id="pzalts">
              <colgroup><col class="c-ico"><col style="width:26%"><col class="c-num"><col class="c-num"><col></colgroup>
              <thead><tr><th class="c-ico">图标</th><th>装备</th><th class="c-num">装等</th>
                <th class="c-num">需要等级</th><th class="w-tail">从哪儿拿</th></tr></thead>
              <tbody>
                <tr v-for="(x, i) in altRows" :key="x.item + '-' + i" :class="{ cur: i === 0 }">
                  <td class="c-ico"><IconCell :icon-key="ic(x.item)" :seed="x.item" :cn="nm(x.item)" small /></td>
                  <td><span class="nm" :class="'q' + (qo(x.item) || 0)">{{ nm(x.item) }}</span>
                    <span v-if="i === 0" class="tag">这套选的</span>
                    <span class="sub" v-if="stOf(x.item)">{{ stOf(x.item) }}</span></td>
                  <td class="c-num num">{{ il(x.item) }}</td>
                  <td class="c-num num">{{ rl(x.item) }}</td>
                  <td class="w-tail dim">{{ srcOf(x.item) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!altRows.length" class="empty">这个部位这一套没列备选。</div>
        </div>
      </div>
    </div>

    <div class="card" v-if="cur">
      <h2>这一套还列了附魔与消耗品</h2>
      <div class="pz-two">
        <div>
          <h3>附魔 · {{ enchRows.length }} 条</h3>
          <div class="boardwrap">
            <table class="board">
              <colgroup><col class="c-ico"><col style="width:30%"><col style="width:22%"><col></colgroup>
              <thead><tr><th class="c-ico">附魔</th><th>贴在哪个部位</th><th class="c-num">附魔技能</th><th class="w-tail">附魔物品</th></tr></thead>
              <tbody>
                <tr v-for="(x, i) in enchRows" :key="x.item + '-' + i">
                  <td class="c-ico"><IconCell :icon-key="ic(x.item)" :seed="x.item" :cn="nm(x.item)" small /></td>
                  <td>{{ (x.slots || []).join('、') || '—' }}</td>
                  <td class="c-num num">{{ x.skill == null ? '' : x.skill }}</td>
                  <td class="w-tail"><span class="nm" :class="'q' + (qo(x.item) || 0)">{{ nm(x.item) }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3>消耗品 · {{ consRows.length }} 件</h3>
          <div class="boardwrap">
            <table class="board">
              <colgroup><col class="c-ico"><col style="width:38%"><col></colgroup>
              <thead><tr><th class="c-ico">物品</th><th>名称</th><th class="w-tail">从哪儿拿</th></tr></thead>
              <tbody>
                <tr v-for="(x, i) in consRows" :key="x + '-' + i">
                  <td class="c-ico"><IconCell :icon-key="ic(x)" :seed="x" :cn="nm(x)" small /></td>
                  <td><span class="nm" :class="'q' + (qo(x) || 0)">{{ nm(x) }}</span></td>
                  <td class="w-tail dim">{{ srcOf(x) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <p class="note">附魔与消耗品是这一套列的清单，本站没有第二处可以核对，也没实测过；
        配方要什么材料、做出来要多少技能点，点上面的物品名去物品库那一页看。</p>
    </div>
  </template>
</template>

<script setup>
/* 配装页（2026-10-16 站主拍板走 C 方案：照参考站做名单 + 同部位可换）。
   数据只有一件事是新的：bis.json 里"哪件装备在哪个部位、按什么顺序"。
   名字 / 装等 / 需要等级 / 属性行 / 图标全部回 items.json 与 items-detail.json 现查——
   同一件装备的数在两处各存一份必然会飘，这是本站一直守的那条。
   参考站那一栏的中文句子（为什么这件好、掉率约 X%、按本页权重比第二件高 N%）
   在抓取阶段就没落盘，这里也就无从渲染（红线：不复制描述文案、掉落不写百分比）。 */
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { loadAll } from '../lib/data.js';
import IconCell from '../components/IconCell.vue';

const FACS = [['alliance', '联盟'], ['horde', '部落']];
const P = ref(null);
const err = ref('');
const route = useRoute();
const router = useRouter();
const cls = ref(String(route.query.c || 'warrior'));
const setId = ref(String(route.query.s || ''));
const fac = ref(route.query.f === 'horde' ? 'horde' : 'alliance');
const sel = ref('头部');

function boot() {
  err.value = '';
  loadAll(['data/bis.json', 'data/items.json', 'data/items-detail.json',
           'data/professions.json', 'data/dungeons.json'])
    .then((r) => {
      const byId = {};
      (r[1].items || []).forEach((x) => { byId[x.id] = x; });
      const prof = {};
      (r[3].professions || r[3].rows || []).forEach((x) => {
        prof[x.id || x.slug] = x.nameCn || x.cn;
      });
      const dun = {};
      ['newDungeons', 'classicDungeons', 'raids'].forEach((k) => {
        (r[4][k] || []).forEach((x) => { dun[x.id] = x.nameCn; });
      });
      P.value = { bis: r[0], byId: byId, det: r[2].items || {}, prof: prof, dun: dun };
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);

const meta = computed(() => ((P.value || {}).bis || {}).meta || { counts: {} });
const sets = computed(() => ((P.value || {}).bis || {}).sets || []);
const classes = computed(() => {
  const out = [];
  sets.value.forEach((s) => {
    let c = out.filter((x) => x.cls === s.cls)[0];
    if (!c) { c = { cls: s.cls, clsCn: s.clsCn, sets: [] }; out.push(c); }
    c.sets.push(s);
  });
  return out;
});
const classSets = computed(() => (classes.value.filter((c) => c.cls === cls.value)[0] || {}).sets || []);
const cur = computed(() => classSets.value.filter((s) => s.id === setId.value)[0]
  || classSets.value[0] || null);
const doll = computed(() => ((cur.value || {}).doll || {})[fac.value] || []);
const altRows = computed(() => {
  const a = (((cur.value || {}).alts || {})[fac.value] || {})[selKey.value] || [];
  return a.map((i) => ({ item: i }));
});
/* 纸娃娃上的中文部位名（"项链"）与名单分区的键（"neck"）不是一套词，这里做一次桥。 */
const KEY_CN = { head: '头部', neck: '项链', shoulder: '肩部', back: '背部', chest: '胸部',
  wrist: '手腕', hands: '手', waist: '腰部', legs: '腿部', feet: '脚', finger: '戒指',
  trinket: '饰品', 'main-hand': '主手', 'off-hand': '副手', 'two-hand': '双手武器',
  shield: '副手：盾牌', held: '副手：手持物品', ranged: '远程', relic: '圣物' };
const selKey = computed(() => {
  const k = Object.keys(KEY_CN).filter((x) => KEY_CN[x] === sel.value)[0];
  return k || sel.value;
});
const enchRows = computed(() => (((cur.value || {}).enchants || {})[fac.value] || []));
const consRows = computed(() => (((cur.value || {}).consumables || {})[fac.value] || []));

function pickClass(v) {
  cls.value = v;
  const first = (classes.value.filter((c) => c.cls === v)[0] || {}).sets || [];
  setId.value = first.length ? first[0].id : '';
  sel.value = '头部';
  router.replace({ path: '/bis', query: { c: v, s: setId.value, f: fac.value } });
}

const it = (id) => ((P.value || {}).byId || {})[id] || {};
function nm(id) { return it(id).name || ''; }
function ic(id) { return it(id).iconKey || ''; }
function qo(id) { return it(id).quality; }
function il(id) { const v = it(id).ilvl; return v == null ? '' : String(v); }
function rl(id) { const v = it(id).rlvl; return v == null ? '' : String(v); }
/* 属性行取本站 items-detail 的 st（第一件装备的属性行往往就是它值不值得换的理由），
   只列前两条，多的去物品库那页看详情。 */
function stOf(id) {
  const st = (((P.value || {}).det || {})[String(id)] || {}).st || [];
  return st.filter((x) => x && x.indexOf('使用') < 0).slice(0, 2).join('，');
}
function srcOf(id) {
  const s = cur.value;
  if (!s) return '';
  const r = ((s.refs || {})[fac.value] || {})[String(id)];
  if (!r) return '';
  const out = [];
  (r.refs || []).forEach((x) => {
    if (x.kind === 'recipe') out.push(((P.value || {}).prof || {})[x.prof] || x.prof);
    else if (x.kind === 'dungeon') out.push('副本：' + (((P.value || {}).dun || {})[x.id] || x.id));
    else if (x.kind === 'quest') out.push('任务奖励');
    else if (x.kind === 'vendor') out.push('商人出售');
    else if (x.kind === 'item') out.push('需要：' + (nm(x.id) || ('#' + x.id)));
  });
  if (r.skill != null && out.length) out[0] = out[0] + '（' + r.skill + '）';
  const seen = {};
  return out.filter((x) => { if (seen[x]) return false; seen[x] = true; return true; }).join('，');
}
</script>

<style scoped>
/* 纸娃娃与右侧备选表并排；窄屏整块换到一列（与全站 899px 断点一致） */
.pz-two { display: grid; grid-template-columns: 300px 1fr; gap: 14px; align-items: start }
.pz-read { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 10px 0 2px; font-size: 13px; color: var(--txt-dim) }
.pz-read b { color: var(--txt-title); font-size: 15px; margin-right: 3px }
.pz-cls { margin-top: 6px }
.pz-mode { margin: 12px 0 14px }
.pz-sep { width: 1px; align-self: stretch; background: var(--line-2); margin: 0 6px }
.pzdoll { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px }
.pzcell { display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  background: var(--bg-2); border: 1px solid var(--line-2); border-radius: 5px;
  padding: 7px 8px; text-align: left; cursor: pointer; min-height: 84px }
.pzcell:hover { border-color: var(--gold-deep) }
.pzcell.on { border-color: var(--gold); box-shadow: inset 0 0 0 1px var(--gold-deep) }
.pzslot { font-size: 11px; color: var(--txt-muted) }
.pzname { font-size: 12.5px; line-height: 1.35; font-weight: 600 }
.pzil { font-size: 11px; color: var(--txt-dim) }
.pzside h3 { margin: 0 0 9px; font-size: 14px }
.pztab tr.cur { background: rgba(201, 162, 74, .07) }
@media (max-width: 899px) {
  .pz-two { grid-template-columns: 1fr }
  .pzdoll { grid-template-columns: repeat(2, 1fr) }
  .pzcell { min-height: 76px }
}
</style>
