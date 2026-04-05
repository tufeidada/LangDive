// src/components/SRSCard.tsx
import type { VocabEntry } from '../types'
import { LEVEL_COLORS, LEVEL_BG_COLORS } from '../types'

interface Props {
  word: VocabEntry
  revealed: boolean
  onReveal: () => void
}

export default function SRSCard({ word, revealed, onReveal }: Props) {
  return (
    <div className="bg-card rounded-2xl border border-border p-6 min-h-[320px] flex flex-col">
      {/* Word header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h2 className="text-3xl font-bold text-text-primary tracking-wide">{word.word}</h2>
          {word.ipa && (
            <p className="text-text-secondary text-sm mt-1">{word.ipa}</p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          {word.level && (
            <span className={`text-xs px-2 py-0.5 rounded ${LEVEL_BG_COLORS[word.level] || ''} ${LEVEL_COLORS[word.level] || ''}`}>
              {word.level}
            </span>
          )}
          <span className="text-xs text-text-secondary">SRS {word.srs_level}</span>
        </div>
      </div>

      <hr className="border-border my-4" />

      {/* Revealed content */}
      {revealed ? (
        <div className="flex-1 space-y-4 animate-fade-in">
          <div>
            <p className="text-xs text-text-secondary uppercase tracking-wider mb-1">含义</p>
            <p className="text-text-primary text-lg font-medium">{word.meaning_zh}</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <button
            onClick={onReveal}
            className="px-8 py-3 bg-elevated border border-border rounded-xl text-text-secondary hover:text-text-primary hover:border-accent transition-colors text-sm"
          >
            点击翻转
          </button>
        </div>
      )}
    </div>
  )
}
