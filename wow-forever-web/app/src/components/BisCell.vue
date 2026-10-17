<template>
  <button ref="root" type="button" class="pzcell" :class="{ on: on }"
          @click="$emit('pick', cell.slot, root)" :aria-pressed="on ? 'true' : 'false'">
    <span class="qbox" :class="'bq' + (cell.quality || 0)">
      <IconCell :icon-key="cell.iconKey" :seed="cell.item" :cn="cell.name" small />
    </span>
    <span class="pzbody">
      <span class="pzslot">{{ cell.slot }}<span v-if="cell.cell > 1" class="mono"> · {{ cell.cell }}</span></span>
      <b class="pzname" :class="'q' + (cell.quality || 0)">{{ cell.name }}</b>
      <span class="pzil mono">装等 {{ cell.ilvl }}</span>
    </span>
  </button>
</template>

<script setup>
/* 纸娃娃上的一格：图标（按品质描边）+ 部位 + 装备名 + 装等。
   三栏布局要摆它三次，抽出来免得同一段标记在页面里抄三遍。
   两枚戒指 / 两个饰品同名，靠 cell 序号区分（数据里同一部位的第二格 cell = 2）。 */
import { ref } from 'vue';
import IconCell from './IconCell.vue';

defineProps({
  cell: { type: Object, required: true },
  on: { type: Boolean, default: false }
});
defineEmits(['pick']);
/* 把自己这个元素一起抛出去：备选是 popover，要知道贴着谁摆 */
const root = ref(null);
</script>

<style scoped>
.pzcell { display: flex; align-items: center; gap: 9px; min-height: 52px; padding: 7px 9px;
  background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 5px;
  text-align: left; cursor: pointer; color: var(--txt) }
.pzcell:hover { border-color: var(--gold-deep) }
.pzcell.on { border-color: var(--gold); box-shadow: inset 0 0 0 1px var(--gold-deep) }
.pzbody { display: flex; flex-direction: column; min-width: 0 }
.pzslot { font-size: 11px; color: var(--txt-muted) }
.pzname { font-size: 13px; line-height: 1.3; font-weight: 600; overflow-wrap: anywhere }
.pzil { font-size: 11px; color: var(--txt-dim) }
.qbox { display: inline-flex; border: 1px solid var(--line-2); border-radius: 4px; padding: 1px }
.qbox.bq2 { border-color: rgba(51, 167, 51, .6) }
.qbox.bq3 { border-color: rgba(74, 130, 224, .65) }
.qbox.bq4 { border-color: rgba(163, 105, 217, .65) }
.qbox.bq5 { border-color: rgba(201, 162, 74, .7) }
</style>
