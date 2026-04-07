// src/components/ArticleReader.tsx
import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { Eye, EyeOff, Play, Pause, Download, Bookmark, Volume2, Lightbulb } from 'lucide-react'
import { markSegmentComplete, getVocab, createBookmark, explainSentence } from '../services/api'
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
  const [userVocab, setUserVocab] = useState<Map<string, string>>(new Map())
  const [hoveredSentenceIdx, setHoveredSentenceIdx] = useState<number | null>(null)
  const [explainPopup, setExplainPopup] = useState<{ text: string; loading: boolean } | null>(null)
  const [bookmarkedSentences, setBookmarkedSentences] = useState<Set<string>>(new Set())

  useEffect(() => {
    getVocab().then(list => {
      const map = new Map<string, string>()
      for (const v of list) map.set(v.word.toLowerCase(), v.status)
      setUserVocab(map)
    }).catch(() => {/* ignore vocab fetch errors */})
  }, [])

  const contentRef = useRef<HTMLDivElement>(null)
  const textEn = overrideTextEn ?? segment.text_en
  const rawWords = overrideWordsJson ?? segment.words_json

  const handleExportPDF = async () => {
    const el = contentRef.current
    if (!el) return
    const html2pdf = (await import('html2pdf.js')).default
    html2pdf()
      .set({
        margin: [10, 10, 10, 10],
        filename: `${segment.title || 'article'}.pdf`,
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      })
      .from(el)
      .save()
  }

  // Split text into sentences for sentence-level actions
  const sentences = useMemo(() => {
    const parts: string[] = []
    // Split on sentence-ending punctuation followed by space or end of string
    const regex = /[^.!?]*[.!?]+(?:\s+|$)/g
    let match
    let lastIndex = 0
    while ((match = regex.exec(textEn)) !== null) {
      parts.push(match[0])
      lastIndex = regex.lastIndex
    }
    // Remainder (no trailing punctuation)
    if (lastIndex < textEn.length) {
      parts.push(textEn.slice(lastIndex))
    }
    return parts.filter(s => s.trim().length > 0)
  }, [textEn])

  const handleSentenceBookmark = async (sentence: string) => {
    const trimmed = sentence.trim()
    try {
      await createBookmark({
        content_id: contentId,
        segment_index: segment.segment_index,
        sentence_text: trimmed,
      })
      setBookmarkedSentences(prev => new Set(prev).add(trimmed))
      log('sentence_bookmark', { content_id: contentId, sentence: trimmed.slice(0, 60) })
    } catch {
      // silently ignore
    }
  }

  const handleSentenceListen = (sentence: string) => {
    const trimmed = sentence.trim()
    if (!trimmed) return
    window.speechSynthesis.cancel()
    const utt = new SpeechSynthesisUtterance(trimmed)
    utt.lang = 'en-US'
    window.speechSynthesis.speak(utt)
    log('sentence_listen', { content_id: contentId, sentence: trimmed.slice(0, 60) })
  }

  const handleSentenceExplain = async (sentence: string) => {
    const trimmed = sentence.trim()
    setExplainPopup({ text: '', loading: true })
    log('sentence_explain', { content_id: contentId, sentence: trimmed.slice(0, 60) })
    try {
      const res = await explainSentence(trimmed)
      setExplainPopup({ text: res.explanation, loading: false })
    } catch {
      setExplainPopup({ text: '解释失败，请稍后重试。', loading: false })
    }
  }

  // Build word lookup map filtered by density and user vocab status
  const wordMap = useMemo(() => {
    const map = new Map<string, VocabWord>()
    if (rawWords) {
      const threshold = DENSITY_THRESHOLD[density]
      for (const w of rawWords) {
        if ((w.importance_score ?? 0) < threshold) continue
        // Skip words user has marked as known or ignored
        const status = userVocab.get(w.word.toLowerCase())
        if (status === 'known' || status === 'ignored') continue
        map.set(w.word.toLowerCase(), w)
      }
    }
    return map
  }, [rawWords, density, userVocab])

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

        {/* Density toggle + export */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportPDF}
            className="flex items-center gap-1 text-xs text-text-secondary hover:text-accent"
          >
            <Download className="w-3.5 h-3.5" /> PDF
          </button>
          <span className="text-xs text-text-secondary">注释密度</span>
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

      {/* Article text + glossary (wrapped for PDF export) */}
      <div ref={contentRef}>
      <div className="leading-7 text-text-primary text-base">
        {sentences.map((sentence, sIdx) => {
          const tokens = sentence.split(/(\s+)/)
          const isHovered = hoveredSentenceIdx === sIdx
          const isBookmarked = bookmarkedSentences.has(sentence.trim())
          return (
            <span
              key={sIdx}
              className={`relative inline transition-colors duration-100 ${isHovered ? 'bg-accent/10 rounded' : ''}`}
              onMouseEnter={() => setHoveredSentenceIdx(sIdx)}
              onMouseLeave={() => setHoveredSentenceIdx(null)}
            >
              {tokens.map((token, tIdx) => {
                const clean = token.replace(/[^a-zA-Z'-]/g, '').toLowerCase()
                const wordData = wordMap.get(clean)
                if (wordData) {
                  return (
                    <span
                      key={tIdx}
                      onClick={(e) => handleWordClick(wordData, e)}
                      className={`cursor-pointer border-b border-dashed border-text-secondary/50 hover:border-accent ${
                        expanded ? LEVEL_COLORS[wordData.level] || '' : ''
                      }`}
                    >
                      {token}
                      {expanded && (
                        <span className="text-xs text-text-secondary ml-0.5">({wordData.meaning_zh})</span>
                      )}
                    </span>
                  )
                }
                return <span key={tIdx}>{token}</span>
              })}
              {/* Sentence toolbar — appears on hover */}
              {isHovered && (
                <span
                  className="inline-flex items-center gap-0.5 ml-1 align-middle"
                  onMouseEnter={() => setHoveredSentenceIdx(sIdx)}
                >
                  <button
                    title="Bookmark sentence"
                    onClick={() => handleSentenceBookmark(sentence)}
                    className={`p-0.5 rounded text-xs ${isBookmarked ? 'text-accent' : 'text-text-secondary hover:text-accent'}`}
                  >
                    <Bookmark className="w-3.5 h-3.5" />
                  </button>
                  <button
                    title="Listen to sentence"
                    onClick={() => handleSentenceListen(sentence)}
                    className="p-0.5 rounded text-xs text-text-secondary hover:text-accent"
                  >
                    <Volume2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    title="AI Explain"
                    onClick={() => handleSentenceExplain(sentence)}
                    className="p-0.5 rounded text-xs text-text-secondary hover:text-accent"
                  >
                    <Lightbulb className="w-3.5 h-3.5" />
                  </button>
                </span>
              )}
            </span>
          )
        })}
      </div>

      {/* Glossary */}
      {rawWords && rawWords.length > 0 && (
        <GlossarySection words={rawWords} />
      )}
      </div>{/* end contentRef */}

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

      {/* AI Explain popup */}
      {explainPopup && (
        <>
          <div className="fixed inset-0 z-40 bg-black/20" onClick={() => setExplainPopup(null)} />
          <div className="fixed z-50 bottom-6 left-1/2 -translate-x-1/2 w-[min(480px,90vw)] bg-card border border-border rounded-xl shadow-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm text-text-primary flex items-center gap-1">
                <Lightbulb className="w-4 h-4 text-accent" /> AI 解释
              </span>
              <button onClick={() => setExplainPopup(null)} className="text-text-secondary hover:text-text-primary text-lg leading-none">&times;</button>
            </div>
            {explainPopup.loading
              ? <p className="text-sm text-text-secondary animate-pulse">正在分析…</p>
              : <p className="text-sm text-text-primary whitespace-pre-wrap leading-relaxed">{explainPopup.text}</p>
            }
          </div>
        </>
      )}
    </div>
  )
}
