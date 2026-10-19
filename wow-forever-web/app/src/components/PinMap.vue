<template>
  <!-- 一张地图 + N 个点位 + 悬停浮层 + 右边的编号列表。
       2026-10-19 从稀有精英那一版抽出来：区域 / 稀有 / 书籍 / 营地四个面板共用一套。
       点位平时是虚的，指上去才实体；列表与点位共用同一套序号，双向高亮。 -->
  <div class="zband" @keydown.esc="closeAll">
    <div class="zbig" :class="{ noimg: !hasMap }">
      <!-- 这一层只装地图与点位，浮层是它的兄弟节点：点位按这一层的高度摆百分比，
           而这一层永远等于图高——浮层再怎么撑也不会把点位挪走（2026-10-19 实测到才会这么分） -->
      <div class="zcanvas">
        <!-- 占位尺寸按 ratio 给：区域底图是 3:2、副本内部底图是 1:1，
             写死 560×373 的话方图加载完会从 3:2 的预留框跳到 1:1，整块往下抖一下 -->
        <img v-if="hasMap" :src="mapSrc" :alt="alt" loading="lazy" decoding="async"
             :width="ar[0]" :height="ar[1]" @error="imgBad = true">
        <b v-if="!hasMap && mapId" class="zbig-id mono">地图编号 {{ mapId }}</b>
        <template v-if="hasMap">
          <button v-for="p in plotted" :key="p.it.key" type="button" class="zdot"
                  :class="['k-' + p.it.kind, { on: active === p.it.key }]" data-dot :data-r="p.it.key"
                  :data-kind="p.it.kind"
                  :style="{ left: p.it.x + '%', top: p.it.y + '%' }"
                  :aria-label="p.it.name + '，第 ' + p.n + ' 号点位'"
                  :aria-expanded="active === p.it.key ? 'true' : 'false'"
                  :aria-describedby="active === p.it.key ? popId : null"
                  @mouseenter="hover(p.it.key)" @mouseleave="leave(p.it.key)"
                  @focus="hover(p.it.key)" @blur="leave(p.it.key)" @click="pin(p.it.key)">
            <span class="zdot-n">{{ p.n }}</span>
          </button>
        </template>
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
import { computed, ref } from 'vue';
import { assetUrl } from '../lib/data.js';
import IconCell from './IconCell.vue';

const props = defineProps({
  alt: { type: String, default: '区域地图' },
  items: { type: Array, default: () => [] },   // 见上面注释的归一化形状
  // 这一组一条都标不出来时（区域自己就没切图，或它的记录全没 mapFile），
  // 仍然要把这张图该是谁、地图编号是多少说出来——所以留两个兜底值
  fallbackMapFile: { type: String, default: '' },
  fallbackMapId: { type: [String, Number], default: '' },
  // 底图的宽高比，只用来给浏览器预留位置（避免加载完抖一下）：区域图 560/373、副本内部图 512/512
  ratio: { type: String, default: '560/373' }
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
const plotted = computed(() => listed.value.filter((p) => p.it.pin && p.it.x != null && p.it.y != null));
const first = computed(() => plotted.value[0] || null);
const mapFile = computed(() => (first.value ? first.value.it.mapFile : props.fallbackMapFile));
const mapId = computed(() => String(first.value ? (first.value.it.mapId || '') : (props.fallbackMapId || '')));
const hasMap = computed(() => !!mapFile.value && !imgBad.value);
const mapSrc = computed(() => (mapFile.value ? assetUrl(mapFile.value) : ''));

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
}
function closeAll() { pinned.value = ''; hovered.value = ''; }
</script>
