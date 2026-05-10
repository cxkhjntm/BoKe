import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getLLMConfigs, getActiveLLMConfig, saveLLMConfig, activateLLMProvider, deleteLLMConfig,
  getChatSessions, createChatSession, updateChatSession, deleteChatSession,
  getChatMessages, sendChatMessage,
} from '../api'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const configs = ref([])
  const activeConfig = ref(null)
  const streaming = ref(false)
  const error = ref(null)
  const loadingSessions = ref(false)
  const loadingMessages = ref(false)

  const currentSession = computed(() =>
    sessions.value.find(s => s.session_id === currentSessionId.value) || null
  )

  async function fetchSessions() {
    loadingSessions.value = true
    try {
      const res = await getChatSessions()
      sessions.value = res.data.data.items || []
    } catch (e) {
      error.value = e.message
    } finally {
      loadingSessions.value = false
    }
  }

  async function createSession(title = '新会话') {
    try {
      const res = await createChatSession({ title })
      const session = res.data.data
      sessions.value.unshift(session)
      return session
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function switchSession(sessionId) {
    currentSessionId.value = sessionId
    messages.value = []
    await fetchMessages(sessionId)
  }

  async function fetchMessages(sessionId) {
    loadingMessages.value = true
    try {
      const res = await getChatMessages(sessionId)
      messages.value = res.data.data.messages || []
    } catch (e) {
      error.value = e.message
    } finally {
      loadingMessages.value = false
    }
  }

  async function renameSession(sessionId, title) {
    try {
      await updateChatSession(sessionId, { title })
      const s = sessions.value.find(s => s.session_id === sessionId)
      if (s) s.title = title
    } catch (e) {
      error.value = e.message
    }
  }

  async function removeSession(sessionId) {
    try {
      await deleteChatSession(sessionId)
      sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = null
        messages.value = []
      }
    } catch (e) {
      error.value = e.message
    }
  }

  async function sendMessage(content) {
    if (!currentSessionId.value) return
    error.value = null
    streaming.value = true

    const currentSession = sessions.value.find(s => s.session_id === currentSessionId.value)
    if (currentSession && currentSession.title === '新会话') {
      const titleText = content.trim()
      if (titleText.length > 10) {
        currentSession.title = titleText.substring(0, 10) + '...'
      } else {
        currentSession.title = titleText
      }
    }

    messages.value.push({ role: 'user', content })
    const assistantMsg = { role: 'assistant', content: '' }
    messages.value.push(assistantMsg)

    try {
      await sendChatMessage(currentSessionId.value, content, (event) => {
        if (event.type === 'delta') {
          assistantMsg.content += event.content
        } else if (event.type === 'finish') {
          assistantMsg.content = event.content
        }
      })
    } catch (e) {
      error.value = e.message
      messages.value = messages.value.filter(m => m !== assistantMsg)
    } finally {
      streaming.value = false
    }
  }

  async function fetchConfigs() {
    try {
      const res = await getLLMConfigs()
      configs.value = res.data.data || []
      const activeRes = await getActiveLLMConfig()
      activeConfig.value = activeRes.data.data
    } catch {
      configs.value = []
      activeConfig.value = null
    }
  }

  async function saveConfig(cfg) {
    try {
      await saveLLMConfig(cfg)
      await fetchConfigs()
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function activateConfig(provider) {
    try {
      await activateLLMProvider(provider)
      await fetchConfigs()
    } catch (e) {
      error.value = e.message
      throw e
    }
  }

  async function deleteConfig(provider) {
    try {
      await deleteLLMConfig(provider)
      await fetchConfigs()
    } catch (e) {
      error.value = e.message
    }
  }

  return {
    sessions, currentSessionId, messages, configs, activeConfig, streaming, error,
    loadingSessions, loadingMessages, currentSession,
    fetchSessions, createSession, switchSession, fetchMessages,
    renameSession, removeSession, sendMessage,
    fetchConfigs, saveConfig, activateConfig, deleteConfig,
  }
})
