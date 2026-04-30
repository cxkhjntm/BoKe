<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">Dashboard</h1>
      <router-link to="/documents" class="btn btn-sm">All Documents</router-link>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <!-- Stats cards -->
    <div class="stats-grid">
      <StatsCard icon="&#128196;" :value="stats.total_docs" label="Total Documents" />
      <StatsCard icon="&#128451;" :value="stats.total_size" label="Total Size" format="size" />
      <StatsCard icon="&#128196;" :value="stats.by_type?.pdf || 0" label="PDFs" />
      <StatsCard icon="&#128196;" :value="stats.by_type?.docx || 0" label="DOCX" />
    </div>

    <!-- Main grid: recent + top docs -->
    <div class="dashboard-grid">
      <RecentDocs
        title="Recently Viewed"
        :docs="recentDocs"
        :loading="loading"
        empty-text="No documents viewed yet"
        @navigate="goToReader"
      />
      <RecentDocs
        title="Most Viewed"
        :docs="topDocs"
        :loading="loading"
        empty-text="No view data yet"
        @navigate="goToReader"
      />
    </div>

    <!-- Activity timeline -->
    <ActivityTimeline :activities="activities" :loading="loading" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getDashboardStats, getDashboardRecent, getDashboardTop, getDashboardActivity } from '../api'
import StatsCard from '../components/StatsCard.vue'
import RecentDocs from '../components/RecentDocs.vue'
import ActivityTimeline from '../components/ActivityTimeline.vue'

const router = useRouter()

const stats = reactive({ total_docs: 0, total_size: 0, by_type: {}, by_status: {} })
const recentDocs = ref([])
const topDocs = ref([])
const activities = ref([])
const loading = ref(false)
const error = ref('')

async function fetchDashboard() {
  loading.value = true
  error.value = ''
  try {
    const [statsRes, recentRes, topRes, actRes] = await Promise.all([
      getDashboardStats(),
      getDashboardRecent({ limit: 10 }),
      getDashboardTop({ limit: 10 }),
      getDashboardActivity({ limit: 20 }),
    ])
    Object.assign(stats, statsRes.data.data)
    recentDocs.value = recentRes.data.data
    topDocs.value = topRes.data.data
    activities.value = actRes.data.data
  } catch (e) {
    error.value = e.response?.data?.message || 'Failed to load dashboard'
  } finally {
    loading.value = false
  }
}

function goToReader(id) {
  router.push(`/documents/${id}`)
}

onMounted(fetchDashboard)
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}
@media (max-width: 768px) {
  .dashboard-grid { grid-template-columns: 1fr; }
}
</style>
