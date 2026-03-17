import { useMemo, useRef, useState } from 'react'
import { chatAPI, onlineAPI, sandboxAPI, voiceAPI } from '../api/client'
import { useAppState } from '../state/AppState'

// System policy injected into every chat request.
const AGENT_SYSTEM_PROMPT = [
  'You are Roampal autonomous local agent.',
  'No manual confirmation, no extra planners. You decide tool usage yourself.',
  'For action-oriented user intents, automatically use web_search and sandbox, then return concise final summary.',
  'Action intents include: find/search, download, inspect, уточни, install, convert, modify, run, verify, analyze.'
].join('\n')

const ACTION_INTENT_RE =
  /(найди|скачай|поищи|посмотри|уточни|установи|конвертируй|измени|запустить|запусти|проверь|разбери|проанализируй|find|search|download|inspect|install|convert|modify|run|verify|analy[sz]e)/i

type BrowserRecognition = {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  continuous: boolean
  onresult: ((event: any) => void) | null
  onerror: ((event: any) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

function speak(text: string) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text.slice(0, 500))
  u.lang = 'ru-RU'
  window.speechSynthesis.speak(u)
}

export default function ChatPage() {
  const { dialogs, activeDialogId, appendDialogMessage, appendTerminalLine, setActiveTab, selectedModel } = useAppState()

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [listening, setListening] = useState(false)
  const [voiceSessionId, setVoiceSessionId] = useState<string | null>(null)
  const recognitionRef = useRef<BrowserRecognition | null>(null)

  const activeDialog = useMemo(() => dialogs.find((d) => d.id === activeDialogId), [dialogs, activeDialogId])
  const messages = activeDialog?.messages || []

  const runSandboxLive = async (code: string) => {
    let running = true
    const poll = window.setInterval(() => {
      if (running) appendTerminalLine({ stream: 'system', text: 'sandbox running... (poll 1s)' })
    }, 1000)

    try {
      const result = await sandboxAPI.execute(code, 'python', 120)
      appendTerminalLine({ stream: result.exit_code === 0 ? 'stdout' : 'stderr', text: `exit_code=${result.exit_code}` })
      if (result.stdout) appendTerminalLine({ stream: 'stdout', text: result.stdout })
      if (result.stderr) appendTerminalLine({ stream: 'stderr', text: result.stderr })
      return result
    } finally {
      running = false
      window.clearInterval(poll)
    }
  }

  const autoTools = async (text: string) => {
    if (!ACTION_INTENT_RE.test(text)) return null

    setActiveTab('terminal')
    appendTerminalLine({ stream: 'system', text: `[agent] action intent detected: ${text}` })

    const searchResp = await onlineAPI.search(text, 3)
    const results = Array.isArray(searchResp?.results) ? searchResp.results : []
    appendTerminalLine({ stream: 'system', text: `[agent] web_search results=${results.length}` })

    // Script intentionally mirrors tool usage for transparent terminal output.
    const code = [
      "print('AGENT TOOL PIPELINE START')",
      `query = ${JSON.stringify(text)}`,
      `results = ${JSON.stringify(results)}`,
      "print('query:', query)",
      "for i, item in enumerate(results, 1):",
      "    print(f'[{i}] {item.get(\"title\", \"Result\")} | {item.get(\"url\", \"\")}')",
      "print('AGENT TOOL PIPELINE END')"
    ].join('\n')

    const sandboxResp = await runSandboxLive(code)
    return { results, sandboxResp }
  }

  const sendMessage = async (raw?: string, source: 'text' | 'voice' = 'text') => {
    const text = (raw ?? input).trim()
    if (!text || loading || !activeDialog) return

    appendDialogMessage(activeDialog.id, { role: 'user', content: text })
    if (source === 'text') setInput('')
    setLoading(true)

    try {
      const tools = await autoTools(text)

      const payloadMessages = [
        { role: 'system', content: AGENT_SYSTEM_PROMPT },
        { role: 'system', content: `Selected model: ${selectedModel}` },
        ...[...messages, { id: 'tmp_user', role: 'user' as const, content: text, createdAt: Date.now() }].map((m) => ({
          role: m.role,
          content: m.content
        }))
      ]

      if (tools) {
        payloadMessages.push({
          role: 'system',
          content: `TOOL_CONTEXT: ${JSON.stringify({
            web_results: tools.results.length,
            sandbox_exit_code: tools.sandboxResp?.exit_code,
            sandbox_stdout_tail: String(tools.sandboxResp?.stdout || '').slice(-700),
            sandbox_stderr_tail: String(tools.sandboxResp?.stderr || '').slice(-700)
          })}`
        })
      }

      const response = await chatAPI.send(payloadMessages, true)
      const answer = response?.response || 'No response'
      appendDialogMessage(activeDialog.id, { role: 'assistant', content: answer })
      speak(answer)
    } catch (error: any) {
      appendDialogMessage(activeDialog.id, {
        role: 'assistant',
        content: `❌ ${error?.response?.data?.detail || error?.message || 'request failed'}`
      })
    } finally {
      setLoading(false)
    }
  }

  const toggleVoice = async () => {
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      if (voiceSessionId) await voiceAPI.stopSession(voiceSessionId)
      setVoiceSessionId(null)
      return
    }

    const voiceSession = await voiceAPI.startSession('duplex', 'female')
    setVoiceSessionId(voiceSession.voice_session_id)
    await voiceAPI.verifyMicrophone(
      voiceSession.voice_session_id,
      true,
      'browser_speech_recognition',
      'voice command path active'
    )

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      appendDialogMessage(activeDialogId, { role: 'assistant', content: '❌ SpeechRecognition is not supported.' })
      return
    }

    const rec: BrowserRecognition = new SpeechRecognition()
    rec.lang = 'ru-RU'
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.continuous = true

    rec.onresult = (event: any) => {
      const transcript = event.results?.[event.results.length - 1]?.[0]?.transcript?.trim()
      if (transcript) void sendMessage(transcript, 'voice')
    }
    rec.onerror = () => setListening(false)
    rec.onend = () => setListening(false)

    rec.start()
    recognitionRef.current = rec
    setListening(true)
  }

  return (
    <div className="h-full flex flex-col overflow-hidden bg-white">
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`max-w-[85%] whitespace-pre-wrap rounded-xl px-3 py-2 text-sm ${
              msg.role === 'user' ? 'ml-auto bg-blue-600 text-white' : 'bg-neutral-100 text-neutral-900'
            }`}
          >
            {msg.content}
          </div>
        ))}
      </div>

      <div className="shrink-0 border-t border-neutral-200 p-2 flex gap-2">
        <button
          onClick={() => void toggleVoice()}
          className={`rounded-md px-3 py-2 text-sm text-white ${listening ? 'bg-red-600' : 'bg-neutral-700'}`}
        >
          {listening ? '🎙 stop' : '🎤 voice'}
        </button>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') void sendMessage()
          }}
          placeholder="Type message or command..."
          className="min-w-0 flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm"
        />

        <button
          onClick={() => void sendMessage()}
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-60"
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
