import { useEffect, useMemo, useState } from 'react'
import { tasksAPI } from '../api/client'

interface TaskEvent {
  ts: number
  kind: string
  message: string
  payload: Record<string, unknown>
}

interface TaskItem {
  task_id: string
  goal: string
  status: string
  attempt: number
  max_attempts: number
  created_at?: number
  updated_at?: number
  last_error?: string | null
  error_class?: string | null
  approval_required: boolean
  approved: boolean
  events: TaskEvent[]
}

const TERMINAL_STATUSES = new Set(['SUCCESS', 'FAILED'])

const statusColor = (status: string) => {
  if (status === 'SUCCESS') return '#4ade80'
  if (status === 'FAILED') return '#f87171'
  if (status === 'NEEDS_APPROVAL') return '#fbbf24'
  if (status === 'RETRYING') return '#f59e0b'
  if (status === 'RUNNING') return '#60a5fa'
  return '#d1d5db'
}

export default function TasksPage() {
  const [goal, setGoal] = useState('echo "hello from tasks"')
  const [maxAttempts, setMaxAttempts] = useState(3)
  const [approvalRequired, setApprovalRequired] = useState(false)
  const [items, setItems] = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [statusFilter, setStatusFilter] = useState('ALL')

  const load = async (silent = false) => {
    if (!silent) {
      setLoading(true)
      setError('')
    }
    try {
      const data = await tasksAPI.list(50)
      setItems(data.items || [])
    } catch (e: any) {
      if (!silent) {
        setError(e?.response?.data?.detail || e?.message || 'Ошибка загрузки задач')
      }
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const t = setInterval(() => {
      void load(true)
    }, 3000)
    return () => clearInterval(t)
  }, [autoRefresh])

  const createTask = async () => {
    if (!goal.trim()) return
    setLoading(true)
    setError('')
    try {
      await tasksAPI.create(goal, maxAttempts, approvalRequired)
      setGoal('')
      await load(true)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Ошибка создания задачи')
    } finally {
      setLoading(false)
    }
  }

  const runTask = async (taskId: string) => {
    setLoading(true)
    setError('')
    try {
      await tasksAPI.run(taskId)
      await load(true)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Ошибка запуска задачи')
    } finally {
      setLoading(false)
    }
  }

  const approveTask = async (taskId: string) => {
    setLoading(true)
    setError('')
    try {
      await tasksAPI.approve(taskId)
      await load(true)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Ошибка approve')
    } finally {
      setLoading(false)
    }
  }

  const filteredItems = useMemo(() => {
    if (statusFilter === 'ALL') return items
    return items.filter((task) => task.status === statusFilter)
  }, [items, statusFilter])

  const statusOptions = useMemo(() => {
    const set = new Set(items.map((x) => x.status))
    return ['ALL', ...Array.from(set)]
  }, [items])

  return (
    <div style={{ padding: '1rem', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ marginBottom: '1rem' }}>Задачи агента</h2>

      <div style={{ display: 'grid', gap: '0.5rem', marginBottom: '1rem' }}>
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="Опиши команду/цель задачи"
          style={{
            minHeight: '90px',
            background: '#1a1a1a',
            color: '#fff',
            border: '1px solid #333',
            borderRadius: '0.5rem',
            padding: '0.75rem'
          }}
        />

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <label>
            Max attempts:{' '}
            <input
              type="number"
              min={1}
              max={10}
              value={maxAttempts}
              onChange={(e) => setMaxAttempts(Number(e.target.value))}
              style={{ width: '70px' }}
            />
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <input
              type="checkbox"
              checked={approvalRequired}
              onChange={(e) => setApprovalRequired(e.target.checked)}
            />
            Требовать approve
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
            Auto-refresh (3s)
          </label>

          <label>
            Фильтр:{' '}
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>

          <button onClick={() => void createTask()} disabled={loading}>
            Создать задачу
          </button>
          <button onClick={() => void load()} disabled={loading}>
            Обновить
          </button>
        </div>
      </div>

      {error && <div style={{ color: '#f87171', marginBottom: '1rem' }}>❌ {error}</div>}

      <div style={{ display: 'grid', gap: '0.75rem' }}>
        {filteredItems.map((task) => {
          const canRun = !TERMINAL_STATUSES.has(task.status)
          const canApprove = task.approval_required && !task.approved
          const lastEvent = task.events?.[task.events.length - 1]

          return (
            <div
              key={task.task_id}
              style={{ border: '1px solid #333', borderRadius: '0.5rem', padding: '0.75rem' }}
            >
              <div>
                <b>ID:</b> {task.task_id}
              </div>
              <div>
                <b>Goal:</b> {task.goal}
              </div>
              <div>
                <b>Status:</b>{' '}
                <span style={{ color: statusColor(task.status), fontWeight: 700 }}>{task.status}</span>
              </div>
              <div>
                <b>Attempts:</b> {task.attempt}/{task.max_attempts}
              </div>
              <div>
                <b>Approval:</b> {String(task.approval_required)} / approved={String(task.approved)}
              </div>
              {task.updated_at && (
                <div>
                  <b>Updated:</b> {new Date(task.updated_at * 1000).toLocaleString()}
                </div>
              )}
              {task.error_class && (
                <div>
                  <b>Error class:</b> {task.error_class}
                </div>
              )}
              {task.last_error && (
                <div style={{ color: '#fca5a5' }}>
                  <b>Last error:</b> {task.last_error}
                </div>
              )}

              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button onClick={() => void runTask(task.task_id)} disabled={loading || !canRun}>
                  Run
                </button>
                <button onClick={() => void approveTask(task.task_id)} disabled={loading || !canApprove}>
                  Approve
                </button>
              </div>

              {lastEvent && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: '#a3a3a3' }}>
                  <b>Последнее событие:</b> [{new Date(lastEvent.ts * 1000).toLocaleTimeString()}]{' '}
                  {lastEvent.kind} — {lastEvent.message}
                  {Object.keys(lastEvent.payload || {}).length > 0 && (
                    <pre
                      style={{
                        marginTop: '0.35rem',
                        background: '#111',
                        border: '1px solid #333',
                        borderRadius: '0.35rem',
                        padding: '0.5rem',
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {JSON.stringify(lastEvent.payload, null, 2)}
                    </pre>
                  )}
                </div>
              )}

              {task.events?.length > 0 && (
                <details style={{ marginTop: '0.5rem' }}>
                  <summary>События ({task.events.length})</summary>
                  <ul style={{ marginTop: '0.5rem' }}>
                    {task.events
                      .slice(-12)
                      .reverse()
                      .map((event, idx) => (
                        <li key={idx}>
                          [{new Date(event.ts * 1000).toLocaleTimeString()}] <b>{event.kind}</b>:{' '}
                          {event.message}
                        </li>
                      ))}
                  </ul>
                </details>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
