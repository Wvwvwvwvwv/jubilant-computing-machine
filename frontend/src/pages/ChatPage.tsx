import { useMemo, useRef, useState } from 'react'
import { Mic, ArrowRight, Plus } from 'lucide-react'
import { chatAPI, onlineAPI, sandboxAPI, voiceAPI } from '../api/client'
import { useAppState } from '../state/AppState'

const AGENT_SYSTEM_PROMPT = [
  'You are Roampal autonomous local agent.',
  'No manual confirmations and no additional planners.',
  'Model decides when and how to use web_search + sandbox.',
  'For any action-oriented user intent (text or voice), automatically run web_search first, then run required operations in sandbox.',
  'During execution, provide terminal-like step-by-step progress, then return one concise final result card.'
].join('\n')

const ACTION_INTENT_RE =
  /(найди|скачай|поищи|посмотри|уточни|установи|конвертируй|измени|запустить|запусти|проверь|разбери|проанализируй|find|search|download|inspect|install|convert|modify|run|verify|analy[sz]e|check|parse)/i

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

function buildSandboxScript(query: string, results: Array<Record<string, any>>) {
  return [
    'from datetime import datetime',
    'def log(line):',
    '    print(f"[{datetime.now().strftime(\"%H:%M:%S\")}] {line}")',
    "log('$ agent start')",
    `query = ${JSON.stringify(query)}`,
    `results = ${JSON.stringify(results)}`,
    "log(f'query: {query}')",
    "log(f'search_results: {len(results)}')",
    "for idx, item in enumerate(results, 1):",
    "    title = item.get('title', 'Result')",
    "    url = item.get('url', '')",
    "    log(f'[{idx}] {title} -> {url}')",
    "log('$ sandbox analyze')",
    "log('$ done')"
  ].join('\n')
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
      if (running) appendTerminalLine({ stream: 'system', text: '[poll] sandbox running...' })
    }, 1000)

    try {
      appendTerminalLine({ stream: 'system', text: '$ sandbox execute --language python' })
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

  const autoToolsIfNeeded = async (text: string) => {
    if (!ACTION_INTENT_RE.test(text)) return null
    setActiveTab('terminal')
    appendTerminalLine({ stream: 'system', text: '$ agent detect-action-intent' })
    appendTerminalLine({ stream: 'system', text: '$ web_search' })
    const searchResp = await onlineAPI.search(text, 5)
    const results = Array.isArray(searchResp?.results) ? searchResp.results : []
    appendTerminalLine({ stream: 'system', text: `web_search results=${results.length}` })
    const sandboxResp = await runSandboxLive(buildSandboxScript(text, results))
    return { results, sandboxResp }
  }

  const sendMessage = async (raw?: string, source: 'text' | 'voice' = 'text') => {
    const text = (raw ?? input).trim()
    if (!text || loading || !activeDialog) return
    appendDialogMessage(activeDialog.id, { role: 'user', content: text })
    if (source === 'text') setInput('')
    setLoading(true)

    try {
      const toolContext = await autoToolsIfNeeded(text)
      const payloadMessages: Array<{ role: string; content: string }> = [
        { role: 'system', content: AGENT_SYSTEM_PROMPT },
        { role: 'system', content: `Selected model: ${selectedModel}` },
        ...[...messages, { id: 'tmp_user', role: 'user' as const, content: text, createdAt: Date.now() }].map((m) => ({ role: m.role, content: m.content }))
      ]

      if (toolContext) {
        payloadMessages.push({
          role: 'system',
          content: `TOOL_CONTEXT: ${JSON.stringify({
            web_results_count: toolContext.results.length,
            sandbox_exit_code: toolContext.sandboxResp?.exit_code,
            sandbox_stdout_tail: String(toolContext.sandboxResp?.stdout || '').slice(-800),
            sandbox_stderr_tail: String(toolContext.sandboxResp?.stderr || '').slice(-800)
          })}`
        })
      }

      const response = await chatAPI.send(payloadMessages, true)
      appendDialogMessage(activeDialog.id, { role: 'assistant', content: response?.response || 'No response' })
    } catch (error: any) {
      appendDialogMessage(activeDialog.id, { role: 'assistant', content: `❌ ${error?.response?.data?.detail || error?.message || 'request failed'}` })
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
    await voiceAPI.verifyMicrophone(voiceSession.voice_session_id, true, 'browser_speech_recognition', 'voice command path active')

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) return

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
    <div className="h-full flex flex-col overflow-hidden bg-[#0f0f10]">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`max-w-[86%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm ${
              msg.role === 'user' ? 'ml-auto bg-[#2a2a2f] text-white' : 'bg-[#1b1b20] text-neutral-200 border border-[#2e2e36]'
            }`}
          >
            {msg.content}
          </div>
        ))}
      </div>

      <div className="shrink-0 p-3">
        <div className="rounded-3xl border border-[#32343a] bg-[#1a1a1f] p-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void sendMessage()
            }}
            placeholder="Задайте любой вопрос..."
            className="w-full bg-transparent text-neutral-200 placeholder:text-neutral-500 outline-none border-none text-[30px]"
          />
          <div className="mt-3 flex items-center justify-between">
            <button className="h-11 w-11 rounded-full border border-[#383a42] flex items-center justify-center text-neutral-300">
              <Plus size={20} />
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={() => void toggleVoice()}
                className={`h-11 w-11 rounded-full flex items-center justify-center ${
                  listening ? 'bg-red-600 text-white' : 'bg-transparent text-neutral-300 border border-[#383a42]'
                }`}
              >
                <Mic size={20} />
              </button>
              <button
                onClick={() => void sendMessage()}
                disabled={loading}
                className="h-11 w-11 rounded-full bg-neutral-300 text-black flex items-center justify-center disabled:opacity-60"
              >
                <ArrowRight size={20} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
