<template>
  <div class="card timeline-section">
    <h3 class="section-title">最近活动</h3>
    <div v-if="loading" class="skeleton-list">
      <div v-for="i in 4" :key="i" class="skeleton-row">
        <div class="skeleton-dot"></div>
        <div class="skeleton-line" style="flex:1"></div>
      </div>
    </div>
    <div v-else-if="activities.length === 0" class="empty-hint">暂无活动记录</div>
    <div v-else class="timeline">
      <div v-for="item in activities" :key="item.id" class="timeline-item">
        <span class="timeline-icon" aria-hidden="true">{{ actionIcon(item.action) }}</span>
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
  const map = { upload: '\u{1F4E4}', view: '\u{1F441}', delete: '\u{1F5D1}', search: '\u{1F50D}', favorite: '★' }
  return map[action] || '•'
}

function actionLabel(action) {
  const map = { upload: '上传了', view: '查看了', delete: '删除了', search: '搜索了', favorite: '收藏了' }
  return map[action] || action
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
.timeline-section {
  padding: 1rem 1.25rem;
  position: relative;
  overflow: hidden;
}
.timeline-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--primary), transparent);
  opacity: 0;
  transition: opacity var(--transition-glass);
}
.timeline-section:hover::before {
  opacity: 0.6;
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
@media (prefers-reduced-motion: reduce) {
  .skeleton-dot, .skeleton-line { animation: none; }
}
</style>
