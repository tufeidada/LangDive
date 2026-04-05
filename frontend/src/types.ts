export interface ContentItem {
  id: number
  type: 'article' | 'video'
  title: string
  source: string
  url: string | null
  difficulty: 'A2' | 'B1' | 'B2' | 'C1' | null
  date: string
  segment_count: number
  has_subtitles: boolean
  duration: string | null
  read_time: string | null
  preview_word_count: number
  summary_zh: string | null
}

export interface ContentDetail extends ContentItem {
  content_text: string | null
  audio_path: string | null
  words_json: VocabWord[] | null
  preview_words_json: PreStudyWord[] | null
}

export interface Segment {
  id: number
  content_id: number
  segment_index: number
  title: string
  start_time: number | null
  end_time: number | null
  text_en: string
  summary_zh: string | null
  audio_en_path: string | null
  audio_url: string | null
  preview_words_json: PreStudyWord[] | null
  words_json: VocabWord[] | null
  is_completed: boolean
}

export interface PreStudyWord {
  word: string
  freq_in_content: number
  importance_score: number
  ipa: string
  meaning_zh: string
  example_in_context: string
  known_status: 'unknown' | 'known' | 'fuzzy' | 'ignored'
}

export interface VocabWord {
  word: string
  ipa: string
  freq_in_content: number
  importance_score: number
  meaning_zh: string
  detail_zh: string
  example_en: string
  example_zh: string
  level: 'CET-4' | 'CET-6' | 'IELTS' | 'Advanced'
}

export interface VocabEntry {
  word: string
  ipa: string | null
  meaning_zh: string
  level: string | null
  status: WordStatus
  srs_level: number
  next_review: string | null
  easy_streak: number
  again_count: number
  encounter_count: number
  added_method: string
}

export type WordStatus = 'unknown' | 'fuzzy' | 'known' | 'focus' | 'ignored'
export type WordLevel = 'CET-4' | 'CET-6' | 'IELTS' | 'Advanced'

export const LEVEL_COLORS: Record<string, string> = {
  'CET-4': 'text-level-cet4',
  'CET-6': 'text-level-cet6',
  'IELTS': 'text-level-ielts',
  'Advanced': 'text-level-adv',
}

export const LEVEL_BG_COLORS: Record<string, string> = {
  'CET-4': 'bg-level-cet4/20',
  'CET-6': 'bg-level-cet6/20',
  'IELTS': 'bg-level-ielts/20',
  'Advanced': 'bg-level-adv/20',
}
