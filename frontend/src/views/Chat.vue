<template>
  <div class="chat-layout">
    <ChatSidebar
      :sessions="chatStore.sessions"
      :current-session-id="chatStore.currentSessionId"
      :loading="chatStore.loadingSessions"
      @switch="chatStore.switchSession"
      @create="handleCreateSession"
      @delete="chatStore.removeSession"
      @rename="chatStore.renameSession"
    />
    <div class="chat-main">
      <ChatConfigPanel
        :config="chatStore.config"
        :saving="savingConfig"
        @save="handleSaveConfig"
        @cancel="chatStore.fetchConfig"
        @delete="handleDeleteConfig"
      />
      <ChatMessageList
        :messages="chatStore.messages"
        :loading="chatStore.loadingMessages"
        :streaming="chatStore.streaming"
      />
      <div v-if="chatStore.error" class="chat-error">
        {{ chatStore.error }}
        <button class="btn btn-sm" @click="chatStore.error = null">清除</button>
      </div>
      <ChatInput
        :disabled="!chatStore.currentSessionId || chatStore.streaming"
        placeholder="输入消息，按 Enter 发送..."
        @send="chatStore.sendMessage"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useChatStore } from '../stores/chat'
import ChatSidebar from '../components/chat/ChatSidebar.vue'
import ChatConfigPanel from '../components/chat/ChatConfigPanel.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import ChatInput from '../components/chat/ChatInput.vue'

const chatStore = useChatStore()
const savingConfig = ref(false)

async function handleCreateSession() {
  const session = await chatStore.createSession()
  if (session) {
    await chatStore.switchSession(session.session_id)
  }
}

async function handleSaveConfig(cfg) {
  savingConfig.value = true
  try {
    await chatStore.saveConfig(cfg)
  } finally {
    savingConfig.value = false
  }
}

async function handleDeleteConfig() {
  savingConfig.value = true
  try {
    await chatStore.clearConfig()
  } finally {
    savingConfig.value = false
  }
}

onMounted(async () => {
  await chatStore.fetchConfig()
  await chatStore.fetchSessions()
  if (chatStore.sessions.length === 0) {
    const session = await chatStore.createSession()
    if (session) {
      await chatStore.switchSession(session.session_id)
    }
  } else if (!chatStore.currentSessionId) {
    await chatStore.switchSession(chatStore.sessions[0].session_id)
  }
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: calc(100vh - 3.5rem);
  background: var(--bg);
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background: var(--status-error-bg);
  color: var(--status-error-text);
  font-size: 0.8125rem;
}
@media (max-width: 768px) {
  .chat-layout {
    flex-direction: column;
    height: calc(100vh - 3.5rem);
  }
}
</style>
