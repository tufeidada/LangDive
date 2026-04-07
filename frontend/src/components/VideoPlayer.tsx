// src/components/VideoPlayer.tsx
import { useState, useEffect, useRef } from 'react'
import { Languages } from 'lucide-react'
import { useEventLogger } from '../hooks/useEventLogger'
import SubtitlePanel from './SubtitlePanel'
import AudioPlayer from './AudioPlayer'
import GlossarySection from './GlossarySection'
import YouTubeEmbed from './YouTubeEmbed'
import { markSegmentComplete, getTranscript } from '../services/api'
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
  const [subtitles, setSubtitles] = useState<{ text: string; start: number; duration: number }[]>([])

  // Ref to imperatively seek the YouTube player
  const seekRef = useRef<((t: number) => void) | null>(null)

  // Extract video ID from URL
  const videoId = content.url?.match(/v=([^&]+)/)?.[1] || ''

  // Fetch real transcript on mount
  useEffect(() => {
    getTranscript(content.id)
      .then(entries => {
        if (entries && entries.length > 0) {
          setSubtitles(entries)
        } else {
          const fallback = segment.text_en.split(/[.!?]+/).filter(s => s.trim()).map((text, i) => ({
            text: text.trim(),
            start: i * 5,
            duration: 5,
          }))
          setSubtitles(fallback)
        }
      })
      .catch(() => {
        const fallback = segment.text_en.split(/[.!?]+/).filter(s => s.trim()).map((text, i) => ({
          text: text.trim(),
          start: i * 5,
          duration: 5,
        }))
        setSubtitles(fallback)
      })
  }, [content.id, segment.text_en])

  const handleToggleChinese = () => {
    setShowChinese(!showChinese)
    log('toggle_chinese')
  }

  const handleSeek = (time: number) => {
    // Seek the actual YouTube player
    if (seekRef.current) {
      seekRef.current(time)
    }
    setCurrentTime(time)
  }

  const handleComplete = async () => {
    await markSegmentComplete(content.id, segment.segment_index)
    setCompleted(true)
    log('segment_complete', { content_id: content.id, segment_index: segment.segment_index })
  }

  return (
    <div>
      {/* YouTube embed with IFrame API for seek support */}
      {videoId && (
        <YouTubeEmbed
          videoId={videoId}
          startTime={segment.start_time || 0}
          onTimeUpdate={setCurrentTime}
          seekRef={seekRef}
        />
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

      {/* Subtitles with click-to-seek */}
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
