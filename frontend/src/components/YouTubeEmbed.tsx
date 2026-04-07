// src/components/YouTubeEmbed.tsx
// YouTube IFrame API wrapper that supports seekTo and currentTime polling
import { useEffect, useRef } from 'react'

declare global {
  interface Window {
    YT: {
      Player: new (
        elementId: string,
        options: {
          videoId: string
          playerVars?: Record<string, number | string>
          events?: {
            onReady?: (event: { target: YTPlayer }) => void
            onStateChange?: (event: { data: number }) => void
          }
        }
      ) => YTPlayer
    }
    onYouTubeIframeAPIReady: () => void
  }
}

interface YTPlayer {
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
  getCurrentTime: () => number
  destroy: () => void
}

interface Props {
  videoId: string
  startTime?: number
  onTimeUpdate?: (time: number) => void
  seekRef?: React.MutableRefObject<((t: number) => void) | null>
}

export default function YouTubeEmbed({ videoId, startTime = 0, onTimeUpdate, seekRef }: Props) {
  const playerRef = useRef<YTPlayer | null>(null)
  const containerIdRef = useRef(`yt-player-${Math.random().toString(36).slice(2)}`)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Load YT IFrame API script once
  useEffect(() => {
    if (!window.YT) {
      const tag = document.createElement('script')
      tag.src = 'https://www.youtube.com/iframe_api'
      document.body.appendChild(tag)
    }
  }, [])

  // Create player instance
  useEffect(() => {
    const containerId = containerIdRef.current

    const initPlayer = () => {
      if (playerRef.current) {
        try { playerRef.current.destroy() } catch (_) { /* ignore */ }
        playerRef.current = null
      }

      playerRef.current = new window.YT.Player(containerId, {
        videoId,
        playerVars: {
          start: Math.floor(startTime),
          rel: 0,
          modestbranding: 1,
        },
        events: {
          onReady: () => {
            // Start polling currentTime every 500ms
            if (pollingRef.current) clearInterval(pollingRef.current)
            pollingRef.current = setInterval(() => {
              if (playerRef.current?.getCurrentTime) {
                const t = playerRef.current.getCurrentTime()
                onTimeUpdate?.(t)
              }
            }, 500)
          },
        },
      })

      // Expose seekTo via seekRef
      if (seekRef) {
        seekRef.current = (t: number) => {
          playerRef.current?.seekTo(t, true)
        }
      }
    }

    if (window.YT?.Player) {
      initPlayer()
    } else {
      window.onYouTubeIframeAPIReady = initPlayer
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current)
      try { playerRef.current?.destroy() } catch (_) { /* ignore */ }
      playerRef.current = null
    }
  }, [videoId])

  return (
    <div className="aspect-video mb-4 rounded-lg overflow-hidden">
      <div id={containerIdRef.current} className="w-full h-full" />
    </div>
  )
}
