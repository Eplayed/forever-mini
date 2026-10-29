<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="w">
    <!-- 卡片头：与旧站 decoratePageHead() 产出的结构逐字一致（改版第二批）。
         世界页的图就是首页图标轨「世界」那一格用的同一张本地原画，站内同一板块同一张脸。
         2026-10-12 站主决定：页首那句讲"世界线数据从哪来、刷新计时与攻略为什么不做"已删，
         出处集中在溯源页（provenance.html）；这一页只留区域、稀有、书与营地的数。 -->
    <div class="card">
      <div class="cdhead big">
        <span class="hicon"><img :src="HEAD_ART" alt="" loading="lazy"></span>
        <h1 class="pt">世界：区域、稀有与书</h1>
      </div>
      <!-- 2026-10-19 站主：这一排五个读数不要了（红框圈出来那句）。
           四个面板的标签上本来就各带自己的数，这排是把同一批数换个说法再列一遍。 -->
      <div class="picks">
        <button v-for="(t, i) in TABS" :key="t[0]" type="button" class="pick" :class="{ on: tab === t[0] }"
                :data-t="t[0]" :aria-pressed="tab === t[0] ? 'true' : 'false'" @click="pickTab(t[0])">
          <b>{{ t[1] }}</b><span class="dim mono">{{ tabCount[i] }}</span>
        </button>
      </div>
      <div class="field">
        <input id="wq" v-model="q" type="search" placeholder="搜区域、稀有或书名">
      </div>
    </div>

    <!-- 面板切换动效（2026-10-29）：四个面板整块换，所以给它们一个按 tab 取 key 的壳，
         切标签时旧面板淡掉、新面板淡入并抬 4px（motion.css 的 swap）。
         壳按 tab 重挂不会重挂数据——这一页的数在 setup 里算好，换的只是这一段 DOM。 -->
    <Transition name="swap" mode="out-in">
    <div class="wswap" :key="tab">
    <!-- 面板一：区域 -->
    <template v-if="tab === 'zones'">
      <template v-if="newZoneRows.length">
        <div class="band"><b>无限新增区域</b><span class="dim">飞行路线多未定</span>
          <span class="dim mono">{{ newZoneRows.length }} 个</span></div>
        <div class="zgrid"><ZoneCard v-for="z in newZoneRows" :key="z.id" :z="z" :items="zoneItems(z)" seal="新" @open="goZone" /></div>
      </template>
      <template v-for="c in continentRows" :key="c.id">
        <div class="band"><b>{{ c.nameCn }}</b>
          <span class="dim mono">{{ c.rows.length }} 个</span></div>
        <div class="zgrid"><ZoneCard v-for="z in c.rows" :key="z.id" :z="z" :items="zoneItems(z)" @open="goZone" /></div>
      </template>
      <div v-if="!zoneRows.length" class="card"><div class="empty">没有匹配的区域，换个名字试试。</div></div>

      <!-- 2026-10-12 站主决定：地图清单只列表身，"哪几张没切出图、为什么不搬别人的交互地图"
           那两段说明已删，素材与缺口集中在溯源页。 -->
      <div class="card">
        <h2>地图清单</h2>
        <div class="boardwrap">
          <table class="board">
            <colgroup><col style="width:34%"><col style="width:13%"><col style="width:13%"><col style="width:14%"><col></colgroup>
            <thead><tr><th>地图</th><th>类型</th><th>地图编号</th><th>兴趣点</th><th>已切图</th></tr></thead>
            <tbody>
              <tr v-for="m in listedMaps" :key="m.slug">
                <td>{{ m.nameCn }}<span v-if="m.isNew" class="tag">新</span></td>
                <td class="dim">{{ m.group || '—' }}</td>
                <td class="mono dim">{{ m.mapId }}</td>
                <td class="mono">{{ m.placeCount === null ? '—' : m.placeCount }}</td>
                <td class="mono">{{ m.painted || 0 }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- 面板二：稀有精英 -->
    <template v-else-if="tab === 'rares'">
      <div class="card">
        <!-- 2026-10-19 站主：「先挑区域」那行标题不要了，筛选胶囊自己说清楚就行 -->
        <div class="picks">
          <button type="button" class="pick" :class="{ on: !zone }" data-z="" @click="zone = ''">
            <b>全部</b><span class="dim mono">{{ rares.length }}</span></button>
          <button v-for="r in rareRegions" :key="r.zone" type="button" class="pick" :class="{ on: zone === r.zone }"
                  :data-z="r.zone" @click="zone = r.zone">
            <b>{{ r.zone }}</b><span class="dim mono">{{ r.count }}</span></button>
        </div>
      </div>
      <div v-if="!rareGroups.length" class="card"><div class="empty">这个筛选下没有稀有精英，换个区域或清空搜索。</div></div>
      <template v-for="g in rareGroups" :key="g.zone">
        <div class="band"><b>{{ g.zone }}</b><span class="dim">{{ lvTxt(g.meta) }} · {{ g.meta.faction || '阵营未定' }}</span>
          <span class="dim mono">{{ g.rows.length }} 个</span></div>
        <!-- 2026-10-18 站主：一个区域一张图，稀有直接标在图上，平时虚着、指上去实体并弹信息。
             2026-10-19 抽成 PinMap，四个面板共用（掉落清单在浮层与列表两处，小抽屉已撤）。 -->
        <PinMap :alt="g.zone + '的区域地图'" :items="rareItems(g.rows)" />
      </template>
      <div v-for="s in w.rareSets" :key="s.nameCn" class="card">
        <h2>套装 · {{ s.nameCn }}</h2>
        <p class="dim">{{ s.pieces.length }} 件套</p>
        <div class="loot">
          <span v-for="p in s.pieces" :key="p.itemId" class="loot-i" :class="'q' + (p.quality || 0)">
            <IconCell :icon-key="p.iconKey || ''" :seed="p.itemId" :cn="p.nameCn" small />
            {{ p.nameCn }}
            <span v-if="p.itemLevel" class="dim mono">iLvl {{ p.itemLevel }}</span>
            <span v-if="p.reqLevel" class="dim mono">需 {{ p.reqLevel }}</span>
            <span class="dim mono">#{{ p.itemId }}</span>
          </span>
        </div>
        <ul class="list">
          <li v-for="p in s.pieces" :key="'f' + p.itemId">{{ p.nameCn }} — <template v-if="p.fromRare">来自稀有「{{ p.fromRare }}」</template><template v-else>来源稀有待补</template></li>
        </ul>
      </div>
      <div v-if="unplaced.length" class="card">
        <h2>没有坐标的 {{ unplaced.length }} 个稀有</h2>
        <div class="chips"><span v-for="u in unplaced" :key="u.nameCn" class="chipc">{{ u.nameCn }}</span></div>
      </div>
    </template>

    <!-- 面板三：书籍 -->
    <template v-else-if="tab === 'books'">
      <div class="card">
        <h2>先找书，再找管理员</h2>
        <div class="stats">
          <div class="stat"><b>{{ books.length }}</b>本已定位</div>
          <div class="stat"><b>{{ bookGroups.length }}</b>个区域有书</div>
          <div class="stat"><b>{{ (w.booksMissing || []).length }}</b>本只有名字</div>
        </div>
        <template v-if="librarians.length">
          <h3>上交对象</h3>
          <div v-for="l in librarians" :key="l.nameCn" class="lrow">
            <b>{{ l.nameCn }}</b>
            <span class="dim">{{ l.faction }} · {{ l.city }}{{ l.quarter ? '，' + l.quarter : '' }}</span>
            <span class="mono dim">{{ coordTxt(l) }}</span>
          </div>
        </template>
      </div>
      <div v-if="!bookGroups.length" class="card"><div class="empty">这个筛选下没有书。</div></div>
      <template v-for="g in bookGroups" :key="g.zone">
        <div class="band"><b>{{ g.zone }}</b><span class="dim">{{ lvTxt(g.meta) }}{{ g.rows[0].zoneKind === 'city' ? ' · 主城' : '' }}</span>
          <span class="dim mono">{{ g.rows.length }} 本</span></div>
        <!-- 2026-10-19：书也换成同一套点位图。原来这里是一张只标了一个点的缩略图 + 一张五列表，
             那张图上一个点都对不上"这一区有几本书"；现在每本书一个点位，
             容器/位置/物品编号进浮层，列表行带上容器，一条信息都没少。 -->
        <PinMap :alt="g.zone + '的书籍地图'" :items="bookItems(g.rows)" />
      </template>
      <div v-if="rewards.length" class="card">
        <h2>上交多少本换什么</h2>
        <div class="boardwrap">
          <table class="board">
            <colgroup><col class="c-num"><col style="width:22%"><col class="c-id"><col></colgroup>
            <thead><tr><th class="c-num">门槛</th><th>称号</th><th>任务</th><th>奖励</th></tr></thead>
            <tbody>
              <tr v-for="rw in rewards" :key="rw.books">
                <td class="mono">{{ rw.books }} 本</td>
                <td>{{ rw.title }}</td>
                <td class="mono dim">{{ rw.questId ? '#' + rw.questId : '—' }}</td>
                <td>
                  <template v-if="rw.noReward"><span class="dim">奖励待补</span></template>
                  <template v-else>
                    <span v-for="d in rw.items" :key="d.itemId" class="loot-i" :class="'q' + (d.quality || 0)">
                      <IconCell :icon-key="d.iconKey || ''" :seed="d.itemId" :cn="d.nameCn" small />{{ d.nameCn }}
                      <span v-if="d.itemLevel" class="dim mono">iLvl {{ d.itemLevel }}</span>
                      <span v-if="d.reqLevel" class="dim mono">需 {{ d.reqLevel }}</span>
                      <span class="dim mono">#{{ d.itemId }}</span>
                    </span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="missingBooks.length" class="card">
        <h2>只有名字、没给坐标的 {{ missingBooks.length }} 本</h2>
        <div class="chips">
          <span v-for="b in missingBooks" :key="b.id" class="chipc">{{ b.nameCn }}<b class="mono dim">#{{ b.itemId }}</b></span>
        </div>
      </div>
    </template>

    <!-- 面板四：睡袋与营地 -->
    <template v-else>
      <div v-if="!bag.bag" class="card"><div class="empty">没有睡袋条目。</div></div>
      <template v-else>
        <!-- 2026-10-12 站主决定：睡袋面板只留物品与机制数值，讲数据来源、冲级路线为什么不搬那两段说明已删 -->
        <div class="card">
          <h2>睡袋本身</h2>
          <div class="itemrow">
            <IconCell :icon-key="bag.bag.iconKey || ''" :seed="bag.bag.itemId" :cn="bag.bag.nameCn" />
            <div><b>{{ bag.bag.nameCn }}</b><span class="dim mono">#{{ bag.bag.itemId }}</span>
              <span v-if="bag.bag.bind" class="dim">{{ bag.bag.bind }}</span>
              <span v-if="bag.usableLevel" class="dim mono">{{ bag.usableLevel }} 级可用</span></div>
          </div>
          <!-- 这张表原来是裸 <table class="mtx">，375 上撑到 680px 宽、整页横溢 338px
               （本轮新增的窄屏断言照出来的既有问题，不是这版改出来的）。
               收进 .board 骨架：table-layout:fixed + 列宽百分比，值再长也只在自己列里换行。 -->
          <div class="boardwrap">
            <table class="board bagtab">
              <colgroup><col style="width:40%"><col></colgroup>
              <thead><tr><th>机制项</th><th>记录值</th></tr></thead>
              <tbody>
                <tr v-for="p in bagRows" :key="p[0]">
                  <td>{{ p[0] }}</td><td class="mono">{{ p[1] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h2>营地点清单 · {{ camps.length }}<template v-if="q.trim()">（搜索 {{ q }} 命中）</template></h2>
          <div v-if="!camps.length" class="empty">这个关键词下没有营点。</div>
        </div>
        <!-- 2026-10-19：营地也走点位图。原来五条各带一张同样的区域缩略图，
             现在按区域归到一张图上标点，一条图对应一个去处 -->
        <template v-for="g in campGroups" :key="g.zone">
          <div class="band"><b>{{ g.zone }}</b><span class="dim">{{ lvTxt(g.meta) }} · {{ g.meta.faction || '阵营未定' }}</span>
            <span class="dim mono">{{ g.rows.length }} 处</span></div>
          <PinMap :alt="g.zone + '的营地点地图'" :items="campItems(g.rows)" />
        </template>
      </template>
    </template>
    </div>
    </Transition>
  </template>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import { levelRangeText as lvTxt, lvStart, coordText as coordTxt } from '../lib/fmt.js';
import ZoneCard from '../components/ZoneCard.vue';
import ZoneMap from '../components/ZoneMap.vue';
import PinMap from '../components/PinMap.vue';
import IconCell from '../components/IconCell.vue';

/* 主卡卡片头用的图：与首页图标轨「世界」那一格同一张本地原画（站内同一板块同一张脸）。
   必须走 JS 常量而不是模板里的字符串字面量——Vite 会去解析静态 src，public 下的路径不在
   构建图里，直接写会让 `npm run build` 报 Rollup failed to resolve。 */
const HEAD_ART = 'img/art/dungeons/city-of-dalaran.webp';
import HlText from '../components/HlText.vue';

const TABS = [['zones', '区域'], ['rares', '稀有精英'], ['books', '图书馆书籍'], ['bag', '睡袋与营地']];
const w = ref(null);
const err = ref('');
const tab = ref('zones');
const q = ref('');
const zone = ref('');

function boot() {
  err.value = '';
  load('data/world.json')
    .then((d) => { w.value = d; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
// 首页搜索带着板块与词跳进来（#/world?t=rares&q=…），落地就该是筛好的样子。
// 必须 watch：这一页自己也在 /world 上，从"区域"跳到"稀有"只换查询参数、
// 不换组件实例——只在建立时读一次的话，点了不会切面板（2026-10-19 实测到）。
const route = useRoute();
function applyQuery() {
  const t = String(route.query.t || '');
  if (TABS.some((x) => x[0] === t)) { tab.value = t; zone.value = ''; }
  if (route.query.q !== undefined) q.value = String(route.query.q || '');
}
applyQuery();
watch(() => [route.query.t, route.query.q], applyQuery);
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

const zones = computed(() => (w.value && w.value.zones) || []);
const newZones = computed(() => zones.value.filter((z) => z.isNew));
const rares = computed(() => (w.value && w.value.rares) || []);
const books = computed(() => (w.value && w.value.books) || []);
const maps = computed(() => (w.value && w.value.maps) || []);
const librarians = computed(() => (w.value && w.value.librarians) || []);
const rewards = computed(() => (w.value && w.value.bookRewards) || []);
const missingBooks = computed(() => (w.value && w.value.booksMissing) || []);
const unplaced = computed(() => (w.value && w.value.raresUnplaced) || []);
const bag = computed(() => (w.value && w.value.bagTool) || {});
const allCamps = computed(() => (bag.value.camps || []).reduce((a, c) => a.concat(c.places || []), []));
// 营点按区域/地标名筛，和旧站一致：搜索框里有词就只看命中的那几个
const camps = computed(() => {
  const k = kw.value;
  if (!k) return allCamps.value;
  return allCamps.value.filter((c) => ((c.zone || '') + ' ' + (c.whereCn || '') + ' ' +
    (c.landmark || '')).toLowerCase().indexOf(k) >= 0);
});
const stopCount = computed(() => ((bag.value.camps) || []).length);
const tabCount = computed(() => [zones.value.length, rares.value.length, books.value.length, stopCount.value]);
const zByName = computed(() => {
  const m = {};
  zones.value.forEach((z) => { m[z.nameCn] = z; });
  return m;
});
const kw = computed(() => q.value.trim().toLowerCase());
function hit(x) {
  const k = kw.value;
  if (!k) return true;
  return ((x.nameCn || '') + ' ' + (x.nameEn || '') + ' ' + (x.zone || '') + ' ' +
    (x.container || '')).toLowerCase().indexOf(k) >= 0;
}

const zoneRows = computed(() => zones.value.filter(hit));
const newZoneRows = computed(() => newZones.value.filter(hit));
// 与旧站同一份分组：大陆之外还有一桶「单独成图的新区域」，那张图不属于任何大陆
const continentRows = computed(() => (((w.value && w.value.continents) || [])
  .concat([{ id: 'new', nameCn: '单独成图的新区域' }]))
  .map((c) => ({ id: c.id, nameCn: c.nameCn, rows: zoneRows.value.filter((z) => z.continent === c.id && !z.isNew) }))
  .filter((c) => c.rows.length));
const listedMaps = computed(() => maps.value.filter((m) => m.isNew || m.group === '大陆'));

const rareGroups = computed(() => {
  const by = {};
  rares.value.filter(hit).forEach((r) => {
    const k = r.zone || '未归区域';
    (by[k] = by[k] || []).push(r);
  });
  let keys = Object.keys(by).sort((a, b) => lvStart(zByName.value[a]) - lvStart(zByName.value[b]) || (a < b ? -1 : 1));
  if (zone.value) keys = keys.filter((k) => k === zone.value);
  return keys.map((k) => ({ zone: k, rows: by[k], meta: zByName.value[k] || {} }));
});
const rareRegions = computed(() => ((w.value || {}).rareRegions || []).filter((r) => r.count));

const bookGroups = computed(() => {
  const by = {};
  books.value.filter(hit).forEach((b) => {
    const k = b.zone || '未归区域';
    (by[k] = by[k] || []).push(b);
  });
  return Object.keys(by)
    .sort((a, b) => lvStart(zByName.value[a]) - lvStart(zByName.value[b]) || (a < b ? -1 : 1))
    .map((k) => ({ zone: k, rows: by[k], meta: zByName.value[k] || {} }));
});

const bagRows = computed(() => {
  const p = bag.value.params || {};
  return [['铺开耗时', p.castSec + ' 秒'], ['休息收益名', p.buffName || '—'], ['收益持续', p.buffHours + ' 小时'],
    ['可叠层', p.stacks + ' 层'], ['铺设冷却', p.cdMin + ' 分钟']];
});

function pickTab(t) { tab.value = t; zone.value = ''; }
function goZone(name) { zone.value = name; tab.value = 'rares'; }

/* ---- 四个面板共用的点位数据（2026-10-19）----
   把各自的记录归一成 PinMap 认的形状：kind 决定点位颜色与浮层长相，
   pin 表示"这条到底能不能标在图上"——没有 mapFile 就不标，不猜位置。 */
function base(r) {
  return {
    key: r.id, pin: !!(r.mapFile && r.mark),
    x: r.mark ? r.mark.x : null, y: r.mark ? r.mark.y : null,
    mapFile: r.mapFile || '', mapId: r.mapId || '',
    name: r.nameCn || '', en: r.nameEn || ''
  };
}
function rareItems(rows) {
  return rows.map((r) => Object.assign(base(r), {
    kind: 'rare', tag: r.kind === 'rare-elite' ? '稀有精英' : '稀有',
    isNew: !!r.isNew, level: lvTxt(r), coord: coordTxt(r),
    drops: r.drops || [],
    hint: (r.drops || []).length ? '掉落 ' + r.drops.length + ' 件' : ''
  }));
}
function bookItems(rows) {
  return rows.map((b) => Object.assign(base(b), {
    kind: 'book', tag: '书', isNew: !!b.forever,
    level: b.afterLevel ? b.afterLevel + ' 级后' : '',
    coord: coordTxt(b),
    rows: [['容器', b.container || '—'], ['位置', b.place || '—'],
      ['物品编号', b.itemId ? '#' + b.itemId : '—']],
    hint: b.place || b.container || ''
  }));
}
function campItems(rows) {
  return rows.map((c, i) => Object.assign(base(c), {
    // 营地记录没有 id，用「区域 + 序号」当键；名字用区域名，地标进浮层那两行
    key: (c.zone || 'x') + '-' + i, name: c.zone || '区域未标', kind: 'camp',
    tag: '营地', isNew: false, level: '', coord: coordTxt(c),
    rows: [['地标', c.landmark || '—'], ['方位', c.whereCn || '—']],
    hint: c.landmark || ''
  }));
}

function groupBy(list) {
  const m = {};
  list.forEach((x) => { const k = x.zone || '未归区域'; (m[k] = m[k] || []).push(x); });
  return m;
}
const campGroups = computed(() => {
  const by = groupBy(camps.value);
  return Object.keys(by)
    .sort((a, b) => lvStart(zByName.value[a]) - lvStart(zByName.value[b]) || (a < b ? -1 : 1))
    .map((k) => ({ zone: k, rows: by[k], meta: zByName.value[k] || {} }));
});
/* 区域卡上那张图要一次标三类东西：本区域的稀有 + 书 + 营地。
   顺序固定按 稀有→书→营地，编号才稳定（断言与列表都靠编号对位） */
function zoneItems(z) {
  const n = z.nameCn;
  return rareItems(rares.value.filter((r) => r.zone === n))
    .concat(bookItems(books.value.filter((x) => x.zone === n)))
    .concat(campItems(allCamps.value.filter((c) => c.zone === n)));
}
</script>
