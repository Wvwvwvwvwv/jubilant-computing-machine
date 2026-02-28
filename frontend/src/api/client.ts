import axios from 'axios'


export function extractApiError(error: any): string {
  const status = error?.response?.status
  const detail = error?.response?.data?.detail

  if (detail && typeof detail === 'string') return detail
  if (status === 503) return 'Сервис временно недоступен. Проверьте запуск backend/embeddings.'
  if (status === 504 || error?.code === 'ECONNABORTED') return 'Превышен таймаут ответа сервера.'
  if (!error?.response) return 'Ошибка соединения с сервером.'

  return `Ошибка API (${status ?? 'unknown'})`
}


const api = axios.create({
  baseURL: '/api',
  timeout: 120000
})

export const chatAPI = {
  send: async (messages: any[], useMemory: boolean = true) => {
    const { data } = await api.post('/chat', {
      messages,
      use_memory: useMemory
    })
    return data
  },

  feedback: async (interactionId: string, helpful: boolean) => {
    const { data } = await api.post('/chat/feedback', null, {
      params: { interaction_id: interactionId, helpful }
    })
    return data
  }
}

export const memoryAPI = {
  search: async (query: string, limit: number = 10) => {
    const { data } = await api.post('/memory/search', { query, limit })
    return data
  },

  add: async (content: string, metadata?: any) => {
    const { data } = await api.post('/memory/add', { content, metadata })
    return data
  },

  stats: async () => {
    const { data } = await api.get('/memory/stats')
    return data
  }
}

export const booksAPI = {
  list: async () => {
    const { data } = await api.get('/books/list')
    return data
  },

  upload: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post('/books/upload', formData)
    return data
  },

  delete: async (bookId: string) => {
    const { data } = await api.delete(`/books/${bookId}`)
    return data
  }
}

export const sandboxAPI = {
  execute: async (code: string, language: string = 'python', timeout: number = 30) => {
    const { data } = await api.post('/sandbox/execute', {
      code,
      language,
      timeout
    })
    return data
  },

  list: async () => {
    const { data } = await api.get('/sandbox/list')
    return data
  }
}

export default api
