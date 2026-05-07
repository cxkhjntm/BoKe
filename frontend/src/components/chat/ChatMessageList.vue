<template>
  <div ref="listRef" class="chat-message-list">
    <template v-if="messages.length === 0">
      <ChatEmptyState />
    </template>
    <template v-else>
      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="message-row"
        :class="msg.role"
      >
        <div class="message-avatar">
          <svg v-if="msg.role === 'user'" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
          <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="9" y1="9" x2="15" y2="9"/>
            <line x1="9" y1="15" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="message-bubble">
          <div v-if="msg.role === 'assistant'" class="message-content" v-html="renderMarkdown(msg.content)" />
          <div v-else class="message-content">{{ msg.content }}</div>
        </div>
      </div>
      <div v-if="streaming && isAssistantEmpty" class="message-row assistant">
        <div class="message-avatar">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="9" y1="9" x2="15" y2="9"/>
            <line x1="9" y1="15" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="message-bubble">
          <div class="thinking-indicator">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import ChatEmptyState from './ChatEmptyState.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  streaming: { type: Boolean, default: false },
})

const listRef = ref(null)

const isAssistantEmpty = computed(() => {
  const last = props.messages[props.messages.length - 1]
  return last && last.role === 'assistant' && !last.content
})

function renderMarkdown(text) {
  if (!text) return ''
  const raw = marked(text, { breaks: true })
  return DOMPurify.sanitize(raw)
}

watch(() => props.messages.length, () => {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.chat-message-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}
.message-row.user {
  flex-direction: row-reverse;
}
.message-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.message-row.user .message-avatar {
  background: var(--primary);
  color: #fff;
}
.message-bubble {
  max-width: 70%;
  padding: 0.625rem 0.875rem;
  border-radius: var(--radius);
  font-size: 0.875rem;
  line-height: 1.6;
  word-break: break-word;
}
.message-row.user .message-bubble {
  background: var(--primary);
  color: #fff;
}
.message-row.assistant .message-bubble {
  background: var(--bg-hover);
  color: var(--text);
}
.message-row.system .message-bubble {
  background: transparent;
  color: var(--text-secondary);
  font-style: italic;
  font-size: 0.8125rem;
  text-align: center;
  max-width: 100%;
}
.message-content :deep(p) {
  margin-bottom: 0.5rem;
}
.message-content :deep(pre) {
  background: var(--bg);
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin-bottom: 0.5rem;
}
.message-content :deep(code) {
  background: var(--bg);
  padding: 0.125rem 0.25rem;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.875em;
}
.message-content :deep(pre code) {
  padding: 0;
  background: none;
}
.thinking-indicator {
  display: flex;
  gap: 0.25rem;
  align-items: center;
  padding: 0.25rem 0;
}
.dot {
  width: 6px;
  height: 6px;
  background: var(--text-secondary);
  border-radius: 50%;
  animation: pulse 1.4s infinite ease-in-out both;
}
.dot:nth-child(1) {
  animation-delay: -0.32s;
}
.dot:nth-child(2) {
  animation-delay: -0.16s;
}
@keyframes pulse {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
