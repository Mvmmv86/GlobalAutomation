/**
 * AdvancedChartContainer - Container que integra CustomChart com sistema de indicadores
 * Wrapper que adiciona suporte aos 74+ indicadores do IndicatorEngine
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { CustomChart, CustomChartProps } from '@/components/atoms/CustomChart'
import { IndicatorSelector } from '@/components/molecules/IndicatorSelector'
import { IndicatorChartPanels } from '@/components/molecules/IndicatorChartPanel'
import { useIndicators, useIndicatorData, PreparedIndicatorData } from '@/hooks/useIndicators'
import { IndicatorType, Candle, AnyIndicatorConfig } from '@/utils/indicators'
import { createChart, IChartApi, ISeriesApi, LineData, Time } from 'lightweight-charts'
import { X, Settings } from 'lucide-react'

// Get API URL from environment variable
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

interface AdvancedChartContainerProps extends Omit<CustomChartProps, 'indicators'> {
  showIndicatorSelector?: boolean
  defaultIndicators?: IndicatorType[]
  onIndicatorChange?: (indicators: AnyIndicatorConfig[]) => void
  indicatorPanelHeight?: number
}

export const AdvancedChartContainer: React.FC<AdvancedChartContainerProps> = ({
  symbol,
  interval,
  showIndicatorSelector = true,
  defaultIndicators = [],
  onIndicatorChange,
  indicatorPanelHeight = 100,
  height = 500,
  ...restProps
}) => {
  // Indicator management
  const {
    indicators,
    results,
    isCalculating,
    addIndicator,
    removeIndicator,
    toggleIndicator,
    calculate,
    clearAll
  } = useIndicators({ defaultIndicators })

  // Candles data for indicator calculation
  const [candles, setCandles] = useState<Candle[]>([])
  const [activeIndicatorIds, setActiveIndicatorIds] = useState<string[]>([])

  // Overlay series refs (for indicators displayed on main chart)
  const overlaySeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())
  const chartApiRef = useRef<IChartApi | null>(null)

  // Convert indicators to legacy format for CustomChart basic indicators
  const legacyIndicators = useMemo(() => {
    // CustomChart already handles these basic indicators internally
    // We only use it for the basic ones that are already supported
    return {}
  }, [])

  // Fetch candles for indicator calculation
  useEffect(() => {
    const fetchCandles = async () => {
      try {
        // Map interval
        const intervalMapping: Record<string, string> = {
          '1': '1m', '3': '3m', '5': '5m', '15': '15m', '30': '30m',
          '60': '1h', '240': '4h', '1D': '1d', '1W': '1w', '1M': '1M'
        }
        const binanceInterval = intervalMapping[interval] || '1h'

        const response = await fetch(
          `${API_URL}/api/v1/market/candles?symbol=${symbol}&interval=${binanceInterval}&limit=500`
        )

        const data = await response.json()

        if (data.success && data.candles) {
          const formattedCandles: Candle[] = data.candles.map((c: any) => ({
            time: c.time,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume
          }))
          setCandles(formattedCandles)
        }
      } catch (error) {
        console.error('Error fetching candles for indicators:', error)
      }
    }

    if (indicators.length > 0) {
      fetchCandles()
    }
  }, [symbol, interval, indicators.length])

  // Calculate indicators when candles or configs change
  useEffect(() => {
    if (candles.length > 0 && indicators.length > 0) {
      calculate(candles)
    }
  }, [candles, indicators, calculate])

  // Prepare indicator data for rendering
  const preparedData = useIndicatorData(results, indicators, candles)

  // Get overlay indicators (displayed on main chart)
  const overlayIndicators = useMemo(() => {
    return preparedData.filter(ind => ind.displayType === 'overlay')
  }, [preparedData])

  // Get separate indicators (displayed in panels below)
  const separateIndicators = useMemo(() => {
    return preparedData.filter(ind => ind.displayType === 'separate')
  }, [preparedData])

  // Handle indicator selection
  const handleAddIndicator = useCallback((type: IndicatorType) => {
    addIndicator(type)
    setActiveIndicatorIds(prev => [...prev, type.toLowerCase()])
  }, [addIndicator])

  // Handle indicator removal
  const handleRemoveIndicator = useCallback((id: string) => {
    const config = indicators.find(ind => ind.id === id)
    if (config) {
      removeIndicator(id)
      setActiveIndicatorIds(prev => prev.filter(aid => aid !== id))
    }
  }, [indicators, removeIndicator])

  // Notify parent of indicator changes
  useEffect(() => {
    if (onIndicatorChange) {
      onIndicatorChange(indicators)
    }
  }, [indicators, onIndicatorChange])

  // Calculate chart heights
  const mainChartHeight = useMemo(() => {
    const numericHeight = typeof height === 'number' ? height : 500
    const separatePanelsHeight = separateIndicators.length * indicatorPanelHeight
    return numericHeight - separatePanelsHeight
  }, [height, separateIndicators.length, indicatorPanelHeight])

  return (
    <div className="flex flex-col w-full">
      {/* Toolbar */}
      {showIndicatorSelector && (
        <div className="flex items-center justify-between px-3 py-2 bg-gray-800/50 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <IndicatorSelector
              onSelect={handleAddIndicator}
              activeIndicators={activeIndicatorIds}
            />

            {/* Active indicators badges */}
            {indicators.length > 0 && (
              <div className="flex items-center gap-1 ml-2">
                {indicators.map(ind => (
                  <div
                    key={ind.id}
                    className="flex items-center gap-1 px-2 py-1 bg-gray-700 rounded text-xs"
                  >
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: ind.color }}
                    />
                    <span className="text-gray-300">{ind.type}</span>
                    <button
                      onClick={() => handleRemoveIndicator(ind.id)}
                      className="ml-1 text-gray-500 hover:text-gray-300"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {indicators.length > 0 && (
            <button
              onClick={clearAll}
              className="text-xs text-gray-500 hover:text-gray-300"
            >
              Clear all
            </button>
          )}
        </div>
      )}

      {/* Main Chart with Overlay Indicators */}
      <div className="relative">
        <CustomChart
          symbol={symbol}
          interval={interval}
          height={mainChartHeight}
          indicators={legacyIndicators}
          {...restProps}
        />

        {/* Overlay Indicator Lines - Rendered as an SVG overlay */}
        {overlayIndicators.length > 0 && (
          <OverlayIndicatorRenderer
            indicators={overlayIndicators}
            candles={candles}
          />
        )}

        {/* Calculating indicator */}
        {isCalculating && (
          <div className="absolute top-2 left-2 flex items-center gap-2 px-2 py-1 bg-gray-800/90 rounded text-xs text-gray-400">
            <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            Calculating...
          </div>
        )}
      </div>

      {/* Separate Indicator Panels */}
      <IndicatorChartPanels
        indicators={separateIndicators}
        panelHeight={indicatorPanelHeight}
        onRemove={handleRemoveIndicator}
      />
    </div>
  )
}

// Component for rendering overlay indicators on the main chart
interface OverlayIndicatorRendererProps {
  indicators: PreparedIndicatorData[]
  candles: Candle[]
}

const OverlayIndicatorRenderer: React.FC<OverlayIndicatorRendererProps> = ({
  indicators,
  candles
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesMapRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())

  // Initialize invisible chart for overlay
  useEffect(() => {
    if (!containerRef.current) return

    // Create transparent chart for overlay
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      layout: {
        background: { color: 'transparent' },
        textColor: 'transparent'
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false }
      },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      crosshair: { mode: 0 },
      handleScroll: false,
      handleScale: false
    })

    chartRef.current = chart

    // Handle resize
    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        chart.applyOptions({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        })
      }
    })

    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
      seriesMapRef.current.clear()
    }
  }, [])

  // Update indicator series
  useEffect(() => {
    if (!chartRef.current) return

    const chart = chartRef.current

    // Remove old series
    seriesMapRef.current.forEach((series, id) => {
      if (!indicators.find(ind => ind.id === id)) {
        chart.removeSeries(series)
        seriesMapRef.current.delete(id)
      }
    })

    // Add/update series
    indicators.forEach(indicator => {
      let series = seriesMapRef.current.get(indicator.id)

      if (!series) {
        series = chart.addLineSeries({
          color: indicator.color,
          lineWidth: indicator.lineWidth,
          priceLineVisible: false,
          lastValueVisible: false
        })
        seriesMapRef.current.set(indicator.id, series)
      }

      // Set data
      const data: LineData<Time>[] = indicator.mainLine.map(d => ({
        time: d.time as Time,
        value: d.value
      }))
      series.setData(data)

      // Handle additional lines (like BB upper/lower)
      if (indicator.additionalLines) {
        Object.entries(indicator.additionalLines).forEach(([key, lineData]) => {
          const lineId = `${indicator.id}-${key}`
          let additionalSeries = seriesMapRef.current.get(lineId)

          if (!additionalSeries) {
            additionalSeries = chart.addLineSeries({
              color: indicator.color,
              lineWidth: 1,
              lineStyle: key === 'upper' || key === 'lower' ? 2 : 0,
              priceLineVisible: false,
              lastValueVisible: false
            })
            seriesMapRef.current.set(lineId, additionalSeries)
          }

          const additionalData: LineData<Time>[] = lineData.map(d => ({
            time: d.time as Time,
            value: d.value
          }))
          additionalSeries.setData(additionalData)
        })
      }
    })

    // Fit content
    chart.timeScale().fitContent()
  }, [indicators])

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 10 }}
    />
  )
}

export default AdvancedChartContainer
