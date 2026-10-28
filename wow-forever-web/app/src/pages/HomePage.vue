<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="S">
    <section class="card hero dh mhero">
      <!-- 整幅底图带：本站自生成的氛围图。2026-10-12 站主决定内容页不挂素材出处角标，
           图的来路记在 app/img/art/manifest.json 与溯源页，页面上不再写。 -->
      <img class="dhbg" :src="HERO_ART" alt="" style="object-position:center 42%"><span class="dhx"></span>
      <div class="herot">
        <!-- 2026-10-25：不再报"全站一个客户端号"。各板块核到的版本不一样（传承 70532、
             改动清单 70425、世界 70338），报一个号就是假数；这里只报最新核到的那个，
             并写明是哪一块，值从规模快照现取。 -->
        <span class="bbadge"><i></i>测试服进行中 · 最新核到客户端 {{ newestTail }}<template v-if="newestSection">（{{ newestSection }}）</template></span>
        <h1 class="pt">回到最初的世界<br><em>探索无限的可能</em></h1>
        <p class="lead">天赋、区域与稀有、副本掉落、专业配方、种族组合、中英术语。</p>
        <SiteSearch :total="S.search || 0" :initial="String($route.query.q || '')" />
        <!-- 2026-10-12 用户决定：首页 hero 不再放覆盖率条、L0-L3 四枚徽标与「数据基线…」那行，
             也不放四条规模读数——出处与数据质量集中在溯源页说，首页只留标题、搜索与入口。 -->
        <div class="herobtns">
          <a class="cta cta-line" :href="hrefOf('updates.html')">看这一版改了什么</a>
          <a class="cta cta-mute" :href="hrefOf('chooser.html')">不知道选哪个职业：做 7 题玩法问答</a>
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
        <a class="kall" :href="hrefOf('chooser.html')">7 题玩法问答 · 帮你定一个 →</a>
      </div>
      <div class="cls9">
        <a v-for="c in classes" :key="c.id" :href="hrefOf('talent.html?c=' + encodeURIComponent(c.id))"
           :title="'打开 ' + c.cn + ' 的天赋计算器'">
          <img v-if="clsArt(c.id)" :src="clsArt(c.id)" alt="" loading="lazy">
          <i v-else class="hrt-x">{{ (c.cn || '?').charAt(0) }}</i>
          <b>{{ c.cn }}</b>
          <small v-if="c.talentCount">{{ c.talentCount }} 点</small>
        </a>
      </div>
    </section>

    <!-- 2026-10-13 用户实拍：入口重复了——六个文字入口卡撤掉，留下面那条带图的图标轨。
         板块卡改成"一张卡 = 一个去处"，每张配 art/ 下已转存的真原画（取不到留纯色，不拿图标放大）。 -->
    <HubRail :art="ART" :nav-new="S.navNew || []" />

    <!-- 两张主推卡整卡可点（「最常用的两个」那行标题按用户要求撤掉）。
         data-go 的跳转由 goCard() 做：点在卡里的链接、按钮、格子、职业条上时不抢它们自己的去向。 -->
    <div class="two">
      <TalentPreview :preview="pv" :classes="classes" :scale="S" :art="ART" />
      <section class="card hasart go" tabindex="0" :data-go="hrefOf('dungeons.html')" @click="goCard"
               @keydown="goKey">
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
        <a class="cta" :href="hrefOf('dungeons.html')">按十级一档看全部 {{ S.dungeons }} 座 →</a>
      </section>
    </div>

    <!-- 入口卡：卡上只有板块归属、标题与一行读数（出处与取舍说明按 3a 不上内容页）。
         分组眉标只写组名，不再挂"N 个板块"那种计数。 -->
    <template v-for="g in MOD_GROUPS" :key="g.line">
      <div class="grphead"><h2>{{ g.line }}</h2></div>
      <div class="modgrid">
        <a v-for="m in g.items" :key="m.href" class="mod hasart" :href="hrefOf(m.href)">
          <span v-if="m.art" class="bgart" aria-hidden="true" :style="{ backgroundImage: 'url(' + m.art + ')' }"></span>
          <div class="mline">{{ m.kicker }}</div>
          <h2>{{ m.t }}</h2>
          <div class="modn">
            <span v-for="n in m.n" :key="n[1]"><b class="mono">{{ n[0] }}</b>{{ n[1] }}</span>
          </div>
        </a>
      </div>
    </template>

    <!-- 「自经典旧世以来的改动」那四格与"全部 vs 四格之和"的对照行搬去动态页
         （2026-10-13 用户：那是数据明细，首页要的是入口）。这里只留一张入口卡。 -->
    <a class="mod big hasart" :href="hrefOf('updates.html')">
      <span class="bgart" aria-hidden="true" :style="{ backgroundImage: 'url(' + (artOf(ART, 'scenes', 'yunhai') || artOf(ART, 'panels', 'talent')) + ')' }"></span>
      <div class="mline">这一版 · 客户端改动</div>
      <h2>自经典旧世以来改了什么</h2>
      <div class="modn">
        <span><b class="mono">{{ S.changes }}</b>条改动</span>
        <span><b class="mono">{{ S.changesNew }}</b>个新增天赋</span>
        <span><b class="mono">{{ cl.length }}</b>条本站更新</span>
      </div>
    </a>

    <!-- 站方那几个去处：一行文字链，点得进但不占卡位 -->
    <div class="chipsrow">
      <span class="dim">更多入口：</span>
      <!-- 走 linkFor 而不是直接写旧站地址：已迁的页留在新站，没迁的自动回落旧站，
           不用每迁一页回来改这里（物品库旧站根本没有这一页） -->
      <component v-for="x in MINILINKS" :key="x[0]" :is="linkFor(x[0]).to ? 'router-link' : 'a'"
                 v-bind="linkFor(x[0])">{{ miniText(x) }} →</component>
    </div>

    <div class="card">
      <h2>最新动态</h2>
      <p class="note">三件事分开说：官方公告里的时间点、客户端里的职业改动、本站自己改了什么。</p>
      <!-- 与旧站 home() 同一套摘要结构：每节一个小标题 + 一个回动态页的出口，
           长句收两行，全文去动态页读（改版第三批，对拍要求两栈一致） -->
      <div class="nsec">
        <h3>官方公告里的时间点<span class="nact"><a :href="hrefOf('updates.html#k0')">全部 {{ recent.length }} 个 →</a></span></h3>
        <div v-for="x in recent.slice(0, 3)" :key="x.id" class="flowrow">
          <b class="mono">{{ x.date }}</b>
          <div><b class="clamp2">{{ x.title }}</b><p class="dim clamp2">{{ x.what }}</p></div>
        </div>
      </div>
      <div v-if="cl.length" class="nsec">
        <h3>本站最近改了什么<span class="nact"><a :href="hrefOf('updates.html#k2')">全部 {{ cl.length }} 条 →</a></span></h3>
        <div v-for="(e, i) in cl.slice(0, 3)" :key="i" class="flowrow">
          <b class="mono">{{ e.date }}</b><div><b class="clamp2">{{ e.title }}</b></div>
        </div>
      </div>
      <a class="cta" :href="hrefOf('updates.html')">全部动态（{{ S.timeline }} 个时间点 · {{ S.changes }} 条改动 · {{ cl.length }} 条本站更新）→</a>
      <a class="cta" :href="hrefOf('rank.html')">资料完整度排行全表 →</a>
    </div>
  </template>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { loadAll } from '../lib/data.js';
