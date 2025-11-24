/**
 * CanvasProChartComplete - Sistema Completo: Indicadores + Drawing Tools + Alertas
 * FASES 11 & 12: Integração final de todas as funcionalidades
 *
 * Este componente é o wrapper completo que integra:
 * - CanvasProChartMinimal (base com candles, zoom, pan, crosshair, indicadores)
 * - Drawing Tools (linhas de tendência, retângulos, fibonacci, etc)
 * - Alert System (alertas de preço, indicadores, volume, notificações)
 */

import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Bell } from 'lucide-react'
import { CanvasProChartMinimal } from './CanvasProChartMinimal'
import type { AnyIndicatorConfig } from './indicators/types'

// Drawing System
import {
  DrawingManager,
  DrawingRenderer,
  DrawingToolbar,
  DrawingType,
  AnyDrawing,
  ChartPoint,
  CanvasPoint,
  RenderContext
} from './drawing'

// Alert System
import {
  AlertManager,
  AlertNotification,
  AnyAlert
} from './alerts'

export interface CanvasProChartCompleteProps {
  symbol: string
  interval: string
  theme?: 'dark' | 'light'
  candles?: any[]
  width?: string
  height?: string
  className?: string
  refreshInterval?: number
  activeIndicators?: AnyIndicatorConfig[]
}

