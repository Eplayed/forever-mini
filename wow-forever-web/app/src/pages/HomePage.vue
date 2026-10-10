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

    <TalentPreview :preview="pv" :classes="classes" />

    <div class="chipsrow">
      <span class="dim">还要去哪：</span>
      <a v-for="x in CHIPS" :key="x[0]" :href="legacy(x[0])">{{ x[1] }} →</a>
    </div>

    <div class="modgrid">
      <a v-for="m in MODS" :key="m.href" class="mod" :href="legacy(m.href)">
        <h2>{{ m.t }}</h2>
        <p class="dim">{{ m.p }}</p>
        <div class="modn">
          <span v-for="n in m.n" :key="n[1]"><b class="mono">{{ n[0] }}</b>{{ n[1] }}</span>
        </div>
        <div class="modf"><LevelPill :level="m.lv" /><span class="dim">{{ m.note }}</span></div>
      </a>
    </div>

    <div class="grid g2">
      <div class="card">
        <h2>最新动态</h2>
        <p class="note">三件事分开说：官方公告里的时间点、客户端解包出的职业改动条数、本站自己改了什么。不做新闻转载与评价；这一页只在网页有，小程序按红线不做动态与排行。</p>
        <h3>官方公告里的时间点</h3>
        <div v-for="x in recent" :key="x.id" class="flowrow">
          <b class="mono">{{ x.date }}</b>
          <div><b>{{ x.title }}</b> <LevelPill :level="x.level" /><p class="dim">{{ x.what }}</p></div>
        </div>
        <h3>客户端改动清单</h3>
        <div class="chgl">
          <span><b class="mono">{{ S.changes }}</b>条已入库</span>
          <span><b class="mono">{{ S.changesNew }}</b>个新增天赋</span>
          <span><b class="mono">{{ S.changesRemoved }}</b>个移除天赋</span>
          <span><b class="mono">{{ S.changes - S.changesNew - S.changesRemoved }}</b>条是改动或移位</span>
        </div>
        <p class="note">清单只列名称与改动类别，前后对照的句子本站不复制。</p>
        <h3>资料完整度前三</h3>
        <div class="chgl">
          <span v-for="x in rankTop" :key="x.classId">
            <b class="mono">{{ x.place }}</b>{{ cnOf(x.classId) }} · {{ x.official }} 条有官方中文</span>
        </div>
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
import { byDate, clockText, PILL_NAME } from '../lib/fmt.js';
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
const gen = ref('');
const { left } = useCountdown();

function boot() {
  err.value = '';
  loadAll(['data/classes.json', 'data/meta.json', 'data/scale.json', 'data/timeline.json',
    'data/releases.json', 'data/talent-preview.json'])
    .then(([c, m, sc, t, ch, pr]) => {
      classes.value = c.classes || [];
      meta.value = m;
      S.value = sc.scale;
      gen.value = (sc.meta || {}).generatedAt || '';
      tl.value = t.items || [];
      cl.value = (ch && ch.items) || [];
      pv.value = pr || { classes: {} };
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
const rankTop = computed(() => ((S.value || {}).classRank || []).slice(0, 3));
function cnOf(id) {
  const c = classes.value.filter((x) => x.id === id)[0];
  return c ? c.cn : id;
}
const MODS = computed(() => {
  const s = S.value || {};
  return [
    { href: 'talent.html', lv: 'L2', t: '全职业天赋模拟器',
      p: '九棵树都是 7 行 × 4 列的客户端真实结构，层级门槛 5 / 10 / 15 / 20 / 25 / 30，能加点、能存链接、能和经典旧世逐格对照。',
      n: [[s.classes, '职业'], [s.talentNodes, '天赋节点'], [s.talentVerified, '名与官网一致']],
      note: '结构与译名来自客户端解包，未经游戏内核实' },
    { href: 'world.html', lv: 'L0', t: '区域与稀有精英',
      p: '每个区域多少级、什么阵营、哪只稀有在哪个坐标、掉了什么；书在哪个容器也标了。',
      n: [[s.zones, '区域'], [s.rares, '已定位稀有'], [s.books, '本书有坐标']],
      note: '刷新计时游戏里没有这个数据，不猜' },
    { href: 'dungeons.html', lv: 'L2', t: '副本手册',
      p: '按十级一档排的 38 座本：首领名单、谁掉什么、等级区间两说的地方两个都留着。',
      n: [[s.dungeons, '座'], [s.bosses, '个首领'], [s.drops, '条掉落归属']],
      note: '掉落不写百分比' },
    { href: 'professions.html', lv: 'L0', t: '专业与配方',
      p: '13 个专业的配方、材料数量、技能橙黄绿灰四档与采集点，能按"我的技能等级"筛。',
      n: [[s.professions, '个专业'], [s.recipes, '条配方'], [s.gatherNodes, '个采集点']],
      note: '冲级路线与性价比建议属攻略，不做' },
    { href: 'races.html', lv: 'L0', t: '种族与职业组合',
      p: '国服官方中文公告里的 10 个种族行与可选职业矩阵，40 条种族特长带官方整句。',
      n: [[s.races, '个种族行'], [s.traits, '条特长整句'], [s.classes, '职业可选']],
      note: '整句直接抄官方，不改写' },
    { href: 'legacy.html', lv: 'L0', t: '传承专长与挑战',
      p: '三棵传承树 27 个槽位（6 个还没公开）、65 项挑战各给 1 点、首发上限 16 点，每个专长写清上限与前置。',
      n: [[(s.legacy || {}).perks, '个专长有明细'], [(s.legacy || {}).challenges, '项挑战'],
        [(s.legacy || {}).unknown, '格未公开']],
      note: '每层效果说明本站不复制' },
    { href: 'glossary.html', lv: 'L0', t: '中英术语速查',
      p: '技能与天赋的中英对照，按职业与种族分组，点一下即复制；38 条带与经典旧世的四态差异。',
      n: [[s.glossary, '条词条'], [s.abilities, '条四态对照'], [s.classes, '组职业']],
      note: '只有官方英文的算 L1，不冒充已核' }
  ];
});
</script>