import { byDate, clockText, tlCounts } from '../lib/fmt.js';
import { useCountdown } from '../lib/countdown.js';
import { linkFor, hrefOf } from '../lib/nav.js';
import { artOf } from '../lib/art.js';
import SiteSearch from '../components/SiteSearch.vue';
import HubRail from '../components/HubRail.vue';
import TalentPreview from '../components/TalentPreview.vue';

const HERO_ART = 'img/gen/hero-ruins.webp';
/* 站方口径的去处不做卡片（2026-10-13 用户：首页留一行小入口就够）：
   排行 / 溯源 / 系统规则 / 这一版改了什么，一行文字链。 */
/* 首页底部那行"更多入口"。2026-10-16 站主收窄导航（世界只留三格、工具只留排行）后，
   被摘掉导航的页面靠这一行 + 上面的板块卡进。**物品库与成就是这一轮补进来的**：
   全站扫了一遍引用，这两页除了导航没有任何入口，导航一摘就成了孤页。
   第三、四个元素是 scale.json 里的计数字段名与量词——数不写死，上游一动这里跟着动。
   拼成一个字符串而不是用 <b> 包一层：模板编译会压缩元素之间的空白文本节点，
   "物品库 21077" 会渲染成"物品库21077"（探针实测）。 */
const MINILINKS = [['rank.html', '资料完整度排行'], ['provenance.html', '溯源与覆盖率'],
  ['systems.html', '系统与新区域'], ['updates.html', '这一版改了什么'],
  ['items.html', '物品库', 'items', '件'], ['achievements.html', '成就目录', 'achievements', '条'],
  ['pets.html', '宠物家族', 'pets', '个']];

function miniText(x) {
  if (!x[2] || !S.value) return x[1];
  return x[1] + ' ' + S.value[x[2]] + ' ' + x[3];
}

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
// 客户端号只报尾号（70532 这种），前面那串 1.60.1 是对方自己的编号习惯，玩家不认
const newestTail = computed(() => String((S.value || {}).newestBuild || '').split('.').pop());
const newestSection = computed(() => (S.value || {}).newestSection || '');
// 倒计时那一行只写日期本体（YYYY-MM-DD），与旧站 LAUNCH.slice(0, 10) 同一个取法
const launchDay = computed(() => String(((meta.value || {}).launch) || '').slice(0, 10));
function clsArt(id) {
  return ((ART.value || {}).classes || {})[id] || '';
}
/* 整卡当入口：点在卡里的链接、按钮、天赋格子、职业条上时让给它们自己，
   只有点在卡的空白处才按 data-go 跳（与旧站 bindGo 同一套判断）。 */
