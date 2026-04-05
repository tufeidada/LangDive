// src/components/WordPopup.tsx
import { X, Plus, Check, Ban } from 'lucide-react'
import { addWord, updateWordStatus } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'
import type { VocabWord } from '../types'
import { LEVEL_COLORS } from '../types'

interface Props {
  word: VocabWord
  position: { x: number; y: number }
  onClose: () => void
}

export default function WordPopup({ word, position, onClose }: Props) {
  const { log } = useEventLogger()

  const handleAdd = async () => {
    await addWord(word.word, word.meaning_zh)
    log('word_add', { word: word.word })
    onClose()
  }

  const handleKnown = async () => {
    await updateWordStatus(word.word, 'known')
    log('word_status_change', { word: word.word, status: 'known' })
    onClose()
  }

  const handleIgnore = async () => {
    await updateWordStatus(word.word, 'ignored')
    log('word_status_change', { word: word.word, status: 'ignored' })
    onClose()
  }

  return (
    <div
      className="fixed z-50 bg-elevated rounded-xl shadow-xl border border-border p-4 w-72"
      style={{ left: Math.min(position.x, window.innerWidth - 300), top: position.y + 10 }}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <span className="text-text-primary font-bold text-lg">{word.word}</span>
          <span className="text-text-secondary text-sm ml-2">{word.ipa}</span>
        </div>
        <button onClick={onClose} className="text-text-secondary hover:text-text-primary">
          <X className="w-4 h-4" />
        </button>
      </div>

      {word.level && (
        <span className={`text-xs px-1.5 py-0.5 rounded ${LEVEL_COLORS[word.level] || 'text-text-secondary'}`}>
          {word.level}
        </span>
      )}

      <div className="text-text-primary text-sm mt-2">{word.meaning_zh}</div>
      {word.detail_zh && <div className="text-text-secondary text-xs mt-1">{word.detail_zh}</div>}
      {word.example_en && (
        <div className="mt-2 text-sm">
          <div className="text-text-primary italic">"{word.example_en}"</div>
          {word.example_zh && <div className="text-text-secondary text-xs">{word.example_zh}</div>}
        </div>
      )}

      <div className="flex gap-2 mt-3">
        <button onClick={handleAdd} className="flex-1 bg-accent text-primary text-xs font-medium py-1.5 rounded flex items-center justify-center gap-1">
          <Plus className="w-3 h-3" /> Add
        </button>
        <button onClick={handleKnown} className="flex-1 bg-card text-text-secondary text-xs py-1.5 rounded flex items-center justify-center gap-1 hover:text-text-primary">
          <Check className="w-3 h-3" /> Known
        </button>
        <button onClick={handleIgnore} className="bg-card text-text-secondary text-xs py-1.5 px-2 rounded flex items-center justify-center gap-1 hover:text-text-primary">
          <Ban className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}
