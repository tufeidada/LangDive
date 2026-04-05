// src/components/HistoryList.tsx
import { useState, useEffect } from 'react'
import { getHistory } from '../services/api'
import ContentCard from './ContentCard'
import type { ContentItem } from '../types'

export default function HistoryList() {
  const [items, setItems] = useState<ContentItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getHistory().then(setItems).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-text-secondary">Loading history...</div>
  if (items.length === 0) return <div className="text-text-secondary">No past content yet.</div>

  return (
    <div className="space-y-3">
      {items.map(item => <ContentCard key={item.id} item={item} />)}
    </div>
  )
}
