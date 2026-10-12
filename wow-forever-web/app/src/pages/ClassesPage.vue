<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="c">
    <!-- 页首职业带：套全站页首 banner 件 .dhero，只补两列布局与 158px 立绘框（CSS 见 app.css 的 .clhero 一节）。
         英文原名吃这一职业的职业色；职业色唯一来源是 lib/glyph.js 那张表，不在这里另抄一份。 -->
    <section class="dhero clhero" :style="clStyle">
      <span class="dx"></span>
      <div class="db">
        <div class="clt">
          <div class="kicker">{{ kicker }}</div>
          <h1 class="pt">{{ c.cn || '未定名' }}<span v-if="c.en" class="clen">{{ c.en }}</span></h1>
          <div class="clline">三系 <b>{{ trees.length }}</b> · 天赋节点 <b>{{ tcnt }}</b> · 客户端改动 <b>{{ bc.all || 0 }}</b> 条 · 官方中文整句 <b>{{ abs.length }}</b> 条</div>
          <p class="clnote">{{ c.note || FALLBACK_NOTE }}</p>
          <span class="dmark">{{ art ? '客户端原画 · 本地转存' : '自绘占位 · 非游戏原画' }}</span>
        </div>
        <div class="chart">
          <ClassTile :class-id="c.id" :cn="c.cn" :icon-key="c.iconKey" mod="lg" />
          <img v-if="art" :src="artSrc" :alt="c.cn + '的职业立绘'" loading="lazy" :class="{ bad: artBad }" @error="artBad = true">
        </div>
      </div>
    </section>

    <div class="card" style="padding-bottom:0">
      <div class="classbar" role="group" aria-label="换一个职业">
        <button v-for="x in CLS" :key="x.id" type="button" class="cls" :class="{ on: x.id === c.id }"
                :data-c="x.id" :aria-pressed="x.id === c.id ? 'true' : 'false'" style="min-width:78px" @click="pick(x.id)">
          <div class="ic"><ClassTile :class-id="x.id" :cn="x.cn" :icon-key="x.iconKey" /></div>
          <div class="n">{{ x.cn }}</div>
        </button>
      </div>
    </div>

    <!-- 三系卡：点一下把右边的技能变化收到那一系，再点一次回到三系都列。
         系名用官方定名，另一来源的叫法走红框悬停（与天赋页同一套符号）。 -->
    <section v-if="trees.length" class="spec3" aria-label="这一职业的三系专精">
      <button v-for="t in trees" :key="t.id" type="button" class="spec plate" :class="{ on: sel === t.nameCn }"
              :data-s="t.nameCn" :aria-pressed="sel === t.nameCn ? 'true' : 'false'" :title="altTip(t)"
              @click="pickSpec(t.nameCn)">
        <b>{{ t.nameCn }}<i v-if="t.nameConflict && t.nameAlt" class="cfl" aria-hidden="true"></i></b>
        <span>{{ (t.nodes || []).length }} 个节点</span>
        <span class="spnote">{{ sel === t.nameCn ? '已只看这一系，再点一次看全部' : '只看这一系的改动' }}</span>
      </button>
    </section>

    <div class="two">
      <section class="card">
        <h2>这一职业有什么</h2>
        <div class="kv"><span>职业中文名</span><b>{{ c.cn }}{{ c.en ? ' / ' + c.en : '' }} <LevelPill :level="c.nameLevel || 'L3'" /> <button type="button" class="ghost" :data-src="'cls-' + c.id" :data-name="c.cn" :aria-label="'查看「' + c.cn + '」的来源'" @click="openBox('cls-' + c.id, c.cn, c.provenance)">{{ boxFor === 'cls-' + c.id ? '收起' : '来源' }}</button></b></div>
        <div class="kv"><span>三系</span><b>{{ treeNames }}</b></div>
        <div class="kv"><span>天赋节点</span><b>{{ tcnt }} 个<component :is="calcLink.to ? 'router-link' : 'a'" v-bind="calcLink">打开计算器 →</component></b></div>
        <div class="kv"><span>名称与官网中文一致</span><b>{{ vcnt }} / {{ tcnt }}</b></div>
        <div class="kv"><span>两个来源叫法不同</span><b>{{ cflTxt }}</b></div>
        <div class="kv"><span>官方中文整句</span><b>{{ abs.length ? abs.length + ' 条' : '' }}<span v-if="!abs.length" class="dim">还没有</span></b></div>
        <div class="kv"><span>客户端改动</span><b>{{ bc.all || 0 }} 条{{ bc.changed ? '（其中 ' + bc.changed + ' 条与经典旧世不同）' : '' }} <button type="button" class="ghost" :data-src="'chg-' + c.id" :data-name="c.cn + '的改动清单'" :aria-label="'查看「' + c.cn + '的改动清单」的来源'" @click="openBox('chg-' + c.id, c.cn + '的改动清单', firstChProv)">{{ boxFor === 'chg-' + c.id ? '收起' : '来源' }}</button></b></div>
        <div class="kv"><span>本站资料完整度</span><b>{{ rankTxt }}</b></div>
        <p class="note">这是按本站能核对的条目数排的资料完整度，是本站自己整理的排序，不是职业强度排行。</p>
        <template v-if="raceRows.length">
          <h3 class="rdh">谁可以选这一职业</h3>
          <div v-for="r in raceRows" :key="r.fac" class="racerow">
            <b>{{ r.fac }}</b>
            <span class="chips"><span v-for="n in r.list" :key="n" class="tag">{{ n }}</span></span>
            <a :href="racesHref">矩阵 →</a>
          </div>
          <p v-if="skyCfl" class="conf">天裔能选几个职业，两份说法还没对上（同页两张矩阵表与导语不一致），<a :href="racesHref">种族页两个都留着</a></p>
        </template>
        <div class="srcbox" id="srcbox" :style="{ display: box ? 'block' : 'none' }">
          <h3 v-if="box">{{ box.name }} · 来源与核对</h3>
          <SourceList v-if="box" :list="box.list" />
        </div>
      </section>

      <section class="card">
        <h2>技能变化<span class="dim mono">{{ sel ? ' 只看 ' + sel : ' 三系都列' }}</span><span class="dim mono"> · {{ shown.length }} 条</span></h2>
        <p class="dim">只列名称、归属与客户端解包给出的改动类别，不复制别人的逐字前后对照；官方中文稿里出现过的名字，把原句整句贴在下面。</p>
        <div v-if="noAb" class="note">{{ noAb }}</div>
        <template v-if="groups.length">
          <template v-for="g in groups" :key="g.k">
            <div class="lgrp"><b>{{ g.label }}</b><span class="dim">{{ g.rows.length }} 条</span>
              <span v-if="g.k === 'unchanged'" class="dim">客户端里这条和经典旧世一样</span></div>
            <div class="scrollx"><table class="entab chtab"><thead><tr><th>名称</th><th>类别</th><th>哪一系</th><th></th></tr></thead><tbody>
              <template v-for="(x, i) in g.rows" :key="x.id || (g.k + i)">
                <tr>
                  <td><b>{{ x.nameCn || '未命名' }}</b><span v-if="x.maxRank" class="dim"> · 最多 {{ x.maxRank }} 层</span><span v-if="abm[x.nameCn]" class="quote">{{ abm[x.nameCn].quote }}</span></td>
                  <td>{{ CL_KIND[x.kind] || '其他' }}<template v-if="g.k === 'other' && x.changeCn"><br><span class="tag">{{ x.changeCn }}</span></template></td>
                  <td><template v-if="x.tree">{{ x.tree }}</template><span v-else class="dim">未归系</span></td>
                  <td class="act"><LevelPill :level="x.level" /> <button type="button" class="ghost" :data-src="uid(g.k, i)" :data-name="x.nameCn || '这一条'" :aria-label="'查看「' + (x.nameCn || '这一条') + '」的来源'" @click="toggleRow(uid(g.k, i))">{{ openRow === uid(g.k, i) ? '收起' : '来源' }}</button></td>
                </tr>
                <tr class="srow" :id="'s-' + uid(g.k, i)" :style="{ display: openRow === uid(g.k, i) ? 'table-row' : 'none' }">
                  <td colspan="4"><SourceList :list="x.provenance" /></td>
                </tr>
              </template>
            </tbody></table></div>
          </template>
        </template>
        <div v-else class="empty">这一系还没有客户端改动记录，等下一次客户端更新再看。</div>
        <div v-if="abs.length" class="chipsrow"><a :href="bookHref">这一职业在技能书里的四态整句 →</a></div>
      </section>
    </div>

    <section class="card">
      <h2>接着看这一职业</h2>
      <div class="tools6">
        <component v-for="t in exits" :is="t.link.to ? 'router-link' : 'a'" v-bind="t.link" :key="t.name" class="tool plate">
          <span class="tico"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke-width="1.8" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="1" /><path d="M9 12h6M12 9v6" /></svg></span>
          <h3>{{ t.name }}</h3><p>{{ t.desc }}</p>
          <span class="foot"><em>{{ t.read }}</em><i>进入 →</i></span>
        </component>
      </div>
    </section>

    <div v-if="gaps.length" class="card">
      <h2>本页还没确认的</h2>
      <ol class="q"><li v-for="(g, i) in gaps" :key="i">{{ g }}</li></ol>
      <p class="dim" style="margin-top:6px">这些条目缺官方来源或未实测，宁可空着也不编。</p>
    </div>
  </template>
