// src/components/SegmentList.tsx
import { CheckCircle, Circle } from 'lucide-react'
import type { Segment } from '../types'

interface Props {
  segments: Segment[]
  onSelect: (segment: Segment) => void
}

export default function SegmentList({ segments, onSelect }: Props) {
  return (
    <div className="space-y-2">
      <h2 className="text-text-primary font-medium mb-3">Segments</h2>
      {segments.map(seg => (
        <button
          key={seg.id}
          onClick={() => onSelect(seg)}
          className="w-full text-left bg-card rounded-lg p-3 border border-border hover:border-accent/50 transition-colors flex items-center gap-3"
        >
          {seg.is_completed ? (
            <CheckCircle className="w-5 h-5 text-status-mastered flex-shrink-0" />
          ) : (
            <Circle className="w-5 h-5 text-text-secondary flex-shrink-0" />
          )}
          <div className="flex-1 min-w-0">
            <div className="text-text-primary text-sm font-medium truncate">{seg.title}</div>
            {seg.summary_zh && (
              <div className="text-text-secondary text-xs mt-0.5 truncate">{seg.summary_zh}</div>
            )}
          </div>
          <span className="text-text-secondary text-xs">
            {seg.preview_words_json?.length || 0} words
          </span>
        </button>
      ))}
    </div>
  )
}
