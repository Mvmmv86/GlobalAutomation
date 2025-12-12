import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { createChart } from 'lightweight-charts'
import type { ChartPosition } from '@/hooks/useChartPositions'
import { indicatorEngine, AnyIndicatorConfig, IndicatorResult, INDICATOR_PRESETS, TPORenderData, TPOBox, TPOHorizontalLine } from '@/utils/indicators'

// Get API URL from environment variable
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

// Quantidade de candles para carregar por página no lazy loading
const LAZY_LOAD_PAGE_SIZE = 1000

interface DraggableLine {
  id: string
  positionId: string
  type: 'stopLoss' | 'takeProfit' | 'entry'
  price: number
  color: string
  y: number
  side?: 'LONG' | 'SHORT'  // Para linhas de entrada, indica o lado da posição
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
  // Novo formato: aceita configs do IndicatorEngine diretamente
  indicators?: AnyIndicatorConfig[] | {
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
  onCreateSLTP?: (positionId: string, type: 'stopLoss' | 'takeProfit', price: number, side: 'LONG' | 'SHORT') => void
  onCancelOrder?: (positionId: string, type: 'stopLoss' | 'takeProfit') => void
  onIndicatorClick?: (indicatorId: string) => void
}

interface CandleData {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number  // Necessário para indicadores como VWAP, MFI, OBV
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
  onSLTPDrag,
  onCreateSLTP,
  onCancelOrder
}) => {
  // 🚨 DEBUG: Log no início do componente para verificar renderização
  console.log('🔵 CustomChart RENDERIZADO com:', {
    symbol,
    interval,
    positionsLength: positions?.length || 0,
    positions: positions
  })

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

  // 🔄 LAZY LOADING: Estado para controlar carregamento incremental
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [hasMoreData, setHasMoreData] = useState(true)
  const hasMoreDataRef = useRef(true) // Ref para usar em closures
  const oldestTimestampRef = useRef<number | null>(null)
  const isLoadingMoreRef = useRef(false) // Ref para evitar múltiplas chamadas

  // Refs para indicadores (legacy)
  const ema9SeriesRef = useRef<any>(null)
  const ema20SeriesRef = useRef<any>(null)
  const ema50SeriesRef = useRef<any>(null)
  const sma20SeriesRef = useRef<any>(null)
  const sma50SeriesRef = useRef<any>(null)
  const sma200SeriesRef = useRef<any>(null)
  const upperBandRef = useRef<any>(null)
  const lowerBandRef = useRef<any>(null)
  const middleBandRef = useRef<any>(null)

  // 🆕 Refs para indicadores dinâmicos do IndicatorEngine
  const indicatorSeriesMapRef = useRef<Map<string, any[]>>(new Map())

  // 📊 TPO Canvas Overlay
  const tpoCanvasRef = useRef<HTMLCanvasElement>(null)
  const tpoRenderDataRef = useRef<TPORenderData[] | null>(null)

  // 🚀 TPO Performance: Debounce para evitar re-renders excessivos
  const tpoRenderTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const tpoLastRenderRef = useRef<number>(0)

  // Mapear interval do frontend para Binance API
  const mapIntervalToBinance = (interval: string): string => {
    const mapping: Record<string, string> = {
      '1': '1m',
      '3': '3m',
      '5': '5m',
      '10': '10m',   // ✅ NOVO: 10 minutos
      '15': '15m',
      '30': '30m',
      '60': '1h',
      '120': '2h',   // ✅ NOVO: 2 horas
      '240': '4h',
      '1D': '1d',
      '3D': '3d',    // ✅ NOVO: 3 dias
      '1W': '1w',
      '1M': '1M'
    }
    return mapping[interval] || '1h'
  }

  // 📅 Limite dinâmico baseado no timeframe para histórico inteligente
  const getOptimalLimit = (interval: string): number => {
    const limits: Record<string, number> = {
      '1': 500,      // 1m = ~8 horas
      '3': 500,      // 3m = ~1 dia
      '5': 500,      // 5m = ~1.7 dias
      '10': 720,     // ✅ NOVO: 10m = ~5 dias
      '15': 672,     // 15m = ~7 dias (1 semana)
      '30': 720,     // 30m = ~15 dias
      '60': 720,     // 1h = ~30 dias (1 mês)
      '120': 720,    // ✅ NOVO: 2h = ~60 dias (2 meses)
      '240': 720,    // 4h = ~120 dias (4 meses)
      '1D': 730,     // 1D = ~2 anos
      '3D': 730,     // ✅ NOVO: 3D = ~6 anos
      '1W': 520,     // 1W = ~10 anos
      '1M': 120      // 1M = ~10 anos
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

  // 🔄 LAZY LOADING: Função para carregar mais candles históricos
  const loadMoreCandles = useCallback(async () => {
    if (isLoadingMoreRef.current || !hasMoreDataRef.current || !oldestTimestampRef.current) {
      console.log('📍 [LazyLoad] Ignorando chamada:', {
        isLoadingMore: isLoadingMoreRef.current,
        hasMoreData: hasMoreDataRef.current,
        oldestTimestamp: oldestTimestampRef.current
      })
      return
    }

    isLoadingMoreRef.current = true
    setIsLoadingMore(true)

    try {
      const binanceInterval = mapIntervalToBinance(interval)
      // endTime deve ser 1ms antes do candle mais antigo atual (em milissegundos)
      const endTime = oldestTimestampRef.current * 1000 - 1

      console.log(`📜 [LazyLoad] Carregando mais candles antes de ${new Date(endTime).toISOString()}`)

      const response = await fetch(
        `${API_URL}/api/v1/market/candles/history?symbol=${symbol}&interval=${binanceInterval}&end_time=${endTime}&limit=${LAZY_LOAD_PAGE_SIZE}`
      )

      const data = await response.json()

      if (!response.ok || !data.success) {
        console.error('❌ [LazyLoad] Erro ao buscar candles históricos:', data)
        setHasMoreData(false)
        hasMoreDataRef.current = false
        return
      }

      const newCandles: CandleData[] = data.candles.map((candle: any) => ({
        time: candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volume: candle.volume || 0,  // Incluir volume para manter consistência
      }))

      if (newCandles.length === 0) {
        console.log('📭 [LazyLoad] Não há mais dados históricos disponíveis')
        setHasMoreData(false)
        hasMoreDataRef.current = false
        return
      }

      // Atualizar timestamp mais antigo
      oldestTimestampRef.current = newCandles[0].time

      // Verificar se há mais dados
      setHasMoreData(data.has_more)
      hasMoreDataRef.current = data.has_more

      // Combinar com dados existentes (novos no início)
      if (candlesDataRef.current) {
        const combined = [...newCandles, ...candlesDataRef.current]
        candlesDataRef.current = combined

        // Atualizar gráfico
        if (candlestickSeriesRef.current) {
          candlestickSeriesRef.current.setData(combined)
          console.log(`✅ [LazyLoad] ${newCandles.length} candles adicionados. Total: ${combined.length}`)
        }

        // Atualizar volume também - preservar volume existente
        if (volumeSeriesRef.current) {
          const volumeData = combined.map((candle: CandleData) => ({
            time: candle.time,
            value: candle.volume || 0, // Usar volume real se disponível
            color: candle.close >= candle.open ? '#10B98180' : '#EF444480',
          }))
          volumeSeriesRef.current.setData(volumeData)
        }
      }

    } catch (err) {
      console.error('❌ [LazyLoad] Erro:', err)
    } finally {
      isLoadingMoreRef.current = false
      setIsLoadingMore(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval])

  // 📊 TPO Canvas Render Function
  // RÉPLICA do TradingView - Perfil à ESQUERDA de cada sessão (fora dos candles)
  // Renderiza histograma horizontal mostrando distribuição de preços
  const renderTPOCanvasInternal = useCallback(() => {
    const canvas = tpoCanvasRef.current
    const chart = chartRef.current
    const series = candlestickSeriesRef.current
    const allRenderData = tpoRenderDataRef.current
    const timeScale = chart?.timeScale()

    if (!canvas || !chart || !series || !timeScale || !allRenderData || allRenderData.length === 0) {
      return
    }

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const chartElement = chartContainerRef.current
    if (!chartElement) return

    const rect = chartElement.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Cores do Pine Script original
    const COLORS = {
      open: '#FF9800',        // Laranja - abertura
      poc: '#FF0000',         // Vermelho - POC
      inValue: '#2196F3',     // Azul - Value Area
      outOfValue: '#4CAF50',  // Verde - Fora do VA
      background: 'rgba(0, 0, 0, 0.3)', // Fundo semi-transparente
    }

    const rightMargin = 65

    // =========================================================================
    // RENDERIZAR CADA SESSÃO COMO HISTOGRAMA
    // IMPORTANTE: Usar profile.startTime e profile.endTime para posicionamento correto
    // Os candles no renderData são apenas para referência, os times do profile são precisos
    // =========================================================================
    for (const renderData of allRenderData) {
      const { profile, candles } = renderData
      if (!candles || candles.length === 0) continue

      // Obter coordenadas X da sessão usando os times do PROFILE (não dos candles)
      // Isso garante posicionamento correto mesmo com sessões consecutivas
      const firstCandleX = timeScale.timeToCoordinate(profile.startTime as any)
      const lastCandleX = timeScale.timeToCoordinate(profile.endTime as any)

      // Skip se a sessão inteira está fora da view
      if (firstCandleX === null || lastCandleX === null) continue
      if (lastCandleX < 0 || firstCandleX > canvas.width - rightMargin) continue

      // =====================================================================
      // CALCULAR DIMENSÕES DO HISTOGRAMA
      // O histograma fica à ESQUERDA da sessão, crescendo para direita (sobrepõe candles)
      // Como no TradingView - perfil fica como "background" atrás dos candles
      // =====================================================================
      const sessionWidth = Math.abs(lastCandleX - firstCandleX)
      const histogramMaxWidth = Math.min(sessionWidth * 0.6, 200) // 60% da sessão ou max 200px
      const histogramStartX = firstCandleX // Começa no primeiro candle da sessão

      // Encontrar o maior TPO count para normalizar
      const maxTPOCount = Math.max(...profile.levels.map(l => l.tpoCount))
      if (maxTPOCount === 0) continue

      // =====================================================================
      // 1. RENDERIZAR BARRAS DO HISTOGRAMA (à direita da sessão)
      // Barras crescem da esquerda para direita (como TradingView)
      // =====================================================================
      for (const level of profile.levels) {
        if (level.tpoCount === 0) continue

        // Coordenadas Y do nível
        const yTop = series.priceToCoordinate(level.priceMax)
        const yBottom = series.priceToCoordinate(level.priceMin)
        if (yTop === null || yBottom === null) continue

        // Largura da barra proporcional ao TPO count
        const barWidth = (level.tpoCount / maxTPOCount) * histogramMaxWidth

        // Cor da barra - mais transparente para não cobrir os candles
        let barColor: string
        let barAlpha = 0.4

        if (level.isPOC) {
          barColor = COLORS.poc
          barAlpha = 0.6
        } else if (level.isInValueArea) {
          barColor = COLORS.inValue
          barAlpha = 0.4
        } else {
          barColor = COLORS.outOfValue
          barAlpha = 0.3
        }

        // Altura da barra
        const barHeight = Math.abs(yBottom - yTop)
        const barY = Math.min(yTop, yBottom)

        // Verificar se o histograma cabe na tela (não ultrapassar rightMargin)
        const maxBarEnd = canvas.width - rightMargin
        const actualBarWidth = Math.min(barWidth, maxBarEnd - histogramStartX)
        if (actualBarWidth <= 0) continue

        // Desenhar barra do histograma (cresce da esquerda para direita)
        ctx.globalAlpha = barAlpha
        ctx.fillStyle = barColor
        ctx.fillRect(
          histogramStartX,
          barY,
          actualBarWidth,
          Math.max(barHeight, 2) // Mínimo 2px de altura
        )

        // Borda mais clara para POC
        if (level.isPOC) {
          ctx.strokeStyle = '#FFFFFF'
          ctx.lineWidth = 1
          ctx.globalAlpha = 0.8
          ctx.strokeRect(
            histogramStartX,
            barY,
            actualBarWidth,
            Math.max(barHeight, 2)
          )
        }
      }

      // =====================================================================
      // 2. LABELS DE PREÇO NO HISTOGRAMA (opcional - à direita das barras)
      // =====================================================================
      ctx.font = 'bold 8px monospace'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'middle'
      ctx.globalAlpha = 0.9

      // Mostrar apenas POC label
      const pocLevel = profile.levels.find(l => l.isPOC)
      if (pocLevel) {
        const yCenter = series.priceToCoordinate(pocLevel.priceMid)
        if (yCenter !== null) {
          const barWidth = (pocLevel.tpoCount / maxTPOCount) * histogramMaxWidth
          const maxBarEnd = canvas.width - rightMargin
          const actualBarWidth = Math.min(barWidth, maxBarEnd - histogramStartX)
          const textX = histogramStartX + actualBarWidth + 3

          if (textX < canvas.width - rightMargin - 30) {
            ctx.fillStyle = '#FFFFFF'
            ctx.fillText(`${pocLevel.tpoCount}`, textX, yCenter)
          }
        }
      }

      // =====================================================================
      // 3. RENDERIZAR LINHAS POC, VAH, VAL - Por toda a sessão
      // =====================================================================
      const lineStartX = Math.max(0, firstCandleX)
      const lineEndX = Math.min(canvas.width - rightMargin, lastCandleX + 10)

      // Linha POC (vermelho sólido, mais grossa)
      if (profile.poc) {
        const pocY = series.priceToCoordinate(profile.poc)
        if (pocY !== null) {
          ctx.strokeStyle = COLORS.poc
          ctx.lineWidth = 2
          ctx.setLineDash([])
          ctx.globalAlpha = 0.8
          ctx.beginPath()
          ctx.moveTo(lineStartX, pocY)
          ctx.lineTo(lineEndX, pocY)
          ctx.stroke()

          // Label POC à esquerda
          ctx.fillStyle = COLORS.poc
          ctx.font = 'bold 9px sans-serif'
          ctx.textAlign = 'right'
          ctx.fillText('POC', lineStartX - 3, pocY + 3)
        }
      }

      // Linha VAH (azul tracejado)
      if (profile.vah) {
        const vahY = series.priceToCoordinate(profile.vah)
        if (vahY !== null) {
          ctx.strokeStyle = COLORS.inValue
          ctx.lineWidth = 1
          ctx.setLineDash([4, 4])
          ctx.globalAlpha = 0.6
          ctx.beginPath()
          ctx.moveTo(lineStartX, vahY)
          ctx.lineTo(lineEndX, vahY)
          ctx.stroke()

          // Label VAH à esquerda
          ctx.fillStyle = COLORS.inValue
          ctx.font = '8px sans-serif'
          ctx.textAlign = 'right'
          ctx.setLineDash([])
          ctx.fillText('VAH', lineStartX - 3, vahY + 3)
        }
      }

      // Linha VAL (azul tracejado)
      if (profile.val) {
        const valY = series.priceToCoordinate(profile.val)
        if (valY !== null) {
          ctx.strokeStyle = COLORS.inValue
          ctx.lineWidth = 1
          ctx.setLineDash([4, 4])
          ctx.globalAlpha = 0.6
          ctx.beginPath()
          ctx.moveTo(lineStartX, valY)
          ctx.lineTo(lineEndX, valY)
          ctx.stroke()

          // Label VAL à esquerda
          ctx.fillStyle = COLORS.inValue
          ctx.font = '8px sans-serif'
          ctx.textAlign = 'right'
          ctx.setLineDash([])
          ctx.fillText('VAL', lineStartX - 3, valY + 3)
        }
      }

      // =====================================================================
      // 4. SEPARADOR DE SESSÃO (linha vertical no início da sessão)
      // =====================================================================
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)'
      ctx.lineWidth = 1
      ctx.setLineDash([4, 8])
      ctx.globalAlpha = 0.4
      ctx.beginPath()
      ctx.moveTo(firstCandleX, 0)
      ctx.lineTo(firstCandleX, canvas.height)
      ctx.stroke()
    }

    // =========================================================================
    // 5. INFO BOX (última sessão) - Pine Script: table.cell()
    // =========================================================================
    const lastProfile = allRenderData[allRenderData.length - 1]?.profile
    if (lastProfile) {
      const infoBoxWidth = 130
      const infoBoxHeight = 70
      const infoBoxX = canvas.width - rightMargin - infoBoxWidth - 10
      const infoBoxY = 10

      ctx.globalAlpha = 0.9
      ctx.fillStyle = '#1a1a2e'
      ctx.setLineDash([])
      ctx.fillRect(infoBoxX, infoBoxY, infoBoxWidth, infoBoxHeight)

      ctx.strokeStyle = '#444'
      ctx.lineWidth = 1
      ctx.strokeRect(infoBoxX, infoBoxY, infoBoxWidth, infoBoxHeight)

      ctx.globalAlpha = 1.0
      ctx.fillStyle = '#FFFFFF'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'

      ctx.fillText(`Tick: $${lastProfile.tickSize.toFixed(2)}`, infoBoxX + 5, infoBoxY + 5)

      const tpoCountColor = lastProfile.totalTPOs > 495 ? '#FF0000' : '#FFFFFF'
      ctx.fillStyle = tpoCountColor
      ctx.fillText(`TPOs: ${lastProfile.totalTPOs}`, infoBoxX + 5, infoBoxY + 20)

      ctx.fillStyle = '#FFFFFF'
      ctx.fillText(`Sessions: ${allRenderData.length}`, infoBoxX + 5, infoBoxY + 35)
      ctx.fillText(`Letter: ${lastProfile.currentLetter}`, infoBoxX + 5, infoBoxY + 50)
    }

    // Reset
    ctx.setLineDash([])
    ctx.globalAlpha = 1.0
  }, [])

  // 🚀 PERFORMANCE: Wrapper com throttle para evitar re-renders excessivos
  const renderTPOCanvas = useCallback(() => {
    const now = Date.now()
    const timeSinceLastRender = now - tpoLastRenderRef.current

    // Se passou menos de 50ms desde o último render, agendar para depois
    if (timeSinceLastRender < 50) {
      if (tpoRenderTimeoutRef.current) {
        clearTimeout(tpoRenderTimeoutRef.current)
      }
      tpoRenderTimeoutRef.current = setTimeout(() => {
        tpoLastRenderRef.current = Date.now()
        renderTPOCanvasInternal()
      }, 50 - timeSinceLastRender)
      return
    }

    // Render imediato
    tpoLastRenderRef.current = now
    renderTPOCanvasInternal()
  }, [renderTPOCanvasInternal])

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
      localization: {
        // 🔥 FIX: Ajustar timezone para horário local (BRT = UTC-3)
        // O timestamp vem em UTC, precisamos converter para horário local
        timeFormatter: (timestamp: number) => {
          const date = new Date(timestamp * 1000)
          return date.toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
          })
        },
        dateFormatter: (timestamp: number) => {
          const date = new Date(timestamp * 1000)
          return date.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: 'short'
          })
        },
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
      lastValueVisible: false,  // Remove a linha horizontal do último valor
      priceLineVisible: false,  // Remove a linha de preço tracejada
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
      baseLineVisible: false, // Remove a linha de base horizontal
      baseLineColor: 'transparent', // Cor transparente caso apareça
      baseLineWidth: 1, // Largura mínima
      baseLineStyle: 0, // Estilo sólido (não pontilhado)
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

    // 🔄 LAZY LOADING: Listener para detectar scroll para a esquerda (passado)
    // 📊 TPO: Re-render canvas when chart view changes
    const timeScale = chart.timeScale()
    timeScale.subscribeVisibleLogicalRangeChange((logicalRange) => {
      if (!logicalRange || !candlesDataRef.current || candlesDataRef.current.length === 0) {
        return
      }

      // Se o usuário scrollou até perto do início dos dados (candles antigos)
      // logicalRange.from é o índice lógico do primeiro candle visível
      // Se from < 10, significa que estamos vendo os candles mais antigos
      // Usando refs para evitar problemas de closure
      if (logicalRange.from !== null && logicalRange.from < 10 && hasMoreDataRef.current && !isLoadingMoreRef.current) {
        console.log(`📍 [LazyLoad] Perto do início dos dados (from=${logicalRange.from}), carregando mais...`)
        loadMoreCandles()
      }

      // 📊 TPO: Re-render canvas when view changes
      if (tpoRenderDataRef.current && tpoRenderDataRef.current.length > 0) {
        renderTPOCanvas()
      }
    })

    // Cleanup
    return () => {
      resizeObserver.disconnect()
      chart.remove()
      console.log('🧹 CustomChart: Gráfico removido')
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme, width, height, onChartClick, loadMoreCandles])

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
          `${API_URL}/api/v1/market/candles?symbol=${symbol}&interval=${binanceInterval}&limit=${optimalLimit}`
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
          volume: candle.volume || 0,  // Incluir volume para indicadores VWAP, MFI, etc.
        }))

        const volumeData = data.candles.map((candle: any) => ({
          time: candle.time,
          value: candle.volume,
          color: candle.close >= candle.open ? '#10B98180' : '#EF444480',
        }))

        // 🚀 PERFORMANCE: Cache the data for future use
        candlesDataRef.current = candleData
        candlesCacheKey.current = `${symbol}:${interval}`

        // 🔄 LAZY LOADING: Salvar timestamp do candle mais antigo
        if (candleData.length > 0) {
          oldestTimestampRef.current = candleData[0].time
          setHasMoreData(true) // Reset para permitir carregar mais
          hasMoreDataRef.current = true
          console.log(`📅 [LazyLoad] Oldest timestamp: ${new Date(candleData[0].time * 1000).toISOString()}, hasMoreData: true`)
        }

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
    // Sempre limpar linhas antigas primeiro
    priceLineIdsRef.current.forEach(priceLine => {
      try {
        candlestickSeriesRef.current?.removePriceLine(priceLine)
      } catch (e) {
        console.warn('Erro ao remover price line:', e)
      }
    })
    priceLineIdsRef.current = []
    setDraggableLines([])  // Limpar linhas draggable também

    if (!candlestickSeriesRef.current || !positions || positions.length === 0) {
      console.log('⚠️ Sem posições para desenhar ou série não disponível')
      return
    }

    console.log('🎨 Desenhando', positions.length, 'posições no gráfico')
    console.log('📊 DEBUG SL/TP - Posições recebidas:', JSON.stringify(positions, null, 2))

    // Array para linhas draggable
    const newDraggableLines: DraggableLine[] = []

    // Desenhar novas linhas para cada posição
    positions.forEach((position, idx) => {
      console.log(`📍 Desenhando posição ${idx + 1}:`, {
        symbol: position.symbol,
        side: position.side,
        entryPrice: position.entryPrice,
        quantity: position.quantity,
        stopLoss: position.stopLoss,
        takeProfit: position.takeProfit,
        allTakeProfits: position.allTakeProfits
      })

      // 🚨 DEBUG CRÍTICO: Verificar se SL/TP existem
      if (!position.stopLoss && !position.takeProfit) {
        console.warn(`⚠️ ATENÇÃO: Posição ${idx + 1} SEM SL/TP! Dados:`, position)
      }

      try {
        const color = position.side === 'LONG' ? '#10B981' : '#EF4444'

        // Linha de entrada - SUTIL (cinza) - a cor aparece no overlay quando arrasta
        const priceLine = candlestickSeriesRef.current!.createPriceLine({
          price: position.entryPrice,
          color: '#6B7280',  // Cinza neutro
          lineWidth: 1,  // Fina
          lineStyle: 2,  // Tracejada
          axisLabelVisible: true,
          title: `${position.side} @ $${position.entryPrice.toFixed(2)}`,
        })
        priceLineIdsRef.current.push(priceLine)

        // Adicionar linha de entrada como draggable
        const entryY = candlestickSeriesRef.current!.priceToCoordinate(position.entryPrice)
        if (entryY !== null) {
          newDraggableLines.push({
            id: `entry-${position.id}`,
            positionId: position.id,
            type: 'entry',
            price: position.entryPrice,
            color: color,  // Cor original para usar quando arrastar
            y: entryY,
            side: position.side as 'LONG' | 'SHORT'
          })
        }

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

  }, [positions, symbol]) // Adiciona symbol para limpar linhas ao mudar de ativo

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
        hasOnSLTPDrag: !!onSLTPDrag,
        hasOnCreateSLTP: !!onCreateSLTP
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

      // Encontrar a linha arrastada
      const line = draggableLines.find(l => l.id === draggedLine)
      console.log('🔍 Linha encontrada:', line)

      if (line) {
        // Converter coordenada Y de volta para preço
        const newPrice = candlestickSeriesRef.current.coordinateToPrice(line.y)
        console.log('💰 Novo preço calculado:', newPrice)

        if (newPrice) {
          // CASO ESPECIAL: Linha de ENTRADA - criar SL ou TP
          if (line.type === 'entry' && onCreateSLTP && line.side) {
            const priceDiff = newPrice - line.price

            // Para LONG: arrastar para cima = TP, arrastar para baixo = SL
            // Para SHORT: arrastar para cima = SL, arrastar para baixo = TP
            let orderType: 'stopLoss' | 'takeProfit'

            if (line.side === 'LONG') {
              orderType = priceDiff > 0 ? 'takeProfit' : 'stopLoss'
            } else {
              orderType = priceDiff > 0 ? 'stopLoss' : 'takeProfit'
            }

            // Verificar se houve movimento significativo (pelo menos 0.1% do preço)
            const minMovement = line.price * 0.001
            if (Math.abs(priceDiff) > minMovement) {
              console.log(`🎯 Criando ${orderType} para ${line.side} @ $${newPrice.toFixed(2)}`)
              onCreateSLTP(line.positionId, orderType, newPrice, line.side)
            } else {
              console.log('⚠️ Movimento muito pequeno, ignorando')
            }
          }
          // CASO NORMAL: Mover SL/TP existente
          else if (line.type !== 'entry' && onSLTPDrag) {
            console.log(`🎯 Linha ${line.type} arrastada para $${newPrice.toFixed(2)} - Chamando API...`)
            onSLTPDrag(line.positionId, line.type, newPrice)
          } else {
            console.log('❌ Callback não disponível para este tipo de linha')
          }
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
  }, [draggedLine, draggableLines, onSLTPDrag, onCreateSLTP])

  // 🔥 FIX CRÍTICO: useEffect para reagir às mudanças de indicadores em tempo real
  // IMPORTANTE: Removido symbol e interval das dependências para evitar race condition
  // 🔥 FIX: Ref para controlar retries de indicadores
  const indicatorRetryCountRef = useRef(0)
  const maxIndicatorRetries = 20  // 20 tentativas x 200ms = 4 segundos máximo

  useEffect(() => {
    if (!chartRef.current || !candlestickSeriesRef.current) return

    const updateIndicators = async () => {
      try {
        // 🚀 RETRY LOGIC: Esperar dados estarem disponíveis
        if (!candlesDataRef.current || candlesDataRef.current.length === 0) {
          indicatorRetryCountRef.current++

          if (indicatorRetryCountRef.current <= maxIndicatorRetries) {
            console.log(`⏳ Aguardando candles... (tentativa ${indicatorRetryCountRef.current}/${maxIndicatorRetries})`)

            // ✅ Retry após 200ms (dados podem estar carregando)
            setTimeout(() => {
              updateIndicators()  // Tentar novamente
            }, 200)
          } else {
            console.log('❌ Timeout esperando candles para indicadores')
          }

          return
        }

        // Reset contador quando sucesso
        indicatorRetryCountRef.current = 0

        const candleData = candlesDataRef.current
        console.log('📊 Aplicando indicadores INSTANTANEAMENTE com', candleData.length, 'candles')

        // 🆕 DETECTAR FORMATO: Array de configs OU objeto booleano
        const isArrayFormat = Array.isArray(indicators)

        if (isArrayFormat) {
          // ========================================
          // 🆕 NOVO FORMATO: Array de AnyIndicatorConfig
          // Usa IndicatorEngine para cálculo
          // ========================================
          const indicatorConfigs = indicators as AnyIndicatorConfig[]
          console.log('📊 Processando', indicatorConfigs.length, 'indicadores via IndicatorEngine')

          // Converter candles para formato do IndicatorEngine
          // 🔥 FIX: Usar volume real dos candles para indicadores como MFI, VP, OBV, ADL, FI, VWAP
          const engineCandles = candleData.map(c => ({
            time: c.time,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume || 0 // 🔥 Agora usando volume real!
          }))

          // IDs dos indicadores atuais
          const currentIndicatorIds = new Set(indicatorConfigs.map(c => c.id))

          // Remover séries de indicadores que não estão mais ativos
          indicatorSeriesMapRef.current.forEach((seriesArray, id) => {
            if (!currentIndicatorIds.has(id)) {
              seriesArray.forEach(series => {
                try {
                  chartRef.current?.removeSeries(series)
                } catch (e) {
                  console.warn('Erro ao remover série:', e)
                }
              })
              indicatorSeriesMapRef.current.delete(id)
              console.log(`❌ Indicador ${id} removido`)

              // 📊 TPO: Limpar canvas se TPO foi removido
              if (id.toLowerCase().includes('tpo')) {
                tpoRenderDataRef.current = null
                const canvas = tpoCanvasRef.current
                if (canvas) {
                  const ctx = canvas.getContext('2d')
                  if (ctx) {
                    ctx.clearRect(0, 0, canvas.width, canvas.height)
                  }
                }
              }
            }
          })

          // 📊 TPO: Verificar se TPO ainda está ativo, senão limpar canvas
          const hasTPO = indicatorConfigs.some(c => c.type === 'TPO' && c.enabled)
          if (!hasTPO && tpoRenderDataRef.current) {
            tpoRenderDataRef.current = null
            const canvas = tpoCanvasRef.current
            if (canvas) {
              const ctx = canvas.getContext('2d')
              if (ctx) {
                ctx.clearRect(0, 0, canvas.width, canvas.height)
              }
            }
          }

          // Processar cada indicador
          for (const config of indicatorConfigs) {
            if (!config.enabled) continue

            // Calcular usando IndicatorEngine
            const result = indicatorEngine.calculateSync(config, engineCandles)
            if (!result) {
              console.warn(`⚠️ Indicador ${config.type} retornou null`)
              continue
            }

            // Verificar se já existe série para este indicador
            let seriesArray = indicatorSeriesMapRef.current.get(config.id)

            // Determinar tipo de indicador (overlay vs separate)
            const isOverlay = config.displayType === 'overlay'

            if (!seriesArray) {
              // Criar novas séries
              seriesArray = []

              // 📊 TPO: Usa apenas canvas, não criar séries de linha
              if (config.type === 'TPO') {
                // TPO não cria LineSeries - usa apenas canvas overlay
                // Apenas registrar no map para controle de lifecycle
                indicatorSeriesMapRef.current.set(config.id, seriesArray)
                console.log(`📊 TPO: Usando apenas canvas para renderização`)

                // Processar dados TPO e renderizar
                if ((result as any).tpoRenderData) {
                  tpoRenderDataRef.current = (result as any).tpoRenderData
                  setTimeout(() => renderTPOCanvas(), 100)
                }
                continue // Pular criação de LineSeries
              }

              // Série principal
              if (isOverlay) {
                // Indicadores overlay usam LineSeries
                // Para NW Envelope, esconder labels da lateral
                const hideLabels = config.type === 'NWENVELOPE'

                const mainColor = config.color || INDICATOR_PRESETS[config.type]?.color || '#FFFFFF'

                const mainSeries = chartRef.current!.addLineSeries({
                  color: mainColor,
                  lineWidth: config.lineWidth || 2,
                  title: hideLabels ? '' : config.type,
                  priceLineVisible: false,
                  lastValueVisible: !hideLabels,
                })
                seriesArray.push(mainSeries)
              } else {
                // Indicadores separate usam HistogramSeries para MACD histogram, ou LineSeries
                const mainSeries = chartRef.current!.addLineSeries({
                  color: config.color || INDICATOR_PRESETS[config.type]?.color || '#FFFFFF',
                  lineWidth: config.lineWidth || 2,
                  title: config.type,
                  priceLineVisible: false,
                  lastValueVisible: true,
                  priceScaleId: `indicator-${config.id}`,
                })

                // Configurar escala de preço separada
                mainSeries.priceScale().applyOptions({
                  scaleMargins: {
                    top: 0.8,
                    bottom: 0,
                  },
                })

                seriesArray.push(mainSeries)
              }

              // Séries adicionais (signal, upper, lower, etc.)
              if (result.additionalLines) {
                // Cores especiais para Nadaraya-Watson Envelope (LuxAlgo style)
                const isNWEnvelope = config.type === 'NWENVELOPE'
                // Cores especiais para TPO / Market Profile
                const isTPO = config.type === 'TPO'

                const additionalColors: Record<string, string> = {
                  signal: '#FF6D00',
                  upper: isNWEnvelope ? 'rgba(239, 83, 80, 0.8)' : '#9E9E9E',  // Red for NW
                  lower: isNWEnvelope ? 'rgba(38, 166, 154, 0.8)' : '#9E9E9E', // Teal for NW
                  // TPO specific colors (Pine Script original: VAH/VAL = azul)
                  vah: isTPO ? '#2196F3' : '#9E9E9E',   // Azul para VAH
                  val: isTPO ? '#2196F3' : '#9E9E9E',   // Azul para VAL
                  d: '#FF6D00',
                  pdi: '#10B981',
                  mdi: '#EF4444',
                  base: '#2962FF',
                  spanA: '#10B98180',
                  spanB: '#EF444480',
                  overbought: '#EF4444',
                  oversold: '#10B981',
                }

                Object.keys(result.additionalLines).forEach(lineKey => {
                  // Determinar estilo da linha baseado no tipo
                  let lineStyle = 0 // Sólido
                  if (lineKey === 'upper' || lineKey === 'lower') lineStyle = 2 // Pontilhado
                  if (isTPO && lineKey === 'vah') lineStyle = 2 // VAH pontilhado

                  // Determinar largura da linha
                  let lineWidthForKey = 1
                  if (isTPO && lineKey === 'val') lineWidthForKey = 2 // VAL mais grossa

                  const additionalSeries = chartRef.current!.addLineSeries({
                    color: additionalColors[lineKey] || '#888888',
                    lineWidth: lineWidthForKey,
                    lineStyle: lineStyle,
                    title: (isNWEnvelope || isTPO) ? '' : `${config.type} ${lineKey}`,  // Hide labels for NW and TPO
                    priceLineVisible: false,
                    lastValueVisible: false,
                    priceScaleId: isOverlay ? undefined : `indicator-${config.id}`,
                  })
                  seriesArray!.push(additionalSeries)
                })
              }

              indicatorSeriesMapRef.current.set(config.id, seriesArray)
              console.log(`✅ Indicador ${config.type} criado com ${seriesArray.length} séries`)
            }

            // 📊 TPO: Apenas atualizar canvas, não séries
            if (config.type === 'TPO') {
              if ((result as any).tpoRenderData) {
                console.log('📊 TPO: Atualizando canvas com novos dados')
                tpoRenderDataRef.current = (result as any).tpoRenderData
                setTimeout(() => renderTPOCanvas(), 100)
              }
              continue // TPO não usa LineSeries
            }

            // Atualizar dados da série principal (para outros indicadores)
            const mainSeriesData = result.values
              .map((value, idx) => ({
                time: candleData[idx].time,
                value: value
              }))
              .filter(d => !isNaN(d.value) && d.value !== null)

            seriesArray[0]?.setData(mainSeriesData)

            // Atualizar séries adicionais
            if (result.additionalLines && seriesArray.length > 1) {
              const additionalKeys = Object.keys(result.additionalLines)
              additionalKeys.forEach((key, idx) => {
                const additionalData = result.additionalLines![key]
                  .map((value, i) => ({
                    time: candleData[i].time,
                    value: value
                  }))
                  .filter(d => !isNaN(d.value) && d.value !== null)

                seriesArray![idx + 1]?.setData(additionalData)
              })
            }

            // Renderizar sinais de compra/venda (para NW Envelope e outros indicadores)
            console.log(`🔍 DEBUG ${config.type}: signals =`, result.signals, 'length =', result.signals?.length || 0)
            if (result.signals && result.signals.length > 0 && candlestickSeriesRef.current) {
              const markers = result.signals.map(signal => ({
                time: signal.time as import('lightweight-charts').Time,
                position: signal.type === 'buy' ? 'belowBar' as const : 'aboveBar' as const,
                color: signal.type === 'buy' ? '#26A69A' : '#EF5350',  // Teal for buy, Red for sell
                shape: signal.type === 'buy' ? 'arrowUp' as const : 'arrowDown' as const,
                text: signal.type === 'buy' ? 'BUY' : 'SELL',
                size: 2
              }))

              console.log(`📍 DEBUG: Creating ${markers.length} markers:`, markers.slice(0, 5))

              // Substituir todos os markers (não acumular)
              candlestickSeriesRef.current.setMarkers(markers)
              console.log(`📍 ${markers.length} sinais de ${config.type} adicionados ao gráfico`)
            } else {
              console.log(`⚠️ DEBUG: No signals to render for ${config.type}. candlestickSeriesRef exists: ${!!candlestickSeriesRef.current}`)
            }

            console.log(`✅ Indicador ${config.type} atualizado`)
          }

        } else {
          // ========================================
          // FORMATO LEGADO: Objeto booleano
          // ========================================
          const legacyIndicators = indicators as {
            ema9?: boolean; ema20?: boolean; ema50?: boolean;
            sma20?: boolean; sma50?: boolean; sma200?: boolean;
            bollingerBands?: boolean;
          }

          // EMA 9
          if (legacyIndicators.ema9) {
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
          if (legacyIndicators.ema20) {
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
          if (legacyIndicators.ema50) {
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
          if (legacyIndicators.sma20) {
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
          if (legacyIndicators.sma50) {
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
          if (legacyIndicators.sma200) {
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
          if (legacyIndicators.bollingerBands) {
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

      {/* 🔄 LAZY LOADING: Indicador de carregamento de mais dados */}
      {isLoadingMore && (
        <div className="absolute top-2 left-2 flex items-center space-x-2 bg-background/90 backdrop-blur-sm border rounded-md px-3 py-1.5 shadow-md z-20">
          <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-muted-foreground">Carregando histórico...</span>
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

      {/* TPO Canvas Overlay */}
      <canvas
        ref={tpoCanvasRef}
        className="absolute inset-0 pointer-events-none"
        style={{ zIndex: 5 }}
      />

      {/* Position Action Buttons Overlay - REMOVIDO conforme solicitação do usuário */}
      {/* Os botões de ação ficam apenas na tabela de posições abaixo do gráfico */}

      {/* Draggable SL/TP Lines Overlay */}
      {draggableLines.map((line) => {
        const isEntryLine = line.type === 'entry'
        const isDragging = draggedLine === line.id

        // Para linhas de entrada sendo arrastadas, calcular direção e cor
        let dragColor = line.color
        let dragLabel = ''
        let showDragPreview = false

        if (isEntryLine && isDragging && candlestickSeriesRef.current) {
          // Calcular preço atual baseado na posição Y
          const currentPrice = candlestickSeriesRef.current.coordinateToPrice(line.y)
          if (currentPrice) {
            const priceDiff = currentPrice - line.price
            const isGoingUp = priceDiff > 0

            // Determinar cor e label baseado na direção e lado da posição
            if (line.side === 'LONG') {
              dragColor = isGoingUp ? '#10B981' : '#EF4444' // Verde para TP, Vermelho para SL
              dragLabel = isGoingUp ? 'TP' : 'SL'
            } else {
              dragColor = isGoingUp ? '#EF4444' : '#10B981' // Vermelho para SL, Verde para TP
              dragLabel = isGoingUp ? 'SL' : 'TP'
            }
            showDragPreview = Math.abs(priceDiff) > line.price * 0.001
          }
        }

        const typeLabel = isEntryLine
          ? `Arraste para criar SL/TP (${line.side})`
          : line.type === 'stopLoss'
            ? 'Stop Loss'
            : 'Take Profit'

        // Cor da linha: cinza neutro para entrada (não arrastando), cor normal para SL/TP
        const lineDisplayColor = isEntryLine && !isDragging
          ? '#6B7280' // Cinza neutro quando não está arrastando
          : isDragging && showDragPreview
            ? dragColor // Cor baseada na direção quando arrastando
            : line.color

        return (
          <div
            key={line.id}
            onMouseDown={(e) => {
              e.preventDefault()
              e.stopPropagation()
              setDraggedLine(line.id)
            }}
            style={{
              position: 'absolute',
              left: 0,
              right: 60,
              top: `${line.y}px`,
              height: isEntryLine ? '32px' : '24px',
              marginTop: isEntryLine ? '-16px' : '-12px',
              cursor: isDragging ? 'grabbing' : 'grab',
              zIndex: isDragging ? 120 : (isEntryLine ? 110 : 100),
              pointerEvents: 'auto'
            }}
            className="group"
            title={`${typeLabel} @ $${line.price.toFixed(2)}`}
          >
            {/* Área de hit maior para facilitar o drag */}
            <div className={`absolute inset-0 bg-transparent ${isEntryLine ? 'hover:bg-white/10' : 'hover:bg-white/5'}`} />

            {/* Linha visual */}
            <div
              className={`absolute left-0 right-0 top-1/2 -translate-y-1/2 transition-all duration-100 ${
                isDragging ? 'h-1 opacity-90' : (isEntryLine ? 'h-0.5 opacity-40 group-hover:opacity-70 group-hover:h-1' : 'h-1 opacity-0 group-hover:opacity-80')
              }`}
              style={{
                backgroundColor: lineDisplayColor,
                boxShadow: isDragging ? `0 0 12px ${lineDisplayColor}` : `0 0 6px ${lineDisplayColor}`,
              }}
            />

            {/* Label de preço - aparece no hover */}
            <div
              className={`absolute right-2 top-1/2 -translate-y-1/2 text-xs font-mono px-2 py-0.5 rounded transition-opacity flex items-center gap-1 ${
                isDragging ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
              } ${isEntryLine ? 'font-bold' : ''}`}
              style={{
                backgroundColor: lineDisplayColor,
                color: 'white'
              }}
            >
              {isDragging && showDragPreview && isEntryLine ? (
                <>
                  {dragLabel} ${candlestickSeriesRef.current?.coordinateToPrice(line.y)?.toFixed(2) || line.price.toFixed(2)}
                </>
              ) : (
                <>${line.price.toFixed(2)}</>
              )}

              {/* Botão X para cancelar ordem SL/TP (não aparece na linha de entrada) */}
              {!isEntryLine && !isDragging && onCancelOrder && (
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    console.log('🗑️ Clicou no X para cancelar:', line.type, 'positionId:', line.positionId)
                    onCancelOrder(line.positionId, line.type as 'stopLoss' | 'takeProfit')
                  }}
                  onMouseDown={(e) => e.stopPropagation()}
                  className="ml-2 w-5 h-5 flex items-center justify-center rounded-full bg-red-500/80 hover:bg-red-600 transition-colors cursor-pointer"
                  title={`Cancelar ${line.type === 'stopLoss' ? 'Stop Loss' : 'Take Profit'}`}
                >
                  <span className="text-[11px] font-bold text-white">×</span>
                </button>
              )}
            </div>

            {/* Tooltip de instrução para linha de entrada (só quando não está arrastando) */}
            {isEntryLine && !isDragging && (
              <div
                className="absolute left-1/2 -translate-x-1/2 -top-8 text-[10px] font-medium px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap"
                style={{
                  backgroundColor: 'rgba(0,0,0,0.9)',
                  color: '#9CA3AF',
                  border: '1px solid #4B5563'
                }}
              >
                ↑ {line.side === 'LONG' ? 'TP' : 'SL'} | ↓ {line.side === 'LONG' ? 'SL' : 'TP'}
              </div>
            )}

            {/* Preview grande quando arrastando */}
            {isDragging && showDragPreview && isEntryLine && (
              <div
                className="absolute left-1/2 -translate-x-1/2 -top-10 text-sm font-bold px-3 py-1.5 rounded shadow-lg animate-pulse whitespace-nowrap"
                style={{
                  backgroundColor: dragColor,
                  color: 'white',
                  boxShadow: `0 0 20px ${dragColor}`
                }}
              >
                {dragLabel === 'TP' ? '🎯' : '🛑'} Criar {dragLabel}
              </div>
            )}
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