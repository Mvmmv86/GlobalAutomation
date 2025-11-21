/**
 * CanvasProChartWithIndicators - Wrapper do CanvasProChartMinimal com sistema completo de indicadores
 * Integra os 25+ indicadores técnicos existentes ao gráfico minimal
 * FASES 9 & 10: Sistema de Indicadores Profissional + Painéis Separados
 */

import React, { useState, useCallback, useMemo, useRef } from 'react'
import { Activity } from 'lucide-react'
import { CanvasProChartMinimal } from './CanvasProChartMinimal'
import { IndicatorPanel } from './components/IndicatorPanel'
import { SeparatePanel } from './components/SeparatePanel'
import {
  AnyIndicatorConfig,
  IndicatorType,
  INDICATOR_PRESETS
} from './indicators/types'

export interface CanvasProChartWithIndicatorsProps {
  symbol: string
  interval: string
  theme?: 'dark' | 'light'
  candles?: any[]
  width?: string
  height?: string
  className?: string
  refreshInterval?: number
}

const CanvasProChartWithIndicators: React.FC<CanvasProChartWithIndicatorsProps> = ({
  symbol,
  interval,
  theme = 'dark',
  candles = [],
  width = '100%',
  height = '600px',
  className = '',
  refreshInterval
}) => {
  // Estado para indicadores ativos
  const [activeIndicators, setActiveIndicators] = useState<AnyIndicatorConfig[]>([])
  const [showIndicatorPanel, setShowIndicatorPanel] = useState(false)

  // Estado para crosshair sincronizado
  const [hoveredCandleIndex, setHoveredCandleIndex] = useState<number | null>(null)
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null)

  // Refs para viewport sincronizado
  const containerRef = useRef<HTMLDivElement>(null)

  // Separar indicadores overlay e separate
  const { overlayIndicators, separateIndicators } = useMemo(() => {
    const overlay = activeIndicators.filter(ind => ind.displayType === 'overlay')
    const separate = activeIndicators.filter(ind => ind.displayType === 'separate')

    // Agrupar indicadores separados por tipo (cada tipo em seu próprio painel)
    const groupedSeparate: Record<string, AnyIndicatorConfig[]> = {}
    separate.forEach(ind => {
      const key = ind.type
      if (!groupedSeparate[key]) {
        groupedSeparate[key] = []
      }
      groupedSeparate[key].push(ind)
    })

    return {
      overlayIndicators: overlay,
      separateIndicators: groupedSeparate
    }
  }, [activeIndicators])

  // Calcular alturas dinâmicas
  const numSeparatePanels = Object.keys(separateIndicators).length
  const separatePanelHeight = 150 // Altura de cada painel separado
  const mainChartHeight = numSeparatePanels > 0
    ? `calc(${height} - ${numSeparatePanels * separatePanelHeight}px)`
    : height

  // Adicionar indicador
  const handleAddIndicator = useCallback((type: IndicatorType) => {
    const preset = INDICATOR_PRESETS[type]
    if (!preset) {
      console.error(`❌ Preset not found for indicator type: ${type}`)
      return
    }

    const newIndicator: AnyIndicatorConfig = {
      id: `${type}_${Date.now()}`,
      type,
      enabled: true,
      displayType: preset.displayType || 'overlay',
      color: preset.color || '#2196F3',
      lineWidth: preset.lineWidth || 2,
      params: preset.params || {}
    } as AnyIndicatorConfig

    setActiveIndicators(prev => [...prev, newIndicator])
    console.log(`✅ Added indicator: ${type} (${preset.displayType})`, newIndicator)
  }, [])

  // Remover indicador
  const handleRemoveIndicator = useCallback((id: string) => {
    setActiveIndicators(prev => prev.filter(ind => ind.id !== id))
    console.log(`🗑️ Removed indicator: ${id}`)
  }, [])

  // Toggle indicador (habilitar/desabilitar)
  const handleToggleIndicator = useCallback((id: string, enabled: boolean) => {
    setActiveIndicators(prev =>
      prev.map(ind => ind.id === id ? { ...ind, enabled } : ind)
    )
    console.log(`👁️ Toggled indicator ${id}: ${enabled}`)
  }, [])

  // Atualizar configuração de indicador
  const handleUpdateIndicator = useCallback((id: string, updates: Partial<AnyIndicatorConfig>) => {
    setActiveIndicators(prev =>
      prev.map(ind => ind.id === id ? { ...ind, ...updates } : ind)
    )
    console.log(`⚙️ Updated indicator ${id}:`, updates)
  }, [])

  const bgButton = theme === 'dark' ? '#2a2e39' : '#e0e3eb'
  const textColor = theme === 'dark' ? '#d1d4dc' : '#131722'

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width,
        height,
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {/* Gráfico Principal */}
      <div style={{ height: mainChartHeight, position: 'relative' }}>
        <CanvasProChartMinimal
          symbol={symbol}
          interval={interval}
          theme={theme}
          candles={candles}
          width="100%"
          height="100%"
          className={className}
          refreshInterval={refreshInterval}
          // Passar apenas indicadores overlay
          activeIndicators={overlayIndicators}
        />
      </div>

      {/* Painéis Separados (RSI, MACD, Stochastic, etc) */}
      {Object.entries(separateIndicators).map(([type, indicators], index) => (
        <SeparatePanel
          key={`separate-${type}-${index}`}
          indicators={indicators}
          candles={candles}
          theme={theme}
          width={containerRef.current?.clientWidth || 800}
          height={separatePanelHeight}
          viewport={{
            zoom: 1, // TODO: Sincronizar com viewport do gráfico principal
            offsetX: 0,
            offsetY: 0
          }}
          hoveredCandleIndex={hoveredCandleIndex}
          mousePos={mousePos}
        />
      ))}

      {/* Botão de Indicadores */}
      <button
        onClick={() => setShowIndicatorPanel(!showIndicatorPanel)}
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          padding: '8px 12px',
          background: showIndicatorPanel ? '#2196F3' : bgButton,
          border: 'none',
          borderRadius: '6px',
          color: showIndicatorPanel ? '#ffffff' : textColor,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '13px',
          fontWeight: 500,
          zIndex: 100,
          boxShadow: theme === 'dark'
            ? '0 2px 8px rgba(0,0,0,0.3)'
            : '0 2px 8px rgba(0,0,0,0.1)',
          transition: 'all 0.2s ease'
        }}
        onMouseEnter={(e) => {
          if (!showIndicatorPanel) {
            e.currentTarget.style.background = theme === 'dark' ? '#363a45' : '#d0d3db'
          }
        }}
        onMouseLeave={(e) => {
          if (!showIndicatorPanel) {
            e.currentTarget.style.background = bgButton
          }
        }}
      >
        <Activity size={16} />
        Indicadores ({activeIndicators.filter(i => i.enabled).length})
        {numSeparatePanels > 0 && <span style={{ fontSize: '11px', opacity: 0.8 }}>({numSeparatePanels} painéis)</span>}
      </button>

      {/* Painel de Indicadores */}
      {showIndicatorPanel && (
        <IndicatorPanel
          activeIndicators={activeIndicators}
          onAddIndicator={handleAddIndicator}
          onRemoveIndicator={handleRemoveIndicator}
          onToggleIndicator={handleToggleIndicator}
          onUpdateIndicator={handleUpdateIndicator}
          theme={theme}
          onClose={() => setShowIndicatorPanel(false)}
        />
      )}
    </div>
  )
}

CanvasProChartWithIndicators.displayName = 'CanvasProChartWithIndicators'

export default CanvasProChartWithIndicators
export { CanvasProChartWithIndicators }
