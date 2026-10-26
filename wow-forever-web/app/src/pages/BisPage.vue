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
        <span class="bn">{{ doll.length }} 个部位 · 点任意一个看这个部位还能换什么
          · 这份名单 <span class="mono">{{ cur.fetched }}</span> 对着来源核过</span>
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
           布局照参考站那页的三栏（实测它是 471 / 360 / 471）。中间默认是职业原画；
           2026-10-26 起可以点开换成 3D——那一层现在是本站自己拼的**占位模型**，
           不是游戏里的样子（游戏模型要等客户端那一层能取到文件，见 docs/EVAL-bis更新与3D模型-2026-10-26.md）。 -->
      <div class="pz-three">
        <div class="pzcol">
          <BisCell v-for="c in colLeft" :key="c.slot + '-' + c.cell" :cell="c"
                   :on="sel === c.slot" @pick="open" />
        </div>
        <div class="pzmid">
          <div class="pzart" :style="artStyle">
            <ModelViewer v-if="modelFile && live3d" :src="assetUrl(modelFile)" :gear="gearQ"
                         :height="300" @fail="glWhy = $event" />
            <span class="pzart-tag mono">{{ cur.clsCn }} · {{ cur.level }} 级</span>
            <button v-if="modelFile" type="button" class="pz-3dbtn"
                    :aria-pressed="live3d ? 'true' : 'false'" @click="toggle3d">{{ live3d ? '返回图片' : '旋转 3D 模型' }}</button>
          </div>
          <!-- 说明压在图下面而不是浮在图上：浮着会把模型本身盖掉一半，
               而"看效果"要看的正是模型。这两句一句都不许省（红线：不冒充）。 -->
          <p v-if="live3d && !glWhy" class="pz-3dnote">这一版是本站自己拼的<b>占位模型</b>，不是游戏里的样子：
            一件一块，颜色跟品质走，这一套没穿的部位就不画。真模型要等客户端那一层能取到文件。</p>
          <p v-if="glWhy" class="pz-3dnote">{{ glWhy }}，这一栏退回静态原画。</p>
          <p v-if="live3d && unmappedSlots.length" class="pz-3dnote">这几个部位占位模型里没有格子：
            {{ unmappedSlots.join('、') }}（不硬塞到别的块上冒充）。</p>
          <div class="pzrow">
            <BisCell v-for="c in colBottom" :key="c.slot + '-' + c.cell" :cell="c"
                     :on="sel === c.slot" @pick="open" />
          </div>
        </div>
        <div class="pzcol">
          <BisCell v-for="c in colRight" :key="c.slot + '-' + c.cell" :cell="c"
                   :on="sel === c.slot" @pick="open" />
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
      <div class="bhead">
        <h2 class="bt">这一套一览</h2>
        <span class="bn">{{ overview.length }} 个部位 · 点一行看这个部位还能换什么</span>
      </div>
      <div class="boardwrap">
        <table class="board" id="pzover">
          <colgroup><col style="width:11%"><col class="c-ico"><col style="width:28%"><col class="c-num"><col class="c-num"><col></colgroup>
          <thead><tr><th>部位</th><th class="c-ico">图标</th><th>这一套选的</th>
            <th class="c-num">装等</th><th class="c-num">可换</th><th class="w-tail">从哪儿拿</th></tr></thead>
          <tbody>
            <tr v-for="x in overview" :key="x.slot + '-' + x.cell" class="pzrow2" @click="open(x.slot, $event.currentTarget)">
              <td><button type="button" class="pzlink">{{ x.slot }}<span v-if="x.cell > 1" class="mono"> · {{ x.cell }}</span></button></td>
              <td class="c-ico"><span class="qbox" :class="'bq' + (x.quality || 0)"><IconCell :icon-key="x.iconKey" :seed="x.item" :cn="x.name" small /></span></td>
              <td><span class="nm" :class="'q' + (x.quality || 0)">{{ x.name }}</span>
                <span class="sub" v-if="x.st">{{ x.st }}</span></td>
              <td class="c-num num">{{ x.ilvl }}</td>
              <td class="c-num num">{{ x.n }}</td>
              <td class="w-tail dim">{{ x.src }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card" v-if="cur && cmpRows.length">
      <div class="bhead">
        <h2 class="bt">两家怎么说</h2>
        <span class="bn">{{ cmpStat.same }} 格一致 · {{ cmpStat.diff }} 格分歧 ·
          {{ cmpStat.none }} 格另一家没单列</span>
      </div>
      <div class="boardwrap">
        <table class="board" id="pzcmp">
          <colgroup><col style="width:11%"><col><col><col style="width:12%"></colgroup>
          <thead><tr><th>部位</th><th>本站这一套用的</th><th>另一家列的第一件</th><th class="c-num">两家</th></tr></thead>
          <tbody>
            <tr v-for="x in cmpRows" :key="x.slot + '-' + x.cell">
              <td>{{ x.slot }}<span v-if="x.cell > 1" class="mono"> · {{ x.cell }}</span></td>
              <td data-l="本站用的"><span class="qbox" :class="'bq' + (x.quality || 0)"><IconCell :icon-key="x.iconKey" :seed="x.item" :cn="x.name" small /></span>
                <span class="nm" :class="'q' + (x.quality || 0)">{{ x.name }}</span>
                <span class="mono dim" v-if="x.ilvl !== ''"> {{ x.ilvl }}</span></td>
              <td data-l="另一家">
                <template v-if="x.theirs == null"><span class="dim">这一格另一家没单列</span></template>
                <template v-else-if="!x.known"><span class="dim mono">#{{ x.theirs }}</span>
                  <span class="dim">· 本站名录里没有这一件</span></template>
                <template v-else>
                  <span class="qbox" :class="'bq' + (x.tQuality || 0)"><IconCell :icon-key="x.tIcon" :seed="x.theirs" :cn="x.tName" small /></span>
                  <span class="nm" :class="'q' + (x.tQuality || 0)">{{ x.tName }}</span>
                  <span class="mono dim" v-if="x.tIlvl !== ''"> {{ x.tIlvl }}</span>
                  <span class="sub" v-if="x.moreNames.length">这一格还列了：{{ x.moreNames.join('、') }}</span>
                </template>
              </td>
              <td class="c-num"><span class="tag" :class="'cmp-' + x.state">{{ CMP_CN[x.state] }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="note">第二份是插件 XR_DungeonGuide 里的配装数据（作者 血染，文件里声明抓自
        foreverchanges.pro/zh-cn/bis，本站 {{ meta.alt.fetched }} 从插件文件里提出来的）。
        两张名单只是并列摆出来，本站不裁决哪件更好，页面用的那一件和顺序仍以主源为准。
        两边件数差得多（一致 {{ meta.alt.counts.same }} / 分歧 {{ meta.alt.counts.diff }}，
        共 {{ meta.alt.counts.slots }} 格），但专精清单 38 对 38 一一对上、连冷门组合同进同出，
        我们没法确认这两份不是从同一个地方抄来的两份转述——所以配装线仍是 L1，不因"有两家"升档。
        装备名与装等一律回本站物品库查，对面写法不同的地方（{{ meta.alt.counts.nameDiffRows }} 处）
        不在这张表里另列。</p>
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

    <!-- 备选 popover：站主 2026-10-17 改口径——不要 modal 弹窗，要贴着点的那一格弹出来。
         纸娃娃那一格与下面一览表的那一行开同一个 popover，anchor 传的是被点的元素。 -->
    <BisPop v-if="pick" :slot="pick" :rows="pickerRows" :head="pickerHead"
            :anchor="anchorEl" @close="pick = ''" />
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
import { sumStatLines } from '../lib/item-stats.js';
import IconCell from '../components/IconCell.vue';
import BisCell from '../components/BisCell.vue';
import BisPop from '../components/BisPop.vue';
import ModelViewer from '../components/ModelViewer.vue';
import { gearNodes } from '../lib/bis-model.js';

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
const pick = ref('');


/* 备选 popover：记着"贴着谁弹"。ESC 与点外面由 BisPop 自己收，
   这里只负责换职业/换套/换阵营时把它关掉——不然 anchor 换了、内容也换了，
   浮层还停在旧位置指着上一格。 */
const anchorEl = ref(null);
function open(slot, el) { sel.value = slot; pick.value = slot; anchorEl.value = el || null; }
function closePop() { pick.value = ''; anchorEl.value = null; }

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
function keyOf(label) {
  const k = Object.keys(KEY_CN).filter((x) => KEY_CN[x] === label)[0];
  return k || label;
}
/* 纸娃娃上只有"主手/副手"两格，可名单里双手武器、盾牌、手持物品是分开的节，
   所以一个标签可能对应好几个键，按顺序找第一个有内容的。 */
const SIB = { '主手': ['main-hand', 'two-hand'], '副手': ['off-hand', 'shield', 'held'] };
function altsFor(label) {
  const all = ((cur.value || {}).alts || {})[fac.value] || {};
  const keys = SIB[label] || [keyOf(label)];
  for (let i = 0; i < keys.length; i++) { if ((all[keys[i]] || []).length) return all[keys[i]]; }
  return [];
}
const altRows = computed(() => altsFor(sel.value).map((i) => ({ item: i })));
/* 一览表的每一行：这一套的每个部位 + 它选的那件 + 这个部位一共列了几件可换 */
const overview = computed(() => cells.value.map((c) => ({
  slot: c.slot, cell: c.cell, item: c.item, name: c.name, iconKey: c.iconKey,
  quality: c.quality, ilvl: c.ilvl, st: stOf(c.item), src: srcOf(c.item),
  n: altsFor(c.slot).length
})));
const pickerRows = computed(() => altRows.value.map((x) => ({
  item: x.item, name: nm(x.item), iconKey: ic(x.item), quality: qo(x.item),
  ilvl: il(x.item), rlvl: rl(x.item), st: stOf(x.item), src: srcOf(x.item)
})));
const pickerHead = computed(() => {
  const c = cur.value;
  if (!c) return '';
  return c.clsCn + ' · ' + c.mode + ' · ' + (fac.value === 'horde' ? '部落' : '联盟')
    + ' · ' + c.level + ' 级';
});
/* 「两家怎么说」：第二份名单按 部位+序号 对到纸娃娃的每一格。
   必须带上 cell 序号——两枚戒指、两个饰品中文名相同，只按部位会串格。
   判定只有三种：一致 / 分歧 / 另一家没单列这一格（本站不裁决，也不替对面编名字）。 */
const CMP_CN = { same: '一致', diff: '分歧', none: '没列' };
const cmpRows = computed(() => {
  const list = (((cur.value || {}).alt || {})[fac.value] || []);
  return cells.value.map((c) => {
    const a = list.filter((x) => x.slot === c.slot && x.cell === c.cell)[0] || null;
    const t = a ? a.item : null;
    const known = t != null && !!(P.value || {}).byId[t];
    const more = (a ? a.top : []).filter((i) => i !== t && (P.value || {}).byId[i]);
    return {
      slot: c.slot, cell: c.cell, item: c.item, name: c.name, iconKey: c.iconKey,
      quality: c.quality, ilvl: c.ilvl,
      theirs: t, known: known, state: !a ? 'none' : (a.same ? 'same' : 'diff'),
      tName: t == null ? '' : nm(t), tIcon: ic(t), tQuality: qo(t), tIlvl: il(t),
      moreNames: more.slice(0, 3).map(nm)
    };
  });
});
const cmpStat = computed(() => {
  const n = { same: 0, diff: 0, none: 0 };
  cmpRows.value.forEach((r) => { n[r.state] += 1; });
  return n;
});
const enchRows = computed(() => (((cur.value || {}).enchants || {})[fac.value] || []));
const consRows = computed(() => (((cur.value || {}).consumables || {})[fac.value] || []));
const artStyle = computed(() => {
  const u = artOf((P.value || {}).art, 'classes', (cur.value || {}).cls || '');
  return u ? { backgroundImage: 'url(' + assetUrl(u) + ')' } : {};
});
/* ---- 3D：模型台账里没有文件就整个按钮不出现（不猜路径、不拿别的图冒充）---- */
const live3d = ref(false);
const glWhy = ref('');
function toggle3d() {
  live3d.value = !live3d.value;
  if (live3d.value) glWhy.value = '';
}
const modelFile = computed(() => {
  const M = ((P.value || {}).art || {}).bisModels || {};
  const f = ((M.items || [])[0] || {}).file || '';
  return M.origin === 'self-generated' && f ? f : '';
});
/* 节点名 → 品质：染色走 tokens.css 的 --q*，这一层只负责"哪件穿了、什么品质" */
const gearQ = computed(() => {
  const g = gearNodes(doll.value);
  const out = {};
  Object.keys(g).forEach((node) => {
    if (node === 'unmapped') return;
    out[node] = { slot: g[node].slot, item: g[node].item, quality: qo(g[node].item) };
  });
  return out;
});
const unmappedSlots = computed(() => (gearNodes(doll.value).unmapped || []));
/* 属性合计：把这套装备的属性行相加。解析在 lib/item-stats.js（可单测），
   基础护甲的三种写法都收，"+N 护甲" 与 "+N 护甲加成" 是加成不是基础护甲、不计，
   效果句与收藏计数行也不计——2026-10-19 那次就是漏了 "90 护甲" 这一种写法。 */
const sum = computed(() => sumStatLines(doll.value.map((c) => {
  return (((P.value || {}).det || {})[String(c.item)] || {}).st || [];
})));

function pickClass(v) {
  cls.value = v;
  const first = (classes.value.filter((c) => c.cls === v)[0] || {}).sets || [];
  setId.value = first.length ? first[0].id : '';
  sel.value = '头部';
  closePop();
  sync();
}
function pickSet(v) { setId.value = v; closePop(); sync(); }
function pickFac(v) { fac.value = v; closePop(); sync(); }
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
  background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 5px;
  color: var(--txt); cursor: pointer; font-size: 13.5px }
.pztab:hover { border-color: var(--gold-deep) }
.pztab.on { border-color: var(--gold); background: var(--panel); color: var(--txt-title); font-weight: 600 }
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
  background-size: cover; background-position: center 22%; background-color: var(--panel);
  position: relative; overflow: hidden }
