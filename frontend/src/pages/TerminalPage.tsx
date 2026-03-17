import { useEffect, useRef } from 'react'
import { useAppState } from '../state/AppState'

export default function TerminalPage() {
  const { terminalLines, clearTerminal } = useAppState()
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [terminalLines])

  return (
    <div className="h-full flex flex-col overflow-hidden bg-black">
      <div className="border-b border-neutral-800 px-3 py-2 flex items-center justify-between">
        <p className="text-xs text-neutral-400">Live sandbox output (polling 1s)</p>
        <button onClick={clearTerminal} className="rounded bg-neutral-800 px-2 py-1 text-xs">Очистить</button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 font-mono text-xs space-y-1">
        {terminalLines.map((line) => (
          <div
            key={line.id}
            className={line.stream === 'stderr' ? 'text-red-300' : line.stream === 'stdout' ? 'text-green-300' : 'text-neutral-300'}
          >
            [{new Date(line.ts).toLocaleTimeString()}] {line.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
