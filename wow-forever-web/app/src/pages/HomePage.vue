<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="S">
    <section class="card hero dh mhero">
      <!-- 整幅底图带与旧站同一件：图是本站自生成的氛围图，角标必须写明"非游戏原画" -->
      <img class="dhbg" :src="HERO_ART" alt="" style="object-position:center 42%"><span class="dhx"></span>
      <span class="dmark">示意图 · 本站自生成，非游戏原画</span>
      <div class="herot">
        <span class="bbadge"><i></i>测试服进行中 · 客户端 {{ buildTail }}</span>
        <h1 class="pt">回到最初的世界<br><em>探索无限的可能</em></h1>
        <p class="lead">天赋、区域与稀有、副本掉落、专业配方、种族组合、中英术语——每条数据都挂着来源与核对状态，没核实的地方直接写「待实测」，不编也不机翻。</p>
        <SiteSearch :total="S.search || 0" :initial="String($route.query.q || '')" />
        <div class="herobtns">
          <a class="cta cta-line" :href="legacy('updates.html')">看这一版改了什么</a>
          <a class="cta cta-mute" :href="legacy('chooser.html')">不知道选哪个职业：做 7 题玩法问答</a>
        </div>
        <CovBar :cov="cov" />
        <div class="covnum">
          <span v-for="k in ['L0', 'L1', 'L2', 'L3']" :key="k" class="pill" :class="k">
            {{ PILL_NAME[k] }} <b>{{ cov[k] || 0 }}</b>
          </span>
          <span class="dim mono">全站 {{ cov.total }} 条（含天赋节点）</span>
        </div>
        <p class="note">数据基线：{{ meta.dataBaseline.build }}，核对于 {{ meta.dataBaseline.checkedAt }}；本站统计 {{ gen }}。本站基于测试服资料整理，正式服上线后需整体重核。</p>
      </div>
      <!-- 读数框里只放倒计时：旧站这条被对拍与断言双双钉住（框里混进链接就算回归） -->
      <aside class="heros">
        <div class="cd">
          <div class="cdrow"><b class="mono">{{ left.d }}</b><span>天</span><i class="mono">{{ clockText(left) }}</i></div>
          <p class="dim">到正式服上线（{{ meta.launch }}）· 差秒按本地时钟走</p>
        </div>
      </aside>
    </section>

    <!-- 下面三块是稿子首页的骨架：选择你的职业 → 六个入口 → 四条读数。
         数字全部从 scale.json 现取，稿子里写死的 753 / 5353 / 6 开放 一个都不抄。 -->
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
      <div class="tools6">
        <a v-for="t in TOOLS6" :key="t[1]" class="tool plate" :href="legacy(t[0])">
          <span class="tico"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke-width="1.8" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="1" /><path d="M9 12h6M12 9v6" /></svg></span>
          <h3>{{ t[1] }}</h3><p>{{ t[3] }}</p>
          <span class="foot"><em>{{ t[2] }}</em><i>进入 →</i></span>
        </a>
      </div>
    </section>

    <section class="stats4 plate big">
      <div v-for="x in STATS4" :key="x[1]" class="scell"><b>{{ x[0] }}</b><span>{{ x[1] }}</span></div>
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
        <p class="dim">按十级一档排的 {{ S.dungeons }} 座本：首领名单、谁掉什么、等级区间两说的地方两个都留着。</p>
        <div class="kv"><span>无限新增</span><b>{{ S.dungeonsNew }} 座</b></div>
        <div class="kv"><span>首领名单</span><LevelPill level="L2" /></div>
        <div class="kv"><span>掉落写百分比吗</span><b>不写</b></div>
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

    <template v-for="g in MOD_GROUPS" :key="g.line">
      <div class="grphead"><h2>{{ g.line }}</h2><span>{{ g.items.length }} 个板块</span></div>
      <div class="modgrid">
        <a v-for="m in g.items" :key="m.href" class="mod" :class="{ hasart: !!m.art }" :href="legacy(m.href)">
          <span v-if="m.art" class="bgart" aria-hidden="true" :style="{ backgroundImage: 'url(' + m.art + ')' }"></span>
          <div class="mline">{{ m.kicker }}</div>
          <h2>{{ m.t }}</h2>
          <p class="dim">{{ m.p }}</p>
          <div class="modn">
            <span v-for="n in m.n" :key="n[1]"><b class="mono">{{ n[0] }}</b>{{ n[1] }}</span>
          </div>
          <div class="modf"><LevelPill :level="m.lv" /><span class="dim">{{ m.note }}</span></div>
        </a>
      </div>
    </template>

    <div class="grphead"><h2>自经典旧世以来的改动</h2><span>客户端解包 · {{ S.changes }} 条</span></div>
    <section class="card">
      <div class="mline">改动清单 · <b>{{ S.changes }}</b> 条 · 与来源站自报计数逐项一致</div>
      <div class="four">
        <div><b>{{ S.changesNew }}</b><s>新增天赋</s></div>
        <div><b>{{ S.changesModified }}</b><s>改动天赋</s></div>
        <div><b>{{ S.changesRemoved }}</b><s>移除</s></div>
        <div><b>{{ S.changesSpellsChanged }}</b><s>法术有变</s></div>
      </div>
      <div class="kv"><span>这四格加起来比上面的 {{ S.changes }} 少 {{ S.changes - chgSum }} 条</span>
        <b>{{ S.changes }} = 天赋 {{ S.changesTalents }} + 法术 {{ S.changes - S.changesTalents }}</b></div>
      <p class="dim">清单把 {{ S.changes }} 条客户端条目都列了出来，其中 {{ chgSum }} 条在无限服真的动了（新增、改动、移除，或法术说明有变）；剩下的只是列进对照表、本身没变。</p>
      <div class="kv"><span>只放名称与改动类别，前后对照的句子是别人转述的，本站不复制</span>
        <a class="mono" :href="legacy('updates.html')">→ updates.html</a></div>
      <div class="kv"><span>资料最全的职业</span><b>{{ cnOf(rankFirst.classId) }} {{ rankFirst.share }}% 有官方中文</b></div>
      <div class="kv"><span>资料最少的职业</span><b>{{ cnOf(rankLast.classId) }} {{ rankLast.share }}%</b></div>
      <div class="kv"><span>这个排行是什么</span><span class="dim">本站整理的资料完整度，不是强度排行 ·
        <a :href="legacy('rank.html')">全表 →</a></span></div>
    </section>

    <div class="grid g2">
      <div class="card">
        <h2>最新动态</h2>
        <p class="note">三件事分开说：官方公告里的时间点、客户端解包出的职业改动条数、本站自己改了什么。不做新闻转载与评价；这一页只在网页有，小程序按红线不做动态与排行。改动条数与完整度在上面的「自经典旧世以来的改动」里，同一个数不在首页摆两遍。</p>
        <!-- 与旧站 home() 同一套摘要结构：每节一个小标题 + 一个回动态页的出口，
             长句收两行，全文去动态页读（改版第三批，对拍要求两栈一致） -->
        <div class="nsec">
          <h3>官方公告里的时间点<span class="nact"><a :href="legacy('updates.html#k0')">全部 {{ recent.length }} 个 →</a></span></h3>
          <div v-for="x in recent.slice(0, 3)" :key="x.id" class="flowrow">
            <b class="mono">{{ x.date }}</b>
            <div><b class="clamp2">{{ x.title }}</b> <LevelPill :level="x.level" /><p class="dim clamp2">{{ x.what }}</p></div>
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

      <div class="card">
        <h2>这一站刻意不做的</h2>
        <p class="note">不是漏了，是决定不做。理由逐条写在这。</p>
        <div v-for="x in NOT_DOING" :key="x[0]" class="flowrow">
          <b>{{ x[0] }}</b><span class="dim">{{ x[1] }}</span>
        </div>
      </div>
    </div>
  </template>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { loadAll } from '../lib/data.js';
