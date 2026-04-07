// src/pages/Dashboard.tsx
import { useState, useEffect } from 'react'
import { getStats } from '../services/api'

interface DailyActivity {
  date: string
  events: number
  words_added: number
  reviews: number
}

interface Stats {
  period_days: number
  content_opened: number
  segments_completed: number
  words_added: number
  words_reviewed: number
  review_accuracy: { again: number; hard: number; easy: number }
  total_events: number
  active_days: number
  vocab_total: number
  vocab_by_status: Record<string, number>
  daily_activity: DailyActivity[]
}

const STATUS_COLORS: Record<string, string> = {
  known: 'bg-status-mastered',
  focus: 'bg-accent',
  fuzzy: 'bg-status-soon',
  unknown: 'bg-status-due',
  ignored: 'bg-elevated',
}

const STATUS_LABELS: Record<string, string> = {
  known: 'Known',
  focus: 'Focus',
  fuzzy: 'Fuzzy',
  unknown: 'Unknown',
  ignored: 'Ignored',
}

export default function Dashboard() {
  const [days, setDays] = useState(7)
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getStats(days)
      .then(data => {
        setStats(data)
        setLoading(false)
      })
      .catch(_err => {
        setError('Failed to load stats')
        setLoading(false)
      })
  }, [days])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48">
        <p className="text-text-secondary">Loading stats...</p>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="flex items-center justify-center h-48">
        <p className="text-status-due">{error || 'No data'}</p>
      </div>
    )
  }

  const totalReviews = stats.review_accuracy.again + stats.review_accuracy.hard + stats.review_accuracy.easy
  const easyPct = totalReviews > 0 ? Math.round((stats.review_accuracy.easy / totalReviews) * 100) : 0

  const totalVocab = stats.vocab_total || 1
  const statusOrder = ['known', 'focus', 'fuzzy', 'unknown', 'ignored']

  const maxDailyEvents = Math.max(...stats.daily_activity.map(d => d.events), 1)

  return (
    <div className="space-y-6">
      {/* Header + period selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-text-primary font-semibold text-lg">Learning Stats</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setDays(7)}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              days === 7
                ? 'bg-accent text-primary'
                : 'bg-elevated text-text-secondary hover:text-text-primary border border-border'
            }`}
          >
            7 days
          </button>
          <button
            onClick={() => setDays(30)}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              days === 30
                ? 'bg-accent text-primary'
                : 'bg-elevated text-text-secondary hover:text-text-primary border border-border'
            }`}
          >
            30 days
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-text-secondary text-xs mb-1">Content Read</p>
          <p className="text-accent text-2xl font-bold">{stats.content_opened}</p>
          <p className="text-text-secondary text-xs mt-1">{stats.segments_completed} segments done</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-text-secondary text-xs mb-1">Words Learned</p>
          <p className="text-status-mastered text-2xl font-bold">{stats.words_added}</p>
          <p className="text-text-secondary text-xs mt-1">{stats.vocab_total} total vocab</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-text-secondary text-xs mb-1">Reviews Done</p>
          <p className="text-status-soon text-2xl font-bold">{stats.words_reviewed}</p>
          <p className="text-text-secondary text-xs mt-1">{easyPct}% accuracy</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4">
          <p className="text-text-secondary text-xs mb-1">Active Days</p>
          <p className="text-text-primary text-2xl font-bold">{stats.active_days}</p>
          <p className="text-text-secondary text-xs mt-1">of {days} days</p>
        </div>
      </div>

      {/* Vocab distribution */}
      <div className="bg-card border border-border rounded-xl p-4 space-y-3">
        <h3 className="text-text-primary font-medium text-sm">Vocabulary Distribution</h3>
        {/* Stacked bar */}
        <div className="flex rounded-full overflow-hidden h-4 gap-px">
          {statusOrder.map(status => {
            const count = stats.vocab_by_status[status] || 0
            const pct = Math.round((count / totalVocab) * 100)
            if (pct === 0) return null
            return (
              <div
                key={status}
                className={`${STATUS_COLORS[status]} transition-all`}
                style={{ width: `${pct}%` }}
                title={`${STATUS_LABELS[status]}: ${count} (${pct}%)`}
              />
            )
          })}
        </div>
        {/* Legend */}
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {statusOrder.map(status => {
            const count = stats.vocab_by_status[status] || 0
            return (
              <div key={status} className="flex items-center gap-1.5">
                <div className={`w-2.5 h-2.5 rounded-sm ${STATUS_COLORS[status]}`} />
                <span className="text-text-secondary text-xs">{STATUS_LABELS[status]}</span>
                <span className="text-text-primary text-xs font-medium">{count}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Review accuracy */}
      {totalReviews > 0 && (
        <div className="bg-card border border-border rounded-xl p-4 space-y-3">
          <h3 className="text-text-primary font-medium text-sm">Review Accuracy</h3>
          <div className="space-y-2">
            {[
              { label: 'Easy', key: 'easy' as const, color: 'bg-status-mastered' },
              { label: 'Hard', key: 'hard' as const, color: 'bg-status-soon' },
              { label: 'Again', key: 'again' as const, color: 'bg-status-due' },
            ].map(({ label, key, color }) => {
              const count = stats.review_accuracy[key]
              const pct = totalReviews > 0 ? Math.round((count / totalReviews) * 100) : 0
              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-text-secondary text-xs w-10">{label}</span>
                  <div className="flex-1 bg-elevated rounded-full h-2">
                    <div
                      className={`${color} h-2 rounded-full transition-all`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-text-secondary text-xs w-12 text-right">{count} ({pct}%)</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Daily activity chart */}
      <div className="bg-card border border-border rounded-xl p-4 space-y-3">
        <h3 className="text-text-primary font-medium text-sm">Daily Activity</h3>
        <div className="flex items-end gap-1 h-20">
          {stats.daily_activity.map(day => {
            const heightPct = Math.round((day.events / maxDailyEvents) * 100)
            const label = day.date.slice(5) // MM-DD
            return (
              <div key={day.date} className="flex-1 flex flex-col items-center gap-1" title={`${day.date}: ${day.events} events, ${day.words_added} words, ${day.reviews} reviews`}>
                <div className="w-full flex flex-col justify-end" style={{ height: '64px' }}>
                  <div
                    className="w-full bg-accent/70 rounded-t transition-all"
                    style={{ height: heightPct > 0 ? `${heightPct}%` : '2px', minHeight: day.events > 0 ? '4px' : '0' }}
                  />
                </div>
                {days <= 14 && (
                  <span className="text-text-secondary text-xs leading-none" style={{ fontSize: '9px' }}>
                    {label}
                  </span>
                )}
              </div>
            )
          })}
        </div>
        <p className="text-text-secondary text-xs text-center">{stats.total_events} total events over {days} days</p>
      </div>
    </div>
  )
}
