import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, logout as apiLogout, refreshToken as apiRefresh, revokeAllBlobUrls } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshTokenVal = ref(localStorage.getItem('refresh_token') || '')

  const isAuthenticated = computed(() => !!accessToken.value)

  // Sync reactive state when the API interceptor refreshes tokens
  if (typeof window !== 'undefined') {
    window.addEventListener('auth:token-refreshed', (e) => {
      accessToken.value = e.detail.access_token
      refreshTokenVal.value = e.detail.refresh_token
    })
  }

  async function login(username, password) {
    const res = await apiLogin(username, password)
    const data = res.data.data
    accessToken.value = data.access_token
    refreshTokenVal.value = data.refresh_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return data
  }

  async function refresh() {
    if (!refreshTokenVal.value) throw new Error('No refresh token')
    const res = await apiRefresh(refreshTokenVal.value)
    const data = res.data.data
    accessToken.value = data.access_token
    refreshTokenVal.value = data.refresh_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    return data
  }

  async function logout() {
    try {
      if (refreshTokenVal.value) {
        await apiLogout(refreshTokenVal.value)
      }
    } catch {
      // Ignore logout errors
    }
    accessToken.value = ''
    refreshTokenVal.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    revokeAllBlobUrls()
  }

  return { accessToken, refreshToken: refreshTokenVal, isAuthenticated, login, refresh, logout }
})
