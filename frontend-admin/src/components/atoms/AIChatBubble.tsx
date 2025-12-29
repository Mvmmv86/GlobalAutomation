/**
 * AI Chat Bubble
 * Floating button with animated Neural Node logo and notification badge
 * Logo features orbiting rings and particles with cyan/purple gradient
 */
import React from 'react'
import { useChat } from '@/contexts/ChatContext'

// Neural Node Logo with orbiting rings and particles
const NeuralNodeLogo: React.FC<{ size?: 'sm' | 'md' | 'lg' | 'xl' }> = ({ size = 'lg' }) => {
  // Size mapping
  const sizeMap = {
    sm: 24,
    md: 32,
    lg: 48,
    xl: 64
  }

  const iconSize = sizeMap[size]
  const particleSize = iconSize * 0.125 // 6px for 48px icon
  const orbitRadius = iconSize * 0.4 // distance from center for particles

  return (
    <div
      className="logo-icon relative"
      style={{ width: iconSize, height: iconSize }}
    >
      {/* Outer Ring - rotating clockwise */}
      <div
        className="absolute inset-0 rounded-full animate-rotate-cw"
        style={{
          border: '2px solid rgba(0, 240, 255, 0.3)',
        }}
      />

      {/* Middle Ring - rotating counter-clockwise */}
      <div
        className="absolute rounded-full animate-rotate-ccw"
        style={{
          inset: '15%',
          border: '1px solid rgba(139, 92, 246, 0.5)',
        }}
      />

      {/* Core - pulsing gradient */}
      <div
        className="absolute rounded-full animate-pulse-scale"
        style={{
          inset: '30%',
          background: 'linear-gradient(to bottom right, #00F0FF, #8B5CF6)',
          boxShadow: '0 0 20px rgba(0, 240, 255, 0.5)',
        }}
      />

      {/* Orbiting Particles */}
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="absolute"
          style={{
            width: particleSize,
            height: particleSize,
            top: '50%',
            left: '50%',
            marginTop: -particleSize / 2,
            marginLeft: -particleSize / 2,
            animation: `orbit ${3 + i * 0.5}s linear infinite ${i * 0.5}s`,
          }}
        >
          <div
            className="absolute rounded-full"
            style={{
              width: particleSize,
              height: particleSize,
              backgroundColor: '#00F0FF',
              boxShadow: '0 0 10px rgba(0, 240, 255, 0.8)',
              transform: `translateX(${orbitRadius}px)`,
            }}
          />
        </div>
      ))}

      {/* CSS Animations */}
      <style>{`
        @keyframes rotate-cw {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes rotate-ccw {
          from { transform: rotate(0deg); }
          to { transform: rotate(-360deg); }
        }

        @keyframes pulse-scale {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }

        @keyframes orbit {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .animate-rotate-cw {
          animation: rotate-cw 20s linear infinite;
        }

        .animate-rotate-ccw {
          animation: rotate-ccw 15s linear infinite;
        }

        .animate-pulse-scale {
          animation: pulse-scale 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  )
}

export const AIChatBubble: React.FC = () => {
  const { toggleChat, unreadAlerts, alerts } = useChat()

  // Determine badge color based on most critical alert type
  const getBadgeColor = (): string => {
    const hasCritical = alerts.some(a => !a.read && a.type === 'critical')
    const hasWarning = alerts.some(a => !a.read && a.type === 'warning')
    const hasInfo = alerts.some(a => !a.read && a.type === 'info')

    if (hasCritical) return 'bg-red-500'
    if (hasWarning) return 'bg-yellow-500'
    if (hasInfo) return 'bg-blue-500'
    return 'bg-emerald-500'
  }

  const hasUnread = unreadAlerts > 0

  return (
    <button
      onClick={toggleChat}
      className={`
        fixed bottom-6 right-6 z-50
        w-20 h-20 rounded-full
        bg-gray-900/95 backdrop-blur-sm
        border border-cyan-500/20
        shadow-lg shadow-cyan-500/20
        flex items-center justify-center
        transition-all duration-300 ease-out
        hover:scale-105 hover:shadow-xl hover:shadow-cyan-500/30
        hover:border-cyan-500/40
        focus:outline-none focus:ring-4 focus:ring-cyan-500/30
        group
        ${hasUnread ? 'ring-2 ring-cyan-500/50' : ''}
      `}
      aria-label="Abrir chat com IA"
    >
      {/* Neural Node Logo */}
      <div className="transition-transform duration-300 group-hover:scale-105">
        <NeuralNodeLogo size="lg" />
      </div>

      {/* Notification Badge */}
      {hasUnread && (
        <span
          className={`
            absolute -top-1 -right-1
            min-w-[24px] h-6 px-2
            flex items-center justify-center
            rounded-full text-xs font-bold text-white
            ${getBadgeColor()}
            border-2 border-gray-900
            shadow-lg
            animate-bounce
          `}
        >
          {unreadAlerts > 99 ? '99+' : unreadAlerts}
        </span>
      )}

      {/* Pulse effect when there are unread alerts */}
      {hasUnread && (
        <>
          <span className="absolute inset-0 rounded-full bg-cyan-500/20 animate-ping" />
          <span className="absolute inset-0 rounded-full bg-cyan-500/10 animate-pulse" />
        </>
      )}

      {/* Subtle outer glow ring */}
      <span className="absolute inset-0 rounded-full border border-cyan-500/10 group-hover:border-cyan-500/30 transition-colors" />
    </button>
  )
}

export default AIChatBubble
