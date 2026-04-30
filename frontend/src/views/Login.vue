<template>
  <div class="login-wrapper">
    <div class="login-card card">
      <div class="login-header">
        <h1 class="login-title">📚 BoKe</h1>
        <p class="login-subtitle">个人研究资料库</p>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label" for="username">用户名</label>
          <input
            id="username"
            v-model="username"
            class="input"
            type="text"
            autocomplete="username"
            required
            autofocus
          />
        </div>
        <div class="form-group">
          <label class="form-label" for="password">密码</label>
          <input
            id="password"
            v-model="password"
            class="input"
            type="password"
            autocomplete="current-password"
            required
          />
        </div>
        <button class="btn btn-primary" style="width:100%;" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  loading.value = true
  error.value = ''
  try {
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    const msg = e.response?.data?.message || '登录失败'
    if (e.response?.data?.code === 4030) {
      error.value = '账户已锁定，请稍后再试'
    } else {
      error.value = msg
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}
.login-card {
  width: 100%;
  max-width: 380px;
  padding: 2rem;
}
.login-header {
  text-align: center;
  margin-bottom: 1.75rem;
}
.login-title {
  font-size: 1.75rem;
  font-weight: 800;
  margin-bottom: 0.25rem;
}
.login-subtitle {
  color: var(--text-secondary);
  font-size: 0.875rem;
}
</style>
