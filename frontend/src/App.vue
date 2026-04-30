<template>
  <div id="app">
    <AppNavbar v-if="authStore.isAuthenticated" />
    <main class="container app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'

const authStore = useAuthStore()
</script>

<style scoped>
.app-main { padding-top: var(--spacing-lg); padding-bottom: 2rem; }
</style>
