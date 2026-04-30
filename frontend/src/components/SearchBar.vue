<template>
  <div class="search-bar" :class="{ 'search-bar-focused': focused }">
    <input
      ref="searchInput"
      v-model="query"
      class="input search-input"
      type="text"
      placeholder="Search documents... (press /)"
      @focus="focused = true"
      @blur="focused = false"
      @keyup.enter="doSearch"
    />
    <button v-if="query" class="btn btn-sm search-clear" @click="clearSearch">&times;</button>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const query = ref('')
const focused = ref(false)
const searchInput = ref(null)
let debounceTimer = null

onMounted(() => {
  if (route.query.q) {
    query.value = route.query.q
  }
  document.addEventListener('keydown', handleGlobalKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleGlobalKey)
  if (debounceTimer) clearTimeout(debounceTimer)
})

watch(() => route.query.q, (q) => {
  if (!q) query.value = ''
})

function handleGlobalKey(e) {
  if (e.key === '/' && !isInputFocused()) {
    e.preventDefault()
    searchInput.value?.focus()
  }
}

function isInputFocused() {
  const tag = document.activeElement?.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'
}

function doSearch() {
  const q = query.value.trim()
  if (q) {
    router.push({ path: '/', query: { q } })
  }
}

function clearSearch() {
  query.value = ''
  router.push('/')
  searchInput.value?.focus()
}
</script>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  transition: all var(--transition-fast);
}
.search-input {
  width: 180px;
  font-size: 0.8125rem;
  padding: 0.375rem 0.625rem;
  transition: width var(--transition-normal);
}
.search-bar-focused .search-input {
  width: 280px;
}
.search-clear {
  padding: 0.25rem 0.5rem;
  font-size: 1rem;
  line-height: 1;
}

@media (max-width: 640px) {
  .search-input { width: 140px; }
  .search-bar-focused .search-input { width: 200px; }
}
</style>
