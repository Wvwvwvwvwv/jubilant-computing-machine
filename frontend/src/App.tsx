import { Menu } from 'lucide-react'
import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatPage from './pages/ChatPage'
import TerminalPage from './pages/TerminalPage'
import { useAppState } from './state/AppState'

export default function App() {
  const { activeTab, setActiveTab } = useAppState()
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#0f0f10] text-white">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />

      <div className="h-screen flex flex-col overflow-hidden">
        <header className="h-[64px] shrink-0 border-b border-[#1d1f22] bg-[#111214] px-3 flex items-center justify-between">
          <button
            onClick={() => setMenuOpen(true)}
            className="h-10 w-10 rounded-md flex items-center justify-center text-neutral-300 hover:bg-[#1c1e22]"
            aria-label="Open menu"
          >
            <Menu size={26} />
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`rounded-md px-3 py-1.5 text-sm ${activeTab === 'chat' ? 'bg-[#2b2f37] text-white' : 'bg-transparent text-neutral-400'}`}
            >
              Чат
            </button>
            <button
              onClick={() => setActiveTab('terminal')}
              className={`rounded-md px-3 py-1.5 text-sm ${activeTab === 'terminal' ? 'bg-[#2b2f37] text-white' : 'bg-transparent text-neutral-400'}`}
            >
              Терминал
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-hidden">{activeTab === 'chat' ? <ChatPage /> : <TerminalPage />}</main>
      </div>
    </div>
  )
}
