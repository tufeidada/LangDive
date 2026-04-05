import { useCallback } from 'react'
import { logEvent } from '../services/api'

export function useEventLogger() {
  const log = useCallback((event_type: string, data: Record<string, any> = {}) => {
    logEvent(event_type, data)
  }, [])
  return { log }
}
