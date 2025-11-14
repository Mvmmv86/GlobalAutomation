/**
 * PanelDivider - Componente para divisor arrastável entre painéis
 * Features:
 * - Drag vertical para redimensionar painéis
 * - Visual feedback durante drag
 * - Double-click para resetar tamanhos
 * - Touch support para mobile
 */

import React, { useRef, useCallback, useState } from 'react'

interface PanelDividerProps {
  /** ID do painel acima do divisor */
  panelId: string

  /** Índice do divisor */
  index: number

  /** Callback quando o usuário arrasta o divisor */
  onDrag: (panelId: string, deltaY: number) => void

  /** Callback quando double-click (resetar tamanhos) */
  onReset?: (panelId: string) => void

  /** Altura do divisor em pixels */
  height?: number

  /** Tema (dark/light) */
  theme?: 'dark' | 'light'

  /** Z-index do divisor */
  zIndex?: number
}

export const PanelDivider: React.FC<PanelDividerProps> = ({
  panelId,
  index,
  onDrag,
  onReset,
  height = 4,
  theme = 'dark',
  zIndex = 100
}) => {
  const dividerRef = useRef<HTMLDivElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [startY, setStartY] = useState(0)
  const lastDragYRef = useRef(0)

  /**
   * Mouse down - iniciar drag
   */
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    setStartY(e.clientY)
    lastDragYRef.current = e.clientY

    // Adicionar listeners globais
    const handleMouseMove = (moveEvent: MouseEvent) => {
      const currentY = moveEvent.clientY
      const deltaY = currentY - lastDragYRef.current

      if (Math.abs(deltaY) > 0) {
        onDrag(panelId, deltaY)
        lastDragYRef.current = currentY
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [panelId, onDrag])

  /**
   * Touch start - mobile support
   */
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0]
    setIsDragging(true)
    setStartY(touch.clientY)
    lastDragYRef.current = touch.clientY

    const handleTouchMove = (moveEvent: TouchEvent) => {
      const touch = moveEvent.touches[0]
      const currentY = touch.clientY
      const deltaY = currentY - lastDragYRef.current

      if (Math.abs(deltaY) > 0) {
        onDrag(panelId, deltaY)
        lastDragYRef.current = currentY
      }
    }

    const handleTouchEnd = () => {
      setIsDragging(false)
      document.removeEventListener('touchmove', handleTouchMove)
      document.removeEventListener('touchend', handleTouchEnd)
    }

    document.addEventListener('touchmove', handleTouchMove)
    document.addEventListener('touchend', handleTouchEnd)
  }, [panelId, onDrag])

  /**
   * Double click - resetar tamanhos
   */
  const handleDoubleClick = useCallback(() => {
    if (onReset) {
      onReset(panelId)
    }
  }, [panelId, onReset])

  // Cores baseadas no tema
  const backgroundColor = theme === 'dark' ? '#1e222d' : '#e1e3e8'
  const hoverColor = theme === 'dark' ? '#2a2e39' : '#d1d4dc'
  const activeColor = theme === 'dark' ? '#363a45' : '#b1b4be'

  return (
    <div
      ref={dividerRef}
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
      onDoubleClick={handleDoubleClick}
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        height: `${height}px`,
        backgroundColor: isDragging ? activeColor : backgroundColor,
        cursor: 'ns-resize',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        zIndex,
        transition: isDragging ? 'none' : 'background-color 0.2s ease',
        borderTop: `1px solid ${theme === 'dark' ? '#2a2e39' : '#d1d4dc'}`,
        borderBottom: `1px solid ${theme === 'dark' ? '#2a2e39' : '#d1d4dc'}`
      }}
      onMouseEnter={(e) => {
        if (!isDragging) {
          e.currentTarget.style.backgroundColor = hoverColor
        }
      }}
      onMouseLeave={(e) => {
        if (!isDragging) {
          e.currentTarget.style.backgroundColor = backgroundColor
        }
      }}
    >
      {/* Indicador visual de drag */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '40px',
          height: '2px',
          backgroundColor: theme === 'dark' ? '#4a4e59' : '#9196a1',
          borderRadius: '1px',
          pointerEvents: 'none'
        }}
      />

      {/* Tooltip hint */}
      {!isDragging && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '10px',
            color: theme === 'dark' ? '#6a6e79' : '#7a7e89',
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            opacity: 0,
            transition: 'opacity 0.2s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.opacity = '1'
          }}
        >
          Drag to resize • Double-click to reset
        </div>
      )}
    </div>
  )
}

export default PanelDivider
