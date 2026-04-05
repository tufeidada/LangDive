// src/components/AddWordModal.tsx (placeholder)
interface Props {
  word: string
  contextSentence?: string
  onClose: () => void
}

export default function AddWordModal({ word: _word, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="bg-elevated rounded-xl border border-border p-6 w-80" onClick={e => e.stopPropagation()}>
        <div className="text-text-secondary text-sm">Add word modal — loading...</div>
      </div>
    </div>
  )
}
