<template>
  <div class="zcard" :class="{ lk: clickable }" :data-zone="z.nameCn">
    <!-- 2026-10-19：卡里的地图换成 PinMap 紧凑版——这一张图上标出该区域能找到的
         稀有 / 书 / 营地，指上去弹同一套浮层。根节点从 <button> 改成 <div>：
         点位自己是按钮，按钮里套按钮是无效 HTML，浏览器会把内层挪出去，布局就散了。
         下半截信息区改成按钮，点它仍然跳到该区域的稀有列表（与原来整卡可点等效）。
         注释必须写在根节点里面：写在 <template> 与根元素之间会多出第二个根节点，
         组件单测里 wrapper.classes() 直接变空数组（本轮踩过）。 -->
    <PinMap :alt="z.nameCn + '的区域地图'" :items="items" compact
            :fallback-map-file="z.mapFile || ''" :fallback-map-id="z.mapId || ''" />
    <button type="button" class="zbody" :disabled="!clickable" :data-open="z.nameCn" @click="click">
      <b>{{ z.nameCn }}</b>
      <span v-if="seal" class="tag new">{{ seal }}</span>
      <span class="dim mono">{{ lv }}</span>
      <span class="dim">{{ z.faction || '阵营未定' }}</span>
      <span v-if="z.flight" class="dim">{{ flightText }}</span>
      <span class="zcnt">
        <template v-if="z.rareCount">{{ z.rareCount }} 个稀有</template>
        <template v-if="z.rareCount && z.bookCount"> · </template>
        <template v-if="z.bookCount">{{ z.bookCount }} 本书</template>
      </span>
    </button>
  </div>
</template>

<script setup>
/* 区域卡：整卡可点 = 跳到该区域的稀有精英列表。没采到东西的区域不可点，避免点了空跳。
   「没有飞行路线 / 有飞行路线，站点待实测」这一行留着：它回答的是玩家会问的事
   （这块地方能不能飞），不是讲我们数据过程的备注。 */
import { computed } from 'vue';
import { levelRangeText as lvTxt } from '../lib/fmt.js';
import PinMap from './PinMap.vue';

const props = defineProps({
  z: { type: Object, required: true },
  items: { type: Array, default: () => [] },
  seal: { type: String, default: '' }
});
const emit = defineEmits(['open']);
const lv = computed(() => lvTxt(props.z));
const clickable = computed(() => !!(props.z.rareCount || props.z.bookCount));
const flightText = computed(() => (props.z.flight === 'no-route'
  ? '没有飞行路线' : '有飞行路线，站点待实测'));
function click() { if (clickable.value) emit('open', props.z.nameCn); }
</script>
