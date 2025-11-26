import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { createChart } from 'lightweight-charts'
import type { ChartPosition } from '@/hooks/useChartPositions'

interface DraggableLine {
  id: string
  positionId: string
  type: 'stopLoss' | 'takeProfit'
  price: number
  color: string
  y: number
}

interface CustomChartProps {
  symbol: string
  interval: string
  theme?: 'light' | 'dark'
  width?: string | number
  height?: string | number
  positions?: ChartPosition[]
  onReady?: () => void
  className?: string
  indicators?: {
    ema9?: boolean
    ema20?: boolean
    ema50?: boolean
    sma20?: boolean
    sma50?: boolean
    sma200?: boolean
    bollingerBands?: boolean
    rsi?: boolean
    macd?: boolean
    stochastic?: boolean
    atr?: boolean
    volume?: boolean
  }
  onChartClick?: (price: number) => void
  onPositionClose?: (positionId: string) => void
  onPositionEdit?: (positionId: string) => void
  onSLTPDrag?: (positionId: string, type: 'stopLoss' | 'takeProfit', newPrice: number) => void
}

interface CandleData {
  time: number
  open: number
  high: number
  low: number
  close: number
}

const CustomChartComponent: React.FC<CustomChartProps> = ({
  symbol,
  interval,
  theme = 'dark',
  width = '100%',
  height = 500,
  positions = [],
  onReady,
  className = '',
  indicators = {},
  onChartClick,
  onPositionClose,
  onPositionEdit,
  onSLTPDrag
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const candlestickSeriesRef = useRef<any>(null)
  const volumeSeriesRef = useRef<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const priceLineIdsRef = useRef<any[]>([])
  const [draggableLines, setDraggableLines] = useState<DraggableLine[]>([])
  const [draggedLine, setDraggedLine] = useState<string | null>(null)
  const dragStartY = useRef<number>(0)
  const draggableLinesRef = useRef<DraggableLine[]>([])

  // 🚀 PERFORMANCE: Cache candles data in memory to avoid re-fetching
  const candlesDataRef = useRef<CandleData[] | null>(null)
  const candlesCacheKey = useRef<string>('')

  // Refs para indicadores
  const ema9SeriesRef = useRef<any>(null)
  const ema20SeriesRef = useRef<any>(null)
  const ema50SeriesRef = useRef<any>(null)
  const sma20SeriesRef = useRef<any>(null)
  const sma50SeriesRef = useRef<any>(null)
  const sma200SeriesRef = useRef<any>(null)
  const upperBandRef = useRef<any>(null)
  const lowerBandRef = useRef<any>(null)
  const middleBandRef = useRef<any>(null)

  // Mapear interval do frontend para Binance API
  const mapIntervalToBinance = (interval: string): string => {
    const mapping: Record<string, string> = {
      '1': '1m',
      '3': '3m',
      '5': '5m',
      '15': '15m',
      '30': '30m',
      '60': '1h',
      '240': '4h',
      '1D': '1d',
      '1W': '1w',   // ✅ NOVO: Semanal
      '1M': '1M'    // ✅ NOVO: Mensal
    }
    return mapping[interval] || '1h'
  }

  // 📅 Limite dinâmico baseado no timeframe para histórico inteligente
  const getOptimalLimit = (interval: string): number => {
    const limits: Record<string, number> = {
      '1': 500,      // 1m = ~8 horas
      '3': 500,      // 3m = ~1 dia
      '5': 500,      // 5m = ~1.7 dias
      '15': 672,     // 15m = ~7 dias (1 semana)
      '30': 720,     // 30m = ~15 dias
      '60': 720,     // 1h = ~30 dias (1 mês)
      '240': 720,    // 4h = ~120 dias (4 meses)
      '1D': 730,     // 1D = ~2 anos ✅
      '1W': 520,     // 1W = ~10 anos ✅
      '1M': 120      // 1M = ~10 anos ✅
    }
    return limits[interval] || 500
  }

  // 🚀 PERFORMANCE: Memoize EMA calculation to avoid recalculation
  const calculateEMA = useCallback((data: CandleData[], period: number) => {
    const k = 2 / (period + 1)
    const emaData: { time: number; value: number }[] = []
    let ema = data[0].close

    data.forEach((candle, index) => {
      if (index === 0) {
        ema = candle.close
      } else {
        ema = candle.close * k + ema * (1 - k)
      }
      emaData.push({ time: candle.time, value: ema })
    })

    return emaData
  }, [])

  // 🚀 PERFORMANCE: Memoize SMA calculation to avoid recalculation
  const calculateSMA = useCallback((data: CandleData[], period: number) => {
    const smaData: { time: number; value: number }[] = []

    for (let i = period - 1; i < data.length; i++) {
      const sum = data.slice(i - period + 1, i + 1).reduce((acc, candle) => acc + candle.close, 0)
      smaData.push({ time: data[i].time, value: sum / period })
    }

    return smaData
  }, [])

  // 🚀 PERFORMANCE: Memoize Bollinger Bands calculation to avoid recalculation
  const calculateBollingerBands = useCallback((data: CandleData[], period: number, stdDev: number) => {
    const sma = calculateSMA(data, period)
    const upper: { time: number; value: number }[] = []
    const lower: { time: number; value: number }[] = []

    sma.forEach((smaPoint, index) => {
      const dataIndex = index + period - 1
      const slice = data.slice(dataIndex - period + 1, dataIndex + 1)
      const variance = slice.reduce((acc, candle) => acc + Math.pow(candle.close - smaPoint.value, 2), 0) / period
      const std = Math.sqrt(variance)

      upper.push({ time: smaPoint.time, value: smaPoint.value + std * stdDev })
      lower.push({ time: smaPoint.time, value: smaPoint.value - std * stdDev })
    })

    return { upper, lower, middle: sma }
  }, [calculateSMA])

  // Inicializar gráfico
  useEffect(() => {
    if (!chartContainerRef.current) return

    console.log('📊 CustomChart: Inicializando gráfico', { symbol, interval, theme })

    // Calcular dimensões do container
    const containerWidth = chartContainerRef.current.clientWidth || 800
    const containerHeight = chartContainerRef.current.clientHeight || 500

    // Criar gráfico com v4 API
    const chart = createChart(chartContainerRef.current, {
      width: typeof width === 'number' ? width : containerWidth,
      height: typeof height === 'number' ? height : containerHeight,
      layout: {
        background: { type: 'solid' as const, color: theme === 'dark' ? '#1e1e1e' : '#ffffff' },
        textColor: theme === 'dark' ? '#d1d4dc' : '#191919',
      },
      grid: {
        vertLines: { color: theme === 'dark' ? '#2b2b43' : '#e1e3eb' },
        horzLines: { color: theme === 'dark' ? '#2b2b43' : '#e1e3eb' },
      },
      rightPriceScale: {
        borderColor: theme === 'dark' ? '#2b2b43' : '#e1e3eb',
      },
      timeScale: {
        borderColor: theme === 'dark' ? '#2b2b43' : '#e1e3eb',
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 0,
      },
    })

    chartRef.current = chart

    console.log('🔍 Chart object:', chart)
    console.log('🔍 Chart methods:', Object.keys(chart))
    console.log('🔍 Has addCandlestickSeries?', typeof chart.addCandlestickSeries)

    // Adicionar série de candles - v4 API
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderVisible: false,
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
    })

    candlestickSeriesRef.current = candlestickSeries

    // Adicionar série de volume em um overlay separado (abaixo dos candles)
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // Escala própria
      lastValueVisible: false, // Não mostrar último valor
      priceLineVisible: false, // Não mostrar linha de preço
    })

    // Configurar height do volume para 20% do gráfico (80% candles, 20% volume)
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8, // Volume começa em 80% da altura
        bottom: 0,
      },
    })

    volumeSeriesRef.current = volumeSeries

    // 🚀 PERFORMANCE: Use ResizeObserver for better performance than window resize
    const resizeObserver = new ResizeObserver(entries => {
      if (!chartContainerRef.current || !chart) return

      const { width, height } = entries[0].contentRect
      console.log('📐 Container resized:', { width, height })

      chart.applyOptions({
        width: width || chartContainerRef.current.clientWidth,
        height: height || chartContainerRef.current.clientHeight
      })
    })

    if (chartContainerRef.current.parentElement) {
      resizeObserver.observe(chartContainerRef.current.parentElement)
    }

    // Handle chart clicks - apenas para criar ordem
    if (onChartClick) {
      chart.subscribeClick((param: any) => {
        if (param.point && param.seriesData && param.seriesData.size > 0) {
          const price = param.seriesData.get(candlestickSeries)?.close
          if (price && typeof price === 'number') {
            console.log('📍 Chart clicked at price:', price)
            onChartClick(price)
          }
        }
      })
    }

    console.log('✅ CustomChart: Gráfico criado com sucesso')

    // Cleanup
    return () => {
      resizeObserver.disconnect()
      chart.remove()
      console.log('🧹 CustomChart: Gráfico removido')
    }
  }, [theme, width, height, onChartClick])

  // Buscar dados de candles da API
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return

    const fetchCandles = async () => {
      // 🚀 PERFORMANCE: Check if we already have data for this symbol+interval
      const newCacheKey = `${symbol}:${interval}`
      if (candlesCacheKey.current === newCacheKey && candlesDataRef.current) {
        console.log('✅ Using CACHED candles data:', newCacheKey)
        setIsLoading(false)
        return // No need to fetch, data already loaded
      }

      setIsLoading(true)
      setError(null)

      try {
        // 🚀 PERFORMANCE: Logs commented out to reduce overhead
        // console.log('📥 Fetching fresh candles:', { symbol, interval })

        const binanceInterval = mapIntervalToBinance(interval)
        const optimalLimit = getOptimalLimit(interval)

        // 🚀 PERFORMANCE: Limite dinâmico baseado no timeframe (optimized with cache)
        // 1m/5m = 500 candles | 1h = 720 | 1D = 730 (2 anos) | 1W = 520 (10 anos)
        const response = await fetch(
          `http://localhost:8000/api/v1/market/candles?symbol=${symbol}&interval=${binanceInterval}&limit=${optimalLimit}`
        )

        const data = await response.json()

        if (!response.ok) {
          // Extrair mensagem de erro detalhada
          const errorMsg = data.detail || `HTTP error! status: ${response.status}`

          // Verificar se é símbolo inválido
          if (errorMsg.includes('Invalid symbol') || errorMsg.includes('-1121')) {
            throw new Error(`O símbolo ${symbol} não está disponível para gráficos na Binance. Este ativo pode não suportar dados históricos de candles.`)
          }

          throw new Error(errorMsg)
        }

        if (!data.success) {
          throw new Error(data.error || 'Failed to fetch candles')
        }

        console.log('✅ Candles recebidos:', data.count, 'candles')

        // Formatar dados para Lightweight Charts v4
        const candleData: CandleData[] = data.candles.map((candle: any) => ({
          time: candle.time,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        }))

        const volumeData = data.candles.map((candle: any) => ({
          time: candle.time,
          value: candle.volume,
          color: candle.close >= candle.open ? '#10B98180' : '#EF444480',
        }))

        // 🚀 PERFORMANCE: Cache the data for future use
        candlesDataRef.current = candleData
        candlesCacheKey.current = `${symbol}:${interval}`

        // Atualizar séries
        if (candlestickSeriesRef.current && volumeSeriesRef.current) {
          candlestickSeriesRef.current.setData(candleData)
          volumeSeriesRef.current.setData(volumeData)

          // Adicionar indicadores se solicitados
          if (indicators.ema9 && chartRef.current) {
            if (!ema9SeriesRef.current) {
              ema9SeriesRef.current = chartRef.current.addLineSeries({
                color: '#2196F3',
                lineWidth: 2,
                title: 'EMA (9)',
              })
            }
            const emaData = calculateEMA(candleData, 9)
            ema9SeriesRef.current.setData(emaData)
            console.log('📊 EMA (9) adicionado')
          }

          if (indicators.ema20 && chartRef.current) {
            if (!ema20SeriesRef.current) {
              ema20SeriesRef.current = chartRef.current.addLineSeries({
                color: '#2962FF',
                lineWidth: 2,
                title: 'EMA (20)',
              })
            }
            const emaData = calculateEMA(candleData, 20)
            ema20SeriesRef.current.setData(emaData)
            console.log('📊 EMA (20) adicionado')
          }

          if (indicators.ema50 && chartRef.current) {
            if (!ema50SeriesRef.current) {
              ema50SeriesRef.current = chartRef.current.addLineSeries({
                color: '#1565C0',
                lineWidth: 2,
                title: 'EMA (50)',
              })
            }
            const emaData = calculateEMA(candleData, 50)
            ema50SeriesRef.current.setData(emaData)
            console.log('📊 EMA (50) adicionado')
          }

          if (indicators.sma20 && chartRef.current) {
            if (!sma20SeriesRef.current) {
              sma20SeriesRef.current = chartRef.current.addLineSeries({
                color: '#FF9800',
                lineWidth: 2,
                title: 'SMA (20)',
              })
            }
            const smaData = calculateSMA(candleData, 20)
            sma20SeriesRef.current.setData(smaData)
            console.log('📊 SMA (20) adicionado')
          }

          if (indicators.sma50 && chartRef.current) {
            if (!sma50SeriesRef.current) {
              sma50SeriesRef.current = chartRef.current.addLineSeries({
                color: '#FF6D00',
                lineWidth: 2,
                title: 'SMA (50)',
              })
            }
            const smaData = calculateSMA(candleData, 50)
            sma50SeriesRef.current.setData(smaData)
            console.log('📊 SMA (50) adicionado')
          }

          if (indicators.sma200 && chartRef.current) {
            if (!sma200SeriesRef.current) {
              sma200SeriesRef.current = chartRef.current.addLineSeries({
                color: '#E65100',
                lineWidth: 2,
                title: 'SMA (200)',
              })
            }
            const smaData = calculateSMA(candleData, 200)
            sma200SeriesRef.current.setData(smaData)
            console.log('📊 SMA (200) adicionado')
          }

          if (indicators.bollingerBands && chartRef.current) {
            const bbData = calculateBollingerBands(candleData, 20, 2)

            if (!upperBandRef.current) {
              upperBandRef.current = chartRef.current.addLineSeries({
                color: '#9E9E9E',
                lineWidth: 1,
                lineStyle: 2, // Dashed
                title: 'BB Upper',
              })
            }

            if (!middleBandRef.current) {
              middleBandRef.current = chartRef.current.addLineSeries({
                color: '#9E9E9E',
                lineWidth: 1,
                title: 'BB Middle',
              })
            }

            if (!lowerBandRef.current) {
              lowerBandRef.current = chartRef.current.addLineSeries({
                color: '#9E9E9E',
                lineWidth: 1,
                lineStyle: 2, // Dashed
                title: 'BB Lower',
              })
            }

            upperBandRef.current.setData(bbData.upper)
            middleBandRef.current.setData(bbData.middle)
            lowerBandRef.current.setData(bbData.lower)
            console.log('📊 Bollinger Bands adicionado')
          }

          // Ajustar visualização
          if (chartRef.current) {
            chartRef.current.timeScale().fitContent()
          }

          console.log('✅ Dados aplicados ao gráfico')
        }

        setIsLoading(false)
        if (onReady) onReady()

      } catch (err) {
        console.error('❌ Erro ao buscar candles:', err)
        setError(err instanceof Error ? err.message : 'Unknown error')
        setIsLoading(false)
      }
    }

    fetchCandles()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval])

  // Desenhar posições no gráfico
  useEffect(() => {
    if (!candlestickSeriesRef.current || !positions || positions.length === 0) {
      console.log('⚠️ Sem posições para desenhar ou série não disponível')
      return
    }

    console.log('🎨 Desenhando', positions.length, 'posições no gráfico')

    // Limpar linhas antigas
    priceLineIdsRef.current.forEach(priceLine => {
      try {
        candlestickSeriesRef.current?.removePriceLine(priceLine)
      } catch (e) {
        console.warn('Erro ao remover price line:', e)
      }
    })
    priceLineIdsRef.current = []

    // Array para linhas draggable
    const newDraggableLines: DraggableLine[] = []

    // Desenhar novas linhas para cada posição
    positions.forEach((position, idx) => {
      console.log(`📍 Desenhando posição ${idx + 1}:`, {
        symbol: position.symbol,
        side: position.side,
        entryPrice: position.entryPrice,
        quantity: position.quantity
      })

      try {
        const color = position.side === 'LONG' ? '#10B981' : '#EF4444'
        const title = `${position.side} ${position.quantity} @ $${position.entryPrice.toFixed(2)}`

        // Linha de entrada
        const priceLine = candlestickSeriesRef.current!.createPriceLine({
          price: position.entryPrice,
          color: color,
          lineWidth: 2,
          lineStyle: 0,
          axisLabelVisible: true,
          title: title,
        })
        priceLineIdsRef.current.push(priceLine)

        // Linha de Stop Loss (vermelha tracejada) - DRAGGABLE
        if (position.stopLoss && position.stopLoss > 0 && candlestickSeriesRef.current) {
          const slLine = candlestickSeriesRef.current.createPriceLine({
            price: position.stopLoss,
            color: '#EF4444',
            lineWidth: 2,
            lineStyle: 2, // Tracejada
            axisLabelVisible: true,
            title: `SL $${position.stopLoss.toFixed(2)} (arraste para ajustar)`,
          })
          priceLineIdsRef.current.push(slLine)

          // Converter preço para coordenada Y
          const yCoord = candlestickSeriesRef.current.priceToCoordinate(position.stopLoss)
          if (yCoord !== null) {
            newDraggableLines.push({
              id: `sl-${position.id}`,
              positionId: position.id,
              type: 'stopLoss',
              price: position.stopLoss,
              color: '#EF4444',
              y: yCoord
            })
          }

          console.log(`  ✅ Stop Loss desenhado: $${position.stopLoss.toFixed(2)}`)
        }

        // Linha de Take Profit (verde tracejada) - DRAGGABLE
        if (position.takeProfit && position.takeProfit > 0 && candlestickSeriesRef.current) {
          const tpLine = candlestickSeriesRef.current.createPriceLine({
            price: position.takeProfit,
            color: '#10B981',
            lineWidth: 2,
            lineStyle: 2, // Tracejada
            axisLabelVisible: true,
            title: `TP $${position.takeProfit.toFixed(2)} (arraste para ajustar)`,
          })
          priceLineIdsRef.current.push(tpLine)

          // Converter preço para coordenada Y
          const yCoord = candlestickSeriesRef.current.priceToCoordinate(position.takeProfit)
          if (yCoord !== null) {
            newDraggableLines.push({
              id: `tp-${position.id}`,
              positionId: position.id,
              type: 'takeProfit',
              price: position.takeProfit,
              color: '#10B981',
              y: yCoord
            })
          }

          console.log(`  ✅ Take Profit desenhado: $${position.takeProfit.toFixed(2)}`)
        }

        // Múltiplos Take Profits adicionais - DRAGGABLE
        if (position.allTakeProfits && position.allTakeProfits.length > 1 && candlestickSeriesRef.current) {
          position.allTakeProfits.forEach((tp, tpIdx) => {
            if (tp !== position.takeProfit) { // Pular o principal já desenhado
              const tpLine = candlestickSeriesRef.current!.createPriceLine({
                price: tp,
                color: '#22C55E',
                lineWidth: 1,
                lineStyle: 3, // Pontilhada
                axisLabelVisible: true,
                title: `TP${tpIdx + 1} $${tp.toFixed(2)} (arraste para ajustar)`,
              })
              priceLineIdsRef.current.push(tpLine)

              // Converter preço para coordenada Y
              const yCoord = candlestickSeriesRef.current!.priceToCoordinate(tp)
              if (yCoord !== null) {
                newDraggableLines.push({
                  id: `tp${tpIdx}-${position.id}`,
                  positionId: position.id,
                  type: 'takeProfit',
                  price: tp,
                  color: '#22C55E',
                  y: yCoord
                })
              }

              console.log(`  ✅ Take Profit ${tpIdx + 1} desenhado: $${tp.toFixed(2)}`)
            }
          })
        }

        console.log(`✅ Posição ${idx + 1} desenhada com sucesso`)

      } catch (err) {
        console.error(`❌ Erro ao desenhar posição ${idx + 1}:`, err)
      }
    })

    // Atualizar state com linhas draggable
    // 🚀 PERFORMANCE: Logs commented out to reduce overhead
    // console.log(`🎯 Total de linhas draggable criadas: ${newDraggableLines.length}`)
    // newDraggableLines.forEach((line, idx) => {
    //   console.log(`   ${idx + 1}. ${line.type} @ $${line.price.toFixed(2)} (y=${line.y.toFixed(1)})`)
    // })
    setDraggableLines(newDraggableLines)

  }, [positions])

  // useEffect para monitorar estado de linhas draggable
  // 🚀 PERFORMANCE: useEffect commented out to reduce overhead
  // useEffect(() => {
  //   console.log(`🔄 Estado draggableLines atualizado: ${draggableLines.length} linhas`)
  //   draggableLines.forEach((line, idx) => {
  //     console.log(`   ${idx + 1}. [${line.id}] ${line.type} @ $${line.price.toFixed(2)} (y=${line.y.toFixed(1)})`)
  //   })
  // }, [draggableLines])

  // Sincronizar ref com state
  useEffect(() => {
    draggableLinesRef.current = draggableLines
  }, [draggableLines])

  // useEffect para atualizar coordenadas Y das linhas quando o gráfico muda (zoom/pan)
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return

    console.log('📍 Configurando listeners para atualização de coordenadas')

    const updateLineCoordinates = () => {
      if (!candlestickSeriesRef.current || draggableLinesRef.current.length === 0) return

      const updatedLines = draggableLinesRef.current.map(line => {
        const newY = candlestickSeriesRef.current!.priceToCoordinate(line.price)
        if (newY !== null && Math.abs(newY - line.y) > 1) { // Atualizar se diferença > 1px
          console.log(`📍 Atualizando Y de ${line.type} de ${line.y.toFixed(1)} para ${newY.toFixed(1)}`)
          return { ...line, y: newY }
        }
        return line
      })

      setDraggableLines(updatedLines)
    }

    // Atualizar coordenadas quando o gráfico é redimensionado ou movido
    const timeScale = chartRef.current.timeScale()
    timeScale.subscribeVisibleLogicalRangeChange(updateLineCoordinates)

    // 🚀 PERFORMANCE: Reduce interval frequency from 1s to 2s to minimize overhead
    const intervalId = setInterval(updateLineCoordinates, 2000)

    return () => {
      console.log('🗑️ Removendo listeners de atualização de coordenadas')
      timeScale.unsubscribeVisibleLogicalRangeChange(updateLineCoordinates)
      clearInterval(intervalId)
    }
  }, []) // Executar apenas uma vez na montagem

  // useEffect para gerenciar drag global
  useEffect(() => {
    if (!draggedLine) return

    const handleGlobalMouseMove = (e: MouseEvent) => {
      if (!chartContainerRef.current || !draggedLine) return

      const rect = chartContainerRef.current.getBoundingClientRect()
      const newY = e.clientY - rect.top

      setDraggableLines(prev =>
        prev.map(l => l.id === draggedLine ? { ...l, y: newY } : l)
      )
    }

    const handleGlobalMouseUp = () => {
      console.log('🖱️ MouseUp disparado', {
        draggedLine,
        hasCandlestickSeries: !!candlestickSeriesRef.current,
        hasOnSLTPDrag: !!onSLTPDrag
      })

      if (!draggedLine) {
        console.log('⚠️ Nenhuma linha sendo arrastada')
        return
      }

      if (!candlestickSeriesRef.current) {
        console.log('❌ candlestickSeriesRef não disponível')
        setDraggedLine(null)
        return
      }

      if (!onSLTPDrag) {
        console.log('❌ onSLTPDrag callback não fornecido')
        setDraggedLine(null)
        return
      }

      // Encontrar a linha arrastada
      const line = draggableLines.find(l => l.id === draggedLine)
      console.log('🔍 Linha encontrada:', line)

      if (line) {
        // Converter coordenada Y de volta para preço
        const newPrice = candlestickSeriesRef.current.coordinateToPrice(line.y)
        console.log('💰 Novo preço calculado:', newPrice)

        if (newPrice) {
          console.log(`🎯 Linha ${line.type} arrastada para $${newPrice.toFixed(2)} - Chamando API...`)
          onSLTPDrag(line.positionId, line.type, newPrice)
        } else {
          console.log('❌ Não foi possível converter Y para preço')
        }
      } else {
        console.log('❌ Linha não encontrada no array draggableLines')
      }

      setDraggedLine(null)
    }

    document.addEventListener('mousemove', handleGlobalMouseMove)
    document.addEventListener('mouseup', handleGlobalMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleGlobalMouseMove)
      document.removeEventListener('mouseup', handleGlobalMouseUp)
    }
  }, [draggedLine, draggableLines, onSLTPDrag])

  // 🔥 FIX CRÍTICO: useEffect para reagir às mudanças de indicadores em tempo real
  // IMPORTANTE: Removido symbol e interval das dependências para evitar race condition
  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return

    const updateIndicators = () => {
      try {
        // 🚀 RETRY LOGIC: Esperar dados estarem disponíveis
        if (!candlesDataRef.current || candlesDataRef.current.length === 0) {
          console.log('⏳ Aguardando candles carregarem para aplicar indicadores...')

          // ✅ Retry após 100ms (dados podem estar carregando)
          setTimeout(() => {
            if (candlesDataRef.current && candlesDataRef.current.length > 0) {
              console.log('✅ Candles carregados! Re-tentando aplicar indicadores...')
              updateIndicators()  // Tentar novamente
            }
          }, 100)

          return
        }

        const candleData = candlesDataRef.current
        console.log('📊 Aplicando indicadores INSTANTANEAMENTE com', candleData.length, 'candles')

        // EMA 9
        if (indicators.ema9) {
          if (!ema9SeriesRef.current && chartRef.current) {
            ema9SeriesRef.current = chartRef.current.addLineSeries({
              color: '#2196F3',
              lineWidth: 2,
              title: 'EMA (9)',
            })
          }
          if (ema9SeriesRef.current) {
            const emaData = calculateEMA(candleData, 9)
            ema9SeriesRef.current.setData(emaData)
            console.log('✅ EMA (9) ativado')
          }
        } else if (ema9SeriesRef.current && chartRef.current) {
          chartRef.current.removeSeries(ema9SeriesRef.current)
          ema9SeriesRef.current = null
          console.log('❌ EMA (9) desativado')
        }

        // EMA 20
        if (indicators.ema20) {
          if (!ema20SeriesRef.current && chartRef.current) {
            ema20SeriesRef.current = chartRef.current.addLineSeries({
              color: '#2962FF',
              lineWidth: 2,
              title: 'EMA (20)',
            })
          }
          if (ema20SeriesRef.current) {
            const emaData = calculateEMA(candleData, 20)
            ema20SeriesRef.current.setData(emaData)
            console.log('✅ EMA (20) ativado')
          }
        } else if (ema20SeriesRef.current && chartRef.current) {
          chartRef.current.removeSeries(ema20SeriesRef.current)
          ema20SeriesRef.current = null
          console.log('❌ EMA (20) desativado')
        }

        // EMA 50
        if (indicators.ema50) {
          if (!ema50SeriesRef.current && chartRef.current) {
            ema50SeriesRef.current = chartRef.current.addLineSeries({
              color: '#1565C0',
              lineWidth: 2,
              title: 'EMA (50)',
            })
          }
          if (ema50SeriesRef.current) {
            const emaData = calculateEMA(candleData, 50)
            ema50SeriesRef.current.setData(emaData)
            console.log('✅ EMA (50) ativado')
          }
        } else if (ema50SeriesRef.current && chartRef.current) {
          chartRef.current.removeSeries(ema50SeriesRef.current)
          ema50SeriesRef.current = null
          console.log('❌ EMA (50) desativado')
        }

        // SMA 20
        if (indicators.sma20) {
          if (!sma20SeriesRef.current && chartRef.current) {
            sma20SeriesRef.current = chartRef.current.addLineSeries({
              color: '#FF9800',
              lineWidth: 2,
              title: 'SMA (20)',
            })
          }
          if (sma20SeriesRef.current) {
            const smaData = calculateSMA(candleData, 20)
            sma20SeriesRef.current.setData(smaData)
            console.log('✅ SMA (20) ativado')
          }
        } else if (sma20SeriesRef.current && chartRef.current) {
          chartRef.current.removeSeries(sma20SeriesRef.current)
          sma20SeriesRef.current = null
          console.log('❌ SMA (20) desativado')
        }

        // SMA 50
        if (indicators.sma50) {
          if (!sma50SeriesRef.current && chartRef.current) {
            sma50SeriesRef.current = chartRef.current.addLineSeries({
              color: '#FF6D00',
              lineWidth: 2,
              title: 'SMA (50)',
            })
          }
          if (sma50SeriesRef.current) {
            const smaData = calculateSMA(candleData, 50)
            sma50SeriesRef.current.setData(smaData)
            console.log('✅ SMA (50) ativado')
          }
        } else if (sma50SeriesRef.current && chartRef.current) {
          chartRef.current.removeSeries(sma50SeriesRef.current)
          sma50SeriesRef.current = null
          console.log('❌ SMA (50) desativado')
        }

        // SMA 200
        if (indicators.sma200) {
          if (!sma200SeriesRef.current && chartRef.current) {
            sma200SeriesRef.current = chartRef.current.addLineSeries({
              color: '#E65100',
              lineWidth: 2,
              title: 'SMA (200)',
            })
          }
          if (sma200SeriesRef.current) {
            const smaData = calculateSMA(candleData, 200)
            sma200SeriesRef.current.setData(smaData)
            console.log('✅ SMA (200) ativado')
          }
        } else if (sma200SeriesRef.current && chartRef.current) {
          chartRef.current.removeSeries(sma200SeriesRef.current)
          sma200SeriesRef.current = null
          console.log('❌ SMA (200) desativado')
        }

        // Bollinger Bands
        if (indicators.bollingerBands) {
          const bbData = calculateBollingerBands(candleData, 20, 2)

          if (!upperBandRef.current && chartRef.current) {
            upperBandRef.current = chartRef.current.addLineSeries({
              color: '#9E9E9E',
              lineWidth: 1,
              lineStyle: 2,
              title: 'BB Upper',
            })
          }

          if (!middleBandRef.current && chartRef.current) {
            middleBandRef.current = chartRef.current.addLineSeries({
              color: '#9E9E9E',
              lineWidth: 1,
              title: 'BB Middle',
            })
          }

          if (!lowerBandRef.current && chartRef.current) {
            lowerBandRef.current = chartRef.current.addLineSeries({
              color: '#9E9E9E',
              lineWidth: 1,
              lineStyle: 2,
              title: 'BB Lower',
            })
          }

          upperBandRef.current?.setData(bbData.upper)
          middleBandRef.current?.setData(bbData.middle)
          lowerBandRef.current?.setData(bbData.lower)
          console.log('✅ Bollinger Bands ativado')
        } else {
          if (upperBandRef.current && chartRef.current) {
            chartRef.current.removeSeries(upperBandRef.current)
            upperBandRef.current = null
          }
          if (middleBandRef.current && chartRef.current) {
            chartRef.current.removeSeries(middleBandRef.current)
            middleBandRef.current = null
          }
          if (lowerBandRef.current && chartRef.current) {
            chartRef.current.removeSeries(lowerBandRef.current)
            lowerBandRef.current = null
          }
          console.log('❌ Bollinger Bands desativado')
        }

      } catch (err) {
        console.error('❌ Erro ao atualizar indicadores:', err)
      }
    }

    updateIndicators()
  }, [indicators, calculateEMA, calculateSMA, calculateBollingerBands])  // 🔥 FIX: Removido symbol e interval!

  // useEffect para atualizar tema dinamicamente sem recriar o gráfico
  useEffect(() => {
    if (!chartRef.current) return

    console.log('🎨 Aplicando tema:', theme)

    chartRef.current.applyOptions({
      layout: {
        background: { type: 'solid' as const, color: theme === 'dark' ? '#1e1e1e' : '#ffffff' },
        textColor: theme === 'dark' ? '#d1d4dc' : '#191919',
      },
      grid: {
        vertLines: { color: theme === 'dark' ? '#2b2b43' : '#e1e3eb' },
        horzLines: { color: theme === 'dark' ? '#2b2b43' : '#e1e3eb' },
      },
      rightPriceScale: {
        borderColor: theme === 'dark' ? '#2b2b43' : '#e1e3eb',
      },
      timeScale: {
        borderColor: theme === 'dark' ? '#2b2b43' : '#e1e3eb',
      },
    })
  }, [theme])

  return (
    <div className={`relative ${className}`} style={{ width, height }}>
      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10">
          <div className="flex flex-col items-center space-y-4">
            <div className="h-8 w-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <div className="text-sm text-muted-foreground">Carregando dados de {symbol}...</div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/95 z-10">
          <div className="text-center p-6 max-w-md">
            <div className="text-destructive font-semibold mb-3 text-lg">⚠️ Gráfico Indisponível</div>
            <div className="text-sm text-muted-foreground mb-4">{error}</div>
            <div className="text-xs text-muted-foreground bg-muted/30 p-3 rounded">
              💡 <strong>Dica:</strong> Alguns ativos de baixo volume ou recém-listados podem não ter dados históricos disponíveis. Tente selecionar outro símbolo popular como BTCUSDT ou ETHUSDT.
            </div>
          </div>
        </div>
      )}

      {/* Chart Container */}
      <div ref={chartContainerRef} className="w-full h-full" />

      {/* Position Action Buttons Overlay */}
      {positions && positions.length > 0 && chartRef.current && (onPositionEdit || onPositionClose) && (
        <div className="absolute top-2 right-2 space-y-1 z-20">
          {positions.map((position, idx) => {
            if (!position?.id || !position?.symbol) return null
            return (
              <div
                key={position.id || idx}
                className="flex items-center space-x-1 bg-background/90 backdrop-blur-sm border rounded-md px-2 py-1 shadow-md"
              >
                <span className="text-xs font-mono">
                  {position.symbol} {position.side}
                </span>
                {onPositionEdit && (
                  <button
                    onClick={() => onPositionEdit(position.id || '')}
                    className="p-1 hover:bg-accent rounded transition-colors"
                    title="Editar SL/TP"
                  >
                    <span className="text-xs">✏️</span>
                  </button>
                )}
                {onPositionClose && (
                  <button
                    onClick={() => onPositionClose(position.id || '')}
                    className="p-1 hover:bg-destructive/20 rounded transition-colors"
                    title="Fechar Posição"
                  >
                    <span className="text-xs">❌</span>
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Draggable SL/TP Lines Overlay */}
      {/* 🚀 PERFORMANCE: Logs commented out to reduce overhead */}
      {/* {draggableLines.length > 0 && console.log(`🎨 Renderizando ${draggableLines.length} linhas draggable`)} */}
      {draggableLines.map((line) => {
        // console.log(`  ✏️ Renderizando linha ${line.id} em y=${line.y.toFixed(1)}px`)
        return (
          <div
            key={line.id}
            onMouseDown={(e) => {
              e.preventDefault()
              e.stopPropagation()
              // console.log(`🖱️ MouseDown na linha ${line.type} (${line.id})`)
              setDraggedLine(line.id)
            }}
            style={{
              position: 'absolute',
              left: 0,
              right: 60,
              top: `${line.y}px`,
              height: '24px',
              marginTop: '-12px',
              cursor: draggedLine === line.id ? 'grabbing' : 'grab',
              zIndex: 100,
              pointerEvents: 'auto'
            }}
            className="group"
            title={`${line.type} @ $${line.price.toFixed(2)} - Arraste para mover`}
          >
            {/* Área de hit maior para facilitar o drag */}
            <div className="absolute inset-0 bg-transparent hover:bg-white/5" />
            {/* Indicador visual quando hover */}
            <div
              className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-1 opacity-0 group-hover:opacity-80 transition-opacity"
              style={{
                backgroundColor: line.color,
                boxShadow: `0 0 6px ${line.color}`,
              }}
            />
            {/* Label de preço */}
            <div
              className="absolute -left-16 top-1/2 -translate-y-1/2 text-xs font-mono px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity"
              style={{
                backgroundColor: line.color,
                color: 'white'
              }}
            >
              ${line.price.toFixed(2)}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// 🚀 PERFORMANCE: Wrap with React.memo to prevent unnecessary re-renders
const CustomChart = React.memo(CustomChartComponent, (prevProps, nextProps) => {
  // Custom comparison function - only re-render if these props change
  return (
    prevProps.symbol === nextProps.symbol &&
    prevProps.interval === nextProps.interval &&
    prevProps.theme === nextProps.theme &&
    prevProps.width === nextProps.width &&
    prevProps.height === nextProps.height &&
    JSON.stringify(prevProps.positions) === JSON.stringify(nextProps.positions) &&
    JSON.stringify(prevProps.indicators) === JSON.stringify(nextProps.indicators)
  )
})

export { CustomChart }
export type { CustomChartProps }