import { byDate, clockText, PILL_NAME, tlCounts } from '../lib/fmt.js';
import { useCountdown } from '../lib/countdown.js';
import { legacyUrl } from '../lib/nav.js';
import CovBar from '../components/CovBar.vue';
import SiteSearch from '../components/SiteSearch.vue';
import HubRail from '../components/HubRail.vue';
import TalentPreview from '../components/TalentPreview.vue';
import LevelPill from '../components/LevelPill.vue';

const legacy = legacyUrl;
const HERO_ART = 'img/gen/hero-ruins.webp';
const CHIPS = [['updates.html', '最新动态'], ['rank.html', '资料完整度排行'], ['timeline.html', '上线时间表'],
  ['provenance.html', '溯源与覆盖率'],
  ['systems.html', '系统规则'], ['skills.html', '技能书'], ['dungeons.html#todo', '还没有数据的']];
const NOT_DOING = [
  ['DPS 与强度排行', '个人主体 + 零 UGC 的类目下不做排行；而且无限服的战斗数据我们没实测过。'],
  ['宏与循环提示', '属攻略性质，本站红线不写打法。'],
  ['掉落概率', '资料里只有"谁掉什么"，没有百分比；官方说过无限服重做过掉落。'],
  ['角色查询 / 战斗日志', '要登录态与个人数据，类目与合规都不允许。'],
  ['新闻流与评论区', '只做资料与工具，不做内容 feed，也不开 UGC。']
];

