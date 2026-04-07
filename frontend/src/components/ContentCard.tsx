// src/components/ContentCard.tsx
import { Link } from 'react-router-dom'
import { BookOpen, Video, AlertCircle, Clock } from 'lucide-react'
import type { ContentItem } from '../types'

const DIFFICULTY_COLORS: Record<string, string> = {
  A2: 'bg-green-600/20 text-green-400',
  B1: 'bg-blue-600/20 text-blue-400',
  B2: 'bg-yellow-600/20 text-yellow-400',
  C1: 'bg-red-600/20 text-red-400',
}

export default function ContentCard({ item }: { item: ContentItem }) {
  const isVideo = item.type === 'video'
  const timeLabel = isVideo ? item.duration : item.read_time

  return (
    <Link to={`/content/${item.id}`} className="block bg-card rounded-xl p-4 border border-border hover:border-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          {isVideo ? (
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-red-500/10">
              <Video className="w-4 h-4 text-red-400" />
            </div>
          ) : (
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10">
              <BookOpen className="w-4 h-4 text-blue-400" />
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          {/* Source + type badge row */}
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-xs font-medium text-text-secondary truncate">{item.source}</span>
            <span className={`shrink-0 px-1.5 py-0.5 rounded text-xs font-medium ${
              isVideo ? 'bg-red-600/15 text-red-400' : 'bg-blue-600/15 text-blue-400'
            }`}>
              {isVideo ? 'Video' : 'Article'}
            </span>
          </div>
          {/* Title */}
          <h3 className="text-text-primary font-medium leading-snug line-clamp-2">{item.title}</h3>
          {/* Meta row */}
          <div className="flex items-center gap-2 mt-1.5 text-xs text-text-secondary flex-wrap">
            {item.difficulty && (
              <span className={`px-1.5 py-0.5 rounded font-medium ${DIFFICULTY_COLORS[item.difficulty] || ''}`}>
                {item.difficulty}
              </span>
            )}
            {timeLabel && (
              <span className="flex items-center gap-0.5">
                <Clock className="w-3 h-3" />
                {timeLabel}
              </span>
            )}
            {item.segment_count > 1 && <span>{item.segment_count} segments</span>}
            {item.preview_word_count > 0 && <span>{item.preview_word_count} words</span>}
          </div>
          {item.type === 'video' && !item.has_subtitles && (
            <div className="flex items-center gap-1 mt-1 text-xs text-yellow-500">
              <AlertCircle className="w-3 h-3" />
              <span>No subtitles available</span>
            </div>
          )}
        </div>
      </div>
    </Link>
  )
}
