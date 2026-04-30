<template>
  <div>
    <div class="page-header">
      <div>
        <router-link to="/" class="back-link">← Documents</router-link>
        <h1 class="page-title" style="margin-top:0.25rem;">{{ doc?.title || 'Loading...' }}</h1>
        <div v-if="doc" class="doc-meta">
          <span class="badge" :class="'badge-' + doc.status">{{ statusLabel(doc.status) }}</span>
          <span class="doc-type">{{ doc.file_type.toUpperCase() }}</span>
          <span>{{ formatSize(doc.file_size) }}</span>
          <span>{{ formatDate(doc.created_at) }}</span>
        </div>
      </div>
      <div v-if="doc" style="display:flex; gap:0.5rem;">
        <a :href="originalUrl" target="_blank" class="btn btn-sm">Open Original</a>
        <button
          v-if="doc.status === 'error'"
          class="btn btn-sm"
          @click="handleRetry"
          :disabled="retrying"
        >
          {{ retrying ? 'Retrying...' : 'Retry Processing' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="empty"><span class="spinner"></span></div>
    <div v-else-if="error" class="alert alert-error">{{ error }}</div>
    <div v-else-if="doc" class="reader-content card">
      <!-- Status messages -->
      <div v-if="doc.status === 'processing'" class="reader-status">
        <span class="spinner"></span>
        <span>Document is being processed...</span>
      </div>
      <div v-else-if="doc.status === 'error'" class="reader-status reader-status-error">
        <span>Processing failed: {{ doc.error_message || 'Unknown error' }}</span>
      </div>

      <!-- PDF viewer -->
      <div v-if="doc.file_type === 'pdf' && doc.status === 'ready'" class="pdf-viewer">
        <iframe :src="originalUrl" class="pdf-frame" title="PDF Viewer"></iframe>
      </div>

      <!-- Image viewer -->
      <div v-else-if="['png','jpg','jpeg'].includes(doc.file_type) && doc.status === 'ready'" class="image-viewer">
        <img :src="originalUrl" :alt="doc.title" class="preview-image" />
      </div>

      <!-- Markdown viewer -->
      <div v-else-if="doc.file_type === 'md'" class="md-viewer">
        <div v-if="doc.status === 'ready' && renderedMd" class="md-content" v-html="renderedMd"></div>
        <div v-else-if="doc.status === 'ready'" class="empty">No content to display</div>
      </div>

      <!-- DOCX: show extracted text -->
      <div v-else-if="doc.file_type === 'docx'" class="text-viewer">
        <div v-if="doc.status === 'ready' && doc.content_text" class="text-content">{{ doc.content_text }}</div>
        <div v-else-if="doc.status === 'ready'" class="empty">No text content extracted</div>
      </div>

      <!-- Fallback: show content_text if available -->
      <div v-else class="text-viewer">
        <div v-if="doc.content_text" class="text-content">{{ doc.content_text }}</div>
        <div v-else class="empty">No preview available for this file type</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getDocument, retryDocument, getFileUrl } from '../api'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const route = useRoute()
const docId = route.params.id

const doc = ref(null)
const loading = ref(true)
const error = ref('')
const retrying = ref(false)

const originalUrl = computed(() => doc.value ? getFileUrl(docId, 'original') : '')

const renderedMd = computed(() => {
  if (doc.value?.file_type === 'md' && doc.value?.content_text) {
    const raw = marked(doc.value.content_text, { breaks: true })
    return DOMPurify.sanitize(raw)
  }
  return ''
})

async function fetchDoc() {
  loading.value = true
  error.value = ''
  try {
    const res = await getDocument(docId)
    doc.value = res.data.data
  } catch (e) {
    error.value = e.response?.data?.message || 'Failed to load document'
  } finally {
    loading.value = false
  }
}

async function handleRetry() {
  retrying.value = true
  try {
    const res = await retryDocument(docId)
    doc.value = res.data.data
  } catch (e) {
    error.value = e.response?.data?.message || 'Retry failed'
  } finally {
    retrying.value = false
  }
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

onMounted(fetchDoc)
</script>

<style scoped>
.back-link { font-size: 0.875rem; color: var(--text-secondary); }
.back-link:hover { color: var(--primary); text-decoration: none; }

.doc-meta { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; color: var(--text-secondary); margin-top: 0.25rem; }
.doc-type { font-family: var(--font-mono); font-size: 0.75rem; }

.reader-content { padding: 1.5rem; min-height: 400px; }

.reader-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #fef9c3;
  border-radius: var(--radius);
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: #854d0e;
}
.reader-status-error { background: #fee2e2; color: #991b1b; }

.pdf-viewer { width: 100%; }
.pdf-frame { width: 100%; height: 80vh; border: 1px solid var(--border); border-radius: var(--radius); }

.image-viewer { text-align: center; }
.preview-image { max-width: 100%; max-height: 80vh; border-radius: var(--radius); }

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

.text-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.875rem;
  line-height: 1.7;
  color: var(--text);
}

@media (max-width: 640px) {
  .reader-content { padding: 1rem; }
  .pdf-frame { height: 60vh; }
}
</style>
