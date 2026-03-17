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
        <p className="text-xs text-neutral-600">Terminal workspace · live stream (polling 1s)</p>
        <button onClick={clearTerminal} className="rounded-md bg-neutral-200 px-2 py-1 text-xs text-neutral-800">
          Clear
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 bg-neutral-100 font-mono text-xs">
        {terminalLines.map((line) => (
          <div
            key={line.id}
            className={`mb-1 whitespace-pre-wrap rounded px-2 py-1 ${
              line.stream === 'stderr'
                ? 'bg-red-50 text-red-700 border border-red-100'
                : line.stream === 'stdout'
                  ? 'bg-green-50 text-green-700 border border-green-100'
                  : 'bg-white text-neutral-700 border border-neutral-200'
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
