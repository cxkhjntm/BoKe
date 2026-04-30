<template>
  <div>
    <div class="page-header">
      <div>
        <router-link to="/documents" class="back-link">&larr; 文档列表</router-link>
        <h1 class="page-title" style="margin-top:0.25rem;">{{ doc?.title || '加载中...' }}</h1>
        <div v-if="doc" class="doc-meta">
          <span class="badge" :class="'badge-' + doc.status">{{ statusLabel(doc.status) }}</span>
          <span class="doc-type">{{ doc.file_type.toUpperCase() }}</span>
          <span>{{ formatSize(doc.file_size) }}</span>
          <span>{{ formatDate(doc.created_at) }}</span>
        </div>
      </div>
      <div v-if="doc" class="header-actions">
        <button class="btn btn-sm" @click="openOriginal" :disabled="fileLoading">
          {{ fileLoading ? '加载中...' : '打开原文' }}
        </button>
        <button
          v-if="doc.status === 'error'"
          class="btn btn-sm btn-primary"
          @click="handleRetry"
          :disabled="retrying"
        >
          {{ retrying ? '重试中...' : '重新处理' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="empty"><span class="spinner"></span></div>
    <div v-else-if="error" class="alert alert-error">
      {{ error }}
      <button class="btn btn-sm" style="margin-left:0.5rem;" @click="fetchDoc">重试</button>
    </div>
    <div v-else-if="doc" class="reader-layout">
      <!-- Main content area -->
      <div class="reader-content card">
        <!-- Status messages -->
        <div v-if="doc.status === 'queued'" class="reader-status">
          <span class="spinner"></span>
          <span>文档排队等待处理...</span>
        </div>
        <div v-else-if="doc.status === 'processing'" class="reader-status">
          <span class="spinner"></span>
          <span>文档处理中...</span>
        </div>
        <div v-else-if="doc.status === 'error'" class="reader-status reader-status-error">
          <span>处理失败：{{ doc.error_message || '未知错误' }}</span>
          <button class="btn btn-sm btn-primary" @click="handleRetry" :disabled="retrying" style="margin-left:auto;">
            {{ retrying ? '重试中...' : '重试' }}
          </button>
        </div>

        <!-- PDF viewer -->
        <div v-if="doc.file_type === 'pdf' && doc.status === 'ready'" class="pdf-viewer">
          <div v-if="fileLoading" class="empty"><span class="spinner"></span> 加载 PDF...</div>
          <iframe v-else-if="fileBlobUrl" :src="fileBlobUrl" class="pdf-frame" title="PDF Viewer"></iframe>
        </div>

        <!-- Image viewer -->
        <div v-else-if="['png','jpg','jpeg'].includes(doc.file_type) && doc.status === 'ready'" class="image-viewer">
          <div v-if="fileLoading" class="empty"><span class="spinner"></span> 加载图片...</div>
          <img v-else-if="fileBlobUrl" :src="fileBlobUrl" :alt="doc.title" class="preview-image" />
        </div>

        <!-- Markdown viewer -->
        <div v-else-if="doc.file_type === 'md'" class="md-viewer">
          <div v-if="doc.status === 'ready' && renderedMd" class="md-content" v-html="renderedMd"></div>
          <div v-else-if="doc.status === 'ready'" class="empty">暂无内容可显示</div>
        </div>

        <!-- DOCX: show extracted text -->
        <div v-else-if="doc.file_type === 'docx'" class="text-viewer">
          <div v-if="doc.status === 'ready' && doc.content_text" class="text-content">{{ doc.content_text }}</div>
          <div v-else-if="doc.status === 'ready'" class="empty">未能提取文本内容</div>
        </div>

        <!-- Fallback -->
        <div v-else class="text-viewer">
          <div v-if="doc.content_text" class="text-content">{{ doc.content_text }}</div>
          <div v-else class="empty">该文件类型暂不支持预览</div>
        </div>
      </div>

      <!-- Metadata sidebar -->
      <aside class="reader-sidebar">
        <div class="card sidebar-section">
          <h3 class="sidebar-title">文档信息</h3>
          <dl class="meta-list">
            <dt>文件类型</dt>
            <dd>{{ doc.file_type.toUpperCase() }}</dd>
            <dt>大小</dt>
            <dd>{{ formatSize(doc.file_size) }}</dd>
            <dt>状态</dt>
            <dd><span class="badge" :class="'badge-' + doc.status">{{ statusLabel(doc.status) }}</span></dd>
            <dt>创建时间</dt>
            <dd>{{ formatDate(doc.created_at) }}</dd>
            <dt>更新时间</dt>
            <dd>{{ formatDate(doc.updated_at) }}</dd>
            <dt>原始文件</dt>
            <dd class="meta-filename">{{ doc.original_filename }}</dd>
          </dl>
        </div>
      </aside>
    </div>

    <!-- Prev/Next navigation -->
    <div v-if="doc" class="doc-nav">
      <button class="btn btn-sm" :disabled="!prevId" @click="goToDoc(prevId)">
        &larr; 上一篇
      </button>
      <button class="btn btn-sm" :disabled="!nextId" @click="goToDoc(nextId)">
        下一篇 &rarr;
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDocument, getDocuments, retryDocument, fetchFileBlobUrl } from '../api'
import { formatDate, formatSize, statusLabel } from '../utils/format'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()

const doc = ref(null)
const loading = ref(true)
const error = ref('')
const retrying = ref(false)
const fileBlobUrl = ref('')
const fileLoading = ref(false)
const renderedMd = ref('')
const prevId = ref(null)
const nextId = ref(null)

// Status polling
let pollTimer = null

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await getDocument(route.params.id)
      doc.value = res.data.data
      updateRenderedMd()
      if (doc.value.status === 'ready' || doc.value.status === 'error') {
        stopPolling()
        if (doc.value.status === 'ready') {
          await loadFileBlob()
        }
      }
    } catch {
      // Silently ignore polling errors
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function updateRenderedMd() {
  if (doc.value?.file_type === 'md' && doc.value?.content_text) {
    const raw = marked(doc.value.content_text, { breaks: true })
    renderedMd.value = DOMPurify.sanitize(raw)
  } else {
    renderedMd.value = ''
  }
}

function revokeBlobUrl() {
  if (fileBlobUrl.value) {
    URL.revokeObjectURL(fileBlobUrl.value)
    fileBlobUrl.value = ''
  }
}

async function loadFileBlob() {
  if (!doc.value || doc.value.status !== 'ready') return
  if (!['pdf', 'png', 'jpg', 'jpeg'].includes(doc.value.file_type)) return

  fileLoading.value = true
  try {
    revokeBlobUrl()
    fileBlobUrl.value = await fetchFileBlobUrl(route.params.id, 'original')
  } catch {
    // Blob load failed — user can still use "Open Original"
  } finally {
    fileLoading.value = false
  }
}

async function fetchAdjacentIds() {
  try {
    const res = await getDocuments({ page: 1, limit: 100, sort_by: 'created_at', sort_order: 'desc' })
    const items = res.data.data.items
    const currentIdx = items.findIndex(d => d.id === Number(route.params.id))
    prevId.value = currentIdx > 0 ? items[currentIdx - 1].id : null
    nextId.value = currentIdx >= 0 && currentIdx < items.length - 1 ? items[currentIdx + 1].id : null
  } catch {
    prevId.value = null
    nextId.value = null
  }
}

async function fetchDoc() {
  loading.value = true
  error.value = ''
  doc.value = null
  revokeBlobUrl()
  try {
    const res = await getDocument(route.params.id)
    doc.value = res.data.data
    updateRenderedMd()

    if (doc.value.status === 'queued' || doc.value.status === 'processing') {
      startPolling()
    } else {
      stopPolling()
    }

    if (doc.value.status === 'ready') {
      await loadFileBlob()
    }
    fetchAdjacentIds()
  } catch (e) {
    error.value = e.response?.data?.message || '加载文档失败'
  } finally {
    loading.value = false
  }
}

async function openOriginal() {
  if (!doc.value) return
  fileLoading.value = true
  try {
    const url = await fetchFileBlobUrl(route.params.id, 'original')
    window.open(url, '_blank')
  } catch {
    error.value = '加载文件失败'
  } finally {
    fileLoading.value = false
  }
}

async function handleRetry() {
  retrying.value = true
  try {
    const res = await retryDocument(route.params.id)
    doc.value = res.data.data
    updateRenderedMd()
    startPolling()
  } catch (e) {
    error.value = e.response?.data?.message || '重试失败'
  } finally {
    retrying.value = false
  }
}

function goToDoc(id) {
  if (id) router.push(`/documents/${id}`)
}

watch(() => route.params.id, (newId, oldId) => {
  if (newId && newId !== oldId) fetchDoc()
})

onBeforeUnmount(() => {
  stopPolling()
  revokeBlobUrl()
})

onMounted(fetchDoc)
</script>

<style scoped>
.back-link { font-size: 0.875rem; color: var(--text-secondary); }
.back-link:hover { color: var(--primary); text-decoration: none; }

.doc-meta { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: var(--text-secondary); margin-top: 0.25rem; }
.doc-type { font-family: var(--font-mono); font-size: 0.75rem; }

.header-actions { display: flex; gap: 0.5rem; }

/* Two-column layout */
.reader-layout {
  display: grid;
  grid-template-columns: 1fr 260px;
  gap: 1rem;
  align-items: start;
}

.reader-content { padding: 1.5rem; min-height: 400px; }

/* Sidebar */
.reader-sidebar { position: sticky; top: 1rem; }
.sidebar-section { padding: 1rem; }
.sidebar-title { font-size: 0.875rem; font-weight: 600; margin-bottom: 0.75rem; }
.meta-list { display: grid; grid-template-columns: auto 1fr; gap: 0.25rem 0.75rem; font-size: 0.8125rem; }
.meta-list dt { color: var(--text-secondary); font-weight: 500; }
.meta-list dd { color: var(--text); word-break: break-all; }
.meta-filename { font-family: var(--font-mono); font-size: 0.75rem; }

/* Status messages */
.reader-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--status-processing-bg);
  border-radius: var(--radius);
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--status-processing-text);
}
.reader-status-error { background: var(--status-error-bg); color: var(--status-error-text); }

