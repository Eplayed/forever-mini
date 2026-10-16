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
      <div class="stats">
        <div class="stat"><b>{{ zones.length }}</b>个区域</div>
        <div class="stat"><b>{{ newZones.length }}</b>个无限新增</div>
        <div class="stat"><b>{{ rares.length }}</b>个已定位稀有</div>
        <div class="stat"><b>{{ books.length }}</b>本书有坐标</div>
        <div class="stat"><b>{{ maps.length }}</b>张客户端地图</div>
      </div>
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

    <!-- 面板一：区域 -->
    <template v-if="tab === 'zones'">
      <template v-if="newZoneRows.length">
        <div class="band"><b>无限新增区域</b><span class="dim">飞行路线多未定</span>
          <span class="dim mono">{{ newZoneRows.length }} 个</span></div>
        <div class="zgrid"><ZoneCard v-for="z in newZoneRows" :key="z.id" :z="z" seal="新" @open="goZone" /></div>
      </template>
      <template v-for="c in continentRows" :key="c.id">
        <div class="band"><b>{{ c.nameCn }}</b>
          <span class="dim mono">{{ c.rows.length }} 个</span></div>
        <div class="zgrid"><ZoneCard v-for="z in c.rows" :key="z.id" :z="z" @open="goZone" /></div>
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
        <h2>先挑区域</h2>
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
        <div class="rgrid">
          <div v-for="r in g.rows" :key="r.id" class="rarecard">
            <ZoneMap :map-file="r.mapFile" :map-id="r.mapId" :mark="r.mark" :alt="g.zone" />
            <div class="rbody">
              <b>{{ r.nameCn }}</b>
              <span v-if="r.nameEn" class="dim mono">{{ r.nameEn }}</span>
              <span class="rtags">
                <span class="tag">{{ r.kind === 'rare-elite' ? '稀有精英' : '稀有' }}</span>
                <span v-if="r.isNew" class="tag new">无限新增</span>
                <span class="dim mono">{{ lvTxt(r) }}</span>
              </span>
              <span class="mono dim">{{ coordTxt(r) }}</span>
              <div v-if="r.drops.length" class="loot">
                <span v-for="d in r.drops" :key="d.itemId" class="loot-i" :class="'q' + (d.quality || 0)">
                  <IconCell :icon-key="d.iconKey || ''" :seed="d.itemId" :cn="d.nameCn" small />
                  {{ d.nameCn }}
                  <span v-if="d.itemLevel" class="dim mono">iLvl {{ d.itemLevel }}</span>
                  <span v-if="d.reqLevel" class="dim mono">需 {{ d.reqLevel }}</span>
                  <span class="dim mono">#{{ d.itemId }}</span>
                </span>
              </div>
              <div v-else class="note">这一条没有掉落记录。</div>
              <button type="button" class="ghost wide" :data-r="r.id" @click="toggleDrawer(r.id)">{{ drawerOf(r.id) ? '收起' : '掉落与坐标' }}</button>
              <div v-show="drawerOf(r.id)" class="wdr" :class="{ open: drawerOf(r.id) }">
                <h3>掉落清单</h3>
                <ul v-if="r.drops.length" class="list">
                  <li v-for="d in r.drops" :key="d.itemId">{{ d.nameCn }}（#{{ d.itemId }}，{{ d.bind || '绑定方式待补' }}）</li>
                </ul>
                <p v-else class="dim">待补。</p>
              </div>
            </div>
          </div>
        </div>
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
        <div v-if="g.rows[0].mapFile" class="zthumb">
          <ZoneMap :map-file="g.rows[0].mapFile" :map-id="g.rows[0].mapId" :mark="g.rows[0].mark" :alt="g.zone" />
        </div>
        <div class="boardwrap">
          <table class="board bktab">
            <colgroup><col class="c-ico"><col style="width:26%"><col style="width:16%"><col><col class="c-id"></colgroup>
            <thead><tr><th class="c-ico">书</th><th>名称</th><th>容器</th><th>位置</th><th class="c-id">物品 ID</th></tr></thead>
            <tbody>
              <tr v-for="b in g.rows" :key="b.id">
                <td class="ich"><IconCell :icon-key="b.iconKey || ''" :seed="b.itemId" :cn="b.nameCn" small /></td>
                <td><b><HlText :text="b.nameCn" :q="q" /></b>
                  <span v-if="b.forever" class="tag new">无限新增</span>
                  <span v-if="b.place" class="dim"> · {{ b.place }}</span></td>
                <td class="dim">{{ b.container || '—' }}</td>
                <td><span class="mono dim">{{ coordTxt(b) }}</span></td>
                <td class="mono dim">{{ b.itemId ? '#' + b.itemId : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
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
          <table class="mtx">
            <thead><tr><th>机制项</th><th>记录值</th></tr></thead>
            <tbody>
              <tr v-for="p in bagRows" :key="p[0]">
                <td>{{ p[0] }}</td><td class="mono">{{ p[1] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="card">
          <h2>营地点清单 · {{ camps.length }}<template v-if="q.trim()">（搜索 {{ q }} 命中）</template></h2>
          <div v-if="!camps.length" class="empty">这个关键词下没有营点。</div>
          <div v-else class="rgrid">
            <div v-for="(c, i) in camps" :key="i" class="rarecard">
              <ZoneMap :map-file="c.mapFile" :map-id="c.mapId" :mark="c.mark" :alt="c.zone" />
              <div class="rbody">
                <b>{{ c.zone || '区域未标' }}</b>
                <span v-if="c.landmark" class="dim">{{ c.landmark }}</span>
                <span v-if="c.whereCn" class="dim">{{ c.whereCn }}</span>
                <span class="mono dim">{{ coordTxt(c) }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </template>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import { levelRangeText as lvTxt, lvStart } from '../lib/fmt.js';
import ZoneCard from '../components/ZoneCard.vue';
import ZoneMap from '../components/ZoneMap.vue';
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
const drawers = ref({});

function coordTxt(o) {
  const s = [];
  if (o.mark) s.push('(' + o.mark.x + ', ' + o.mark.y + ')');
  if (o.world) s.push('世界 ' + o.world.x + ', ' + o.world.y);
  return s.join(' · ') || '坐标待补';
}
function boot() {
  err.value = '';
  load('data/world.json')
    .then((d) => { w.value = d; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
// 首页搜索带着板块与词跳进来（#/world?t=rares&q=…），落地就该是筛好的样子
const route = useRoute();
if (TABS.some((t) => t[0] === route.query.t)) tab.value = String(route.query.t);
if (route.query.q) q.value = String(route.query.q);
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

function toggleDrawer(id) { drawers.value[id] = !drawers.value[id]; }
function drawerOf(id) { return !!drawers.value[id]; }
function pickTab(t) { tab.value = t; zone.value = ''; }
function goZone(name) { zone.value = name; tab.value = 'rares'; }
</script>
