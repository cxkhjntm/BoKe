<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">RAG 设置</h1>
      <router-link to="/" class="btn btn-sm">返回仪表盘</router-link>
    </div>

    <div v-if="pageError" class="alert alert-error">{{ pageError }}</div>
    <div v-if="saveSuccess" class="alert alert-success">设置已保存</div>

    <!-- Loading skeleton -->
    <template v-if="initialLoading">
      <div class="settings-section" v-for="i in 2" :key="i">
        <div class="card settings-card">
          <div class="settings-card-header">
            <div class="skeleton-line skeleton-line-title" style="width: 140px; height: 1.125rem;"></div>
          </div>
          <div class="settings-card-body">
            <div class="settings-field" v-for="j in 4" :key="j">
              <div class="skeleton-line skeleton-line-label" style="width: 90px; height: 0.75rem;"></div>
              <div class="skeleton-line" style="width: 100%; height: 2.25rem;"></div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- Embedding Model Section -->
      <div class="settings-section">
        <div class="card settings-card">
          <div class="settings-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="settings-icon">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
            <h2 class="settings-card-title">嵌入模型</h2>
          </div>
          <div class="settings-card-body">
            <div class="settings-field">
              <label class="form-label" for="apiKey">API Key</label>
              <input
                id="apiKey"
                v-model="embedding.api_key"
                type="password"
                class="input"
                placeholder="sk-..."
                autocomplete="off"
              />
            </div>
            <div class="settings-field">
              <label class="form-label" for="baseUrl">Base URL</label>
              <input
                id="baseUrl"
                v-model="embedding.base_url"
                type="text"
                class="input"
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div class="settings-field">
              <label class="form-label" for="modelName">模型名称</label>
              <input
                id="modelName"
                v-model="embedding.model_name"
                type="text"
                class="input"
                placeholder="text-embedding-3-small"
              />
            </div>
            <div class="settings-field">
              <label class="form-label" for="vectorDim">向量维度</label>
              <input
                id="vectorDim"
                v-model.number="embedding.vector_dimension"
                type="number"
                class="input"
                placeholder="1536"
                min="1"
              />
            </div>
          </div>
          <div class="settings-card-footer">
            <div class="test-connection-status">
              <Transition name="fade-slide">
                <span v-if="testSuccess" class="test-msg test-msg-success">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><polyline points="20 6 9 17 4 12"/></svg>
                  连接成功
                </span>
                <span v-else-if="testError" class="test-msg test-msg-error">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  {{ testError }}
                </span>
              </Transition>
            </div>
            <button
              class="btn btn-sm"
              :disabled="savingEmbedding || testingConnection"
              @click="testConnection"
            >
              <span v-if="testingConnection" class="spinner"></span>
              {{ testingConnection ? '测试中...' : '测试连接' }}
            </button>
            <button
              class="btn btn-primary btn-sm"
              :disabled="savingEmbedding"
              @click="saveEmbeddingConfig"
            >
              <span v-if="savingEmbedding" class="spinner"></span>
              {{ savingEmbedding ? '保存中...' : '保存嵌入配置' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Retrieval Parameters Section -->
      <div class="settings-section">
        <div class="card settings-card">
          <div class="settings-card-header">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="settings-icon">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <h2 class="settings-card-title">检索参数</h2>
          </div>
          <div class="settings-card-body">
            <div class="settings-field">
              <label class="form-label" for="chunkSize">分块大小</label>
              <input
                id="chunkSize"
                v-model.number="rag.chunk_size"
                type="number"
                class="input"
                placeholder="512"
                min="1"
              />
            </div>
            <div class="settings-field">
              <label class="form-label" for="chunkOverlap">分块重叠</label>
              <input
                id="chunkOverlap"
                v-model.number="rag.chunk_overlap"
                type="number"
                class="input"
                placeholder="50"
                min="0"
              />
            </div>
            <div class="settings-field">
              <label class="form-label" for="topK">Top K</label>
              <input
                id="topK"
                v-model.number="rag.top_k"
                type="number"
                class="input"
                placeholder="5"
                min="1"
              />
            </div>
            <div class="settings-field">
              <label class="form-label" for="threshold">阈值距离</label>
              <input
                id="threshold"
                v-model.number="rag.threshold_distance"
                type="number"
                class="input"
                placeholder="0.5"
                min="0"
                max="2"
                step="0.01"
              />
            </div>
            <div class="settings-field">
              <label class="form-label" for="queryBuffer">查询缓冲</label>
              <input
                id="queryBuffer"
                v-model.number="rag.query_buffer"
                type="number"
                class="input"
                placeholder="0"
                min="0"
              />
            </div>
          </div>
          <div class="settings-card-footer">
            <button
              class="btn btn-primary btn-sm"
              :disabled="savingRag"
              @click="saveRAGConfig"
            >
              <span v-if="savingRag" class="spinner"></span>
              {{ savingRag ? '保存中...' : '保存检索配置' }}
            </button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRagConfigStore } from '../stores/ragConfig'

const ragStore = useRagConfigStore()

const initialLoading = ref(true)
const savingEmbedding = ref(false)
const savingRag = ref(false)
const testingConnection = ref(false)
const pageError = ref('')
const saveSuccess = ref(false)
const testSuccess = ref(false)
const testError = ref('')

const embedding = reactive({
  api_key: '',
  base_url: '',
  model_name: '',
  vector_dimension: null,
})

const rag = reactive({
  chunk_size: null,
  chunk_overlap: null,
  top_k: null,
  threshold_distance: null,
  query_buffer: null,
})

function showSuccess() {
  saveSuccess.value = true
  setTimeout(() => { saveSuccess.value = false }, 3000)
}

async function fetchConfigs() {
  initialLoading.value = true
  pageError.value = ''
  try {
    const [embedRes, ragRes] = await Promise.allSettled([
      ragStore.fetchEmbeddingConfig(),
      ragStore.fetchRAGConfig(),
    ])

    if (embedRes.status === 'fulfilled' && ragStore.embeddingConfig) {
      const ec = ragStore.embeddingConfig
      embedding.api_key = ec.api_key || ''
      embedding.base_url = ec.base_url || ''
      embedding.model_name = ec.model_name || ''
      embedding.vector_dimension = ec.vector_dimension ?? null
    }

    if (ragRes.status === 'fulfilled' && ragStore.ragConfig) {
      const rc = ragStore.ragConfig
      rag.chunk_size = rc.chunk_size ?? null
      rag.chunk_overlap = rc.chunk_overlap ?? null
      rag.top_k = rc.top_k ?? null
      rag.threshold_distance = rc.threshold_distance ?? null
      rag.query_buffer = rc.query_buffer ?? null
    }

    if (embedRes.status === 'rejected' && ragRes.status === 'rejected') {
      pageError.value = '加载配置失败，请检查网络连接'
    }
  } catch {
    pageError.value = '加载配置失败'
  } finally {
    initialLoading.value = false
  }
}

async function saveEmbeddingConfig() {
  savingEmbedding.value = true
  pageError.value = ''
  try {
    await ragStore.updateEmbeddingConfig({
      api_key: embedding.api_key,
      base_url: embedding.base_url,
      model_name: embedding.model_name,
      vector_dimension: embedding.vector_dimension,
    })
    showSuccess()
  } catch (e) {
    pageError.value = e.response?.data?.message || '保存嵌入配置失败'
  } finally {
    savingEmbedding.value = false
  }
}

async function testConnection() {
  testingConnection.value = true
  testSuccess.value = false
  testError.value = ''
  try {
    await ragStore.testEmbeddingConnection({
      api_key: embedding.api_key,
      base_url: embedding.base_url,
      model_name: embedding.model_name,
    })
    testSuccess.value = true
    setTimeout(() => { testSuccess.value = false }, 3000)
  } catch (e) {
    testError.value = e.response?.data?.message || '连接测试失败'
    setTimeout(() => { testError.value = '' }, 3000)
  } finally {
    testingConnection.value = false
  }
}

async function saveRAGConfig() {
  savingRag.value = true
  pageError.value = ''
  try {
    await ragStore.updateRAGConfig({
      chunk_size: rag.chunk_size,
      chunk_overlap: rag.chunk_overlap,
      top_k: rag.top_k,
      threshold_distance: rag.threshold_distance,
      query_buffer: rag.query_buffer,
    })
    showSuccess()
  } catch (e) {
    pageError.value = e.response?.data?.message || '保存检索配置失败'
  } finally {
    savingRag.value = false
  }
}

onMounted(fetchConfigs)
</script>

<style scoped>
.settings-section {
  margin-bottom: 1.25rem;
}

.settings-card {
  cursor: default;
}

.settings-card-header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
}

.settings-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: var(--primary);
  flex-shrink: 0;
}

.settings-card-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text);
}

.settings-card-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.settings-card-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.5rem;
}

.test-connection-status {
  flex: 1;
  min-width: 0;
}

.test-msg {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 500;
}

.test-msg-success {
  color: var(--success);
}

.test-msg-error {
  color: var(--danger);
}

.settings-field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.settings-field .form-label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
}

/* Skeleton loading */
.skeleton-line {
  border-radius: var(--radius);
  background: linear-gradient(90deg, var(--border) 25%, var(--bg) 50%, var(--border) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton-line-title {
  border-radius: 4px;
}
.skeleton-line-label {
  border-radius: 4px;
  height: 0.75rem;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-line { animation: none; }
}

@media (max-width: 640px) {
  .settings-card-header {
    padding: 0.75rem 1rem;
  }
  .settings-card-body {
    padding: 1rem;
  }
  .settings-card-footer {
    padding: 0.625rem 1rem;
  }
}
</style>
