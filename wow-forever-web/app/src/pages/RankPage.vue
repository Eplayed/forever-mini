<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="base">
    <!-- 主卡卡片头：rank 不在旧站 PAGE_HEAD_SEC 表里，走 cdhead 的 noart 形态。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">职业资料完整度排行</h1></div>
      <p class="dim">这是<b>本站资料覆盖度</b>的排序：哪个职业在我们这儿查得到的东西多、哪部分还是只有客户端解包撑着。它回答"这个职业的资料全不全"，<b>不回答哪个职业强</b>——我们没有战斗日志与实测数据，也不做强度排行。</p>
      <div class="banner">排序依据：先按"官方中文佐证的条数"，再按"本站条目合计"。全部由数据现算，改了数据重新生成就会变，不是人工排的名次。</div>
      <div class="card">
        <h2>九职业的官方中文佐证，先比长短</h2>
        <div class="rankbars">
          <div v-for="x in rows" :key="x.classId" class="rb">
            <b>{{ cnOf(x) }}</b>
            <i><s :style="{ width: pct(x.official) }"></s><u :style="{ width: pct(x.datamine) }"></u></i>
            <em class="mono">{{ x.official }} / {{ x.datamine }}</em>
          </div>
        </div>
        <p class="note">上条是官方中文佐证的条数，下条是只有客户端解包支撑的条数；长短按全站最多的那个职业归一。表格在下面，给的是同一批数的精确值。</p>
      </div>
      <div class="boardwrap">
        <table class="board ranktab">
          <colgroup><col class="c-num"><col style="width:16%"><col style="width:16%"><col style="width:14%"><col style="width:16%"><col></colgroup>
          <thead><tr><th class="c-num">名次</th><th>职业</th><th>官方中文佐证</th><th>客户端解包</th><th>本站条目合计</th><th>覆盖情况</th></tr></thead>
          <tbody>
            <tr v-for="x in rows" :key="x.classId">
              <td class="ich"><b class="rankno mono">{{ x.place }}</b></td>
              <td><IconCell :icon-key="clsIcon(x.classId)" :seed="x.classId" :cn="cnOf(x)" small /><b>{{ cnOf(x) }}</b><span class="dim mono">{{ x.classId }}</span></td>
              <td class="mono">{{ x.official }}</td>
              <td class="mono">{{ x.datamine }}</td>
              <td class="mono">{{ x.total }}</td>
              <td><span class="cov mini"><i class="L0" :style="{ width: pct(x.official) }"></i><i class="L2" :style="{ width: pct(x.datamine) }"></i></span><span class="mono dim">{{ x.share }}% 有官方中文</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- 2026-10-12 站主决定：这一页只留排行本身，外加那句"是本站整理的排序、不是强度排行"
           （红线要求留着）。"每一列怎么算出来的"那段口径说明、L0/L2 图例与「来源与核对」块
           都移出内容页：列名已在表头，条数的含义由右侧那句"x% 有官方中文"直接给。 -->
      <p class="dim">这个排序是本站按自己查得到的条数排的，改了数据重新生成就会变，不是官方结论。</p>
    </div>
  </template>
</template>

<script setup>
/* 资料完整度排行 · 与旧站 app.js rank()（行 3410-3454）逐块对齐。
   红线：排行页必须原样保留「本站整理的排序，不是强度排行」声明；
   条数与横条全部由数据现算（归一基数是全站最大的本站条目合计，与旧站同一算法）。
   旧站还顺手 load 了 art.json（渲染里没用到），这里保留同一次请求，
   对拍脚本核对请求数据清单时两边才一致。 */
import { computed, onMounted, ref } from 'vue';
import { load } from '../lib/data.js';
import IconCell from '../components/IconCell.vue';

const base = ref(null);
const err = ref('');

function boot() {
  err.value = '';
  Promise.all([load('data/scale.json'), load('data/classes.json'),
    load('data/art.json').catch(() => ({}))])
    .then((rs) => { base.value = { S: rs[0].scale || {}, classes: rs[1].classes || [] }; })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);   // 从别的页切回来看不到数据时（比如 JSON 改名），重新拉一次

const classes = computed(() => (base.value && base.value.classes) || []);
const rows = computed(() => (base.value && base.value.S.classRank) || []);
const max = computed(() => rows.value.reduce((m, x) => Math.max(m, x.total), 1));

function cnOf(x) {
  const hit = classes.value.filter((c) => c.id === x.classId)[0];
  return (hit && hit.cn) || x.classId;
}
function clsIcon(classId) {
  const hit = classes.value.filter((c) => c.id === classId)[0];
  return (hit && hit.iconKey) || '';
}
function pct(n) { return Math.round(n / max.value * 100) + '%'; }
</script>
