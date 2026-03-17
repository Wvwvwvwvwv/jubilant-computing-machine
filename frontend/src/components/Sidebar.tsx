import { useEffect, useState, type ReactNode } from 'react'
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
        className="w-full px-3 py-2 text-left text-sm font-semibold text-neutral-100"
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

  const [newModel, setNewModel] = useState('')
  const [books, setBooks] = useState<BookItem[]>([])

  const loadBooks = async () => {
    try {
      const data = await booksAPI.list()
      setBooks(Array.isArray(data?.books) ? data.books : [])
    } catch {
      setBooks([])
    }
  }

  useEffect(() => {
    void loadBooks()
  }, [])

  return (
    <aside className="w-[280px] min-[1600px]:w-[300px] h-screen shrink-0 bg-neutral-950 text-white border-r border-neutral-800 overflow-hidden">
      <div className="h-full flex flex-col">
        <div className="shrink-0 px-3 py-3 border-b border-neutral-800 flex items-center justify-between">
          <h1 className="text-base font-bold">Roampal</h1>
          <button onClick={createDialog} className="rounded bg-blue-600 px-2 py-1 text-xs">
            + chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <Section title="Диалоги">
            <div className="space-y-2">
              {dialogs.map((dialog) => (
                <div
                  key={dialog.id}
                  className={`rounded p-2 text-xs ${dialog.id === activeDialogId ? 'bg-blue-900/40' : 'bg-neutral-900'}`}
                >
                  <button
                    onClick={() => setActiveDialogId(dialog.id)}
                    className="block w-full truncate text-left text-neutral-100"
                  >
                    {dialog.title}
                  </button>
                  <div className="mt-1 flex items-center justify-between text-neutral-400">
                    <span>{new Date(dialog.createdAt).toLocaleDateString()}</span>
                    <button onClick={() => deleteDialog(dialog.id)} className="text-red-400">
                      del
                    </button>
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
                  placeholder="model.gguf"
                  className="min-w-0 flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-xs text-white"
                />
                <button
                  onClick={() => {
                    addModel(newModel)
                    setNewModel('')
                  }}
                  className="rounded bg-neutral-700 px-2 py-1 text-xs"
                >
                  +
                </button>
              </div>

              {models.map((model) => (
                <div
                  key={model}
                  className={`rounded p-2 text-xs ${selectedModel === model ? 'bg-blue-900/40' : 'bg-neutral-900'}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <button className="truncate text-left" onClick={() => setSelectedModel(model)}>
                      {model}
                    </button>
                    <button className="text-red-400" onClick={() => removeModel(model)}>
                      ×
                    </button>
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
                    if (!file) return
                    void booksAPI.upload(file).then(loadBooks)
                  }}
                />
                <span className="inline-block cursor-pointer rounded bg-neutral-700 px-2 py-1 text-xs">Upload file</span>
              </label>

              {books.map((book) => (
                <div key={book.id} className="rounded bg-neutral-900 p-2 text-xs">
                  <p className="truncate">{book.title || book.id}</p>
                  <div className="mt-1 flex items-center justify-between text-neutral-400">
                    <span>{book.uploaded_at ? new Date(book.uploaded_at * 1000).toLocaleDateString() : '—'}</span>
                    <button
                      className="text-red-400"
                      onClick={() => {
                        void booksAPI.delete(book.id).then(loadBooks)
                      }}
                    >
                      del
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
