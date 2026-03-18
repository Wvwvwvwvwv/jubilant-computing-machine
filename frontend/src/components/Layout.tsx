import { Outlet, NavLink } from 'react-router-dom'
import { MessageSquare, Brain, Terminal } from 'lucide-react'

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  flex: 1,
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.25rem',
  padding: '0.8rem 0.5rem',
  color: isActive ? '#60a5fa' : '#8b8f98',
  textDecoration: 'none',
  fontSize: '0.875rem',
  fontWeight: 500,
  borderRadius: '0.9rem',
  background: isActive ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
  border: isActive ? '1px solid rgba(96, 165, 250, 0.24)' : '1px solid transparent',
})

export default function Layout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#0b0b0c' }}>
      <header style={{
        background: 'linear-gradient(180deg, #111214 0%, #0d0e10 100%)',
        borderBottom: '1px solid #20232a',
        padding: '1rem 1.25rem',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.22)'
      }}>
        <h1 style={{ fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
          🤖 Roampal Android
        </h1>
      </header>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Outlet />
      </div>

      <nav style={{
        display: 'flex',
        gap: '0.6rem',
        background: '#101113',
        borderTop: '1px solid #20232a',
        padding: '0.7rem',
        boxShadow: '0 -10px 30px rgba(0, 0, 0, 0.18)'
      }}>
        <NavLink to="/chat" style={navLinkStyle}>
          <MessageSquare size={22} />
          <span>Чат</span>
        </NavLink>

        <NavLink to="/memory" style={navLinkStyle}>
          <Brain size={22} />
          <span>Память</span>
        </NavLink>

        <NavLink to="/terminal" style={navLinkStyle}>
          <Terminal size={22} />
          <span>Терминал</span>
        </NavLink>
      </nav>
    </div>
  )
}
