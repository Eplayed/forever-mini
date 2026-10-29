<template>
  <AppShell>
    <!-- 换页动效（2026-10-29）。mode="out-in" 是硬要求：新旧页不重叠，
         天赋页/配装页那种挂着 3D 预览与几百行表的页面不会被同时挂两份，
         门禁的逐页断言也不会在一页里数到两套同名元素。
         外面这层 div 是给 <Transition> 的一个真元素根：多数页的根节点是 fragment
         （v-if 错误卡 + template v-else 里好几块），过渡找不到单一元素根就不动，
         Vue 只会留一句警告、画面什么都没有。规格见 docs/PLAN-网页交互动效-2026-10-29.md。 -->
    <router-view v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <div class="view" :key="$route.path"><component :is="Component" /></div>
      </Transition>
    </router-view>
  </AppShell>
</template>

<script setup>
import AppShell from './components/AppShell.vue';
</script>
