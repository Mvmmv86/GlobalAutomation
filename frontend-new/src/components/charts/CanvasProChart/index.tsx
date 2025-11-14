/**
 * CanvasProChart - Sistema Profissional de Gráficos para Trading
 * Utilizando arquitetura multi-layer com dirty regions
 */

import React, { useRef, useEffect, forwardRef, useImperativeHandle, useState, useCallback } from 'react'
import { getTheme } from './theme'
import { LayerManager } from './core/LayerManager'
import { PanelManager } from './PanelManager'
import { DataManager } from './DataManager'
import { ChartEngine } from './Engine'

// Types
export interface CanvasProChartProps {
  symbol: string
  interval: string
  theme?: 'dark' | 'light'
  candles: any[]
  positions?: any[]
  stopLoss?: number | null
  takeProfit?: number | null
  onDragSLTP?: (type: 'STOP_LOSS' | 'TAKE_PROFIT', newPrice: number) => void
  width?: string
  height?: string
  className?: string
}

export interface CanvasProChartHandle {
  addIndicator: (config: any) => void
  removeIndicator: (id: string) => void
  updateIndicator: (id: string, updates: any) => void
  getIndicators: () => any[]
  clearIndicators: () => void
  resetZoom: () => void
  zoomIn: () => void
  zoomOut: () => void
}

// Export do painel de indicadores
export { IndicatorPanel } from './components/IndicatorPanel'

