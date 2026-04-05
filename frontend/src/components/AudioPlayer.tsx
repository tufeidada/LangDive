// src/components/AudioPlayer.tsx
import { Play, Pause } from 'lucide-react'
import { useAudio } from '../hooks/useAudio'
import { useEventLogger } from '../hooks/useEventLogger'

const SPEEDS = [0.75, 1.0, 1.25, 1.5]

export default function AudioPlayer({ src }: { src: string }) {
  const { playing, currentTime, duration, speed, toggle, changeSpeed } = useAudio(src)
  const { log } = useEventLogger()

  const handleToggle = () => {
    toggle()
    log('audio_play', { playing: !playing })
  }

  const handleSpeed = (s: number) => {
    changeSpeed(s)
    log('audio_speed_change', { speed: s })
  }

  const formatTime = (t: number) => {
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-card rounded-lg p-3 border border-border mb-4 flex items-center gap-3">
      <button onClick={handleToggle} className="text-accent">
        {playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
      </button>
      <div className="flex-1 text-xs text-text-secondary">
        {formatTime(currentTime)} / {formatTime(duration || 0)}
      </div>
      <div className="flex gap-1">
        {SPEEDS.map(s => (
          <button
            key={s}
            onClick={() => handleSpeed(s)}
            className={`text-xs px-1.5 py-0.5 rounded ${speed === s ? 'bg-accent text-primary' : 'text-text-secondary hover:text-text-primary'}`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  )
}
