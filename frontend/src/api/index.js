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

// Response interceptor: handle 401 → redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

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

// --- Files ---
export const getFileUrl = (docId, type = 'original') =>
  `/api/v1/files/${docId}/${type}`

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
