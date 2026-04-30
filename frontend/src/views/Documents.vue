<template>
  <div>
    <!-- Search results mode -->
    <template v-if="isSearch">
      <div class="page-header">
        <h1 class="page-title">Search: "{{ searchQuery }}"</h1>
        <router-link to="/" class="btn btn-sm">Back to documents</router-link>
      </div>
      <div v-if="searchLoading" class="skeleton-list">
        <div v-for="i in 3" :key="i" class="card skeleton-card">
          <div class="skeleton-thumb"></div>
          <div class="skeleton-lines">
            <div class="skeleton-line skeleton-line-title"></div>
            <div class="skeleton-line skeleton-line-meta"></div>
          </div>
        </div>
      </div>
      <div v-else-if="searchError" class="alert alert-error">{{ searchError }}</div>
      <div v-else-if="searchResults.length === 0" class="empty">
        <div class="empty-icon">&#128269;</div>
        <p>No results found</p>
      </div>
      <div v-else class="doc-list">
        <div
          v-for="(item, idx) in searchResults"
          :key="item.id"
          class="card doc-card"
          :style="{ animationDelay: idx * 80 + 'ms' }"
          @click="goToReader(item.id)"
        >
          <div class="doc-card-visual">
            <span class="file-type-icon" :class="'ft-' + item.file_type">
              {{ item.file_type.toUpperCase() }}
            </span>
          </div>
          <div class="doc-card-info">
            <div class="doc-title">{{ item.title }}</div>
            <div class="doc-meta">
              <span class="badge" :class="'badge-' + item.status">{{ statusLabel(item.status) }}</span>
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

      <!-- Drag-drop zone -->
      <div
        class="drop-zone"
        :class="{ 'drop-zone-active': dragging }"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
      >
        <div class="drop-zone-content">
          <span class="drop-zone-icon">&#128220;</span>
          <span>Drag & drop files here, or click Upload</span>
        </div>
      </div>

      <div v-if="uploadError" class="alert alert-error">{{ uploadError }}</div>
      <div v-if="uploadSuccess" class="alert alert-success">Document uploaded successfully!</div>
      <div v-if="listError" class="alert alert-error">{{ listError }}</div>

      <!-- Filter bar with clearable tags -->
      <div class="filter-bar">
        <select v-model="filters.status" class="input filter-select" @change="onFilterChange">
          <option value="">All Status</option>
          <option value="queued">Queued</option>
          <option value="processing">Processing</option>
          <option value="ready">Ready</option>
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
        <label class="filter-fav-toggle">
          <input type="checkbox" v-model="filters.favoritesOnly" @change="onFilterChange" />
          <span class="fav-toggle-label">&#9733; Favorites</span>
        </label>
        <div v-if="hasActiveFilters" class="filter-tags">
          <span v-if="filters.status" class="filter-tag" @click="clearFilter('status')">
            {{ statusLabel(filters.status) }} &times;
          </span>
          <span v-if="filters.file_type" class="filter-tag" @click="clearFilter('file_type')">
            {{ filters.file_type.toUpperCase() }} &times;
          </span>
          <span v-if="filters.favoritesOnly" class="filter-tag" @click="clearFilter('favoritesOnly')">
            &#9733; Favorites &times;
          </span>
        </div>
      </div>

      <!-- Skeleton loading -->
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 5" :key="i" class="card skeleton-card">
          <div class="skeleton-thumb"></div>
          <div class="skeleton-lines">
            <div class="skeleton-line skeleton-line-title"></div>
            <div class="skeleton-line skeleton-line-meta"></div>
          </div>
        </div>
      </div>

      <div v-else-if="documents.length === 0" class="empty">
        <div class="empty-icon">&#128196;</div>
        <p>No documents yet. Upload your first document!</p>
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
            <div v-if="doc.status === 'error' && doc.error_message" class="doc-error">
              {{ doc.error_message }}
            </div>
          </div>
          <div class="doc-card-actions">
            <button
              class="btn-icon fav-btn"
              :class="{ 'fav-active': doc.is_favorite }"
              @click.stop="handleToggleFavorite(doc)"
              :title="doc.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
            >
              {{ doc.is_favorite ? '&#9733;' : '&#9734;' }}
            </button>
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
import { ref, reactive, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDocuments, uploadDocument, deleteDocument, retryDocument, searchDocuments, toggleFavorite } from '../api'
import { formatDate, formatSize, statusLabel } from '../utils/format'

const route = useRoute()
const router = useRouter()

const documents = ref([])
const loading = ref(false)
const listError = ref('')
const page = ref(1)
const limit = 20
const total = ref(0)
const filters = reactive({ status: '', file_type: '', favoritesOnly: false })
const dragging = ref(false)
let dragCounter = 0

const uploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref('')
const uploadSuccess = ref(false)
const fileInput = ref(null)
const deletingId = ref(null)
const retryingId = ref(null)

const searchQuery = computed(() => route.query.q || '')
const isSearch = computed(() => !!route.query.q)
const searchResults = ref([])
const searchLoading = ref(false)
const searchError = ref('')

const authToken = computed(() => localStorage.getItem('access_token') || '')
const hasActiveFilters = computed(() => filters.status || filters.file_type || filters.favoritesOnly)

// Status polling
let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => fetchDocs(true), 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function shouldPoll() {
  return documents.value.some(d => d.status === 'queued' || d.status === 'processing')
}

function thumbUrl(docId) {
  return `/api/v1/files/${docId}/thumbnail?token=${encodeURIComponent(authToken.value)}`
}

async function fetchDocs(silent = false) {
  if (!silent) loading.value = true
  listError.value = ''
  try {
    const res = await getDocuments({
      page: page.value,
      limit,
      sort_by: 'created_at',
      sort_order: 'desc',
      ...(filters.status && { status: filters.status }),
      ...(filters.file_type && { file_type: filters.file_type }),
      ...(filters.favoritesOnly && { is_favorite: true }),
    })
    documents.value = res.data.data.items
    total.value = res.data.data.total

    if (shouldPoll()) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (e) {
    listError.value = e.response?.data?.message || 'Failed to load documents'
  } finally {
    if (!silent) loading.value = false
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

function clearFilter(key) {
  filters[key] = key === 'favoritesOnly' ? false : ''
  onFilterChange()
}

async function handleToggleFavorite(doc) {
  const prev = doc.is_favorite
  doc.is_favorite = !prev // Optimistic update
  try {
    await toggleFavorite(doc.id)
  } catch {
    doc.is_favorite = prev // Revert on error
  }
}

function onDragEnter() {
  dragCounter++
  dragging.value = true
}

function onDragLeave() {
  dragCounter--
  if (dragCounter <= 0) {
    dragging.value = false
    dragCounter = 0
  }
}

function onDrop(e) {
  dragging.value = false
  dragCounter = 0
  const file = e.dataTransfer?.files?.[0]
  if (file) uploadFile(file)
}

async function handleUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploadFile(file)
}

async function uploadFile(file) {
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

watch(() => route.query.q, (q) => {
  if (q) {
    doSearch(q)
  } else if (route.path === '/') {
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

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<style scoped>
/* Stagger animation */
@keyframes cardIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.doc-list { display: flex; flex-direction: column; gap: 0.625rem; }

.doc-card {
  display: flex;
  align-items: stretch;
  cursor: pointer;
  transition: box-shadow var(--transition-fast);
  animation: cardIn var(--transition-normal) both;
}
.doc-card:hover { box-shadow: var(--shadow-hover); }

/* Dual-zone card: visual left + info right */
.doc-card-visual {
  flex-shrink: 0;
  width: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid var(--border);
  background: var(--bg);
  border-radius: var(--radius) 0 0 var(--radius);
  overflow: hidden;
}
.doc-thumb-img { width: 100%; height: 100%; object-fit: cover; }

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
}
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

.filter-fav-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  cursor: pointer;
  user-select: none;
}
.filter-fav-toggle input { accent-color: var(--primary); }
.fav-toggle-label { color: var(--text-secondary); }

/* Drag-drop zone */
.drop-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  margin-bottom: 1rem;
  text-align: center;
  transition: all var(--transition-fast);
  background: var(--bg-card);
}
.drop-zone-active {
  border-color: var(--primary);
  background: var(--primary-focus-ring);
}
.drop-zone-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}
.drop-zone-icon { font-size: 1.5rem; }

/* Filter bar */
.filter-bar {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  align-items: center;
  flex-wrap: wrap;
}
.filter-select { width: auto; min-width: 120px; font-size: 0.8125rem; padding: 0.375rem 0.625rem; }

.filter-tags { display: flex; gap: 0.375rem; }
.filter-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.625rem;
  background: var(--primary-focus-ring);
  color: var(--primary);
  border-radius: 9999px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.filter-tag:hover { background: var(--border); }

/* Skeleton loading */
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

/* Pagination */
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
  .doc-card-visual { width: 48px; }
  .doc-card-info { padding: 0.625rem 0.75rem; }
  .doc-card-actions { flex-direction: column; padding: 0.5rem; border-left: none; border-top: 1px solid var(--border); }
  .filter-bar { flex-direction: column; }
  .filter-select { width: 100%; }
  .drop-zone { padding: 1rem; }
}
</style>
