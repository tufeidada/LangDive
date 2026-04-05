// src/components/VocabBook.tsx
import { useState, useEffect } from 'react'
import { Search } from 'lucide-react'
import { getVocab, updateWordStatus } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'
import type { VocabEntry, WordStatus } from '../types'
import { LEVEL_COLORS, LEVEL_BG_COLORS } from '../types'

const STATUS_LABELS: Record<WordStatus, string> = {
  unknown: 'Unknown',
  fuzzy: 'Fuzzy',
  known: 'Known',
  focus: 'Focus',
  ignored: 'Ignored',
}

const STATUS_COLORS: Record<WordStatus, string> = {
  unknown: 'text-text-secondary',
  fuzzy: 'text-yellow-400',
  known: 'text-status-mastered',
  focus: 'text-accent',
  ignored: 'text-text-secondary/50',
}

export default function VocabBook() {
  const { log } = useEventLogger()
  const [words, setWords] = useState<VocabEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState<WordStatus | 'all'>('all')

  useEffect(() => {
    loadWords()
  }, [])

  const loadWords = async () => {
    setLoading(true)
    try {
      const data = await getVocab()
      setWords(data)
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = async (word: string, status: WordStatus) => {
    await updateWordStatus(word, status)
    log('word_status_change', { word, status })
    await loadWords()
  }

  const filtered = words.filter(w => {
    if (search && !w.word.toLowerCase().includes(search.toLowerCase())) return false
    if (filterStatus !== 'all' && w.status !== filterStatus) return false
    return true
  })

  if (loading) return <div className="text-text-secondary">Loading vocabulary...</div>

  return (
    <div>
      {/* Search + filter */}
      <div className="flex gap-2 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search words..."
            className="w-full bg-card border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value as WordStatus | 'all')}
          className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none"
        >
          <option value="all">All ({words.length})</option>
          {(Object.keys(STATUS_LABELS) as WordStatus[]).map(s => (
            <option key={s} value={s}>{STATUS_LABELS[s]} ({words.filter(w => w.status === s).length})</option>
          ))}
        </select>
      </div>

      {/* Word list */}
      <div className="space-y-2">
        {filtered.length === 0 && <div className="text-text-secondary text-sm">No words found.</div>}
        {filtered.map(w => (
          <div key={w.word} className="bg-card rounded-lg p-3 border border-border">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-text-primary font-medium">{w.word}</span>
                {w.ipa && <span className="text-text-secondary text-xs ml-2">{w.ipa}</span>}
                {w.level && (
                  <span className={`text-xs px-1.5 py-0.5 rounded ml-2 ${LEVEL_BG_COLORS[w.level] || ''} ${LEVEL_COLORS[w.level] || ''}`}>
                    {w.level}
                  </span>
                )}
              </div>
              <select
                value={w.status}
                onChange={e => handleStatusChange(w.word, e.target.value as WordStatus)}
                className={`text-xs bg-transparent border-none ${STATUS_COLORS[w.status as WordStatus] || ''}`}
              >
                {(Object.keys(STATUS_LABELS) as WordStatus[]).map(s => (
                  <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                ))}
              </select>
            </div>
            <div className="text-text-secondary text-sm mt-1">{w.meaning_zh}</div>
            <div className="text-text-secondary text-xs mt-1">
              SRS Level {w.srs_level} · {w.added_method}
              {w.next_review && ` · Next: ${new Date(w.next_review).toLocaleDateString()}`}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
