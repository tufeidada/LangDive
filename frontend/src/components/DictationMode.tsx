// src/components/DictationMode.tsx
import { useState, useEffect, useCallback } from 'react'
import { X, Volume2, ChevronRight, RotateCcw } from 'lucide-react'
import { logEvent } from '../services/api'

interface Props {
  sentences: string[]
  onExit: () => void
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s']/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

interface WordResult {
  word: string
  status: 'correct' | 'wrong' | 'extra'
}

function diffWords(expected: string, actual: string): { expectedResults: WordResult[]; extraWords: WordResult[] } {
  const expectedWords = normalize(expected).split(/\s+/).filter(Boolean)
  const actualWords = normalize(actual).split(/\s+/).filter(Boolean)

  // Build a frequency map of actual words
  const actualFreq = new Map<string, number>()
  for (const w of actualWords) {
    actualFreq.set(w, (actualFreq.get(w) ?? 0) + 1)
  }

  const expectedResults: WordResult[] = expectedWords.map(word => {
    const count = actualFreq.get(word) ?? 0
    if (count > 0) {
      actualFreq.set(word, count - 1)
      return { word, status: 'correct' }
    }
    return { word, status: 'wrong' }
  })

  // Extra words: words in actual that weren't matched to expected
  const matchedFreq = new Map<string, number>()
  for (const r of expectedResults) {
    if (r.status === 'correct') {
      matchedFreq.set(r.word, (matchedFreq.get(r.word) ?? 0) + 1)
    }
  }
  const extraWords: WordResult[] = []
  for (const w of actualWords) {
    const matched = matchedFreq.get(w) ?? 0
    if (matched > 0) {
      matchedFreq.set(w, matched - 1)
    } else {
      extraWords.push({ word: w, status: 'extra' })
    }
  }

  return { expectedResults, extraWords }
}

export default function DictationMode({ sentences, onExit }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [userInput, setUserInput] = useState('')
  const [checked, setChecked] = useState(false)
  const [results, setResults] = useState<{ correct: number; total: number }>({ correct: 0, total: 0 })
  const [diffResult, setDiffResult] = useState<{ expectedResults: WordResult[]; extraWords: WordResult[]; accuracy: number } | null>(null)
  const [finished, setFinished] = useState(false)

  const currentSentence = sentences[currentIndex] ?? ''
  const total = sentences.length

  const playSentence = useCallback((rate = 0.85) => {
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(currentSentence.trim())
    utterance.lang = 'en-US'
    utterance.rate = rate
    window.speechSynthesis.speak(utterance)
  }, [currentSentence])

  // Auto-play when sentence changes
  useEffect(() => {
    if (!finished) {
      playSentence()
    }
    return () => {
      window.speechSynthesis.cancel()
    }
  }, [currentIndex, finished])

  // Log dictation start
  useEffect(() => {
    logEvent('dictation_start', { total_sentences: total })
  }, [])

  const handleCheck = () => {
    const { expectedResults, extraWords } = diffWords(currentSentence, userInput)
    const correctCount = expectedResults.filter(r => r.status === 'correct').length
    const totalExpected = expectedResults.length
    const accuracy = totalExpected > 0 ? correctCount / totalExpected : 0

    setDiffResult({ expectedResults, extraWords, accuracy })
    setChecked(true)

    const isPerfect = accuracy === 1 && extraWords.length === 0
    setResults(prev => ({
      correct: prev.correct + (isPerfect ? 1 : 0),
      total: prev.total + 1,
    }))

    logEvent('dictation_check', {
      sentence_index: currentIndex,
      accuracy: Math.round(accuracy * 100),
    })
  }

  const handleNext = () => {
    if (currentIndex + 1 >= total) {
      setFinished(true)
      logEvent('dictation_complete', {
        score: results.correct,
        total,
      })
    } else {
      setCurrentIndex(i => i + 1)
      setUserInput('')
      setChecked(false)
      setDiffResult(null)
    }
  }

  const handleRestart = () => {
    setCurrentIndex(0)
    setUserInput('')
    setChecked(false)
    setDiffResult(null)
    setResults({ correct: 0, total: 0 })
    setFinished(false)
    logEvent('dictation_start', { total_sentences: total })
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!checked) handleCheck()
      else handleNext()
    }
  }

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="font-semibold text-text-primary text-sm">Dictation Mode</span>
        <button
          onClick={onExit}
          className="flex items-center gap-1 text-xs text-text-secondary hover:text-accent transition-colors"
        >
          <X className="w-4 h-4" /> Exit
        </button>
      </div>

      {finished ? (
        /* ── Final score screen ── */
        <div className="p-6 text-center space-y-4">
          <div className="text-4xl font-bold text-accent">
            {results.correct} / {results.total}
          </div>
          <div className="text-text-secondary text-sm">sentences with 100% accuracy</div>
          <div className="text-text-secondary text-xs">
            {results.correct === results.total
              ? 'Perfect score!'
              : results.correct >= Math.ceil(results.total / 2)
              ? 'Good job!'
              : 'Keep practising!'}
          </div>
          <div className="flex justify-center gap-3 pt-2">
            <button
              onClick={handleRestart}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-border text-text-secondary hover:border-accent hover:text-accent text-sm transition-colors"
            >
              <RotateCcw className="w-4 h-4" /> Try Again
            </button>
            <button
              onClick={onExit}
              className="px-4 py-2 rounded-lg bg-accent text-primary font-medium text-sm"
            >
              Done
            </button>
          </div>
        </div>
      ) : (
        <div className="p-4 space-y-4">
          {/* Progress */}
          <div className="flex items-center justify-between text-xs text-text-secondary">
            <span>Sentence {currentIndex + 1} / {total}</span>
            <span>Score: {results.correct} / {results.total} perfect</span>
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-border rounded-full overflow-hidden">
            <div
              className="h-full bg-accent transition-all duration-300"
              style={{ width: `${((currentIndex) / total) * 100}%` }}
            />
          </div>

          {/* Play buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => playSentence(0.85)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:border-accent hover:text-accent text-sm transition-colors"
            >
              <Volume2 className="w-4 h-4" /> Play
            </button>
            <button
              onClick={() => playSentence(0.6)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:border-accent hover:text-accent text-sm transition-colors"
            >
              <Volume2 className="w-4 h-4" /> Play Slow
            </button>
          </div>

          {/* Input area */}
          <div>
            <textarea
              value={userInput}
              onChange={e => setUserInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={checked}
              placeholder="Type what you hear... (Enter to check)"
              rows={3}
              className="w-full bg-primary border border-border rounded-lg px-3 py-2 text-text-primary text-sm placeholder:text-text-secondary/50 resize-none focus:outline-none focus:border-accent disabled:opacity-60 transition-colors"
            />
          </div>

          {/* Check button */}
          {!checked && (
            <button
              onClick={handleCheck}
              disabled={!userInput.trim()}
              className="px-4 py-2 bg-accent text-primary font-medium text-sm rounded-lg disabled:opacity-40 transition-opacity"
            >
              Check
            </button>
          )}

          {/* Result display */}
          {checked && diffResult && (
            <div className="space-y-3">
              {/* Word-level diff */}
              <div className="bg-primary rounded-lg p-3 border border-border space-y-2">
                {/* Expected sentence with colour coding */}
                <div className="text-xs text-text-secondary mb-1">Original:</div>
                <div className="text-sm leading-relaxed flex flex-wrap gap-1">
                  {diffResult.expectedResults.map((r, i) => (
                    <span
                      key={i}
                      className={
                        r.status === 'correct'
                          ? 'text-green-400 font-medium'
                          : 'text-red-400 font-medium line-through'
                      }
                    >
                      {r.word}
                    </span>
                  ))}
                </div>

                {/* Extra words the user typed */}
                {diffResult.extraWords.length > 0 && (
                  <div className="text-xs text-text-secondary mt-1">
                    Extra words:{' '}
                    {diffResult.extraWords.map((r, i) => (
                      <span key={i} className="text-yellow-400 font-medium mr-1">{r.word}</span>
                    ))}
                  </div>
                )}

                {/* Accuracy summary */}
                <div className="flex items-center gap-1.5 text-xs pt-1 border-t border-border">
                  <span className={diffResult.accuracy === 1 ? 'text-green-400' : 'text-text-secondary'}>
                    {diffResult.accuracy === 1 ? '✅' : '📝'}
                  </span>
                  <span className="text-text-secondary">
                    {diffResult.expectedResults.filter(r => r.status === 'correct').length}
                    {' / '}
                    {diffResult.expectedResults.length} words correct
                    {' '}
                    ({Math.round(diffResult.accuracy * 100)}%)
                  </span>
                </div>
              </div>

              {/* Next button */}
              <button
                onClick={handleNext}
                className="flex items-center gap-1.5 px-4 py-2 bg-accent text-primary font-medium text-sm rounded-lg"
              >
                {currentIndex + 1 >= total ? 'See Results' : 'Next Sentence'}
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
