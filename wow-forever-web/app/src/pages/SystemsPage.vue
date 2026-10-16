<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="s">
    <!-- 主卡卡片头：systems 不在旧站 PAGE_HEAD_SEC 表里，走 cdhead 的 noart 形态。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">系统与新区域</h1></div>
    </div>

    <!-- 2026-10-12 站主决定：这一页只留词条名——逐条的来源说明（note 字段）与分级徽标不再上内容页，
         出处集中在溯源页（provenance.html）。撤完那些句子后一条一个卡片太空，
         所以改成一组一张表：这一页本来就是"这个词官方中文叫什么"的对照表。 -->
    <div v-for="g in s.groups" :key="g.id" class="card">
      <h2>{{ g.label }}<span class="dim mono"> · {{ g.items.length }} 条</span></h2>
      <div class="boardwrap">
        <table class="board">
          <colgroup><col style="width:46%"><col></colgroup>
          <thead><tr><th>中文名</th><th>英文原名</th></tr></thead>
          <tbody>
            <tr v-for="x in g.items" :key="x.id">
              <td><b>{{ x.nameCn || '中文名未定' }}</b></td>
              <td class="en mono"><template v-if="x.nameEn">{{ x.nameEn }}</template><span v-else class="dim">英文原名未证实</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 系统与新区域 · 与旧站 app.js systems()（行 2356-2373）逐块对齐。
   一组一张中英对照表，内容全部从 systems.json 现取，一条不写死。 */
import { onMounted, ref } from 'vue';
import { load } from '../lib/data.js';

const s = ref(null);
const err = ref('');

function boot() {
  err.value = '';
  load('data/systems.json')
    .then((json) => { s.value = json; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次
</script>
