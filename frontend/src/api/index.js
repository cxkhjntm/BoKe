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

  const res = await api.get(`/files/${docId}/${type}`, { responseType: 'blob' })
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

export default api