const CanvasProChart = forwardRef<CanvasProChartHandle, CanvasProChartProps>((props, ref) => {
  const {
    symbol,
    interval,
    theme = 'dark',
    candles = [],
    positions = [],
    stopLoss = null,
    takeProfit = null,
    onDragSLTP,
    width = '100%',
    height = '600px',
    className = ''
  } = props

  // Refs
  const containerRef = useRef<HTMLDivElement>(null)
  const layerManagerRef = useRef<LayerManager | null>(null)
  const panelManagerRef = useRef<PanelManager | null>(null)
  const dataManagerRef = useRef<DataManager | null>(null)
  const engineRef = useRef<ChartEngine | null>(null)

  // State
  const [indicators, setIndicators] = useState<any[]>([])
  const [isInitialized, setIsInitialized] = useState(false)

  /**
   * Inicializa todo o sistema de layers
   */
  useEffect(() => {
    if (!containerRef.current) return

    console.log('🎨 [CanvasProChart] Inicializando sistema de layers...')

    try {
      // Criar container para layers
      const layerContainer = document.createElement('div')
      layerContainer.className = 'chart-layers-container'
      layerContainer.style.position = 'relative'
      layerContainer.style.width = '100%'
      layerContainer.style.height = '100%'
      containerRef.current.appendChild(layerContainer)

      // Obter dimensões
      const rect = containerRef.current.getBoundingClientRect()
      const chartTheme = getTheme(theme)

      // Criar canvas temporário para o Engine (será substituído pelas layers)
      const tempCanvas = document.createElement('canvas')
      tempCanvas.width = rect.width
      tempCanvas.height = rect.height

      // Inicializar managers
      dataManagerRef.current = new DataManager()
      panelManagerRef.current = new PanelManager(layerContainer, rect.height)
      engineRef.current = new ChartEngine(tempCanvas, dataManagerRef.current, chartTheme)

      // Criar LayerManager com todos os componentes
      layerManagerRef.current = new LayerManager({
        container: layerContainer,
        dataManager: dataManagerRef.current,
        panelManager: panelManagerRef.current,
        engine: engineRef.current,
        theme: chartTheme
      })

      // Configurar callbacks do PanelManager
      panelManagerRef.current.onLayoutChangeCallback((layout) => {
        console.log('📐 [PanelManager] Layout changed:', layout)

        // Atualizar layers para cada painel
        layout.panels.forEach(panel => {
          if (panel.type === 'separate' && panel.indicators.length > 0) {
            layerManagerRef.current?.addSeparatePanelLayer(panel.id, panel.indicators)
          }
        })

        // Re-renderizar
        layerManagerRef.current?.forceRender()
      })

      // Redimensionar layers
      layerManagerRef.current.resize(rect.width, rect.height)

      console.log('✅ [CanvasProChart] Sistema de layers inicializado com sucesso')
      setIsInitialized(true)

    } catch (error) {
      console.error('❌ [CanvasProChart] Erro ao inicializar:', error)
    }

    // Cleanup
    return () => {
      console.log('🧹 [CanvasProChart] Limpando sistema de layers...')
      layerManagerRef.current?.destroy()
      panelManagerRef.current?.destroy()
      dataManagerRef.current = null
      engineRef.current = null

      if (containerRef.current) {
        containerRef.current.innerHTML = ''
      }
    }
  }, [theme])

  /**
   * Atualiza dados quando candles mudam
   */
  useEffect(() => {
    if (!isInitialized || !dataManagerRef.current || candles.length === 0) {
      return
    }

    console.log(`📊 [CanvasProChart] Atualizando ${candles.length} candles`)

    // Atualizar DataManager
    dataManagerRef.current.clear()
    dataManagerRef.current.addCandles(candles)

    // Atualizar ViewportManager com o número de candles
    layerManagerRef.current?.updateDataLength(candles.length)

    // Marcar layers como dirty para re-renderizar
    layerManagerRef.current?.markLayerDirty('background')
    layerManagerRef.current?.markLayerDirty('main')

    // Se houver indicadores, marcar layer de indicadores também
    if (indicators.length > 0) {
      layerManagerRef.current?.markLayerDirty('indicators')
    }

  }, [candles, isInitialized, indicators.length])

  /**
   * Atualiza posições, SL/TP
   */
  useEffect(() => {
    if (!isInitialized || !dataManagerRef.current) {
      return
    }

    // Atualizar DataManager com posições
    if (positions && positions.length > 0) {
      console.log(`📍 [CanvasProChart] Atualizando ${positions.length} posições`)
      // dataManagerRef.current.setPositions(positions) // Se o DataManager suportar
    }

    // Atualizar SL/TP
    if (stopLoss !== null || takeProfit !== null) {
      console.log('🎯 [CanvasProChart] Atualizando SL/TP:', { stopLoss, takeProfit })
      // Marcar overlay layer como dirty
      layerManagerRef.current?.markLayerDirty('overlays')
    }

  }, [positions, stopLoss, takeProfit, isInitialized])

  /**
   * Redimensionamento
   */
  useEffect(() => {
    if (!isInitialized || !containerRef.current) return

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect

        console.log(`📐 [CanvasProChart] Resize: ${width}x${height}`)

        // Redimensionar todos os componentes
        engineRef.current?.resize(width, height)
        panelManagerRef.current?.resize(height)
        layerManagerRef.current?.resize(width, height)
      }
    })

    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
    }
  }, [isInitialized])

  /**
   * Handlers de indicadores
   */
  const addIndicator = useCallback((config: any) => {
    console.log('➕ [CanvasProChart] Adicionando indicador:', config)

    const newIndicator = {
      ...config,
      id: config.id || `${config.type}-${Date.now()}`
    }

    setIndicators(prev => [...prev, newIndicator])

    // Se for indicador separado, criar novo painel
    if (config.separate && panelManagerRef.current) {
      const panelId = panelManagerRef.current.addPanel({
        type: 'separate',
        height: 150,
        minHeight: 100,
        maxHeight: 300,
        indicators: [newIndicator.id],
        title: config.name || config.type
      })

      console.log(`📊 [CanvasProChart] Novo painel criado: ${panelId}`)
    }

    // Marcar layer de indicadores como dirty
    layerManagerRef.current?.markLayerDirty('indicators')

  }, [])

  const removeIndicator = useCallback((id: string) => {
    console.log('➖ [CanvasProChart] Removendo indicador:', id)

    setIndicators(prev => prev.filter(ind => ind.id !== id))

    // Remover do painel se necessário
    if (panelManagerRef.current) {
      const panels = panelManagerRef.current.getPanels()
      panels.forEach(panel => {
        if (panel.indicators.includes(id)) {
          panelManagerRef.current?.removeIndicatorFromPanel(panel.id, id)
        }
      })
    }

    // Marcar layer de indicadores como dirty
    layerManagerRef.current?.markLayerDirty('indicators')

  }, [])

  const updateIndicator = useCallback((id: string, updates: any) => {
    console.log('🔄 [CanvasProChart] Atualizando indicador:', id, updates)

    setIndicators(prev => prev.map(ind =>
      ind.id === id ? { ...ind, ...updates } : ind
    ))

    // Marcar layer de indicadores como dirty
    layerManagerRef.current?.markLayerDirty('indicators')

  }, [])

  const clearIndicators = useCallback(() => {
    console.log('🧹 [CanvasProChart] Limpando todos os indicadores')

    setIndicators([])

    // Limpar painéis separados
    panelManagerRef.current?.clearSeparatePanels()

    // Marcar layer de indicadores como dirty
    layerManagerRef.current?.markLayerDirty('indicators')

  }, [])

  /**
   * Handlers de zoom
   */
  const resetZoom = useCallback(() => {
    console.log('🔄 [CanvasProChart] Reset zoom')
    layerManagerRef.current?.goToLatest()
  }, [])

  const zoomIn = useCallback(() => {
    console.log('🔍+ [CanvasProChart] Zoom in')
    layerManagerRef.current?.zoom(-0.1) // zoom in = negative delta
  }, [])

  const zoomOut = useCallback(() => {
    console.log('🔍- [CanvasProChart] Zoom out')
    layerManagerRef.current?.zoom(0.1) // zoom out = positive delta
  }, [])

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    addIndicator,
    removeIndicator,
    updateIndicator,
    getIndicators: () => indicators,
    clearIndicators,
    resetZoom,
    zoomIn,
    zoomOut
  }), [indicators, addIndicator, removeIndicator, updateIndicator, clearIndicators, resetZoom, zoomIn, zoomOut])

  // Atualizar layers quando indicadores mudam
  useEffect(() => {
    if (!isInitialized || !dataManagerRef.current) return

    console.log(`📈 [CanvasProChart] ${indicators.length} indicadores ativos`)

    // Atualizar DataManager com indicadores
    // dataManagerRef.current.setIndicators(indicators) // Se o DataManager suportar

    // Marcar layer de indicadores como dirty
    if (indicators.length > 0) {
      layerManagerRef.current?.markLayerDirty('indicators')
    }

  }, [indicators, isInitialized])

  return (
    <div
      ref={containerRef}
      className={`canvas-pro-chart ${className}`}
      style={{
        width,
        height,
        backgroundColor: getTheme(theme).background,
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {!isInitialized && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          color: getTheme(theme).text.primary,
          fontSize: '14px',
          fontFamily: 'monospace'
        }}>
          Inicializando gráfico...
        </div>
      )}
    </div>
  )
})

CanvasProChart.displayName = 'CanvasProChart'

export default CanvasProChart
export { CanvasProChart }