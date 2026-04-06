// src/components/PipelineStatus.tsx
import { Activity } from 'lucide-react'

interface Props {
  candidates: any[]
}

export default function PipelineStatus({ candidates }: Props) {
  if (candidates.length === 0) return null

  const layer1 = candidates.filter(c => c.source_layer === 1).length
  const layer2 = candidates.filter(c => c.source_layer === 2).length
  const layer3 = candidates.filter(c => c.source_layer === 3).length
  const selected = candidates.filter(c =>
    ['selected', 'user_promoted', 'user_submitted'].includes(c.status)
  ).length
  const total = candidates.length
  const errors = candidates.filter(c => c.status === 'error').length

  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <div className="flex items-center gap-2 mb-3 text-text-secondary text-sm font-medium">
        <Activity className="w-4 h-4" />
        Pipeline Status
      </div>
      <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs text-text-secondary">
        <span>Layer 1: <span className="text-text-primary">{layer1} fetched</span></span>
        <span>Layer 2: <span className="text-text-primary">{layer2 > 0 ? `${layer2} drawn` : 'not triggered'}</span></span>
        <span>Layer 3: <span className="text-text-primary">{layer3 > 0 ? `${layer3} fetched` : 'not triggered'}</span></span>
        <span>
          Selected: <span className="text-text-primary">{selected}</span>
          {' · '}Total: <span className="text-text-primary">{total}</span>
        </span>
        <span>
          Errors:{' '}
          <span className={errors > 0 ? 'text-red-400' : 'text-green-400'}>
            {errors}
          </span>
        </span>
      </div>
    </div>
  )
}
