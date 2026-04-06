// src/components/UrlSubmitForm.tsx
import { useState } from 'react'
import { Link, Loader2 } from 'lucide-react'
import { submitUrl } from '../services/api'

interface Props {
  onSubmitted?: () => void
}

export default function UrlSubmitForm({ onSubmitted }: Props) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await submitUrl(url.trim())
      setSuccess(`Submitted (candidate #${result.candidate_id}). Processing...`)
      setUrl('')
      onSubmitted?.()
    } catch (err: any) {
      setError(err.message || 'Submission failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-card rounded-xl p-4 border border-border">
      <div className="flex items-center gap-2 mb-3 text-text-secondary text-sm font-medium">
        <Link className="w-4 h-4" />
        Paste URL to add content
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://..."
          disabled={loading}
          className="flex-1 bg-primary border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="px-4 py-2 bg-accent text-primary text-sm font-medium rounded-lg hover:bg-accent/90 disabled:opacity-50 transition-colors flex items-center gap-2"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {loading ? 'Processing...' : 'Submit'}
        </button>
      </form>
      {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
      {success && <p className="mt-2 text-xs text-green-400">{success}</p>}
      {loading && (
        <p className="mt-2 text-xs text-text-secondary animate-pulse">
          Processing your content... this may take 30–60 seconds.
        </p>
      )}
    </div>
  )
}
