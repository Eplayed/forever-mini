<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="S">
    <section class="card hero">
      <div class="herot">
        <h1 class="pt">《魔兽世界：无限》中文资料站</h1>
        <p class="dim">天赋、区域与稀有、副本掉落、专业配方、种族组合、中英术语——每条数据都挂着来源与核对状态，没核实的地方直接写「待实测」，不编也不机翻。</p>
        <SiteSearch :total="S.search || 0" />
        <!-- 两家参考站都把"先挑职业"放在首屏：这里只做进那一职业页的入口，切树仍在下面的预览卡里 -->
        <div class="pickcls">
          <div class="mline">选择你的职业 · <b>{{ S.classes || 0 }}</b> 个职业各有一页改动、天赋与技能</div>
          <div class="clsrow">
            <a v-for="c in classes" :key="c.id" :href="legacy('talent.html?c=' + encodeURIComponent(c.id))">
              <i :style="clsBg(c.id)"></i>{{ c.cn }}
            </a>
          </div>
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
      <aside class="heros">
        <div class="cd">
          <div class="cdrow"><b class="mono">{{ left.d }}</b><span>天</span><i class="mono">{{ clockText(left) }}</i></div>
          <p class="dim">到正式服上线（{{ meta.launch }}）· 差秒按本地时钟走</p>
        </div>
        <a class="cta" :href="legacy('chooser.html')">不知道选哪个职业？做 7 题玩法问答 →</a>
        <span class="dim">问答是本站整理的玩法取向，不是强度排行。</span>
      </aside>
    </section>

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

    <div class="grphead"><h2>自经典旧世以来的改动</h2><span>客户端解包 · 964 条</span></div>
    <section class="card">
      <div class="mline">改动清单 · <b>{{ S.changes }}</b> 条 · 与来源站自报计数逐项一致</div>
      <div class="four">
        <div><b>{{ S.changesNew }}</b><s>新增天赋</s></div>
        <div><b>{{ S.changesModified }}</b><s>改动天赋</s></div>
        <div><b>{{ S.changesRemoved }}</b><s>移除</s></div>
        <div><b>{{ S.changesSpellsChanged }}</b><s>法术有变</s></div>
      </div>
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
        <p class="note">三件事分开说：官方公告里的时间点、客户端解包出的职业改动条数、本站自己改了什么。不做新闻转载与评价；这一页只在网页有，小程序按红线不做动态与排行。</p>
        <h3>官方公告里的时间点</h3>
        <div v-for="x in recent" :key="x.id" class="flowrow">
          <b class="mono">{{ x.date }}</b>
          <div><b>{{ x.title }}</b> <LevelPill :level="x.level" /><p class="dim">{{ x.what }}</p></div>
        </div>
        <h3>客户端改动与资料完整度</h3>
        <p class="note">这两块的数在上面的「自经典旧世以来的改动」里，动态页只按职业与时间列清单，同一个数不在首页摆两遍。</p>
        <template v-if="cl.length">
          <h3>本站最近改了什么</h3>
          <div v-for="(e, i) in cl.slice(0, 3)" :key="i" class="flowrow">
            <b class="mono">{{ e.date }}</b><div><b>{{ e.title }}</b></div>
          </div>
        </template>
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
import TalentPreview from '../components/TalentPreview.vue';
import LevelPill from '../components/LevelPill.vue';

const legacy = legacyUrl;
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
function cnOf(id) {
  const c = classes.value.filter((x) => x.id === id)[0];
  return c ? c.cn : id;
}
function clsBg(id) {
  const f = (ART.value.classes || {})[id];
  return f ? { backgroundImage: 'url(' + f + ')' } : {};
}
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
        p: '三棵传承树 27 个槽位（6 个还没公开）、65 项挑战各给 1 点、首发上限 16 点，每个专长写清上限与前置。',
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