</template>

<script setup>
/* 职业页（每职业一页）· 与旧站 src/classes.html + app.js 的 classPage() 逐块对齐。
   任务书 docs/PLAN-classes-and-nav-2026-10-12.md：内容一条都不写死，全部从 src/data 现取；
   稿子「职业概览」那六行里我们没有可核对来源的五行（战斗定位 / 核心资源 / 护甲类型 /
   可用武器 / 团队职责）不显示，缺的进本页未确认清单。 */
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { assetUrl, load } from '../lib/data.js';
import { legacyUrl, linkFor } from '../lib/nav.js';
import { CLASS_COLOR } from '../lib/glyph.js';
import ClassTile from '../components/ClassTile.vue';
import LevelPill from '../components/LevelPill.vue';
import SourceList from '../components/SourceList.vue';

const CL_STATE = { added: '新增', modified: '改动', removed: '移除', unchanged: '未变' };
const CL_ORDER = ['added', 'modified', 'removed', 'unchanged'];
const CL_KIND = { talent: '天赋', spell: '技能' };
const FALLBACK_NOTE = '这一职业的说法以客户端解包为准，游戏内层级未获得。';

const base = ref(null);
const tree = ref(null);
const err = ref('');
const sel = ref('');
const openRow = ref('');
const box = ref(null);
const boxFor = ref('');
const artBad = ref(false);
const route = useRoute();
const router = useRouter();