function goCard(e) {
  const box = e.currentTarget;
  if (e.target && e.target.closest && e.target.closest('a, button, .stripc, .pnode, .pick')) return;
  jump(box.getAttribute('data-go'));
}
function goKey(e) {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goCard(e); }
}
function jump(href) {
  if (!href) return;
  const file = String(href).split('?')[0].replace(/\.html$/, '') + '.html';
  const l = linkFor(file.indexOf('.html') >= 0 ? file : 'index.html');
  if (l.to) {
    const q = {};
    const raw = String(href).split('?')[1] || '';
    raw.split('&').forEach((kv) => { if (kv) { const i = kv.indexOf('='); q[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); } });
    window.location.hash = l.to + (Object.keys(q).length ? '?' + new URLSearchParams(q).toString() : '');
    return;
  }
  window.location.href = href;
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

/* 入口卡两组：一张卡一个去处，配图一律从 art.json 取已转存的真原画（artOf 取不到就返回空，
   留纯色，不拿 128 的图标放大凑数——那正是用户实拍指出的问题）。
   卡上只有板块归属、标题与一行读数；出处与取舍说明按 AGENTS 3a 不上内容页。 */
const MOD_GROUPS = computed(() => {
  const s = S.value || {}, A = ART.value;
  return [
    { line: '角色与职业', items: [
      { href: 'talent.html', t: '天赋计算器', kicker: '工具 · ' + s.classes + ' 职业',
        art: artOf(A, 'panels', 'talent'),
        n: [[s.talentNodes, '个天赋节点'], [s.changesNew, '个新增天赋']] },
      { href: 'classes.html', t: '职业总览', kicker: '职业 · ' + s.classes + ' 页',
        art: artOf(A, 'classBanners', 'warrior'),
        n: [[s.classes, '个职业'], [s.abilities, '条技能说明']] },
      { href: 'chooser.html', t: '不知道选哪个职业', kicker: '工具 · 问答 7 题',
        art: artOf(A, 'classBanners', 'druid'),
        n: [[7, '题'], [s.classes, '职业候选']] },
      { href: 'skills.html', t: '技能书', kicker: '角色 · 技能',
        art: artOf(A, 'panels', 'spellbook'),
        n: [[s.spells, '条法术'], [s.abilities, '条官方整句四态']] },
      { href: 'legacy.html', t: '传承专长与挑战', kicker: '角色 · 本版新增',
        art: artOf(A, 'scenes', 'guangshu'),
        n: [[(s.legacy || {}).perks, '个专长有明细'], [(s.legacy || {}).unknown, '格未公开']] },
      { href: 'races.html', t: '种族与职业组合', kicker: '角色 · 种族 ' + s.races + ' 行',
        art: artOf(A, 'factionCities', 'alliance'),
        n: [[s.races, '个种族行'], [s.traits, '条特长整句']] }
    ] },
    { line: '世界与冒险', items: [
      { href: 'world.html', t: '区域与稀有精英', kicker: '世界 · 区域 ' + s.zones + ' 个',
        art: artOf(A, 'maps', '1411'),
        n: [[s.zones, '区域'], [s.rares, '已定位稀有'], [s.books, '本书有坐标']] },
      { href: 'dungeons.html', t: '副本与掉落', kicker: '世界 · ' + s.dungeons + ' 座',
        art: artOf(A, 'dungeons', 'city-of-dalaran'),
        n: [[s.dungeons, '座本'], [s.bosses, '个首领'], [s.drops, '条掉落']] },
      { href: 'raids.html', t: '团队副本', kicker: '世界 · 团本',
        art: artOf(A, 'scenes', 'tielu-dadian'),
        n: [[(s.raids || {}).names || 0, '个团队条目'], [(s.raids || {}).claimed || 0, '座有名单']] },
      { href: 'professions.html', t: '专业与配方', kicker: '专业 · ' + s.professions + ' 个',
        art: artOf(A, 'scenes', 'gulin'),
        n: [[s.professions, '个专业'], [s.recipes, '条配方'], [s.gatherNodes, '个采集点']] },
      { href: 'glossary.html', t: '中英术语速查', kicker: '世界 · 词条',
        art: artOf(A, 'classBanners', 'mage'),
        n: [[s.glossary, '条词条'], [s.classes, '组职业']] },
      { href: 'timeline.html', t: '上线与 Beta 时间表', kicker: '工具 · 时间点',
        art: artOf(A, 'factionCities', 'horde'),
        n: [[s.timeline, '个时间点'], [tlCounts(tl.value).done, '个已过'], [tlCounts(tl.value).upcoming, '个待来']] }
    ] }
  ];
});
</script>
