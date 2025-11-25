/**
 * SeparateIndicatorPanels - Container para múltiplos painéis de indicadores
 * Gerencia a exibição de indicadores separados com resize handle
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { IChartApi } from 'lightweight-charts'
import { GripHorizontal, ChevronDown, ChevronUp } from 'lucide-react'
import { SeparateIndicatorPanel } from './SeparateIndicatorPanel'
import { AnyIndicatorConfig, Candle } from '@/utils/indicators'

interface SeparateIndicatorPanelsProps {
  indicators: AnyIndicatorConfig[]
  candles: Candle[]
  theme?: 'light' | 'dark'
  mainChart?: IChartApi | null
  onRemoveIndicator?: (id: string) => void
  onIndicatorSettings?: (id: string) => void
  className?: string
}

// Altura mínima e máxima do container
const MIN_HEIGHT = 100
const MAX_HEIGHT = 500
const DEFAULT_HEIGHT = 250

export const SeparateIndicatorPanels: React.FC<SeparateIndicatorPanelsProps> = ({
  indicators,
  candles,
  theme = 'dark',
  mainChart,
  onRemoveIndicator,
  onIndicatorSettings,
  className = ''
}) => {
  // Filtrar apenas indicadores separados
  const separateIndicators = useMemo(
    () => indicators.filter(ind => ind.enabled && ind.displayType === 'separate'),
    [indicators]
  )

  // Altura do container (persiste no localStorage)
  const [containerHeight, setContainerHeight] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('indicator-panels-height')
      return saved ? parseInt(saved, 10) : DEFAULT_HEIGHT
    }
    return DEFAULT_HEIGHT
  })

  // Estado de colapso
  const [isCollapsed, setIsCollapsed] = useState(false)

  // Estado reativo para drag (importante para re-render durante drag)
  const [isDragging, setIsDragging] = useState(false)

  // Ref para resize
  const containerRef = useRef<HTMLDivElement>(null)
  const startY = useRef(0)
  const startHeight = useRef(0)

  // Calcular altura por painel
  const panelHeight = useMemo(() => {
    if (separateIndicators.length === 0) return 0
    return Math.max(80, containerHeight / separateIndicators.length)
  }, [containerHeight, separateIndicators.length])

  // Salvar altura no localStorage
  useEffect(() => {
    localStorage.setItem('indicator-panels-height', containerHeight.toString())
  }, [containerHeight])

  // Handle resize start
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
    startY.current = e.clientY
    startHeight.current = containerHeight

    document.body.style.cursor = 'row-resize'
    document.body.style.userSelect = 'none'
  }, [containerHeight])

  // Handle resize move - usar isDragging como dependência para garantir cleanup correto
  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      e.preventDefault()
      const deltaY = startY.current - e.clientY  // Invertido porque estamos redimensionando para cima
      const newHeight = Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, startHeight.current + deltaY))
      setContainerHeight(newHeight)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }

    // Adicionar listeners apenas quando dragging está ativo
    document.addEventListener('mousemove', handleMouseMove, { passive: false })
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isDragging])

  // Se não há indicadores separados, não renderizar nada
  if (separateIndicators.length === 0) {
    return null
  }

  return (
    <div
      ref={containerRef}
      className={`flex flex-col bg-[#131722] ${className}`}
    >
      {/* 🔥 Resize Handle - Barra horizontal estilo TradingView (mais alto para facilitar clique) */}
      <div
        className={`flex items-center justify-center h-3 cursor-row-resize transition-colors duration-150 group select-none ${
          isDragging
            ? 'bg-[#2962FF]'
            : 'bg-[#2a2e39] hover:bg-[#363a45]'
        }`}
        onMouseDown={handleResizeStart}
        title="Arraste para redimensionar"
        style={{ touchAction: 'none' }}
      >
        <div className="flex items-center gap-1">
          <div className={`w-8 h-0.5 rounded-full transition-colors ${isDragging ? 'bg-white' : 'bg-[#4c525e] group-hover:bg-[#787b86]'}`} />
          <div className={`w-1.5 h-1.5 rounded-full transition-colors ${isDragging ? 'bg-white' : 'bg-[#4c525e] group-hover:bg-[#787b86]'}`} />
          <div className={`w-1.5 h-1.5 rounded-full transition-colors ${isDragging ? 'bg-white' : 'bg-[#4c525e] group-hover:bg-[#787b86]'}`} />
          <div className={`w-1.5 h-1.5 rounded-full transition-colors ${isDragging ? 'bg-white' : 'bg-[#4c525e] group-hover:bg-[#787b86]'}`} />
          <div className={`w-8 h-0.5 rounded-full transition-colors ${isDragging ? 'bg-white' : 'bg-[#4c525e] group-hover:bg-[#787b86]'}`} />
        </div>
      </div>

      {/* Header com toggle de colapso e nome dos indicadores */}
      <div className="flex items-center justify-between px-3 py-1 bg-[#1e222d] border-b border-[#2a2e39]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-[#787b86]">
            Indicadores
          </span>
          <span className="text-[10px] text-[#4c525e]">
            ({separateIndicators.length} ativos)
          </span>
        </div>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-[#787b86] hover:text-[#d1d4dc] hover:bg-[#2a2e39] rounded transition-colors"
          title={isCollapsed ? 'Expandir painéis' : 'Recolher painéis'}
        >
          {isCollapsed ? (
            <>
              <ChevronUp className="w-3 h-3" />
              <span>Expandir</span>
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              <span>Recolher</span>
            </>
          )}
        </button>
      </div>

      {/* Painéis de indicadores */}
      {!isCollapsed && (
        <div
          className="flex flex-col overflow-y-auto bg-[#131722]"
          style={{ height: containerHeight }}
        >
          {separateIndicators.map(indicator => (
            <SeparateIndicatorPanel
              key={indicator.id}
              config={indicator}
              candles={candles}
              height={panelHeight}
              theme={theme}
              onRemove={onRemoveIndicator ? () => onRemoveIndicator(indicator.id) : undefined}
              onSettings={onIndicatorSettings ? () => onIndicatorSettings(indicator.id) : undefined}
              timeScaleSync={mainChart}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default SeparateIndicatorPanels
