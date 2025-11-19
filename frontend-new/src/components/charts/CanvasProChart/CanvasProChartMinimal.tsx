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

  // 🎯 TESTE ULTRA SIMPLES: useEffect SEM DEPENDÊNCIAS
  useEffect(() => {
    console.log('🔥🔥🔥 [CanvasProMinimal] useEffect DISPARADO (sem dependências)!')
    console.log('📦 Estado atual:', { isInitialized, hasLayerManager: !!layerManagerRef.current })
  }, []) // ✅ SEM dependências - executa UMA VEZ ao montar

  // ✅ CLEANUP quando componente desmonta
  useEffect(() => {
    return () => {
      console.log('🧹 [CanvasProMinimal] Cleanup (componente desmontando)')

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
  }, [])

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
