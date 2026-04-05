// src/components/VideoPlayer.tsx
import { useState } from 'react'
import { Languages } from 'lucide-react'
import { useEventLogger } from '../hooks/useEventLogger'
import SubtitlePanel from './SubtitlePanel'
import AudioPlayer from './AudioPlayer'
import GlossarySection from './GlossarySection'
import { markSegmentComplete } from '../services/api'
import type { ContentDetail, Segment } from '../types'

interface Props {
  content: ContentDetail
  segment: Segment
}

export default function VideoPlayer({ content, segment }: Props) {
  const { log } = useEventLogger()
  const [showChinese, setShowChinese] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [completed, setCompleted] = useState(segment.is_completed)

  // Extract video ID from URL
  const videoId = content.url?.match(/v=([^&]+)/)?.[1] || ''

  const handleToggleChinese = () => {
    setShowChinese(!showChinese)
    log('toggle_chinese')
  }

  const handleSeek = (time: number) => {
    setCurrentTime(time)
    // If using iframe API, could seek the video here
  }

  const handleComplete = async () => {
    await markSegmentComplete(content.id, segment.segment_index)
    setCompleted(true)
    log('segment_complete', { content_id: content.id, segment_index: segment.segment_index })
  }

  // Build subtitle list from segment words/text
  // In real implementation, this would come from the transcript data
  const subtitles = segment.text_en.split(/[.!?]+/).filter(s => s.trim()).map((text, i) => ({
    text: text.trim(),
    start: i * 5, // placeholder timing
    duration: 5,
  }))

  return (
    <div>
      {/* YouTube embed */}
      {videoId && (
        <div className="aspect-video mb-4 rounded-lg overflow-hidden">
          <iframe
            src={`https://www.youtube.com/embed/${videoId}?start=${Math.floor(segment.start_time || 0)}`}
            className="w-full h-full"
            allowFullScreen
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope"
          />
        </div>
      )}

      {/* Audio player for segment TTS */}
      {segment.audio_url && <AudioPlayer src={segment.audio_url} />}

      {/* Chinese toggle */}
      <div className="flex items-center justify-end mb-3">
        <button
          onClick={handleToggleChinese}
          className={`flex items-center gap-1 text-sm px-3 py-1 rounded-lg ${
            showChinese ? 'bg-accent text-primary' : 'text-text-secondary hover:text-text-primary'
          }`}
        >
          <Languages className="w-4 h-4" /> {showChinese ? 'Hide' : 'Show'} Chinese
        </button>
      </div>

      {/* Subtitles */}
      <SubtitlePanel
        subtitles={subtitles}
        currentTime={currentTime}
        showChinese={showChinese}
        onSeek={handleSeek}
      />

      {/* Glossary */}
      {segment.words_json && segment.words_json.length > 0 && (
        <GlossarySection words={segment.words_json} />
      )}

      {/* Complete button */}
      {!completed ? (
        <button onClick={handleComplete} className="w-full mt-6 bg-accent text-primary font-medium py-3 rounded-lg">
          Mark as completed
        </button>
      ) : (
        <div className="mt-6 text-center text-status-mastered text-sm">Segment completed!</div>
      )}
    </div>
  )
}
