import { useRef, useState } from 'react'
import { Send, ThumbsUp, ThumbsDown } from 'lucide-react'
import { chatAPI } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  id?: string
}

interface ChatDraftState {
  messages: Message[]
  useMemory: boolean
}

const CHAT_MESSAGES_KEY = 'chat_messages'
const CHAT_USE_MEMORY_KEY = 'chat_use_memory'

// In-memory fallback: survives route unmount/mount even if storage is unavailable.
let chatDraftState: ChatDraftState | null = null

function loadMessages(): Message[] {
  if (chatDraftState) {
    return chatDraftState.messages
  }

  try {
    const saved = localStorage.getItem(CHAT_MESSAGES_KEY)
    const parsed = saved ? JSON.parse(saved) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function loadUseMemory(): boolean {
  if (chatDraftState) {
    return chatDraftState.useMemory
  }

  try {
    const saved = localStorage.getItem(CHAT_USE_MEMORY_KEY)
    return saved ? Boolean(JSON.parse(saved)) : true
  } catch {
    return true
  }
}

function persistState(messages: Message[], useMemory: boolean) {
  chatDraftState = { messages, useMemory }

  try {
    localStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(messages))
    localStorage.setItem(CHAT_USE_MEMORY_KEY, JSON.stringify(useMemory))
  } catch {
    // ignore storage errors (quota/private mode)
  }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>(loadMessages)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [useMemory, setUseMemory] = useState<boolean>(loadUseMemory)

  const messagesRef = useRef(messages)
  const useMemoryRef = useRef(useMemory)

  const updateMessages = (next: Message[] | ((prev: Message[]) => Message[])) => {
    setMessages(prev => {
      const computed = typeof next === 'function' ? (next as (p: Message[]) => Message[])(prev) : next
      messagesRef.current = computed
      persistState(computed, useMemoryRef.current)
      return computed
    })
  }

  const updateUseMemory = (next: boolean) => {
    useMemoryRef.current = next
    setUseMemory(next)
    persistState(messagesRef.current, next)
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = { role: 'user', content: input }
    const nextMessages = [...messagesRef.current, userMessage]

    updateMessages(nextMessages)
    setInput('')
    setLoading(true)

    try {
      const response = await chatAPI.send(nextMessages, useMemoryRef.current)

      updateMessages(prev => [...prev, {
        role: 'assistant',
        content: response.response,
        id: response.interaction_id
      }])
    } catch (error: any) {
      console.error('Chat error:', error)
      const detail = error?.response?.data?.detail
      updateMessages(prev => [...prev, {
        role: 'assistant',
        content: detail ? `❌ ${detail}` : '❌ Ошибка соединения с сервером'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (messageId: string, helpful: boolean) => {
    try {
      await chatAPI.feedback(messageId, helpful)
    } catch (error) {
      console.error('Feedback error:', error)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '80%'
            }}
          >
            <div style={{
              background: msg.role === 'user' ? '#3b82f6' : '#1f1f1f',
              padding: '0.75rem 1rem',
              borderRadius: '1rem',
              wordWrap: 'break-word'
            }}>
              {msg.content}
            </div>

            {msg.role === 'assistant' && msg.id && (
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                marginTop: '0.5rem',
                fontSize: '0.875rem'
              }}>
                <button
                  onClick={() => handleFeedback(msg.id!, true)}
                  style={{
                    background: 'transparent',
                    border: '1px solid #333',
                    borderRadius: '0.5rem',
                    padding: '0.25rem 0.5rem',
                    color: '#888',
                    cursor: 'pointer'
                  }}
                >
                  <ThumbsUp size={14} />
                </button>
                <button
                  onClick={() => handleFeedback(msg.id!, false)}
                  style={{
                    background: 'transparent',
                    border: '1px solid #333',
                    borderRadius: '0.5rem',
                    padding: '0.25rem 0.5rem',
                    color: '#888',
                    cursor: 'pointer'
                  }}
                >
                  <ThumbsDown size={14} />
                </button>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ alignSelf: 'flex-start' }}>
            <div style={{
              background: '#1f1f1f',
              padding: '0.75rem 1rem',
              borderRadius: '1rem'
            }}>
              Думаю...
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{
        padding: '1rem',
        borderTop: '1px solid #222',
        display: 'flex',
        gap: '0.5rem',
        alignItems: 'center'
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
          <input
            type="checkbox"
            checked={useMemory}
            onChange={(e) => updateUseMemory(e.target.checked)}
          />
          Память
        </label>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Сообщение..."
          style={{
            flex: 1,
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '1.5rem',
            padding: '0.75rem 1rem',
            color: '#fff',
            outline: 'none'
          }}
        />

        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          style={{
            background: '#3b82f6',
            border: 'none',
            borderRadius: '50%',
            width: '3rem',
            height: '3rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.5 : 1
          }}
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  )
}
