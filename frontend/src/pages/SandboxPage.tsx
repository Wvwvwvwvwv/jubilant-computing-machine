import { useState } from 'react'
import { Play, Trash2 } from 'lucide-react'
import { sandboxAPI } from '../api/client'

export default function SandboxPage() {
  const [code, setCode] = useState('print("Hello from Roampal!")')
  const [language, setLanguage] = useState('python')
  const [output, setOutput] = useState('')
  const [loading, setLoading] = useState(false)

  const runCode = async () => {
    setLoading(true)
    setOutput('')

    try {
      const result = await sandboxAPI.execute(code, language)
      
      let outputText = ''
      if (result.stdout) outputText += result.stdout
      if (result.stderr) outputText += '\n' + result.stderr
      if (result.exit_code !== 0) outputText += `\n\nExit code: ${result.exit_code}`
      
      outputText += `\n\nВремя выполнения: ${result.execution_time.toFixed(2)}s`
      
      setOutput(outputText || 'Нет вывода')
    } catch (error: any) {
      setOutput(`❌ Ошибка: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '1rem', gap: '1rem' }}>
      {/* Controls */}
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          style={{
            background: '#1a1a1a',
            border: '1px solid #333',
            borderRadius: '0.5rem',
            padding: '0.5rem',
            color: '#fff'
          }}
        >
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
          <option value="bash">Bash</option>
        </select>

        <button
          onClick={runCode}
          disabled={loading}
          style={{
            background: '#10b981',
            border: 'none',
            borderRadius: '0.5rem',
            padding: '0.5rem 1rem',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            opacity: loading ? 0.5 : 1
          }}
        >
          <Play size={16} />
          {loading ? 'Выполняется...' : 'Запустить'}
        </button>

        <button
          onClick={() => { setCode(''); setOutput('') }}
          style={{
            background: '#ef4444',
            border: 'none',
            borderRadius: '0.5rem',
            padding: '0.5rem 1rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          <Trash2 size={16} />
          Очистить
        </button>
      </div>

      {/* Code Editor */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.875rem', color: '#888', marginBottom: '0.5rem' }}>
            Код:
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{
              width: '100%',
              height: '100%',
              background: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: '0.5rem',
              padding: '1rem',
              color: '#fff',
              fontFamily: 'monospace',
              fontSize: '0.875rem',
              resize: 'none'
            }}
          />
        </div>

        {/* Output */}
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.875rem', color: '#888', marginBottom: '0.5rem' }}>
            Вывод:
          </div>
          <pre style={{
            width: '100%',
            height: '100%',
            background: '#0a0a0a',
            border: '1px solid #333',
            borderRadius: '0.5rem',
            padding: '1rem',
            color: '#fff',
            fontFamily: 'monospace',
            fontSize: '0.875rem',
            overflow: 'auto',
            margin: 0
          }}>
            {output || 'Вывод появится здесь...'}
          </pre>
        </div>
      </div>
    </div>
  )
}
