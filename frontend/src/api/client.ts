import axios from 'axios'



export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    const status = error.response?.status

    if (typeof detail === 'string' && detail.trim()) {
      return `❌ ${detail}`
    }

    if (status) {
      return `❌ Ошибка API (${status})`
    }
  }

  return `❌ ${fallback}`
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


export const tasksAPI = {
  create: async (goal: string, maxAttempts: number = 3, approvalRequired: boolean = false) => {
    const { data } = await api.post('/tasks', {
      goal,
      max_attempts: maxAttempts,
      approval_required: approvalRequired
    })
    return data
  },

  get: async (taskId: string) => {
    const { data } = await api.get(`/tasks/${taskId}`)
    return data
  },

  list: async (limit: number = 50) => {
    const { data } = await api.get('/tasks', { params: { limit } })
    return data
  },

  run: async (taskId: string) => {
    const { data } = await api.post(`/tasks/${taskId}/run`)
    return data
  },

  approve: async (taskId: string) => {
    const { data } = await api.post(`/tasks/${taskId}/approve`)
    return data
  }
}

export default api