.pzart-tag { position: absolute; left: 8px; bottom: 7px; font-size: 11.5px;
  background: rgba(8, 10, 14, .72); color: var(--txt-dim); padding: 2px 7px; border-radius: 3px }
/* 3D 那一层盖在原画上面：原画留着当降级面（加载失败或没有 WebGL 时它就露出来）。
   占位模型这件事必须写在界面上，不许让玩家拿它当"穿上身的样子"。 */
.pzart :deep(.pzc-glbox) { position: absolute; inset: 0; z-index: 2 }
.pz-3dbtn { position: absolute; right: 8px; top: 8px; z-index: 3; min-height: 34px;
  font: 600 12px var(--font-body); padding: 7px 12px; border-radius: 999px;
  background: rgba(8, 10, 14, .78); color: var(--txt); border: 1px solid var(--line-2); cursor: pointer }
.pz-3dbtn[aria-pressed="true"] { border-color: var(--gold); color: var(--gold) }
.pz-3dnote { margin: 0; font-size: 11.5px; line-height: 1.55; color: var(--txt-dim);
  background: var(--sunk); border: 1px solid var(--line); border-radius: 4px; padding: 6px 8px }
@media (max-width: 720px) {
  .pz-3dbtn { min-height: 44px; min-width: 44px }
}
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
/* 一览表整行可点开弹窗。行里那个"部位"渲染成 button 是为了键盘能 Tab 到，
   但点击热区是整行，所以 button 自己不带边框与内边距。 */