/* PDF viewer */
.pdf-viewer { width: 100%; }
.pdf-frame { width: 100%; height: 80vh; border: 1px solid var(--border); border-radius: var(--radius); }

/* Image viewer */
.image-viewer { text-align: center; }
.preview-image { max-width: 100%; max-height: 80vh; border-radius: var(--radius); }

/* Markdown viewer */
.md-content { line-height: 1.8; font-size: 0.9375rem; }
.md-content :deep(h1) { font-size: 1.5rem; margin: 1.5rem 0 0.75rem; }
.md-content :deep(h2) { font-size: 1.25rem; margin: 1.25rem 0 0.625rem; }
.md-content :deep(h3) { font-size: 1.125rem; margin: 1rem 0 0.5rem; }
.md-content :deep(p) { margin-bottom: 0.75rem; }
.md-content :deep(code) { background: var(--bg); padding: 0.125rem 0.375rem; border-radius: 4px; font-family: var(--font-mono); font-size: 0.875em; }
.md-content :deep(pre) { background: var(--bg); padding: 1rem; border-radius: var(--radius); overflow-x: auto; margin-bottom: 1rem; }
.md-content :deep(pre code) { padding: 0; background: none; }
.md-content :deep(blockquote) { border-left: 3px solid var(--primary); padding-left: 1rem; color: var(--text-secondary); margin-bottom: 0.75rem; }
.md-content :deep(ul), .md-content :deep(ol) { padding-left: 1.5rem; margin-bottom: 0.75rem; }
.md-content :deep(table) { border-collapse: collapse; width: 100%; margin-bottom: 1rem; }
.md-content :deep(th), .md-content :deep(td) { border: 1px solid var(--border); padding: 0.5rem; text-align: left; font-size: 0.875rem; }
.md-content :deep(th) { background: var(--bg); }
.md-content :deep(img) { max-width: 100%; border-radius: var(--radius); }

/* Text viewer */
.text-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.875rem;
  line-height: 1.7;
  color: var(--text);
}

/* Prev/Next navigation */
.doc-nav {
  display: flex;
  justify-content: space-between;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
}

@media (max-width: 768px) {
  .reader-layout { grid-template-columns: 1fr; }
  .reader-sidebar { position: static; }
  .reader-content { padding: 1rem; }
  .pdf-frame { height: 60vh; }
}
</style>
