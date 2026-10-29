<template>
  <!-- 一张地图 + N 个点位 + 悬停浮层 + 右边的编号列表。
       2026-10-19 从稀有精英那一版抽出来：区域 / 稀有 / 书籍 / 营地四个面板共用一套。
       点位平时是虚的，指上去才实体；列表与点位共用同一套序号，双向高亮。 -->
  <div v-if="hasMap || noMapLine" class="zband" :class="{ nomap: !hasMap }" @keydown.esc="closeAll">
    <div v-if="hasMap" class="zbig">
      <!-- 图例即筛选：一颗芯片筛一类，再点同一颗回"全部"。放在图上方、和点位不同层，
           所以它占多高都不会把点挪走（点位百分比是相对 .zcanvas 的）。 -->
      <div v-if="legend.length > 1" class="zlegend" role="group" aria-label="按类型筛选图上画的点">
        <button type="button" class="zlg" data-lg="all" :class="{ on: !only }" :aria-pressed="String(!only)"
                @click="setOnly('')">全部 <b class="mono">{{ plottedAll.length }}</b></button>
        <button v-for="x in legend" :key="x.kind" type="button" class="zlg" :data-lg="x.kind"
                :class="['k-' + x.kind, { on: only === x.kind }]" :aria-pressed="String(only === x.kind)"
                :aria-label="'只看' + x.label + '，' + x.n + ' 颗'"
                @click="setOnly(x.kind)">
          <i aria-hidden="true"></i>{{ x.label }} <b class="mono">{{ x.n }}</b>
        </button>
      </div>
      <!-- 这一层只装地图与点位，浮层是它的兄弟节点：点位按这一层的高度摆百分比，
           而这一层永远等于图高——浮层再怎么撑也不会把点位挪走（2026-10-19 实测到才会这么分） -->
      <div class="zcanvas">
        <!-- 占位尺寸按 ratio 给：区域底图是 3:2、副本内部底图是 1:1，
             写死 560×373 的话方图加载完会从 3:2 的预留框跳到 1:1，整块往下抖一下 -->
        <img :src="mapSrc" :alt="alt" loading="lazy" decoding="async"
             :width="ar[0]" :height="ar[1]" @error="imgBad = true">
        <button v-for="p in plotted" :key="p.it.key" type="button" class="zdot"
                :class="['k-' + p.it.kind, 't' + (TIER[p.it.kind] || 2), { on: active === p.it.key }]" data-dot :data-r="p.it.key"
                :data-kind="p.it.kind"
                :style="{ left: p.it.x + '%', top: p.it.y + '%' }"
                :aria-label="p.it.name + '，第 ' + p.n + ' 号点位'"
                :aria-expanded="active === p.it.key ? 'true' : 'false'"
                :aria-describedby="active === p.it.key ? popId : null"
                @mouseenter="hover(p.it.key)" @mouseleave="leave(p.it.key)"
                @focus="hover(p.it.key)" @blur="leave(p.it.key)" @click="pin(p.it.key)">
          <span class="zdot-n">{{ p.n }}</span>
        </button>
      </div>
      <div v-if="cur" :id="popId" class="zpop" :class="'k-' + cur.it.kind" :style="popStyle" role="tooltip">
        <div class="zpop-h">
          <b>{{ cur.it.name }}</b>
          <span v-if="cur.it.en" class="dim mono">{{ cur.it.en }}</span>
        </div>
        <div class="zpop-t">
          <span v-if="cur.it.tag" class="tag">{{ cur.it.tag }}</span>
          <span v-if="cur.it.isNew" class="tag new">无限新增</span>
          <span v-if="cur.it.level" class="dim mono">{{ cur.it.level }}</span>
          <span class="dim mono">{{ cur.it.coord }}</span>
        </div>
        <div v-if="(cur.it.rows || []).length" class="zpop-x">
          <div v-for="(r, i) in cur.it.rows" :key="i"><span class="dim">{{ r[0] }}</span><b>{{ r[1] }}</b></div>
        </div>
        <div v-if="(cur.it.drops || []).length" class="zpop-d">
          <div v-for="d in cur.it.drops" :key="d.itemId" class="zpop-i" :class="'q' + (d.quality || 0)">
            <IconCell :icon-key="d.iconKey || ''" :seed="d.itemId" :cn="d.nameCn" small />
            <span class="nm2">{{ d.nameCn }}</span>
            <span v-if="d.itemLevel" class="dim mono">iLvl {{ d.itemLevel }}</span>
            <span v-if="d.reqLevel" class="dim mono">需 {{ d.reqLevel }}</span>
            <span class="dim mono">#{{ d.itemId }}</span>
            <span v-if="d.bind" class="dim">{{ d.bind }}</span>
          </div>
        </div>
        <div v-else-if="cur.it.kind === 'rare'" class="note">这一条没有掉落记录。</div>
      </div>
    </div>

    <!-- 没有底图（这一组记录一条 mapFile 都没有，或图请求失败了）：2026-10-20 W01 起
         不再留那个 120px 高的空图框——空框把"这一片有图"暗示成了"图坏了"，还把列表挤到右边 330px。
         现在只留数据值那一行（地图编号沿用 world.json 的值，不新写句子：
         缺图时讲"我们为什么没有这张图"不上内容页，2026-10-12 那条口径），列表占满整行。
         区域名、等级、阵营、稀有/书籍/营地与坐标全在列表里，信息一条不少。 -->
    <p v-else-if="mapId" class="znomap"><b class="zbig-id mono">地图编号 {{ mapId }}</b></p>

    <!-- 列表：手机上没有悬停，这张表就是主入口；一个区域最多 33 个点位，
         密的时候列表是那条兜底。区域卡也用这一份（2026-10-19 站主：一行一张图，
         左边图右边列表，原先"小图不带列表"那个紧凑版整个撤掉） -->
    <ol class="zlist">
      <li v-for="p in listed" :key="p.it.key">
        <button type="button" class="zrow" :class="['k-' + p.it.kind, { on: active === p.it.key, nopin: !p.it.pin }]"
                data-row :data-r="p.it.key"
                @mouseenter="hover(p.it.key)" @mouseleave="leave(p.it.key)"
                @focus="hover(p.it.key)" @blur="leave(p.it.key)" @click="pin(p.it.key)">
          <span class="zn mono">{{ p.it.pin ? p.n : '—' }}</span>
          <span class="znm">{{ p.it.name }}</span>
          <span v-if="p.it.isNew" class="tag new">无限新增</span>
          <span v-if="p.it.level" class="dim mono">{{ p.it.level }}</span>
          <span class="dim mono">{{ p.it.coord }}</span>
          <span v-if="p.it.hint" class="dim mono">{{ p.it.hint }}</span>
        </button>
      </li>
    </ol>
  </div>
