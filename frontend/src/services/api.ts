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

// Content Pool (admin)
export const getCandidates = (date?: string) =>
  fetchJSON<any>(`/candidates${date ? `?date=${date}` : ''}`)
export const promoteCandidate = (id: number) =>
  fetchJSON<{ candidate_id: number; content_id: number }>(`/candidates/${id}/promote`, { method: 'PUT' })
export const rejectCandidate = (id: number) =>
  fetchJSON<any>(`/candidates/${id}/reject`, { method: 'PUT' })
export const getSources = () => fetchJSON<any[]>('/sources')
export const addSource = (data: any) =>
  fetchJSON<any>('/sources', { method: 'POST', body: JSON.stringify(data) })
export const updateSource = (id: number, data: any) =>
  fetchJSON<any>(`/sources/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const deleteSource = (id: number) =>
  fetchJSON<any>(`/sources/${id}`, { method: 'DELETE' })
export const submitUrl = (url: string) =>
  fetchJSON<{ candidate_id: number; content_id: number; status: string }>(
    '/content/submit-url',
    { method: 'POST', body: JSON.stringify({ url }) }
  )

// Events (fire-and-forget)
export const logEvent = (event_type: string, data: Record<string, any> = {}) => {
  fetch(`${BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_type, ...data }),
  }).catch(() => {})
}
