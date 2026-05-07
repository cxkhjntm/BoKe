<template>
  <aside class="chat-sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">会话列表</span>
      <button class="btn btn-sm btn-primary" @click="$emit('create')">+ 新建</button>
    </div>

    <div v-if="loading" class="sidebar-empty">加载中...</div>
    <div v-else-if="sessions.length === 0" class="sidebar-empty">
      暂无会话，点击新建
    </div>
    <ul v-else class="session-list">
      <li
        v-for="s in sessions"
        :key="s.session_id"
        class="session-item"
        :class="{ active: s.session_id === currentSessionId }"
        @click="$emit('switch', s.session_id)"
      >
        <div class="session-info">
          <div
            v-if="editingId === s.session_id"
            class="session-title-input-wrap"
            @click.stop
          >
            <input
              v-model="editingTitle"
              class="session-title-input"
              @blur="commitRename(s.session_id)"
              @keydown.enter="commitRename(s.session_id)"
            />
          </div>
          <span v-else class="session-title" @dblclick.stop="startRename(s)">
            {{ s.title }}
          </span>
          <span class="session-time">{{ formatTime(s.updated_at) }}</span>
        </div>
        <button
          class="btn btn-sm btn-danger session-delete"
          @click.stop="$emit('delete', s.session_id)"
          title="删除会话"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </li>
    </ul>
  </aside>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  sessions: { type: Array, default: () => [] },
  currentSessionId: { type: String, default: null },
  loading: { type: Boolean, default: false },
})

defineEmits(['switch', 'create', 'delete', 'rename'])

const editingId = ref(null)
const editingTitle = ref('')

function startRename(s) {
  editingId.value = s.session_id
  editingTitle.value = s.title
}

function commitRename(sessionId) {
  const title = editingTitle.value.trim()
  if (title) {
    $emit('rename', sessionId, title)
  }
  editingId.value = null
  editingTitle.value = ''
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  if (diff < 60 * 1000) return '刚刚'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / (60 * 1000))}分钟前`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / (60 * 60 * 1000))}小时前`
  return `${d.getMonth() + 1}月${d.getDate()}日`
}
</script>

<style scoped>
.chat-sidebar {
  width: 260px;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border);
}
.sidebar-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text);
}
.session-list {
  list-style: none;
  margin: 0;
  padding: 0.5rem;
  overflow-y: auto;
  flex: 1;
}
.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.625rem;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
  border-left: 3px solid transparent;
}
.session-item:hover {
  background: var(--bg-hover);
}
.session-item.active {
  background: var(--bg-hover);
  border-left-color: var(--primary);
}
.session-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.session-title {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-time {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.125rem;
}
.session-title-input-wrap {
  width: 100%;
}
.session-title-input {
  width: 100%;
  font-size: 0.8125rem;
  padding: 0.25rem 0.375rem;
  border: 1px solid var(--primary);
  border-radius: var(--radius-sm);
  outline: none;
  background: var(--bg-card);
  color: var(--text);
}
.session-delete {
  opacity: 0;
  margin-left: 0.5rem;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.session-item:hover .session-delete {
  opacity: 1;
}
.sidebar-empty {
  padding: 1rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  text-align: center;
}
@media (max-width: 768px) {
  .chat-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--border);
  }
}
</style>