#pzover tbody tr.pzrow2 { cursor: pointer }
#pzover tbody tr.pzrow2:hover td { background: rgba(201, 162, 74, .05) }
.pzlink { background: none; border: 0; padding: 0; font: inherit; color: var(--txt-title);
  text-align: left; cursor: pointer }
.pzlink:hover { color: var(--gold) }
.pz-two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-items: start }
/* 「两家怎么说」：图标与名字挤在同一格，图标要压着基线走（一览表里图标独占一格，不需要这条）。
   判定角标：一致绿、分歧琥珀、没列灰——分歧不是错误，不许用红，也不许把某一家的名字加粗。 */
#pzcmp td .qbox { vertical-align: -7px; margin-right: 6px }
#pzcmp .tag.cmp-same { color: var(--ok); border-color: rgba(103, 194, 103, .45) }
#pzcmp .tag.cmp-diff { color: var(--warn); border-color: rgba(221, 159, 68, .45);
  background: rgba(221, 159, 68, .1) }
#pzcmp .tag.cmp-none { color: var(--txt-muted); border-color: var(--line-2); background: none }
#pzcmp td .tag { margin-left: 0 }
/* 375 下这张表必须竖起来：横滚的话「本站用的」和「另一家」永远看不到同一屏，
   而"两家并排"就是这张表唯一的作用（其余表横滚是列多、少看几列还能读，这张不行）。
   做法是整表 display:block、表头隐藏、列名靠 data-l 补在每行前面、判定角标钉在行首右侧。 */
