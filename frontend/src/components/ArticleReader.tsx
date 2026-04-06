// src/components/ArticleReader.tsx
import { useState, useCallback, useMemo } from 'react'
import { Eye, EyeOff, Play, Pause } from 'lucide-react'
import { markSegmentComplete } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'
import WordPopup from './WordPopup'
import GlossarySection from './GlossarySection'
import AudioPlayer from './AudioPlayer'
import AddWordModal from './AddWordModal'
import { useAudio } from '../hooks/useAudio'
import type { Segment, VocabWord } from '../types'
import { LEVEL_COLORS } from '../types'

const SPEEDS = [0.75, 1.0, 1.25, 1.5]

/** Multi-track audio player — renders one track at a time, advances on end */
function MultiTrackPlayer({ urls }: { urls: string[] }) {
  const [index, setIndex] = useState(0)
  const { log } = useEventLogger()

  const handleEnded = useCallback(() => {
    setIndex(i => Math.min(i + 1, urls.length - 1))
  }, [urls.length])

  const src = urls[index] ?? null
  const { playing, currentTime, duration, speed, toggle, changeSpeed } = useAudio(src, handleEnded)

  const handleToggle = () => {
    toggle()
    log('audio_play', { playing: !playing, track: index })
  }

  const formatTime = (t: number) => {
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-card rounded-lg p-3 border border-border mb-4 flex items-center gap-3">
      <button onClick={handleToggle} className="text-accent">
        {playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
      </button>
      <div className="flex-1 text-xs text-text-secondary">
        {formatTime(currentTime)} / {formatTime(duration || 0)}
        {urls.length > 1 && (
          <span className="ml-2 text-text-secondary/60">Part {index + 1}/{urls.length}</span>
        )}
      </div>
      <div className="flex gap-1">
        {SPEEDS.map(s => (
          <button
            key={s}
            onClick={() => changeSpeed(s)}
            className={`text-xs px-1.5 py-0.5 rounded ${speed === s ? 'bg-accent text-primary' : 'text-text-secondary hover:text-text-primary'}`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  )
}

type DensityLevel = 'few' | 'medium' | 'all'

const DENSITY_THRESHOLD: Record<DensityLevel, number> = {
  few: 0.8,
  medium: 0.5,
  all: 0.0,
}

const DENSITY_LABELS: Record<DensityLevel, string> = {
  few: '少',
  medium: '中',
  all: '多',
}

interface Props {
  segment: Segment
  contentId: number
  // Optional overrides for full-article mode
  overrideTextEn?: string
  overrideWordsJson?: VocabWord[]
  // Sequential audio tracks for full-article mode
  audioUrls?: string[]
  // Hide complete button in full-article mode
  hideComplete?: boolean
}

export default function ArticleReader({
  segment,
  contentId,
  overrideTextEn,
  overrideWordsJson,
  audioUrls,
  hideComplete,
}: Props) {
  const { log } = useEventLogger()
  const [expanded, setExpanded] = useState(false)
  const [density, setDensity] = useState<DensityLevel>('medium')
  const [popupWord, setPopupWord] = useState<{ word: VocabWord; pos: { x: number; y: number } } | null>(null)
  const [completed, setCompleted] = useState(segment.is_completed)
  const [addWordModal, setAddWordModal] = useState<{ word: string; context: string } | null>(null)

  const textEn = overrideTextEn ?? segment.text_en
  const rawWords = overrideWordsJson ?? segment.words_json

  // Build word lookup map filtered by density
  const wordMap = useMemo(() => {
    const map = new Map<string, VocabWord>()
    if (rawWords) {
      const threshold = DENSITY_THRESHOLD[density]
      for (const w of rawWords) {
        if ((w.importance_score ?? 0) >= threshold) {
          map.set(w.word.toLowerCase(), w)
        }
      }
    }
    return map
  }, [rawWords, density])

  // Full unfiltered word map for double-click "already annotated" check
  const fullWordMap = useMemo(() => {
    const map = new Map<string, VocabWord>()
    if (rawWords) {
      for (const w of rawWords) {
        map.set(w.word.toLowerCase(), w)
      }
    }
    return map
  }, [rawWords])

  // Annotate text: split into tokens, mark annotated words
  const annotatedContent = useMemo(() => {
    const tokens = textEn.split(/(\s+)/)
    return tokens.map((token, i) => {
      const clean = token.replace(/[^a-zA-Z'-]/g, '').toLowerCase()
      const wordData = wordMap.get(clean)
      if (wordData) {
        return { key: i, text: token, word: wordData, isWord: true }
      }
      return { key: i, text: token, word: null, isWord: false }
    })
  }, [textEn, wordMap])

  const handleWordClick = (word: VocabWord, e: React.MouseEvent) => {
    log('word_lookup', { word: word.word })
    setPopupWord({ word, pos: { x: e.clientX, y: e.clientY } })
  }

  const handleDoubleClick = useCallback((_e: React.MouseEvent) => {
    const selection = window.getSelection()?.toString().trim()
    if (!selection) return
    if (selection.includes(' ') || selection.length < 2 || selection.length > 30) return
    if (fullWordMap.has(selection.toLowerCase())) return
    // Find context sentence
    const sentences = textEn.split(/[.!?]+/)
    const contextSentence = sentences.find(s => s.toLowerCase().includes(selection.toLowerCase()))?.trim() || ''
    setAddWordModal({ word: selection, context: contextSentence })
    log('word_custom_add', { word: selection })
  }, [fullWordMap, textEn, log])

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

        {/* Density toggle */}
        <div className="flex items-center gap-1">
          <span className="text-xs text-text-secondary mr-1">注释密度</span>
          {(['few', 'medium', 'all'] as DensityLevel[]).map(level => (
            <button
              key={level}
              onClick={() => setDensity(level)}
              className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                density === level
                  ? 'bg-accent text-primary border-accent'
                  : 'text-text-secondary border-border hover:border-accent hover:text-accent'
              }`}
            >
              {DENSITY_LABELS[level]}
            </button>
          ))}
        </div>
      </div>

      {/* Audio player */}
      {audioUrls && audioUrls.length > 0
        ? <MultiTrackPlayer urls={audioUrls} />
        : segment.audio_url && <AudioPlayer src={segment.audio_url} />
      }

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
      {rawWords && rawWords.length > 0 && (
        <GlossarySection words={rawWords} />
      )}

      {/* Complete button */}
      {!hideComplete && !completed && (
        <button
          onClick={handleComplete}
          className="w-full mt-6 bg-accent text-primary font-medium py-3 rounded-lg"
        >
          Mark as completed
        </button>
      )}
      {!hideComplete && completed && (
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
