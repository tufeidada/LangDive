// src/pages/Home.tsx
import { useState, useEffect, useMemo } from 'react'
import { RefreshCw } from 'lucide-react'
import { getToday } from '../services/api'
import ContentCard from '../components/ContentCard'
import HistoryList from '../components/HistoryList'
import VocabBook from '../components/VocabBook'
import type { ContentItem } from '../types'

type Tab = 'today' | 'history' | 'vocab'

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

function CardSkeleton() {
  return (
    <div className="bg-card rounded-xl p-4 border border-border animate-pulse">
      <div className="flex items-start gap-3">
        <div className="mt-1 w-5 h-5 bg-elevated rounded" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-elevated rounded w-3/4" />
          <div className="flex gap-2">
            <div className="h-3 bg-elevated rounded w-20" />
            <div className="h-3 bg-elevated rounded w-10" />
            <div className="h-3 bg-elevated rounded w-16" />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Home() {
  const [tab, setTab] = useState<Tab>('today')
  const [items, setItems] = useState<ContentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    getToday()
      .then(setItems)
      .catch((e: any) => setError(e.message || 'Failed to load content'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
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
          <div className="space-y-3">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <p className="text-text-secondary text-sm">{error}</p>
            <button
              onClick={load}
              className="flex items-center gap-2 px-4 py-2 bg-elevated border border-border rounded-lg text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="text-text-secondary text-sm text-center py-12">
            No content for today. Pipeline may not have run yet.
          </div>
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
