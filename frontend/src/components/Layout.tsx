import { Outlet, NavLink } from 'react-router-dom'
import { MessageSquare, Brain, Terminal, ListChecks, SlidersHorizontal, Mic } from 'lucide-react'

export default function Layout() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Header */}
      <header style={{
        background: '#111',
        borderBottom: '1px solid #222',
        padding: '1rem'
      }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
          🤖 Roampal Android
        </h1>
      </header>

      {/* Main Content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Outlet />
      </div>

      {/* Bottom Navigation */}
      <nav style={{
        display: 'flex',
        background: '#111',
        borderTop: '1px solid #222',
        padding: '0.5rem'
      }}>
        <NavLink
          to="/chat"
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '0.75rem',
            color: isActive ? '#3b82f6' : '#888',
            textDecoration: 'none',
            fontSize: '0.875rem'
          })}
        >
          <MessageSquare size={24} />
          <span style={{ marginTop: '0.25rem' }}>Чат</span>
        </NavLink>

        <NavLink
          to="/memory"
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '0.75rem',
            color: isActive ? '#3b82f6' : '#888',
            textDecoration: 'none',
            fontSize: '0.875rem'
          })}
        >
          <Brain size={24} />
          <span style={{ marginTop: '0.25rem' }}>Память</span>
        </NavLink>

        <NavLink
          to="/sandbox"
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '0.75rem',
            color: isActive ? '#3b82f6' : '#888',
            textDecoration: 'none',
            fontSize: '0.875rem'
          })}
        >
          <Terminal size={24} />
          <span style={{ marginTop: '0.25rem' }}>Sandbox</span>
        </NavLink>

        <NavLink
          to="/tasks"
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '0.75rem',
            color: isActive ? '#3b82f6' : '#888',
            textDecoration: 'none',
            fontSize: '0.875rem'
          })}
        >
          <ListChecks size={24} />
          <span style={{ marginTop: '0.25rem' }}>Задачи</span>
        </NavLink>

        <NavLink
          to="/companion"
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '0.75rem',
            color: isActive ? '#3b82f6' : '#888',
            textDecoration: 'none',
            fontSize: '0.875rem'
          })}
        >
          <SlidersHorizontal size={24} />
          <span style={{ marginTop: '0.25rem' }}>Companion</span>
        </NavLink>


        <NavLink
          to="/voice"
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '0.75rem',
            color: isActive ? '#3b82f6' : '#888',
            textDecoration: 'none',
            fontSize: '0.875rem'
          })}
        >
          <Mic size={24} />
          <span style={{ marginTop: '0.25rem' }}>Voice</span>
        </NavLink>
      </nav>
    </div>
  )
}
