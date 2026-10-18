<template>
  <!-- 一个区域 = 一张地图。原来每条稀有各带一张同样的区域图，一个区域八条就是八张重复图；
       2026-10-18 站主要改成"在地图上直接标点位，平时虚着，指上去实体并弹出信息"。 -->
  <div class="zband" @keydown.esc="closeAll">
    <div class="zbig" :class="{ noimg: !hasMap }">
      <!-- 这一层只装地图和点位。浮层是它的兄弟节点，不是子节点——
           点位按父盒高度的百分比摆，浮层一旦塞进同一个盒子里把高度撑大，
           所有点位就会集体往下跳一截（375 上实测到，桌面靠 absolute 不占位躲过了这一劫）。 -->
      <div class="zcanvas">
        <img v-if="hasMap" :src="mapSrc" :alt="zone + '的区域地图'" loading="lazy" decoding="async"
             width="560" height="373" @error="imgBad = true">
        <b v-if="!hasMap" class="zbig-id mono">{{ mapId || '无图' }}</b>
        <template v-if="hasMap">
          <button v-for="p in plotted" :key="p.r.id" type="button" class="zdot"
                  :class="{ on: active === p.r.id }" data-dot :data-r="p.r.id"
                  :style="{ left: p.r.mark.x + '%', top: p.r.mark.y + '%' }"
                  :aria-label="p.r.nameCn + '，第 ' + p.n + ' 号点位'"
                  :aria-expanded="active === p.r.id ? 'true' : 'false'"
                  :aria-describedby="active === p.r.id ? popId : null"
                  @mouseenter="hover(p.r.id)" @mouseleave="leave(p.r.id)"
                  @focus="hover(p.r.id)" @blur="leave(p.r.id)" @click="pin(p.r.id)">
            <span class="zdot-n">{{ p.n }}</span>
          </button>
        </template>
      </div>
      <div v-if="cur" :id="popId" class="zpop" :style="popStyle" role="tooltip">
        <div class="zpop-h">
          <b>{{ cur.r.nameCn }}</b>
          <span v-if="cur.r.nameEn" class="dim mono">{{ cur.r.nameEn }}</span>
        </div>
        <div class="zpop-t">
          <span class="tag">{{ cur.r.kind === 'rare-elite' ? '稀有精英' : '稀有' }}</span>
          <span v-if="cur.r.isNew" class="tag new">无限新增</span>
          <span class="dim mono">{{ lvTxt(cur.r) }}</span>
          <span class="dim mono">{{ coordTxt(cur.r) }}</span>
        </div>
        <div v-if="(cur.r.drops || []).length" class="zpop-d">
          <div v-for="d in cur.r.drops" :key="d.itemId" class="zpop-i" :class="'q' + (d.quality || 0)">
            <IconCell :icon-key="d.iconKey || ''" :seed="d.itemId" :cn="d.nameCn" small />
            <span class="nm2">{{ d.nameCn }}</span>
            <span v-if="d.itemLevel" class="dim mono">iLvl {{ d.itemLevel }}</span>
            <span v-if="d.reqLevel" class="dim mono">需 {{ d.reqLevel }}</span>
            <span class="dim mono">#{{ d.itemId }}</span>
            <span v-if="d.bind" class="dim">{{ d.bind }}</span>
          </div>
        </div>
        <div v-else class="note">这一条没有掉落记录。</div>
      </div>
    </div>

    <!-- 列表一直摆在旁边：手机上没有悬停，信息不能只活在浮层里；
         而且一个区域最多有 33 条（贫瘠之地），点位挤在一张图上时列表是那条兜底。 -->
    <ol class="zlist">
      <li v-for="p in listed" :key="p.r.id">
        <button type="button" class="zrow" :class="{ on: active === p.r.id, nopin: !p.r.mark }"
                data-row :data-r="p.r.id"
                @mouseenter="hover(p.r.id)" @mouseleave="leave(p.r.id)"
                @focus="hover(p.r.id)" @blur="leave(p.r.id)" @click="pin(p.r.id)">
          <span class="zn mono">{{ p.r.mark ? p.n : '—' }}</span>
          <span class="znm">{{ p.r.nameCn }}</span>
          <span v-if="p.r.isNew" class="tag new">无限新增</span>
          <span class="dim mono">{{ lvTxt(p.r) }}</span>
          <span class="dim mono">{{ coordTxt(p.r) }}</span>
          <span v-if="(p.r.drops || []).length" class="dim mono">掉落 {{ p.r.drops.length }} 件</span>
        </button>
      </li>
    </ol>
  </div>
