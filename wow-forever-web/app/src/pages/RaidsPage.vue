<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="P">
    <!-- 页首 banner：团本页不在旧站 PAGE_HEAD_SEC 表里，2026-10-12 起按设计稿改用 .dhero 放 H1，
         不套卡片头。卡上的图一律是本站自生成的氛围底图，不拿一张通用风景冒充某个团本的载入图。
         名字与人数只用我们数据里有的说法：中文定名没公布就写英文原名，两说的两个数都摆。 -->
    <section class="dhero" style="height:300px">
      <img :src="HERO" alt="" style="object-position:center 25%">
      <span class="dx"></span>
      <div class="db" style="padding-top:104px">
        <div class="kicker">RAID</div>
        <h1 class="pt" style="font-family:var(--font-display);font-size:46px;margin:10px 0 8px;color:#f2ead8">团队副本</h1>
        <div style="font-size:15px;color:var(--txt-dim)">现在能排到 {{ P.names.length }} 个团队条目。<template v-if="P.nextRaid">新团本 <b style="color:var(--gold-hi);font-family:var(--font-mono)">{{ raidDate }}</b> 开放。</template></div>
      </div>
      <div class="dstate"><i></i><b>{{ P.both ? '部分已有名单' : '全部未开放' }}</b></div>
    </section>

    <section style="padding:36px 0 0">
      <div class="raidgrid">
        <div v-for="c in cards" :key="c.r.id" class="raidcard">
          <div class="art">
            <img :src="c.art" alt="" loading="lazy">
            <span class="sh"></span>
            <span class="goldtag">{{ c.sizes.length ? c.sizes[0] + ' 人' : '人数未定' }}</span>
            <span class="chip-open">{{ c.bosses ? '名单已收录' : '未开放' }}</span>
            <h3>{{ c.r.nameEn || c.r.nameCn || '未定名' }}</h3>
          </div>
          <div class="bd">
            <div class="facts">
              <template v-if="c.sizes.length > 1">人数两说：<template v-for="(s, i) in c.sizes" :key="s + '-' + i"><b>{{ s }}</b>{{ i < c.sizes.length - 1 ? ' / ' : '' }}</template> 人</template>
              <template v-else-if="c.sizes.length">进入人数 <b>{{ c.sizes[0] }}</b> 人</template>
              <template v-else>人数未定</template>
              <br>{{ c.r.nameCn || '中文定名未公布' }}
            </div>
            <div class="dashedbox">{{ c.bosses ? '首领 ' + c.bosses + ' 个已收录' : '首领名单待补' }}</div>
            <!-- 红线：两份名单人数不一致时两个都摆着，不替玩家挑一个 -->
            <div v-if="c.sizes.length > 1" class="conf">规模两说：另一份资料自报的人数与客户端排队条目写的不是一个数，两个都摆着等定稿。</div>
            <component v-if="c.inClient" :is="c.link.to ? 'router-link' : 'a'" v-bind="c.link" class="cta-cut">看这一座的收录情况</component>
            <component v-else :is="TL_LINK.to ? 'router-link' : 'a'" v-bind="TL_LINK" class="cta-cut">看上线时间表那一页</component>
          </div>
        </div>
      </div>
    </section>

    <!-- 三步带：日期全部取自 timeline.json（官方那条怎么写就怎么摆），不抄稿子写死的日期 -->
    <section class="tl3" style="margin-top:32px">
      <template v-for="(n, i) in tlSeq" :key="i">
        <span v-if="n.link" class="link"></span>
        <div v-else class="node">
          <i :style="{ background: n.col }"></i>
          <div><b>{{ n.lab }}</b><span :style="{ color: n.col }">{{ n.date }}</span></div>
        </div>
      </template>
    </section>

    <div class="card">
      <div class="stats">
        <div class="stat"><b>{{ P.names.length }}</b>可排队的团队条目</div>
        <div class="stat"><b>{{ P.claimed.length }}</b>名单里的团本</div>
        <div class="stat"><b>{{ P.both }}</b>两边对得上</div>
        <div class="stat"><b>{{ P.named }}</b>有中文名</div>
      </div>
    </div>

    <div class="card" id="client">
      <h2>能排到队的团队副本</h2>
      <div class="field">
        <input id="rq" type="search" placeholder="按英文名筛，例如 Storm" aria-label="按英文名筛团本"
               :value="q" @input="onFilter">
        <span class="dim mono" id="rcnt">{{ shown.length }} / {{ P.names.length }}</span>
      </div>
      <template v-if="shown.length">
        <template v-for="b in bands" :key="b.key">
          <div class="band"><b>{{ b.label }}</b><span v-if="b.count !== null" class="dim mono">{{ b.count }} 座</span></div>
          <div class="scrollx">
            <table class="entab rtab">
              <thead><tr><th>客户端里的名字</th><th>排队等级</th><th>一次几人</th><th>排队条目</th><th>本站</th></tr></thead>
              <tbody>
                <tr v-for="x in b.rows" :key="x.nameEn">
                  <td><b>{{ x.nameEn }}</b><span class="dim">　中文定名未公布</span></td>
                  <td class="mono">{{ x.levelRange }} 级</td>
                  <td class="mono">{{ sizeText(x) }}</td>
                  <td class="mono">{{ entryText(x) }}</td>
                  <td>
                    <template v-if="x.st">
                      <span class="dim">{{ x.matchedIn === 'raid' ? '已有这一座：' : '按地下城收录：' }}</span><component :is="x.st.link.to ? 'router-link' : 'a'" v-bind="x.st.link">{{ x.st.label }}</component>
                    </template>
                    <template v-else><span class="dim">还没有名单</span></template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </template>
      <div v-else class="empty">没有匹配的名字；这一列只有客户端里的英文原名，中文定名还没公布。</div>
    </div>

    <div class="card" id="claimed">
      <h2>名单里的 {{ P.claimed.length }} 座</h2>
      <div class="scrollx">
        <table class="entab rtab">
          <thead><tr><th>载入图</th><th>名字</th><th>它自报规模</th><th>客户端的队伍查找器里</th></tr></thead>
          <tbody>
            <tr v-for="r in P.claimed" :key="r.id">
              <td class="ich">
                <span v-if="r.art" class="liw t"><img :src="r.art" :alt="(r.nameEn || '') + ' 的客户端载入图'"
                      loading="lazy" :class="{ bad: artBad[r.id] }" @error="artBad[r.id] = true"></span>
                <span v-else class="dim">没有这张载入图</span>
              </td>
              <td><b>{{ r.nameEn || r.nameCn || '未定名' }}</b><template v-if="r.nameCn"><span class="dim">　{{ r.nameCn }}</span></template><template v-else><span class="dim">　中文定名未公布</span></template></td>
              <td class="mono">{{ r.sizeClaim || '未写' }} 人</td>
              <td>
                <template v-if="clientOf[r.id]">有这一条：{{ sizeText(clientOf[r.id]) }}、{{ entryText(clientOf[r.id]) }}</template>
                <template v-else><span class="dim">没有对应的排队条目</span></template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 团本名单 · 与旧站 src/js/app.js 的 raids()（行 2033-2212）逐块对齐。
   同名两条排队条目归并成一座，条目数留着说清是「两种规模」还是「两个入口」；
   queues（能排到但没名单的）与 dungeons.json 的 raids 数组对照呈现，两源分歧两个都摆。
   2026-10-12 站主决定：这一页只留两份名单本身的数与表，讲来路的说明已删，出处集中在溯源页。 */
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import { linkFor } from '../lib/nav.js';

