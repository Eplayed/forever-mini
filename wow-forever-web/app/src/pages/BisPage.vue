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
    </div>

    <!-- 职业条：一格一个职业，带职业图标与本套数（10-17 站主实拍：原来只有文字，认不出） -->
    <div class="pzrail">
      <button v-for="c in classes" :key="c.cls" type="button" class="pztab"
              :class="{ on: cls === c.cls }" @click="pickClass(c.cls)">
        <IconCell :icon-key="clsIcon(c.cls)" :seed="c.cls" :cn="c.clsCn" small />
        <span class="pztab-n">{{ c.clsCn }}</span><span class="pztab-c mono">{{ c.sets.length }}</span>
      </button>
    </div>

    <div class="card" v-if="cur">
      <div class="bhead">
        <h2 class="bt">{{ cur.clsCn }} · {{ cur.mode }}</h2>
        <span class="bn">{{ doll.length }} 个部位 · 点任意一个看这个部位还能换什么</span>
      </div>
      <div class="pz-picks">
        <div class="picks pz-mode">
          <button v-for="s in classSets" :key="s.id" type="button" class="pick"
                  :class="{ on: setId === s.id }" @click="pickSet(s.id)"><b>{{ s.mode }}</b></button>
        </div>
        <!-- 阵营：带徽记（本地 art/factions/*.png，与种族页同一套素材） -->
        <div class="picks pz-fac" role="group" aria-label="阵营">
          <button v-for="f in FACS" :key="f[0]" type="button" class="pick fac"
                  :class="{ on: fac === f[0] }" @click="pickFac(f[0])">
            <img v-if="emb(f[0]) && !embBad" class="femb" :src="assetUrl(emb(f[0]))" alt="" loading="lazy" @error="embBad = true">
            <b>{{ f[1] }}</b></button>
        </div>
      </div>

      <!-- 纸娃娃：左列 / 中间职业原画 / 右列，武器与远程压在中间那一列下面。
           布局照参考站那页的三栏（实测它是 471 / 360 / 471）。中间放的是职业原画，
           不是人物模型——本站没有 3D 素材，也不拿别的图冒充"穿上身的样子"。 -->
      <div class="pz-three">
        <div class="pzcol">
          <BisCell v-for="c in colLeft" :key="c.slot + '-' + c.cell" :cell="c"
                   :on="sel === c.slot" @pick="sel = $event" />
        </div>
        <div class="pzmid">
          <div class="pzart" :style="artStyle">
            <span class="pzart-tag mono">{{ cur.clsCn }} · {{ cur.level }} 级</span>
          </div>
          <div class="pzrow">
            <BisCell v-for="c in colBottom" :key="c.slot + '-' + c.cell" :cell="c"
                     :on="sel === c.slot" @pick="sel = $event" />
          </div>
        </div>
        <div class="pzcol">
          <BisCell v-for="c in colRight" :key="c.slot + '-' + c.cell" :cell="c"
                   :on="sel === c.slot" @pick="sel = $event" />
        </div>
      </div>

      <!-- 属性合计：纯把这套装备的属性行相加，不含职业与种族基础值、不含附魔与套装效果。
           参考站那一页还叠了基础属性，那套值我们没有，所以这里只算装备给的。 -->
      <div class="pzsum">
        <div class="pzsum-h"><b>这套装备给的属性</b><span class="dim">只把上面这些装备的属性行相加：不含职业与种族的基础值，也不含附魔和套装效果</span></div>
        <div class="pzsum-i">
          <span v-for="k in SUM_KEYS" :key="k" v-show="sum[k]"><b class="mono">{{ sum[k] }}</b>{{ k }}</span>
        </div>
      </div>
    </div>

    <div class="card" v-if="cur">
      <h2>{{ sel }}：这一套选的是它，往下是同部位备选</h2>
      <div class="boardwrap">
        <table class="board pztab-t" id="pzalts">
          <colgroup><col class="c-ico"><col style="width:26%"><col class="c-num"><col class="c-num"><col></colgroup>
          <thead><tr><th class="c-ico">图标</th><th>装备</th><th class="c-num">装等</th>
            <th class="c-num">需要等级</th><th class="w-tail">从哪儿拿</th></tr></thead>
          <tbody>
            <tr v-for="(x, i) in altRows" :key="x.item + '-' + i" :class="{ cur: i === 0 }">
              <td class="c-ico"><span class="qbox" :class="'bq' + (qo(x.item) || 0)"><IconCell :icon-key="ic(x.item)" :seed="x.item" :cn="nm(x.item)" small /></span></td>
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
   在抓取阶段就没落盘，这里也就无从渲染（红线：不复制描述文案、掉落不写百分比）。
   10-17 站主实拍后补的：职业条要带职业图标、阵营要带徽记、纸娃娃要照参考站那样
   左右两列夹着中间一块，而不是我们原来那个三列小方格。 */
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { loadAll, assetUrl } from '../lib/data.js';
import { artOf } from '../lib/art.js';
import IconCell from '../components/IconCell.vue';
import BisCell from '../components/BisCell.vue';

