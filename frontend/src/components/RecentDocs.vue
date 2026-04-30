<template>
  <div class="card recent-section">
    <h3 class="section-title">{{ title }}</h3>
    <div v-if="loading" class="skeleton-list">
      <div v-for="i in 3" :key="i" class="skeleton-row">
        <div class="skeleton-dot"></div>
        <div class="skeleton-line" style="flex:1"></div>
      </div>
    </div>
    <div v-else-if="docs.length === 0" class="empty-hint">{{ emptyText }}</div>
    <div v-else class="doc-list">
      <div
        v-for="doc in docs"
        :key="doc.id"
        class="doc-row"
        @click="$emit('navigate', doc.id)"
      >
        <span class="doc-icon" :class="'ft-' + doc.file_type">{{ doc.file_type.toUpperCase() }}</span>
        <div class="doc-info">
          <div class="doc-name">{{ doc.title }}</div>
          <div class="doc-meta-row">
            <span class="badge" :class="'badge-' + doc.status">{{ statusLabel(doc.status) }}</span>
            <span>{{ formatDate(doc.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatDate, statusLabel } from '../utils/format'

defineProps({
  title: { type: String, default: '文档列表' },
  docs: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: '暂无文档' },
})

defineEmits(['navigate'])
</script>

<style scoped>
.recent-section {
  padding: 1rem 1.25rem;
}
.section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--text);
}
.doc-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}
.doc-row {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.375rem;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--transition-fast);
}
.doc-row:hover { background: var(--bg); }
.doc-icon {
  font-family: var(--font-mono);
  font-size: 0.625rem;
  font-weight: 700;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  background: var(--border);
  color: var(--text-secondary);
  flex-shrink: 0;
}
.ft-pdf { background: #fee2e2; color: #991b1b; }
.ft-docx { background: #dbeafe; color: #1e40af; }
.ft-md { background: #dcfce7; color: #166534; }
.ft-png, .ft-jpg, .ft-jpeg { background: #fef9c3; color: #854d0e; }
.doc-info { min-width: 0; flex: 1; }
.doc-name {
  font-size: 0.875rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.doc-meta-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.125rem;
}
.empty-hint {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  padding: 0.5rem 0;
}
.skeleton-list { display: flex; flex-direction: column; gap: 0.5rem; }
.skeleton-row { display: flex; align-items: center; gap: 0.5rem; }
.skeleton-dot {
  width: 28px;
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton-line {
  height: 0.75rem;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--border) 25%, var(--bg) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
