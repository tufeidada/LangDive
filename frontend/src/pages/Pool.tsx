// src/pages/Pool.tsx — Hidden admin page, accessible via /pool only
import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { getCandidates, promoteCandidate, rejectCandidate } from '../services/api'
import CandidateCard from '../components/CandidateCard'
import SourceManager from '../components/SourceManager'
import UrlSubmitForm from '../components/UrlSubmitForm'
import PipelineStatus from '../components/PipelineStatus'

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

const SELECTED_STATUSES = new Set(['selected', 'user_promoted', 'user_submitted'])

export default function Pool() {
  const [date, setDate] = useState(todayStr())
  const [candidates, setCandidates] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [showAllUnselected, setShowAllUnselected] = useState(false)

  const load = useCallback(async (d: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await getCandidates(d)
      // API may return { candidates: [...] } or directly an array
      setCandidates(Array.isArray(data) ? data : (data.candidates ?? []))
    } catch (e: any) {
      setError(e.message || 'Failed to load candidates')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(date)
  }, [date, load])

  const handlePromote = async (id: number) => {
    setActionLoading(id)
    try {
      await promoteCandidate(id)
      // Optimistically update status
      setCandidates(prev =>
        prev.map(c => c.id === id ? { ...c, status: 'user_promoted' } : c)
      )
    } catch (e: any) {
      setError(e.message)
    } finally {
      setActionLoading(null)
    }
  }

  const handleReject = async (id: number) => {
    setActionLoading(id)
    try {
      await rejectCandidate(id)
      setCandidates(prev =>
        prev.map(c => c.id === id ? { ...c, status: 'user_rejected' } : c)
      )
    } catch (e: any) {
      setError(e.message)
    } finally {
      setActionLoading(null)
    }
  }

  const selected = candidates.filter(c => SELECTED_STATUSES.has(c.status))
  const unselected = candidates.filter(c => !SELECTED_STATUSES.has(c.status) && c.status !== 'user_rejected')
  const visibleUnselected = showAllUnselected ? unselected : unselected.slice(0, 3)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-text-primary font-bold text-xl">Content Pool</h1>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
            className="bg-card border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent"
          />
          <button
            onClick={() => load(date)}
            disabled={loading}
            className="p-2 bg-card border border-border rounded-lg text-text-secondary hover:text-text-primary hover:border-accent/50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* URL Submit */}
      <UrlSubmitForm onSubmitted={() => load(date)} />

      {/* Source Manager */}
      <SourceManager />

      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg px-4 py-2 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-text-secondary text-sm py-4">Loading candidates...</div>
      ) : (
        <>
          {/* Selected */}
          <section>
            <h2 className="text-sm font-semibold text-text-secondary mb-2 uppercase tracking-wide">
              Today's Selected ({selected.length})
            </h2>
            {selected.length === 0 ? (
              <p className="text-text-secondary text-xs px-2">No items selected yet.</p>
            ) : (
              <div className="space-y-2">
                {selected.map(c => (
                  <CandidateCard
                    key={c.id}
                    candidate={c}
                    mode="selected"
                    onAction={handleReject}
                    loading={actionLoading === c.id}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Unselected candidates */}
          <section>
            <h2 className="text-sm font-semibold text-text-secondary mb-2 uppercase tracking-wide">
              Candidates Not Selected ({unselected.length})
            </h2>
            {unselected.length === 0 ? (
              <p className="text-text-secondary text-xs px-2">No unselected candidates.</p>
            ) : (
              <>
                <div className="space-y-2">
                  {visibleUnselected.map(c => (
                    <CandidateCard
                      key={c.id}
                      candidate={c}
                      mode="unselected"
                      onAction={handlePromote}
                      loading={actionLoading === c.id}
                    />
                  ))}
                </div>
                {unselected.length > 3 && (
                  <button
                    onClick={() => setShowAllUnselected(v => !v)}
                    className="mt-2 flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary transition-colors"
                  >
                    {showAllUnselected ? (
                      <><ChevronUp className="w-3.5 h-3.5" /> Show fewer</>
                    ) : (
                      <><ChevronDown className="w-3.5 h-3.5" /> Show all {unselected.length}</>
                    )}
                  </button>
                )}
              </>
            )}
          </section>

          {/* Pipeline Status */}
          <PipelineStatus candidates={candidates} />
        </>
      )}
    </div>
  )
}
