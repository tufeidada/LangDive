// src/pages/ContentDetail.tsx
import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ExternalLink } from 'lucide-react'
import { getContent, getSegments } from '../services/api'
import { useEventLogger } from '../hooks/useEventLogger'
import SegmentList from '../components/SegmentList'
import PreviewScreen from '../components/PreviewScreen'
import ArticleReader from '../components/ArticleReader'
import VideoPlayer from '../components/VideoPlayer'
import type { ContentDetail as ContentDetailType, Segment } from '../types'

type Phase = 'segments' | 'preview' | 'reading'

export default function ContentDetail() {
  const { id } = useParams<{ id: string }>()
  const { log } = useEventLogger()
  const [content, setContent] = useState<ContentDetailType | null>(null)
  const [segments, setSegments] = useState<Segment[]>([])
  const [activeSegment, setActiveSegment] = useState<Segment | null>(null)
  const [phase, setPhase] = useState<Phase>('segments')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const numId = parseInt(id)
    Promise.all([getContent(numId), getSegments(numId)])
      .then(([c, s]) => {
        setContent(c)
        setSegments(s)
        log('content_open', { content_id: numId })
        // If single segment, go directly to preview
        if (s.length === 1) {
          setActiveSegment(s[0])
          setPhase(s[0].preview_words_json?.length ? 'preview' : 'reading')
        }
      })
      .finally(() => setLoading(false))
  }, [id])

  const handleSelectSegment = (seg: Segment) => {
    setActiveSegment(seg)
    setPhase(seg.preview_words_json?.length ? 'preview' : 'reading')
    log('segment_start', { content_id: content?.id, segment_index: seg.segment_index })
  }

  const handleStartReading = () => {
    setPhase('reading')
  }

  const handleBack = () => {
    if (phase === 'reading') {
      setPhase(segments.length > 1 ? 'segments' : 'preview')
    } else if (phase === 'preview') {
      setPhase('segments')
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

  return (
    <div>
      <button onClick={phase === 'segments' ? undefined : handleBack} className="text-text-secondary hover:text-accent flex items-center gap-1 mb-4">
        {phase === 'segments' ? (
          <Link to="/" className="flex items-center gap-1"><ArrowLeft className="w-4 h-4" /> Back</Link>
        ) : (
          <><ArrowLeft className="w-4 h-4" /> Back</>
        )}
      </button>

      <h1 className="text-text-primary font-bold text-lg mb-1">{content.title}</h1>
      <div className="text-text-secondary text-sm mb-4">{content.source} {content.difficulty && `· ${content.difficulty}`}</div>
      {content.summary_zh && <p className="text-text-secondary text-sm mb-4 italic">{content.summary_zh}</p>}

      {phase === 'segments' && segments.length > 1 && (
        <SegmentList segments={segments} onSelect={handleSelectSegment} />
      )}

      {phase === 'preview' && activeSegment?.preview_words_json && (
        <PreviewScreen
          words={activeSegment.preview_words_json}
          segmentTitle={activeSegment.title}
          onStart={handleStartReading}
        />
      )}

      {phase === 'reading' && activeSegment && (
        content.type === 'video' ? (
          <VideoPlayer content={content} segment={activeSegment} />
        ) : (
          <ArticleReader segment={activeSegment} contentId={content.id} />
        )
      )}
    </div>
  )
}
