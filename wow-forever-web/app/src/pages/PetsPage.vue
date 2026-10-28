<template>
  <div v-if="err" class="card">
    <h2>数据没加载出来</h2>
    <p class="dim">刷新一下试试；如果一直这样，请把这一页的地址发给我们。</p>
    <button @click="boot">重试</button>
  </div>

  <template v-else-if="d">
    <div class="card">
      <div class="cdhead noart big"><h1 class="pt">宠物家族与技能</h1></div>
      <div class="field">
        <input type="search" id="q" placeholder="搜中文或英文" :value="q" @input="onQ" aria-label="搜宠物家族或技能">
        <label class="pt-new"><input type="checkbox" id="onlynew" v-model="onlyNew"> 只看《无限》新加的</label>
        <span class="dim mono" id="ptcnt">家族 {{ fams.length }} / {{ famAll.length }} · 技能 {{ sks.length }} / {{ skAll.length }}</span>
      </div>
    </div>

    <!-- 家族表：一项一行。三项修正是相对同一代宠物的偏移，0 就写 0，不留空——
         留空会被读成"这一格没数据"，而"没数据"和"不偏"是两回事。 -->
    <div class="card">
      <div class="bhead"><span class="bn">家族 {{ fams.length }} / {{ famAll.length }} 个</span></div>
      <div class="boardwrap">
        <table class="board" id="ptfam">
          <thead><tr>
            <th class="c-ico">图标</th><th class="c-name">家族</th><th class="c-name">英文原名</th>
            <th class="c-num2">伤害</th><th class="c-num2">护甲</th><th class="c-num2">生命</th>
            <th class="w-tail">会的技能</th>
          </tr></thead>
          <tbody>
            <tr v-for="x in fams" :key="x.id">
              <td class="c-ico"><IconCell :icon-key="x.iconKey || ''" :seed="x.id" :cn="x.name" /></td>
              <td><span class="nm"><HlText :text="x.name" :q="q" /></span>
                <span v-if="x.isNew" class="tag">无限新增</span></td>
              <td class="en"><HlText :text="x.nameEn" :q="q" /></td>
              <td class="c-num2 num">{{ mod(x.dmgMod) }}</td>
              <td class="c-num2 num">{{ mod(x.armorMod) }}</td>
              <td class="c-num2 num">{{ mod(x.hpMod) }}</td>
              <td class="w-tail">
                <button v-for="s in chips(x)" :key="s.id" type="button" class="pt-chip"
                        :class="{ isNew: s.isNew }" @click="pick(s.name)">{{ s.name }}</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!fams.length" class="empty">没有匹配的家族，换个词或把「只看《无限》新加的」取消。</div>
    </div>

    <!-- 技能表：那条「按家族筛」只筛这一张表，写在它的卡头里，不假装管全页。
         点上一张表的技能名会跳到这里并填进搜索框——两个入口做同一件事，不是白放的装饰。 -->
    <div class="card">
      <div class="bhead">
        <span class="bn">技能 {{ sks.length }} / {{ skAll.length }} 条</span>
        <select id="ptfamf" aria-label="按家族筛技能" v-model="fam">
          <option value="">全部家族</option>
          <option v-for="n in famOpts" :key="n" :value="n">{{ n }}</option>
        </select>
      </div>
      <div class="boardwrap">
        <table class="board" id="ptsk">
          <thead><tr>
            <th class="c-name">技能</th><th class="c-name">英文原名</th>
            <th class="c-num2">几级能学</th><th class="c-num2">最高到</th><th class="c-num2">等级数</th>
            <th class="c-num2">冷却</th><th class="c-num2">耗能</th><th class="w-tail">哪些族会用</th>
          </tr></thead>
          <tbody>
            <tr v-for="x in sks" :key="x.id">
              <td><span class="nm"><HlText :text="x.name" :q="q" /></span>
                <span v-if="x.isNew" class="tag">无限新增</span>
                <span v-if="x.renamed" class="tag">改过名</span></td>
              <td class="en"><HlText :text="x.nameEn" :q="q" /></td>
              <td class="c-num2 num">{{ num(x.learnLevel) }}</td>
              <td class="c-num2 num">{{ num(x.maxLevel) }}</td>
              <td class="c-num2 num">{{ num(x.ranks) }}</td>
              <td class="c-num2 num">{{ cd(x.cooldownSec) }}</td>
              <td class="c-num2 num">{{ num(x.cost) }}</td>
              <td class="w-tail"><template v-if="x.families && x.families.length">
                <button v-for="n in x.families" :key="n" type="button" class="pt-chip" @click="pickFam(n)">{{ n }}</button>
              </template><span v-else class="dim">这一条挂在的家族号对不上</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="!sks.length" class="empty">没有匹配的技能，换个词或放宽筛选。</div>
    </div>
  </template>
