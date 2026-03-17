import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { booksAPI } from '../api/client'
import { useAppState } from '../state/AppState'

interface BookItem {
  id: string
  title: string
  uploaded_at?: number
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(true)
  return (
    <section className="border-b border-neutral-800">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full px-3 py-2 text-left text-sm font-semibold text-neutral-200"
      >
        {title}
      </button>
      {open ? <div className="px-2 pb-3">{children}</div> : null}
    </section>
  )
}

export default function Sidebar() {
  const {
    dialogs,
    activeDialogId,
    setActiveDialogId,
    createDialog,
    deleteDialog,
    models,
    selectedModel,
    setSelectedModel,
    addModel,
    removeModel
  } = useAppState()

  const [books, setBooks] = useState<BookItem[]>([])
  const [loadingBooks, setLoadingBooks] = useState(false)
  const [newModel, setNewModel] = useState('')

  const sidebarWidthClass = useMemo(() => 'w-[280px] min-[1600px]:w-[300px]', [])

  const loadBooks = async () => {
    setLoadingBooks(true)
    try {
      const data = await booksAPI.list()
      setBooks(Array.isArray(data?.books) ? data.books : [])
    } finally {
      setLoadingBooks(false)
    }
  }

  useEffect(() => {
    void loadBooks()
  }, [])

  const onUpload = async (file: File) => {
    await booksAPI.upload(file)
    await loadBooks()
  }

  return (
    <aside className={`${sidebarWidthClass} h-screen shrink-0 border-r border-neutral-800 bg-neutral-950 overflow-hidden`}>
      <div className="h-full flex flex-col">
        <div className="px-3 py-3 border-b border-neutral-800 flex items-center justify-between">
          <h1 className="text-base font-bold text-neutral-100">Roampal Android</h1>
          <button onClick={createDialog} className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-500">+ чат</button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <Section title="Диалоги">
            <div className="space-y-2">
              {dialogs.map((d) => (
                <div key={d.id} className={`rounded p-2 text-xs ${d.id === activeDialogId ? 'bg-blue-900/50' : 'bg-neutral-900'}`}>
                  <button onClick={() => setActiveDialogId(d.id)} className="block w-full text-left text-neutral-100 truncate">{d.title}</button>
                  <div className="mt-1 flex items-center justify-between text-neutral-400">
                    <span>{new Date(d.createdAt).toLocaleDateString()}</span>
                    <button onClick={() => deleteDialog(d.id)} className="text-red-400 hover:text-red-300">удалить</button>
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Модели">
            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  value={newModel}
                  onChange={(e) => setNewModel(e.target.value)}
                  placeholder="Имя GGUF"
                  className="min-w-0 flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-xs text-white"
                />
                <button
                  onClick={() => {
                    addModel(newModel)
                    setNewModel('')
                  }}
                  className="rounded bg-neutral-700 px-2 py-1 text-xs text-white"
                >
                  +
                </button>
              </div>
              {models.map((model) => (
                <div key={model} className={`rounded p-2 text-xs ${selectedModel === model ? 'bg-blue-900/50' : 'bg-neutral-900'}`}>
                  <div className="flex items-center justify-between gap-2">
                    <button className="truncate text-left text-neutral-100" onClick={() => setSelectedModel(model)}>{model}</button>
                    <button className="text-red-400" onClick={() => removeModel(model)}>×</button>
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section title="Литература">
            <div className="space-y-2">
              <label className="block">
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) void onUpload(file)
                  }}
                />
                <span className="inline-block cursor-pointer rounded bg-neutral-700 px-2 py-1 text-xs text-white">Загрузить файл</span>
              </label>

              {loadingBooks ? <p className="text-xs text-neutral-400">Загрузка...</p> : null}

              {books.map((book) => (
                <div key={book.id} className="rounded bg-neutral-900 p-2 text-xs">
                  <p className="truncate text-neutral-100">{book.title || book.id}</p>
                  <div className="mt-1 flex items-center justify-between text-neutral-400">
                    <span>{book.uploaded_at ? new Date(book.uploaded_at * 1000).toLocaleDateString() : '—'}</span>
                    <button
                      className="text-red-400"
                      onClick={async () => {
                        await booksAPI.delete(book.id)
                        await loadBooks()
                      }}
                    >
                      удалить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      </div>
    </aside>
  )
}
