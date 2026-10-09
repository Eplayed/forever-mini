<template>
  <div v-if="mapFile && !broken" class="zmap">
    <img :src="src" :alt="alt + '的区域小地图'" loading="lazy" decoding="async" width="560" height="373"
         @error="broken = true">
    <b v-if="mark" class="zmark" aria-hidden="true" :style="pos"></b>
    <span class="dbn2-mark">客户端地图 · 本地转存</span>
  </div>
  <div v-else class="zmap none">
    <span class="dim">{{ broken ? '这张小地图本地文件读不出来' : '这一张客户端没有切出小地图' }}</span>
    <b v-if="mapId" class="mono">地图编号 {{ mapId }}</b>
  </div>
</template>

<script setup>
/* 区域小地图块：本地图 + 数据里的百分比标记点。
   标记点位置是数据不是样式，所以用 :style 绑定（旧站是渲染后拿 JS 写 left/top，
   那正是 innerHTML 时代没法做的写法）。图缺失时不放假图，退回文字 + mapId。 */
import { computed, ref, watch } from 'vue';
import { assetUrl } from '../lib/data.js';

const props = defineProps({
  mapFile: { type: String, default: '' },
  mapId: { type: [String, Number], default: '' },
  mark: { type: Object, default: null },
  alt: { type: String, default: '' }
});
const broken = ref(false);
const src = computed(() => (props.mapFile ? assetUrl(props.mapFile) : ''));
const pos = computed(() => (props.mark
  ? { left: props.mark.x + '%', top: props.mark.y + '%' }
  : {}));
watch(() => props.mapFile, () => { broken.value = false; });
</script>