function boot() {
  err.value = '';
  Promise.all([load('data/classes.json'), load('data/scale.json'), load('data/abilities.json'),
    load('data/changes.json'), load('data/races.json'),
    load('data/art.json').catch(() => ({}))])
    .then((rs) => { base.value = { CLS: rs[0].classes || [], SC: rs[1].scale || {}, AB: rs[2] || { items: [], meta: {} }, CHR: rs[3] || {}, RC: rs[4] || {}, ART: rs[5] || {} }; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
const CLS = computed(() => (base.value && base.value.CLS) || []);
const cid = computed(() => {
  const q = String(route.query.c || '');
  const hit = CLS.value.filter((x) => x.id === q)[0];
  return hit ? hit.id : ((CLS.value[0] || {}).id || '');
});
watch(cid, (v) => {
  sel.value = ''; openRow.value = ''; box.value = null; boxFor.value = ''; artBad.value = false;
  if (!v) return;
  load('data/talents/' + v + '.json').then((d) => { tree.value = d; }).catch(() => { tree.value = null; });
});
watch(() => route.query.c, (v) => {
  // 地址里换了职业号但还没落到数据上（例如从别页带 ?c= 进来）：清掉上一职业的展开态
  if (String(v || '') !== cid.value) { openRow.value = ''; box.value = null; boxFor.value = ''; }
});
onMounted(boot);

function pick(id) {
  if (id !== cid.value) router.replace({ path: '/classes', query: { c: id } });
}
function pickSpec(name) { sel.value = sel.value === name ? '' : name; }
function uid(k, i) { return cid.value + '-' + k + '-' + i; }
function toggleRow(id) { openRow.value = openRow.value === id ? '' : id; }
function openBox(id, name, list) {
  if (boxFor.value === id && box.value) { box.value = null; boxFor.value = ''; return; }
  boxFor.value = id; box.value = { name: name, list: list || [] };
}
function altTip(t) {
  return t.nameConflict && t.nameAlt
    ? '这一系有两个叫法：官方中文写「' + t.nameCn + '」，另一来源译作「' + t.nameAlt + '」，待定稿' : null;
}

const c = computed(() => CLS.value.filter((x) => x.id === cid.value)[0] || null);
const trees = computed(() => (tree.value && tree.value.trees) || []);
const st = computed(() => (tree.value && tree.value.stats) || {});
/* 名称核对数按节点现数；系名的两个叫法记在 trees[] 自己身上，分开数 */
const tcnt = computed(() => {
  let n = 0;
  trees.value.forEach((t) => { (t.nodes || []).forEach(() => { n++; }); });
  return n || st.value.nodes || 0;
});
const vcnt = computed(() => {
  let n = 0;
  trees.value.forEach((t) => { (t.nodes || []).forEach((x) => { if (x.nameVerified) n++; }); });
  return n;
});
const altTrees = computed(() => trees.value.filter((t) => t.nameConflict && t.nameAlt));
const treeNames = computed(() => trees.value.map((t) => t.nameCn).join(' · ') || '待补');
const cflTxt = computed(() => ((st.value.nameConflict || 0) +
  (altTrees.value.length ? ' 个节点、' + altTrees.value.length + ' 个系名' : ' 个节点')) + '（两个都留着）');
const col = computed(() => (c.value && CLASS_COLOR[c.value.id]) || '');
const clStyle = computed(() => (col.value ? '--cl:' + col.value : ''));
const kicker = computed(() => 'CLASS · ' + String((c.value && (c.value.en || c.value.id)) || '').toUpperCase());
const art = computed(() => (c.value && base.value && (base.value.ART.classes || {})[c.value.id]) || '');
const artSrc = computed(() => (art.value ? assetUrl(art.value) : ''));
const SC = computed(() => (base.value && base.value.SC) || {});
const AB = computed(() => (base.value && base.value.AB) || { items: [], meta: {} });
const CHR = computed(() => (base.value && base.value.CHR) || {});
const RC = computed(() => (base.value && base.value.RC) || {});
const abs = computed(() => (AB.value.items || []).filter((x) => x.classId === cid.value));
const abm = computed(() => {
  const m = {};
  abs.value.forEach((x) => { if (x.name && !m[x.name]) m[x.name] = x; });
  return m;
});
const allCh = computed(() => (CHR.value.items || []).filter((x) => x.classId === cid.value));
const shown = computed(() => allCh.value.filter((x) => !sel.value || x.tree === sel.value));
const bc = computed(() => ((CHR.value.meta || {}).byClass || []).filter((x) => x.classId === cid.value)[0] || {});
const firstChProv = computed(() => ((allCh.value[0] || {}).provenance) || []);
const rank = computed(() => (SC.value.classRank || []).filter((x) => x.classId === cid.value)[0] || {});
const rankTxt = computed(() => (rank.value.share !== undefined ? rank.value.share + '%' : '未排') +
  (rank.value.place ? ' · 第 ' + rank.value.place + ' 位' : ''));
const noAb = computed(() => {
  const cn = (c.value && c.value.cn) || '__none__';
  return ((AB.value.meta || {}).notCollected || []).filter((s) => String(s).indexOf(cn) >= 0)[0] || '';
});
const groups = computed(() => {
  const by = {};
  shown.value.forEach((x) => {
    const k = CL_STATE[x.changeKind] ? x.changeKind : 'other';
    (by[k] = by[k] || []).push(x);
  });
  const keys = CL_ORDER.filter((k) => by[k]);
  if (by.other) keys.push('other');
  return keys.map((k) => ({ k: k, label: k === 'other' ? '其它说法' : CL_STATE[k], rows: by[k] }));
});
/* 可选种族：矩阵存的是职业 id，展示用 races.json 的正式中文名（天裔按官方写法带子族） */
const raceRows = computed(() => {
  const out = [];
  ['horde', 'alliance'].forEach((fid) => {
    const list = (RC.value.races || []).filter((r) => (r.classes || []).indexOf(cid.value) >= 0 && r.faction === fid)
      .map((r) => (r.subgroup && r.subgroup.nameCn) || r.nameCn);
    if (!list.length) return;
    const fac = (RC.value.factions || []).filter((x) => x.id === fid)[0];
    out.push({ fac: fac ? fac.nameCn : fid, list: list });
  });
  return out;
});
const hasSky = computed(() => (RC.value.races || []).some((r) =>
  (r.classes || []).indexOf(cid.value) >= 0 && String(r.id).indexOf('skyborne') === 0));
const skyCfl = computed(() => hasSky.value && (RC.value.conflicts || []).length > 0);
const racesHref = legacyUrl('races.html');
const bookHref = legacyUrl('skills.html');
const calcLink = computed(() => {
  const l = linkFor('talent.html');
  return l.to ? { to: { path: l.to, query: { c: cid.value } } }
    : { href: l.href + '?c=' + encodeURIComponent(cid.value) };
});
const exits = computed(() => {
  const items = [
    ['talent.html', '天赋计算器', tcnt.value + ' 个节点 · 三棵真树',
      '格子就是客户端里的天赋本身：位置、每层上限、与经典旧世的差异都按真结构摆。', { c: cid.value }],
    ['skills.html', '技能书', abs.value.length + ' 条官方中文整句（这一职业）',
      '中英对照与新增 / 改动 / 改名 / 移除四态，整句出自国服官方公告，名称不在句里就不收。', null],
    ['chooser.html', '玩法问答', '答完题才知道这一职业合不合手',
      '按玩法取向问答，不给强度排行——那是本站红线。', null]];
  return items.map((x) => {
    const l = linkFor(x[0]);
    return {
      name: x[1], read: x[2], desc: x[3],
      link: l.to ? { to: { path: l.to, query: x[4] || {} } }
        : { href: l.href + (x[4] ? '?c=' + encodeURIComponent(x[4].c) : '') }
    };
  });
});
const gaps = computed(() => {
  const out = [];
  if (!trees.value.length) out.push('这一职业的天赋结构还没有可信来源，三系与节点数都空着');
  out.push('第几层需要点满多少点：客户端解包给过一组数，正式服没实测，这一页只按坐标摆位，不做「够点才能点下一层」的判定');
  if (!abs.value.length) out.push('官方中文的职业深度解析稿还没发，这一页没有官方整句');
  if (c.value && c.value.nameLevel !== 'L0') out.push('职业中文名的官方中文说法还没逐字核到');
  out.push('这个职业用什么资源、穿什么护甲、能用什么武器、在团队里顶什么位置：官方中文里还没有能核对的说法，这一页就不写');
  out.push('三系各自在副本与 PvP 里的实际手感需要实测，本站不做强度与胜率结论');
  return out;
});
</script>
