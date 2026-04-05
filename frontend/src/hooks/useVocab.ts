import { useState, useCallback } from 'react'
import * as api from '../services/api'
import type { VocabEntry } from '../types'

export function useVocab() {
  const [vocabList, setVocabList] = useState<VocabEntry[]>([])
  const [loading, setLoading] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getVocab()
      setVocabList(data)
    } finally {
      setLoading(false)
    }
  }, [])

  const addWord = useCallback(async (word: string, meaning_zh?: string) => {
    await api.addWord(word, meaning_zh)
    await refresh()
  }, [refresh])

  const updateStatus = useCallback(async (word: string, status: string) => {
    await api.updateWordStatus(word, status)
    await refresh()
  }, [refresh])

  return { vocabList, loading, refresh, addWord, updateStatus }
}
