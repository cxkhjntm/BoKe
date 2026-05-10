<template>
  <div class="chat-config-panel">
    <div class="config-summary" @click="expanded = !expanded">
      <div class="config-summary-text">
        <span v-if="activeConfig" class="config-ok">
          当前配置：{{ getProviderDisplayName(activeConfig.provider) }} / {{ activeConfig.model }}
        </span>
        <span v-else class="config-warn">
          未配置 API，点击展开设置
        </span>
      </div>
      <button class="btn btn-sm toggle-btn">
        {{ expanded ? '收起' : '展开' }}
      </button>
    </div>

    <div v-if="expanded" class="config-form">
      <div class="form-row">
        <label>Provider</label>
        <select v-model="form.provider" class="form-control" @change="onProviderChange">
          <option value="siliconflow">SiliconFlow</option>
          <option value="deepseek">DeepSeek</option>
          <optgroup v-if="customProviders.length > 0" label="自定义">
            <option v-for="cp in customProviders" :key="cp.id" :value="cp.id">
              {{ cp.name }}
            </option>
          </optgroup>
        </select>
        <button class="btn btn-sm btn-outline" @click="showAddForm = !showAddForm" :disabled="customProviders.length >= 8">
          {{ showAddForm ? '取消' : '+ 添加' }}
        </button>
      </div>

      <div v-if="showAddForm" class="custom-provider-form">
        <div class="form-row">
          <label>名称</label>
          <input v-model="newProvider.name" type="text" class="form-control" placeholder="例如：我的 OpenAI" />
        </div>
        <div class="form-row">
          <label>Base URL</label>
          <input v-model="newProvider.base_url" type="text" class="form-control" placeholder="https://api.openai.com/v1" />
        </div>
        <div class="form-actions">
          <button class="btn btn-sm btn-primary" @click="addCustomProvider" :disabled="!newProvider.name || !newProvider.base_url">
            确认添加
          </button>
        </div>
      </div>

      <div class="form-row">
        <label>API Key</label>
        <input v-model="form.api_key" type="password" class="form-control" placeholder="sk-..." />
      </div>
      <div class="form-row">
        <label>Base URL</label>
        <input v-model="form.base_url" type="text" class="form-control" placeholder="https://api.example.com/v1" :disabled="isFixedProvider" />
      </div>
      <div class="form-row">
        <label>Model</label>
        <input v-model="form.model" type="text" class="form-control" placeholder="例如 deepseek-chat" />
      </div>

      <div v-if="isCustomProvider" class="form-row">
        <label></label>
        <button class="btn btn-sm btn-danger" @click="removeCustomProvider(form.provider)">
          删除此自定义 Provider
        </button>
      </div>

      <div class="form-actions">
        <button class="btn btn-sm btn-primary" @click="handleSave" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button v-if="!isActive" class="btn btn-sm btn-success" @click="handleActivate">
          设为当前
        </button>
        <button class="btn btn-sm" @click="handleCancel">取消</button>
        <button v-if="currentConfig" class="btn btn-sm btn-danger" @click="handleDelete">删除配置</button>
      </div>
      <div v-if="error" class="config-error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const CUSTOM_PROVIDERS_KEY = 'boke_custom_llm_providers'
const MAX_CUSTOM_PROVIDERS = 8

