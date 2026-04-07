// src/components/SourceManager.tsx
import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, Plus, Check, X, Pencil } from 'lucide-react'
import { getSources, addSource, updateSource, deleteSource } from '../services/api'

const TYPE_LABELS: Record<string, string> = {
  youtube_channel: 'YT',
  newsletter_rss: 'RSS',
  blog_rss: 'Blog',
  hn_api: 'HN',
  classic_library: 'Classic',
}

interface Source {
  id: number
  name: string
  type: string
  url: string
  layer: number
  priority: number
  quality_score: number
  is_active: boolean
  candidate_count?: number
  tags?: string[]
  default_difficulty?: string
}

interface EditState {
  priority: string
  quality_score: string
  is_active: boolean
}

const EMPTY_NEW: Omit<Source, 'id' | 'candidate_count'> = {
  name: '',
  type: 'blog_rss',
  url: '',
  layer: 1,
  priority: 50,
  quality_score: 0.5,
  is_active: true,
  tags: [],
  default_difficulty: 'B2',
}

export default function SourceManager() {
  const [expanded, setExpanded] = useState(false)
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editState, setEditState] = useState<EditState>({ priority: '50', quality_score: '0.5', is_active: true })
  const [showAddForm, setShowAddForm] = useState(false)
  const [newSource, setNewSource] = useState({ ...EMPTY_NEW })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const data = await getSources()
      setSources(data)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const startEdit = (s: Source) => {
    setEditingId(s.id)
    setEditState({
      priority: String(s.priority),
      quality_score: String(s.quality_score),
      is_active: s.is_active,
    })
  }

  const saveEdit = async (id: number) => {
    setSaving(true)
    try {
      await updateSource(id, {
        priority: Number(editState.priority),
        quality_score: Number(editState.quality_score),
        is_active: editState.is_active,
      })
      setSources(prev =>
        prev.map(s => s.id === id
          ? { ...s, priority: Number(editState.priority), quality_score: Number(editState.quality_score), is_active: editState.is_active }
          : s
        )
      )
      setEditingId(null)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Deactivate this source?')) return
    try {
      await deleteSource(id)
      setSources(prev => prev.map(s => s.id === id ? { ...s, is_active: false } : s))
    } catch (e: any) {
      setError(e.message)
    }
  }

  const handleAdd = async () => {
    if (!newSource.name.trim() || !newSource.url.trim()) return
    setSaving(true)
    try {
      const created = await addSource(newSource)
      setSources(prev => [...prev, created])
      setNewSource({ ...EMPTY_NEW })
      setShowAddForm(false)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const activeCount = sources.filter(s => s.is_active).length

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/5 transition-colors"
      >
        <span className="text-sm font-medium text-text-primary">
          Sources ({activeCount} active)
        </span>
        <span className="flex items-center gap-1 text-xs text-text-secondary">
          Manage
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {expanded && (
        <div className="border-t border-border">
          {loading && (
            <p className="px-4 py-3 text-xs text-text-secondary">Loading sources...</p>
          )}
          {error && (
            <p className="px-4 py-2 text-xs text-red-400">{error}</p>
          )}

          <div className="divide-y divide-border">
            {sources.map(s => (
              <div key={s.id} className="px-4 py-2 flex items-center gap-3 text-sm">
                <span className={`text-lg ${s.is_active ? '' : 'opacity-30'}`}>
                  {s.is_active ? '✅' : '⬜'}
                </span>
                <span className="flex-1 min-w-0">
                  <span className={`font-medium ${s.is_active ? 'text-text-primary' : 'text-text-secondary line-through'}`}>
                    {s.name}
                  </span>
                  <span className="ml-2 text-xs text-text-secondary inline-flex items-center gap-1.5">
                    {TYPE_LABELS[s.type] || s.type}
                    {s.candidate_count != null && s.candidate_count > 0 ? (
                      <span className="px-1.5 py-0.5 rounded-full bg-accent/20 text-accent font-medium">
                        {s.candidate_count}
                      </span>
                    ) : (
                      <span className="text-text-secondary/50">· no candidates</span>
                    )}
                  </span>
                </span>

                {editingId === s.id ? (
                  <div className="flex items-center gap-2 text-xs">
                    <label className="text-text-secondary">P:</label>
                    <input
                      type="number"
                      value={editState.priority}
                      onChange={e => setEditState(v => ({ ...v, priority: e.target.value }))}
                      className="w-14 bg-primary border border-border rounded px-1 py-0.5 text-text-primary"
                      min="1" max="100"
                    />
                    <label className="text-text-secondary">Q:</label>
                    <input
                      type="number"
                      value={editState.quality_score}
                      onChange={e => setEditState(v => ({ ...v, quality_score: e.target.value }))}
                      className="w-14 bg-primary border border-border rounded px-1 py-0.5 text-text-primary"
                      min="0" max="1" step="0.1"
                    />
                    <label className="text-text-secondary flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editState.is_active}
                        onChange={e => setEditState(v => ({ ...v, is_active: e.target.checked }))}
                      />
                      Active
                    </label>
                    <button onClick={() => saveEdit(s.id)} disabled={saving} className="text-green-400 hover:text-green-300">
                      <Check className="w-4 h-4" />
                    </button>
                    <button onClick={() => setEditingId(null)} className="text-text-secondary hover:text-text-primary">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-3 text-xs text-text-secondary">
                    <span>P:{s.priority}</span>
                    <span>Q:{s.quality_score.toFixed(1)}</span>
                    <button
                      onClick={() => startEdit(s)}
                      className="text-text-secondary hover:text-accent transition-colors"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(s.id)}
                      className="text-text-secondary hover:text-red-400 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          {showAddForm ? (
            <div className="px-4 py-3 border-t border-border space-y-2">
              <p className="text-xs font-medium text-text-secondary">Add New Source</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <input
                  placeholder="Name"
                  value={newSource.name}
                  onChange={e => setNewSource(v => ({ ...v, name: e.target.value }))}
                  className="col-span-2 bg-primary border border-border rounded px-2 py-1.5 text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent"
                />
                <input
                  placeholder="URL or Channel ID"
                  value={newSource.url}
                  onChange={e => setNewSource(v => ({ ...v, url: e.target.value }))}
                  className="col-span-2 bg-primary border border-border rounded px-2 py-1.5 text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent"
                />
                <select
                  value={newSource.type}
                  onChange={e => setNewSource(v => ({ ...v, type: e.target.value }))}
                  className="bg-primary border border-border rounded px-2 py-1.5 text-text-primary focus:outline-none focus:border-accent"
                >
                  <option value="youtube_channel">YouTube Channel</option>
                  <option value="newsletter_rss">Newsletter RSS</option>
                  <option value="blog_rss">Blog RSS</option>
                  <option value="hn_api">Hacker News</option>
                  <option value="classic_library">Classic Library</option>
                </select>
                <select
                  value={newSource.layer}
                  onChange={e => setNewSource(v => ({ ...v, layer: Number(e.target.value) }))}
                  className="bg-primary border border-border rounded px-2 py-1.5 text-text-primary focus:outline-none focus:border-accent"
                >
                  <option value={1}>Layer 1 (Whitelist)</option>
                  <option value={2}>Layer 2 (Classic)</option>
                  <option value={3}>Layer 3 (Search)</option>
                </select>
                <div className="flex items-center gap-2">
                  <label className="text-text-secondary">Priority:</label>
                  <input
                    type="number" min="1" max="100"
                    value={newSource.priority}
                    onChange={e => setNewSource(v => ({ ...v, priority: Number(e.target.value) }))}
                    className="w-16 bg-primary border border-border rounded px-2 py-1.5 text-text-primary focus:outline-none focus:border-accent"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-text-secondary">Quality:</label>
                  <input
                    type="number" min="0" max="1" step="0.1"
                    value={newSource.quality_score}
                    onChange={e => setNewSource(v => ({ ...v, quality_score: Number(e.target.value) }))}
                    className="w-16 bg-primary border border-border rounded px-2 py-1.5 text-text-primary focus:outline-none focus:border-accent"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleAdd}
                  disabled={saving || !newSource.name.trim() || !newSource.url.trim()}
                  className="px-3 py-1.5 bg-accent text-primary text-xs rounded hover:bg-accent/90 disabled:opacity-50 transition-colors"
                >
                  Add Source
                </button>
                <button
                  onClick={() => { setShowAddForm(false); setNewSource({ ...EMPTY_NEW }) }}
                  className="px-3 py-1.5 text-text-secondary text-xs hover:text-text-primary transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="px-4 py-2 border-t border-border">
              <button
                onClick={() => setShowAddForm(true)}
                className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Source
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
