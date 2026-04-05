// src/components/ArticleReader.tsx (placeholder)
import type { Segment } from '../types'
export default function ArticleReader({ segment, contentId: _contentId }: { segment: Segment; contentId: number }) {
  return <div className="text-text-primary">{segment.text_en}</div>
}
