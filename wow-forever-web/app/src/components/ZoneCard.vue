<template>
  <div class="zcard" :class="{ lk: clickable }" :data-zone="z.nameCn">
    <!-- 2026-10-19 改过两次：先是换成卡里嵌一张小图（一行两张），站主说图太小，
         现在改成**一行一张**：上面一行区域信息（点它仍跳到该区域的稀有列表），
         下面一整套点位图（左图右列表，与稀有精英那一屏同一版式）。
         根节点是 div 不是 button：点位自己是按钮，按钮里套按钮是无效 HTML，
         浏览器会把内层挪出去，布局就散了。
         注释必须写在根节点里面：写在 <template> 与根元素之间会多出第二个根节点，
         组件单测里 wrapper.classes() 直接变空数组（本轮踩过）。 -->
    <button type="button" class="zhead" :disabled="!clickable" :data-open="z.nameCn" @click="click">
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
    <PinMap :alt="z.nameCn + '的区域地图'" :items="items"
            :fallback-map-file="z.mapFile || ''" :fallback-map-id="z.mapId || ''" />
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
