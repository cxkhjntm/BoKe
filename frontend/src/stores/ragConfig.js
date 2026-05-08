import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getEmbeddingConfig,
  updateEmbeddingConfig as apiUpdateEmbeddingConfig,
  getRAGConfig,
  updateRAGConfig as apiUpdateRAGConfig,
  testEmbeddingConnection as apiTestEmbeddingConnection,
} from '../api/ragConfig'

export const useRagConfigStore = defineStore('ragConfig', () => {
  const embeddingConfig = ref(null)
  const ragConfig = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchEmbeddingConfig() {
    loading.value = true
    error.value = null
    try {
      const res = await getEmbeddingConfig()
      embeddingConfig.value = res.data.data
      return embeddingConfig.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateEmbeddingConfig(data) {
    loading.value = true
    error.value = null
    try {
      const res = await apiUpdateEmbeddingConfig(data)
      embeddingConfig.value = res.data.data
      return embeddingConfig.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchRAGConfig() {
    loading.value = true
    error.value = null
    try {
      const res = await getRAGConfig()
      ragConfig.value = res.data.data
      return ragConfig.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateRAGConfig(data) {
    loading.value = true
    error.value = null
    try {
      const res = await apiUpdateRAGConfig(data)
      ragConfig.value = res.data.data
      return ragConfig.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function testEmbeddingConnection(data) {
    const res = await apiTestEmbeddingConnection(data)
    return res.data
  }

  return {
    embeddingConfig,
    ragConfig,
    loading,
    error,
    fetchEmbeddingConfig,
    updateEmbeddingConfig,
    fetchRAGConfig,
    updateRAGConfig,
    testEmbeddingConnection,
  }
})
