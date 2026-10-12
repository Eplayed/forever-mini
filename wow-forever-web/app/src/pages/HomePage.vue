<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="S">
    <section class="card hero dh mhero">
      <!-- 整幅底图带：本站自生成的氛围图。2026-10-12 站主决定内容页不挂素材出处角标，
           图的来路记在 src/img/art/manifest.json 与溯源页，页面上不再写。 -->
      <img class="dhbg" :src="HERO_ART" alt="" style="object-position:center 42%"><span class="dhx"></span>
      <div class="herot">
        <span class="bbadge"><i></i>测试服进行中 · 客户端 {{ buildTail }}</span>
        <h1 class="pt">回到最初的世界<br><em>探索无限的可能</em></h1>
        <p class="lead">天赋、区域与稀有、副本掉落、专业配方、种族组合、中英术语。</p>
        <SiteSearch :total="S.search || 0" :initial="String($route.query.q || '')" />
        <!-- 2026-10-12 用户决定：首页 hero 不再放覆盖率条、L0-L3 四枚徽标与「数据基线…」那行，
             也不放四条规模读数——出处与数据质量集中在溯源页说，首页只留标题、搜索与入口。 -->
        <div class="herobtns">
          <a class="cta cta-line" :href="legacy('updates.html')">看这一版改了什么</a>
          <a class="cta cta-mute" :href="legacy('chooser.html')">不知道选哪个职业：做 7 题玩法问答</a>
        </div>
      </div>
      <!-- 读数框里只放倒计时：旧站这条被对拍与断言双双钉住（框里混进链接就算回归） -->
      <aside class="heros">
        <div class="cd">
          <div class="cdrow"><b class="mono">{{ left.d }}</b><span>天</span><i class="mono">{{ clockText(left) }}</i></div>
          <p class="dim">到正式服上线（{{ launchDay }}）</p>
        </div>
      </aside>
    </section>

    <!-- 下面几块是稿子首页的骨架：选择你的职业 → 六个入口 → 板块图标轨 → 常用两卡。
         数字全部从 scale.json 现取，稿子里写死的 753 / 5353 / 6 开放 一个都不抄。 -->
    <!-- 这九格点进去是"那一职业的天赋计算器"，不是职业页——2026-10-12 用户实拍后确认这样是对的，
         别"顺手"改成 classes.html：这一节的语义是"选一个职业开始加点"。 -->
    <section class="hsec">
      <div class="krow">
        <div><div class="kicker">CHOOSE YOUR CLASS</div><h2>选择你的职业</h2></div>
        <a class="kall" :href="legacy('chooser.html')">7 题玩法问答 · 帮你定一个 →</a>
      </div>
      <div class="cls9">
        <a v-for="c in classes" :key="c.id" :href="legacy('talent.html?c=' + encodeURIComponent(c.id))">
          <img v-if="clsArt(c.id)" :src="clsArt(c.id)" alt="" loading="lazy">
          <i v-else class="hrt-x">{{ (c.cn || '?').charAt(0) }}</i>
          <b>{{ c.cn }}</b>
        </a>
      </div>
    </section>

    <section class="hsec">
      <div class="krow"><div><div class="kicker">EXPLORE TOOLS</div><h2>这座站的六个入口</h2></div></div>
      <!-- 2026-10-12 站主决定：六个入口卡只留标题与条数，讲"这页的数据从哪来、本站不做什么"
           的那句说明已删掉，出处集中在溯源页。 -->
      <div class="tools6">
        <a v-for="t in TOOLS6" :key="t[1]" class="tool plate" :href="legacy(t[0])">
          <span class="tico"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke-width="1.8" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="1" /><path d="M9 12h6M12 9v6" /></svg></span>
          <h3>{{ t[1] }}</h3>
          <span class="foot"><em>{{ t[2] }}</em><i>进入 →</i></span>
        </a>
      </div>
    </section>

    <HubRail :art="ART" :nav-new="S.navNew || []" />

    <div class="sect"><h2>最常用的两个</h2></div>
    <div class="two">
      <TalentPreview :preview="pv" :classes="classes" :scale="S" :art="ART" />
      <section class="card hasart">
        <span class="bgart" aria-hidden="true" :style="dunBg"></span>
        <div class="mline">世界 · 副本 · <b>{{ S.dungeons }}</b> 座 <b>{{ S.bosses }}</b> 首领
          <b>{{ S.drops }}</b> 条掉落归属</div>
        <h2>副本手册</h2>
        <div class="kv"><span>无限新增</span><b>{{ S.dungeonsNew }} 座</b></div>
        <div class="mline" style="margin-top:var(--s3)">无限新增的 {{ DUN.length }} 座</div>
        <div v-for="x in newDungeons" :key="x.id" class="dunrow">
          <i aria-hidden="true" :style="x.art ? { backgroundImage: 'url(' + x.art + ')' } : {}"></i>
          <b>{{ x.nameCn }}</b>
          <span class="dim mono">{{ dunLv(x) }}</span>
          <span class="dim mono">{{ (x.bosses || []).length ? (x.bosses || []).length + ' 首领' : '首领待补' }}</span>
        </div>
        <a class="cta" :href="legacy('dungeons.html')">按十级一档看全部 {{ S.dungeons }} 座 →</a>
      </section>
    </div>

    <div class="chipsrow">
      <span class="dim">还要去哪：</span>
      <a v-for="x in CHIPS" :key="x[0]" :href="legacy(x[0])">{{ x[1] }} →</a>
    </div>

    <!-- 板块卡：2026-10-12 站主决定只留板块归属、标题与规模读数，
         讲数据出处与取舍的那两句（p 与 modf）已删掉，出处集中在溯源页。 -->
    <template v-for="g in MOD_GROUPS" :key="g.line">
      <div class="grphead"><h2>{{ g.line }}</h2><span>{{ g.items.length }} 个板块</span></div>
      <div class="modgrid">
        <a v-for="m in g.items" :key="m.href" class="mod" :class="{ hasart: !!m.art }" :href="legacy(m.href)">
          <span v-if="m.art" class="bgart" aria-hidden="true" :style="{ backgroundImage: 'url(' + m.art + ')' }"></span>
          <div class="mline">{{ m.kicker }}</div>
          <h2>{{ m.t }}</h2>
          <div class="modn">
            <span v-for="n in m.n" :key="n[1]"><b class="mono">{{ n[0] }}</b>{{ n[1] }}</span>
          </div>
        </a>
      </div>
    </template>

    <div class="grphead"><h2>自经典旧世以来的改动</h2><span>{{ S.changes }} 条</span></div>
    <section class="card">
      <div class="mline">改动清单 · <b>{{ S.changes }}</b> 条</div>
      <div class="four">
        <div><b>{{ S.changesNew }}</b><s>新增天赋</s></div>
        <div><b>{{ S.changesModified }}</b><s>改动天赋</s></div>
        <div><b>{{ S.changesRemoved }}</b><s>移除</s></div>
        <div><b>{{ S.changesSpellsChanged }}</b><s>法术有变</s></div>
      </div>
      <!-- 这两行不是说明文案，是数与数之间的对照：全部条目与四格之和同屏出现，
           不把差在哪写清楚就是自己打脸。 -->
      <div class="kv"><span>这四格加起来比上面的 {{ S.changes }} 少 {{ S.changes - chgSum }} 条</span>
        <b>{{ S.changes }} = 天赋 {{ S.changesTalents }} + 法术 {{ S.changes - S.changesTalents }}</b></div>
      <p class="dim">清单把 {{ S.changes }} 条客户端条目都列了出来，其中 {{ chgSum }} 条在无限服真的动了（新增、改动、移除，或法术说明有变）；剩下的只是列进对照表、本身没变。</p>
    </section>

    <!-- 原来这里是 .grid.g2 两栏（最新动态 + 「这一站刻意不做的」）；后一张卡按站主决定撤掉后只剩一张，
         两栏会空出半行，所以连壳一起换成整宽单卡。 -->
    <div class="card">
      <h2>最新动态</h2>
      <p class="note">三件事分开说：官方公告里的时间点、客户端里的职业改动、本站自己改了什么。</p>
      <!-- 与旧站 home() 同一套摘要结构：每节一个小标题 + 一个回动态页的出口，
           长句收两行，全文去动态页读（改版第三批，对拍要求两栈一致） -->
      <div class="nsec">
        <h3>官方公告里的时间点<span class="nact"><a :href="legacy('updates.html#k0')">全部 {{ recent.length }} 个 →</a></span></h3>
        <div v-for="x in recent.slice(0, 3)" :key="x.id" class="flowrow">
          <b class="mono">{{ x.date }}</b>
          <div><b class="clamp2">{{ x.title }}</b><p class="dim clamp2">{{ x.what }}</p></div>
        </div>
      </div>
      <div v-if="cl.length" class="nsec">
        <h3>本站最近改了什么<span class="nact"><a :href="legacy('updates.html#k2')">全部 {{ cl.length }} 条 →</a></span></h3>
        <div v-for="(e, i) in cl.slice(0, 3)" :key="i" class="flowrow">
          <b class="mono">{{ e.date }}</b><div><b class="clamp2">{{ e.title }}</b></div>
        </div>
      </div>
      <a class="cta" :href="legacy('updates.html')">全部动态（{{ S.timeline }} 个时间点 · {{ S.changes }} 条改动 · {{ cl.length }} 条本站更新）→</a>
      <a class="cta" :href="legacy('rank.html')">资料完整度排行全表 →</a>
    </div>
  </template>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { loadAll } from '../lib/data.js';
