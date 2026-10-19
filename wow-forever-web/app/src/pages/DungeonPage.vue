<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <!-- 没带本号：给一张目录，别让人对着空页发愣（旧站 dungeonPage() 的 !id 分支） -->
  <template v-else-if="D && !did">
    <div class="card">
      <h1 class="pt">先挑一座本</h1>
      <p class="dim">这一页是一座本一页：等级区间、一次几人、首领名单与按首领分组的掉落都在里面。下面按十级一档列出本站收录的 {{ duns.length }} 座，点一个就过去。</p>
      <template v-for="b in dirBands" :key="b.title">
        <h3>{{ b.title }}</h3>
        <p class="dirl"><router-link v-for="y in b.rows" :key="y.id" :to="{ path: '/dungeon', query: { d: y.id } }">{{ y.nameCn || y.nameEn || y.id }}<span class="dim mono">{{ y.levelRange || '未定' }}</span></router-link></p>
      </template>
      <router-link class="cta" to="/dungeons">回列表页，填等级一次看一档 →</router-link>
    </div>
  </template>

  <!-- 带了本号但查无此本 -->
  <template v-else-if="D && !x">
    <div class="card">
      <h1 class="pt">这座本还没收录</h1>
      <p class="dim">地址里那座本（{{ did }}）不在本站的副本名单里。名单以正式开放的为准，能查到的都已经在列表页里了。</p>
      <router-link class="cta" to="/dungeons">回到副本手册，按等级挑一座 →</router-link>
    </div>
  </template>

  <template v-else-if="x">
    <!-- 页首 hero：与旧站 dungeonPage() 的 .dhero.dunh 一节逐字对齐 -->
    <section class="dhero dunh" :class="{ noart: !art }">
      <img v-if="art" :src="assetUrl(art)" alt="">
      <span class="dx"></span>
      <div class="db">
        <div class="crumb"><router-link to="/dungeons">副本手册</router-link><i>›</i><b>{{ nm }}</b></div>
        <div class="kicker">{{ kindCn }}<template v-if="x.levelRange"> · {{ x.levelRange }} 级</template></div>
        <h1 class="pt">{{ nm }}</h1>
        <div class="dhen">{{ x.nameEn || '中文与英文定名都还没公布' }}</div>
        <div class="dhline">{{ bosses.length ? bosses.length + ' 个首领 · ' : '首领待补 · ' }}{{ drops.length ? drops.length + ' 件掉落归属' : '掉落待补' }} · {{ x.faction || '阵营未标' }}<template v-if="x.partySize"> · 一次 {{ x.partySize }} 人</template><template v-if="quests.length"> · {{ quests.length }} 条任务</template></div>
        <router-link v-if="zone" class="cta" :to="{ path: '/world', query: { q: zone } }">在世界那一页找「{{ zone }}」</router-link>
      </div>
    </section>

    <!-- 上一座 / 下一座：同一档（团本只与团本相邻） -->
    <div class="card dnear">
      <router-link v-if="prevD" class="dnear-l" :to="{ path: '/dungeon', query: { d: prevD.id } }">上一座 <b>{{ prevD.nameCn || prevD.nameEn || prevD.id }}</b><span class="dim mono">{{ prevD.levelRange || '区间未定' }}</span></router-link>
      <span v-else class="dim">这一档的第一座</span>
      <span class="dim mono">{{ at + 1 }} / {{ sibs.length }}</span>
      <router-link v-if="nextD" class="dnear-l" :to="{ path: '/dungeon', query: { d: nextD.id } }">下一座 <b>{{ nextD.nameCn || nextD.nameEn || nextD.id }}</b><span class="dim mono">{{ nextD.levelRange || '区间未定' }}</span></router-link>
      <span v-else class="dim">这一档的最后一座</span>
    </div>

    <div class="card">
      <h2>进本之前</h2>
      <div class="four dhfact">
        <div><s>位置</s><b class="t">{{ x.zoneCn || '待补' }}</b></div>
        <div><s>等级区间</s><b>{{ x.levelRange || '待实测' }}</b><s>{{ x.levelRange ? '推荐等级范围' : '还没有核到的数' }}</s></div>
        <div><s>一次几人</s><b>{{ x.partySize ? x.partySize : '未标' }}</b><s>{{ x.partySize ? '取自客户端的队伍查找器' : '客户端里还没有它' }}</s></div>
        <div><s>掉落</s><b>{{ drops.length || '待补' }}</b><s>{{ drops.length ? '件，按首领分组' : '还没有名单' }}</s></div>
      </div>
      <div v-for="(t, i) in conf" :key="i" class="conf">{{ t }}</div>
      <div v-if="noQueue" class="note">客户端的队伍查找器里还没有这座本，所以现在还不能排队进去，名单与掉落以正式开放后为准。</div>
      <p v-if="!x.nameCn" class="note">中文定名未公布，这一页的标题用的是客户端里的原名。</p>
      <h3>首领顺序</h3>
      <ol v-if="bosses.length" class="dunord">
        <li v-for="b in bosses" :key="b.id"><a :href="'#b-' + b.id" @click.prevent="jump('b-' + b.id)">{{ b.nameCn }}</a></li>
      </ol>
      <p v-else class="dim">这座本还没有首领名单。</p>
    </div>

    <div class="card">
      <h2>首领与掉落</h2>
      <template v-if="bosses.length">
        <!-- 首领块：Glyph.bossFace('lg') 的等价内联复刻（同算法同类名），id="b-首领id" 供锚点跳转 -->
        <div v-for="b in bossRows" :key="b.id" class="brow" :id="'b-' + b.id">
          <div class="bh">
            <span class="liw t lg">
              <svg viewBox="0 0 40 40" aria-hidden="true">
                <rect width="40" height="40" rx="6" :fill="'hsl(' + b.f.hue + ',22%,16%)'" :stroke="'hsl(' + b.f.hue + ',30%,42%)'" stroke-opacity=".65" />
                <text x="20" y="26" text-anchor="middle" font-size="16" font-weight="600" :fill="'hsl(' + b.f.hue + ',46%,78%)'" font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ b.f.letter }}</text>
              </svg>
              <img v-if="b.portrait" :class="{ bad: badFace[b.id] }" :src="assetUrl(b.portrait)" alt="" loading="lazy" @error="badFace[b.id] = true">
            </span>
            <div class="bt"><b>{{ b.nameCn }}</b>
              <span class="dim">{{ b.mine.length ? '这座本里它掉 ' + b.mine.length + ' 件' : '掉落待补' }}</span>
              <span v-if="!b.portrait" class="dim">没有这张头像</span>
              <!-- 本内位置：坐标的参照物是这座本自己的内部图，本站目前没有那批图，
                   所以先给数字（游戏里地图上的百分比就是这套数），等有图了再画点 -->
              <span v-if="b.pos" class="dim mono">本内 {{ b.posText }}</span>
            </div>
          </div>
          <div v-if="b.mine.length" class="items">
            <div v-for="y in b.mine" :key="y.itemId" class="itemc">
              <b :class="'q' + (y.quality || 0)"><IconCell :icon-key="y.iconKey || ''" :seed="y.itemId" :cn="y.nameCn" small />{{ y.nameCn }}</b>
              <span class="dim mono">#{{ y.itemId }}</span>
            </div>
          </div>
        </div>
      </template>
      <p v-else class="dim">这座本还没有首领名单，掉落也就没有归属可写。</p>
    </div>

    <!-- 入口在哪（2026-10-19 接上副本坐标这一层）：一颗点画在所在区域那张图上，
         与世界页同一套点位组件。本地没有那张区域图时不假画，退成"地图编号 + 坐标"一行。 -->
    <div v-if="entry" class="card dgeo">
      <h2>入口在哪</h2>
      <PinMap v-if="entryItems.length" :alt="nm + '的入口位置'" :items="entryItems"
              :fallback-map-file="entry.mapFile || ''" :fallback-map-id="entry.mapId || ''" />
      <p class="dgeo-line">
        <b>{{ entry.zone }}</b>
        <span class="dim mono">{{ entry.x }}，{{ entry.y }}</span>
        <span v-if="!entry.mapFile" class="dim">这一片的区域图本站还没有，只给坐标：地图编号 {{ entry.mapId }}</span>
        <span v-else class="dim">指上去或点住那个点能看到细节</span>
      </p>
      <router-link class="cta" :to="{ path: '/world', query: { t: 'zones', q: entry.zone } }">
        看「{{ entry.zone }}」这一片还有什么 →
      </router-link>
    </div>

    <!-- 首领在哪个位置（2026-10-19：副本内部底图接进来之后，坐标从数字变成点）。
         一个刷新点一颗点，同一只首领有多个点就出多颗；层号写在浮层与列表行里。 -->
    <div v-if="bossMapItems.length" class="card dboss">
      <h2>首领在哪个位置</h2>
      <PinMap :alt="nm + '的首领位置图'" :items="bossMapItems" :ratio="geo.bossMapRatio || '512/512'" />
      <p class="dim">点一下钉住、再点收掉；手机上直接点右边那一行。同一只首领有多个刷新点就出多颗。</p>
    </div>

    <!-- 本里的任务（2026-10-13 口径：讲资料出处的句子一律不上页面；唯一保留的是
         「用物品开启」与经验两说那句，缺的格子留空不写"待补"） -->
    <div class="card" id="dquests">
      <h2>本里的任务</h2>
      <template v-if="quests.length">
        <p class="dim">共 {{ quests.length }} 条<template v-if="qSum.xpTotal">，合计 {{ qSum.xpTotal }} 点经验</template><template v-if="qSum.faction">，{{ qSum.faction }}一侧</template>。经验与可接等级是经典旧世的数字，无限服可能调整，本站没实测过。</p>
        <div class="boardwrap">
          <table class="board">
            <thead><tr>
              <th class="w-name">任务</th><th class="c-num2">几级能接</th><th class="c-num2">任务等级</th>
              <th class="c-num">经验</th><th class="w-tail">在哪接</th>
            </tr></thead>
            <tbody>
              <tr v-for="(y, i) in quests" :key="y.nameCn + '-' + i">
                <td><span class="nm">{{ y.nameCn }}</span><span v-if="y.preQuest" class="sub">前置：{{ y.preQuest }}</span><span v-if="y.xpAlt" class="conf">经验值有两个说法：{{ y.xp }} / {{ y.xpAlt }}，还没实测</span></td>
                <td class="c-num2 num">{{ num(y.reqLevel) }}</td>
                <td class="c-num2 num">{{ num(y.questLevel) }}</td>
                <td class="c-num num"><b v-if="y.xp !== null && y.xp !== undefined">{{ y.xp }}</b></td>
                <td class="w-tail"><template v-if="y.pickupNpc">{{ y.pickupNpc }}<span v-if="y.pickupZone" class="dim">，{{ y.pickupZone }}</span></template><span v-else-if="y.startItem" class="dim">用物品开启：{{ y.startItem }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <p v-else class="dim">这座本还没有任务记录。</p>
      <template v-if="qItems.length">
        <h3>进本之前要带的东西</h3>
        <div class="boardwrap">
          <table class="board">
            <thead><tr><th class="w-name">任务物品</th><th class="c-num2">谁掉</th><th class="w-tail">对应任务</th></tr></thead>
            <tbody>
              <tr v-for="(y, i) in qItems" :key="i">
                <td><span class="nm">{{ y.itemCn || '—' }}</span></td>
                <td class="c-num2">{{ y.from && y.from !== '—' ? y.from : '' }}</td>
                <td class="w-tail">{{ y.quest || '—' }}<span v-if="y.faction" class="dim">　{{ y.faction }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <template v-if="qStarts.length">
        <h3>在哪儿接</h3>
        <div class="boardwrap">
          <table class="board">
            <thead><tr><th class="w-name">谁给任务</th><th class="c-num2">在哪儿</th><th class="w-tail">能接到什么</th></tr></thead>
            <tbody>
              <tr v-for="(y, i) in qStarts" :key="i">
                <td><span class="nm">{{ y.npc || '—' }}</span></td>
                <td class="c-num2">{{ y.zone || '—' }}</td>
                <td class="w-tail">{{ y.quest || '—' }}<span v-if="y.faction" class="dim">　{{ y.faction }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>

    <div class="card">
      <h2>换一座</h2>
      <!-- 2026-10-13 站主要求：全部副本平铺展开好找，不再藏进下拉。分组与目录页同一份
           DUN_BANDS，团本单列一组；当前这一座不挂链接，方便定位。 -->
      <template v-for="g in swapGroups" :key="g.title">
        <h3>{{ g.title }}</h3>
        <p class="dirl">
          <template v-for="y in g.rows" :key="y.id">
            <router-link v-if="y.id !== x.id" :to="{ path: '/dungeon', query: { d: y.id } }">{{ y.nameCn || y.nameEn || y.id }}<span class="dim mono">{{ y.levelRange || '未定' }}</span></router-link>
            <b v-else>{{ y.nameCn || y.nameEn || y.id }}<span class="dim mono">{{ y.levelRange || '未定' }}</span></b>
          </template>
        </p>
      </template>
      <router-link class="cta" to="/dungeons">回列表，按等级段挑 →</router-link>
    </div>
  </template>
</template>

<script setup>
/* 每座本一页 · 与旧站 src/js/app.js 的 dungeonPage() 逐块对齐（目录 / 未收录 / 详情三分支）。
   App.vue 以 route.path 作 :key，query.d 变化不会重建组件——标题与锚点一律 watch query.d。
   art.json / dungeon-quests.json 加载失败按旧站 catch 空对象兜底。 */
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { assetUrl, load } from '../lib/data.js';
import { fnv } from '../lib/glyph.js';
import IconCell from '../components/IconCell.vue';
import PinMap from '../components/PinMap.vue';

// 按十级一档分：与旧站同一份表（目录页与上一座/下一座的分档都靠它）
const DUN_BANDS = [[10, 19, '起步'], [20, 29, '前期'], [30, 39, '中期'], [40, 49, '中后期'], [50, 99, '满级前后']];

const D = ref(null);
const ART = ref({});
const QD = ref({});
const GEO = ref({});
const err = ref('');
const badFace = ref({});
const route = useRoute();

/* 与旧站 dunRange/dunBand/dunSort 同一套算法 */
function dunRange(x) {
  const m = String(x.levelRange || '').match(/(\d+)\D+(\d+)/);
  return m ? [parseInt(m[1], 10), parseInt(m[2], 10)] : null;
}
function dunBand(x) {
  const s = parseInt(String(x.levelRange || '').split('-')[0], 10);
  if (!s) return null;
  for (let i = 0; i < DUN_BANDS.length; i++) if (s >= DUN_BANDS[i][0] && s <= DUN_BANDS[i][1]) return i;
  return null;
}
function dunSort(a, b) {
  const ra = dunRange(a) || [99, 99], rb = dunRange(b) || [99, 99];
  if (ra[0] !== rb[0]) return ra[0] - rb[0];
  if (ra[1] !== rb[1]) return ra[1] - rb[1];
  return String(a.nameCn || a.nameEn || '').localeCompare(String(b.nameCn || b.nameEn || ''));
}
/* 两源分歧（与列表页 dunConf 共用同一份措辞） */
function confRows(x) {
  const out = [];
  if (x.partySizeAlt) {
    out.push('客户端的队伍查找器里它另有一条 ' + x.partySizeAlt +
      ' 人的排队条目，与本站的 ' + x.partySize + ' 人并列，是不是同一个本两种规模要实测');
  }
  if (x.nameEnClient) {
    out.push('英文原名两说：本站写「' + x.nameEn + '」，客户端写「' + x.nameEnClient + '」');
  }
  return out;
}
/* Glyph.bossFace 等价复刻（只算参数，SVG 交给模板） */
function faceOf(b) {
  const h = fnv(b.id || b.nameCn || '');
  return { hue: (32 + h % 300) % 360, letter: (b.nameCn || '?').charAt(0) };
}
function num(v) { return v === null || v === undefined ? '—' : v; }

function boot() {
  err.value = '';
  Promise.all([load('data/dungeons.json'),
    load('data/art.json').catch(() => ({})),
    load('data/dungeon-quests.json').catch(() => ({})),
    // 坐标这一层缺了不挡页：没有入口的本就不显示那一节
    load('data/dungeon-geo.json').catch(() => ({}))])
    .then((rs) => { D.value = rs[0]; ART.value = rs[1] || {}; QD.value = rs[2] || {}; GEO.value = rs[3] || {}; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时，重新拉一次

const did = computed(() => String(route.query.d || route.query.id || ''));
const duns = computed(() => [].concat((D.value || {}).newDungeons || [], (D.value || {}).classicDungeons || []));
const all = computed(() => duns.value.concat((D.value || {}).raids || []));
const x = computed(() => (did.value ? all.value.filter((y) => y.id === did.value)[0] || null : null));

/* query.d 变化（App.vue 不重建组件）→ 换标题；query.b → 滚到那名首领 */
watch([did, D], () => {
  nextTick(() => {
    if (x.value) document.title = (x.value.nameCn || x.value.nameEn || '未定名') + ' · 副本手册';
    else document.title = '副本详情 · 无限资料站';
    const bb = String(route.query.b || '');
    if (bb) {
      const node = document.getElementById('b-' + bb);
      if (node && node.scrollIntoView) node.scrollIntoView({ block: 'center' });
    }
  });
}, { immediate: true });

/* 目录页（没带本号）：只列 DUN_BANDS 五档（与旧站 byBand 一致，区间未定不上目录） */
const dirBands = computed(() => {
  const out = [];
  DUN_BANDS.forEach((b, i) => {
    const rows = duns.value.filter((y) => dunBand(y) === i).sort(dunSort);
    if (rows.length) out.push({ title: b[0] + (b[1] > 60 ? '–60' : '–' + b[1]) + ' 级 · ' + b[2], rows: rows });
  });
  return out;
});

/* 「换一座」平铺：五档 + 团本全列出（当前这座在模板里不加链接）。分组串与目录页 dirBands 同款。 */
const swapGroups = computed(() => {
  const out = [];
  DUN_BANDS.forEach((b, i) => {
    const rows = duns.value.filter((y) => dunBand(y) === i).sort(dunSort);
    if (rows.length) out.push({ title: b[0] + (b[1] > 60 ? '–60' : '–' + b[1]) + ' 级 · ' + b[2], rows: rows });
  });
  const raids = ((D.value || {}).raids || []).slice().sort(dunSort);
  if (raids.length) out.push({ title: '团队副本', rows: raids });
  return out;
});

/* 详情读数 */
const nm = computed(() => (x.value ? x.value.nameCn || x.value.nameEn || '未定名' : ''));
const bosses = computed(() => (x.value && x.value.bosses) || []);
const drops = computed(() => (x.value && x.value.drops) || []);
const art = computed(() => (x.value ? x.value.art || ((ART.value.dungeons || {})[x.value.id]) || '' : ''));
const kindCn = computed(() => (x.value ? (x.value.kind === 'new' ? '无限新增' : (x.value.kind === 'raid' ? '团队副本' : '经典旧世')) : ''));
const zone = computed(() => String((x.value && x.value.zoneCn) || '').split(/[，·]/)[0].trim());
const conf = computed(() => confRows(x.value || {}));
const noQueue = computed(() => !!(x.value && !x.value.clientActivityId));

/* 任务区（wclbox 为准，wowhead 补；页面只摆数字，出处不上页面） */
const q = computed(() => ((QD.value.dungeons || {})[(x.value || {}).id]) || {});
const quests = computed(() => q.value.quests || []);
const qItems = computed(() => q.value.questItems || []);
const qStarts = computed(() => q.value.questStarts || []);
const qSum = computed(() => q.value.summary || {});

/* 同档相邻本：团本只与团本排（旧站 sibs） */
const sibs = computed(() => {
  if (!x.value || !D.value) return [];
  return (x.value.kind === 'raid' ? (D.value.raids || []).slice() : duns.value.slice()).sort(dunSort);
});
const at = computed(() => {
  let a = 0;
  sibs.value.forEach((y, i) => { if (y.id === (x.value || {}).id) a = i; });
  return a;
});
const prevD = computed(() => sibs.value[at.value - 1] || null);
const nextD = computed(() => sibs.value[at.value + 1] || null);

/* 坐标这一层（2026-10-19 接上）：入口画在所在区域那张图上，首领位置先只给数字 */
const geo = computed(() => ((GEO.value.dungeons || {})[(x.value || {}).id]) || {});
const entry = computed(() => geo.value.entry || null);
const entryItems = computed(() => {
  const e = entry.value;
  if (!e) return [];
  return [{
    key: (x.value || {}).id + '-entry', kind: 'entry',
    pin: !!e.mapFile,                       // 没那张区域图就不画点，不猜位置
    x: e.x, y: e.y, mapFile: e.mapFile || '', mapId: e.mapId || '',
    name: nm.value + ' · 入口', en: '', tag: '入口', isNew: false, level: '',
    coord: e.x + '，' + e.y,
    rows: [['所在区域', e.zone || '—'], ['区域地图编号', e.mapId || '—']],
    drops: [], hint: ''
  }];
});

/* 首领位置画成点：一个刷新点一颗。没有 bossMap（那张内部底图）的本，
   一颗都不画，只在首领行给数字——不拿别的图猜位置。 */
const bossMapItems = computed(() => {
  const file = geo.value.bossMap || '';
  const bs = geo.value.bossPos || {};
  const out = [];
  Object.keys(bs).forEach((name) => {
    (bs[name] || []).forEach((p, i) => {
      out.push({
        key: 'b-' + name + '-' + i, kind: 'boss', pin: !!file,
        x: p.x, y: p.y, mapFile: file, mapId: '',
        name: name, en: '', tag: '首领', isNew: false, level: '',
        coord: p.x + '，' + p.y,
        rows: p.floor ? [['在第几层', String(p.floor)]] : [],
        drops: [], hint: p.floor ? '第 ' + p.floor + ' 层' : ''
      });
    });
  });
  return out;
});
/* 首领块：带掉落归属与头像参数 */
const bossRows = computed(() => bosses.value.map((b) => {
  const pts = (geo.value.bossPos || {})[b.nameCn] || [];
  return {
    id: b.id, nameCn: b.nameCn, portrait: b.portrait, f: faceOf(b),
    mine: drops.value.filter((y) => y.bossId === b.id),
    // 一只首领可能给好几个刷新点，全列出来；层号（多层的本才有）跟着各自那个点
    pos: pts.length,
    posText: pts.map((p) => p.x + '，' + p.y + (p.floor ? ' · 第 ' + p.floor + ' 层' : '')).join('　')
  };
}));

function jump(id) {
  const node = document.getElementById(id);
  if (node && node.scrollIntoView) node.scrollIntoView();
}
</script>
