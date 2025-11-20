/**
 * CanvasProChart - VERSÃO MÍNIMA INCREMENTAL
 * FASE 5: Renderização de Candles
 *
 * Objetivo: Renderizar candles (velas) no gráfico
 * Anterior: Grid profissional implementado na FASE 4
 */

import React, { useRef, useEffect, useState, useCallback } from 'react'
import { getTheme } from './theme'
import { LayerManagerMinimal } from './core/LayerManagerMinimal'
import { DataManagerMinimal } from './core/DataManagerMinimal'

export interface CanvasProChartMinimalProps {
  symbol: string
  interval: string
  theme?: 'dark' | 'light'
  candles?: any[]
  width?: string
  height?: string
  className?: string
}

const CanvasProChartMinimal: React.FC<CanvasProChartMinimalProps> = ({
  symbol,
  interval,
  theme = 'dark',
  candles = [],
  width = '100%',
  height = '600px',
  className = ''
}) => {
  console.log('🚀🚀🚀 [CanvasProMinimal] COMPONENTE CHAMADO!', { symbol, interval, candles: candles.length })

  const layerManagerRef = useRef<LayerManagerMinimal | null>(null)
  const dataManagerRef = useRef<DataManagerMinimal | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)

  /**
   * 🔥 SOLUÇÃO FINAL: useEffect com containerRef.current
   */
  const containerRef = useRef<HTMLDivElement>(null)

  // 🎯 LOG ANTES DO useEffect PARA TESTAR
  console.log('💡 [CanvasProMinimal] ANTES DO useEffect:', {
    containerRefExists: !!containerRef,
    layerManagerExists: !!layerManagerRef.current,
    isInitialized
  })

  /**
   * ✅ INICIALIZAÇÃO DO SISTEMA (BEST PRACTICE - React + Canvas)
   * Pattern confirmado por:
   * - TradingView Lightweight Charts
   * - React Official Docs
   * - Stack Overflow community
   */
  useEffect(() => {
    const container = containerRef.current

    // ✅ Null check (best practice)
    if (!container) {
      console.warn('⚠️ [CanvasProMinimal] Container ref não disponível')
      return
    }

    // Obter dimensões do container
    const rect = container.getBoundingClientRect()

    // ✅ Validar dimensões antes de inicializar
    if (!rect.width || !rect.height || rect.width < 100 || rect.height < 100) {
      console.warn('⚠️ [CanvasProMinimal] Dimensões inválidas:', rect)
      // Retry após 100ms (caso container ainda não tenha tamanho)
      const retryTimer = setTimeout(() => {
        const newRect = container.getBoundingClientRect()
        if (newRect.width > 100 && newRect.height > 100) {
          console.log('🔄 [CanvasProMinimal] Dimensões válidas detectadas, forçando re-init')
          // Trigger re-render para tentar novamente
          setIsInitialized(false)
        }
      }, 100)
      return () => clearTimeout(retryTimer)
    }

    console.log('🎨 [CanvasProMinimal] Inicializando sistema...', {
      symbol,
      interval,
      dimensions: rect
    })

    try {
      const chartTheme = getTheme(theme)

      // ✅ CRIAR MANAGERS (seguindo pattern TradingView)
      // 1. DataManager: armazena e gerencia os candles
      dataManagerRef.current = new DataManagerMinimal(symbol, interval)

      // 2. LayerManager: cria e gerencia as layers de canvas
      layerManagerRef.current = new LayerManagerMinimal(container, chartTheme)

      console.log('✅ [CanvasProMinimal] Sistema inicializado com sucesso')

      // ✅ Marcar como inicializado (ativa o useEffect de renderização)
      setIsInitialized(true)

    } catch (error) {
      console.error('❌ [CanvasProMinimal] Erro ao inicializar:', error)
    }

    // ✅ CLEANUP FUNCTION (best practice - React Official Docs)
    // Executada antes de re-render com dependências mudadas E no unmount
    return () => {
      console.log('🧹 [CanvasProMinimal] Cleanup - destruindo instâncias')

      if (layerManagerRef.current) {
        layerManagerRef.current.destroy()
        layerManagerRef.current = null
      }
      if (dataManagerRef.current) {
        dataManagerRef.current.destroy()
        dataManagerRef.current = null
      }
      setIsInitialized(false)
    }
  }, [symbol, interval, theme]) // ✅ Dependencies: re-inicializar se mudar símbolo, intervalo ou tema

  /**
   * FASE 5: Atualizar grid E candles quando dados mudam
   */
  useEffect(() => {
    if (!isInitialized || !dataManagerRef.current || !layerManagerRef.current) return

    if (candles.length === 0) {
      console.log('⚠️ [CanvasProMinimal] Nenhum candle disponível ainda')
      return
    }

    // Atualizar dados no DataManager
    dataManagerRef.current.updateCandles(candles)

    // Obter estatísticas dos dados
    const priceRange = dataManagerRef.current.getPriceRange()
    const timeRange = dataManagerRef.current.getTimeRange()
    const candlesData = dataManagerRef.current.getCandles()

    console.log(`📊 [CanvasProMinimal] Atualizando grid E candles:`, {
      candles: candles.length,
      priceRange,
      timeRange: {
        start: new Date(timeRange.start).toISOString(),
        end: new Date(timeRange.end).toISOString()
      }
    })

    // ✅ FASE 4: Atualizar grid profissional
    layerManagerRef.current.updateGrid(
      priceRange.min,
      priceRange.max,
      timeRange.start,
      timeRange.end
    )

    // ✅ FASE 5: Atualizar candles
    layerManagerRef.current.updateCandles(
      candlesData,
      priceRange.min,
      priceRange.max,
      timeRange.start,
      timeRange.end
    )
  }, [isInitialized, candles.length]) // ✅ FIX CRITICAL: REMOVIDO symbol/interval que causavam loop!

  const chartTheme = getTheme(theme)

  return (
    <div
      ref={containerRef}
      className={`canvas-pro-chart-minimal ${className}`}
      style={{
        width,
        height,
        backgroundColor: chartTheme.background,
        position: 'relative',
        overflow: 'hidden'
      }}
    />
  )
}

CanvasProChartMinimal.displayName = 'CanvasProChartMinimal'

export default CanvasProChartMinimal
export { CanvasProChartMinimal }