</template>

<script setup>
/* 三条口径（四个面板共用）：
   1) 只标"这条记录自己有 mapFile 且有坐标"的点。稀有里 73 条没有 mapFile——
      它的坐标是不是某张图的空间确认不了，**不猜位置**，只在列表里出现（序号列一条横杠）。
   2) 一张带上的图取这一组里第一条有图的记录；实测同一区域内非空 mapFile 最多一种，
      所以不会出现"一组里两张图混着标"。全组都没图就只印地图编号，与 ZoneMap 缺图时的做法一致。
   3) 浮层位置 = 点位百分比 + 一个 transform，不量 DOM。 */
/* 2026-10-29 S3（`PLAN-把OpenMap那套展示搬到网页`）：点位分级 + 图例即筛选。
   抄的是它"按重要度分级出现"这个思路，不是它的图。三条自己的口径：
   ① **底图按全量可画的点选**，筛选绝不换底图——一筛就跳图等于把玩家的参照物抽走；
   ② **右边列表始终全量**：筛的是"图上画哪几颗"，不是把信息藏起来（选了看不见那条红线）；
   ③ **只给这一屏真有点可筛的类别出芯片**，选了必然为空的不许出现（宠物页那条同样的教训）。 */
import { computed, ref, watch } from 'vue';
import { assetUrl } from '../lib/data.js';
import IconCell from './IconCell.vue';

/* 1 = 这一屏的主角，3 = 补充信息。没列进来的按 2 档（宁可不降级，也别把陌生类别压看不见） */
const TIER = { boss: 1, entry: 1, rare: 2, book: 3, camp: 3 };
const KIND_LABEL = { boss: '首领', entry: '入口', rare: '稀有', book: '书', camp: '营地' };

const props = defineProps({
  alt: { type: String, default: '区域地图' },
  items: { type: Array, default: () => [] },   // 见上面注释的归一化形状
  // 这一组一条都标不出来时（区域自己就没切图，或它的记录全没 mapFile），
  // 仍然要把这张图该是谁、地图编号是多少说出来——所以留两个兜底值
  fallbackMapFile: { type: String, default: '' },
  fallbackMapId: { type: [String, Number], default: '' },
  // 底图的宽高比，只用来给浏览器预留位置（避免加载完抖一下）：区域图 560/373、副本内部图 512/512
  ratio: { type: String, default: '560/373' },
  // 无图那一屏怎么收：true（默认）= 留一行"地图编号"+ 列表整宽；
  // false = 没有图就整块不渲染，调用方自己把编号与坐标说在别处。
  // 副本详情页「入口在哪」用的是 false——那张卡下面 `.dgeo-line` 已经把
  // "这一片的区域图本站还没有，只给坐标：地图编号 1440" 说全了，这里再印一遍就是同一屏两个数。
  noMapLine: { type: Boolean, default: true }
});

