<template>
  <div class="card timeline-section">
    <h3 class="section-title">Recent Activity</h3>
    <div v-if="loading" class="skeleton-list">
      <div v-for="i in 4" :key="i" class="skeleton-row">
        <div class="skeleton-dot"></div>
        <div class="skeleton-line" style="flex:1"></div>
      </div>
    </div>
    <div v-else-if="activities.length === 0" class="empty-hint">No activity yet</div>
    <div v-else class="timeline">
      <div v-for="item in activities" :key="item.id" class="timeline-item">
        <span class="timeline-icon">{{ actionIcon(item.action) }}</span>
        <div class="timeline-body">
          <span class="timeline-action">{{ actionLabel(item.action) }}</span>
          <span v-if="item.document_title" class="timeline-doc">{{ item.document_title }}</span>
          <span class="timeline-time">{{ formatTime(item.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  activities: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

function actionIcon(action) {
  const map = { upload: '&#128228;', view: '&#128065;', delete: '&#128465;', search: '&#128269;', favorite: '&#9733;' }
  return map[action] || '&#8226;'
}

function actionLabel(action) {
  const map = { upload: 'Uploaded', view: 'Viewed', delete: 'Deleted', search: 'Searched', favorite: 'Favorited' }
  return map[action] || action
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h ago`
  const diffD = Math.floor(diffH / 24)
  return `${diffD}d ago`
}
</script>

<style scoped>
.timeline-section {
  padding: 1rem 1.25rem;
}
.section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--text);
}
.timeline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.timeline-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.8125rem;
}
.timeline-icon {
  flex-shrink: 0;
  width: 1.5rem;
  text-align: center;
}
.timeline-body {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  flex-wrap: wrap;
  min-width: 0;
}
.timeline-action {
  font-weight: 500;
  color: var(--text);
}
.timeline-doc {
  color: var(--primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}
.timeline-time {
  color: var(--text-secondary);
  font-size: 0.75rem;
  white-space: nowrap;
}
.empty-hint {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  padding: 0.5rem 0;
}
.skeleton-list { display: flex; flex-direction: column; gap: 0.5rem; }
.skeleton-row { display: flex; align-items: center; gap: 0.5rem; }
.skeleton-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
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