const classes = ref([]);
const S = ref(null);
const meta = ref({ dataBaseline: {} });
const tl = ref([]);
const cl = ref([]);
const err = ref('');
const pv = ref({ classes: {} });
const ART = ref({});
const DUN = ref([]);
const gen = ref('');
const { left } = useCountdown();

function boot() {
  err.value = '';
  loadAll(['data/classes.json', 'data/meta.json', 'data/scale.json', 'data/timeline.json',
    'data/releases.json', 'data/talent-preview.json', 'data/art.json', 'data/dungeons.json'])
    .then(([c, m, sc, t, ch, pr, art, dg]) => {
      classes.value = c.classes || [];
      meta.value = m;
      S.value = sc.scale;
      gen.value = (sc.meta || {}).generatedAt || '';
      tl.value = t.items || [];
      cl.value = (ch && ch.items) || [];
      pv.value = pr || { classes: {} };
      ART.value = art || {};
      DUN.value = (dg && dg.newDungeons) || [];
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
onMounted(boot);

const cov = computed(() => {
  if (!S.value) return { total: 1 };
  return { L0: S.value.coverage.L0, L1: S.value.coverage.L1, L2: S.value.coverage.L2,
    L3: S.value.coverage.L3, total: S.value.coverageTotal };
});
const recent = computed(() => tl.value.slice().sort(byDate).slice(0, 3));
const rankAll = computed(() => ((S.value || {}).classRank || []).slice().sort((a, b) => a.share - b.share));
const rankFirst = computed(() => (((S.value || {}).classRank || [])[0]) || { classId: '', share: 0 });
const rankLast = computed(() => rankAll.value[0] || { classId: '', share: 0 });
// 四格之和：现算，不写死。写死的 751 与 964 会在同一张卡里互相打脸
const chgSum = computed(() => {
  const s = S.value || {};
  return (s.changesNew || 0) + (s.changesModified || 0) + (s.changesRemoved || 0) +
    (s.changesSpellsChanged || 0);
});
function cnOf(id) {
  const c = classes.value.filter((x) => x.id === id)[0];
  return c ? c.cn : id;
}
// 客户端号那一串里取最后一段（build 形如 1.60.1.70338（…对齐结果），页面上只报_build 尾号_）
const buildTail = computed(() => String(((meta.value || {}).dataBaseline || {}).build || '').split('.').pop());
function clsArt(id) {
  return ((ART.value || {}).classes || {})[id] || '';
}
/* 六个入口与四条读数：与旧站 home() 逐字同一份文案，数字全部现取。
   改这里必须同时改 src/js/app.js，否则 app-parity 会按行报差异。 */
const TOOLS6 = computed(() => {
  const s = S.value || {};
  return [
    ['talent.html', '天赋计算器', s.talentNodes + ' 个节点 · ' + s.classes + ' 职业',
      '格子里就是客户端解出来的天赋本身：位置、每层上限、与经典旧世的差异都按真结构摆，点格子进计算器并亮那一格。'],
    ['updates.html', '这一版改了什么', s.changes + ' 条改动清单',
      '官方公告里的时间点、客户端解出的职业改动、本站自己改了什么，三件事分开摆。改动只列名称与类别，不抄别人的前后对照句子。'],
    ['dungeons.html', '副本与掉落', s.dungeons + ' 座 · ' + s.bosses + ' 个首领',
      '按十级一档排：首领名单、谁掉了什么、等级区间两说的两个数都留着。掉落只回答"谁掉了什么"，不写概率。'],
    ['skills.html', '技能书', s.abilities + ' 条官方中文整句',
      '新增 / 改动 / 移除 / 未变四态与经典旧世并排；中文名出自国服官方公告的整句，名称不在句里就不收。'],
    ['professions.html', '专业与配方', s.professions + ' 个专业 · ' + s.recipes + ' 条配方',
      '每个专业的配方、所需材料与采集点，含无限新增那一批。野营那一页摆不出一条能核的清单，就不编。'],
    ['glossary.html', '中英术语速查', s.glossary + ' 条词条',
      '天赋、技能、物品、种族特长的中英对照，按职业与种族分组，两个叫法都留着，不替你做取舍。']
  ];
});
const STATS4 = computed(() => {
  const s = S.value || {}, c = cov.value;
  return [[c.L0, '条已对过官方中文'], [s.talentNodes, '个天赋节点已入库'],
    [s.dungeons, '座副本有名单'], [s.search, '条内容可搜']];
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
   背景图只用 src/img/art 里已转存的本地原画，没有对应素材的卡不加背景层。 */
const MOD_GROUPS = computed(() => {
  const s = S.value || {}, a = ART.value;
  return [
    { line: '角色线', items: [
      { href: 'races.html', lv: 'L0', t: '种族与职业组合', kicker: '角色 · 种族 ' + s.races + ' 行',
        art: (a.races || {})['skyborne'] || '',
        p: '国服官方中文公告里的 10 个种族行与可选职业矩阵，40 条种族特长带官方整句。',
        n: [[s.races, '个种族行'], [s.traits, '条特长整句'], [s.classes, '职业可选']],
        note: '整句直接抄官方，不改写' },
      { href: 'legacy.html', lv: 'L0', t: '传承专长与挑战', kicker: '角色 · 传承 · 本版新增',
        p: `三棵传承树 ${(s.legacy || {}).slots} 个槽位（${(s.legacy || {}).unknown} 个还没公开）、${(s.legacy || {}).challenges} 项挑战，客户端给的点合计 ${(s.legacy || {}).total}（其中一项给 16 点，不是每项 1 点），首发上限 ${(s.legacy || {}).cap} 点。每个专长写清上限与前置。`,
        n: [[(s.legacy || {}).perks, '个专长有明细'], [(s.legacy || {}).challenges, '项挑战'],
          [(s.legacy || {}).unknown, '格未公开']],
        note: '每层效果说明本站不复制' },
      { href: 'skills.html', lv: 'L0', t: '技能书', kicker: '角色 · 技能 · ' + s.abilities + ' 条官方整句',
        p: '按职业与种族分组的技能页；与经典旧世的差异用新增/改动/删除/未变四态标出。',
        n: [[s.glossary, '条技能书'], [s.abilities, '条官方整句']],
        note: '英文原名待补，不机翻' }
    ] },
    { line: '世界线', items: [
      { href: 'world.html', lv: 'L0', t: '区域与稀有精英', kicker: '世界 · 区域 ' + s.zones + ' 个',
        art: (a.maps || {})['1411'] || '',
        p: '每个区域多少级、什么阵营、哪只稀有在哪个坐标、掉了什么；书在哪个容器也标了。',
        n: [[s.zones, '区域'], [s.rares, '已定位稀有'], [s.books, '本书有坐标']],
        note: '刷新计时游戏里没有这个数据，不猜' },
      { href: 'professions.html', lv: 'L0', t: '专业与配方', kicker: '专业 · ' + s.professions + ' 个',
        p: '13 个专业的配方、材料数量、技能橙黄绿灰四档与采集点，能按"我的技能等级"筛。',
        n: [[s.professions, '个专业'], [s.recipes, '条配方'], [s.gatherNodes, '个采集点']],
        note: '冲级路线与性价比建议属攻略，不做' },
      { href: 'glossary.html', lv: 'L0', t: '中英术语速查', kicker: '世界 · 词条 ' + s.glossary + ' 条',
        p: '技能与天赋的中英对照，按职业与种族分组，点一下即复制；38 条带与经典旧世的四态差异。',
        n: [[s.glossary, '条词条'], [s.abilities, '条四态对照'], [s.classes, '组职业']],
        note: '只有官方英文的算 L1，不冒充已核' }
    ] },
    { line: '工具线', items: [
      { href: 'chooser.html', lv: 'L0', t: '不知道选哪个职业', kicker: '工具 · 问答 7 题',
        p: '回答 7 个玩法取向问题，给出候选与理由。每题的权重都写在页上。',
        n: [[7, '题'], [s.classes, '职业候选'], [s.talentNodes, '节点参与算分']],
        note: '本站整理的取向，不是强度排行' },
      { href: 'timeline.html', lv: 'L1', t: '上线与 Beta 时间表', kicker: '工具 · 时间点 ' + s.timeline + ' 个',
        art: (a.factionCities || {})['alliance'] || '',
        p: '官方给过的时间点、已过与待来，以及上线日期为什么有两个说法。',
        n: [[s.timeline, '个时间点'], [tlCounts(tl.value).done, '个已过'], [tlCounts(tl.value).upcoming, '个待来']],
        note: '两说两个都留，不挑一个当准' },
      { href: 'systems.html', lv: 'L1', t: '系统与新区域', kicker: '工具 · 规则条目',
        p: '规则、区域、种族与装备名的官方中文说法，逐条带来源。',
        n: [[s.newZones, '个新区域'], [s.pubTotal, '条对外词条']],
        note: '没有中文整句的标出来，不猜' }
    ] }
  ];
});
</script>