export const CanvasProChartComplete: React.FC<CanvasProChartCompleteProps> = ({
  symbol,
  interval,
  theme = 'dark',
  candles = [],
  width = '100%',
  height = '600px',
  className = '',
  refreshInterval,
  activeIndicators = []
}) => {
  // Refs
  const containerRef = useRef<HTMLDivElement>(null)
  const drawingCanvasRef = useRef<HTMLCanvasElement>(null)
  const drawingManagerRef = useRef<DrawingManager | null>(null)
  const alertManagerRef = useRef<AlertManager | null>(null)

  // Estado de desenhos
  const [drawings, setDrawings] = useState<AnyDrawing[]>([])
  const [activeDrawingType, setActiveDrawingType] = useState<DrawingType | null>(null)
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null)

  // Estado de alertas
  const [alerts, setAlerts] = useState<AnyAlert[]>([])
  const [notifications, setNotifications] = useState<AlertNotification[]>([])
  const [showNotifications, setShowNotifications] = useState(false)

  // Estado de coordenadas para desenho
  const [chartArea, setChartArea] = useState({ left: 10, right: 730, top: 10, bottom: 540 })
  const [priceRange, setPriceRange] = useState({ min: 0, max: 0 })

  // ============================================================================
  // INICIALIZAÇÃO DOS MANAGERS
  // ============================================================================

  useEffect(() => {
    if (!drawingManagerRef.current) {
      drawingManagerRef.current = new DrawingManager()

      // Listeners para sincronizar estado React
      drawingManagerRef.current.on('stateChange', (state) => {
        setDrawings(state.drawings)
        setActiveDrawingType(state.activeDrawingType)
        setSelectedDrawingId(state.selectedDrawingId)
      })

      console.log('✅ DrawingManager initialized')
    }

    if (!alertManagerRef.current) {
      alertManagerRef.current = new AlertManager()

      // Listeners para sincronizar alertas
      alertManagerRef.current.on('alertTriggered', ({ alert, notification }) => {
        setNotifications(prev => [notification, ...prev])
        console.log('🚨 Alert triggered:', notification.message)
      })

      alertManagerRef.current.on('alertAdded', () => {
        setAlerts(alertManagerRef.current!.getAlerts())
      })

      alertManagerRef.current.on('alertRemoved', () => {
        setAlerts(alertManagerRef.current!.getAlerts())
      })

      console.log('✅ AlertManager initialized')
    }

    return () => {
      // Cleanup listeners (managers são singleton, não destruir)
    }
  }, [])

  // ============================================================================
  // MONITORAMENTO DE ALERTAS
  // ============================================================================

  useEffect(() => {
    if (!alertManagerRef.current || candles.length === 0) return

    const latestCandle = candles[candles.length - 1]
    const currentPrice = parseFloat(latestCandle.close || latestCandle.c || 0)

    // TODO: Passar indicadores calculados
    alertManagerRef.current.checkAlerts({
      candles,
      price: currentPrice,
      indicators: new Map(), // TODO: popular com indicadores
      drawings
    })
  }, [candles, drawings])

  // ============================================================================
  // RENDERIZAÇÃO DE DESENHOS
  // ============================================================================

  useEffect(() => {
    const canvas = drawingCanvasRef.current
    if (!canvas || !containerRef.current || drawings.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Configurar canvas
    const rect = containerRef.current.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1

    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    canvas.style.width = `${rect.width}px`
    canvas.style.height = `${rect.height}px`

    ctx.scale(dpr, dpr)

    // Limpar canvas
    ctx.clearRect(0, 0, rect.width, rect.height)

    // Transformador de coordenadas (ChartPoint -> CanvasPoint)
    const coordTransform = (cp: ChartPoint): CanvasPoint => {
      // TODO: Implementar transformação real baseada em viewport
      // Por enquanto, mock básico
      return {
        x: chartArea.left + 100, // Mock
        y: chartArea.top + 100   // Mock
      }
    }

    // Renderizar todos os desenhos
    const renderCtx: RenderContext = {
      ctx,
      width: rect.width,
      height: rect.height,
      dpr,
      chartArea
    }

    DrawingRenderer.renderAll(
      drawings,
      renderCtx,
      coordTransform,
      selectedDrawingId,
      null
    )

  }, [drawings, selectedDrawingId, chartArea])

  // ============================================================================
  // HANDLERS DE DESENHO
  // ============================================================================

  const handleSelectTool = useCallback((type: DrawingType | null) => {
    if (!drawingManagerRef.current) return

    if (type) {
      drawingManagerRef.current.startDrawing(type)
    } else {
      drawingManagerRef.current.cancelDrawing()
    }
  }, [])

  const handleDeleteSelected = useCallback(() => {
    if (!drawingManagerRef.current || !selectedDrawingId) return
    drawingManagerRef.current.removeDrawing(selectedDrawingId)
  }, [selectedDrawingId])

  const handleClearAll = useCallback(() => {
    if (!drawingManagerRef.current) return
    drawingManagerRef.current.clearDrawings()
  }, [])

  const handleExport = useCallback(() => {
    if (!drawingManagerRef.current) return
    const json = drawingManagerRef.current.exportDrawings()

    // Download como arquivo
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `drawings_${symbol}_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [symbol])

  const handleImport = useCallback((json: string) => {
    if (!drawingManagerRef.current) return
    drawingManagerRef.current.importDrawings(json)
  }, [])

  // ============================================================================
  // CLICK NO GRÁFICO PARA ADICIONAR PONTOS DE DESENHO
  // ============================================================================

  const handleChartClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!drawingManagerRef.current || !activeDrawingType) return

    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return

    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // TODO: Converter coordenadas canvas -> ChartPoint (timestamp + price)
    // Por enquanto, mock
    const chartPoint: ChartPoint = {
      timestamp: Date.now(),
      price: 50000 // Mock - precisa calcular baseado em Y
    }

    const completed = drawingManagerRef.current.addPoint(chartPoint)
    if (completed) {
      console.log('✅ Drawing completed')
    }
  }, [activeDrawingType])

  // ============================================================================
  // UI COMPONENTS
  // ============================================================================

  const unreadCount = notifications.filter(n => !n.read).length

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width,
        height,
        overflow: 'hidden'
      }}
      onClick={handleChartClick}
    >
      {/* Gráfico Base */}
      <CanvasProChartMinimal
        symbol={symbol}
        interval={interval}
        theme={theme}
        candles={candles}
        width="100%"
        height="100%"
        className={className}
        refreshInterval={refreshInterval}
        activeIndicators={activeIndicators}
      />

      {/* Canvas de Desenhos (overlay) */}
      <canvas
        ref={drawingCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 10
        }}
      />

      {/* Drawing Toolbar */}
      <DrawingToolbar
        activeDrawingType={activeDrawingType}
        selectedDrawingId={selectedDrawingId}
        drawings={drawings}
        onSelectTool={handleSelectTool}
        onDeleteSelected={handleDeleteSelected}
        onClearAll={handleClearAll}
        onExport={handleExport}
        onImport={handleImport}
        theme={theme}
      />

      {/* Botão de Notificações */}
      <button
        onClick={() => setShowNotifications(!showNotifications)}
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          padding: '8px 12px',
          background: theme === 'dark' ? '#2a2e39' : '#ffffff',
          border: `1px solid ${theme === 'dark' ? '#2a2e39' : '#e0e3eb'}`,
          borderRadius: '6px',
          color: theme === 'dark' ? '#d1d4dc' : '#131722',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '13px',
          fontWeight: 500,
          zIndex: 100,
          boxShadow: theme === 'dark'
            ? '0 2px 8px rgba(0,0,0,0.3)'
            : '0 2px 8px rgba(0,0,0,0.1)'
        }}
      >
        <Bell size={16} />
        Alertas
        {unreadCount > 0 && (
          <span
            style={{
              background: '#F44336',
              color: '#fff',
              borderRadius: '10px',
              padding: '2px 6px',
              fontSize: '11px',
              fontWeight: 600
            }}
          >
            {unreadCount}
          </span>
        )}
      </button>

      {/* Painel de Notificações */}
      {showNotifications && (
        <div
          style={{
            position: 'absolute',
            top: 50,
            right: 10,
            width: '320px',
            maxHeight: '400px',
            background: theme === 'dark' ? '#1e222d' : '#ffffff',
            border: `1px solid ${theme === 'dark' ? '#2a2e39' : '#e0e3eb'}`,
            borderRadius: '8px',
            padding: '12px',
            zIndex: 100,
            boxShadow: theme === 'dark'
              ? '0 4px 16px rgba(0,0,0,0.4)'
              : '0 4px 16px rgba(0,0,0,0.15)',
            overflowY: 'auto'
          }}
        >
          <div
            style={{
              fontSize: '14px',
              fontWeight: 600,
              marginBottom: '12px',
              color: theme === 'dark' ? '#d1d4dc' : '#131722'
            }}
          >
            Notificações ({notifications.length})
          </div>

          {notifications.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '20px',
                color: theme === 'dark' ? '#787b86' : '#787b86',
                fontSize: '13px'
              }}
            >
              Nenhuma notificação ainda
            </div>
          ) : (
            notifications.slice(0, 10).map((notif) => (
              <div
                key={notif.id}
                style={{
                  padding: '10px',
                  marginBottom: '8px',
                  background: theme === 'dark' ? '#131722' : '#f5f7fa',
                  borderRadius: '6px',
                  borderLeft: `3px solid ${notif.read ? '#787b86' : '#2196F3'}`,
                  fontSize: '12px',
                  color: theme === 'dark' ? '#d1d4dc' : '#131722'
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: '4px' }}>
                  {notif.alert.name}
                </div>
                <div style={{ opacity: 0.8 }}>
                  {notif.message}
                </div>
                <div
                  style={{
                    marginTop: '4px',
                    fontSize: '11px',
                    opacity: 0.6
                  }}
                >
                  {new Date(notif.triggeredAt).toLocaleString('pt-BR')}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

CanvasProChartComplete.displayName = 'CanvasProChartComplete'

export default CanvasProChartComplete
