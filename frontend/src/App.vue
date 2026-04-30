<template>
  <div id="app">
    <AppNavbar v-if="authStore.isAuthenticated" />
    <main class="container" style="padding-top: 1.5rem; padding-bottom: 2rem;">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'

const authStore = useAuthStore()
</script>
