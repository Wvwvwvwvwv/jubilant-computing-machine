import Sidebar from './components/Sidebar'
import ChatPage from './pages/ChatPage'
import TerminalPage from './pages/TerminalPage'
import { useAppState } from './state/AppState'

export default function App() {
  const { activeTab, setActiveTab } = useAppState()

  return (
    <div className="h-screen flex overflow-hidden bg-black text-white">
      <Sidebar />

      <main className="flex-1 h-screen overflow-hidden" style={{ width: 'calc(100vw - 300px)' }}>
        <div className="h-full flex flex-col overflow-hidden">
          <div className="border-b border-neutral-800 px-3 py-2 flex gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`rounded px-3 py-1 text-sm ${activeTab === 'chat' ? 'bg-blue-600' : 'bg-neutral-800'}`}
            >
              Чат
            </button>
            <button
              onClick={() => setActiveTab('terminal')}
              className={`rounded px-3 py-1 text-sm ${activeTab === 'terminal' ? 'bg-blue-600' : 'bg-neutral-800'}`}
            >
              Терминал
            </button>
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === 'chat' ? <ChatPage /> : <TerminalPage />}
          </div>
        </div>
      </main>
    </div>
  )
}
