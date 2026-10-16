<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <!-- 与旧站 app.js achievements() 逐块对齐。页头是 noart 分支：成就没有对应的板块原画，
         按「不拿不相干的图凑数」那条留着左侧蓝线（时间表/速查/动态/排行/溯源同一处理）。 -->
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">成就目录</h1></div>
      <div class="field">
        <input type="search" id="q" placeholder="搜中文或英文" :value="q" @input="onQ">
        <select id="g" aria-label="按大类筛选" v-model="fg">
          <option value="">全部大类</option>
          <option v-for="x in groups" :key="x.gid" :value="x.gid">{{ x.top }}（{{ shownOf(x) }}）</option>
        </select>
        <span class="dim mono" id="cnt">{{ list.length }} / {{ rows.length }} 条</span>
      </div>
    </div>

    <div class="card tblbox">
      <div id="tbl">
        <template v-if="blocks.length">
          <template v-for="b in blocks" :key="b.gid + '-' + b.cat">
            <div class="lgrp">
              <b>{{ b.top }}</b>
              <span class="dim mono">{{ b.cat }}</span>
              <span class="dim">{{ b.rows.length }} 条</span>
            </div>
            <div class="scrollx">
              <table class="entab">
                <thead><tr><th class="ich">图标</th><th>成就</th><th>英文原名</th><th>编号</th></tr></thead>
                <tbody>
                  <tr v-for="x in b.rows" :key="x.id">
                    <td class="ich"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.name" /></td>
                    <td><b><HlText :text="x.name" :q="q" /></b><br v-if="x.forever"><span v-if="x.forever" class="dim">无限新增</span></td>
                    <td class="en"><HlText v-if="x.nameEn" :text="x.nameEn" :q="q" /></td>
                    <td class="mono dim">#{{ x.achId }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </template>
        <div v-else class="empty">没有匹配的成就，换个词或放宽大类筛选。</div>
      </div>
    </div>
  </template>
</template>

<script setup>
/* 成就目录 · 与旧站 app.js achievements() 逐块对齐。
   只列目录：编号、中文名、英文原名、大类与小类。成就的完成条件文本三份资料里都有，
   那是转述站写的正文（红线：不复制描述文案），这里一格都不落；
   缺的地方按 2026-10-13 口径留空，不写"待补"这类讲缺口的话。
   devOnly 那几条（客户端里的开发埋点、问卷、已废弃条目）不列——它们不是玩家能拿的成就，
   列出来反而是在骗人；条目仍在数据里，差额由 meta.counts.devOnly 点名，溯源页说。 */
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import IconCell from '../components/IconCell.vue';
import HlText from '../components/HlText.vue';

const d = ref(null);
const err = ref('');
const route = useRoute();
const q = ref(String(route.query.q || ''));
const fg = ref(String(route.query.g || ''));

function boot() {
  err.value = '';
  load('data/achievements.json')
    .then((doc) => {
      const rowsAll = ((doc || {}).achievements || []).filter((x) => !x.devOnly);
      d.value = {
        rows: rowsAll,
        groups: (((doc || {}).meta || {}).counts || {}).groups || []
      };
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);

const rows = computed(() => (d.value && d.value.rows) || []);
const groups = computed(() => (d.value && d.value.groups) || []);
const list = computed(() => rows.value.filter((x) => {
  if (fg.value && x.gid !== fg.value) return false;
  if (q.value && (String(x.name || '') + String(x.nameEn || '')).toLowerCase()
    .indexOf(q.value.toLowerCase()) < 0) return false;
  return true;
}));

/* 下拉里的数用 shown（页面上真列出来的条数），不用 count（源侧自报的全量）——
   两个数不相等时，下拉写 60、屏幕上翻出来只有 51，玩家看到的是自相矛盾。 */
function shownOf(g) { return g.shown === undefined ? g.count : g.shown; }

// 分组顺序跟着 meta.counts.groups，小类按这一类里首次出现的顺序（与旧站同一算法）
const blocks = computed(() => {
  const out = [];
  groups.value.forEach((grp) => {
    const sub = {};
    const order = [];
    list.value.forEach((x) => {
      if (x.gid !== grp.gid) return;
      const k = x.cat || '未分类';
      if (!sub[k]) { sub[k] = []; order.push(k); }
      sub[k].push(x);
    });
    order.forEach((k) => {
      out.push({ gid: grp.gid, top: grp.top, cat: k, rows: sub[k] });
    });
  });
  return out;
});

function onQ(e) { q.value = e.target.value; }
</script>
