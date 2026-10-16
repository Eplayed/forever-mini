<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <!-- 与旧站 app.js skills() 逐块对齐：主卡在旧站 PAGE_HEAD_SEC 表里（skills → img/art/classes/mage.webp），
         这里的 .cdhead.big + .hicon img 与旧站 decoratePageHead() 的产出逐字一致。
         图必须走 JS 常量而不是模板字符串字面量——Vite 会去解析静态 src，public 路径直接写会让
         `npm run build` 报 Rollup failed to resolve（参照 WorldPage 的 HEAD_ART）。 -->
    <div class="card">
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">技能书</h1>
      </div>
      <div class="field">
        <input type="search" id="q" placeholder="搜中文或英文" :value="q" @input="onQ">
        <select id="c" v-model="fc">
          <option value="">全部职业</option>
          <option v-for="x in cls" :key="x.id" :value="x.id">{{ x.cn }}</option>
        </select>
        <select id="k" v-model="fk">
          <option value="">全部类型</option>
          <option v-for="kk in kindKeys" :key="kk" :value="kk">{{ KIND[kk] }}</option>
        </select>
        <span class="dim mono" id="cnt">{{ list.length }} / {{ items.length }} 条 · 有图标 {{ withIcon }} 条</span>
      </div>
    </div>

    <!-- 法术书（M2 数据 / 10-16 视觉升级第一批）：按「职业 · 系」分组，只列名称、级数、
         起学等级与与经典旧世的对照状态。级数或起学等级两边说法不一样的，两个数都摆
         （红线：两源分歧两个都留），写成玩家读得懂的那一句；描述正文一条不落。
         表格换成 .board：列宽固定（原来富余宽度全塞在名字列后面，中间一大片空白）、
         状态做成 chip、分组头滚动时吸附在表头下面。样式在 src/css/board.css，旧站不加载。 -->
    <div class="card">
      <div class="bhead">
        <h2 class="bt">法术书</h2>
        <span class="bn" id="spcnt">{{ spList.length }} 条 · {{ spBlocks.length }} 组</span>
      </div>
      <div class="boardwrap">
        <table class="board" id="sptbl">
          <thead><tr>
            <th class="c-ico">图标</th><th class="w-name">法术</th>
            <th class="c-num">级数</th><th class="c-num2">起学等级</th><th class="w-tail">与经典旧世</th>
          </tr></thead>
          <tbody class="grp" v-for="b in spBlocks" :key="b.cid + '-' + b.tab">
            <tr class="grp2h"><th colspan="5">
              <ClassTile :class-id="b.cid" :cn="b.cname" :icon-key="b.iconKey" />
              {{ b.cname }}<span class="gtag">{{ b.tab }}</span>
              <span class="gcount">{{ b.rows.length }} 条</span>
            </th></tr>
            <tr v-for="x in b.rows" :key="x.id">
              <td class="c-ico"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.name" /></td>
              <td><span class="nm"><HlText :text="x.name" :q="q" /></span>
                <span v-if="x.relation" class="sub">{{ SP_REL[x.relation] || x.relation }}</span></td>
              <td class="c-num num">{{ x.ranks ? x.ranks + ' 级' : '' }}
                <span v-if="x.ranksAlt" class="conf">级数有两个说法：{{ x.ranks }} / {{ x.ranksAlt }}，还没实测</span></td>
              <td class="c-num2 num">{{ x.learnLevel ? x.learnLevel + ' 级起' : '' }}
                <span v-if="x.learnAlt" class="conf">起学等级有两个说法：{{ x.learnLevel }} / {{ x.learnAlt }}，还没实测</span></td>
              <td class="w-tail"><span v-if="x.state" class="chip-st" :class="x.state">{{ SP_STATE[x.state] || x.state }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!spBlocks.length" class="empty">没有匹配的法术，换个词或放宽职业筛选。</div>
    </div>

    <!-- 与经典旧世的差异（四态）：abilities.json 现取，跟着职业筛选走（不吃搜索词与类型筛选）。
         2026-10-12 站主决定：这一页只留词条与原句，讲"原句出自哪份稿子、为什么没有未变这一档"
         的那几段已删，出处集中在溯源页。 -->
    <div class="card">
      <h2>与经典旧世的差异（四态）<span class="dim mono" id="abcnt">{{ abShown }}</span></h2>
      <div id="abtbl">
        <template v-if="abList.length">
          <template v-for="st in AB_STATES" :key="st">
            <template v-if="(byState[st] || []).length">
              <h3>{{ AB_STATE[st] }} · {{ byState[st].length }} 条</h3>
              <div class="boardwrap">
                <table class="board abtab">
                  <colgroup><col style="width:20%"><col style="width:16%"><col style="width:18%"><col></colgroup>
                  <thead><tr><th>名称</th><th>职业/专精</th><th>层级线索</th><th>官方原句</th></tr></thead>
                  <tbody>
                    <tr v-for="x in byState[st]" :key="x.id">
                      <td><IconCell :icon-key="ICONS[x.classId + '|' + x.name] || ''" :seed="x.classId + x.name" :cn="x.name" small /><b>{{ x.name }}</b><br><span class="dim">{{ AB_KIND[x.kind] || x.kind }}</span></td>
                      <td>{{ cnName[x.classId] || x.classId }}<template v-if="x.spec"> · {{ AB_SPEC[x.spec] || x.spec }}</template></td>
                      <td class="mono">{{ tierOf(x) }}</td>
                      <td class="quote">{{ x.quote }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>
          </template>
        </template>
        <!-- 空态要说清"为什么空"，那句话取自 abilities.json 的「没收到的」，不在代码里另写一遍 -->
        <div v-else class="empty">{{ abWhy || '这个职业还没有官方中文深度解析稿，四态无从谈起。' }}</div>
      </div>
    </div>

    <!-- 词条表：职业/种族/装备与其他三段分组（groupEntries 与速查页同一份口径），
         每条带图标，搜索词命中走 HlText 高亮（旧站 D.hl 等价，不拼 HTML）。 -->
    <div class="card tblbox">
      <div id="tbl">
        <template v-if="groups.length">
          <template v-for="g in groups" :key="g.kind + '-' + g.id">
            <div class="lgrp">
              <ClassTile v-if="g.kind === 'class'" :class-id="g.id" :cn="g.name" :icon-key="g.iconKey" />
              <!-- 种族方块：新站无现成组件，按 lib/glyph.js raceStyle 同一算法内联（阵营色打底 + 首字），
                   本地官方图标盖面，取不到露出自绘块——与旧站 Glyph.raceTile 同一结构 .liw.t -->
              <span v-else-if="g.kind === 'race'" class="liw t">
                <svg viewBox="0 0 40 40" aria-hidden="true">
                  <rect width="40" height="40" rx="6" :fill="g.st.fill" :stroke="g.st.stroke" stroke-opacity=".7" />
                  <text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" :fill="g.st.text"
                        font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ g.st.letter }}</text>
                </svg>
                <img v-if="g.iconKey" :src="iconUrl(g.iconKey)" alt="" loading="lazy" @error="tileImgBad">
              </span>
              <b>{{ g.name }}</b>
              <span v-if="g.sub" class="dim mono">{{ g.sub }}</span>
              <span class="dim">{{ g.rows.length }} 条</span>
            </div>
            <div class="boardwrap">
              <table class="board">
                <colgroup><col class="c-ico"><col style="width:28%"><col style="width:30%"><col class="c-num2"><col class="c-num"></colgroup>
                <thead><tr><th class="c-ico">图标</th><th>中文名</th><th>英文原名</th><th class="c-num2">类型</th><th class="c-num"></th></tr></thead>
                <tbody>
                  <tr v-for="x in g.rows" :key="x.id">
                    <td class="ich"><IconCell :icon-key="ICONS[iconKeyOf(x)] || ''" :seed="x.id" :cn="x.cn" /></td>
                    <td><HlText :text="x.cn" :q="q" /></td>
                    <td class="en"><HlText v-if="x.en" :text="x.en" :q="q" /><span v-else class="dim">待补</span></td>
                    <td>{{ KIND[x.kind] || x.kind }}</td>
                    <td class="act"><button class="ghost" :data-copy="copyText(x)" @click="copyEntry(x)">复制</button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </template>
        <div v-else class="empty">没有匹配条目，试试放宽筛选。</div>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 技能书 · 与旧站 app.js skills() 逐块对齐（行 1476-1583）。
   词条来自 glossary.json（职业/种族/装备与其他三段分组），四态来自 abilities.json，
   图标查表 icons.json.map，种族归属 races.json——全部 load() 现取，一条不写死。
   groupEntries/raceLookup/iconKeyOf 与旧站行 126-212 同一算法（GlossaryPage 已复刻过一份）。 */
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import { iconUrl, raceStyle } from '../lib/glyph.js';
import IconCell from '../components/IconCell.vue';
import ClassTile from '../components/ClassTile.vue';
import HlText from '../components/HlText.vue';

