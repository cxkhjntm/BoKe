<template>
  <div class="chat-input-bar">
    <div class="chat-input-inner">
      <textarea
        ref="textareaRef"
        v-model="text"
        class="chat-textarea"
        rows="1"
        :disabled="disabled"
        :placeholder="placeholder"
        @keydown="handleKeydown"
        @input="autoResize"
      />
      <button
        class="btn btn-primary send-btn"
        :disabled="disabled || !text.trim()"
        @click="handleSend"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: '请输入消息...' },
})
const emit = defineEmits(['send'])

const text = ref('')
const textareaRef = ref(null)

function handleSend() {
  const content = text.value.trim()
  if (!content || props.disabled) return
  emit('send', content)
  text.value = ''
  nextTick(autoResize)
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  const maxRows = 4
  const lineHeight = 20
  const maxHeight = maxRows * lineHeight
  el.style.height = Math.min(el.scrollHeight, maxHeight) + 'px'
}

watch(() => props.disabled, (val) => {
  if (!val) {
    nextTick(() => textareaRef.value?.focus())
  }
})
</script>

<style scoped>
.chat-input-bar {
  background: var(--bg-card);
  border-top: 1px solid var(--border);
  padding: 0.75rem 1rem;
}
.chat-input-inner {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  max-width: 800px;
  margin: 0 auto;
}
.chat-textarea {
  flex: 1;
  resize: none;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.875rem;
  line-height: 1.5;
  background: var(--bg);
  color: var(--text);
  outline: none;
  min-height: 2.25rem;
  max-height: 6rem;
  overflow-y: auto;
}
.chat-textarea:focus {
  border-color: var(--primary);
}
.chat-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.send-btn {
  padding: 0.5rem 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
