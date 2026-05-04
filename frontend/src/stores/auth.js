import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, logout as apiLogout, refreshToken as apiRefresh, revokeAllBlobUrls, getProfile, getBackgrounds } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshTokenVal = ref(localStorage.getItem('refresh_token') || '')
  const userProfile = ref(JSON.parse(localStorage.getItem('user_profile') || 'null'))

  const isAuthenticated = computed(() => !!accessToken.value)

  const avatarUrl = computed(() => {
    if (!userProfile.value?.avatar_path || !accessToken.value) return null
    return `/api/v1/files/profile/avatar?token=${encodeURIComponent(accessToken.value)}`
  })

  const backgroundUrl = computed(() => {
    if (!userProfile.value?.background_path || !accessToken.value) return null
    return `/api/v1/files/profile/background?token=${encodeURIComponent(accessToken.value)}`
  })

  const backgroundOpacity = computed(() => userProfile.value?.background_opacity ?? 0.3)

  const backgrounds = ref(JSON.parse(localStorage.getItem('user_backgrounds') || '[]'))
  const carouselInterval = computed(() => userProfile.value?.carousel_interval ?? 5)

  const backgroundUrls = computed(() => {
    if (!accessToken.value) return []
    return backgrounds.value.map(bg =>
      `/api/v1/files/profile/backgrounds/${bg.id}?token=${encodeURIComponent(accessToken.value)}`
    )
  })

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
    if (data.user) {
      userProfile.value = data.user
      localStorage.setItem('user_profile', JSON.stringify(data.user))
    }
    await fetchBackgrounds()
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

  async function fetchProfile() {
    try {
      const res = await getProfile()
      const profile = res.data.data
      updateProfileInStore(profile)
      await fetchBackgrounds()
      return profile
    } catch {
      return null
    }
  }

  async function fetchBackgrounds() {
    try {
      const res = await getBackgrounds()
      backgrounds.value = res.data.data
      localStorage.setItem('user_backgrounds', JSON.stringify(backgrounds.value))
      return backgrounds.value
    } catch {
      return []
    }
  }

  function updateProfileInStore(profile) {
    userProfile.value = profile
    localStorage.setItem('user_profile', JSON.stringify(profile))
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
    userProfile.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_profile')
    backgrounds.value = []
    localStorage.removeItem('user_backgrounds')
    revokeAllBlobUrls()
  }

  return {
    accessToken,
    refreshToken: refreshTokenVal,
    isAuthenticated,
    userProfile,
    avatarUrl,
    backgroundUrl,
    backgroundOpacity,
    backgrounds,
    backgroundUrls,
    carouselInterval,
    login,
    refresh,
    logout,
    fetchProfile,
    fetchBackgrounds,
    updateProfileInStore,
  }
})
