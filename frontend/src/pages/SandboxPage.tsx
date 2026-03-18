import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { loadTerminalState, resetTerminalState, subscribeTerminalState, type TerminalState } from '../terminalStore'

function streamColor(stream?: 'stdout' | 'stderr' | 'status') {
  if (stream === 'stderr') return '#fca5a5'
  if (stream === 'status') return '#93c5fd'
  return '#e5e7eb'
}

export default function SandboxPage() {
  const [terminalState, setTerminalState] = useState<TerminalState>(loadTerminalState)

  useEffect(() => {
    setTerminalState(loadTerminalState())
    return subscribeTerminalState((state) => setTerminalState(state))
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '1rem', gap: '0.9rem', background: '#0b0b0c' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        background: '#121417',
        border: '1px solid #22262d',
        borderRadius: '1rem',
        padding: '0.9rem 1rem'
      }}>
        <div>
          <div style={{ fontSize: '1rem', fontWeight: 600, color: '#f3f4f6' }}>Терминал</div>
          <div style={{ fontSize: '0.82rem', color: '#8b93a1', marginTop: '0.25rem' }}>
            {terminalState.title}
          </div>
        </div>

        <button
          onClick={() => resetTerminalState()}
          style={{
            background: '#7f1d1d',
            border: '1px solid #991b1b',
            borderRadius: '0.8rem',
            padding: '0.7rem 1rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: '#fff',
            fontWeight: 600
          }}
        >
          <Trash2 size={16} />
          Очистить
        </button>
      </div>

      <div style={{
        flex: 1,
        background: '#050608',
        border: '1px solid #20232a',
        borderRadius: '1rem',
        padding: '1rem',
        overflow: 'auto',
        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.02)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          marginBottom: '1rem',
          color: '#8b93a1',
          fontSize: '0.8rem'
        }}>
          <span style={{ width: '0.6rem', height: '0.6rem', borderRadius: '999px', background: '#ef4444' }} />
          <span style={{ width: '0.6rem', height: '0.6rem', borderRadius: '999px', background: '#f59e0b' }} />
          <span style={{ width: '0.6rem', height: '0.6rem', borderRadius: '999px', background: '#10b981' }} />
          <span style={{ marginLeft: '0.5rem' }}>
            {terminalState.active ? 'Сессия выполняется…' : 'Ожидание команды'}
          </span>
        </div>

        <pre style={{
          margin: 0,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
          fontSize: '0.88rem',
          lineHeight: 1.65,
        }}>
          {terminalState.entries.map((entry) => (
            <div key={entry.id} style={{ color: streamColor(entry.stream), marginBottom: '0.55rem' }}>
              <span style={{ color: '#4b5563' }}>[{new Date(entry.timestamp).toLocaleTimeString()}]</span>{' '}
              {entry.text}
            </div>
          ))}
        </pre>
      </div>
    </div>
  )
}