import { byDate, clockText, tlCounts } from '../lib/fmt.js';
import { useCountdown } from '../lib/countdown.js';
import { legacyUrl } from '../lib/nav.js';
import SiteSearch from '../components/SiteSearch.vue';
import HubRail from '../components/HubRail.vue';
import TalentPreview from '../components/TalentPreview.vue';

const legacy = legacyUrl;
const HERO_ART = 'img/gen/hero-ruins.webp';
// 「还没有数据的」那个 chip 指向 dungeons.html#todo——那张缺口卡已按站主决定撤掉，锚点也就没了
const CHIPS = [['updates.html', '最新动态'], ['rank.html', '资料完整度排行'], ['timeline.html', '上线时间表'],
  ['provenance.html', '溯源与覆盖率'], ['systems.html', '系统规则'], ['skills.html', '技能书']];

const classes = ref([]);
const S = ref(null);
const meta = ref({ dataBaseline: {} });
const tl = ref([]);
const cl = ref([]);
const err = ref('');
const pv = ref({ classes: {} });
const ART = ref({});
const DUN = ref([]);
const { left } = useCountdown();

function boot() {
  err.value = '';
  loadAll(['data/classes.json', 'data/meta.json', 'data/scale.json', 'data/timeline.json',
    'data/releases.json', 'data/talent-preview.json', 'data/art.json', 'data/dungeons.json'])
    .then(([c, m, sc, t, ch, pr, art, dg]) => {
      classes.value = c.classes || [];
      meta.value = m;
      S.value = sc.scale;
      tl.value = t.items || [];
      cl.value = (ch && ch.items) || [];
      pv.value = pr || { classes: {} };
      ART.value = art || {};
      DUN.value = (dg && dg.newDungeons) || [];
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
onMounted(boot);

const recent = computed(() => tl.value.slice().sort(byDate).slice(0, 3));
// 四格之和现算，不写死：写死的数会在同一张卡里与"全部条目"互相打脸
const chgSum = computed(() => {
  const s = S.value || {};
  return (s.changesNew || 0) + (s.changesModified || 0) + (s.changesRemoved || 0) +
    (s.changesSpellsChanged || 0);
});
// 客户端号那一串里取最后一段（build 形如 1.60.1.70338（…对齐结果），页面上只报_build 尾号_）
// 客户端号只报 build 尾号：字段里括号那段（"天赋树成品仍是两份第三方资料站…的对齐结果"）
// 是我们自己的核对备注，不上页面。取号先按括号截断，再按点取最后一段（与旧站 buildTail 同一条规则）
const buildTail = computed(() => String(((meta.value || {}).dataBaseline || {}).build || '')
  .split('（')[0].split('.').pop());
// 倒计时那一行只写日期本体（YYYY-MM-DD），与旧站 LAUNCH.slice(0, 10) 同一个取法
const launchDay = computed(() => String(((meta.value || {}).launch) || '').slice(0, 10));
function clsArt(id) {
  return ((ART.value || {}).classes || {})[id] || '';
}
/* 六个入口：与旧站 home() 逐字同一份文案与条数，数字全部现取。
   改这里必须同时改 src/js/app.js，否则 app-parity 会按行报差异。 */
const TOOLS6 = computed(() => {
  const s = S.value || {};
  return [
    ['talent.html', '天赋计算器', s.talentNodes + ' 个节点 · ' + s.classes + ' 职业'],
    ['updates.html', '这一版改了什么', s.changes + ' 条改动清单'],
    ['dungeons.html', '副本与掉落', s.dungeons + ' 座 · ' + s.bosses + ' 个首领'],
    ['skills.html', '技能书', s.abilities + ' 条'],
    ['professions.html', '专业与配方', s.professions + ' 个专业 · ' + s.recipes + ' 条配方'],
    ['glossary.html', '中英术语速查', s.glossary + ' 条词条']
  ];
});
// 副本卡背景取第一座"无限新增"本的载入图；素材没到位就不加背景层
const newDungeons = computed(() => DUN.value);
const dunBg = computed(() => {
  const x = DUN.value.filter((y) => y.art)[0];
  return x ? { backgroundImage: 'url(' + x.art + ')' } : {};
});
function dunLv(x) {
  const r = x.levelRange;
  if (typeof r === 'string') return r + ' 级';
  return (r || [])[0] ? r.join('–') + ' 级' : '等级待补';
}

/* 模块按三条线分组；天赋与副本已升为「最常用的两个」，这里不再重复出现。
   背景图只用 src/img/art 里已转存的本地原画，没有对应素材的卡不加背景层。
   卡上只有板块归属、标题与规模读数——出处与取舍说明按 2026-10-12 站主决定不上内容页。 */
const MOD_GROUPS = computed(() => {
  const s = S.value || {}, a = ART.value;
  return [
    { line: '角色线', items: [
      { href: 'races.html', t: '种族与职业组合', kicker: '角色 · 种族 ' + s.races + ' 行',
        art: (a.races || {})['skyborne'] || (a.races || {})['alliance'] || '',
        n: [[s.races, '个种族行'], [s.traits, '条特长整句'], [s.classes, '职业可选']] },
      { href: 'legacy.html', t: '传承专长与挑战', kicker: '角色 · 传承 · 本版新增',
        n: [[(s.legacy || {}).perks, '个专长有明细'], [(s.legacy || {}).challenges, '项挑战'],
          [(s.legacy || {}).unknown, '格未公开']] },
      { href: 'skills.html', t: '技能书', kicker: '角色 · 技能 · ' + s.abilities + ' 条',
        n: [[s.glossary, '条技能书'], [s.abilities, '条官方整句']] }
    ] },
    { line: '世界线', items: [
      { href: 'world.html', t: '区域与稀有精英', kicker: '世界 · 区域 ' + s.zones + ' 个',
        art: (a.maps || {})['1411'] || '',
        n: [[s.zones, '区域'], [s.rares, '已定位稀有'], [s.books, '本书有坐标']] },
      { href: 'professions.html', t: '专业与配方', kicker: '专业 · ' + s.professions + ' 个',
        n: [[s.professions, '个专业'], [s.recipes, '条配方'], [s.gatherNodes, '个采集点']] },
      { href: 'glossary.html', t: '中英术语速查', kicker: '世界 · 词条 ' + s.glossary + ' 条',
        n: [[s.glossary, '条词条'], [s.abilities, '条四态对照'], [s.classes, '组职业']] }
    ] },
    { line: '工具线', items: [
      { href: 'chooser.html', t: '不知道选哪个职业', kicker: '工具 · 问答 7 题',
        n: [[7, '题'], [s.classes, '职业候选'], [s.talentNodes, '节点参与算分']] },
      { href: 'timeline.html', t: '上线与 Beta 时间表', kicker: '工具 · 时间点 ' + s.timeline + ' 个',
        art: (a.factionCities || {})['alliance'] || '',
        n: [[s.timeline, '个时间点'], [tlCounts(tl.value).done, '个已过'], [tlCounts(tl.value).upcoming, '个待来']] },
      { href: 'systems.html', t: '系统与新区域', kicker: '工具 · 规则条目',
        n: [[s.newZones, '个新区域'], [s.pubTotal, '条对外词条']] }
    ] }
  ];
});
</script>
