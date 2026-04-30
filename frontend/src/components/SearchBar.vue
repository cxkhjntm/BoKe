<template>
  <div class="search-bar">
    <input
      v-model="query"
      class="input search-input"
      type="text"
      placeholder="Search documents..."
      @keyup.enter="doSearch"
    />
    <button v-if="query" class="btn btn-sm" @click="clearSearch">✕</button>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const query = ref('')

onMounted(() => {
  if (route.query.q) {
    query.value = route.query.q
  }
})

watch(() => route.query.q, (q) => {
  if (!q) query.value = ''
})

function doSearch() {
  const q = query.value.trim()
  if (q) {
    router.push({ path: '/', query: { q } })
  }
}

function clearSearch() {
  query.value = ''
  router.push('/')
}
</script>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: 0.375rem;
}
.search-input {
  width: 200px;
  font-size: 0.8125rem;
  padding: 0.375rem 0.625rem;
}
@media (max-width: 640px) {
  .search-input { width: 140px; }
}
</style>