const HERO = 'img/gen/banner-cloudsea.webp';
/* 各团本的氛围底图：本站自生成，取不到退回页首同一张，不拿不相干的图凑数 */
const CARD_ART = { 'barrow-deeps': 'img/gen/cavern-hall.webp', 'hyjal-summit': HERO,
  'onyxias-lair': 'img/gen/hero-ruins.webp' };

const D = ref(null);
const err = ref('');
const artBad = ref({});
const route = useRoute();
const q = ref(String(route.query.q || ''));   // 旧站 urlQ('q')：落地带着筛好的词

function boot() {
  err.value = '';
  /* queue.json 与 timeline.json 取不到就按空表出页，不整页报错（与旧站同一兜底口径） */
  Promise.all([load('data/queue.json').catch(() => ({})), load('data/dungeons.json'),
    load('data/timeline.json').catch(() => ({ items: [] }))])
    .then((rs) => { D.value = { QU: rs[0] || {}, DG: rs[1], TL: (rs[2] || {}).items || [] }; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时重新拉一次

/* 数据整理与旧站 raids() 同一份算法：按 nameEn 归并、规模降序、 matchedId 判定对上了哪份名单 */
const P = computed(() => {
  if (!D.value) return null;
  const QU = D.value.QU, DG = D.value.DG, TL = D.value.TL;
  const rows = (QU.items || []).filter((x) => x.kind === 'raid');
  const claimed = DG.raids || [];
  const dunIds = {};
  [].concat(DG.newDungeons || [], DG.classicDungeons || []).forEach((x) => { dunIds[x.id] = x; });
  const raidById = {};
  claimed.forEach((x) => { raidById[x.id] = x; });
  const grp = {}, order = [];
  rows.forEach((x) => {
    if (!grp[x.nameEn]) { grp[x.nameEn] = []; order.push(x.nameEn); }
    grp[x.nameEn].push(x);
  });
  const names = order.map((k) => {
    const list = grp[k], sizes = [], diffs = {};
    let matched = null;
    list.forEach((x) => {
      if (x.partySize && sizes.indexOf(x.partySize) < 0) sizes.push(x.partySize);
      if (x.matchedId && !matched) matched = x.matchedId;
      diffs[String(x.partySize)] = 1;
    });
    sizes.sort((a, b) => b - a);
    const matchedIn = matched ? (raidById[matched] ? 'raid' : (dunIds[matched] ? 'dungeon' : '')) : '';
    let st = null;
    if (matchedIn === 'raid') {
      const rr = raidById[matched];
      st = { label: (rr && (rr.nameCn || rr.nameEn)) || matched, link: dLinkProps(matched) };
    } else if (matchedIn === 'dungeon') {
      const dn = dunIds[matched];
      st = { label: (dn && dn.nameCn) || matched, link: dLinkProps(matched) };
    }
    return { nameEn: k, entries: list.length, sizes: sizes,
      multiSize: Object.keys(diffs).length > 1,
      levelRange: list[0].levelRange,
      matched: matched, matchedIn: matchedIn, st: st,
      prov: list[0].provenance || [] };
  });
  names.sort((a, b) => (b.sizes[0] || 0) - (a.sizes[0] || 0) || a.nameEn.localeCompare(b.nameEn));
  const both = names.filter((x) => x.matchedIn === 'raid').length;
  const nextRaid = TL.filter((x) => /团本|团队副本/.test(x.title || ''))[0] || null;
  const beta = TL.filter((x) => /国服 Beta 开启/.test(x.title || ''))[0] || null;
  const launch = TL.filter((x) => /国服/.test(x.title || '') && /上线/.test(x.title || ''))[0] || null;
  const named = claimed.filter((r) => r.nameCn).length;
  return { claimed: claimed, names: names, both: both, nextRaid: nextRaid, beta: beta,
    launch: launch, named: named };
});

function sizeText(x) { return x.sizes.length ? x.sizes.join(' / ') + ' 人' : '未标'; }
function entryText(x) {
  if (x.entries < 2) return '1 条';
  return x.entries + ' 条（' + (x.multiSize ? '两种规模' : '同规模的两个入口') + '）';
}

/* 客户端里对得上这座团本的那条排队条目（多条时取旧站 filter()[0] 同款的第一条） */
const clientOf = computed(() => {
  const m = {};
  if (P.value) P.value.names.forEach((x) => { if (x.matchedIn === 'raid' && !m[x.matched]) m[x.matched] = x; });
  return m;
});

const cards = computed(() => {
  if (!P.value) return [];
  return P.value.claimed.map((r) => {
    const inClient = clientOf.value[r.id];
    const sizes = [];
    if (r.sizeClaim) sizes.push(String(r.sizeClaim));
    if (inClient && inClient.sizes) inClient.sizes.forEach((s) => {
      if (sizes.indexOf(String(s)) < 0) sizes.push(String(s));
    });
    return { r: r, inClient: !!inClient, sizes: sizes,
      bosses: (r.bosses || []).length,
      art: CARD_ART[r.id] || HERO,
      link: dLinkProps(r.id) };
  });
});

const raidDate = computed(() => ((P.value && P.value.nextRaid)
  ? P.value.nextRaid.date.slice(5).replace('-', ' 月 ') + ' 日' : ''));

const shown = computed(() => {
  const k = q.value.trim().toLowerCase();
  if (!P.value) return [];
  return k ? P.value.names.filter((x) => x.nameEn.toLowerCase().indexOf(k) >= 0) : P.value.names;
});

/* 三步带：Beta → 国服上线 → 新团本，节点有无决定连线有无 */
const tlSeq = computed(() => {
  if (!P.value) return [];
  const seq = [];
  if (P.value.beta) seq.push({ lab: '国服 Beta 进行中', col: 'var(--ok)', date: P.value.beta.date });
  if (P.value.beta && P.value.launch) seq.push({ link: true });
  if (P.value.launch) seq.push({ lab: P.value.launch.title, col: 'var(--gold)', date: P.value.launch.date });
  if (P.value.launch && P.value.nextRaid) seq.push({ link: true });
  if (P.value.nextRaid) seq.push({ lab: P.value.nextRaid.title, col: 'var(--warn)', date: P.value.nextRaid.date });
  return seq;
});

/* 人数分档带：40/25/20/15/10 各一段，剩下的进「人数未标」 */
const bands = computed(() => {
  const out = [];
  [40, 25, 20, 15, 10].forEach((n) => {
    const pick = shown.value.filter((x) => (x.sizes[0] || 0) === n);
    if (!pick.length) return;
    out.push({ key: String(n), label: n + ' 人团队条目', count: pick.length, rows: pick });
  });
  const rest = shown.value.filter((x) => [40, 25, 20, 15, 10].indexOf(x.sizes[0] || 0) < 0);
  if (rest.length) out.push({ key: 'rest', label: '人数未标', count: null, rows: rest });
  return out;
});

function onFilter(e) { q.value = e.target.value; }

function dLinkProps(id) {
  const l = linkFor('dungeon.html');
  return l.to ? { to: { path: l.to, query: { d: id } } }
    : { href: l.href + '?d=' + encodeURIComponent(id) };
}
const TL_LINK = (() => {
  const l = linkFor('timeline.html');
  return l.to ? { to: { path: l.to } } : { href: l.href };
})();
</script>