const props = defineProps({
  configs: { type: Array, default: () => [] },
  activeConfig: { type: Object, default: null },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['save', 'cancel', 'delete', 'activate'])

const expanded = ref(false)
const error = ref('')
const showAddForm = ref(false)
const form = ref({
  provider: 'siliconflow',
  api_key: '',
  base_url: '',
  model: '',
})
const newProvider = ref({ name: '', base_url: '' })

const DEFAULT_BASE_URLS = {
  siliconflow: 'https://api.siliconflow.cn/v1',
  deepseek: 'https://api.deepseek.com/v1',
}

const FIXED_PROVIDERS = new Set(Object.keys(DEFAULT_BASE_URLS))

const isFixedProvider = computed(() => FIXED_PROVIDERS.has(form.value.provider))
const isCustomProvider = computed(() => !FIXED_PROVIDERS.has(form.value.provider))

const currentConfig = computed(() => {
  return props.configs.find(c => c.provider === form.value.provider)
})

const isActive = computed(() => {
  return props.activeConfig && props.activeConfig.provider === form.value.provider
})

const customProviders = ref(loadCustomProviders())

function loadCustomProviders() {
  try {
    const raw = localStorage.getItem(CUSTOM_PROVIDERS_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveCustomProviders(list) {
  localStorage.setItem(CUSTOM_PROVIDERS_KEY, JSON.stringify(list))
}

function getProviderDisplayName(provider) {
  if (provider === 'siliconflow') return 'SiliconFlow'
  if (provider === 'deepseek') return 'DeepSeek'
  const cp = customProviders.value.find(p => p.id === provider)
  return cp ? cp.name : provider
}

function addCustomProvider() {
  if (!newProvider.value.name.trim() || !newProvider.value.base_url.trim()) return
  if (customProviders.value.length >= MAX_CUSTOM_PROVIDERS) {
    error.value = `自定义 Provider 上限为 ${MAX_CUSTOM_PROVIDERS} 个`
    return
  }
  const id = 'custom_' + Date.now()
  const entry = { id, name: newProvider.value.name.trim(), base_url: newProvider.value.base_url.trim() }
  customProviders.value.push(entry)
  saveCustomProviders(customProviders.value)
  form.value.provider = id
  form.value.base_url = entry.base_url
  form.value.api_key = ''
  form.value.model = ''
  newProvider.value = { name: '', base_url: '' }
  showAddForm.value = false
}

function removeCustomProvider(id) {
  if (!confirm('确定删除此自定义 Provider？')) return
  customProviders.value = customProviders.value.filter(p => p.id !== id)
  saveCustomProviders(customProviders.value)
  emit('delete', id)
  form.value.provider = 'siliconflow'
  loadProviderConfig('siliconflow')
}

function onProviderChange() {
  loadProviderConfig(form.value.provider)
}

function loadProviderConfig(provider) {
  const config = props.configs.find(c => c.provider === provider)
  if (config) {
    form.value = {
      provider: config.provider,
      api_key: config.api_key,
      base_url: config.base_url,
      model: config.model,
    }
  } else {
    form.value = {
      provider: provider,
      api_key: '',
      base_url: DEFAULT_BASE_URLS[provider] || '',
      model: '',
    }
    if (!FIXED_PROVIDERS.has(provider)) {
      const cp = customProviders.value.find(p => p.id === provider)
      if (cp) form.value.base_url = cp.base_url
    }
  }
}

watch(() => props.activeConfig, (cfg) => {
  if (cfg) {
    form.value = {
      provider: cfg.provider || 'siliconflow',
      api_key: cfg.api_key || '',
      base_url: cfg.base_url || '',
      model: cfg.model || '',
    }
  } else {
    form.value = { provider: 'siliconflow', api_key: '', base_url: '', model: '' }
  }
}, { immediate: true })

function handleSave() {
  error.value = ''
  if (!form.value.api_key.trim()) {
    error.value = 'API Key 不能为空'
    return
  }
  if (!form.value.model.trim()) {
    error.value = 'Model 不能为空'
    return
  }
  emit('save', { ...form.value })
}

function handleActivate() {
  emit('activate', form.value.provider)
}

function handleCancel() {
  expanded.value = false
  error.value = ''
  emit('cancel')
}

function handleDelete() {
  if (confirm('确定删除当前 Provider 配置吗？')) {
    emit('delete', form.value.provider)
  }
}
</script>

<style scoped>
.chat-config-panel {
  background: var(--bg-card);
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border);
}
.config-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}
.config-summary-text {
  font-size: 0.8125rem;
}
.config-ok {
  color: var(--text-secondary);
}
.config-warn {
  color: var(--danger);
  font-weight: 500;
}
.toggle-btn {
  margin-left: 0.5rem;
}
.config-form {
  margin-top: 0.75rem;
  display: grid;
  gap: 0.625rem;
}
.form-row {
  display: grid;
  grid-template-columns: 80px 1fr;
  align-items: center;
  gap: 0.5rem;
}
.form-row label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
.form-control {
  padding: 0.375rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  background: var(--bg);
  color: var(--text);
  outline: none;
}
.form-control:focus {
  border-color: var(--primary);
}
.form-control:disabled {
  background: var(--bg-hover);
  color: var(--text-secondary);
  cursor: not-allowed;
  opacity: 0.7;
}
.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
}
.config-error {
  font-size: 0.8125rem;
  color: var(--danger);
}
.btn-success {
  background: var(--success);
  color: white;
}
.btn-success:hover {
  opacity: 0.9;
}
.custom-provider-form {
  background: var(--bg-hover);
  padding: 0.75rem;
  border-radius: var(--radius-sm);
  margin-top: 0.25rem;
}
.custom-provider-form .form-row {
  margin-bottom: 0.5rem;
}
.custom-provider-form .form-row:last-of-type {
  margin-bottom: 0;
}
.custom-provider-form .form-actions {
  margin-top: 0.5rem;
}
select optgroup {
  font-weight: bold;
  color: var(--text-secondary);
}
select option[value="__add_new__"] {
  color: var(--primary);
  font-style: italic;
}
@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
