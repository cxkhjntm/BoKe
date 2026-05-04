<template>
  <div id="app" :style="appStyle">
    <template v-if="authStore.backgroundUrls.length > 0">
      <div
        v-for="(url, idx) in authStore.backgroundUrls"
        :key="idx"
        class="user-bg"
        :style="bgLayerStyle(idx)"
      ></div>
    </template>
    <AppNavbar v-if="authStore.isAuthenticated" />
    <main class="container app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'

const authStore = useAuthStore()
const activeIndex = ref(0)
let timer = null

const appStyle = computed(() => ({
  position: 'relative',
  minHeight: '100vh',
}))

function bgLayerStyle(idx) {
  return {
    position: 'fixed',
    inset: '0',
    backgroundImage: `url(${authStore.backgroundUrls[idx]})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    opacity: idx === activeIndex.value ? authStore.backgroundOpacity : 0,
    zIndex: '-1',
    pointerEvents: 'none',
  }
}

function startCarousel() {
  stopCarousel()
  const urls = authStore.backgroundUrls
  if (urls.length <= 1) {
    activeIndex.value = 0
    return
  }
  timer = setInterval(() => {
    activeIndex.value = (activeIndex.value + 1) % authStore.backgroundUrls.length
  }, authStore.carouselInterval * 1000)
}

function stopCarousel() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(() => authStore.carouselInterval, startCarousel)
watch(() => authStore.backgroundUrls, () => {
  if (activeIndex.value >= authStore.backgroundUrls.length) {
    activeIndex.value = 0
  }
  startCarousel()
})
onMounted(startCarousel)
onUnmounted(stopCarousel)
</script>

<style scoped>
.user-bg {
  transition: opacity 1s ease-in-out;
}
.app-main { padding-top: var(--spacing-lg); padding-bottom: 2rem; position: relative; }
</style>
