<template>
  <div id="app" :style="appStyle">
    <template v-if="authStore.backgroundUrls.length > 0">
      <div
        v-for="(url, idx) in authStore.backgroundUrls"
        :key="url"
        class="user-bg"
        :style="bgLayerStyle(idx)"
      ></div>
    </template>
    <AppNavbar v-if="authStore.isAuthenticated" />
    <main class="container app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'

const authStore = useAuthStore()
const activeIndex = ref(0)
const loadedUrls = reactive(new Set())
let timer = null

const appStyle = computed(() => ({
  position: 'relative',
  minHeight: '100vh',
}))

function preloadImage(url) {
  if (!url || loadedUrls.has(url)) return
  const img = new Image()
  img.onload = () => {
    loadedUrls.add(url)
  }
  img.src = url
}

function bgLayerStyle(idx) {
  const url = authStore.backgroundUrls[idx]
  const isLoaded = loadedUrls.has(url)
  
  // Only attempt to show if it's the active one, or if we're preloading
  return {
    position: 'fixed',
    inset: '0',
    backgroundImage: isLoaded ? `url(${url})` : 'none',
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
  if (urls.length === 0) return
  
  // Preload current immediately
  preloadImage(urls[activeIndex.value])
  // Preload next
  if (urls.length > 1) {
    const nextIdx = (activeIndex.value + 1) % urls.length
    preloadImage(urls[nextIdx])
  }

  if (urls.length <= 1) {
    return
  }
  
  timer = setInterval(() => {
    activeIndex.value = (activeIndex.value + 1) % urls.length
    const nextIdx = (activeIndex.value + 1) % urls.length
    preloadImage(urls[nextIdx])
  }, authStore.carouselInterval * 1000)
}

function stopCarousel() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(() => authStore.carouselInterval, startCarousel)
watch(() => authStore.backgroundUrls, (newUrls, oldUrls) => {
  const oldLen = oldUrls ? oldUrls.length : 0
  const newLen = newUrls.length
  if (oldLen > 0 && newLen > oldLen) {
    activeIndex.value = newLen - 1
  } else if (activeIndex.value >= newLen) {
    activeIndex.value = Math.max(0, newLen - 1)
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
