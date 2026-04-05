// src/components/PreviewScreen.tsx
import { useState } from 'react'
import { Eye, Plus, ChevronsRight } from 'lucide-react'
import { updateWordStatus, previewAddAll } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'
import type { PreStudyWord } from '../types'

interface Props {
  words: PreStudyWord[]
  segmentTitle: string
  onStart: () => void
}

export default function PreviewScreen({ words, segmentTitle, onStart }: Props) {
  const { log } = useEventLogger()
  const [wordList, setWordList] = useState(
    [...words].sort((a, b) => b.freq_in_content - a.freq_in_content || b.importance_score - a.importance_score)
  )

  const handleKnow = async (word: string) => {
    await updateWordStatus(word, 'known')
    setWordList(prev => prev.filter(w => w.word !== word))
    log('word_status_change', { word, status: 'known' })
  }

  const handleAddAll = async () => {
    const unknowns = wordList.filter(w => w.known_status === 'unknown')
    if (unknowns.length === 0) return
    await previewAddAll(unknowns.map(w => ({ word: w.word, meaning_zh: w.meaning_zh })))
    log('preview_add_all', { count: unknowns.length })
    onStart()
  }

  const handleSkip = () => {
    log('preview_skip')
    onStart()
  }

  return (
    <div>
      <h2 className="text-text-primary font-medium mb-1">{segmentTitle}</h2>
      <p className="text-text-secondary text-sm mb-4">
        {wordList.length} words to preview
      </p>

      <div className="space-y-2 mb-6">
        {wordList.map(w => (
          <div key={w.word} className="bg-card rounded-lg p-3 border border-border">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-text-primary font-medium">{w.word}</span>
                <span className="text-text-secondary text-xs ml-2">{w.ipa}</span>
              </div>
              <button
                onClick={() => handleKnow(w.word)}
                className="text-xs text-text-secondary hover:text-accent flex items-center gap-1"
              >
                <Eye className="w-3 h-3" /> I know this
              </button>
            </div>
            <div className="text-text-secondary text-sm mt-1">{w.meaning_zh}</div>
            {w.example_in_context && (
              <div className="text-text-secondary text-xs mt-1 italic">"{w.example_in_context}"</div>
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleAddAll}
          className="flex-1 bg-accent text-primary font-medium py-2.5 rounded-lg flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" /> Add all unknown
        </button>
        <button
          onClick={handleSkip}
          className="px-4 py-2.5 border border-border rounded-lg text-text-secondary hover:text-text-primary flex items-center gap-2"
        >
          <ChevronsRight className="w-4 h-4" /> Skip
        </button>
      </div>
    </div>
  )
}
