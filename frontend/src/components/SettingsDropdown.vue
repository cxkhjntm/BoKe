<template>
  <div class="settings-dropdown" ref="dropdownRef">
    <button class="settings-trigger" @click="open = !open" aria-label="设置">
      <img v-if="authStore.avatarUrl" :src="authStore.avatarUrl" class="trigger-avatar" alt="头像" />
      <svg v-else class="trigger-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21v-1a6 6 0 0 1 12 0v1" />
      </svg>
    </button>
    <transition name="dropdown">
      <div v-if="open" class="dropdown-menu">
        <div class="dropdown-user">
          <img v-if="authStore.avatarUrl" :src="authStore.avatarUrl" class="dropdown-avatar" alt="头像" />
          <div v-else class="dropdown-avatar-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21v-1a6 6 0 0 1 12 0v1" />
            </svg>
          </div>
          <span class="dropdown-username">{{ username }}</span>
        </div>
        <div class="dropdown-divider"></div>
        <button class="dropdown-item" @click="openSettings">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          个人设置
        </button>
        <button class="dropdown-item dropdown-item-danger" @click="handleLogout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
          退出登录
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const emit = defineEmits(['open-settings'])
const router = useRouter()
const authStore = useAuthStore()
const open = ref(false)
const dropdownRef = ref(null)

const username = computed(() => authStore.userProfile?.username || '用户')

function openSettings() {
  open.value = false
  emit('open-settings')
}

async function handleLogout() {
  open.value = false
  await authStore.logout()
  router.push('/login')
}

function handleClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
.settings-dropdown {
  position: relative;
}

.settings-trigger {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--bg-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  overflow: hidden;
  transition: border-color var(--transition-fast);
}

.settings-trigger:hover {
  border-color: var(--primary);
}

.trigger-avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.trigger-icon {
  width: 1.125rem;
  height: 1.125rem;
  color: var(--text-secondary);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  min-width: 10rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--elevation-3);
  padding: 0.375rem 0;
  z-index: 200;
}

.dropdown-user {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
}

.dropdown-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  object-fit: cover;
}

.dropdown-avatar-placeholder {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.dropdown-avatar-placeholder svg {
  width: 1.125rem;
  height: 1.125rem;
}

.dropdown-username {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text);
}

.dropdown-divider {
  height: 1px;
  background: var(--border);
  margin: 0.25rem 0;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: none;
  background: none;
  font-size: 0.8125rem;
  color: var(--text);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.dropdown-item:hover {
  background: var(--bg);
}

.dropdown-item svg {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

.dropdown-item-danger {
  color: var(--danger);
}

.dropdown-item-danger:hover {
  background: var(--status-error-bg);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 150ms ease, transform 150ms ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