const uid = 'zpop-' + String(props.alt || '').replace(/[^A-Za-z0-9_-]/g, '');
const popId = computed(() => uid);
const imgBad = ref(false);
const ar = computed(() => {
  const p = String(props.ratio || '560/373').split('/');
  const w = parseInt(p[0], 10), h = parseInt(p[1], 10);
  return (w > 0 && h > 0) ? [w, h] : [560, 373];
});
const hovered = ref('');
const pinned = ref('');

const listed = computed(() => props.items.map((it, i) => ({ it: it, n: i + 1 })));
/* 全量可画的点：底图与图例都以这份为准（见文件头口径 ①） */
const plottedAll = computed(() => listed.value.filter((p) => p.it.pin && p.it.x != null && p.it.y != null));
const only = ref('');
const plotted = computed(() => (only.value
  ? plottedAll.value.filter((p) => p.it.kind === only.value) : plottedAll.value));
/* 图例只列"这一屏真画得出来的类别"，且带上该类有几颗——空芯片不许存在 */
const legend = computed(() => {
  const c = {};
  plottedAll.value.forEach((p) => { c[p.it.kind] = (c[p.it.kind] || 0) + 1; });
  return Object.keys(c).map((k) => ({ kind: k, n: c[k], label: KIND_LABEL[k] || k }));
});
const first = computed(() => plottedAll.value[0] || null);
const mapFile = computed(() => (first.value ? first.value.it.mapFile : props.fallbackMapFile));
const mapId = computed(() => String(first.value ? (first.value.it.mapId || '') : (props.fallbackMapId || '')));
const hasMap = computed(() => !!mapFile.value && !imgBad.value);
const mapSrc = computed(() => (mapFile.value ? assetUrl(mapFile.value) : ''));
/* 换图必须把失败标记清掉（2026-10-20 W01）：imgBad 原来只在挂载时是 false，
   一次失败就永久落回无图态——同一块面板里从"有图的区域"跳到另一个区域（items/fallback 变了、
   组件实例复用），新那张图明明是好的也再也不显示。ZoneMap 早就有这条 watch，这里补齐。 */
watch(mapFile, () => { imgBad.value = false; });

const active = computed(() => pinned.value || hovered.value);
const cur = computed(() => {
  if (!active.value || !hasMap.value) return null;
  return plotted.value.filter((p) => p.it.key === active.value)[0] || null;
});
/* 横向靠右就往左开；纵向靠下就整块挂在点位上面、靠上就挂在下面，中间居中 */
const popStyle = computed(() => {
  const c = cur.value;
  if (!c) return {};
  const x = c.it.x, y = c.it.y;
  const tx = x > 58 ? 'calc(-100% - 16px)' : '16px';
  const ty = y > 62 ? 'calc(-100% + 12px)' : (y < 24 ? '-12px' : '-50%');
  return { left: x + '%', top: y + '%', transform: 'translate(' + tx + ', ' + ty + ')' };
});

function hover(k) { if (!pinned.value) hovered.value = k; }
function leave(k) { if (hovered.value === k) hovered.value = ''; }
function pin(k) {
  if (pinned.value === k) { pinned.value = ''; return; }
  pinned.value = k;
  hovered.value = '';
  /* 钉住的那颗如果被筛掉了，浮层会指向一颗看不见的点——直接把选择收掉，
     比留一个"浮层在、点不在"的半成品好（口径 ② 的另一面：不许代码静默留着失效的选择） */
  if (only.value && (!plotted.value.some((p) => p.it.key === k))) pinned.value = '';
}
function setOnly(k) {
  only.value = (only.value === k || !k) ? '' : k;
  pinned.value = ''; hovered.value = '';
}
/* 换区域/换本时，上一屏的筛选对新屏幕未必成立：留下的类在新屏一颗都没有就自动清回"全部"，
   不然会出现"芯片还在但图上一个点都没有"。 */
watch(legend, (ls) => { if (only.value && !ls.some((x) => x.kind === only.value)) only.value = ''; });
function closeAll() { pinned.value = ''; hovered.value = ''; }
</script>
