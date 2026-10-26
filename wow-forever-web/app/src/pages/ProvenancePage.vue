<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <!-- 与旧站 provenance() 逐块对齐（主卡不在 PAGE_HEAD_SEC 表里 → .cdhead.noart big）。
         全站只有这一页画分级徽标与覆盖率条：内容页那些按 2026-10-12 站主决定撤到这里来。
         lib/prov.js 的 SHOW_PROV 是给内容页的开关，本组件只挂在 /provenance 路由上，
         等价旧站 data-page="provenance" 的常开态，所以徽标与覆盖率条直接渲染（CovBar/LevelPill
         内含该开关会整体吞掉，故此处写同一份 DOM 而不经那两个组件）。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">溯源与覆盖率</h1></div>
      <p class="dim">每条数据从哪来、什么时候核的、哪些刻意没拿，全部摊在这里。内容页（天赋、副本、世界、种族那些）只放标题与数据，不挂分级徽标与来源标记——要看出处就到这一页。</p>
    </div>

    <div class="card">
      <h2>数据覆盖率</h2>
      <p class="note">这里统计的是 {{ sc.pubTotal }} 条对外词条（术语 + 副本 + 世界线），不含天赋；连九棵天赋树的节点一起算是 {{ sc.coverageTotal }} 条，多出来的 {{ sc.coverageTotal - sc.pubTotal }} 条是天赋节点。页面上只有这一处给覆盖率，内容页不再重复。</p>
      <!-- 覆盖率条：四段宽度按真实计数算（除以 pubTotal），计数为 0 的那段不渲染——与旧站 D.covBar 同一算法 -->
      <div class="cov">
        <i v-for="s in covSegs" :key="s.k" :class="s.k" :style="{ width: s.w }" :title="s.title"></i>
      </div>
      <div class="stats">
        <div v-for="k in COV_KEYS" :key="k" class="stat"><span class="pill" :class="k">{{ NAMES[k] }}</span><b>{{ cov[k] }}</b>{{ NAMES[k] }}</div>
      </div>
      <p class="dim">判定标准：一条数据只有挂着官方来源且人工核过，才算已核实；粉丝站与转载最高只算待实测。</p>
    </div>

    <!-- 各板块分别核到哪个版本（2026-10-25）。页脚不再挂一句全站版本号：
         传承核到 70532、客户端改动是 70425、世界还是 70338，一句话概括全站必然是假数。
         这张表的值由规模快照现算（谁自带版本就报谁），页面一个数都不写死。 -->
    <div class="card" v-if="dataVersions.length">
      <h2>各板块数据核到哪个版本</h2>
      <p class="note">同一天的客户端不会同时被全部板块核过，所以这里逐块报：版本号是那一份数据自己对着的客户端，
        日期是本站核对的那天。没写日期的，是那一块只留了版本、没留核对日。</p>
      <div class="boardwrap">
        <table class="board vtab" id="lver">
          <thead><tr><th>板块</th><th>对着的客户端</th><th>本站核对日</th><th>多久没核了</th><th>同时留的经典旧世版本</th></tr></thead>
          <tbody>
            <tr v-for="v in dataVersions" :key="v.file">
              <td>{{ v.section }}</td>
              <td class="mono">{{ v.build ? tail(v.build) : '—' }}</td>
              <td class="mono">{{ v.checkedAt || '未记录' }}</td>
              <td class="mono" :class="'stale-' + (v.stale || 'ok')">
                {{ v.checkedAt ? v.daysSince + ' 天' : '—' }}
                <template v-if="v.stale"> · {{ v.stale === 'red' ? '已过期' : '快过期' }}</template></td>
              <td class="mono dim">{{ v.classic ? tail(v.classic) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="dim">客户端号只报尾号（{{ newest }} 这种），前面那串是对方自己的编号习惯。
        <template v-if="stalePolicy">超过 {{ stalePolicy.soft }} 天标"快过期"，
          超过 {{ stalePolicy.hard }} 天那一块会被挡住不放行——得重抓一遍，别把日期抄新一点糊过去。</template></p>
    </div>

    <div v-if="ti" class="card">
      <h2>天赋数据来源与风险</h2>
      <div class="grid g2">
        <div>
          <h3>来源与方法</h3>
          <p class="dim">{{ ti.method }}<br>
            <template v-for="(s, i) in ti.sources || []" :key="i"><span class="mono" style="font-size:11.5px">{{ s }}</span><br></template>
            {{ ti.collectedAt }}</p>
          <div class="stats" style="margin-top:10px">
            <div class="stat"><b>{{ ti.nodes }}</b>天赋节点</div>
            <div class="stat"><b>{{ ti.nameVerified }}</b>名与官网一致</div>
            <div class="stat"><b>{{ ti.nameConflict + (sc.talentTreeConflict || 0) }}</b>译名有两个叫法<template v-if="sc.talentTreeConflict">（含 {{ sc.talentTreeConflict }} 个系名）</template></div>
            <div class="stat"><b>{{ ti.onlyInOneSource }}</b>仅单源出现</div>
            <div class="stat"><b>{{ ti.withIcon }}</b>带图标</div>
            <div class="stat"><b>{{ ti.resolvedRequires }}</b>带前置</div>
          </div>
        </div>
        <div>
          <h3>刻意没拿的部分</h3>
          <p class="dim">{{ ti.excluded }}</p>
          <h3 style="margin-top:8px">还缺什么</h3>
          <p class="dim">{{ ti.stillMissing }}</p>
          <h3 style="margin-top:8px">风险</h3>
          <p class="caution">{{ ti.risk }}</p>
        </div>
      </div>
    </div>

    <div v-if="m.steps" class="card">
      <h2>我们怎么拿到这些数据</h2>
      <p class="dim">{{ m.meta ? m.meta.note : '' }}</p>
      <div class="grid g2">
        <div v-for="(x, i) in m.steps" :key="i" class="step">
          <h3>{{ x.title }}</h3>
          <p class="dim">{{ x.body }}</p>
        </div>
      </div>
      <template v-if="m.neverTake">
        <h3 style="margin-top:var(--s4)">刻意不拿的东西</h3>
        <ul class="list"><li v-for="(x, i) in m.neverTake" :key="i">{{ x }}</li></ul>
      </template>
      <template v-if="m.onError">
        <h3 style="margin-top:var(--s4)">被指出错了怎么办</h3>
        <p class="dim">{{ m.onError }}</p>
      </template>
      <template v-if="m.recheck">
        <h3 style="margin-top:var(--s4)">什么时候重核</h3>
        <p class="dim">{{ m.recheck }}</p>
      </template>
      <p class="src">方法说明核对日期：{{ (m.meta || {}).generatedAt || '—' }}</p>
    </div>

    <div class="card">
      <h2>还没被证实的</h2>
      <ol class="q"><li v-for="(q, i) in openQuestions" :key="i">{{ q }}</li></ol>
    </div>

    <div class="card">
      <h2>来源站点与用法边界</h2>
      <table>
        <thead><tr><th>站点</th><th>能给什么</th><th>怎么用</th></tr></thead>
        <tbody>
          <tr v-for="(x, i) in REFS" :key="i"><td class="mono">{{ x[0] }}</td><td>{{ x[1] }}</td><td>{{ x[2] }}</td></tr>
        </tbody>
      </table>
      <!-- 副本等级区间定稿这条决定写在溯源页：内容页只摆定稿后的那一个数，
           但"以前有两个数、按哪个定的、另一个去哪了"必须有人交代，写在数据里由这一页读出来。 -->
      <p v-if="RS.levelRangeSettled" class="dim" style="margin-top:var(--s3)">{{ RS.levelRangeSettled.by }}：{{ RS.levelRangeSettled.note }}</p>
      <!-- 副本任务的取数顺序也是站主定的决定，和内容页那句"两个都留着"配套看。 -->
      <p v-if="QS.counts" class="dim">{{ QS.pageNote || '' }} 这一份共 {{ QS.counts.quests }} 条任务，其中经验值退到另一份资料的 {{ QS.counts.xpFromWowhead }} 条、两份数不一样留着两个的 {{ QS.counts.xpConflict }} 条、只有一份资料有的 {{ QS.counts.addedFromWowhead }} 条。</p>
      <!-- 副本坐标这一层的边界也在这页说：从哪家插件取的、只取了什么、没凑上的有多少 -->
      <p v-if="GEO.counts" class="dim">{{ GEO.sources[0].name }}：入口 {{ GEO.counts.entryDungeons }} 座、
        本内首领位置 {{ GEO.counts.bossDungeons }} 座 {{ GEO.counts.bossRows }} 条。
        只取坐标与地图编号，作者写的说明没拿；两边首领名字对不上的 {{ GEO.counts.droppedRows }} 条没有硬凑，
        留在没采用的名单里。这些数本站没进游戏核过。</p>
      <!-- 底图是这一轮新拿进来的一层素材，和坐标不是同一家插件，必须分开说一句（数字来自 manifest 现算） -->
      <p v-if="GEO.mapNote" class="dim">{{ GEO.mapNote }}</p>
      <!-- 素材的红线是"图标只从暴雪官方 CDN 取"，下面这些是站主逐张特批、从插件目录转存的例外，
           必须一张一张点名说清是谁给的、批到哪一步、怎么撤——文案直接读 manifest 里那条授权记录，
           不在页面里另抄一遍（抄了就和 manifest 漂移，将来加一张图还得改代码）。 -->
      <template v-if="addonArt.length">
        <h3 style="margin-top:var(--s4)">从插件目录转存的素材（特批，不走官方 CDN）</h3>
        <p class="dim">站点的图标一贯只从暴雪官方 CDN 取。下面这几张官方 CDN 没有，
          是站主逐张批准从本机插件目录转存的，<b>不算官方已核素材</b>，页面上也不当官方图用：</p>
        <ul class="list">
          <li v-for="(x, i) in addonArt" :key="i">
            {{ ART_KIND[x.kind] || x.kind }}「{{ x.name }}」：取自插件 {{ x.addon }}
            <span class="mono">v{{ x.addonVersion }}</span> 的 <span class="mono">{{ x.sourceDisplay }}</span>，
            {{ x.importedAt }} 转存为 <span class="mono">{{ x.file }}</span>，
            文件校验和 <span class="mono">{{ (x.sha256 || '').slice(0, 12) }}</span>。
            {{ x.authorizedBy }}
            <br>要撤回：{{ x.rollback }}
          </li>
        </ul>
      </template>
    </div>

    <!-- 2026-10-20 站主决定：玩家看的页面只给一个数，"两份说法还没对上"那类红字从内容页撤走。
         撤走不等于丢掉——分歧还得有人看得见，所以集中到这一页。
         条数全部从成品数据现算（ranksAlt / learnAlt / partySizeAlt / nameEnClient / xpAlt 都留在原处没删），
         这里一个数都不手抄，免得数据变了这一页还在说旧话。 -->
    <div class="card">
      <h2>两份说法怎么处置的</h2>
      <p class="dim">同一件事两份资料给两个值时，内容页只显示一个：数值类按最新插件的数（属性 GI 先行、其次 XR），
        任务经验值按参考站优先、缺则另一份客户端资料。另一说留在数据里没删，条数如下。</p>
      <ul class="list"><li v-for="x in altCounts" :key="x.k">{{ x.label }}：{{ x.n }} 条</li></ul>
      <template v-for="cf in raceConf" :key="cf.id">
        <h3 style="margin-top:var(--s4)">{{ cf.topic }}（{{ cf.level }}）</h3>
        <p class="dim">说法一：{{ cf.a.saying }}<br>说法二：{{ cf.b.saying }}</p>
        <p class="dim">{{ cf.handling }}</p>
      </template>
    </div>

    <div class="card">
      <h2>发布前的检查规则</h2>
      <ul><li v-for="(x, i) in rules" :key="i">{{ x }}</li></ul>
    </div>
  </template>
</template>

<script setup>
/* 溯源与覆盖率 · 与旧站 app.js provenance() 逐块对齐。
   scale.json 里的分级不带 total，这里像旧站一样显式补上（覆盖率条按 pubTotal 算四段宽度）；
   dungeons / dungeon-quests 两份数据缺了不挡页（catch 返回空对象，对应两段条件渲染自动消失）。
   来源站点表是写死在页面里的（旧站同样写死），不进数据文件。 */
import { computed, ref } from 'vue';
import { load } from '../lib/data.js';
import { PILL_NAME } from '../lib/fmt.js';

const NAMES = PILL_NAME;                       // L0-L3 的中文读数，与 lib/fmt.js 同一份
const COV_KEYS = ['L0', 'L1', 'L2', 'L3'];
// manifest 里 kind 的中文读法（只对可能来自插件目录的那几类，其余原样显示英文键）
const ART_KIND = {
  'race-icon': '种族小图标', 'race-portrait': '种族原画', 'zone-map': '区域底图',
  'boss-portrait': '首领头像', 'class-bg': '职业背景原画', 'spec-bg': '专精背景图',
  'dungeon-loading': '副本载入图'
};
const REFS = [
  ['wow.blizzard.cn/news/', '国服官方公告与职业深度解析', '可入自动化'],
  ['wow.blizzard.cn/24266320/', '国服在线修正', '可入自动化（需整页比对）'],
  ['news.blizzard.com', '官方英文回顾与上线时间', '可入自动化'],
  ['worldofwarcraft.blizzard.com/en-us/forever', '官方英文 forever 页', '可入自动化'],
  ['wowforever.wclbox.com', '客户端解包转述的中文名、副本卡片与等级区间、首领头像',
    '只取名称、编号、区间、图标文件名与原画转存；它的攻略正文与掉落概率一律不搬'],
  ['插件 GearInsight_Forever · XR_DungeonGuide · DungeonsForever',
   '客户端里读出的稀有精英与掉落、法术书、成就、配方来源、区域→地图号、副本入口与本内首领位置',
   '只取名称、编号、坐标与图标文件名。作者写的讲解与攻略句子、自绘的副本地图一律不搬；' +
   'DungeonsForever 的 LICENSE 是「保留所有权利」，所以只取坐标这一层'],
  ['wowhead.com/forever', '逐本指南、天赋计算器、天梯', '人工参照，禁止搬数据'],
  ['wago.tools/db2', '客户端数据表的 CSV 转储（非暴雪域名，只留最近几个版本）',
    '只取英文名、ID、等级与人数；文案一律不搬'],
  ['wowclassicforever.info', '最接近数据库的粉丝站', '人工参照，禁止搬数据'],
  ['foreverchanges.pro', '9 新本名单与区间', '线索，禁止整库复制'],
  ['news.17173.com', '中文蓝贴转载', '旁证，需回校官方'],
  ['github.com/cmangos/classic-db', '1.12 国服中文 locale（GPL-3.0）', '只取译名与结构'],
  ['search.bilibili.com', '测试服实测视频', 'ASR + 关键帧识别后人工确认']
];

const d = ref(null);
const err = ref('');

function boot() {
  err.value = '';
  Promise.all([load('data/meta.json'), load('data/method.json'), load('data/scale.json'),
    load('data/dungeons.json').catch(() => ({})),
    load('data/dungeon-quests.json').catch(() => ({})),
    load('data/dungeon-geo.json').catch(() => ({})),
    load('data/art.json').catch(() => ({})),
    load('data/races.json').catch(() => ({})),
    load('data/spells.json').catch(() => ({}))])
    .then((r) => {
      d.value = { meta: r[0] || {}, method: r[1] || {}, scale: (r[2] || {}).scale || {},
        RS: (r[3] || {}).meta || {}, QS: (r[4] || {}).meta || {}, GEO: (r[5] || {}).meta || {},
        ART: (r[6] || {}).meta || {}, DUN: r[3] || {}, RC: r[7] || {},
        SP: (r[8] || {}).spells || [] };
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();

const sc = computed(() => d.value.scale);
// 逐板块的数据版本：一律读规模快照里现算的那一份，页面不挑也不写死任何一个号
const dataVersions = computed(() => (sc.value || {}).dataVersions || []);
// 过期天数与阈值都由 build-data 现算下发，这一页只负责标出来（不抄第二份天数）
const stalePolicy = computed(() => (sc.value || {}).stalePolicy || null);
const newest = computed(() => tail((sc.value || {}).newestBuild || ''));
function tail(v) { return String(v || '').split('.').pop(); }
const ti = computed(() => d.value.meta.talentImport);
const m = computed(() => d.value.method || {});
const RS = computed(() => d.value.RS);
const QS = computed(() => d.value.QS);
const GEO = computed(() => d.value.GEO);
// 插件目录转存的素材名单（art.json.meta.addonFiles，由 fetch-art.py 从 manifest 现算）
const addonArt = computed(() => ((d.value || {}).ART || {}).addonFiles || []);
/* 分歧条数一律现算，不手抄：数据变了这一页跟着变，抄死的数字迟早说旧话。
   副本那三张表（新增 / 经典 / 团本）要合起来数，只数一张会漏。 */
const altCounts = computed(() => {
  const dd = d.value || {};
  const dun = [].concat(dd.DUN.newDungeons || [], dd.DUN.classicDungeons || [], dd.DUN.raids || []);
  const sp = dd.SP || [];
  const out = [
    { k: 'ranks', label: '技能等级数有两说', n: sp.filter((x) => x.ranksAlt).length },
    { k: 'learn', label: '起学等级有两说', n: sp.filter((x) => x.learnAlt).length },
    { k: 'party', label: '一次几人有两说', n: dun.filter((x) => x.partySizeAlt).length },
    { k: 'nameEn', label: '英文原名有两说', n: dun.filter((x) => x.nameEnClient).length },
    { k: 'xp', label: '任务经验值有两说', n: ((dd.QS || {}).counts || {}).xpConflict || 0 },
    // 物品"测试服上有没有"这两条腿：名录自报与 2026-10-19 的逐件探针，反向对不上的条数
    { k: 'srv', label: '物品在测试服有没有，两源说法不同（页面按探针那条显示）',
      n: ((dd.scale || {}).itemsSrvConflict) || 0 }
  ];
  return out.filter((x) => x.n > 0);
});
const raceConf = computed(() => ((d.value || {}).RC || {}).conflicts || []);
const openQuestions = computed(() => d.value.meta.openQuestions || []);
const rules = computed(() => d.value.meta.rules || []);

// 覆盖率四段：{ L0..L3, total }，total 取 pubTotal（旧站同款显式补法）
const cov = computed(() => {
  const p = sc.value.pubCoverage || {};
  return { L0: p.L0, L1: p.L1, L2: p.L2, L3: p.L3, total: sc.value.pubTotal };
});
const covSegs = computed(() => {
  const c = cov.value;
  const total = Math.max(c.total, 1);
  return COV_KEYS.filter((k) => c[k]).map((k) => ({
    k: k, w: (c[k] / total * 100) + '%', title: NAMES[k] + ' ' + c[k] + ' 条'
  }));
});
</script>