@media (max-width: 899px) {
  #pzcmp { min-width: 0 }
  #pzcmp thead { display: none }
  #pzcmp, #pzcmp tbody, #pzcmp tr, #pzcmp td { display: block; width: auto }
  #pzcmp tr { position: relative; padding: 9px 0; border-bottom: 1px solid var(--line-2) }
  #pzcmp td { padding: 0; border: 0 }
  #pzcmp td:first-child { font-weight: 600; color: var(--txt-title); padding-right: 58px }
  #pzcmp td:nth-child(2), #pzcmp td:nth-child(3) { margin-top: 4px }
  #pzcmp td[data-l]::before { content: attr(data-l); font-size: 11.5px; color: var(--txt-muted);
    margin-right: 6px }
  #pzcmp td:nth-child(4) { position: absolute; right: 0; top: 9px }
}
#pzcmp .nm { white-space: normal }
/* grid 子项的 min-width 默认是 auto，会被里面那张 min-width:640px 的 .board 顶开——
   实测 375 下附魔与消耗品那两张 .boardwrap 变成 640 宽，连带把布局视口撑到 674
   （Chrome 移动端于是整体缩放，innerWidth 报 674、"整页不横溢"那条断言反而还是 0）。
   显式给 0，让 .boardwrap 自己横滚。 */
.pz-two > * { min-width: 0 }
@media (max-width: 899px) {
  .pz-three { grid-template-columns: 1fr }
  .pzart { height: 190px }
  .pz-two { grid-template-columns: 1fr }
  .pztab { flex: 1 1 auto; justify-content: center }
}
</style>
