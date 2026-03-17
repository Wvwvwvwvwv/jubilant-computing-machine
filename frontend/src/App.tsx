import Sidebar from './components/Sidebar'
import ChatPage from './pages/ChatPage'
import TerminalPage from './pages/TerminalPage'
import { useAppState } from './state/AppState'

export default function App() {
  const { activeTab, setActiveTab } = useAppState()

  return (
    <div className="h-screen flex overflow-hidden bg-neutral-200 text-neutral-900">
      <Sidebar />

      <main className="flex-1 h-screen overflow-hidden bg-white" style={{ width: 'calc(100vw - 300px)' }}>
        <div className="h-full flex flex-col overflow-hidden">
          <div className="shrink-0 border-b border-neutral-200 bg-white p-2">
            <div className="inline-flex rounded-lg bg-neutral-100 p-1">
              <button
                onClick={() => setActiveTab('chat')}
                className={`rounded-md px-4 py-2 text-sm font-medium ${
                  activeTab === 'chat' ? 'bg-blue-600 text-white' : 'text-neutral-700 hover:bg-neutral-200'
                }`}
              >
                Чат
              </button>
              <button
                onClick={() => setActiveTab('terminal')}
                className={`rounded-md px-4 py-2 text-sm font-medium ${
                  activeTab === 'terminal' ? 'bg-blue-600 text-white' : 'text-neutral-700 hover:bg-neutral-200'
                }`}
              >
                Терминал
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-hidden bg-white">{activeTab === 'chat' ? <ChatPage /> : <TerminalPage />}</div>
        </div>
      </main>
    </div>
  )
}
