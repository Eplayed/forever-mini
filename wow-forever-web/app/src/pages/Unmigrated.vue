<template>
  <div class="card">
    <h1 class="pt">这页还没迁到新站</h1>
    <p class="dim">新站目前只有 <b>首页</b> 与 <b>世界页</b> 两页；其余页面仍在旧站上，内容完全一样。
      迁移期间两栈并存，数据是同一份。</p>
    <p class="note">你刚才要找的是 <span class="mono">{{ want }}</span>。</p>
    <a class="cta" :href="legacy">回到旧站这一页 →</a>
    <h2>已经能在新站看的页</h2>
    <ul class="list">
      <li><router-link to="/">首页 · 数据覆盖率与入口</router-link></li>
      <li><router-link to="/world">世界 · 区域、稀有与书</router-link></li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { legacyUrl } from '../lib/nav.js';

const route = useRoute();
const want = computed(() => String(route.params.all || '未知页'));
const legacy = computed(() => legacyUrl(want.value + '.html'));
</script>
