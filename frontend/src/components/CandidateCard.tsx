// src/components/CandidateCard.tsx
import { Video, BookOpen, ArrowUp, X } from 'lucide-react'

const DIFFICULTY_COLORS: Record<string, string> = {
  A2: 'bg-green-600/20 text-green-400',
  B1: 'bg-blue-600/20 text-blue-400',
  'B1-B2': 'bg-blue-600/20 text-blue-400',
  B2: 'bg-yellow-600/20 text-yellow-400',
  'B2-C1': 'bg-orange-600/20 text-orange-400',
  C1: 'bg-red-600/20 text-red-400',
}

const LAYER_LABELS: Record<number, string> = {
  0: 'Manual',
  1: 'Layer 1',
  2: 'Layer 2 (classic)',
  3: 'Layer 3 (search)',
}

interface Props {
  candidate: {
    id: number
    title: string
    url: string
    type: 'article' | 'video'
    source_layer: number
    estimated_difficulty?: string
    ai_score?: number
    ai_reason?: string
    status: string
  }
  mode: 'selected' | 'unselected'
  onAction: (id: number) => void
  loading?: boolean
}

export default function CandidateCard({ candidate, mode, onAction, loading }: Props) {
  const diffColor = DIFFICULTY_COLORS[candidate.estimated_difficulty || ''] || 'bg-zinc-700 text-zinc-400'
  const layerLabel = LAYER_LABELS[candidate.source_layer] || `Layer ${candidate.source_layer}`

  return (
    <div className="bg-card rounded-lg p-3 border border-border flex items-start gap-3">
      <div className="mt-0.5 shrink-0">
        {candidate.type === 'video' ? (
          <Video className="w-4 h-4 text-red-400" />
        ) : (
          <BookOpen className="w-4 h-4 text-blue-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <a
          href={candidate.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-text-primary font-medium text-sm hover:text-accent truncate block"
          title={candidate.title}
        >
          {candidate.title}
        </a>
        <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-text-secondary">
          <span>{layerLabel}</span>
          {candidate.ai_score != null && (
            <span>Score: {candidate.ai_score.toFixed(2)}</span>
          )}
          {candidate.estimated_difficulty && (
            <span className={`px-1.5 py-0.5 rounded ${diffColor}`}>
              {candidate.estimated_difficulty}
            </span>
          )}
        </div>
        {candidate.ai_reason && (
          <p className="text-xs text-text-secondary mt-1 italic">"{candidate.ai_reason}"</p>
        )}
      </div>
      <div className="shrink-0">
        {mode === 'selected' ? (
          <button
            onClick={() => onAction(candidate.id)}
            disabled={loading}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-red-900/30 text-red-400 hover:bg-red-900/50 disabled:opacity-50 transition-colors"
          >
            <X className="w-3 h-3" />
            Remove
          </button>
        ) : (
          <button
            onClick={() => onAction(candidate.id)}
            disabled={loading}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-accent/20 text-accent hover:bg-accent/30 disabled:opacity-50 transition-colors"
          >
            <ArrowUp className="w-3 h-3" />
            Promote
          </button>
        )}
      </div>
    </div>
  )
}
