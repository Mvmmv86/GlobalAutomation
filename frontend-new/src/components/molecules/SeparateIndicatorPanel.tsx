/**
 * SeparateIndicatorPanel - Painel individual para indicadores separados
 * Renderiza indicadores como RSI, MACD, STOCH, ADX etc. em painéis próprios abaixo do gráfico principal
 */

import React, { useEffect, useRef, useMemo, useCallback } from 'react'
import { createChart, IChartApi, ISeriesApi, LineData, HistogramData, Time } from 'lightweight-charts'
import { X, Settings, GripHorizontal } from 'lucide-react'
import { AnyIndicatorConfig, IndicatorResult, INDICATOR_NAMES, INDICATOR_PRESETS, indicatorEngine, Candle } from '@/utils/indicators'

interface SeparateIndicatorPanelProps {
  config: AnyIndicatorConfig
  candles: Candle[]
  height?: number
  theme?: 'light' | 'dark'
  onRemove?: () => void
  onSettings?: () => void
  className?: string
  timeScaleSync?: IChartApi | null  // Para sincronizar timeScale com gráfico principal
}

// Cores para linhas adicionais
const ADDITIONAL_LINE_COLORS: Record<string, string> = {
  signal: '#FF6B6B',
  histogram: '#4ECDC4',
  d: '#FFE66D',
  upper: '#26A69A',
  lower: '#EF5350',
  overbought: '#ff6b6b55',
  oversold: '#4ecdc455',
  pdi: '#26A69A',
  mdi: '#EF5350',
  base: '#2962FF',
  spanA: '#10B98180',
  spanB: '#EF444480'
}

