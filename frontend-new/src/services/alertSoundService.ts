/**
 * Alert Sound Service
 * Provides audio playback for indicator alerts using Web Audio API
 * Supports multiple sound types with adjustable volume
 */

// Sound types available for alerts
export type AlertSoundType = 'default' | 'bell' | 'chime' | 'alarm' | 'notification' | 'none'

// Audio context singleton
let audioContext: AudioContext | null = null

// Get or create audio context
const getAudioContext = (): AudioContext => {
  if (!audioContext) {
    audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
  }
  return audioContext
}

// Sound frequency configurations
const SOUND_CONFIGS: Record<AlertSoundType, { frequencies: number[]; durations: number[]; type: OscillatorType }> = {
  default: {
    frequencies: [523, 659, 784], // C5, E5, G5 - pleasant major chord arpeggio
    durations: [100, 100, 200],
    type: 'sine'
  },
  bell: {
    frequencies: [880, 1760, 880], // A5, A6, A5 - bell-like tone
    durations: [150, 50, 200],
    type: 'triangle'
  },
  chime: {
    frequencies: [1047, 1319, 1568, 2093], // C6, E6, G6, C7 - wind chime
    durations: [100, 100, 100, 300],
    type: 'sine'
  },
  alarm: {
    frequencies: [880, 440, 880, 440], // A5, A4 alternating - urgent
    durations: [100, 100, 100, 100],
    type: 'square'
  },
  notification: {
    frequencies: [587, 784], // D5, G5 - simple two-tone notification
    durations: [100, 150],
    type: 'sine'
  },
  none: {
    frequencies: [],
    durations: [],
    type: 'sine'
  }
}

// Play a single tone
const playTone = (
  ctx: AudioContext,
  frequency: number,
  duration: number,
  type: OscillatorType,
  volume: number,
  startTime: number
): void => {
  const oscillator = ctx.createOscillator()
  const gainNode = ctx.createGain()

  oscillator.type = type
  oscillator.frequency.setValueAtTime(frequency, startTime)

  // ADSR envelope for natural sound
  gainNode.gain.setValueAtTime(0, startTime)
  gainNode.gain.linearRampToValueAtTime(volume, startTime + 0.01) // Attack
  gainNode.gain.exponentialRampToValueAtTime(volume * 0.7, startTime + duration / 2000) // Decay
  gainNode.gain.exponentialRampToValueAtTime(0.001, startTime + duration / 1000) // Release

  oscillator.connect(gainNode)
  gainNode.connect(ctx.destination)

  oscillator.start(startTime)
  oscillator.stop(startTime + duration / 1000 + 0.05)
}

/**
 * Play an alert sound
 * @param soundType - The type of sound to play
 * @param volume - Volume level (0 to 1, default 0.5)
 */
export const playAlertSound = async (soundType: AlertSoundType, volume: number = 0.5): Promise<void> => {
  if (soundType === 'none') return

  try {
    const ctx = getAudioContext()

    // Resume audio context if suspended (required by browsers)
    if (ctx.state === 'suspended') {
      await ctx.resume()
    }

    const config = SOUND_CONFIGS[soundType]
    if (!config || config.frequencies.length === 0) return

    const now = ctx.currentTime
    let timeOffset = 0

    config.frequencies.forEach((freq, index) => {
      const duration = config.durations[index]
      playTone(ctx, freq, duration, config.type, volume, now + timeOffset / 1000)
      timeOffset += duration * 0.8 // Slight overlap for smoother sound
    })
  } catch (error) {
    console.error('Error playing alert sound:', error)
  }
}

/**
 * Play a custom beep with specific frequency
 * @param frequency - Frequency in Hz
 * @param duration - Duration in ms
 * @param volume - Volume level (0 to 1)
 */
export const playBeep = async (frequency: number = 440, duration: number = 200, volume: number = 0.5): Promise<void> => {
  try {
    const ctx = getAudioContext()

    if (ctx.state === 'suspended') {
      await ctx.resume()
    }

    playTone(ctx, frequency, duration, 'sine', volume, ctx.currentTime)
  } catch (error) {
    console.error('Error playing beep:', error)
  }
}

/**
 * Test all available sounds
 * @param volume - Volume level for test sounds
 */
export const testAllSounds = async (volume: number = 0.3): Promise<void> => {
  const sounds: AlertSoundType[] = ['default', 'bell', 'chime', 'alarm', 'notification']

  for (const sound of sounds) {
    console.log(`Testing sound: ${sound}`)
    await playAlertSound(sound, volume)
    await new Promise(resolve => setTimeout(resolve, 1000)) // Wait between sounds
  }
}

// Sound labels for UI
export const SOUND_LABELS: Record<AlertSoundType, string> = {
  default: 'Default',
  bell: 'Bell',
  chime: 'Chime',
  alarm: 'Alarm',
  notification: 'Notification',
  none: 'No Sound'
}

// Export sound types array for UI selectors
export const AVAILABLE_SOUNDS: AlertSoundType[] = ['default', 'bell', 'chime', 'alarm', 'notification', 'none']
