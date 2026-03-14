import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import MemoryPage from './pages/MemoryPage'
import SandboxPage from './pages/SandboxPage'
import TasksPage from './pages/TasksPage'
import CompanionPage from './pages/CompanionPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/chat" replace />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="memory" element={<MemoryPage />} />
          <Route path="sandbox" element={<SandboxPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="companion" element={<CompanionPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