export const SeparateIndicatorPanel: React.FC<SeparateIndicatorPanelProps> = ({
  config,
  candles,
  height = 120,
  theme = 'dark',
  onRemove,
  onSettings,
  className = '',
  timeScaleSync
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRefs = useRef<Map<string, ISeriesApi<'Line' | 'Histogram'>>>(new Map())

  // Calcular resultado do indicador
  // 🔥 FIX: Usar JSON.stringify para params para garantir que mudanças nos parâmetros disparem recálculo
  const paramsKey = JSON.stringify(config.params)

  // 🔧 DEBUG: Log quando config muda
  console.log(`📊 SeparateIndicatorPanel [${config.type}] RENDER:`, {
    id: config.id,
    color: config.color,
    lineWidth: config.lineWidth,
    params: config.params,
    paramsKey
  })

  const indicatorResult = useMemo(() => {
    console.log(`📊 [${config.type}] useMemo RECALCULANDO indicatorResult`)
    if (!candles.length || !config.enabled) return null
    return indicatorEngine.calculateSync(config, candles)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.type, config.enabled, paramsKey, candles])

  // Título do painel com parâmetros
  // 🔥 FIX: Usar paramsKey para garantir atualização do título quando params mudam
  const panelTitle = useMemo(() => {
    const baseName = INDICATOR_NAMES[config.type] || config.type
    const params = config.params

    // Formatar parâmetros baseado no tipo
    switch (config.type) {
      case 'RSI':
        return `${baseName} (${params.period})`
      case 'MACD':
        return `${baseName} (${params.fastPeriod},${params.slowPeriod},${params.signalPeriod})`
      case 'STOCH':
        return `${baseName} (${params.period},${params.signalPeriod})`
      case 'STOCHRSI':
        return `${baseName} (${params.rsiPeriod},${params.stochPeriod})`
      case 'ADX':
      case 'ATR':
      case 'CCI':
      case 'ROC':
      case 'WILLR':
      case 'MFI':
        return `${baseName} (${params.period})`
      case 'AO':
        return `${baseName} (${params.fastPeriod},${params.slowPeriod})`
      case 'KST':
        return `${baseName} (${params.roc1},${params.roc2},${params.roc3},${params.roc4})`
      case 'TRIX':
        return `${baseName} (${params.period})`
      default:
        return baseName
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.type, paramsKey])

  // Valor atual
  const currentValue = useMemo(() => {
    if (!indicatorResult?.values?.length) return null
    const lastValue = indicatorResult.values[indicatorResult.values.length - 1]
    if (isNaN(lastValue) || lastValue === null) return null
    return lastValue
  }, [indicatorResult])

  // Inicializar gráfico
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: height - 28, // Subtrair altura do header
      layout: {
        background: { type: 'solid', color: theme === 'dark' ? '#131722' : '#ffffff' },
        textColor: theme === 'dark' ? '#787b86' : '#333333'
      },
      grid: {
        vertLines: { color: theme === 'dark' ? '#1e222d' : '#e1e3eb' },
        horzLines: { color: theme === 'dark' ? '#1e222d' : '#e1e3eb' }
      },
      rightPriceScale: {
        borderColor: theme === 'dark' ? '#2a2e39' : '#e1e3eb',
        scaleMargins: { top: 0.1, bottom: 0.1 }
      },
      timeScale: {
        borderColor: theme === 'dark' ? '#2a2e39' : '#e1e3eb',
        visible: true,
        timeVisible: true,
        secondsVisible: false
      },
      crosshair: {
        mode: 1,
        vertLine: { color: '#4c525e', width: 1, style: 2 },
        horzLine: { color: '#4c525e', width: 1, style: 2 }
      }
    })

    chartRef.current = chart

    // Resize observer
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
      seriesRefs.current.clear()
    }
  }, [height, theme])

  // Atualizar tema
  useEffect(() => {
    if (!chartRef.current) return

    chartRef.current.applyOptions({
      layout: {
        background: { type: 'solid', color: theme === 'dark' ? '#131722' : '#ffffff' },
        textColor: theme === 'dark' ? '#787b86' : '#333333'
      },
      grid: {
        vertLines: { color: theme === 'dark' ? '#1e222d' : '#e1e3eb' },
        horzLines: { color: theme === 'dark' ? '#1e222d' : '#e1e3eb' }
      },
      rightPriceScale: {
        borderColor: theme === 'dark' ? '#2a2e39' : '#e1e3eb'
      },
      timeScale: {
        borderColor: theme === 'dark' ? '#2a2e39' : '#e1e3eb'
      }
    })
  }, [theme])

  // Atualizar dados do indicador
  useEffect(() => {
    console.log(`📊 [${config.type}] useEffect ATUALIZANDO GRÁFICO:`, {
      hasChart: !!chartRef.current,
      hasIndicatorResult: !!indicatorResult,
      candlesLength: candles.length,
      color: config.color,
      lineWidth: config.lineWidth
    })

    if (!chartRef.current || !indicatorResult || !candles.length) return

    const chart = chartRef.current

    // Limpar séries existentes
    seriesRefs.current.forEach(series => {
      try {
        chart.removeSeries(series)
      } catch (e) {}
    })
    seriesRefs.current.clear()

    // Adicionar série principal
    const mainData: LineData<Time>[] = indicatorResult.values
      .map((value, idx) => ({
        time: candles[idx].time as Time,
        value: value
      }))
      .filter(d => !isNaN(d.value) && d.value !== null)

    if (mainData.length > 0) {
      // Para MACD histogram, usar HistogramSeries
      if (config.type === 'MACD' && indicatorResult.additionalLines?.histogram) {
        // MACD Line
        const macdSeries = chart.addLineSeries({
          color: config.color || INDICATOR_PRESETS[config.type]?.color || '#4CAF50',
          lineWidth: config.lineWidth || 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: 'MACD'
        })
        macdSeries.setData(mainData)
        seriesRefs.current.set('main', macdSeries)

        // Signal Line
        const signalData: LineData<Time>[] = indicatorResult.additionalLines.signal
          .map((value, idx) => ({
            time: candles[idx].time as Time,
            value: value
          }))
          .filter(d => !isNaN(d.value) && d.value !== null)

        const signalSeries = chart.addLineSeries({
          color: '#FF6B6B',
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
          title: 'Signal'
        })
        signalSeries.setData(signalData)
        seriesRefs.current.set('signal', signalSeries)

        // Histogram
        const histogramData: HistogramData<Time>[] = indicatorResult.additionalLines.histogram
          .map((value, idx) => ({
            time: candles[idx].time as Time,
            value: value,
            color: value >= 0 ? '#26A69A' : '#EF5350'
          }))
          .filter(d => !isNaN(d.value) && d.value !== null)

        const histogramSeries = chart.addHistogramSeries({
          priceLineVisible: false,
          lastValueVisible: false,
          title: 'Histogram'
        })
        histogramSeries.setData(histogramData)
        seriesRefs.current.set('histogram', histogramSeries)
      }
      // Para AO (Awesome Oscillator), também usar histogram
      else if (config.type === 'AO') {
        const histogramData: HistogramData<Time>[] = indicatorResult.values
          .map((value, idx) => ({
            time: candles[idx].time as Time,
            value: value,
            color: value >= 0 ? '#26A69A' : '#EF5350'
          }))
          .filter(d => !isNaN(d.value) && d.value !== null)

        const histogramSeries = chart.addHistogramSeries({
          priceLineVisible: false,
          lastValueVisible: true,
          title: 'AO'
        })
        histogramSeries.setData(histogramData)
        seriesRefs.current.set('main', histogramSeries)
      }
      // Para outros indicadores, usar LineSeries
      else {
        const mainSeries = chart.addLineSeries({
          color: config.color || INDICATOR_PRESETS[config.type]?.color || '#2196F3',
          lineWidth: config.lineWidth || 2,
          priceLineVisible: false,
          lastValueVisible: true,
          title: config.type
        })
        mainSeries.setData(mainData)
        seriesRefs.current.set('main', mainSeries)

        // Linhas adicionais (exceto MACD que já foi tratado)
        if (indicatorResult.additionalLines && config.type !== 'MACD') {
          Object.entries(indicatorResult.additionalLines).forEach(([key, values]) => {
            if (key === 'histogram') return // Histogram tratado separadamente

            const additionalData: LineData<Time>[] = values
              .map((value, idx) => ({
                time: candles[idx].time as Time,
                value: value
              }))
              .filter(d => !isNaN(d.value) && d.value !== null)

            if (additionalData.length > 0) {
              const lineStyle = (key === 'overbought' || key === 'oversold' || key === 'upper' || key === 'lower') ? 2 : 0

              const additionalSeries = chart.addLineSeries({
                color: ADDITIONAL_LINE_COLORS[key] || '#888888',
                lineWidth: 1,
                lineStyle,
                priceLineVisible: false,
                lastValueVisible: false,
                title: key
              })
              additionalSeries.setData(additionalData)
              seriesRefs.current.set(key, additionalSeries)
            }
          })
        }
      }
    }

    // Fit content
    chart.timeScale().fitContent()
  }, [indicatorResult, candles, config.type, config.color, config.lineWidth, config.params])

  // Sincronizar timeScale com gráfico principal
  useEffect(() => {
    if (!chartRef.current || !timeScaleSync) return

    // Sincronizar scroll do tempo
    const handleTimeRangeChange = () => {
      const mainTimeScale = timeScaleSync.timeScale()
      const panelTimeScale = chartRef.current?.timeScale()

      if (mainTimeScale && panelTimeScale) {
        const visibleRange = mainTimeScale.getVisibleRange()
        if (visibleRange) {
          panelTimeScale.setVisibleRange(visibleRange)
        }
      }
    }

    const subscription = timeScaleSync.timeScale().subscribeVisibleTimeRangeChange(handleTimeRangeChange)

    return () => {
      subscription
    }
  }, [timeScaleSync])

  return (
    <div className={`bg-[#131722] border-t border-[#2a2e39] ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1 bg-[#1e222d] border-b border-[#2a2e39]">
        <div className="flex items-center gap-2">
          {/* Drag handle */}
          <GripHorizontal className="w-3 h-3 text-gray-500 cursor-grab" />

          {/* Color indicator */}
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: config.color || INDICATOR_PRESETS[config.type]?.color }}
          />

          {/* Title with params */}
          <span className="text-xs font-medium text-gray-300">
            {panelTitle}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Current value */}
          {currentValue !== null && (
            <span className="text-xs font-mono text-gray-400">
              {currentValue.toFixed(2)}
            </span>
          )}

          {/* Settings button */}
          {onSettings && (
            <button
              onClick={onSettings}
              className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
              title="Configurar indicador"
            >
              <Settings className="w-3 h-3" />
            </button>
          )}

          {/* Remove button */}
          {onRemove && (
            <button
              onClick={onRemove}
              className="p-1 text-gray-500 hover:text-red-400 transition-colors"
              title="Remover indicador"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Chart Container */}
      <div ref={containerRef} style={{ height: height - 28 }} />
    </div>
  )
}

export default SeparateIndicatorPanel