/* 主卡卡片头用的板块图：与首页图标轨「职业」格同一张本地原画（站内同一板块同一张脸） */
const HEAD_ART = 'img/art/classes/mage.webp';

const KIND = { talent: '天赋/技能', item: '装备', dungeon: '副本', boss: 'BOSS', system: '系统', zone: '地名', skill: '技能', racial: '种族特长' };
/* 法术书的两个标签族：state 是"与经典旧世对照到哪儿"，relation 是"这条从哪来"。
   同一条只会有其中一族（build-data.js 卡这条），所以一格显示就够，不并排摆两列。 */
const SP_STATE = { same: '与经典一致', changed: '改动', new: '无限新增', removed: '已移除', renamed: '改名' };
const SP_REL = { talent: '天赋赋予', race: '种族技能', earlier: '比经典更早学会', baseline: '职业技能' };
const AB_STATE = { new: '新增', changed: '改动', renamed: '改名', removed: '移除' };
const AB_STATES = ['new', 'changed', 'renamed', 'removed'];
const AB_KIND = { talent: '天赋', skill: '技能', pet: '宠物技能' };
const AB_SPEC = { 'beast-mastery': '野兽控制', marksmanship: '射击', survival: '生存', feral: '野性战斗',
  restoration: '恢复', balance: '平衡', discipline: '戒律', holy: '神圣', shadow: '暗影',
  arms: '武器', fury: '狂怒', protection: '防护' };

