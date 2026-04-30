<template>
  <div>
    <!-- Search results mode -->
    <template v-if="isSearch">
      <div class="page-header">
        <h1 class="page-title">Search: "{{ searchQuery }}"</h1>
        <router-link to="/" class="btn btn-sm">Back to documents</router-link>
      </div>
      <div v-if="searchLoading" class="empty"><span class="spinner"></span></div>
      <div v-else-if="searchError" class="alert alert-error">{{ searchError }}</div>
      <div v-else-if="searchResults.length === 0" class="empty">
        <div class="empty-icon">🔍</div>
        <p>No results found</p>
      </div>
      <div v-else class="doc-list">
        <div v-for="item in searchResults" :key="item.id" class="card doc-card" @click="goToReader(item.id)">
          <div class="doc-card-body">
            <div class="doc-title">{{ item.title }}</div>
            <div class="doc-meta">
              <span class="badge" :class="'badge-' + item.status">{{ statusLabel(item.status) }}</span>
              <span class="doc-type">{{ item.file_type.toUpperCase() }}</span>
              <span>{{ formatDate(item.created_at) }}</span>
            </div>
            <div v-if="item.snippet" class="doc-snippet">{{ item.snippet }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- Normal document list mode -->
    <template v-else>
      <div class="page-header">
        <h1 class="page-title">Documents</h1>
        <div style="display:flex; gap:0.5rem; align-items:center;">
          <label class="btn btn-primary btn-sm" :class="{ disabled: uploading }">
            <span v-if="uploading" class="spinner"></span>
            {{ uploading ? `${uploadProgress}%` : 'Upload' }}
            <input
              ref="fileInput"
              type="file"
              accept=".pdf,.docx,.md,.png,.jpg,.jpeg"
              hidden
              :disabled="uploading"
              @change="handleUpload"
            />
          </label>
        </div>
      </div>

      <div v-if="uploadError" class="alert alert-error">{{ uploadError }}</div>
      <div v-if="uploadSuccess" class="alert alert-success">Document uploaded successfully!</div>
      <div v-if="listError" class="alert alert-error">{{ listError }}</div>

      <!-- Filters -->
      <div class="filters">
        <select v-model="filters.status" class="input filter-select" @change="onFilterChange">
          <option value="">All Status</option>
          <option value="ready">Ready</option>
          <option value="processing">Processing</option>
          <option value="error">Error</option>
        </select>
        <select v-model="filters.file_type" class="input filter-select" @change="onFilterChange">
          <option value="">All Types</option>
          <option value="pdf">PDF</option>
          <option value="docx">DOCX</option>
          <option value="md">Markdown</option>
          <option value="png">PNG</option>
          <option value="jpg">JPG</option>
        </select>
      </div>

      <div v-if="loading" class="empty"><span class="spinner"></span></div>
      <div v-else-if="documents.length === 0" class="empty">
        <div class="empty-icon">📄</div>
        <p>No documents yet. Upload your first document!</p>
      </div>
      <div v-else class="doc-list">
        <div v-for="doc in documents" :key="doc.id" class="card doc-card">
          <div class="doc-card-body" @click="goToReader(doc.id)">
            <div class="doc-card-thumb" v-if="doc.status === 'ready' && doc.thumbnail_path">
              <img
                :src="thumbUrl(doc.id)"
                :alt="doc.title"
                loading="lazy"
                @error="$event.target.style.display='none'"
              />
            </div>
            <div class="doc-card-info">
              <div class="doc-title">{{ doc.title }}</div>
              <div class="doc-meta">
                <span class="badge" :class="'badge-' + doc.status">{{ statusLabel(doc.status) }}</span>
                <span class="doc-type">{{ doc.file_type.toUpperCase() }}</span>
                <span>{{ formatSize(doc.file_size) }}</span>
                <span>{{ formatDate(doc.created_at) }}</span>
              </div>
              <div v-if="doc.status === 'error' && doc.error_message" class="doc-error">
                {{ doc.error_message }}
              </div>
            </div>
          </div>
          <div class="doc-card-actions">
            <button
              v-if="doc.status === 'error'"
              class="btn btn-sm"
              @click.stop="handleRetry(doc.id)"
              :disabled="retryingId === doc.id"
            >
              {{ retryingId === doc.id ? 'Retrying...' : 'Retry' }}
            </button>
            <button
              class="btn btn-sm btn-danger"
              @click.stop="handleDelete(doc.id, doc.title)"
              :disabled="deletingId === doc.id"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="total > limit" class="pagination">
        <button class="btn btn-sm" :disabled="page <= 1" @click="page--; fetchDocs()">Prev</button>
        <span class="page-info">Page {{ page }} of {{ Math.ceil(total / limit) }}</span>
        <button class="btn btn-sm" :disabled="page * limit >= total" @click="page++; fetchDocs()">Next</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDocuments, uploadDocument, deleteDocument, retryDocument, searchDocuments } from '../api'

