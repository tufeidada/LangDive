// src/pages/Review.tsx
import { useState, useEffect, useRef, useCallback } from 'react'
import { CheckCircle, RotateCcw } from 'lucide-react'
import SRSCard from '../components/SRSCard'
import { getReviewWords, reviewWord, logEvent } from '../services/api'
import type { VocabEntry } from '../types'

type SessionState = 'loading' | 'empty' | 'session' | 'done'

export default function Review() {
  const [state, setState] = useState<SessionState>('loading')
  const [queue, setQueue] = useState<VocabEntry[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [grading, setGrading] = useState(false)
  const [sessionStartTime] = useState(() => Date.now())
  const [reviewedCount, setReviewedCount] = useState(0)
  const startedRef = useRef(false)

  // Load due words once on mount
  useEffect(() => {
    getReviewWords()
      .then(words => {
        setQueue(words)
        if (words.length === 0) {
          setState('empty')
        } else {
          setState('session')
          if (!startedRef.current) {
            startedRef.current = true
            logEvent('review_start', { word_count: words.length })
          }
        }
      })
      .catch(() => setState('empty'))
  }, [])

  // Log review_exit on page unload if session is in progress
  useEffect(() => {
    const handleUnload = () => {
      if (state === 'session' && queue.length > 0) {
        const remaining = queue.length - currentIndex
        logEvent('review_exit', { reviewed: reviewedCount, remaining })
      }
    }
    window.addEventListener('beforeunload', handleUnload)
    return () => window.removeEventListener('beforeunload', handleUnload)
  }, [state, queue.length, currentIndex, reviewedCount])

  const currentWord = queue[currentIndex]

  const handleGrade = useCallback(async (grade: 0 | 1 | 2) => {
    if (!currentWord || grading) return
    setGrading(true)
    try {
      const result = await reviewWord(currentWord.word, grade)
      logEvent('review_grade', {
        word: currentWord.word,
        grade,
        srs_level: result.srs_level,
      })
      const nextCount = reviewedCount + 1
      setReviewedCount(nextCount)

      if (currentIndex + 1 >= queue.length) {
        const durationSec = Math.round((Date.now() - sessionStartTime) / 1000)
        logEvent('review_complete', { total: nextCount, duration_sec: durationSec })
        setState('done')
      } else {
        setCurrentIndex(i => i + 1)
        setRevealed(false)
      }
    } finally {
      setGrading(false)
    }
  }, [currentWord, grading, currentIndex, queue.length, reviewedCount, sessionStartTime])

  // Keyboard shortcuts: Space = reveal, 1/2/3 = grade
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (state !== 'session') return
      if (e.key === ' ' && !revealed) {
        e.preventDefault()
        setRevealed(true)
      } else if (revealed && !grading) {
        if (e.key === '1') handleGrade(0)
        else if (e.key === '2') handleGrade(1)
        else if (e.key === '3') handleGrade(2)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [state, revealed, grading, handleGrade])

  if (state === 'loading') {
    return (
      <div className="flex items-center justify-center h-48">
        <p className="text-text-secondary">Loading review queue...</p>
      </div>
    )
  }

  if (state === 'empty') {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <CheckCircle className="w-12 h-12 text-status-mastered" />
        <p className="text-text-primary font-medium">今日复习完成</p>
        <p className="text-text-secondary text-sm">No words due for review today.</p>
      </div>
    )
  }

  if (state === 'done') {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <CheckCircle className="w-12 h-12 text-status-mastered" />
        <p className="text-text-primary font-medium text-lg">复习完成！</p>
        <p className="text-text-secondary text-sm">Reviewed {reviewedCount} word{reviewedCount !== 1 ? 's' : ''} today.</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 flex items-center gap-2 px-4 py-2 bg-elevated border border-border rounded-lg text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          <RotateCcw className="w-4 h-4" />
          Check for more
        </button>
      </div>
    )
  }

  // session
  const progress = currentIndex / queue.length

  return (
    <div className="space-y-4">
      {/* Header: progress + cap display */}
      <div className="flex items-center justify-between text-sm text-text-secondary">
        <span>{currentIndex + 1} / {queue.length}</span>
        <span className="text-xs">Daily cap: {queue.length} words</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-elevated rounded-full h-1.5">
        <div
          className="bg-accent h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      {/* Flashcard */}
      {currentWord && (
        <SRSCard
          word={currentWord}
          revealed={revealed}
          onReveal={() => setRevealed(true)}
        />
      )}

      {/* Grade buttons — only show after reveal */}
      {revealed && (
        <div className="grid grid-cols-3 gap-3">
          <button
            onClick={() => handleGrade(0)}
            disabled={grading}
            className="flex flex-col items-center py-3 px-2 rounded-xl border border-status-due/40 bg-status-due/10 hover:bg-status-due/20 transition-colors disabled:opacity-50"
          >
            <span className="text-status-due font-semibold text-sm">Again</span>
            <span className="text-status-due/70 text-xs mt-0.5">再来</span>
            <span className="text-text-secondary text-xs mt-1">[ 1 ]</span>
          </button>
          <button
            onClick={() => handleGrade(1)}
            disabled={grading}
            className="flex flex-col items-center py-3 px-2 rounded-xl border border-status-soon/40 bg-status-soon/10 hover:bg-status-soon/20 transition-colors disabled:opacity-50"
          >
            <span className="text-status-soon font-semibold text-sm">Hard</span>
            <span className="text-status-soon/70 text-xs mt-0.5">较难</span>
            <span className="text-text-secondary text-xs mt-1">[ 2 ]</span>
          </button>
          <button
            onClick={() => handleGrade(2)}
            disabled={grading}
            className="flex flex-col items-center py-3 px-2 rounded-xl border border-status-mastered/40 bg-status-mastered/10 hover:bg-status-mastered/20 transition-colors disabled:opacity-50"
          >
            <span className="text-status-mastered font-semibold text-sm">Easy</span>
            <span className="text-status-mastered/70 text-xs mt-0.5">掌握</span>
            <span className="text-text-secondary text-xs mt-1">[ 3 ]</span>
          </button>
        </div>
      )}

      {/* Keyboard hint */}
      {!revealed && (
        <p className="text-center text-text-secondary text-xs">
          Press <kbd className="px-1.5 py-0.5 bg-elevated border border-border rounded text-xs">Space</kbd> to reveal
        </p>
      )}
    </div>
  )
}
