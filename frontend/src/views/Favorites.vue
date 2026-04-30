<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">&#9733; 我的收藏</h1>
      <router-link to="/documents" class="btn btn-sm">全部文档</router-link>
    </div>

    <div v-if="listError" class="alert alert-error">{{ listError }}</div>

    <!-- Skeleton loading -->
    <div v-if="loading" class="skeleton-list">
      <div v-for="i in 3" :key="i" class="card skeleton-card">
        <div class="skeleton-thumb"></div>
        <div class="skeleton-lines">
          <div class="skeleton-line skeleton-line-title"></div>
          <div class="skeleton-line skeleton-line-meta"></div>
        </div>
      </div>
    </div>

    <div v-else-if="documents.length === 0" class="empty">
      <div class="empty-icon">&#9734;</div>
      <p>暂无收藏，给文档添加星标即可在此查看！</p>
    </div>
    <div v-else class="doc-list">
      <div
        v-for="(doc, idx) in documents"
        :key="doc.id"
        class="card doc-card"
        :style="{ animationDelay: idx * 80 + 'ms' }"
      >
        <div class="doc-card-visual" @click="goToReader(doc.id)">
          <img
            v-if="doc.status === 'ready' && doc.thumbnail_path"
            :src="thumbUrl(doc.id)"
            :alt="doc.title"
            class="doc-thumb-img"
            loading="lazy"
            @error="$event.target.style.display='none'"
          />
          <span v-else class="file-type-icon" :class="'ft-' + doc.file_type">
            {{ doc.file_type.toUpperCase() }}
          </span>
        </div>
        <div class="doc-card-info" @click="goToReader(doc.id)">
          <div class="doc-title">{{ doc.title }}</div>
          <div class="doc-meta">
            <span class="badge" :class="'badge-' + doc.status">{{ statusLabel(doc.status) }}</span>
            <span class="doc-type">{{ doc.file_type.toUpperCase() }}</span>
            <span>{{ formatSize(doc.file_size) }}</span>
            <span>{{ formatDate(doc.created_at) }}</span>
          </div>
        </div>
        <div class="doc-card-actions">
          <button
            class="btn-icon fav-btn fav-active"
            @click.stop="handleRemoveFavorite(doc)"
            title="取消收藏"
          >
            &#9733;
          </button>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="total > limit" class="pagination">
      <button class="btn btn-sm" :disabled="page <= 1" @click="page--; fetchDocs()">上一页</button>
      <span class="page-info">第 {{ page }} 页，共 {{ Math.ceil(total / limit) }} 页</span>
      <button class="btn btn-sm" :disabled="page * limit >= total" @click="page++; fetchDocs()">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getDocuments, toggleFavorite } from '../api'
import { formatDate, formatSize, statusLabel } from '../utils/format'

const router = useRouter()

const documents = ref([])
const loading = ref(false)
const listError = ref('')
const page = ref(1)
const limit = 20
const total = ref(0)

const authToken = computed(() => localStorage.getItem('access_token') || '')

function thumbUrl(docId) {
  return `/api/v1/files/${docId}/thumbnail?token=${encodeURIComponent(authToken.value)}`
}

async function fetchDocs() {
  loading.value = true
  listError.value = ''
  try {
    const res = await getDocuments({
      page: page.value,
      limit,
      sort_by: 'created_at',
      sort_order: 'desc',
      is_favorite: true,
    })
    documents.value = res.data.data.items
    total.value = res.data.data.total
  } catch (e) {
    listError.value = e.response?.data?.message || '加载收藏失败'
  } finally {
    loading.value = false
  }
}

async function handleRemoveFavorite(doc) {
  try {
    await toggleFavorite(doc.id)
    // Remove from list since it's no longer a favorite
    documents.value = documents.value.filter(d => d.id !== doc.id)
    total.value--
  } catch {
    // Silently ignore
  }
}

function goToReader(id) {
  router.push(`/documents/${id}`)
}

onMounted(fetchDocs)
</script>

<style scoped>
@keyframes cardIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.doc-list { display: flex; flex-direction: column; gap: 0.625rem; }

.doc-card {
  display: flex;
  align-items: stretch;
  cursor: pointer;
  animation: cardIn var(--transition-normal) both;
}

.doc-card-visual {
  flex-shrink: 0;
  width: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid rgba(0, 0, 0, 0.06);
  background: linear-gradient(135deg, rgba(241, 245, 249, 0.6), rgba(226, 232, 240, 0.3));
  border-radius: var(--radius) 0 0 var(--radius);
  overflow: hidden;
  cursor: pointer;
  position: relative;
}
.doc-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-glass);
}
.doc-card:hover .doc-thumb-img {
  transform: scale(1.08);
}

.file-type-icon {
  font-family: var(--font-mono);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  background: var(--border);
  color: var(--text-secondary);
}
.ft-pdf { background: #fee2e2; color: #991b1b; }
.ft-docx { background: #dbeafe; color: #1e40af; }
.ft-md { background: #dcfce7; color: #166534; }
.ft-png, .ft-jpg, .ft-jpeg { background: #fef9c3; color: #854d0e; }

.doc-card-info {
  flex: 1;
  padding: 0.75rem 1rem;
  min-width: 0;
  cursor: pointer;
}
.doc-title { font-weight: 600; font-size: 0.9375rem; margin-bottom: 0.25rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-meta { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: var(--text-secondary); flex-wrap: wrap; }
.doc-type { font-family: var(--font-mono); font-size: 0.75rem; }

.doc-card-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0 0.75rem;
  border-left: 1px solid var(--border);
}

.fav-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0.25rem;
  line-height: 1;
  transition: color var(--transition-fast), transform var(--transition-fast);
}
.fav-btn:hover { transform: scale(1.2); }
.fav-active { color: #f59e0b; }

.skeleton-list { display: flex; flex-direction: column; gap: 0.625rem; }
.skeleton-card {
  display: flex;
  align-items: center;
  padding: 0.875rem 1rem;
  gap: 0.75rem;
}
.skeleton-thumb {
  width: 64px;
  height: 48px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  flex-shrink: 0;
}
.skeleton-lines { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }
.skeleton-line {
  height: 0.875rem;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton-line-title { width: 60%; }
.skeleton-line-meta { width: 40%; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}
.page-info { font-size: 0.8125rem; color: var(--text-secondary); }

@media (max-width: 640px) {
  .doc-card-visual { width: 48px; }
  .doc-card-info { padding: 0.625rem 0.75rem; }
  .doc-card-actions { flex-direction: column; padding: 0.5rem; border-left: none; border-top: 1px solid var(--border); }
}
</style>
