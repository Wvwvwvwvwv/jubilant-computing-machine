import { useEffect, useRef, useState } from 'react'
import { voiceAPI } from '../api/client'

type GoNoGo = {
  voice_session_id: string
  decision: string
  checks: Record<string, boolean>
  failed_checks: string[]
  metrics: Record<string, number>
}

type MicProbeResult = {
  peakRms: number
  baselineRms: number
  hasSignal: boolean
}

const MIC_MIN_ABSOLUTE_RMS = 0.004
const MIC_RELATIVE_GAIN = 1.8
const VOICE_SESSION_KEY = 'voice_session_id'
const VOICE_MODE_KEY = 'voice_mode'
const VOICE_GENDER_KEY = 'voice_gender'

export default function VoicePage() {
  const [mode, setMode] = useState<'ptt' | 'duplex'>(() => {
    try {
      const raw = localStorage.getItem(VOICE_MODE_KEY)
      return raw === 'duplex' ? 'duplex' : 'ptt'
    } catch {
      return 'ptt'
    }
  })
  const [voiceGender, setVoiceGender] = useState<'male' | 'female'>(() => {
    try {
      const raw = localStorage.getItem(VOICE_GENDER_KEY)
      return raw === 'male' ? 'male' : 'female'
    } catch {
      return 'female'
    }
  })
  const [sessionId, setSessionId] = useState(() => {
    try {
      return localStorage.getItem(VOICE_SESSION_KEY) || ''
    } catch {
      return ''
    }
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [health, setHealth] = useState<any | null>(null)
  const [goNoGo, setGoNoGo] = useState<GoNoGo | null>(null)

  const [micStatus, setMicStatus] = useState<'idle' | 'connected' | 'error'>('idle')
  const [micError, setMicError] = useState<string | null>(null)
  const [micLabel, setMicLabel] = useState<string>('')
  const [micSignalRms, setMicSignalRms] = useState<number>(0)
  const micStreamRef = useRef<MediaStream | null>(null)

  const probeMicrophoneSignal = async (stream: MediaStream): Promise<MicProbeResult> => {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
    if (!AudioCtx) return { peakRms: 0, baselineRms: 0, hasSignal: false }
    const ctx = new AudioCtx()
    try {
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 2048
      source.connect(analyser)

      const data = new Uint8Array(analyser.fftSize)
      const started = performance.now()
      let peakRms = 0
      let baselineSum = 0
      let baselineCount = 0

      while (performance.now() - started < 900) {
        analyser.getByteTimeDomainData(data)
        let sum = 0
        for (let i = 0; i < data.length; i += 1) {
          const normalized = (data[i] - 128) / 128
          sum += normalized * normalized
        }
        const rms = Math.sqrt(sum / data.length)
        peakRms = Math.max(peakRms, rms)
        if (performance.now() - started < 250) {
          baselineSum += rms
          baselineCount += 1
        }
        await new Promise((resolve) => setTimeout(resolve, 50))
      }
      const baselineRms = baselineCount > 0 ? baselineSum / baselineCount : 0
      const hasSignal = peakRms >= MIC_MIN_ABSOLUTE_RMS || (baselineRms > 0 && peakRms / baselineRms >= MIC_RELATIVE_GAIN)
      return { peakRms, baselineRms, hasSignal }
    } finally {
      await ctx.close()
    }
  }

  const isVoiceEnabled = Boolean(sessionId)

  useEffect(() => {
    try {
      localStorage.setItem(VOICE_MODE_KEY, mode)
    } catch {
      // ignore
    }
  }, [mode])

  useEffect(() => {
    try {
      localStorage.setItem(VOICE_GENDER_KEY, voiceGender)
    } catch {
      // ignore
    }
  }, [voiceGender])

  useEffect(() => {
    try {
      if (sessionId) {
        localStorage.setItem(VOICE_SESSION_KEY, sessionId)
      } else {
        localStorage.removeItem(VOICE_SESSION_KEY)
      }
    } catch {
      // ignore
    }
  }, [sessionId])

  const syncMicVerification = async (
    sid: string | undefined,
    verified: boolean,
    source: string,
    detail: string
  ) => {
    if (!sid) return
    try {
      await voiceAPI.verifyMicrophone(sid, verified, source, detail)
    } catch {
      // Keep UI responsive: health/go-no-go refresh can retry verification later.
    }
  }

  useEffect(() => {
    const restore = async () => {
      if (!sessionId) return
      try {
        const h = await voiceAPI.health(sessionId)
        if (h?.status === 'stopped') {
          setSessionId('')
          return
        }
        const g = await voiceAPI.goNoGo(sessionId)
        setHealth(h)
        setGoNoGo(g)
        if (micStatus !== 'connected') {
          await connectMic(sessionId)
        }
      } catch {
        setSessionId('')
      }
    }
    void restore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    return () => {
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((t) => t.stop())
        micStreamRef.current = null
      }
    }
  }, [])

  const connectMic = async (voiceSessionId?: string) => {
    try {
      setMicError(null)
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((t) => t.stop())
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      micStreamRef.current = stream
      const track = stream.getAudioTracks()[0]
      const probe = await probeMicrophoneSignal(stream)
      setMicSignalRms(probe.peakRms)
      const hasSignal = probe.hasSignal
      setMicLabel(track?.label || 'default microphone')
      setMicStatus(hasSignal ? 'connected' : 'error')
      if (!hasSignal) {
        setMicError(
          'Микрофон подключен, но сигнал слишком тихий/плоский. Попробуйте говорить громче 1-2 сек, отключить шумоподавление или проверить mute.'
        )
      }
      const sid = voiceSessionId || sessionId
      if (sid) {
        await syncMicVerification(
          sid,
          hasSignal,
          'browser_rms_probe',
          `${track?.label || 'default microphone'}; peak_rms=${probe.peakRms.toFixed(4)}; baseline_rms=${probe.baselineRms.toFixed(4)}`
        )
      }
    } catch (e: any) {
      setMicStatus('error')
      setMicSignalRms(0)
      setMicError(e?.message || 'Не удалось получить доступ к микрофону')
      const sid = voiceSessionId || sessionId
      if (sid) {
        await syncMicVerification(sid, false, 'browser_getUserMedia', e?.message || 'mic access failed')
      }
    }
  }

  const disconnectMic = (voiceSessionId?: string) => {
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop())
      micStreamRef.current = null
    }
    setMicStatus('idle')
    setMicLabel('')
    setMicSignalRms(0)
    setMicError(null)
    const sid = voiceSessionId || sessionId
    if (sid) {
      void syncMicVerification(sid, false, 'browser_disconnect', 'microphone disconnected by user')
    }
  }

  const startSession = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await voiceAPI.startSession(mode, voiceGender)
      setSessionId(data.voice_session_id)
      setHealth(null)
      setGoNoGo(null)
      if (micStatus !== 'connected') {
        await connectMic(data.voice_session_id)
      } else {
        await syncMicVerification(
          data.voice_session_id,
          micSignalRms >= MIC_MIN_ABSOLUTE_RMS,
          'ui_session_start_sync',
          `${micLabel || 'connected before session start'}; peak_rms=${micSignalRms.toFixed(4)}`
        )
      }
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
      disconnectMic(sessionId)
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
      // Re-sync mic state before health/go-no-go in case browser verify event was missed.
      if (micStatus === 'connected') {
        await syncMicVerification(
          sessionId,
          micSignalRms >= MIC_MIN_ABSOLUTE_RMS,
          'ui_refresh_sync',
          `${micLabel || 'connected microphone'}; peak_rms=${micSignalRms.toFixed(4)}`
        )
      }
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
        <h3 style={{ marginTop: 0 }}>Microphone</h3>
        <div style={{ marginBottom: '0.5rem' }}>
          Status:{' '}
          <strong style={{ color: micStatus === 'connected' ? '#22c55e' : micStatus === 'error' ? '#ef4444' : '#aaa' }}>
            {micStatus}
          </strong>
        </div>
        {micLabel && <div style={{ marginBottom: '0.5rem' }}>Device: {micLabel}</div>}
        <div style={{ marginBottom: '0.5rem' }}>Signal peak RMS: {micSignalRms.toFixed(4)}</div>
        {micError && <div style={{ marginBottom: '0.5rem', color: '#fca5a5' }}>{micError}</div>}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button onClick={() => void connectMic()} disabled={loading} style={{ padding: '0.5rem 0.8rem' }}>Подключить микрофон</button>
          <button onClick={() => disconnectMic()} disabled={loading || micStatus !== 'connected'} style={{ padding: '0.5rem 0.8rem' }}>Отключить микрофон</button>
        </div>
      </section>

      <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem' }}>
        <h3 style={{ marginTop: 0 }}>Health</h3>
        {!health ? (
          <div style={{ color: '#aaa' }}>Нет данных.</div>
        ) : (
          <>
            <div style={{ display: 'grid', gap: '0.35rem', marginBottom: '0.75rem', fontSize: '0.92rem' }}>
              <div><strong>Active mode:</strong> {health.mode}</div>
              <div><strong>STT engine:</strong> {health.stt_engine}</div>
              <div><strong>TTS engine:</strong> {health.tts_engine}</div>
              <div><strong>Status:</strong> {health.status}</div>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(health, null, 2)}</pre>
          </>
        )}
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
