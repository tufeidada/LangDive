// src/components/ArticleReader.tsx
import { useState, useCallback, useMemo } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { markSegmentComplete } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'
import WordPopup from './WordPopup'
import GlossarySection from './GlossarySection'
import AudioPlayer from './AudioPlayer'
import AddWordModal from './AddWordModal'
import type { Segment, VocabWord } from '../types'
import { LEVEL_COLORS } from '../types'

interface Props {
  segment: Segment
  contentId: number
}

export default function ArticleReader({ segment, contentId }: Props) {
  const { log } = useEventLogger()
  const [expanded, setExpanded] = useState(false)
  const [popupWord, setPopupWord] = useState<{ word: VocabWord; pos: { x: number; y: number } } | null>(null)
  const [completed, setCompleted] = useState(segment.is_completed)
  const [addWordModal, setAddWordModal] = useState<{ word: string; context: string } | null>(null)

  // Build word lookup map
  const wordMap = useMemo(() => {
    const map = new Map<string, VocabWord>()
    if (segment.words_json) {
      for (const w of segment.words_json) {
        map.set(w.word.toLowerCase(), w)
      }
    }
    return map
  }, [segment.words_json])

  // Annotate text: split into tokens, mark annotated words
  const annotatedContent = useMemo(() => {
    const text = segment.text_en
    const tokens = text.split(/(\s+)/)
    return tokens.map((token, i) => {
      const clean = token.replace(/[^a-zA-Z'-]/g, '').toLowerCase()
      const wordData = wordMap.get(clean)
      if (wordData) {
        return { key: i, text: token, word: wordData, isWord: true }
      }
      return { key: i, text: token, word: null, isWord: false }
    })
  }, [segment.text_en, wordMap])

  const handleWordClick = (word: VocabWord, e: React.MouseEvent) => {
    log('word_lookup', { word: word.word })
    setPopupWord({ word, pos: { x: e.clientX, y: e.clientY } })
  }

  const handleDoubleClick = useCallback((_e: React.MouseEvent) => {
    const selection = window.getSelection()?.toString().trim()
    if (!selection) return
    if (selection.includes(' ') || selection.length < 2 || selection.length > 30) return
    if (wordMap.has(selection.toLowerCase())) return
    // Find context sentence
    const text = segment.text_en
    const sentences = text.split(/[.!?]+/)
    const contextSentence = sentences.find(s => s.toLowerCase().includes(selection.toLowerCase()))?.trim() || ''
    setAddWordModal({ word: selection, context: contextSentence })
    log('word_custom_add', { word: selection })
  }, [wordMap, segment.text_en, log])

  const handleComplete = async () => {
    await markSegmentComplete(contentId, segment.segment_index)
    setCompleted(true)
    log('segment_complete', { content_id: contentId, segment_index: segment.segment_index })
  }

  return (
    <div onDoubleClick={handleDoubleClick}>
      {/* Controls */}
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={() => { setExpanded(!expanded); log('toggle_expand') }}
          className="flex items-center gap-1 text-sm text-text-secondary hover:text-accent"
        >
          {expanded ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          {expanded ? 'Collapse' : 'Expand'} annotations
        </button>
      </div>

      {/* Audio player */}
      {segment.audio_url && <AudioPlayer src={segment.audio_url} />}

      {/* Article text */}
      <div className="leading-7 text-text-primary text-base">
        {annotatedContent.map(token =>
          token.isWord && token.word ? (
            <span
              key={token.key}
              onClick={(e) => handleWordClick(token.word!, e)}
              className={`cursor-pointer border-b border-dashed border-text-secondary/50 hover:border-accent ${
                expanded ? LEVEL_COLORS[token.word.level] || '' : ''
              }`}
            >
              {token.text}
              {expanded && (
                <span className="text-xs text-text-secondary ml-0.5">({token.word.meaning_zh})</span>
              )}
            </span>
          ) : (
            <span key={token.key}>{token.text}</span>
          )
        )}
      </div>

      {/* Glossary */}
      {segment.words_json && segment.words_json.length > 0 && (
        <GlossarySection words={segment.words_json} />
      )}

      {/* Complete button */}
      {!completed && (
        <button
          onClick={handleComplete}
          className="w-full mt-6 bg-accent text-primary font-medium py-3 rounded-lg"
        >
          Mark as completed
        </button>
      )}
      {completed && (
        <div className="mt-6 text-center text-status-mastered text-sm">Segment completed!</div>
      )}

      {/* Word popup */}
      {popupWord && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setPopupWord(null)} />
          <WordPopup word={popupWord.word} position={popupWord.pos} onClose={() => setPopupWord(null)} />
        </>
      )}

      {/* Add word modal */}
      {addWordModal && (
        <AddWordModal
          word={addWordModal.word}
          contextSentence={addWordModal.context}
          onClose={() => setAddWordModal(null)}
        />
      )}
    </div>
  )
}
