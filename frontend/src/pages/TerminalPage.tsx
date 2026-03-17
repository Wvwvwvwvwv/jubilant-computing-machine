import { useEffect, useRef } from 'react'
import { useAppState } from '../state/AppState'

export default function TerminalPage() {
  const { terminalLines, clearTerminal } = useAppState()
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [terminalLines])

  return (
    <div className="h-full flex flex-col overflow-hidden bg-white">
      <div className="shrink-0 border-b border-neutral-200 bg-neutral-50 px-3 py-2 flex items-center justify-between">
        <p className="text-xs text-neutral-600">Live sandbox output (real-time via polling each second)</p>
        <button onClick={clearTerminal} className="rounded-md bg-neutral-200 px-2 py-1 text-xs text-neutral-800">
          Clear
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs bg-neutral-100">
        {terminalLines.map((line) => (
          <div
            key={line.id}
            className={`mb-1 whitespace-pre-wrap ${
              line.stream === 'stderr' ? 'text-red-700' : line.stream === 'stdout' ? 'text-green-700' : 'text-neutral-700'
            }`}
          >
            [{new Date(line.ts).toLocaleTimeString()}] {line.text}
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  )
}
