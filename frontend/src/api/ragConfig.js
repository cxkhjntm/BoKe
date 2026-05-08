import api from './index'

export const getEmbeddingConfig = () =>
  api.get('/rag/embedding-config')

export const updateEmbeddingConfig = (data) =>
  api.post('/rag/embedding-config', data)

export const getRAGConfig = () =>
  api.get('/rag/config')

export const updateRAGConfig = (data) =>
  api.post('/rag/config', data)

export const testEmbeddingConnection = (data) =>
  api.post('/rag/test-connection', data)
