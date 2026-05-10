import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// Request interceptor: attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- Refresh lock to prevent concurrent refresh races ---
let refreshPromise = null

function doRefresh() {
  if (!refreshPromise) {
    const rt = localStorage.getItem('refresh_token')
    if (!rt) {
      return Promise.reject(new Error('No refresh token'))
    }
    refreshPromise = axios
      .post('/api/v1/auth/refresh', { refresh_token: rt })
      .then((res) => {
        const data = res.data.data
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        // Notify the auth store to sync its reactive state
        window.dispatchEvent(new CustomEvent('auth:token-refreshed', { detail: data }))
        return data.access_token
      })
      .catch((err) => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        throw err
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

// Response interceptor: handle 401 → attempt refresh, then retry
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const newToken = await doRefresh()
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        if (window.location.pathname !== '/login') {
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    }
    return Promise.reject(error)
  }
)

// --- Blob URL cache (revoked on logout or page unload) ---
const blobCache = new Map()

export function revokeAllBlobUrls() {
  for (const url of blobCache.values()) URL.revokeObjectURL(url)
  blobCache.clear()
}

export function revokeBlobUrlFromCache(docId, type = 'original') {
  const cacheKey = `${docId}:${type}`
  const url = blobCache.get(cacheKey)
  if (url) {
    URL.revokeObjectURL(url)
    blobCache.delete(cacheKey)
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', revokeAllBlobUrls)
}

/**
 * Fetch a file via authenticated axios and return a blob URL.
 * Cached so the same doc+type is only fetched once per session.
 */
export async function fetchFileBlobUrl(docId, type = 'original') {
  const cacheKey = `${docId}:${type}`
  if (blobCache.has(cacheKey)) return blobCache.get(cacheKey)

  // Append a cache-buster query (?_t=...) to avoid browser disk cache returning a 0-byte Blob for XHR blob response
  const res = await api.get(`/files/${docId}/${type}?_t=${Date.now()}`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data)
  blobCache.set(cacheKey, url)
  return url
}

// --- Auth ---
export const login = (username, password) =>
  api.post('/auth/login', { username, password })

export const refreshToken = (refresh_token) =>
  api.post('/auth/refresh', { refresh_token })

export const logout = (refresh_token) =>
  api.post('/auth/logout', { refresh_token })

// --- Documents ---
export const getDocuments = (params) =>
  api.get('/documents', { params })

export const getDocumentTimeline = (params) =>
  api.get('/documents/timeline', { params })

export const getDocument = (id) =>
  api.get(`/documents/${id}`)

export const uploadDocument = (formData, onProgress) =>
  api.post('/documents', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  })

export const updateDocument = (id, data) =>
  api.patch(`/documents/${id}`, data)

export const deleteDocument = (id) =>
  api.delete(`/documents/${id}`)

export const retryDocument = (id) =>
  api.post(`/documents/${id}/retry`)

export const reprocessDocument = (id) =>
  api.post(`/documents/${id}/reprocess`)

export const toggleFavorite = (id) =>
  api.patch(`/documents/${id}/favorite`)

export const setCategory = (id, category) =>
  api.patch(`/documents/${id}/category`, { category })

export const getCategories = () =>
  api.get('/documents/categories')

// --- Search ---
export const searchDocuments = (params) =>
  api.get('/documents/search', { params })

// --- API Keys ---
export const getApiKeys = () =>
  api.get('/api-keys')

export const createApiKey = (data) =>
  api.post('/api-keys', data)

export const deleteApiKey = (id) =>
  api.delete(`/api-keys/${id}`)

// --- Placeholders ---
export const getChatStatus = () =>
  api.get('/chat/')

export const getMilvusStatus = () =>
  api.get('/milvus/status')

// --- Health ---
export const getHealth = () =>
  api.get('/health')

// --- Dashboard ---
export const getDashboardStats = () =>
  api.get('/dashboard/stats')

export const getDashboardRecent = (params) =>
  api.get('/dashboard/recent', { params })

export const getDashboardTop = (params) =>
  api.get('/dashboard/top', { params })

export const getDashboardActivity = (params) =>
  api.get('/dashboard/activity', { params })

// --- Profile ---
export const getProfile = () =>
  api.get('/profile')

export const updateProfile = (data) =>
  api.put('/profile', data)

export const uploadAvatar = (formData) =>
  api.post('/profile/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const deleteAvatar = () =>
  api.delete('/profile/avatar')

export const uploadBackground = (formData) =>
  api.post('/profile/background', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const deleteBackground = () =>
  api.delete('/profile/background')

// --- Multi-backgrounds ---
export const getBackgrounds = () =>
  api.get('/profile/backgrounds')

export const uploadBackgroundMulti = (formData) =>
  api.post('/profile/backgrounds', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const deleteBackgroundMulti = (id) =>
  api.delete(`/profile/backgrounds/${id}`)

export const reorderBackgrounds = (backgroundIds) =>
  api.put('/profile/backgrounds/reorder', { background_ids: backgroundIds })

export function getBackgroundUrlById(bgId, token, hash = '') {
  let url = `/api/v1/files/profile/backgrounds/${bgId}?token=${encodeURIComponent(token)}`
  if (hash) {
    url += `&v=${encodeURIComponent(hash)}`
  }
  return url
}

export function getAvatarUrl(token) {
  return `/api/v1/files/profile/avatar?token=${encodeURIComponent(token)}`
}

export function getBackgroundUrl(token) {
  return `/api/v1/files/profile/background?token=${encodeURIComponent(token)}`
}

// --- LLM Config ---
export const getLLMConfigs = () => api.get('/llm-config')
export const getActiveLLMConfig = () => api.get('/llm-config/active')
export const saveLLMConfig = (data) => api.post('/llm-config', data)
export const activateLLMProvider = (provider) => api.post(`/llm-config/${provider}/activate`)
export const deleteLLMConfig = (provider) => api.delete(`/llm-config/${provider}`)

// --- Chat Sessions ---
export const getChatSessions = () => api.get('/chat-sessions')
export const createChatSession = (data) => api.post('/chat-sessions', data)
export const updateChatSession = (sessionId, data) => api.patch(`/chat-sessions/${sessionId}`, data)
export const deleteChatSession = (sessionId) => api.delete(`/chat-sessions/${sessionId}`)

// --- Chat Messages ---
export const getChatMessages = (sessionId) => api.get(`/chat/messages/${sessionId}`)

export async function sendChatMessage(sessionId, content, onEvent) {
  const token = localStorage.getItem('access_token')
  const response = await fetch(`/api/v1/chat/messages/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ message: 'Request failed' }))
    throw new Error(err.message || 'Request failed')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6)
        if (jsonStr) {
          try {
            const event = JSON.parse(jsonStr)
            onEvent(event)
            if (event.type === 'error') throw new Error(event.message)
          } catch (e) {
            if (e.message !== jsonStr) throw e
          }
        }
      }
    }
  }
}

/**
 * Get authenticated URL for a DOCX extracted image.
 * Uses the cached JWT token from localStorage.
 */
export function getDocxImageUrl(docId, imageIndex) {
  const token = localStorage.getItem('access_token') || ''
  const baseUrl = api.defaults.baseURL || '/api/v1'
  return `${baseUrl}/files/${docId}/docx_images/${imageIndex}?token=${encodeURIComponent(token)}`
}

export default api
