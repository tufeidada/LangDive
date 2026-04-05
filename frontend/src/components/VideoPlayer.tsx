// src/components/VideoPlayer.tsx (placeholder)
import type { ContentDetail, Segment } from '../types'
export default function VideoPlayer({ content, segment: _segment }: { content: ContentDetail; segment: Segment }) {
  return <div className="text-text-secondary">Video player — {content.title}</div>
}
