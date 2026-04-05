// src/components/GlossarySection.tsx
import type { VocabWord } from '../types'
import { LEVEL_COLORS, LEVEL_BG_COLORS } from '../types'

export default function GlossarySection({ words }: { words: VocabWord[] }) {
  const sorted = [...words].sort((a, b) => b.freq_in_content - a.freq_in_content)

  return (
    <div className="mt-8 pt-6 border-t border-border">
      <h3 className="text-text-primary font-medium mb-4">Glossary</h3>
      <div className="space-y-3">
        {sorted.map(w => (
          <div key={w.word} className="bg-card rounded-lg p-3 border border-border">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-text-primary font-medium">{w.word}</span>
              <span className="text-text-secondary text-xs">{w.ipa}</span>
              {w.level && (
                <span className={`text-xs px-1.5 py-0.5 rounded ${LEVEL_BG_COLORS[w.level] || ''} ${LEVEL_COLORS[w.level] || ''}`}>
                  {w.level}
                </span>
              )}
              <span className="text-text-secondary text-xs ml-auto">x{w.freq_in_content}</span>
            </div>
            <div className="text-text-primary text-sm">{w.meaning_zh}</div>
            {w.detail_zh && <div className="text-text-secondary text-xs mt-1">{w.detail_zh}</div>}
            {w.example_en && (
              <div className="mt-2 text-sm">
                <div className="text-text-secondary italic">"{w.example_en}"</div>
                {w.example_zh && <div className="text-text-secondary text-xs">{w.example_zh}</div>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
