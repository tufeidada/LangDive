// src/components/ShadowMode.tsx
import { useState, useRef, useEffect } from 'react'
import { X, Play, Mic, Square, RefreshCw, ChevronRight, Volume2 } from 'lucide-react'
import { useEventLogger } from '../hooks/useEventLogger'

interface Props {
  sentences: string[]
  onExit: () => void
}

export default function ShadowMode({ sentences, onExit }: Props) {
  const { log } = useEventLogger()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [recording, setRecording] = useState(false)
  const [recordingUrl, setRecordingUrl] = useState<string | null>(null)
  const [micError, setMicError] = useState<string | null>(null)
  const [playingOriginal, setPlayingOriginal] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const prevRecordingUrlRef = useRef<string | null>(null)

  // Log shadow_start once on mount
  useEffect(() => {
    log('shadow_start', { total_sentences: sentences.length })
  }, [])

  // Clean up previous recording URL when it changes
  useEffect(() => {
    if (prevRecordingUrlRef.current) {
      URL.revokeObjectURL(prevRecordingUrlRef.current)
    }
    prevRecordingUrlRef.current = recordingUrl
  }, [recordingUrl])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (prevRecordingUrlRef.current) {
        URL.revokeObjectURL(prevRecordingUrlRef.current)
      }
    }
  }, [])

  const currentSentence = sentences[currentIndex] ?? ''

  const playOriginal = () => {
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(currentSentence)
    u.lang = 'en-US'
    u.rate = 0.9
    setPlayingOriginal(true)
    u.onend = () => setPlayingOriginal(false)
    u.onerror = () => setPlayingOriginal(false)
    window.speechSynthesis.speak(u)
    log('shadow_original_play', { sentence_index: currentIndex })
  }

  const startRecording = async () => {
    setMicError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setRecordingUrl(URL.createObjectURL(blob))
        stream.getTracks().forEach(t => t.stop())
        log('shadow_record', { sentence_index: currentIndex })
      }
      recorder.start()
      mediaRecorderRef.current = recorder
      setRecording(true)
    } catch (err: any) {
      if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
        setMicError('Microphone access denied. Please allow microphone access in your browser settings.')
      } else {
        setMicError('Could not access microphone. Please check your device settings.')
      }
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  const playRecording = () => {
    if (recordingUrl) {
      const audio = new Audio(recordingUrl)
      audio.play()
      log('shadow_recording_play', { sentence_index: currentIndex })
    }
  }

  const reRecord = () => {
    setRecordingUrl(null)
    setMicError(null)
  }

  const handleNext = () => {
    // Stop any ongoing speech
    window.speechSynthesis.cancel()
    setPlayingOriginal(false)
    // Stop recording if active
    if (recording) {
      mediaRecorderRef.current?.stop()
      setRecording(false)
    }

    const nextIndex = currentIndex + 1
    if (nextIndex >= sentences.length) {
      log('shadow_complete', { total_sentences: sentences.length })
      onExit()
      return
    }

    setCurrentIndex(nextIndex)
    setRecordingUrl(null)
    setMicError(null)
  }

  const handleExit = () => {
    window.speechSynthesis.cancel()
    if (recording) {
      mediaRecorderRef.current?.stop()
    }
    onExit()
  }

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-text-primary font-semibold text-base flex items-center gap-2">
          <Mic className="w-4 h-4 text-accent" />
          Shadow Reading
        </h2>
        <button
          onClick={handleExit}
          className="flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          <X className="w-4 h-4" />
          Exit
        </button>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-2 mb-4">
        <div className="text-xs text-text-secondary">
          Sentence {currentIndex + 1} / {sentences.length}
        </div>
        <div className="flex-1 bg-border rounded-full h-1">
          <div
            className="bg-accent rounded-full h-1 transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / sentences.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Current sentence */}
      <div className="bg-primary rounded-lg p-4 mb-5 border border-border">
        <p className="text-text-primary text-base leading-relaxed">{currentSentence}</p>
      </div>

      {/* Listen original */}
      <div className="mb-4">
        <button
          onClick={playOriginal}
          disabled={playingOriginal}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            playingOriginal
              ? 'bg-accent/50 text-primary cursor-not-allowed'
              : 'bg-accent text-primary hover:bg-accent/90'
          }`}
        >
          <Volume2 className="w-4 h-4" />
          {playingOriginal ? 'Playing…' : 'Listen Original'}
        </button>
      </div>

      {/* Recording controls */}
      {!recordingUrl && (
        <div className="mb-4">
          {!recording ? (
            <button
              onClick={startRecording}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-border text-text-secondary hover:border-accent hover:text-accent transition-colors"
            >
              <Mic className="w-4 h-4" />
              Record
            </button>
          ) : (
            <button
              onClick={stopRecording}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 transition-colors animate-pulse"
            >
              <Square className="w-4 h-4" />
              Stop Recording
            </button>
          )}
        </div>
      )}

      {/* Mic error */}
      {micError && (
        <div className="mb-4 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          {micError}
        </div>
      )}

      {/* Playback section — shown after recording */}
      {recordingUrl && (
        <div className="mb-5 p-3 bg-primary rounded-lg border border-border">
          <p className="text-xs text-text-secondary mb-2 font-medium">Compare playbacks</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={playRecording}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-border text-text-secondary hover:border-accent hover:text-accent transition-colors"
            >
              <Play className="w-3.5 h-3.5" />
              My Recording
            </button>
            <button
              onClick={playOriginal}
              disabled={playingOriginal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-border text-text-secondary hover:border-accent hover:text-accent transition-colors disabled:opacity-50"
            >
              <Volume2 className="w-3.5 h-3.5" />
              {playingOriginal ? 'Playing…' : 'Original'}
            </button>
            <button
              onClick={reRecord}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-border text-text-secondary hover:border-accent hover:text-accent transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Re-record
            </button>
          </div>
        </div>
      )}

      {/* Next button */}
      <button
        onClick={handleNext}
        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-border text-text-secondary hover:border-accent hover:text-accent transition-colors"
      >
        {currentIndex + 1 >= sentences.length ? 'Finish' : 'Next'}
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  )
}
