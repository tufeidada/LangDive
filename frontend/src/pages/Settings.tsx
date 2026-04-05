// src/pages/Settings.tsx
import { useState, useEffect } from 'react'
import { Save, RotateCcw } from 'lucide-react'
import { getSettings, updateSettings } from '../services/api'

const DEFAULTS: Record<string, string> = {
  daily_new_word_cap: '20',
  daily_review_cap: '50',
  tts_provider: 'google',
  tts_fallback: 'qwen',
  tts_speed: '1.0',
  show_chinese: 'false',
  vocab_baseline: '3500',
  daily_content_count: '5',
  keywords: '["AI","Finance","Tech","Management"]',
}

export default function Settings() {
  const [settings, setSettings] = useState<Record<string, string>>(DEFAULTS)
  const [original, setOriginal] = useState<Record<string, string>>(DEFAULTS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSettings()
      .then(data => {
        const merged = { ...DEFAULTS, ...data }
        setSettings(merged)
        setOriginal(merged)
      })
      .catch(() => setError('Failed to load settings.'))
      .finally(() => setLoading(false))
  }, [])

  const set = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await updateSettings(settings)
      setOriginal(settings)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch {
      setError('Failed to save settings.')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setSettings(original)
    setSaved(false)
  }

  const isDirty = JSON.stringify(settings) !== JSON.stringify(original)

  if (loading) {
    return <div className="text-text-secondary">Loading settings...</div>
  }

  return (
    <div className="space-y-6 max-w-lg">
      <h2 className="text-text-primary font-semibold text-lg">Settings</h2>

      {error && (
        <div className="bg-status-due/10 border border-status-due/40 text-status-due text-sm rounded-lg px-4 py-2">
          {error}
        </div>
      )}

      {/* SRS / Vocabulary */}
      <section className="bg-card border border-border rounded-xl p-4 space-y-4">
        <h3 className="text-text-secondary text-xs uppercase tracking-wider">SRS / Vocabulary</h3>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">Daily new word cap</p>
            <p className="text-text-secondary text-xs">Max new words added to review queue per day</p>
          </div>
          <input
            type="number"
            min={1}
            max={100}
            value={settings.daily_new_word_cap}
            onChange={e => set('daily_new_word_cap', e.target.value)}
            className="w-20 bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary text-center focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">Daily review cap</p>
            <p className="text-text-secondary text-xs">Max reviews shown per day</p>
          </div>
          <input
            type="number"
            min={1}
            max={200}
            value={settings.daily_review_cap}
            onChange={e => set('daily_review_cap', e.target.value)}
            className="w-20 bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary text-center focus:outline-none focus:border-accent"
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">Vocab baseline</p>
            <p className="text-text-secondary text-xs">Known word count (CET-4 ≈ 3500)</p>
          </div>
          <input
            type="number"
            min={0}
            max={20000}
            step={100}
            value={settings.vocab_baseline}
            onChange={e => set('vocab_baseline', e.target.value)}
            className="w-24 bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary text-center focus:outline-none focus:border-accent"
          />
        </div>
      </section>

      {/* Reading */}
      <section className="bg-card border border-border rounded-xl p-4 space-y-4">
        <h3 className="text-text-secondary text-xs uppercase tracking-wider">Reading</h3>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">Show Chinese by default</p>
            <p className="text-text-secondary text-xs">Show Chinese summaries and translations on load</p>
          </div>
          <button
            onClick={() => set('show_chinese', settings.show_chinese === 'true' ? 'false' : 'true')}
            className={`relative w-12 h-6 rounded-full transition-colors ${settings.show_chinese === 'true' ? 'bg-accent' : 'bg-elevated border border-border'}`}
          >
            <span
              className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${settings.show_chinese === 'true' ? 'translate-x-6' : 'translate-x-0.5'}`}
            />
          </button>
        </div>
      </section>

      {/* TTS */}
      <section className="bg-card border border-border rounded-xl p-4 space-y-4">
        <h3 className="text-text-secondary text-xs uppercase tracking-wider">Text-to-Speech</h3>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">TTS provider</p>
            <p className="text-text-secondary text-xs">Primary audio generation service</p>
          </div>
          <select
            value={settings.tts_provider}
            onChange={e => set('tts_provider', e.target.value)}
            className="bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent"
          >
            <option value="google">Google Neural2</option>
            <option value="qwen">Alibaba Qwen TTS</option>
          </select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">Fallback provider</p>
            <p className="text-text-secondary text-xs">Used if primary fails or times out</p>
          </div>
          <select
            value={settings.tts_fallback}
            onChange={e => set('tts_fallback', e.target.value)}
            className="bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent"
          >
            <option value="qwen">Alibaba Qwen TTS</option>
            <option value="google">Google Neural2</option>
          </select>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">Default playback speed</p>
            <p className="text-text-secondary text-xs">Audio player default speed</p>
          </div>
          <select
            value={settings.tts_speed}
            onChange={e => set('tts_speed', e.target.value)}
            className="bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent"
          >
            <option value="0.75">0.75×</option>
            <option value="1.0">1.0×</option>
            <option value="1.25">1.25×</option>
            <option value="1.5">1.5×</option>
          </select>
        </div>
      </section>

      {/* Content Pipeline */}
      <section className="bg-card border border-border rounded-xl p-4 space-y-4">
        <h3 className="text-text-secondary text-xs uppercase tracking-wider">Content Pipeline</h3>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-text-primary text-sm font-medium">Daily content count</p>
            <p className="text-text-secondary text-xs">Items fetched per daily pipeline run</p>
          </div>
          <input
            type="number"
            min={1}
            max={10}
            value={settings.daily_content_count}
            onChange={e => set('daily_content_count', e.target.value)}
            className="w-20 bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm text-text-primary text-center focus:outline-none focus:border-accent"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <div>
              <p className="text-text-primary text-sm font-medium">Interest keywords</p>
              <p className="text-text-secondary text-xs">JSON array — drives LLM content search queries</p>
            </div>
          </div>
          <textarea
            value={settings.keywords}
            onChange={e => set('keywords', e.target.value)}
            rows={3}
            spellCheck={false}
            className="w-full bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-text-primary font-mono focus:outline-none focus:border-accent resize-none"
          />
        </div>
      </section>

      {/* Save / Reset */}
      <div className="flex items-center gap-3 pb-6">
        <button
          onClick={handleSave}
          disabled={saving || !isDirty}
          className="flex items-center gap-2 px-5 py-2.5 bg-accent text-primary font-semibold rounded-xl text-sm hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
        </button>
        {isDirty && (
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2.5 bg-elevated border border-border rounded-xl text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
        )}
      </div>
    </div>
  )
}
