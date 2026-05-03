<template>
  <div id="app" :style="appStyle">
    <div v-if="authStore.backgroundUrl" class="user-bg" :style="bgLayerStyle"></div>
    <AppNavbar v-if="authStore.isAuthenticated" />
    <main class="container app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'

const authStore = useAuthStore()

const appStyle = computed(() => ({
  position: 'relative',
  minHeight: '100vh',
}))

const bgLayerStyle = computed(() => ({
  position: 'fixed',
  inset: '0',
  backgroundImage: `url(${authStore.backgroundUrl})`,
  backgroundSize: 'cover',
  backgroundPosition: 'center',
  opacity: authStore.backgroundOpacity,
  zIndex: '-1',
  pointerEvents: 'none',
}))
</script>

<style scoped>
.app-main { padding-top: var(--spacing-lg); padding-bottom: 2rem; position: relative; }
</style>
