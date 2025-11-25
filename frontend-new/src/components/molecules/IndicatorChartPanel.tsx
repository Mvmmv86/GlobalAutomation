/**
 * IndicatorChartPanel - Painel de gráfico para indicadores separados (RSI, MACD, Stoch, etc)
 * Usa lightweight-charts para renderização
 */

import React, { useEffect, useRef, useMemo } from 'react'
import { createChart, IChartApi, ISeriesApi, LineData, HistogramData, Time } from 'lightweight-charts'
import { PreparedIndicatorData, IndicatorSeriesData } from '@/hooks/useIndicators'
import { X } from 'lucide-react'

interface IndicatorChartPanelProps {
  indicator: PreparedIndicatorData
  height?: number
  onRemove?: () => void
  className?: string
}

// Colors for additional lines
const ADDITIONAL_LINE_COLORS: Record<string, string> = {
  signal: '#FF6B6B',
  histogram: '#4ECDC4',
  d: '#FFE66D',
  upper: '#26A69A',
  lower: '#EF5350',
  overbought: '#ff6b6b55',
  oversold: '#4ecdc455',
  pdi: '#26A69A',
  mdi: '#EF5350'
}

export const IndicatorChartPanel: React.FC<IndicatorChartPanelProps> = ({
  indicator,
  height = 100,
  onRemove,
  className = ''
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<Map<string, ISeriesApi<'Line' | 'Histogram'>>>(new Map())

  // Format data for chart
  const formatData = (data: IndicatorSeriesData[]): LineData<Time>[] => {
    return data.map(d => ({
      time: d.time as Time,
      value: d.value
    }))
  }

  // Get panel title
  const panelTitle = useMemo(() => {
    const names: Record<string, string> = {
      RSI: 'RSI (14)',
      MACD: 'MACD (12,26,9)',
      STOCH: 'Stochastic (14,3)',
      STOCHRSI: 'Stochastic RSI',
      CCI: 'CCI (20)',
      ADX: 'ADX (14)',
      ATR: 'ATR (14)',
      ROC: 'ROC (12)',
      WILLR: 'Williams %R',
      AO: 'Awesome Oscillator',
      TRIX: 'TRIX (18)',
      OBV: 'OBV',
      MFI: 'MFI (14)',
      KST: 'KST'
    }
    return names[indicator.type] || indicator.type
  }, [indicator.type])

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return

    // Create chart
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: '#1a1a2e' },
        textColor: '#a0aec0'
      },
      grid: {
        vertLines: { color: '#2d3748' },
        horzLines: { color: '#2d3748' }
      },
      rightPriceScale: {
        borderColor: '#4a5568',
        scaleMargins: { top: 0.1, bottom: 0.1 }
      },
      timeScale: {
        borderColor: '#4a5568',
        visible: false
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#718096',
          width: 1,
          style: 2
        },
        horzLine: {
          color: '#718096',
          width: 1,
          style: 2
        }
      }
    })

    chartRef.current = chart

    // Handle resize
    const resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        chart.applyOptions({
          width: entry.contentRect.width
        })
      }
    })

    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
      seriesRef.current.clear()
    }
  }, [height])

  // Update series data
  useEffect(() => {
    if (!chartRef.current) return

    const chart = chartRef.current

    // Clear existing series
    seriesRef.current.forEach(series => {
      chart.removeSeries(series)
    })
    seriesRef.current.clear()

    // Add main line
    if (indicator.mainLine.length > 0) {
      const mainSeries = chart.addLineSeries({
        color: indicator.color,
        lineWidth: indicator.lineWidth,
        priceLineVisible: false,
        lastValueVisible: true
      })
      mainSeries.setData(formatData(indicator.mainLine))
      seriesRef.current.set('main', mainSeries)
    }

    // Add additional lines
    if (indicator.additionalLines) {
      Object.entries(indicator.additionalLines).forEach(([key, data]) => {
        if (data.length === 0) return

        const color = ADDITIONAL_LINE_COLORS[key] || '#888888'

        // Special handling for histogram
        if (key === 'histogram') {
          const histogramSeries = chart.addHistogramSeries({
            color: '#4ECDC4',
            priceLineVisible: false,
            lastValueVisible: false
          })
          const histogramData: HistogramData<Time>[] = data.map(d => ({
            time: d.time as Time,
            value: d.value,
            color: d.value >= 0 ? '#26A69A' : '#EF5350'
          }))
          histogramSeries.setData(histogramData)
          seriesRef.current.set(key, histogramSeries as any)
        }
        // Special handling for overbought/oversold levels
        else if (key === 'overbought' || key === 'oversold') {
          const levelSeries = chart.addLineSeries({
            color: color,
            lineWidth: 1,
            lineStyle: 2, // Dashed
            priceLineVisible: false,
            lastValueVisible: false
          })
          levelSeries.setData(formatData(data))
          seriesRef.current.set(key, levelSeries)
        }
        // Regular additional lines
        else {
          const lineSeries = chart.addLineSeries({
            color: color,
            lineWidth: Math.max(1, indicator.lineWidth - 1),
            priceLineVisible: false,
            lastValueVisible: false
          })
          lineSeries.setData(formatData(data))
          seriesRef.current.set(key, lineSeries)
        }
      })
    }

    // Fit content
    chart.timeScale().fitContent()
  }, [indicator])

  // Get current value for display
  const currentValue = useMemo(() => {
    if (indicator.mainLine.length === 0) return null
    return indicator.mainLine[indicator.mainLine.length - 1]?.value
  }, [indicator.mainLine])

  return (
    <div className={`bg-gray-900 border-t border-gray-700 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1 bg-gray-800/50 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: indicator.color }}
          />
          <span className="text-xs font-medium text-gray-300">
            {panelTitle}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {currentValue !== null && (
            <span className="text-xs text-gray-400">
              {currentValue.toFixed(2)}
            </span>
          )}
          {onRemove && (
            <button
              onClick={onRemove}
              className="text-gray-500 hover:text-gray-300 transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Chart Container */}
      <div ref={containerRef} style={{ height }} />
    </div>
  )
}

// Multi-panel component for multiple indicators
interface IndicatorChartPanelsProps {
  indicators: PreparedIndicatorData[]
  panelHeight?: number
  onRemove?: (id: string) => void
  className?: string
}

export const IndicatorChartPanels: React.FC<IndicatorChartPanelsProps> = ({
  indicators,
  panelHeight = 100,
  onRemove,
  className = ''
}) => {
  const separateIndicators = indicators.filter(ind => ind.displayType === 'separate')

  if (separateIndicators.length === 0) {
    return null
  }

  return (
    <div className={`flex flex-col ${className}`}>
      {separateIndicators.map(indicator => (
        <IndicatorChartPanel
          key={indicator.id}
          indicator={indicator}
          height={panelHeight}
          onRemove={onRemove ? () => onRemove(indicator.id) : undefined}
        />
      ))}
    </div>
  )
}

export default IndicatorChartPanel
