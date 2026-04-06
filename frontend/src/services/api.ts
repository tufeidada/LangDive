import type { ContentItem, ContentDetail, Segment, VocabEntry, VocabWord } from '../types'

const BASE = '/api'

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) throw new Error(`API error: ${resp.status}`)
  return resp.json()
}

// Content
export const getToday = () => fetchJSON<ContentItem[]>('/content/today')
export const getHistory = (date?: string) => fetchJSON<ContentItem[]>(`/content/history${date ? `?date=${date}` : ''}`)
export const getContent = (id: number) => fetchJSON<ContentDetail>(`/content/${id}`)
export const getSegments = (id: number) => fetchJSON<Segment[]>(`/content/${id}/segments`)
export const getSegment = (id: number, idx: number) => fetchJSON<Segment>(`/content/${id}/segments/${idx}`)
export const markSegmentComplete = (id: number, idx: number) =>
  fetchJSON(`/content/${id}/segments/${idx}/complete`, { method: 'POST' })
export const getTranscript = (id: number) =>
  fetchJSON<{ text: string; start: number; duration: number }[]>(`/content/${id}/transcript`)

// Vocabulary
export const getVocab = () => fetchJSON<VocabEntry[]>('/vocab')
export const getReviewWords = () => fetchJSON<VocabEntry[]>('/vocab/review')
export const addWord = (word: string, meaning_zh?: string) =>
  fetchJSON('/vocab', { method: 'POST', body: JSON.stringify({ word, meaning_zh }) })
export const updateWordStatus = (word: string, status: string) =>
  fetchJSON(`/vocab/${word}/status`, { method: 'PUT', body: JSON.stringify({ status }) })
export const reviewWord = (word: string, grade: number) =>
  fetchJSON<{ srs_level: number; next_review: string; status: string }>(`/vocab/${word}/review`, { method: 'PUT', body: JSON.stringify({ grade }) })
export const aiLookup = (word: string, context_sentence?: string) =>
  fetchJSON<VocabWord>('/vocab/ai-lookup', { method: 'POST', body: JSON.stringify({ word, context_sentence }) })
export const previewAddAll = (words: { word: string; meaning_zh: string; level?: string }[]) =>
  fetchJSON<{ added: number }>('/vocab/preview-add-all', { method: 'POST', body: JSON.stringify({ words }) })

// Settings
export const getSettings = () => fetchJSON<Record<string, string>>('/settings')
export const updateSettings = (updates: Record<string, string>) =>
  fetchJSON('/settings', { method: 'PUT', body: JSON.stringify(updates) })

// Events (fire-and-forget)
export const logEvent = (event_type: string, data: Record<string, any> = {}) => {
  fetch(`${BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type, ...data }),
  }).catch(() => {})
}
