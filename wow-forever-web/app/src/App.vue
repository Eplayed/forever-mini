<template>
  <AppShell>
    <router-view v-slot="{ Component }">
      <component :is="Component" :key="$route.path" />
    </router-view>
  </AppShell>
</template>

<script setup>
import AppShell from './components/AppShell.vue';
</script>
