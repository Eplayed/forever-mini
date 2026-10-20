<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <!-- 与旧站 glossary() 逐块对齐：主卡不在 PAGE_HEAD_SEC 表里 → .cdhead.noart big（标题不带图）。
         2026-10-12 站主决定：这一页只留词条本身，讲「来源」按钮、待补口径与自绘占位图标的
         那两句说明已删，出处集中在溯源页。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">中英术语速查</h1></div>
      <div class="field">
        <input type="search" id="q" placeholder="输入中文或英文" :value="routeQ" @input="onQ">
        <select id="fk" v-model="kind" aria-label="按类型筛选">
          <option value="">全部类型</option>
          <option v-for="(label, k) in KIND" :key="k" :value="k">{{ label }}</option>
        </select>
        <select id="fr" v-model="race" aria-label="按种族筛选">
          <option value="">全部种族</option>
          <option v-for="id in raceIds" :key="id" :value="id">{{ raceName(id) }}</option>
        </select>
        <span class="dim mono" id="cnt">{{ list.length }} / {{ items.length }}</span>
      </div>
      <div id="pool">
        <template v-if="groups.length">
          <template v-for="g in groups" :key="g.kind + (g.id || g.name)">
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
                <img v-if="g.iconKey || g.artIcon" :src="g.iconKey ? iconUrl(g.iconKey) : assetUrl(g.artIcon)"
                     alt="" loading="lazy" @error="tileImgBad">
              </span>
              <b>{{ g.name }}</b>
              <span v-if="g.sub" class="dim mono">{{ g.sub }}</span>
              <span class="dim">{{ g.rows.length }} 条</span>
            </div>
            <div class="pool">
              <!-- 点一下复制中英一对（navigator.clipboard + 兜底 execCommand，成功走 #toast 提示） -->
              <span v-for="x in g.rows" :key="x.id || x.cn" class="term" :class="q ? 'hit' : null"
                    :data-c="copyText(x)" @click="copyTerm(x)">
                <IconCell :icon-key="iconOf(x)" :seed="x.id" :cn="x.cn" small />{{ x.cn }}
              </span>
            </div>
          </template>
        </template>
        <div v-else class="empty">没有匹配词条，试试放宽筛选。</div>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 中英术语速查 · 与旧站 app.js glossary() 逐块对齐。
   分组算法与技能书页共用同一份口径（旧站 groupEntries）：职业词条按职业、种族特长按种族
   （天裔两行并进「天裔」一组），剩下的进「装备与其他」；种族组按官方页的阵营顺序排。
   旧站这些是字符串拼接，这里全部等价复刻在组件内，DOM 类名逐字一致。 */
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { assetUrl, load } from '../lib/data.js';
import { raceStyle, iconUrl } from '../lib/glyph.js';
import IconCell from '../components/IconCell.vue';
import ClassTile from '../components/ClassTile.vue';

const KIND = { talent: '天赋/技能', item: '装备', racial: '种族特长' };

const d = ref(null);
const err = ref('');
const q = ref('');
const kind = ref('');
const race = ref('');
const route = useRoute();
// 首页搜索带着 q 跳进来（#/glossary?q=…），落地就该是筛好的样子；初始值不 trim，与旧站 urlQ 一致
const routeQ = String(route.query.q || '');
q.value = routeQ;

function boot() {
  err.value = '';
  Promise.all([load('data/glossary.json'), load('data/races.json'),
    load('data/classes.json'), load('data/icons.json'), load('data/art.json').catch(() => ({}))])
    .then((r) => {
      d.value = {
        items: r[0].items || [],
        RACE: raceLookup(r[1].races),
        classes: r[2].classes || [],
        ICONS: (r[3] || {}).map || {}, RI: (r[4] || {}).raceIcons || {}
      };
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();

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
      /* 官方 CDN 没有这一族的小图标时（天裔两边都没有），落 raceIcons 那张插件转存图
         ——站主 2026-10-20 特批，只当种族小图标用，来源记在 art/manifest.json，不称官方已核。
         两边都没有就仍然只露自绘首字块，不放假图。 */
      artIcon: ((d.value && d.value.RI) || {})[rid] || '',
      st: raceStyle(rid, rc.fac, rc.cn), rows: byRace[rid]
    });
  });
  if (rest.length) out.push({ kind: 'rest', id: 'rest', name: '装备与其他', sub: '', iconKey: '', rows: rest });
  return out;
}

const items = computed(() => (d.value && d.value.items) || []);
const RACE = computed(() => (d.value && d.value.RACE) || { order: [] });

const raceIds = computed(() => {
  const ids = [];
  items.value.forEach((x) => {
    if (!x.raceId) return;
    const rid = raceBucket(x.raceId);
    if (ids.indexOf(rid) < 0) ids.push(rid);
  });
  const order = RACE.value.order || [];
  ids.sort((a, b) => order.indexOf(a) - order.indexOf(b));
  return ids;
});
function raceName(id) { return ((RACE.value[id] || {}).cn) || id; }

const list = computed(() => items.value.filter((x) => {
  if (kind.value && x.kind !== kind.value) return false;
  if (race.value && raceBucket(x.raceId || '') !== race.value) return false;
  if (q.value && ((x.cn || '') + (x.en || '')).toLowerCase().indexOf(q.value.toLowerCase()) < 0) return false;
  return true;
}));
const groups = computed(() => groupEntries(list.value, (d.value && d.value.classes) || [], RACE.value));

/* 图标查表的键：职业词条用 classId，种族特长用 raceId（同名特长在不同种族是两回事） */
function iconOf(x) {
  const key = (x.kind === 'racial' ? (x.raceId || '') : (x.classId || '')) + '|' + x.cn;
  return ((d.value && d.value.ICONS) || {})[key] || '';
}
function copyText(x) { return x.cn + (x.en ? ' / ' + x.en : ''); }
function onQ(e) { q.value = e.target.value.trim(); }
function tileImgBad(e) { e.target.className = 'bad'; }

/* ---- 点词条复制：与旧站 D.copy + D.toast 同一行为（含 execCommand 兜底与 1.8s 提示） ---- */
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
function copyTerm(x) {
  const text = copyText(x);
  const done = () => toast('已复制：' + String(text).slice(0, 12));
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, () => { copyFallback(text); done(); });
  } else { copyFallback(text); done(); }
}
</script>