const route = useRoute()
const router = useRouter()

const documents = ref([])
const loading = ref(false)
const listError = ref('')
const page = ref(1)
const limit = 20
const total = ref(0)
const filters = reactive({ status: '', file_type: '' })

const uploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref('')
const uploadSuccess = ref(false)
const fileInput = ref(null)
const deletingId = ref(null)
const retryingId = ref(null)

// Search state
const searchQuery = computed(() => route.query.q || '')
const isSearch = computed(() => !!route.query.q)
const searchResults = ref([])
const searchLoading = ref(false)
const searchError = ref('')

// Auth token for img src
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
      ...(filters.status && { status: filters.status }),
      ...(filters.file_type && { file_type: filters.file_type }),
    })
    documents.value = res.data.data.items
    total.value = res.data.data.total
  } catch (e) {
    listError.value = e.response?.data?.message || 'Failed to load documents'
  } finally {
    loading.value = false
  }
}

async function doSearch(q) {
  if (!q) return
  searchLoading.value = true
  searchError.value = ''
  try {
    const res = await searchDocuments({ q, page: 1, limit: 50 })
    searchResults.value = res.data.data.items
  } catch (e) {
    searchError.value = e.response?.data?.message || 'Search failed'
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

function onFilterChange() {
  page.value = 1
  fetchDocs()
}

async function handleUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploading.value = true
  uploadError.value = ''
  uploadSuccess.value = false
  try {
    const fd = new FormData()
    fd.append('file', file)
    await uploadDocument(fd, (ev) => {
      if (ev.total) uploadProgress.value = Math.round((ev.loaded / ev.total) * 100)
    })
    uploadSuccess.value = true
    setTimeout(() => { uploadSuccess.value = false }, 3000)
    fetchDocs()
  } catch (err) {
    uploadError.value = err.response?.data?.message || 'Upload failed'
  } finally {
    uploading.value = false
    setTimeout(() => { uploadProgress.value = 0 }, 500)
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function handleDelete(id, title) {
  if (!confirm(`Delete "${title}"?`)) return
  deletingId.value = id
  try {
    await deleteDocument(id)
    fetchDocs()
  } catch (e) {
    listError.value = e.response?.data?.message || 'Delete failed'
  } finally {
    deletingId.value = null
  }
}

async function handleRetry(id) {
  retryingId.value = id
  try {
    await retryDocument(id)
    fetchDocs()
  } catch (e) {
    listError.value = e.response?.data?.message || 'Retry failed'
  } finally {
    retryingId.value = null
  }
}

function goToReader(id) {
  router.push(`/documents/${id}`)
}

function formatDate(d) {
  if (!d) return ''
  return new Date(d).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function statusLabel(s) {
  return { ready: 'Ready', processing: 'Processing', error: 'Error' }[s] || s
}

// Watch search query — handle both present and absent
watch(() => route.query.q, (q) => {
  if (q) {
    doSearch(q)
  } else if (route.path === '/') {
    // Switched back to normal list mode
    page.value = 1
    fetchDocs()
  }
})

onMounted(() => {
  if (isSearch.value) {
    doSearch(searchQuery.value)
  } else {
    fetchDocs()
  }
})
</script>

<style scoped>
.doc-list { display: flex; flex-direction: column; gap: 0.625rem; }
.doc-card { display: flex; align-items: stretch; cursor: pointer; transition: box-shadow 0.15s; }
.doc-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.doc-card-body {
  flex: 1;
  display: flex;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  min-width: 0;
}
.doc-card-thumb {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg);
}
.doc-card-thumb img { width: 100%; height: 100%; object-fit: cover; }
.doc-card-info { flex: 1; min-width: 0; }
.doc-title { font-weight: 600; font-size: 0.9375rem; margin-bottom: 0.25rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-meta { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: var(--text-secondary); flex-wrap: wrap; }
.doc-type { font-family: var(--font-mono); font-size: 0.75rem; }
.doc-error { font-size: 0.8125rem; color: var(--danger); margin-top: 0.25rem; }
.doc-snippet { font-size: 0.8125rem; color: var(--text-secondary); margin-top: 0.375rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-card-actions {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0 0.75rem;
  border-left: 1px solid var(--border);
}
.filters {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.filter-select { width: auto; min-width: 120px; font-size: 0.8125rem; padding: 0.375rem 0.625rem; }
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}
.page-info { font-size: 0.8125rem; color: var(--text-secondary); }
.disabled { opacity: 0.5; pointer-events: none; }

@media (max-width: 640px) {
  .doc-card-body { padding: 0.625rem 0.75rem; }
  .doc-card-thumb { display: none; }
  .doc-card-actions { flex-direction: column; padding: 0.5rem; border-left: none; border-top: 1px solid var(--border); }
  .filters { flex-direction: column; }
  .filter-select { width: 100%; }
}
</style>
