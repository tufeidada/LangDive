// src/components/AddWordModal.tsx
import { useState } from 'react'
import { X, Sparkles, Loader2 } from 'lucide-react'
import { addWord, aiLookup } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'

interface Props {
  word: string
  contextSentence?: string
  onClose: () => void
}

export default function AddWordModal({ word, contextSentence, onClose }: Props) {
  const { log } = useEventLogger()
  const [meaningZh, setMeaningZh] = useState('')
  const [lookingUp, setLookingUp] = useState(false)
  const [looked, setLooked] = useState(false)

  const handleAILookup = async () => {
    setLookingUp(true)
    try {
      const result = await aiLookup(word, contextSentence)
      if (result?.meaning_zh) setMeaningZh(result.meaning_zh)
      setLooked(true)
    } finally {
      setLookingUp(false)
    }
  }

  const handleAdd = async () => {
    await addWord(word, meaningZh || undefined)
    log('word_custom_add', { word })
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-elevated rounded-xl border border-border p-6 w-80">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-text-primary font-bold text-lg">Add Word</h3>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="text-accent font-medium text-xl mb-4">{word}</div>

        <div className="mb-4">
          <label className="text-text-secondary text-sm mb-1 block">Chinese meaning</label>
          <input
            type="text"
            value={meaningZh}
            onChange={e => setMeaningZh(e.target.value)}
            placeholder="Enter meaning or use AI lookup"
            className="w-full bg-card border border-border rounded-lg px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleAILookup}
            disabled={lookingUp || looked}
            className="flex-1 bg-card border border-border text-text-secondary text-sm py-2 rounded-lg flex items-center justify-center gap-1 hover:text-accent disabled:opacity-50"
          >
            {lookingUp ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            AI Lookup
          </button>
          <button
            onClick={handleAdd}
            className="flex-1 bg-accent text-primary font-medium text-sm py-2 rounded-lg"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  )
}