const d = ref(null);
const err = ref('');
const q = ref('');
const fc = ref('');
const fk = ref('');
const route = useRoute();
// 首页搜索带着 q 跳进来（#/skills?q=…），落地就该是筛好的样子；旧站 skills 的 q 不 trim
q.value = String(route.query.q || '');
// 搜索索引点一条法术会带 c=<职业> 跳进来（同名技能在不同职业是两条），落地就该是筛好的样子
fc.value = String(route.query.c || '');

function boot() {
  err.value = '';
  Promise.all([load('data/glossary.json'), load('data/classes.json'), load('data/abilities.json'),
    load('data/icons.json'), load('data/races.json'), load('data/spells.json')])
    .then((r) => {
      d.value = {
        items: r[0].items, cls: r[1].classes, ab: r[2] || { items: [], meta: {} },
        ICONS: (r[3] || {}).map || {}, RACE: raceLookup((r[4] || {}).races || []),
        SP: (r[5] || {}).spells || []
      };
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

/* ---- 种族查表与分组：与旧站 app.js 行 173-212 同一算法 ---- */
function raceLookup(races) {
  const m = { order: [] };
  (races || []).forEach((x) => {
    m[x.id] = { cn: x.subgroup ? x.subgroup.nameCn : x.nameCn, fac: x.faction, iconKey: x.iconKey };
    m.order.push(x.id);
    // 天裔在两张表里各一行，词条归属可能落在子族上；展示时统一并进「天裔」一组
    if (x.nameCn === '天裔' && !m.skyborne) {
      m.skyborne = { cn: '天裔', fac: '', iconKey: x.iconKey };
      m.order.push('skyborne');
    }
  });
  return m;
}
function raceBucket(rid) { return String(rid || '').indexOf('skyborne') === 0 ? 'skyborne' : (rid || ''); }
function groupEntries(list, classes, RACE) {
  const byCls = {}, byRace = {}, rest = [];
  list.forEach((x) => {
    if (x.kind === 'racial') {
      const rid = raceBucket(x.raceId);
      (byRace[rid] = byRace[rid] || []).push(x);
      return;
    }
    if (x.classId) { (byCls[x.classId] = byCls[x.classId] || []).push(x); return; }
    rest.push(x);
  });
  const out = [];
  classes.forEach((c) => {
    if (byCls[c.id]) out.push({
      kind: 'class', id: c.id, name: c.cn, sub: c.en, iconKey: c.iconKey, rows: byCls[c.id]
    });
  });
  // 种族组按官方页的阵营顺序排（部落五个 → 联盟五个），不按拼音也不按 id
  Object.keys(byRace).sort((a, b) => {
    const ia = RACE.order.indexOf(a), ib = RACE.order.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  }).forEach((rid) => {
    const rc = RACE[rid] || { cn: '未归属种族', fac: '' };
    out.push({
      kind: 'race', id: rid, name: rc.cn, sub: '种族特长', iconKey: rc.iconKey,
      st: raceStyle(rid, rc.fac, rc.cn), rows: byRace[rid]
    });
  });
  if (rest.length) out.push({ kind: 'rest', id: 'rest', name: '装备与其他', sub: '', iconKey: '', rows: rest });
  return out;
}
/* 图标查表的键：职业词条用 classId，种族特长用 raceId（同名特长在不同种族是两回事） */
function iconKeyOf(x) {
  return (x.kind === 'racial' ? (x.raceId || '') : (x.classId || '')) + '|' + x.cn;
}

const items = computed(() => (d.value && d.value.items) || []);
const cls = computed(() => (d.value && d.value.cls) || []);
const ICONS = computed(() => (d.value && d.value.ICONS) || {});
const RACE = computed(() => (d.value && d.value.RACE) || { order: [] });

const kindKeys = computed(() => Object.keys(KIND).filter((k) => items.value.some((x) => x.kind === k)));
const list = computed(() => items.value.filter((x) => {
  if (fc.value && x.classId !== fc.value) return false;
  if (fk.value && x.kind !== fk.value) return false;
  if (q.value && ((x.cn || '') + (x.en || '')).toLowerCase().indexOf(q.value.toLowerCase()) < 0) return false;
  return true;
}));
const groups = computed(() => groupEntries(list.value, cls.value, RACE.value));
const withIcon = computed(() => list.value.filter((x) => ICONS.value[iconKeyOf(x)]).length);

/* ---- 法术书（spells.json）：跟职业与搜索词走，与旧站 drawSpells 同一算法 ---- */
const spAll = computed(() => (d.value && d.value.SP) || []);
const spList = computed(() => spAll.value.filter((x) => {
  if (fc.value && x.classId !== fc.value) return false;
  if (q.value && String(x.name || '').toLowerCase().indexOf(q.value.toLowerCase()) < 0) return false;
  return true;
}));
const spBlocks = computed(() => {
  const byCls = {};
  spList.value.forEach((x) => {
    const g = byCls[x.classId] || (byCls[x.classId] = { order: [], rows: {} });
    const tab = x.tab || '未分系';
    if (!g.rows[tab]) { g.rows[tab] = []; g.order.push(tab); }
    g.rows[tab].push(x);
  });
  const out = [];
  cls.value.forEach((c) => {
    const g = byCls[c.id];
    if (!g) return;
    g.order.forEach((tab) => {
      out.push({ cid: c.id, cname: c.cn, iconKey: c.iconKey, tab: tab, rows: g.rows[tab] });
    });
  });
  return out;
});
function onQ(e) { q.value = e.target.value; }
function tileImgBad(e) { e.target.className = 'bad'; }

/* ---- 四态（abilities.json）：跟着职业筛选走 ---- */
const ab = computed(() => (d.value && d.value.ab) || { items: [], meta: {} });
const abList = computed(() => (ab.value.items || []).filter((x) => !fc.value || x.classId === fc.value));
const byState = computed(() => {
  const m = { new: [], changed: [], renamed: [], removed: [] };
  abList.value.forEach((x) => { (m[x.state] || (m[x.state] = [])).push(x); });
  return m;
});
const cnName = computed(() => { const m = {}; cls.value.forEach((c) => { m[c.id] = c.cn; }); return m; });
// 旧站 drawAbilities 在四态清单为空时提前 return，这格读数保留上一次的值——照抄这个行为
const abShown = ref('');
watch(abList, (v) => { if (v.length) abShown.value = ' · ' + v.length + ' 条'; });
const abWhy = computed(() => {
  const cname = ((cls.value.filter((x) => x.id === fc.value)[0] || {}).cn) || '';
  return ((ab.value.meta || {}).notCollected || []).filter((s) => cname && String(s).indexOf(cname) >= 0)[0] || '';
});
function tierOf(x) {
  let tier = x.tierFrom !== null && x.tierFrom !== undefined
    ? '第' + x.tierFrom + ' 层 → 第' + x.tierHint + ' 层'
    : (x.tierHint ? '第' + x.tierHint + ' 层' : '—');
  if (x.milestone) tier += ' ｜ 第' + x.milestone + ' 点关键天赋';
  return tier;
}

/* ---- 复制：与旧站 D.copy + D.toast 同一行为（含 execCommand 兜底与 1.8s 提示） ---- */
function copyText(x) { return x.cn + (x.en ? ' / ' + x.en : ''); }
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
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch (e) { /* 剪贴板不可用就算了 */ }
  document.body.removeChild(ta);
}
function copyEntry(x) {
  const text = copyText(x);
  const done = () => toast('已复制：' + String(text).slice(0, 12));
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, () => { copyFallback(text); done(); });
  } else { copyFallback(text); done(); }
}
</script>
