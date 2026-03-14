import { useState } from 'react'
import { voiceAPI } from '../api/client'

type GoNoGo = {
  voice_session_id: string
  decision: string
  checks: Record<string, boolean>
  failed_checks: string[]
  metrics: Record<string, number>
}

export default function VoicePage() {
  const [mode, setMode] = useState<'ptt' | 'duplex'>('ptt')
  const [voiceGender, setVoiceGender] = useState<'male' | 'female'>('female')
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [health, setHealth] = useState<any | null>(null)
  const [goNoGo, setGoNoGo] = useState<GoNoGo | null>(null)

  const isVoiceEnabled = Boolean(sessionId)

  const startSession = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await voiceAPI.startSession(mode, voiceGender)
      setSessionId(data.voice_session_id)
      setHealth(null)
      setGoNoGo(null)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось стартовать voice session')
    } finally {
      setLoading(false)
    }
  }

  const stopSession = async () => {
    if (!sessionId) return
    try {
      setLoading(true)
      setError(null)
      await voiceAPI.stopSession(sessionId)
      setSessionId('')
      setHealth(null)
      setGoNoGo(null)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось остановить voice session')
    } finally {
      setLoading(false)
    }
  }

  const toggleVoice = async () => {
    if (isVoiceEnabled) {
      await stopSession()
    } else {
      await startSession()
    }
  }

  const refresh = async () => {
    if (!sessionId) return
    try {
      setLoading(true)
      setError(null)
      const [h, g] = await Promise.all([
        voiceAPI.health(sessionId),
        voiceAPI.goNoGo(sessionId),
      ])
      setHealth(h)
      setGoNoGo(g)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось обновить voice статус')
    } finally {
      setLoading(false)
    }
  }

  const applyGoodMetrics = async () => {
    if (!sessionId) return
    try {
      setLoading(true)
      setError(null)
      await voiceAPI.updateMetrics(sessionId, {
        latency_p95_ms: 1800,
        crash_free_rate: 0.995,
        audio_loss_percent: 0.4,
        approval_bypass_incidents: 0,
        user_score: 4.4,
      })
      await refresh()
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось применить метрики')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '1rem', height: '100%', overflowY: 'auto' }}>
      <h2 style={{ marginBottom: '1rem' }}>Voice readiness</h2>

      {error && (
        <div style={{
          background: '#3b1d1d',
          border: '1px solid #7f1d1d',
          borderRadius: '0.5rem',
          padding: '0.75rem',
          marginBottom: '1rem',
          color: '#fecaca'
        }}>
          {error}
        </div>
      )}

      <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Session control</h3>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as 'ptt' | 'duplex')}
            disabled={loading || isVoiceEnabled}
            style={{ padding: '0.5rem', background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '0.5rem' }}
          >
            <option value="ptt">ptt</option>
            <option value="duplex">duplex</option>
          </select>

          <select
            value={voiceGender}
            onChange={(e) => setVoiceGender(e.target.value as 'male' | 'female')}
            disabled={loading || isVoiceEnabled}
            style={{ padding: '0.5rem', background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '0.5rem' }}
          >
            <option value="female">женский голос</option>
            <option value="male">мужской голос</option>
          </select>

          <button onClick={toggleVoice} disabled={loading} style={{ padding: '0.5rem 0.8rem' }}>
            {isVoiceEnabled ? 'Выключить голосовое общение' : 'Включить голосовое общение'}
          </button>

          <button onClick={refresh} disabled={loading || !sessionId} style={{ padding: '0.5rem 0.8rem' }}>Refresh</button>
          <button onClick={applyGoodMetrics} disabled={loading || !sessionId} style={{ padding: '0.5rem 0.8rem' }}>Apply MVP GO metrics</button>
        </div>
        <div style={{ marginTop: '0.75rem', color: '#aaa' }}>session_id: {sessionId || '—'}</div>
      </section>

      <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Health</h3>
        {!health ? <div style={{ color: '#aaa' }}>Нет данных.</div> : <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(health, null, 2)}</pre>}
      </section>

      <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Go / No-Go</h3>
        {!goNoGo ? (
          <div style={{ color: '#aaa' }}>Нет данных.</div>
        ) : (
          <>
            <div style={{ fontSize: '1.05rem', marginBottom: '0.5rem' }}>
              Decision: <strong style={{ color: goNoGo.decision === 'GO' ? '#22c55e' : '#ef4444' }}>{goNoGo.decision}</strong>
            </div>
            <div style={{ marginBottom: '0.5rem' }}>
              Failed checks: {goNoGo.failed_checks.length ? goNoGo.failed_checks.join(', ') : 'none'}
            </div>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(goNoGo, null, 2)}</pre>
          </>
        )}
      </section>
    </div>
  )
}
