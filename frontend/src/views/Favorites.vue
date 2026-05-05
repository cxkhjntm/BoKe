<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">&#9733; 我的收藏</h1>
      <router-link to="/documents" class="btn btn-sm">全部文档</router-link>
    </div>

    <div v-if="listError" class="alert alert-error">{{ listError }}</div>

    <FavoritesTimeline
      :groups="groups"
      :has-more="hasMore"
      :loading="loading"
      :loading-more="loadingMore"
      @open-doc="goToReader"
      @remove-favorite="handleRemoveFavorite"
      @load-more="loadMore"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDocumentTimeline, toggleFavorite } from '../api'
import FavoritesTimeline from '../components/FavoritesTimeline.vue'

const router = useRouter()

const groups = ref({})
const loading = ref(false)
const loadingMore = ref(false)
const listError = ref('')
const hasMore = ref(false)
const nextBefore = ref(null)

async function fetchTimeline(replace = true) {
  if (replace) {
    loading.value = true
  } else {
    loadingMore.value = true
  }
  listError.value = ''
  try {
    const params = { is_favorite: true, limit: 20 }
    if (!replace && nextBefore.value) {
      params.before = nextBefore.value
    }
    const res = await getDocumentTimeline(params)
    const data = res.data.data
    if (replace) {
      groups.value = data.groups
    } else {
      // Merge new groups into existing
      for (const [date, docs] of Object.entries(data.groups)) {
        if (groups.value[date]) {
          groups.value[date] = [...groups.value[date], ...docs]
        } else {
          groups.value[date] = docs
        }
      }
    }
    hasMore.value = data.has_more
    nextBefore.value = data.next_before
  } catch (e) {
    listError.value = e.response?.data?.message || '加载收藏失败'
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

function loadMore() {
  fetchTimeline(false)
}

async function handleRemoveFavorite(doc) {
  try {
    await toggleFavorite(doc.id)
    // Remove from local groups
    for (const [date, docs] of Object.entries(groups.value)) {
      groups.value[date] = docs.filter(d => d.id !== doc.id)
      if (groups.value[date].length === 0) {
        delete groups.value[date]
      }
    }
    // Force reactivity
    groups.value = { ...groups.value }
  } catch {
    // Silently ignore
  }
}

function goToReader(id) {
  router.push(`/documents/${id}`)
}

onMounted(() => fetchTimeline(true))
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}
.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text);
}
</style>
