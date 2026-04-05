// src/components/ContentCard.tsx
import { Link } from 'react-router-dom'
import { BookOpen, Video, AlertCircle } from 'lucide-react'
import type { ContentItem } from '../types'

const DIFFICULTY_COLORS: Record<string, string> = {
  A2: 'bg-green-600/20 text-green-400',
  B1: 'bg-blue-600/20 text-blue-400',
  B2: 'bg-yellow-600/20 text-yellow-400',
  C1: 'bg-red-600/20 text-red-400',
}

export default function ContentCard({ item }: { item: ContentItem }) {
  return (
    <Link to={`/content/${item.id}`} className="block bg-card rounded-xl p-4 border border-border hover:border-accent/50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="mt-1">
          {item.type === 'video' ? (
            <Video className="w-5 h-5 text-red-400" />
          ) : (
            <BookOpen className="w-5 h-5 text-blue-400" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-text-primary font-medium truncate">{item.title}</h3>
          <div className="flex items-center gap-2 mt-1 text-sm text-text-secondary">
            <span>{item.source}</span>
            {item.difficulty && (
              <span className={`px-1.5 py-0.5 rounded text-xs ${DIFFICULTY_COLORS[item.difficulty] || ''}`}>
                {item.difficulty}
              </span>
            )}
            {item.segment_count > 1 && <span>{item.segment_count} segments</span>}
            {item.preview_word_count > 0 && <span>{item.preview_word_count} words</span>}
          </div>
          {!item.has_subtitles && (
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
