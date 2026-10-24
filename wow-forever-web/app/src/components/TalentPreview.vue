<template>
  <!-- 整卡当入口（2026-10-13 用户：「最常用的两个」那行标题不要了，卡片本身点进计算器）。
       背景是"当前这一系"的专精原画（320×384），不是 128 的职业图标放大。 -->
  <section class="card hasart go" id="treecard" tabindex="0" :data-go="legacy(calcFile(cid, ti))"
           @click="goCard" @keydown="goKey">
    <span class="bgart" aria-hidden="true" :style="bgStyle"></span>
    <div class="mline">工具 · 天赋 · <b>{{ S.classes || 0 }}</b> 职业 <b>{{ S.talentNodes || 0 }}</b> 节点</div>
    <h2>先看一棵真树，再进计算器</h2>
    <div class="pvpicks">
      <button v-for="(tr, i) in trees" :key="tr.n" type="button" class="pick" :class="{ on: i === ti }"
              :aria-pressed="i === ti ? 'true' : 'false'" @click="ti = i">
        <b>{{ tr.n }}</b><span class="dim mono">{{ tr.nodes.length }}</span>
      </button>
    </div>
    <div class="treewrap">
      <div class="treeleft">
        <div class="pv">
          <template v-for="(nd, i) in cells" :key="i">
            <component v-if="nd" :is="linkFor(nodeFile(cid, ti, nd[2])).to ? 'router-link' : 'a'"
                       v-bind="linkFor(nodeFile(cid, ti, nd[2]))"
                       class="pnode" :class="nd[5] ? 'chg-' + nd[5] : ''"
                       :title="nodeLabel(nd)" :aria-label="nodeLabel(nd)">
              <span class="ico-wrap">
                <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">
                  <rect width="28" height="28" rx="4" :fill="ph(nd).fill" :stroke="ph(nd).stroke" />
                  <text x="14" y="19" text-anchor="middle" font-size="12" :fill="ph(nd).text"
                        font-family="PingFang SC,Microsoft YaHei,sans-serif">{{ ph(nd).letter }}</text>
                </svg>
                <img v-if="nd[3] && !gone[keyOf(nd)]" class="ico" :src="iconUrl(nd[3])" alt=""
                     loading="lazy" @error="hide(nd)">
              </span>
            </component>
            <span v-else class="pempty"></span>
          </template>
        </div>
        <div class="pvmeta">
          <span v-for="s in states" :key="s.k">
            <i class="dot" :class="s.k !== 'none' ? 'chg-' + s.k : ''"></i>{{ s.label }} <b class="mono">{{ s.n }}</b>
          </span>
        </div>
      </div>
      <aside class="tright">
        <div class="strip">
          <button v-for="c in classes" :key="c.id" type="button" class="stripc" :class="{ on: c.id === cid }"
                  :aria-pressed="c.id === cid ? 'true' : 'false'" @click="pick(c.id)">
            <ClassTile :class-id="c.id" :cn="c.cn" :icon-key="c.iconKey || ''" />
            <b>{{ c.cn }}</b><span class="dim mono">{{ c.talentCount || 0 }} 天赋</span>
          </button>
        </div>
        <component :is="linkFor(calcFile(cid, ti)).to ? 'router-link' : 'a'" v-bind="linkFor(calcFile(cid, ti))" class="cta">
          打开{{ cnOf }} · {{ (trees[ti] || {}).n || '' }} 的完整计算器（能加点、能存方案）→
        </component>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';
import { linkFor, hrefOf } from '../lib/nav.js';
import { tileStyle, iconUrl } from '../lib/glyph.js';
import { gridCells, countStates, nodeLabel, nodeFile, calcFile, treeOf } from '../lib/preview.js';
import { specArt } from '../lib/art.js';

const legacy = hrefOf;
/* 点在卡里的链接、按钮、格子、职业条上时让给它们自己，只有点在空白处才按 data-go 跳
   （与旧站 bindGo 同一套判断）。data-go 用旧站那套 .html 地址，linkFor 认得它就换站内路由。 */
function goCard(e) {
  if (e.target && e.target.closest && e.target.closest('a, button, .stripc, .pnode, .pick')) return;
  const to = linkFor(String(e.currentTarget.getAttribute('data-go') || '').split('?')[0]);
  if (to.to) { window.location.hash = to.to + ('?' + String(e.currentTarget.getAttribute('data-go')).split('?')[1] || ''); return; }
  window.location.href = e.currentTarget.getAttribute('data-go');
}
function goKey(e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); goCard(e); } }
import ClassTile from './ClassTile.vue';

const props = defineProps({
  preview: { type: Object, default: () => ({ classes: {} }) },
  classes: { type: Array, default: () => [] },
  scale: { type: Object, default: () => ({}) },
  art: { type: Object, default: () => ({}) }
});

const cid = ref(props.classes.length ? props.classes[0].id : 'hunter');
const ti = ref(0);
const gone = ref({});
const S = computed(() => props.scale || {});

const trees = computed(() => (((props.preview.classes || {})[cid.value] || {}).trees) || []);
const cells = computed(() => gridCells(treeOf(props.preview, cid.value, ti.value)));
const states = computed(() => countStates(treeOf(props.preview, cid.value, ti.value)));
const cnOf = computed(() => {
  const c = props.classes.filter((x) => x.id === cid.value)[0];
  return c ? c.cn : cid.value;
});
// 卡片背景随选中的职业换：素材只用已转存的本地原画，没有就不加背景层
// 背景用"当前这一系"的专精原画；那一系没图就退回该职业第一系，再没有就留纯色
const bgStyle = computed(() => {
  const f = specArt(props.art, cid.value, ti.value);
  return f ? { backgroundImage: 'url(' + f + ')' } : {};
});
// 2026-10-12 站主决定：卡尾那条"名称与官网中文一致 462 / 466"的读数与进度条撤下，
// 覆盖率只在溯源页给一处，所以这里不再算 share。

function pick(id) { cid.value = id; ti.value = 0; }
function keyOf(nd) { return cid.value + '-' + ti.value + '-' + nd[0] + '-' + nd[1]; }
function ph(nd) { return tileStyle(keyOf(nd), nd[2]); }
// 图取不到就不占位：旧站是 onerror 改类名，这里等价但不产生失败请求
function hide(nd) { gone.value[keyOf(nd)] = true; }
</script>
