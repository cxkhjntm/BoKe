<template>
  <div class="timeline-view">
    <!-- Skeleton loading -->
    <div v-if="loading && !hasData" class="skeleton-list">
      <div v-for="i in 3" :key="i" class="card skeleton-card">
        <div class="skeleton-thumb"></div>
        <div class="skeleton-lines">
          <div class="skeleton-line skeleton-line-title"></div>
          <div class="skeleton-line skeleton-line-meta"></div>
        </div>
      </div>
    </div>

    <div v-else-if="!hasData" class="empty">
      <div class="empty-icon" aria-hidden="true">&#9734;</div>
      <p>暂无收藏，给文档添加星标即可在此查看！</p>
    </div>

    <template v-else>
      <div v-for="(docs, dateKey) in groups" :key="dateKey" class="timeline-group">
        <div class="timeline-date-header">
          <span class="timeline-date-dot"></span>
          <span class="timeline-date-label">{{ formatGroupDate(dateKey) }}</span>
          <span class="timeline-date-count">{{ docs.length }} 篇</span>
        </div>
        <TransitionGroup name="list" tag="div" class="doc-list">
          <div
            v-for="(doc, idx) in docs"
            :key="doc.id"
            class="card doc-card"
            :style="{ animationDelay: idx * 80 + 'ms' }"
          >
            <div class="doc-card-visual" @click="$emit('open-doc', doc.id)">
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
            <div class="doc-card-info" @click="$emit('open-doc', doc.id)">
              <div class="doc-title">{{ doc.title }}</div>
              <div class="doc-meta">
                <span class="badge" :class="'badge-' + doc.status">{{ statusLabel(doc.status) }}</span>
                <span class="doc-type">{{ doc.file_type.toUpperCase() }}</span>
                <span>{{ formatSize(doc.file_size) }}</span>
                <span>{{ formatTime(doc.created_at) }}</span>
              </div>
            </div>
            <div class="doc-card-actions">
              <button
                class="btn-icon fav-btn fav-active"
                @click.stop="$emit('remove-favorite', doc)"
                title="取消收藏"
                aria-label="取消收藏"
              >
                &#9733;
              </button>
            </div>
          </div>
        </TransitionGroup>
      </div>

      <!-- Load more button -->
      <div v-if="hasMore" class="load-more">
        <button class="btn btn-sm" :disabled="loadingMore" @click="$emit('load-more')">
          {{ loadingMore ? '加载中...' : '加载更多' }}
        </button>
      </div>
      <div v-else-if="hasData" class="load-more">
        <span class="page-info">已加载全部</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatSize, statusLabel } from '../utils/format'

const props = defineProps({
  groups: { type: Object, default: () => ({}) },
  hasMore: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
})

defineEmits(['open-doc', 'remove-favorite', 'load-more'])

const hasData = computed(() => Object.keys(props.groups).length > 0)

function thumbUrl(docId) {
  const token = localStorage.getItem('access_token') || ''
  return `/api/v1/files/${docId}/thumbnail?token=${encodeURIComponent(token)}`
}

function formatGroupDate(dateStr) {
  const today = new Date().toISOString().slice(0, 10)
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  if (dateStr === today) return '今天'
  if (dateStr === yesterday) return '昨天'
  return dateStr.replace(/-/g, '/')
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}小时前`
  const diffD = Math.floor(diffH / 24)
  return `${diffD}天前`
}
</script>

<style scoped>
.timeline-view { 
  display: flex; 
  flex-direction: column; 
  gap: 1.5rem; 
  position: relative;
  padding-left: 1.5rem;
}
.timeline-view::before {
  content: "";
  position: absolute;
  left: 0.75rem;
  top: 1rem;
  bottom: 0;
  width: 2px;
  background: var(--border);
  z-index: 0;
}

.timeline-group { display: flex; flex-direction: column; gap: 0.625rem; }

.timeline-date-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  position: relative;
}
.timeline-date-dot {
  position: absolute;
  left: -1.0625rem;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--bg, #fff);
  border: 3px solid var(--primary);
  flex-shrink: 0;
  z-index: 1;
}
.timeline-date-label {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.5px;
}
.timeline-date-count {
  background: var(--bg-hover, #eff6ff);
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.doc-list { display: flex; flex-direction: column; gap: 0.625rem; }

.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(20px) scale(0.95);
}
.list-leave-active {
  position: absolute;
}

.doc-card {
  display: flex;
  align-items: stretch;
  cursor: pointer;
  animation: cardIn var(--transition-normal) both;
  border: 1px solid var(--border);
  background: var(--card-bg, #fff);
  border-radius: var(--radius);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.doc-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.1);
}
@keyframes cardIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
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
.doc-card:hover .doc-thumb-img { transform: scale(1.08); }

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
.fav-btn:active { transform: scale(0.8); }
.fav-active { color: #f59e0b; }

.load-more {
  display: flex;
  justify-content: center;
  margin-top: 0.5rem;
}
.page-info { font-size: 0.8125rem; color: var(--text-secondary); }

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

.skeleton-card:nth-child(2) .skeleton-thumb,
.skeleton-card:nth-child(2) .skeleton-line {
  animation-delay: 0.15s;
}
.skeleton-card:nth-child(3) .skeleton-thumb,
.skeleton-card:nth-child(3) .skeleton-line {
  animation-delay: 0.3s;
}

@media (prefers-reduced-motion: reduce) {
  .doc-card { animation: none; }
  .skeleton-thumb, .skeleton-line { animation: none; }
  .doc-thumb-img { transition: none; }
}

@media (max-width: 640px) {
  .doc-card-visual { width: 48px; }
  .doc-card-info { padding: 0.625rem 0.75rem; }
  .doc-card-actions { flex-direction: column; padding: 0.5rem; border-left: none; border-top: 1px solid var(--border); }
}
</style>
