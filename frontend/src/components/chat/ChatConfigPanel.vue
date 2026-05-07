<template>
  <div class="chat-config-panel">
    <div class="config-summary" @click="expanded = !expanded">
      <div class="config-summary-text">
        <span v-if="config" class="config-ok">
          当前配置：{{ config.provider }} / {{ config.model }}
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
        <select v-model="form.provider" class="form-control">
          <option value="siliconflow">SiliconFlow</option>
          <option value="deepseek">DeepSeek</option>
        </select>
      </div>
      <div class="form-row">
        <label>API Key</label>
        <input v-model="form.api_key" type="password" class="form-control" placeholder="sk-..." />
      </div>
      <div class="form-row">
        <label>Base URL</label>
        <input v-model="form.base_url" type="text" class="form-control" placeholder="https://api.example.com/v1" />
      </div>
      <div class="form-row">
        <label>Model</label>
        <input v-model="form.model" type="text" class="form-control" placeholder="例如 deepseek-chat" />
      </div>
      <div class="form-actions">
        <button class="btn btn-sm btn-primary" @click="handleSave" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button class="btn btn-sm" @click="handleCancel">取消</button>
        <button v-if="config" class="btn btn-sm btn-danger" @click="handleDelete">清除配置</button>
      </div>
      <div v-if="error" class="config-error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  config: { type: Object, default: null },
})
const emit = defineEmits(['save', 'cancel', 'delete'])

const expanded = ref(false)
const saving = ref(false)
const error = ref('')
const form = ref({
  provider: 'siliconflow',
  api_key: '',
  base_url: '',
  model: '',
})

watch(() => props.config, (cfg) => {
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
  saving.value = true
  emit('save', { ...form.value }, () => {
    saving.value = false
    expanded.value = false
  })
}

function handleCancel() {
  expanded.value = false
  error.value = ''
  emit('cancel')
}

function handleDelete() {
  if (confirm('确定清除当前 API 配置吗？')) {
    emit('delete')
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
.form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
}
.config-error {
  font-size: 0.8125rem;
  color: var(--danger);
}
@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
