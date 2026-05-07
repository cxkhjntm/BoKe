<template>
  <div class="chat-empty">
    <svg class="chat-empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
      <path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
    <p class="chat-empty-title">开始一段新的对话</p>
    <p class="chat-empty-subtitle">在下方输入框发送消息</p>
  </div>
</template>

<style scoped>
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-secondary);
  gap: 0.5rem;
}
.chat-empty-icon {
  width: 3rem;
  height: 3rem;
  opacity: 0.4;
}
.chat-empty-title {
  font-size: 1rem;
  font-weight: 500;
  margin: 0;
}
.chat-empty-subtitle {
  font-size: 0.8125rem;
  margin: 0;
  opacity: 0.7;
}
</style>