</template>

<script setup>
/* 猎人宠物 · 2026-10-28 站主拍板开这一页。
   这一页只有两层：家族 ↔ 宠物技能。它**不是**"哪只宠在哪个区域能抓"的名录——
   源数据里没有逐只的位置与驯服条件，所以标题、卡头、搜索类型都写"家族/技能"，
   不写"宠物大全"那种会让人觉得这里有坐标的话。缺的那一层在溯源页按板块说，不占这一屏。
   数值一律 L1：一家第三方插件转述客户端，本站没逐行回查、也没进游戏实测。
   插件里那些成句的技能说明文字（dcn/den）一条没取，界面上也就没有描述栏。 */
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { load } from '../lib/data.js';
import IconCell from '../components/IconCell.vue';
import HlText from '../components/HlText.vue';
import { modText, cdText, filterFamilies, filterSkills, familyOptions, skillChips } from '../lib/pets.js';

const d = ref(null);
const err = ref('');
const route = useRoute();
const q = ref(String(route.query.q || ''));
const onlyNew = ref(route.query.new === '1');
const fam = ref('');

function boot() {
  err.value = '';
  load('data/pets.json')
    .then((doc) => {
      d.value = {
        families: (doc || {}).families || [],
        skills: (doc || {}).skills || []
      };
    })
    .catch((e) => { err.value = (e && e.message) || String(e); });
}
boot();
onMounted(boot);

const famAll = computed(() => (d.value && d.value.families) || []);
const skAll = computed(() => (d.value && d.value.skills) || []);
const fams = computed(() => filterFamilies(famAll.value, { q: q.value, onlyNew: onlyNew.value }));
const sks = computed(() => filterSkills(skAll.value, { q: q.value, onlyNew: onlyNew.value, fam: fam.value }));
const famOpts = computed(() => familyOptions(famAll.value, skAll.value));

const mod = modText;
const cd = cdText;
const chips = skillChips;
function num(v) { return (v === null || v === undefined) ? '待实测' : String(v); }
function onQ(e) { q.value = e.target.value; }
/* 点技能名 → 把技能表筛到这一条；点家族名 → 用那一族筛技能。都是真筛，不是装饰。 */
function pick(name) { q.value = name; }
function pickFam(name) { fam.value = name; }
</script>

<style scoped>
.pt-new { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.pt-new input { width: 18px; height: 18px; accent-color: var(--gold); }
.pt-chip {
  display: inline-block; margin: 2px 4px 2px 0; padding: 2px 7px; font-size: 12px;
  border: 1px solid var(--line); border-radius: 10px; background: var(--panel-2);
  color: var(--txt); cursor: pointer;
}
.pt-chip.isNew { border-color: var(--gold); color: var(--gold); }
.pt-chip:hover { border-color: var(--gold); }
@media (max-width: 720px) {
  /* 技能条与家族条都是真按钮（点了会筛表），手机上得够 44px 才不算误触 */
  .pt-chip { min-height: 44px; min-width: 44px; padding: 8px 12px; }
  .pt-new { min-height: 44px; }
}
</style>
