import { useEffect, useState } from 'react'
import { companionAPI } from '../api/client'

type ReasoningMode = 'stable' | 'wild'
type ChallengeMode = 'off' | 'balanced' | 'strict'

type Profile = {
  user_id: string
  style: {
    verbosity: string
    tone: string
    language: string
  }
  debate_preferences: {
    allow_disagreement: boolean
    strictness: string
  }
  initiative_preferences: {
    allow_proactive_suggestions: boolean
    max_unsolicited_per_hour: number
  }
  updated_at: number
}

type Session = {
  session_id: string
  reasoning_mode: ReasoningMode
  challenge_mode: ChallengeMode
  initiative_mode: 'off' | 'adaptive' | 'proactive'
  voice_mode: 'off' | 'ptt' | 'duplex'
}

type ResponseTrace = {
  response_id: string
  reasoning_mode: ReasoningMode
  challenge_mode: ChallengeMode
  relationship_used: string[]
  uncertainty_markers: string[]
  counter_position_used: boolean
  confidence: number
}

export default function CompanionPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [lastTrace, setLastTrace] = useState<ResponseTrace | null>(null)
  const [traceHistory, setTraceHistory] = useState<ResponseTrace[]>([])

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      const [sessionData, profileData, lastTraceData, tracesData] = await Promise.all([
        companionAPI.getSession(),
        companionAPI.getRelationshipProfile(),
        companionAPI.getLastResponseTrace(),
        companionAPI.getResponseTraces(5),
      ])
      setSession(sessionData)
      setProfile(profileData)
      setLastTrace(lastTraceData)
      setTraceHistory(tracesData.items || [])
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось загрузить данные companion')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const patchSession = async (patch: Partial<Session>) => {
    try {
      setSaving(true)
      const updated = await companionAPI.patchSession(patch)
      setSession(updated)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось сохранить session policy')
    } finally {
      setSaving(false)
    }
  }

  const patchProfile = async (patch: {
    style?: Partial<Profile['style']>
    debate_preferences?: Partial<Profile['debate_preferences']>
  }) => {
    try {
      setSaving(true)
      const updated = await companionAPI.patchRelationshipProfile(patch)
      setProfile(updated)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось сохранить relationship profile')
    } finally {
      setSaving(false)
    }
  }

  const refreshTraces = async () => {
    try {
      const [lastTraceData, tracesData] = await Promise.all([
        companionAPI.getLastResponseTrace(),
        companionAPI.getResponseTraces(5),
      ])
      setLastTrace(lastTraceData)
      setTraceHistory(tracesData.items || [])
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Не удалось обновить explainability trace')
    }
  }

  if (loading) {
    return <div style={{ padding: '1rem' }}>Загрузка companion настроек...</div>
  }

  return (
    <div style={{ padding: '1rem', overflowY: 'auto', height: '100%' }}>
      <h2 style={{ marginBottom: '1rem' }}>Companion</h2>

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

      {session && (
        <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem' }}>
          <h3 style={{ marginBottom: '0.75rem' }}>Session policy</h3>

          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <label>
              <div style={{ marginBottom: '0.25rem', color: '#aaa', fontSize: '0.875rem' }}>Reasoning mode</div>
              <select
                value={session.reasoning_mode}
                onChange={(e) => patchSession({ reasoning_mode: e.target.value as ReasoningMode })}
                disabled={saving}
                style={{ width: '100%', padding: '0.6rem', background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '0.5rem' }}
              >
                <option value="stable">stable</option>
                <option value="wild">wild</option>
              </select>
            </label>

            <label>
              <div style={{ marginBottom: '0.25rem', color: '#aaa', fontSize: '0.875rem' }}>Challenge mode</div>
              <select
                value={session.challenge_mode}
                onChange={(e) => patchSession({ challenge_mode: e.target.value as ChallengeMode })}
                disabled={saving}
                style={{ width: '100%', padding: '0.6rem', background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '0.5rem' }}
              >
                <option value="off">off</option>
                <option value="balanced">balanced</option>
                <option value="strict">strict</option>
              </select>
            </label>


            <label>
              <div style={{ marginBottom: '0.25rem', color: '#aaa', fontSize: '0.875rem' }}>Initiative mode</div>
              <select
                value={session.initiative_mode}
                onChange={(e) => patchSession({ initiative_mode: e.target.value as Session['initiative_mode'] })}
                disabled={saving}
                style={{ width: '100%', padding: '0.6rem', background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '0.5rem' }}
              >
                <option value="off">off</option>
                <option value="adaptive">adaptive</option>
                <option value="proactive">proactive</option>
              </select>
            </label>

            <label>
              <div style={{ marginBottom: '0.25rem', color: '#aaa', fontSize: '0.875rem' }}>Voice mode</div>
              <select
                value={session.voice_mode}
                onChange={(e) => patchSession({ voice_mode: e.target.value as Session['voice_mode'] })}
                disabled={saving}
                style={{ width: '100%', padding: '0.6rem', background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '0.5rem' }}
              >
                <option value="off">off</option>
                <option value="ptt">ptt</option>
                <option value="duplex">duplex</option>
              </select>
            </label>
          </div>
        </section>
      )}

      {profile && (
        <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem', marginBottom: '1rem' }}>
          <h3 style={{ marginBottom: '0.75rem' }}>Relationship profile</h3>

          <div style={{ display: 'grid', gap: '0.75rem' }}>
            <label>
              <div style={{ marginBottom: '0.25rem', color: '#aaa', fontSize: '0.875rem' }}>Verbosity</div>
              <input
                value={profile.style.verbosity}
                onChange={(e) => {
                  const next = e.target.value
                  setProfile({ ...profile, style: { ...profile.style, verbosity: next } })
                }}
                onBlur={() => patchProfile({ style: { verbosity: profile.style.verbosity } })}
                disabled={saving}
                style={{ width: '100%', padding: '0.6rem', background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '0.5rem' }}
              />
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                checked={profile.debate_preferences.allow_disagreement}
                onChange={(e) => {
                  const allow = e.target.checked
                  setProfile({
                    ...profile,
                    debate_preferences: { ...profile.debate_preferences, allow_disagreement: allow },
                  })
                  patchProfile({ debate_preferences: { allow_disagreement: allow } })
                }}
                disabled={saving}
              />
              Разрешать несогласие ассистента
            </label>

            <label>
              <div style={{ marginBottom: '0.25rem', color: '#aaa', fontSize: '0.875rem' }}>Debate strictness</div>
              <select
                value={profile.debate_preferences.strictness}
                onChange={(e) => {
                  const strictness = e.target.value
                  setProfile({
                    ...profile,
                    debate_preferences: { ...profile.debate_preferences, strictness },
                  })
                  patchProfile({ debate_preferences: { strictness } })
                }}
                disabled={saving}
                style={{ width: '100%', padding: '0.6rem', background: '#1a1a1a', color: '#fff', border: '1px solid #333', borderRadius: '0.5rem' }}
              >
                <option value="off">off</option>
                <option value="balanced">balanced</option>
                <option value="strict">strict</option>
              </select>
            </label>
          </div>
        </section>
      )}

      <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h3 style={{ margin: 0 }}>Explainability trace</h3>
          <button
            onClick={refreshTraces}
            style={{
              background: '#1f2937',
              border: '1px solid #374151',
              borderRadius: '0.5rem',
              color: '#fff',
              padding: '0.4rem 0.75rem',
              cursor: 'pointer'
            }}
          >
            Обновить
          </button>
        </div>

        {lastTrace ? (
          <div style={{ marginBottom: '0.75rem', fontSize: '0.9rem' }}>
            <div><strong>Last response:</strong> {lastTrace.response_id}</div>
            <div><strong>Mode:</strong> {lastTrace.reasoning_mode} / {lastTrace.challenge_mode}</div>
            <div><strong>Confidence:</strong> {lastTrace.confidence.toFixed(2)}</div>
            <div><strong>Facts used:</strong> {lastTrace.relationship_used.length}</div>
          </div>
        ) : (
          <div style={{ marginBottom: '0.75rem', color: '#aaa' }}>Trace пока отсутствует.</div>
        )}

        <div style={{ fontSize: '0.9rem' }}>
          <div style={{ marginBottom: '0.5rem', color: '#aaa' }}>Последние trace (до 5):</div>
          {traceHistory.length === 0 ? (
            <div style={{ color: '#aaa' }}>История пуста.</div>
          ) : (
            <ul style={{ margin: 0, paddingLeft: '1rem' }}>
              {traceHistory.map((trace) => (
                <li key={trace.response_id} style={{ marginBottom: '0.35rem' }}>
                  <strong>{trace.response_id}</strong> — {trace.reasoning_mode}/{trace.challenge_mode}, conf {trace.confidence.toFixed(2)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}
