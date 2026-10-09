<template>
  <button type="button" class="zcard" :class="{ lk: clickable }" :data-zone="z.nameCn" @click="click">
    <ZoneMap :map-file="z.mapFile" :map-id="z.mapId" :alt="z.nameCn" />
    <div class="zbody">
      <b>{{ z.nameCn }}</b>
      <span v-if="seal" class="tag new">{{ seal }}</span>
      <span class="dim mono">{{ lv }}</span>
      <span class="dim">{{ z.faction || '阵营未定' }}</span>
      <span v-if="z.flight" class="dim">{{ flightText }}</span>
      <span class="zcnt">
        <template v-if="z.rareCount || z.bookCount">
          <template v-if="z.rareCount">{{ z.rareCount }} 个稀有</template>
          <template v-if="z.rareCount && z.bookCount"> · </template>
          <template v-if="z.bookCount">{{ z.bookCount }} 本书</template>
        </template>
        <i v-else class="dim">这一版还没有数据</i>
      </span>
    </div>
  </button>
</template>

<script setup>
/* 区域卡：整卡可点 = 跳到该区域的稀有精英列表。没采到东西的区域不可点，避免点了空跳。 */
import { computed } from 'vue';
import { levelRangeText as lvTxt } from '../lib/fmt.js';
import ZoneMap from './ZoneMap.vue';

const props = defineProps({
  z: { type: Object, required: true },
  seal: { type: String, default: '' }
});
const emit = defineEmits(['open']);
const lv = computed(() => lvTxt(props.z));
const clickable = computed(() => !!(props.z.rareCount || props.z.bookCount));
const flightText = computed(() => (props.z.flight === 'no-route'
  ? '客户端里还没有飞行路线' : '有飞行路线，站点待实测'));
function click() { if (clickable.value) emit('open', props.z.nameCn); }
</script>
