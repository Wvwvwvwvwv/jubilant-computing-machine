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

export default function CompanionPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<Profile | null>(null)

  const load = async () => {
    try {
      setLoading(true)
      setError(null)
      const [sessionData, profileData] = await Promise.all([
        companionAPI.getSession(),
        companionAPI.getRelationshipProfile(),
      ])
      setSession(sessionData)
      setProfile(profileData)
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
    if (!session) return
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

  const patchProfile = async (patch: any) => {
    if (!profile) return
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
          </div>
        </section>
      )}

      {profile && (
        <section style={{ border: '1px solid #333', borderRadius: '0.75rem', padding: '1rem' }}>
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
    </div>
  )
}
