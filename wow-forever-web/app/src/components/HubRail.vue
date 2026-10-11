<template>
  <!-- 板块入口图标轨：与旧站 home() 里同一份 tiles 定义，一格一张本地原画，
       取不到图的退回字母块（不热链第三方图）。 -->
  <div class="hrail" aria-label="板块入口">
    <template v-for="t in tiles" :key="t.label">
      <router-link v-if="t.link" class="hrt" :to="t.link" :title="t.label">
        <span class="hrt-b">
          <img v-if="t.src" :src="t.src" alt="" loading="lazy">
          <i v-else class="hrt-x">{{ t.letter }}</i>
          <em v-if="isNew(t.label)" class="hrt-n">新</em>
        </span>
        <span class="hrt-l">{{ t.label }}</span>
      </router-link>
      <a v-else class="hrt" :href="t.href" :title="t.label">
        <span class="hrt-b">
          <img v-if="t.src" :src="t.src" alt="" loading="lazy">
          <i v-else class="hrt-x">{{ t.letter }}</i>
          <em v-if="isNew(t.label)" class="hrt-n">新</em>
        </span>
        <span class="hrt-l">{{ t.label }}</span>
      </a>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { linkFor } from '../lib/nav.js';

const props = defineProps({
  art: { type: Object, default: () => ({}) },   // art.json 里的 classes / races / dungeons 三张表
  navNew: { type: Array, default: () => [] }    // scale.navNew：最新一批更新的板块标签
});

/* 与旧站 src/js/app.js 里 home() 的 tiles 一一对应：改一处必须改两处，
   app-parity.py 会数 #main 里的 img 与类名，对不上就红。 */
const SPEC = [
  ['天赋计算器', 'talent.html', 'classes', 'druid', 'D'],
  ['玩法问答', 'chooser.html', 'classes', 'paladin', 'P'],
  ['技能书', 'skills.html', 'classes', 'mage', 'M'],
  ['传承', 'legacy.html', 'races', 'skyborne', 'L'],
  ['种族', 'races.html', 'races', 'human', 'H'],
  ['世界', 'world.html', 'dungeons', 'city-of-dalaran', 'W'],
  ['副本', 'dungeons.html', 'dungeons', 'blackrock-depths', 'D'],
  ['团本', 'raids.html', 'dungeons', 'blackmaw-hold', 'R'],
  ['专业', 'professions.html', 'icons', '10prof_table_tailoring01', 'C']
];

const tiles = computed(() => SPEC.map((s) => {
  const src = s[2] === 'icons' ? 'img/icons/' + s[3] + '.jpg' : ((props.art[s[2]] || {})[s[3]] || null);
  const l = linkFor(s[1]);
  return { label: s[0], href: s[1], link: l && l.to ? l.to : null, src: src, letter: s[4] };
}));

function isNew(label) { return props.navNew.indexOf(label) >= 0; }
</script>
