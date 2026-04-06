// src/pages/ContentDetail.tsx
import { useState, useEffect, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import { getContent, getSegments } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'
import SegmentList from '../components/SegmentList'
import PreviewScreen from '../components/PreviewScreen'
import ArticleReader from '../components/ArticleReader'
import VideoPlayer from '../components/VideoPlayer'
import type { ContentDetail as ContentDetailType, Segment, VocabWord } from '../types'

type Phase = 'full' | 'segments' | 'preview' | 'segment-reading'

export default function ContentDetail() {
  const { id } = useParams<{ id: string }>()
  const { log } = useEventLogger()
  const [content, setContent] = useState<ContentDetailType | null>(null)
  const [segments, setSegments] = useState<Segment[]>([])
  const [activeSegment, setActiveSegment] = useState<Segment | null>(null)
  const [phase, setPhase] = useState<Phase>('full')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const numId = parseInt(id)
    Promise.all([getContent(numId), getSegments(numId)])
      .then(([c, s]) => {
        setContent(c)
        setSegments(s)
        log('content_open', { content_id: numId })
        // Videos don't have a "full" article view — go to segments
        if (c.type === 'video') {
          if (s.length === 1) {
            setActiveSegment(s[0])
            setPhase(s[0].preview_words_json?.length ? 'preview' : 'segment-reading')
          } else {
            setPhase('segments')
          }
        }
        // Articles default to 'full' (already set)
      })
      .finally(() => setLoading(false))
  }, [id])

  // Merge all segments into one for full-article view
  const fullArticleText = useMemo(() => {
    if (!segments.length) return ''
    return segments.map(s => s.text_en).join('\n\n')
  }, [segments])

  const fullArticleWords = useMemo((): VocabWord[] => {
    const seen = new Set<string>()
    const merged: VocabWord[] = []
    for (const seg of segments) {
      if (seg.words_json) {
        for (const w of seg.words_json) {
          if (!seen.has(w.word.toLowerCase())) {
            seen.add(w.word.toLowerCase())
            merged.push(w)
          }
        }
      }
    }
    return merged
  }, [segments])

  // A synthetic segment used by ArticleReader in full mode (only needs segment_index + is_completed)
  const fullModeSyntheticSegment = useMemo((): Segment | null => {
    if (!segments.length) return null
    return {
      ...segments[0],
      text_en: fullArticleText,
      words_json: fullArticleWords,
      audio_url: null,
    }
  }, [segments, fullArticleText, fullArticleWords])

  const handleSelectSegment = (seg: Segment) => {
    setActiveSegment(seg)
    setPhase(seg.preview_words_json?.length ? 'preview' : 'segment-reading')
    log('segment_start', { content_id: content?.id, segment_index: seg.segment_index })
  }

  const handleStartReading = () => {
    setPhase('segment-reading')
  }

  const handleBack = () => {
    if (phase === 'segment-reading') {
      setPhase('preview')
    } else if (phase === 'preview') {
      setPhase('segments')
    } else if (phase === 'segments') {
      setPhase('full')
    }
  }

  if (loading) return <div className="text-text-secondary">Loading...</div>
  if (!content) return <div className="text-text-secondary">Content not found.</div>

  // No-subtitle video fallback
  if (content.type === 'video' && !content.has_subtitles) {
    return (
      <div>
        <Link to="/" className="text-text-secondary hover:text-accent flex items-center gap-1 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back
        </Link>
        <div className="bg-card rounded-xl p-6 border border-border text-center">
          <h2 className="text-text-primary font-medium text-lg mb-2">{content.title}</h2>
          <div className="text-text-secondary text-sm mb-4">{content.source} {content.difficulty && `· ${content.difficulty}`}</div>
          <div className="inline-block bg-yellow-500/20 text-yellow-400 text-sm px-3 py-1 rounded mb-4">No subtitles available</div>
          <div>
            <a href={content.url || '#'} target="_blank" rel="noopener" className="inline-flex items-center gap-2 bg-accent text-primary font-medium px-4 py-2 rounded-lg">
              <ExternalLink className="w-4 h-4" /> Watch on YouTube
            </a>
          </div>
        </div>
      </div>
    )
  }

  const isAtRoot = phase === 'full' || (content.type === 'video' && phase === 'segments')

  return (
    <div>
      {/* Back navigation */}
      <div className="mb-4">
        {isAtRoot ? (
          <Link to="/" className="text-text-secondary hover:text-accent flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
        ) : (
          <button onClick={handleBack} className="text-text-secondary hover:text-accent flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
        )}
      </div>

      <h1 className="text-text-primary font-bold text-lg mb-1">{content.title}</h1>
      <div className="text-text-secondary text-sm mb-4">{content.source} {content.difficulty && `· ${content.difficulty}`}</div>
      {content.summary_zh && <p className="text-text-secondary text-sm mb-4 italic">{content.summary_zh}</p>}

      {/* Full article view (default for articles) */}
      {phase === 'full' && fullModeSyntheticSegment && (
        <div>
          {/* Mode switcher buttons */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setPhase('segments')}
              className="text-sm px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:border-accent hover:text-accent transition-colors"
            >
              Segment Mode
            </button>
            {(() => {
              // Collect all preview words across segments
              const allPreviewWords = segments.flatMap(s => s.preview_words_json ?? [])
              if (!allPreviewWords.length) return null
              return (
                <button
                  onClick={() => {
                    // Use first segment with preview words as vehicle
                    const segWithPreview = segments.find(s => s.preview_words_json?.length)
                    if (segWithPreview) {
                      setActiveSegment(segWithPreview)
                      setPhase('preview')
                    }
                  }}
                  className="text-sm px-3 py-1.5 rounded-lg border border-border text-text-secondary hover:border-accent hover:text-accent transition-colors"
                >
                  Preview Words
                </button>
              )
            })()}
          </div>

          <ArticleReader
            segment={fullModeSyntheticSegment}
            contentId={content.id}
            overrideTextEn={fullArticleText}
            overrideWordsJson={fullArticleWords}
            hideComplete
          />
        </div>
      )}

      {/* Segment list */}
      {phase === 'segments' && (
        <SegmentList segments={segments} onSelect={handleSelectSegment} />
      )}

      {/* Preview screen */}
      {phase === 'preview' && activeSegment?.preview_words_json && (
        <PreviewScreen
          words={activeSegment.preview_words_json}
          segmentTitle={activeSegment.title}
          onStart={handleStartReading}
        />
      )}

      {/* Segment reading */}
      {phase === 'segment-reading' && activeSegment && (
        content.type === 'video' ? (
          <VideoPlayer content={content} segment={activeSegment} />
        ) : (
          <ArticleReader segment={activeSegment} contentId={content.id} />
        )
      )}
    </div>
  )
}