const FACS = [['alliance', '联盟'], ['horde', '部落']];
/* 纸娃娃三栏的部位归属（16 种标签实测枚举，见 docs/VERIFY-bis-2026-10-16.md） */
const COL_LEFT = ['头部', '项链', '肩部', '背部', '胸部', '手腕'];
const COL_BOTTOM = ['主手', '副手', '远程', '圣物'];
const SUM_KEYS = ['力量', '敏捷', '耐力', '智力', '精神', '护甲'];
const P = ref(null);
const err = ref('');
const embBad = ref(false);
const route = useRoute();
const router = useRouter();
const cls = ref(String(route.query.c || 'warrior'));
const setId = ref(String(route.query.s || ''));
const fac = ref(route.query.f === 'horde' ? 'horde' : 'alliance');
const sel = ref('头部');

function boot() {
  err.value = '';
  loadAll(['data/bis.json', 'data/items.json', 'data/items-detail.json', 'data/professions.json',
           'data/dungeons.json', 'data/classes.json', 'data/art.json'])
    .then((r) => {
      const byId = {};
      (r[1].items || []).forEach((x) => { byId[x.id] = x; });
      const prof = {};
      (r[3].professions || []).forEach((x) => { prof[x.id] = x.nameCn; });
      const dun = {};
      ['newDungeons', 'classicDungeons', 'raids'].forEach((k) => {
        (r[4][k] || []).forEach((x) => { dun[x.id] = x.nameCn; });
      });
      const cicon = {};
      (r[5].classes || []).forEach((x) => { cicon[x.id] = x.iconKey; });
      P.value = { bis: r[0], byId: byId, det: r[2].items || {}, prof: prof, dun: dun,
                  clsIcon: cicon, art: r[6] || {} };
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
/* 纸娃娃的三栏归属。两枚戒指与两个饰品同名，靠数据里的 cell 序号区分 */
const cells = computed(() => doll.value.map((c) => ({
  slot: c.slot, cell: c.cell, item: c.item, name: nm(c.item), iconKey: ic(c.item),
  quality: qo(c.item), ilvl: it(c.item).ilvl == null ? '' : it(c.item).ilvl
})));
const colLeft = computed(() => cells.value.filter((c) => COL_LEFT.indexOf(c.slot) >= 0));
const colBottom = computed(() => cells.value.filter((c) => COL_BOTTOM.indexOf(c.slot) >= 0));
const colRight = computed(() => cells.value.filter((c) =>
  COL_LEFT.indexOf(c.slot) < 0 && COL_BOTTOM.indexOf(c.slot) < 0));
/* 参考站的部位键（head/neck…）与纸娃娃上的中文标签（项链/戒指…）不是一套词，这里做一次桥 */
const KEY_CN = { head: '头部', neck: '项链', shoulder: '肩部', back: '背部', chest: '胸部',
  wrist: '手腕', hands: '手', waist: '腰部', legs: '腿部', feet: '脚', finger: '戒指',
  trinket: '饰品', 'main-hand': '主手', 'off-hand': '副手', 'two-hand': '双手武器',
  shield: '副手：盾牌', held: '副手：手持物品', ranged: '远程', relic: '圣物' };
const selKey = computed(() => {
  const k = Object.keys(KEY_CN).filter((x) => KEY_CN[x] === sel.value)[0];
  return k || sel.value;
});
const altRows = computed(() => {
  const a = (((cur.value || {}).alts || {})[fac.value] || {})[selKey.value] || [];
  return a.map((i) => ({ item: i }));
});
const enchRows = computed(() => (((cur.value || {}).enchants || {})[fac.value] || []));
const consRows = computed(() => (((cur.value || {}).consumables || {})[fac.value] || []));
const artStyle = computed(() => {
  const u = artOf((P.value || {}).art, 'classes', (cur.value || {}).cls || '');
  return u ? { backgroundImage: 'url(' + assetUrl(u) + ')' } : {};
});
/* 属性合计：把这套装备的属性行相加。两种护甲写法（"173点护甲" / "护甲值 173"）都收进护甲，
   "+N 护甲加成" 是另一回事，不并进护甲；效果句（装备：…）不参与。 */
const sum = computed(() => {
  const out = {};
  doll.value.forEach((c) => {
    const lines = (((P.value || {}).det || {})[String(c.item)] || {}).st || [];
    lines.forEach((l) => {
      const s = String(l).trim();
      let m = /^\+\s*(\d+)\s*(力量|敏捷|耐力|智力|精神)$/.exec(s);
      if (m) { out[m[2]] = (out[m[2]] || 0) + Number(m[1]); return; }
      m = /^(\d+)\s*点护甲$/.exec(s) || /^护甲值\s*(\d+)$/.exec(s);
      if (m) out['护甲'] = (out['护甲'] || 0) + Number(m[1]);
    });
  });
  return out;
});

function pickClass(v) {
  cls.value = v;
  const first = (classes.value.filter((c) => c.cls === v)[0] || {}).sets || [];
  setId.value = first.length ? first[0].id : '';
  sel.value = '头部';
  sync();
}
function pickSet(v) { setId.value = v; sync(); }
function pickFac(v) { fac.value = v; sync(); }
function sync() {
  router.replace({ path: '/bis', query: { c: cls.value, s: setId.value, f: fac.value } });
}

const emb = (f) => artOf((P.value || {}).art, 'factions', f);
const clsIcon = (c) => ((P.value || {}).clsIcon || {})[c] || '';
const it = (id) => ((P.value || {}).byId || {})[id] || {};
function nm(id) { return it(id).name || ''; }
function ic(id) { return it(id).iconKey || ''; }
function qo(id) { return it(id).quality; }
function il(id) { const v = it(id).ilvl; return v == null ? '' : String(v); }
function rl(id) { const v = it(id).rlvl; return v == null ? '' : String(v); }
/* 属性行取本站 items-detail 的 st，只列前两条数值行，多的去物品库那页看详情 */
function stOf(id) {
  const st = (((P.value || {}).det || {})[String(id)] || {}).st || [];
  return st.filter((x) => x && x.indexOf('使用') < 0 && x.indexOf('装备：') < 0).slice(0, 2).join('，');
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
/* 页头那排读数：数字与单位之间要留缝（模板里 </b>套 两个节点之间的空白会被编译压缩，
   只能靠 CSS 撑），读数之间留大间隔。这条在 10-17 改版时被我整块删过一次，
   结果五个数糊成一行"38套9个职业30级这一档"——删样式前先看它管着什么。 */
.pz-read { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 10px 0 2px; font-size: 13px; color: var(--txt-dim) }
.pz-read b { color: var(--txt-title); font-size: 15px; margin-right: 4px }
/* 职业条：一格一个职业，图标 + 名字 + 本职业套数（参考站那条也是带图标的） */
.pzrail { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 14px }
.pztab { display: flex; align-items: center; gap: 7px; min-height: 44px; padding: 0 12px;
  background: var(--bg-1); border: 1px solid var(--line-2); border-radius: 5px;
  color: var(--txt); cursor: pointer; font-size: 13.5px }
.pztab:hover { border-color: var(--gold-deep) }
.pztab.on { border-color: var(--gold); background: var(--bg-2); color: var(--txt-title); font-weight: 600 }
.pztab-c { font-size: 11.5px; color: var(--txt-muted) }
.pz-picks { display: flex; flex-wrap: wrap; gap: 10px 18px; align-items: center; margin: 12px 0 14px }
.pz-mode, .pz-fac { margin: 0 }
.pz-fac .fac { display: flex; align-items: center; gap: 6px }
.femb { width: 20px; height: 24px; object-fit: contain }
/* 三栏纸娃娃：左列 / 中间原画 + 武器行 / 右列（参考站实测是 471 | 360 | 471） */
.pz-three { display: grid; grid-template-columns: 1fr minmax(240px, 330px) 1fr; gap: 12px; align-items: start }
.pzcol { display: flex; flex-direction: column; gap: 7px }
.pzmid { display: flex; flex-direction: column; gap: 7px }
.pzart { height: 300px; border-radius: 6px; border: 1px solid var(--line-2);
  background-size: cover; background-position: center 22%; background-color: var(--bg-2);
  position: relative; overflow: hidden }
.pzart-tag { position: absolute; left: 8px; bottom: 7px; font-size: 11.5px;
  background: rgba(8, 10, 14, .72); color: var(--txt-dim); padding: 2px 7px; border-radius: 3px }
.pzrow { display: grid; grid-template-columns: repeat(2, 1fr); gap: 7px }
/* 图标按品质描边（备选表里也用这套；纸娃娃那一套在 BisCell.vue 里） */
.qbox { display: inline-flex; border: 1px solid var(--line-2); border-radius: 4px; padding: 1px }
.qbox.bq2 { border-color: rgba(51, 167, 51, .6) }
.qbox.bq3 { border-color: rgba(74, 130, 224, .65) }
.qbox.bq4 { border-color: rgba(163, 105, 217, .65) }
.qbox.bq5 { border-color: rgba(201, 162, 74, .7) }
.pzsum { margin-top: 14px; border-top: 1px solid var(--line-2); padding-top: 11px }
.pzsum-h { display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: baseline; margin-bottom: 8px }
.pzsum-h b { font-size: 13.5px; color: var(--txt-title) }
.pzsum-h .dim { font-size: 11.5px }
.pzsum-i { display: flex; flex-wrap: wrap; gap: 6px 20px; font-size: 13px; color: var(--txt-dim) }
.pzsum-i b { color: var(--ok); font-size: 15px; margin-right: 4px }
.pztab-t tr.cur { background: rgba(201, 162, 74, .07) }
.pz-two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: start }
@media (max-width: 899px) {
  .pz-three { grid-template-columns: 1fr }
  .pzart { height: 190px }
  .pz-two { grid-template-columns: 1fr }
  .pztab { flex: 1 1 auto; justify-content: center }
}
</style>
