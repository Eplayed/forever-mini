<template>
  <div ref="el" class="pzpop" role="dialog" :aria-label="slot + '：可替换的装备'">
    <div class="pzh">
      <div>
        <h3>{{ slot }}<span class="pzh-n mono">{{ rows.length }} 件可换</span></h3>
        <p class="dim">{{ head }}</p>
      </div>
      <button type="button" class="pzx" aria-label="关闭" @click="$emit('close')">×</button>
    </div>
    <div class="boardwrap pzbody">
      <table class="board" id="pzalts">
        <colgroup><col class="c-ico"><col style="width:32%"><col class="c-num"><col class="c-num"><col></colgroup>
        <thead><tr><th class="c-ico">图标</th><th>装备</th><th class="c-num">装等</th>
          <th class="c-num">需要</th><th class="w-tail">从哪儿拿</th></tr></thead>
        <tbody>
          <tr v-for="(x, i) in rows" :key="x.item" :class="{ cur: i === 0 }">
            <td class="c-ico"><span class="qbox" :class="'bq' + (x.quality || 0)">
              <IconCell :icon-key="x.iconKey" :seed="x.item" :cn="x.name" small /></span></td>
            <td><span class="nm" :class="'q' + (x.quality || 0)">{{ x.name }}</span>
              <span v-if="i === 0" class="tag">这套选的</span>
              <span class="sub" v-if="x.st">{{ x.st }}</span></td>
            <td class="c-num num">{{ x.ilvl }}</td>
            <td class="c-num num">{{ x.rlvl }}</td>
            <td class="w-tail"><span class="dim">{{ x.src }}</span>
              <router-link class="pzgo" :to="{ path: '/items', query: { q: x.name } }">去物品库看详情 →</router-link></td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="pzf dim">顺序照这份名单列的先后，本站不重新排、也不做强度评价。</p>
  </div>
</template>

<script setup>
/* 配装页的备选 popover（2026-10-17 站主改口径：不要弹窗，要贴着点的那一格弹出来）。
   与上一版 modal 的区别：没有遮罩、不锁页面，点别处或按 ESC 就收。
   位置自己算：挂在 body 上按触发元素的矩形摆 fixed，右边放不下就翻到左边，
   上下超出就夹回视口内；滚动与窗口变化时重算。
   行数据仍由 BisPage 算好传进来——名字、装等、属性、来源都要回 items.json 查，
   这一层只管摆与关，不碰数据。 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import IconCell from './IconCell.vue';

const props = defineProps({
  slot: { type: String, required: true },
  rows: { type: Array, default: () => [] },
  head: { type: String, default: '' },
  anchor: { type: null, default: null }
});
const emit = defineEmits(['close']);
const el = ref(null);

function place() {
  const a = props.anchor instanceof HTMLElement ? props.anchor : null;
  const p = el.value;
  if (!p) return;
  if (!a) { p.classList.add('pzpop-fixed'); return; }
  const narrow = window.innerWidth < 900;
  const pw = p.offsetWidth;
  const ph = p.offsetHeight;
  const r = a.getBoundingClientRect();
  let top;
  let left;
  if (narrow) {
    /* 窄屏贴着某一格摆会盖住大半屏，改成贴底的一张面板，仍然是非模态的 popover */
    p.style.left = '8px';
    p.style.width = (window.innerWidth - 16) + 'px';
    p.style.top = Math.max(8, window.innerHeight - ph - 8) + 'px';
    return;
  }
  left = r.right + 10;
  if (left + pw > window.innerWidth - 8) left = r.left - pw - 10;
  if (left < 8) left = Math.max(8, Math.min(r.left, window.innerWidth - pw - 8));
  top = r.top - 6;
  if (top + ph > window.innerHeight - 8) top = Math.max(8, window.innerHeight - ph - 8);
  p.style.left = Math.round(left) + 'px';
  p.style.top = Math.round(top) + 'px';
  p.style.width = '';
}

function onDoc(e) {
  const p = el.value;
  const a = props.anchor instanceof HTMLElement ? props.anchor : null;
  if (!p || !a) return;
  if (p.contains(e.target) || a.contains(e.target)) return;
  emit('close');
}
function onKey(e) { if (e.key === 'Escape') emit('close'); }

function bind() {
  document.addEventListener('pointerdown', onDoc, true);
  window.addEventListener('keydown', onKey);
  window.addEventListener('scroll', place, true);
  window.addEventListener('resize', place);
}
function unbind() {
  document.removeEventListener('pointerdown', onDoc, true);
  window.removeEventListener('keydown', onKey);
  window.removeEventListener('scroll', place, true);
  window.removeEventListener('resize', place);
}

onMounted(() => { nextTick(place); bind(); });
onBeforeUnmount(unbind);
/* 换部位 / 换阵营 / 换职业都会换 anchor 与内容，重算一次位置 */
watch(() => [props.slot, props.anchor], () => nextTick(place));
watch(() => props.rows.length, () => nextTick(place));
</script>

<style scoped>
.pzpop { position: fixed; z-index: 62; width: min(620px, calc(100vw - 20px));
  max-height: min(66vh, 620px); display: flex; flex-direction: column; overflow: hidden;
  background: var(--panel); border: 1px solid var(--line-2); border-radius: 6px;
  box-shadow: 0 14px 34px rgba(0, 0, 0, .48) }
.pzpop-fixed { left: 50%; top: 50%; transform: translate(-50%, -50%) }
.pzh { display: flex; gap: 10px; align-items: flex-start; padding: 11px 13px 9px;
  border-bottom: 1px solid var(--line-2) }
.pzh h3 { margin: 0; font-size: 15px; color: var(--txt-title) }
.pzh-n { font-size: 11.5px; color: var(--txt-muted); margin-left: 7px; font-weight: 400 }
.pzh .dim { margin: 3px 0 0; font-size: 11.5px }
.pzx { margin-left: auto; width: 30px; height: 30px; flex: 0 0 auto; font-size: 18px; line-height: 1;
  background: transparent; border: 1px solid var(--line-2); border-radius: 4px; color: var(--txt-dim); cursor: pointer }
.pzx:hover { color: var(--txt-title); border-color: var(--gold-deep) }
/* .pzpop 是 flex 纵向，子项默认 min-width:auto 等于内容宽，而 .board 在窄屏下有
   min-width:640px——不写 min-width:0 整张表会把 popover 撑破
   （上一版 modal 就是这么把 375 视口撑到 674 的）。 */
.pzbody { overflow: auto; padding: 0 13px; flex: 1 1 auto; min-width: 0 }
/* 表头吸附的 top 全站是按顶栏高度算的（--hd-h），弹层里的参照物是弹层自己，
   照抄会把表头推到第一行下面（实拍为证），这里改回贴着弹层顶。 */
.pzbody table.board > thead > tr > th { top: 0 }
.pzf { margin: 0; padding: 8px 13px 10px; border-top: 1px solid var(--line-2); font-size: 11.5px }
.pzgo { display: block; margin-top: 3px; font-size: 11.5px; color: var(--azure) }
tr.cur { background: rgba(201, 162, 74, .07) }
.qbox { display: inline-flex; border: 1px solid var(--line-2); border-radius: 4px; padding: 1px }
.qbox.bq2 { border-color: rgba(51, 167, 51, .6) }
.qbox.bq3 { border-color: rgba(74, 130, 224, .65) }
.qbox.bq4 { border-color: rgba(163, 105, 217, .65) }
.qbox.bq5 { border-color: rgba(201, 162, 74, .7) }
</style>
