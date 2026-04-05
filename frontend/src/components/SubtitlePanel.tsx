// src/components/SubtitlePanel.tsx
import { useRef, useEffect } from 'react'

interface Subtitle {
  text: string
  start: number
  duration: number
  translation_zh?: string
}

interface Props {
  subtitles: Subtitle[]
  currentTime: number
  showChinese: boolean
  onSeek: (time: number) => void
}

export default function SubtitlePanel({ subtitles, currentTime, showChinese, onSeek }: Props) {
  const activeRef = useRef<HTMLDivElement>(null)

  const activeIndex = subtitles.findIndex(
    (s, i) => currentTime >= s.start && (i === subtitles.length - 1 || currentTime < subtitles[i + 1].start)
  )

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [activeIndex])

  return (
    <div className="space-y-1 max-h-96 overflow-y-auto">
      {subtitles.map((sub, i) => (
        <div
          key={i}
          ref={i === activeIndex ? activeRef : null}
          onClick={() => onSeek(sub.start)}
          className={`p-2 rounded cursor-pointer transition-colors ${
            i === activeIndex
              ? 'bg-accent/10 border-l-2 border-accent'
              : 'hover:bg-card'
          }`}
        >
          <div className={`text-sm ${i === activeIndex ? 'text-text-primary' : 'text-text-secondary'}`}>
            {sub.text}
          </div>
          {showChinese && sub.translation_zh && (
            <div className="text-xs text-text-secondary mt-0.5">{sub.translation_zh}</div>
          )}
        </div>
      ))}
    </div>
  )
}