</template>

<script setup>
/* 区域稀有点位图（2026-10-18）。三条口径写死在这里：
   1) 只标"这条稀有自己带地图文件"的点位。362 条里有 73 条没有 mapFile——
      它们的坐标是不是同一张图的空间没法确认，**不猜位置**，只在右边列表里出现（编号列画一条横杠）。
   2) 一个区域内带图的稀有共用同一张图（实测 41 个区域里非空的 mapFile 每个区域最多一种），
      所以取第一条有图的当这张带图；全组都没图就退回只显示地图编号，与 ZoneMap 缺图时的做法一致。
   3) 浮层位置用百分比 + 四种翻转，不量 DOM：点位本来就是按 % 摆的，
      靠右就朝左开、靠下就朝上开，省掉一套测量与重排逻辑。 */
import { computed, ref } from 'vue';
import { assetUrl } from '../lib/data.js';
import { levelRangeText as lvTxt, coordText as coordTxt } from '../lib/fmt.js';
import IconCell from './IconCell.vue';

const props = defineProps({
  zone: { type: String, default: '' },
  rows: { type: Array, default: () => [] }
});

const imgBad = ref(false);
const hovered = ref('');
const pinned = ref('');
const popId = 'zpop-' + String(props.zone || '').replace(/[^A-Za-z0-9_-]/g, '');

/* 编号按列表顺序给（列表与点位共用同一个 n，两边对得上） */
const listed = computed(() => props.rows.map((r, i) => ({ r: r, n: i + 1 })));
const plotted = computed(() => listed.value.filter((p) => p.r.mapFile && p.r.mark));
const mapFile = computed(() => {
  const f = plotted.value[0];
  return f ? f.r.mapFile : '';
});
const mapId = computed(() => {
  const f = plotted.value[0];
  return f ? String(f.r.mapId || '') : '';
});
const hasMap = computed(() => !!mapFile.value && !imgBad.value);
const mapSrc = computed(() => (mapFile.value ? assetUrl(mapFile.value) : ''));

const active = computed(() => pinned.value || hovered.value);
const cur = computed(() => {
  if (!active.value || !hasMap.value) return null;
  return plotted.value.filter((p) => p.r.id === active.value)[0] || null;
});
/* 浮层位置 = 点位百分比 + 一个 transform，不量 DOM：
   横向靠右就往左开；纵向靠下就把整块挂在点位上面、靠上就挂在下面，中间就居中。
   窄屏这条 transform 由 CSS 覆盖成"整宽贴在图下面"，所以这里只算桌面。 */
const popStyle = computed(() => {
  const c = cur.value;
  if (!c) return {};
  const x = c.r.mark.x, y = c.r.mark.y;
  const tx = x > 58 ? 'calc(-100% - 16px)' : '16px';
  const ty = y > 62 ? 'calc(-100% + 12px)' : (y < 24 ? '-12px' : '-50%');
  return { left: x + '%', top: y + '%', transform: 'translate(' + tx + ', ' + ty + ')' };
});

function hover(id) { if (!pinned.value) hovered.value = id; }
function leave(id) { if (hovered.value === id) hovered.value = ''; }
function pin(id) {
  if (pinned.value === id) { pinned.value = ''; return; }
  pinned.value = id;
  hovered.value = '';
}
function closeAll() { pinned.value = ''; hovered.value = ''; }
</script>
