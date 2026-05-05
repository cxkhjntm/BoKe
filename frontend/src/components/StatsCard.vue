<template>
  <div class="card stats-card">
    <div class="stats-icon">
      <component :is="icon" v-if="typeof icon === 'object' || typeof icon === 'function'" :size="32" :stroke-width="1.5" class="text-primary" />
      <span v-else>{{ icon }}</span>
    </div>
    <div class="stats-body">
      <div v-if="loading" class="skeleton-line" style="width: 60px; height: 1.5rem; margin-bottom: 0.125rem;"></div>
      <div v-else class="stats-value">{{ displayValue }}</div>
      <div class="stats-label">{{ label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  icon: { type: [String, Object, Function], default: '' },
  value: { type: [Number, String], default: 0 },
  label: { type: String, default: '' },
  format: { type: String, default: 'number' },
  loading: { type: Boolean, default: false }
})

const displayValue = computed(() => {
  if (props.format === 'size') return formatBytes(props.value)
  return props.value
})

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}
</script>

<style scoped>
.stats-card {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 1.125rem 1.375rem;
}
.stats-icon {
  font-size: 1.75rem;
  flex-shrink: 0;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), rgba(37, 99, 235, 0.04));
}
.stats-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.stats-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin-top: 0.125rem;
}
</style>
