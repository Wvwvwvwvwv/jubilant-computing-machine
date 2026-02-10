import { useState, useEffect } from 'react'
import { Upload, Trash2, Book, Search } from 'lucide-react'
import { memoryAPI, booksAPI } from '../api/client'

export default function MemoryPage() {
  const [books, setBooks] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)

  useEffect(() => {
    loadBooks()
    loadStats()
  }, [])

  const loadBooks = async () => {
    try {
      const data = await booksAPI.list()
      setBooks(data.books)
    } catch (error) {
      console.error('Load books error:', error)
    }
  }

  const loadStats = async () => {
    try {
      const data = await memoryAPI.stats()
      setStats(data)
    } catch (error) {
      console.error('Load stats error:', error)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      await booksAPI.upload(file)
      loadBooks()
    } catch (error) {
      console.error('Upload error:', error)
    }
  }

  const handleDelete = async (bookId: string) => {
    try {
      await booksAPI.delete(bookId)
      loadBooks()
    } catch (error) {
      console.error('Delete error:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    try {
      const data = await memoryAPI.search(searchQuery)
      setSearchResults(data.results)
    } catch (error) {
      console.error('Search error:', error)
    }
  }

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '1rem' }}>
      {/* Stats */}
      {stats && (
        <div style={{
          background: '#1a1a1a',
          borderRadius: '0.5rem',
          padding: '1rem',
          marginBottom: '1rem',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '1rem'
        }}>
          <div>
            <div style={{ fontSize: '0.875rem', color: '#888' }}>Всего</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{stats.total_items}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.875rem', color: '#888' }}>Диалоги</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{stats.interactions}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.875rem', color: '#888' }}>Книги</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{books.length}</div>
          </div>
        </div>
      )}

      {/* Search */}
      <div style={{
        background: '#1a1a1a',
        borderRadius: '0.5rem',
        padding: '1rem',
        marginBottom: '1rem'
      }}>
        <h3 style={{ marginBottom: '0.5rem' }}>🔍 Поиск в памяти</h3>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Поиск..."
            style={{
              flex: 1,
              background: '#0a0a0a',
              border: '1px solid #333',
              borderRadius: '0.5rem',
              padding: '0.5rem',
              color: '#fff'
            }}
          />
          <button
            onClick={handleSearch}
            style={{
              background: '#3b82f6',
              border: 'none',
              borderRadius: '0.5rem',
              padding: '0.5rem 1rem',
              cursor: 'pointer'
            }}
          >
            <Search size={20} />
          </button>
        </div>

        {searchResults.length > 0 && (
          <div style={{ marginTop: '1rem' }}>
            {searchResults.map((result, idx) => (
              <div
                key={idx}
                style={{
                  background: '#0a0a0a',
                  borderRadius: '0.5rem',
                  padding: '0.75rem',
                  marginBottom: '0.5rem'
                }}
              >
                <div style={{ fontSize: '0.875rem', color: '#888', marginBottom: '0.25rem' }}>
                  Score: {result.score.toFixed(2)} | Outcome: {result.outcome_score.toFixed(2)}
                </div>
                <div>{result.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Books */}
      <div style={{
        background: '#1a1a1a',
        borderRadius: '0.5rem',
        padding: '1rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3>📚 Библиотека</h3>
          <label style={{
            background: '#3b82f6',
            borderRadius: '0.5rem',
            padding: '0.5rem 1rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Upload size={16} />
            Загрузить
            <input
              type="file"
              accept=".txt,.md"
              onChange={handleUpload}
              style={{ display: 'none' }}
            />
          </label>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {books.map((book) => (
            <div
              key={book.id}
              style={{
                background: '#0a0a0a',
                borderRadius: '0.5rem',
                padding: '0.75rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Book size={16} />
                <div>
                  <div>{book.filename}</div>
                  <div style={{ fontSize: '0.75rem', color: '#888' }}>
                    {(book.size / 1024).toFixed(1)} KB
                  </div>
                </div>
              </div>
              <button
                onClick={() => handleDelete(book.id)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#ef4444',
                  cursor: 'pointer'
                }}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
