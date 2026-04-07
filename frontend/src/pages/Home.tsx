// src/pages/Home.tsx
import { useState, useEffect, useMemo } from 'react'
import { getToday } from '../services/api'
import ContentCard from '../components/ContentCard'
import HistoryList from '../components/HistoryList'
import VocabBook from '../components/VocabBook'
import type { ContentItem } from '../types'

type Tab = 'today' | 'history' | 'vocab'

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function Home() {
  const [tab, setTab] = useState<Tab>('today')
  const [items, setItems] = useState<ContentItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getToday().then(setItems).finally(() => setLoading(false))
  }, [])

  // Group items by date, sorted newest first
  const grouped = useMemo(() => {
    const map = new Map<string, ContentItem[]>()
    for (const item of items) {
      const d = item.date
      if (!map.has(d)) map.set(d, [])
      map.get(d)!.push(item)
    }
    return Array.from(map.entries()).sort((a, b) => b[0].localeCompare(a[0]))
  }, [items])

  return (
    <div>
      <div className="flex gap-1 mb-6 bg-card rounded-lg p-1">
        {(['today', 'history', 'vocab'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
              tab === t ? 'bg-accent text-primary' : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {t === 'today' ? 'Now' : t === 'history' ? 'Archive' : 'Vocab'}
          </button>
        ))}
      </div>

      {tab === 'today' && (
        loading ? (
          <div className="text-text-secondary">Loading today's content...</div>
        ) : items.length === 0 ? (
          <div className="text-text-secondary">No content for today. Pipeline may not have run yet.</div>
        ) : (
          <div className="space-y-6">
            {grouped.map(([date, dateItems]) => (
              <div key={date}>
                <h3 className="text-text-secondary text-sm mb-2">
                  {date === todayStr() ? 'Today' : date}
                </h3>
                <div className="space-y-3">
                  {dateItems.map(item => <ContentCard key={item.id} item={item} />)}
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {tab === 'history' && <HistoryList />}
      {tab === 'vocab' && <VocabBook />}
    </div>
  )
}
