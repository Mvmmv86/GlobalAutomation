/**
 * CanvasProChart - FASES 9 & 10: Sistema Completo de Indicadores
 * Layer 1: Background (grid) - renderiza menos frequentemente
 * Layer 2: Candles - renderiza em tempo real
 * Layer 3: Indicators - renderiza indicadores técnicos
 * Layer 4: Crosshair - renderiza no mousemove
 * + Zoom com scroll do mouse
 * + Pan com drag do mouse
 * + Crosshair seguindo o mouse
 * + Tooltip com info do candle
 * + 25+ Indicadores Técnicos Profissionais
 * + Painéis separados para osciladores
 * + Indicadores overlay avançados (VWAP, PSAR, Ichimoku, ADX)
 */

import React, { useRef, useEffect, useState, useCallback } from 'react'
import {
  SMA, EMA, WMA, BollingerBands, VWAP, PSAR, IchimokuCloud,
  ADX, TRIX, KeltnerChannels
} from 'technicalindicators'
import type { AnyIndicatorConfig } from './indicators/types'
import { SeparatePanel } from './components/SeparatePanel'

// VWMA custom implementation (not available in technicalindicators)
const calculateVWMA = (prices: number[], volumes: number[], period: number): number[] => {
  const result: number[] = []

  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) {
      result.push(NaN)
      continue
    }

    let sumPriceVolume = 0
    let sumVolume = 0

    for (let j = 0; j < period; j++) {
      const idx = i - j
      sumPriceVolume += prices[idx] * volumes[idx]
      sumVolume += volumes[idx]
    }

    result.push(sumVolume > 0 ? sumPriceVolume / sumVolume : NaN)
  }

  return result
}

export interface CanvasProChartMinimalProps {
  symbol: string
  interval: string
  theme?: 'dark' | 'light'
  candles?: any[]
  width?: string
  height?: string
  className?: string
  /** Intervalo de atualização em ms (default: 5000 = 5s) */
  refreshInterval?: number
  /** Indicadores ativos para renderizar */
  activeIndicators?: AnyIndicatorConfig[]
  /** Posições abertas (para mostrar entry price) */
  positions?: any[]
  /** Stop Loss price - linha vermelha draggable */
  stopLoss?: number | null
  /** Take Profit price - linha verde draggable */
  takeProfit?: number | null
  /** Position ID para callback de drag */
  positionId?: string
  /** Callback quando SL/TP é arrastado */
  onSLTPDrag?: (positionId: string, type: 'stopLoss' | 'takeProfit', newPrice: number) => void
}

// Configurações de zoom - Estilo TradingView
const ZOOM_CONFIG = {
  min: 0.1,      // Zoom mínimo - ver MUITOS candles
  max: 50,       // Zoom máximo - ver POUCOS candles com MUITO detalhe (TradingView level)
  step: 0.15,    // Incremento de zoom por scroll (mais sensível)
  default: 1     // Zoom inicial
}

// Cores do tema (extraído para reutilização)
const getThemeColors = (theme: 'dark' | 'light') => theme === 'dark' ? {
  background: '#131722',
  grid: '#1e222d',
  text: '#787b86',
  bullish: '#26a69a',
  bearish: '#ef5350'
} : {
  background: '#ffffff',
  grid: '#e0e3eb',
  text: '#787b86',
  bullish: '#26a69a',
  bearish: '#ef5350'
}

// Formatação dinâmica do eixo X baseada no intervalo
const getTimeAxisFormat = (interval: string) => {
  // Timeframes intraday: mostrar hora:minuto + data curta
  // Timeframes diários+: mostrar data mais completa
  switch (interval) {
    case '1':
    case '3':
    case '5':
    case '15':
    case '30':
      // Intraday curto: "14:30" + "21 Nov"
      return {
        primary: (date: Date) => date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        secondary: (date: Date) => date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
      }
    case '60':
    case '120':
    case '240':
    case '360':
    case '480':
    case '720':
      // Intraday longo: "14:00" + "21 Nov 24"
      return {
        primary: (date: Date) => date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        secondary: (date: Date) => date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: '2-digit' })
      }
    case '1D':
      // Diário: "21 Nov" + "2024"
      return {
        primary: (date: Date) => date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }),
        secondary: (date: Date) => date.getFullYear().toString()
      }
    case '3D':
    case '1W':
      // Semanal: "21 Nov 24"
      return {
        primary: (date: Date) => date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: '2-digit' }),
        secondary: () => ''
      }
    case '1M':
      // Mensal: "Nov 2024"
      return {
        primary: (date: Date) => date.toLocaleDateString('pt-BR', { month: 'short', year: 'numeric' }),
        secondary: () => ''
      }
    default:
      return {
        primary: (date: Date) => date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        secondary: (date: Date) => date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
      }
  }
}

const CanvasProChartMinimal: React.FC<CanvasProChartMinimalProps> = ({
  symbol,
  interval,
  theme = 'dark',
  candles = [],
  width = '100%',
  height = '600px',
  className = '',
  activeIndicators = [],
  positions = [],
  stopLoss = null,
  takeProfit = null,
  positionId = '',
  onSLTPDrag
}) => {
  // Layer 1: Background (grid) - renderiza menos frequentemente
  const backgroundCanvasRef = useRef<HTMLCanvasElement>(null)
  // Layer 2: Candles - renderiza em tempo real
  const candlesCanvasRef = useRef<HTMLCanvasElement>(null)
  // Layer 3: Indicators - renderiza indicadores técnicos
  const indicatorsCanvasRef = useRef<HTMLCanvasElement>(null)
  // Layer 4: Crosshair - renderiza no mousemove
  const crosshairCanvasRef = useRef<HTMLCanvasElement>(null)
  // Layer 5: SL/TP Lines - linhas draggable de Stop Loss e Take Profit
  const sltpCanvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

  // ========== FASE 6: Estado de Viewport (Zoom e Pan) ==========
  const [viewport, setViewport] = useState({
    zoom: ZOOM_CONFIG.default,
    offsetX: 0,  // Offset horizontal em pixels (para pan)
    offsetY: 0   // Offset vertical em pixels (para pan de preço)
  })

  // Estado para drag (pan)
  const isDraggingRef = useRef(false)
  const lastMousePosRef = useRef({ x: 0, y: 0 })

  // ========== FASE 7: Estado para Crosshair e Tooltip ==========
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null)
  const [hoveredCandle, setHoveredCandle] = useState<any | null>(null)

  // ========== FASE 11: Estado para SL/TP Drag ==========
  const [draggingSLTP, setDraggingSLTP] = useState<'stopLoss' | 'takeProfit' | null>(null)
  const [hoveringSLTP, setHoveringSLTP] = useState<'stopLoss' | 'takeProfit' | null>(null)
  const [dragPrice, setDragPrice] = useState<number | null>(null)
  const dragStartPriceRef = useRef<number | null>(null)

  // Debug: log no início do componente
  console.log('🚀 [CanvasProMinimal] Componente renderizado:', {
    symbol,
    interval,
    candlesCount: candles.length,
    dimensions,
    viewport
  })

  // Obter dimensões do container
  useEffect(() => {
    if (!containerRef.current) return

    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({ width: rect.width, height: rect.height })
      }
    }

    updateDimensions()

    const resizeObserver = new ResizeObserver(updateDimensions)
    resizeObserver.observe(containerRef.current)

    return () => resizeObserver.disconnect()
  }, [])

  // Calcular dados do gráfico (memoizado) - AUTO-SCALE baseado em candles VISÍVEIS
  const chartData = React.useMemo(() => {
    if (candles.length === 0 || dimensions.width === 0) return null

    // Calcular quais candles estão visíveis baseado no zoom e offsetX
    const { chartLeft, chartRight } = {
      chartLeft: 10,
      chartRight: dimensions.width - 70
    }
    const chartWidth = chartRight - chartLeft
    const baseWidth = chartWidth / candles.length
    const zoomedWidth = baseWidth * viewport.zoom

    // Determinar range de candles visíveis
    const startIndex = Math.max(0, Math.floor(-viewport.offsetX / zoomedWidth))
    const visibleCandleCount = Math.ceil(chartWidth / zoomedWidth)
    const endIndex = Math.min(candles.length, startIndex + visibleCandleCount + 2)

    // Calcular min/max APENAS dos candles visíveis (AUTO-SCALE)
    let priceMin = Infinity
    let priceMax = -Infinity
    for (let i = startIndex; i < endIndex; i++) {
      const c = candles[i]
      const low = parseFloat(c.low || c.l || 0)
      const high = parseFloat(c.high || c.h || 0)
      if (low < priceMin) priceMin = low
      if (high > priceMax) priceMax = high
    }

    // Padding adaptativo - menor padding em zooms maiores
    const paddingPercent = Math.max(0.02, 0.1 / viewport.zoom)
    const pricePadding = (priceMax - priceMin) * paddingPercent
    priceMin -= pricePadding
    priceMax += pricePadding

    const firstCandle = candles[0]
    const lastCandle = candles[candles.length - 1]
    const timeStart = firstCandle?.time || firstCandle?.openTime || firstCandle?.t || 0
    const timeEnd = lastCandle?.time || lastCandle?.openTime || lastCandle?.t || 0

    return {
      priceMin,
      priceMax,
      priceRange: priceMax - priceMin,
      timeStart,
      timeEnd,
      timeRange: timeEnd - timeStart,
      visibleRange: { startIndex, endIndex, count: endIndex - startIndex }
    }
  }, [candles, viewport.zoom, viewport.offsetX, dimensions.width])

  // Chart área constants
  const getChartArea = useCallback(() => ({
    chartLeft: 10,
    chartRight: dimensions.width - 70,
    chartTop: 10,
    chartBottom: dimensions.height - 50,
    chartWidth: dimensions.width - 80,
    chartHeight: dimensions.height - 60
  }), [dimensions])

  // ========== LAYER 1: BACKGROUND (Grid) ==========
  // Renderiza apenas quando: dimensões mudam, tema muda, ou range de dados muda significativamente
  useEffect(() => {
    const canvas = backgroundCanvasRef.current
    if (!canvas || dimensions.width === 0 || dimensions.height === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = dimensions.width * dpr
    canvas.height = dimensions.height * dpr
    ctx.scale(dpr, dpr)

    const colors = getThemeColors(theme)
    const { chartLeft, chartRight, chartTop, chartBottom, chartWidth, chartHeight } = getChartArea()

    // Limpar e preencher background
    ctx.fillStyle = colors.background
    ctx.fillRect(0, 0, dimensions.width, dimensions.height)

    if (!chartData) {
      ctx.fillStyle = colors.text
      ctx.font = '14px Arial'
      ctx.textAlign = 'center'
      ctx.fillText('Carregando candles...', dimensions.width / 2, dimensions.height / 2)
      return
    }

    const { priceMin, priceMax, priceRange, timeStart, timeEnd, timeRange } = chartData
    const { zoom, offsetX, offsetY } = viewport

    // Calcular range visível ajustado pelo viewport
    const visiblePriceRange = priceRange / zoom
    const visiblePriceMin = priceMin - (offsetY / chartHeight) * priceRange
    const visiblePriceMax = visiblePriceMin + visiblePriceRange

    // ========== GRID HORIZONTAL (preços) - DINÂMICO ==========
    ctx.strokeStyle = colors.grid
    ctx.lineWidth = 1

    // Calcular número ideal de linhas baseado no priceRange e altura
    // Objetivo: ~50-80px entre linhas de preço
    const targetSpacing = 60
    const idealGridLines = Math.max(4, Math.min(12, Math.floor(chartHeight / targetSpacing)))
    const gridLinesY = idealGridLines

    for (let i = 0; i <= gridLinesY; i++) {
      const y = chartTop + (chartHeight / gridLinesY) * i

      ctx.beginPath()
      ctx.setLineDash([2, 3])
      ctx.moveTo(chartLeft, y)
      ctx.lineTo(chartRight, y)
      ctx.stroke()
      ctx.setLineDash([])

      // Preço ajustado pelo offset vertical
      const price = priceMax - (priceRange / gridLinesY) * i - (offsetY / chartHeight) * priceRange
      ctx.fillStyle = colors.text
      ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      ctx.textAlign = 'left'

      // Determinar casas decimais baseado no priceRange (mais zoom = mais casas)
      const decimals = priceRange < 1 ? 4 : priceRange < 10 ? 3 : 2
      ctx.fillText(price.toFixed(decimals), chartRight + 5, y + 3)
    }

    // ========== GRID VERTICAL (tempo) - Ajustado pelo zoom e pan ==========
    // Calcular range de tempo visível
    const visibleTimeRange = timeRange / zoom
    const visibleTimeStart = timeStart - (offsetX / chartWidth) * visibleTimeRange

    // Obter formatadores dinâmicos baseados no intervalo
    const timeFormat = getTimeAxisFormat(interval)

    const gridLinesX = 6
    for (let i = 0; i <= gridLinesX; i++) {
      const x = chartLeft + (chartWidth / gridLinesX) * i

      ctx.strokeStyle = colors.grid
      ctx.beginPath()
      ctx.setLineDash([2, 3])
      ctx.moveTo(x, chartTop)
      ctx.lineTo(x, chartBottom)
      ctx.stroke()
      ctx.setLineDash([])

      // Timestamp ajustado pelo zoom e offset horizontal
      // useCandles já converte timestamps para MS - usar diretamente
      const timestamp = visibleTimeStart + (visibleTimeRange / gridLinesX) * i
      const date = new Date(timestamp)

      // Usar formatação dinâmica baseada no intervalo
      const primaryLabel = timeFormat.primary(date)
      const secondaryLabel = timeFormat.secondary(date)

      ctx.fillStyle = colors.text
      ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(primaryLabel, x, chartBottom + 14)
      if (secondaryLabel) {
        ctx.font = '9px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        ctx.fillText(secondaryLabel, x, chartBottom + 26)
      }
    }

    console.log('🎨 [Layer1-Background] Grid renderizado')
  }, [dimensions, theme, chartData, getChartArea, viewport, interval])

  // ========== LAYER 2: CANDLES ==========
  // Renderiza sempre que os candles mudam (para real-time updates)
  useEffect(() => {
    const canvas = candlesCanvasRef.current
    if (!canvas || dimensions.width === 0 || dimensions.height === 0 || !chartData) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = dimensions.width * dpr
    canvas.height = dimensions.height * dpr
    ctx.scale(dpr, dpr)

    // Limpar apenas o layer de candles (transparente)
    ctx.clearRect(0, 0, dimensions.width, dimensions.height)

    const colors = getThemeColors(theme)
    const { chartLeft, chartTop, chartWidth, chartHeight } = getChartArea()
    const { priceMax, priceRange } = chartData

    // ========== APLICAR ZOOM E PAN ==========
    const { zoom, offsetX, offsetY } = viewport

    // Calcular largura dos candles COM ZOOM
    const candleCount = candles.length
    const baseWidth = chartWidth / candleCount
    const zoomedWidth = baseWidth * zoom
    const candleWidth = Math.max(2, Math.min(20, zoomedWidth * 0.7)) // Ajustado para zoom
    const candleSpacing = zoomedWidth

    // Renderizar cada candle COM OFFSET
    candles.forEach((candle, index) => {
      const open = parseFloat(candle.open || candle.o || 0)
      const high = parseFloat(candle.high || candle.h || 0)
      const low = parseFloat(candle.low || candle.l || 0)
      const close = parseFloat(candle.close || candle.c || 0)

      // Posição X com zoom e pan horizontal
      const x = chartLeft + index * candleSpacing + candleSpacing / 2 + offsetX

      // Pular candles fora da área visível (otimização)
      if (x < chartLeft - candleWidth || x > chartLeft + chartWidth + candleWidth) {
        return
      }

      const isBullish = close >= open

      // Posições Y com pan vertical
      const yHigh = chartTop + ((priceMax - high) / priceRange) * chartHeight + offsetY
      const yLow = chartTop + ((priceMax - low) / priceRange) * chartHeight + offsetY
      const yOpen = chartTop + ((priceMax - open) / priceRange) * chartHeight + offsetY
      const yClose = chartTop + ((priceMax - close) / priceRange) * chartHeight + offsetY

      const color = isBullish ? colors.bullish : colors.bearish

      // Desenhar wick (pavio)
      ctx.strokeStyle = color
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, yHigh)
      ctx.lineTo(x, yLow)
      ctx.stroke()

      // Desenhar body (corpo)
      const bodyTop = Math.min(yOpen, yClose)
      const bodyHeight = Math.max(1, Math.abs(yClose - yOpen))

      ctx.fillStyle = color
      ctx.fillRect(x - candleWidth / 2, bodyTop, candleWidth, bodyHeight)
    })

    // ========== INDICADOR DE PREÇO ATUAL (última linha horizontal) ==========
    if (candles.length > 0) {
      const lastCandle = candles[candles.length - 1]
      const lastClose = parseFloat(lastCandle.close || lastCandle.c || 0)
      const yLastPrice = chartTop + ((priceMax - lastClose) / priceRange) * chartHeight + offsetY

      // Só mostra se estiver na área visível
      if (yLastPrice >= chartTop && yLastPrice <= chartTop + chartHeight) {
        // Linha pontilhada do preço atual
        ctx.strokeStyle = lastCandle.close >= lastCandle.open ? colors.bullish : colors.bearish
        ctx.lineWidth = 1
        ctx.setLineDash([4, 4])
        ctx.beginPath()
        ctx.moveTo(chartLeft, yLastPrice)
        ctx.lineTo(chartLeft + chartWidth, yLastPrice)
        ctx.stroke()
        ctx.setLineDash([])

        // Label do preço atual (destaque)
        const priceLabel = lastClose.toFixed(2)
        ctx.fillStyle = lastCandle.close >= lastCandle.open ? colors.bullish : colors.bearish
        ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        ctx.textAlign = 'left'

        // Background do label
        const labelWidth = ctx.measureText(priceLabel).width + 8
        ctx.fillRect(chartLeft + chartWidth + 2, yLastPrice - 8, labelWidth, 16)

        // Texto do preço
        ctx.fillStyle = '#ffffff'
        ctx.fillText(priceLabel, chartLeft + chartWidth + 6, yLastPrice + 4)
      }
    }

    console.log(`🕯️ [Layer2-Candles] ${candles.length} candles renderizados (zoom: ${viewport.zoom.toFixed(2)})`)
  }, [candles, dimensions, theme, chartData, getChartArea, viewport])

  // ========== LAYER 3: INDICATORS ==========
  // Renderiza indicadores técnicos (SMA, EMA, Bollinger Bands, etc)
  useEffect(() => {
    const canvas = indicatorsCanvasRef.current
    if (!canvas || dimensions.width === 0 || dimensions.height === 0 || !chartData) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = dimensions.width * dpr
    canvas.height = dimensions.height * dpr
    ctx.scale(dpr, dpr)

    // Limpar canvas de indicadores
    ctx.clearRect(0, 0, dimensions.width, dimensions.height)

    // Filtrar apenas indicadores overlay habilitados
    const overlayIndicators = activeIndicators.filter(
      ind => ind.enabled && ind.displayType === 'overlay'
    )

    if (overlayIndicators.length === 0 || candles.length < 20) {
      return // Precisamos de pelo menos 20 candles para indicadores
    }

    const colors = getThemeColors(theme)
    const { chartLeft, chartTop, chartWidth, chartHeight } = getChartArea()
    const { priceMax, priceRange } = chartData
    const { zoom, offsetX, offsetY } = viewport

    // Preparar dados dos candles para indicadores
    const closePrices = candles.map(c => parseFloat(c.close || c.c || 0))
    const highPrices = candles.map(c => parseFloat(c.high || c.h || 0))
    const lowPrices = candles.map(c => parseFloat(c.low || c.l || 0))
    const volumes = candles.map(c => parseFloat(c.volume || c.v || 0))

    // Calcular largura dos candles COM ZOOM (mesmo cálculo da Layer 2)
    const candleCount = candles.length
    const baseWidth = chartWidth / candleCount
    const zoomedWidth = baseWidth * zoom
    const candleSpacing = zoomedWidth

    // Renderizar cada indicador
    overlayIndicators.forEach(indicator => {
      try {
        let values: number[] | null = null

        // Calcular indicador baseado no tipo
        switch (indicator.type) {
          case 'SMA': {
            const period = (indicator.params as any).period || 20
            values = SMA.calculate({ period, values: closePrices })
            break
          }
          case 'EMA': {
            const period = (indicator.params as any).period || 20
            values = EMA.calculate({ period, values: closePrices })
            break
          }
          case 'WMA': {
            const period = (indicator.params as any).period || 20
            values = WMA.calculate({ period, values: closePrices })
            break
          }
          case 'VWMA': {
            const period = (indicator.params as any).period || 20
            values = calculateVWMA(closePrices, volumes, period)
            break
          }
          case 'VWAP': {
            // VWAP precisa de high, low, close e volume
            const vwapResult = VWAP.calculate({
              high: highPrices,
              low: lowPrices,
              close: closePrices,
              volume: volumes
            })
            values = vwapResult
            break
          }
          case 'PSAR': {
            // Parabolic SAR
            const step = (indicator.params as any).step || 0.02
            const max = (indicator.params as any).max || 0.2
            const psarResult = PSAR.calculate({
              high: highPrices,
              low: lowPrices,
              step,
              max
            })
            values = psarResult
            break
          }
          case 'TRIX': {
            const period = (indicator.params as any).period || 18
            values = TRIX.calculate({ period, values: closePrices })
            break
          }
          case 'KC': {
            // Keltner Channels
            const period = (indicator.params as any).period || 20
            const multiplier = (indicator.params as any).multiplier || 2
            const kcResult = KeltnerChannels.calculate({
              high: highPrices,
              low: lowPrices,
              close: closePrices,
              period,
              atrPeriod: period,
              multiplier
            })

            if (kcResult && kcResult.length > 0) {
              // Renderizar 3 linhas: upper, middle, lower (similar ao BB)
              ctx.strokeStyle = indicator.color
              ctx.globalAlpha = 0.6
              ctx.lineWidth = indicator.lineWidth || 1

              // Upper Band
              ctx.beginPath()
              kcResult.forEach((kc, i) => {
                if (!kc || !kc.upper) return
                const actualIndex = i + (closePrices.length - kcResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - kc.upper) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              // Middle Line
              ctx.beginPath()
              kcResult.forEach((kc, i) => {
                if (!kc || !kc.middle) return
                const actualIndex = i + (closePrices.length - kcResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - kc.middle) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              // Lower Band
              ctx.beginPath()
              kcResult.forEach((kc, i) => {
                if (!kc || !kc.lower) return
                const actualIndex = i + (closePrices.length - kcResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - kc.lower) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()
              ctx.globalAlpha = 1
            }
            return // Já renderizamos KC, pular renderização de values abaixo
          }
          case 'ICHIMOKU': {
            // Ichimoku Cloud
            const conversionPeriod = (indicator.params as any).conversionPeriod || 9
            const basePeriod = (indicator.params as any).basePeriod || 26
            const spanPeriod = (indicator.params as any).spanPeriod || 52
            const displacement = (indicator.params as any).displacement || 26

            const ichimokuResult = IchimokuCloud.calculate({
              high: highPrices,
              low: lowPrices,
              conversionPeriod,
              basePeriod,
              spanPeriod,
              displacement
            })

            if (ichimokuResult && ichimokuResult.length > 0) {
              ctx.globalAlpha = 0.5

              // Conversion Line (Tenkan-sen) - vermelho
              ctx.strokeStyle = '#f23645'
              ctx.lineWidth = 1
              ctx.beginPath()
              ichimokuResult.forEach((ich, i) => {
                if (!ich || !ich.conversion) return
                const actualIndex = i + (closePrices.length - ichimokuResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - ich.conversion) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              // Base Line (Kijun-sen) - azul
              ctx.strokeStyle = '#2962ff'
              ctx.beginPath()
              ichimokuResult.forEach((ich, i) => {
                if (!ich || !ich.base) return
                const actualIndex = i + (closePrices.length - ichimokuResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - ich.base) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              // Leading Span A (Senkou Span A) - verde
              ctx.strokeStyle = '#43a047'
              ctx.beginPath()
              ichimokuResult.forEach((ich, i) => {
                if (!ich || !ich.spanA) return
                const actualIndex = i + (closePrices.length - ichimokuResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - ich.spanA) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              // Leading Span B (Senkou Span B) - vermelho escuro
              ctx.strokeStyle = '#e53935'
              ctx.beginPath()
              ichimokuResult.forEach((ich, i) => {
                if (!ich || !ich.spanB) return
                const actualIndex = i + (closePrices.length - ichimokuResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - ich.spanB) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              ctx.globalAlpha = 1
            }
            return // Já renderizamos Ichimoku
          }
          case 'BB': {
            const period = (indicator.params as any).period || 20
            const stdDev = (indicator.params as any).stdDev || 2
            const bbResult = BollingerBands.calculate({
              period,
              values: closePrices,
              stdDev
            })

            if (bbResult && bbResult.length > 0) {
              // Renderizar 3 linhas: upper, middle, lower
              ctx.strokeStyle = indicator.color
              ctx.globalAlpha = 0.6
              ctx.lineWidth = indicator.lineWidth || 1

              // Upper Band
              ctx.beginPath()
              bbResult.forEach((bb, i) => {
                if (!bb || !bb.upper) return
                const actualIndex = i + (closePrices.length - bbResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - bb.upper) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              // Middle Band
              ctx.beginPath()
              bbResult.forEach((bb, i) => {
                if (!bb || !bb.middle) return
                const actualIndex = i + (closePrices.length - bbResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - bb.middle) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()

              // Lower Band
              ctx.beginPath()
              bbResult.forEach((bb, i) => {
                if (!bb || !bb.lower) return
                const actualIndex = i + (closePrices.length - bbResult.length)
                const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
                const y = chartTop + ((priceMax - bb.lower) / priceRange) * chartHeight + offsetY

                if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
                  if (i === 0) ctx.moveTo(x, y)
                  else ctx.lineTo(x, y)
                }
              })
              ctx.stroke()
              ctx.globalAlpha = 1
            }
            return // Já renderizamos BB, pular renderização de values abaixo
          }
        }

        // Renderizar linha do indicador (para SMA, EMA, WMA, etc)
        if (values && values.length > 0) {
          ctx.strokeStyle = indicator.color
          ctx.lineWidth = indicator.lineWidth || 2
          ctx.globalAlpha = 0.8

          ctx.beginPath()
          values.forEach((value, i) => {
            if (!value || isNaN(value)) return

            // Ajustar índice (indicadores retornam menos valores que candles)
            const actualIndex = i + (closePrices.length - values!.length)
            const x = chartLeft + actualIndex * candleSpacing + candleSpacing / 2 + offsetX
            const y = chartTop + ((priceMax - value) / priceRange) * chartHeight + offsetY

            // Só desenhar se estiver na área visível
            if (x >= chartLeft - candleSpacing && x <= chartLeft + chartWidth + candleSpacing) {
              if (i === 0) {
                ctx.moveTo(x, y)
              } else {
                ctx.lineTo(x, y)
              }
            }
          })
          ctx.stroke()
          ctx.globalAlpha = 1
        }
      } catch (error) {
        console.error(`❌ Error calculating indicator ${indicator.type}:`, error)
      }
    })

    if (overlayIndicators.length > 0) {
      console.log(`📊 [Layer3-Indicators] ${overlayIndicators.length} indicadores renderizados`)
    }
  }, [candles, dimensions, theme, chartData, getChartArea, viewport, activeIndicators])

  // ========== FASE 6: Event Handlers para Zoom e Pan ==========

  // Handler de Zoom (scroll do mouse) - ZOOM NO PONTO DO MOUSE
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault()

    if (!containerRef.current || !chartData) return

    // Obter posição do mouse relativa ao container
    const rect = containerRef.current.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const { chartLeft, chartWidth } = getChartArea()

    // Posição do mouse relativa ao chart (0 = esquerda, 1 = direita)
    const mouseRatio = Math.max(0, Math.min(1, (mouseX - chartLeft) / chartWidth))

    const delta = e.deltaY > 0 ? -ZOOM_CONFIG.step : ZOOM_CONFIG.step

    setViewport(prev => {
      const newZoom = Math.max(ZOOM_CONFIG.min, Math.min(ZOOM_CONFIG.max, prev.zoom + delta))

      // CRITICAL: Ajustar offsetX para manter o ponto sob o mouse fixo
      // Fórmula: novo_offset = offset_antigo + (diferença_zoom * largura * posição_relativa_mouse)
      const zoomRatio = newZoom / prev.zoom
      const newOffsetX = prev.offsetX * zoomRatio + chartWidth * (1 - zoomRatio) * mouseRatio

      console.log(`🔍 [Zoom] ${prev.zoom.toFixed(2)} → ${newZoom.toFixed(2)} @ mouse ${(mouseRatio * 100).toFixed(0)}%`)

      return {
        ...prev,
        zoom: newZoom,
        offsetX: newOffsetX
      }
    })
  }, [chartData, getChartArea])

  // Handler de início do drag (pan ou SL/TP)
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return

    const y = e.clientY - rect.top

    // Verificar se está sobre uma linha SL/TP
    const sltpHover = checkSLTPHover(y)
    if (sltpHover && onSLTPDrag && positionId) {
      // Iniciar drag de SL/TP
      setDraggingSLTP(sltpHover)
      dragStartPriceRef.current = sltpHover === 'stopLoss' ? stopLoss : takeProfit
      setDragPrice(dragStartPriceRef.current)
      e.preventDefault()
      e.stopPropagation()
      console.log(`🎯 [SLTP Drag] Iniciando drag de ${sltpHover} @ ${dragStartPriceRef.current}`)
      return
    }

    // Se não está sobre SL/TP, iniciar pan normal
    isDraggingRef.current = true
    lastMousePosRef.current = { x: e.clientX, y: e.clientY }
    if (containerRef.current) {
      containerRef.current.style.cursor = 'grabbing'
    }
  }, [checkSLTPHover, onSLTPDrag, positionId, stopLoss, takeProfit])

  // Handler de movimento do mouse (pan ou SL/TP drag)
  const handleMouseMove = useCallback((e: MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return

    const y = e.clientY - rect.top

    // Se está arrastando SL/TP, atualizar o preço
    if (draggingSLTP) {
      const newPrice = yToPrice(y)
      setDragPrice(newPrice)
      return
    }

    // Pan normal
    if (!isDraggingRef.current) return

    const deltaX = e.clientX - lastMousePosRef.current.x
    const deltaY = e.clientY - lastMousePosRef.current.y
    lastMousePosRef.current = { x: e.clientX, y: e.clientY }

    setViewport(prev => ({
      ...prev,
      offsetX: prev.offsetX + deltaX,
      offsetY: prev.offsetY + deltaY
    }))
  }, [draggingSLTP, yToPrice])

  // Handler de fim do drag (pan ou SL/TP)
  const handleMouseUp = useCallback(() => {
    // Se estava arrastando SL/TP, finalizar e chamar callback
    if (draggingSLTP && dragPrice !== null && onSLTPDrag && positionId) {
      const type = draggingSLTP
      const newPrice = dragPrice
      const oldPrice = type === 'stopLoss' ? stopLoss : takeProfit

      // Só chamar callback se o preço mudou significativamente
      if (oldPrice !== null && Math.abs(newPrice - oldPrice) > 0.01) {
        console.log(`✅ [SLTP Drag] Finalizando ${type}: ${oldPrice} → ${newPrice}`)
        onSLTPDrag(positionId, type, newPrice)
      } else {
        console.log(`⚠️ [SLTP Drag] Preço não mudou significativamente, ignorando`)
      }

      // Reset estado de drag
      setDraggingSLTP(null)
      setDragPrice(null)
      dragStartPriceRef.current = null
      return
    }

    // Pan normal
    isDraggingRef.current = false
    if (containerRef.current) {
      containerRef.current.style.cursor = hoveringSLTP ? 'ns-resize' : 'crosshair'
    }
  }, [draggingSLTP, dragPrice, onSLTPDrag, positionId, stopLoss, takeProfit, hoveringSLTP])

  // Registrar event listeners
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Wheel para zoom
    container.addEventListener('wheel', handleWheel, { passive: false })

    // Mouse move e up no document (para continuar drag fora do container)
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      container.removeEventListener('wheel', handleWheel)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleWheel, handleMouseMove, handleMouseUp])

  // Reset viewport quando mudar de símbolo ou intervalo
  useEffect(() => {
    setViewport({
      zoom: ZOOM_CONFIG.default,
      offsetX: 0,
      offsetY: 0
    })
  }, [symbol, interval])

  // ========== FASE 7: Crosshair e Tooltip ==========

  // Handler para atualizar posição do mouse e encontrar candle
  const handleMouseMoveForCrosshair = useCallback((e: React.MouseEvent) => {
    if (isDraggingRef.current) return // Não mostrar crosshair durante drag pan
    if (draggingSLTP) return // Não mudar hover durante drag de SL/TP

    const rect = containerRef.current?.getBoundingClientRect()
    if (!rect) return

    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    setMousePos({ x, y })

    // Verificar hover sobre linhas SL/TP
    const sltpHover = checkSLTPHover(y)
    setHoveringSLTP(sltpHover)

    // Mudar cursor baseado no hover
    if (containerRef.current) {
      containerRef.current.style.cursor = sltpHover ? 'ns-resize' : 'crosshair'
    }

    // Encontrar candle sob o mouse
    if (candles.length > 0 && chartData) {
      const { chartLeft, chartWidth } = getChartArea()
      const { zoom, offsetX } = viewport

      const candleCount = candles.length
      const baseWidth = chartWidth / candleCount
      const zoomedWidth = baseWidth * zoom

      // Calcular índice do candle baseado na posição X
      const relativeX = x - chartLeft - offsetX
      const candleIndex = Math.floor(relativeX / zoomedWidth)

      if (candleIndex >= 0 && candleIndex < candles.length) {
        setHoveredCandle(candles[candleIndex])
      } else {
        setHoveredCandle(null)
      }
    }
  }, [candles, chartData, getChartArea, viewport, checkSLTPHover, draggingSLTP])

  // Handler para esconder crosshair quando mouse sai
  const handleMouseLeave = useCallback(() => {
    setMousePos(null)
    setHoveredCandle(null)
  }, [])

  // ========== LAYER 4: CROSSHAIR ==========
  useEffect(() => {
    const canvas = crosshairCanvasRef.current
    if (!canvas || dimensions.width === 0 || dimensions.height === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = dimensions.width * dpr
    canvas.height = dimensions.height * dpr
    ctx.scale(dpr, dpr)

    // Limpar canvas
    ctx.clearRect(0, 0, dimensions.width, dimensions.height)

    if (!mousePos || !chartData) return

    const colors = getThemeColors(theme)
    const { chartLeft, chartRight, chartTop, chartBottom, chartWidth, chartHeight } = getChartArea()
    const { priceMax, priceRange } = chartData
    const { offsetY } = viewport

    // Só desenhar se o mouse estiver na área do gráfico
    if (mousePos.x < chartLeft || mousePos.x > chartRight ||
        mousePos.y < chartTop || mousePos.y > chartBottom) {
      return
    }

    // Linha vertical (tempo)
    ctx.strokeStyle = '#555'
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(mousePos.x, chartTop)
    ctx.lineTo(mousePos.x, chartBottom)
    ctx.stroke()

    // Linha horizontal (preço)
    ctx.beginPath()
    ctx.moveTo(chartLeft, mousePos.y)
    ctx.lineTo(chartRight, mousePos.y)
    ctx.stroke()
    ctx.setLineDash([])

    // Calcular preço na posição do mouse
    const priceAtMouse = priceMax - ((mousePos.y - chartTop - offsetY) / chartHeight) * priceRange

    // Label de preço no eixo Y
    ctx.fillStyle = '#363a45'
    ctx.fillRect(chartRight + 2, mousePos.y - 10, 65, 20)
    ctx.fillStyle = '#ffffff'
    ctx.font = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(priceAtMouse.toFixed(2), chartRight + 5, mousePos.y + 4)

  }, [mousePos, dimensions, theme, chartData, getChartArea, viewport])

  // ========== LAYER 5: SL/TP LINES ==========
  // Renderiza linhas de Stop Loss (vermelha) e Take Profit (verde) draggable
  useEffect(() => {
    const canvas = sltpCanvasRef.current
    if (!canvas || dimensions.width === 0 || dimensions.height === 0 || !chartData) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = dimensions.width * dpr
    canvas.height = dimensions.height * dpr
    ctx.scale(dpr, dpr)

    // Limpar canvas
    ctx.clearRect(0, 0, dimensions.width, dimensions.height)

    const { chartLeft, chartRight, chartTop, chartHeight } = getChartArea()
    const { priceMax, priceRange } = chartData
    const { offsetY } = viewport

    // Função helper para desenhar linha SL/TP
    const drawSLTPLine = (price: number, color: string, label: string, isHovered: boolean, isDragging: boolean) => {
      const y = chartTop + ((priceMax - price) / priceRange) * chartHeight + offsetY

      // Só desenhar se estiver na área visível
      if (y < chartTop || y > chartTop + chartHeight) return

      // Linha principal
      ctx.strokeStyle = color
      ctx.lineWidth = isHovered || isDragging ? 2.5 : 1.5
      ctx.setLineDash(isDragging ? [8, 4] : [6, 3])
      ctx.beginPath()
      ctx.moveTo(chartLeft, y)
      ctx.lineTo(chartRight, y)
      ctx.stroke()
      ctx.setLineDash([])

      // Background do label
      const labelText = `${label}: ${price.toFixed(2)}`
      ctx.font = 'bold 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      const labelWidth = ctx.measureText(labelText).width + 12
      const labelHeight = 18
      const labelX = chartRight + 3
      const labelY = y - labelHeight / 2

      // Retângulo com borda arredondada
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.roundRect(labelX, labelY, labelWidth, labelHeight, 3)
      ctx.fill()

      // Texto do label
      ctx.fillStyle = '#ffffff'
      ctx.textAlign = 'left'
      ctx.fillText(labelText, labelX + 6, y + 4)

      // Indicador de drag (setas)
      if (isHovered || isDragging) {
        ctx.fillStyle = color
        ctx.globalAlpha = 0.8
        // Seta para cima
        ctx.beginPath()
        ctx.moveTo(chartLeft + 15, y - 8)
        ctx.lineTo(chartLeft + 20, y - 3)
        ctx.lineTo(chartLeft + 10, y - 3)
        ctx.closePath()
        ctx.fill()
        // Seta para baixo
        ctx.beginPath()
        ctx.moveTo(chartLeft + 15, y + 8)
        ctx.lineTo(chartLeft + 20, y + 3)
        ctx.lineTo(chartLeft + 10, y + 3)
        ctx.closePath()
        ctx.fill()
        ctx.globalAlpha = 1
      }
    }

    // Renderizar Stop Loss (linha vermelha)
    const slPrice = draggingSLTP === 'stopLoss' && dragPrice !== null ? dragPrice : stopLoss
    if (slPrice !== null && slPrice !== undefined) {
      drawSLTPLine(
        slPrice,
        '#ef5350', // Vermelho
        'SL',
        hoveringSLTP === 'stopLoss',
        draggingSLTP === 'stopLoss'
      )
    }

    // Renderizar Take Profit (linha verde)
    const tpPrice = draggingSLTP === 'takeProfit' && dragPrice !== null ? dragPrice : takeProfit
    if (tpPrice !== null && tpPrice !== undefined) {
      drawSLTPLine(
        tpPrice,
        '#26a69a', // Verde
        'TP',
        hoveringSLTP === 'takeProfit',
        draggingSLTP === 'takeProfit'
      )
    }

    if ((stopLoss || takeProfit) && !draggingSLTP) {
      console.log(`📍 [Layer5-SLTP] SL: ${stopLoss}, TP: ${takeProfit}`)
    }
  }, [stopLoss, takeProfit, dimensions, chartData, getChartArea, viewport, hoveringSLTP, draggingSLTP, dragPrice])

  // ========== HELPER: Verificar se mouse está sobre linha SL/TP ==========
  const checkSLTPHover = useCallback((mouseY: number): 'stopLoss' | 'takeProfit' | null => {
    if (!chartData) return null

    const { chartTop, chartHeight } = getChartArea()
    const { priceMax, priceRange } = chartData
    const { offsetY } = viewport
    const hitTolerance = 8 // Pixels de tolerância para hover

    // Verificar Stop Loss
    if (stopLoss !== null && stopLoss !== undefined) {
      const slY = chartTop + ((priceMax - stopLoss) / priceRange) * chartHeight + offsetY
      if (Math.abs(mouseY - slY) <= hitTolerance) {
        return 'stopLoss'
      }
    }

    // Verificar Take Profit
    if (takeProfit !== null && takeProfit !== undefined) {
      const tpY = chartTop + ((priceMax - takeProfit) / priceRange) * chartHeight + offsetY
      if (Math.abs(mouseY - tpY) <= hitTolerance) {
        return 'takeProfit'
      }
    }

    return null
  }, [chartData, getChartArea, viewport, stopLoss, takeProfit])

  // ========== HELPER: Converter Y para preço ==========
  const yToPrice = useCallback((y: number): number => {
    if (!chartData) return 0

    const { chartTop, chartHeight } = getChartArea()
    const { priceMax, priceRange } = chartData
    const { offsetY } = viewport

    return priceMax - ((y - chartTop - offsetY) / chartHeight) * priceRange
  }, [chartData, getChartArea, viewport])

  return (
    <div
      ref={containerRef}
      className={`canvas-pro-chart-minimal ${className}`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMoveForCrosshair}
      onMouseLeave={handleMouseLeave}
      style={{
        width,
        height,
        position: 'relative',
        overflow: 'hidden',
        cursor: 'crosshair'
      }}
    >
      {/* Layer 1: Background (grid, eixos) - z-index: 1 */}
      <canvas
        ref={backgroundCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 1
        }}
      />
      {/* Layer 2: Candles - z-index: 2 (por cima do background) */}
      <canvas
        ref={candlesCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 2
        }}
      />
      {/* Layer 3: Indicators - z-index: 3 (por cima dos candles) */}
      <canvas
        ref={indicatorsCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 3,
          pointerEvents: 'none' // Não bloqueia eventos do mouse
        }}
      />
      {/* Layer 4: Crosshair - z-index: 4 */}
      <canvas
        ref={crosshairCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 4,
          pointerEvents: 'none' // Não bloqueia eventos do mouse
        }}
      />
      {/* Layer 5: SL/TP Lines - z-index: 5 (por cima de tudo, draggable) */}
      <canvas
        ref={sltpCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 5,
          pointerEvents: 'none' // Eventos tratados pelo container
        }}
      />

      {/* Tooltip com info do candle */}
      {hoveredCandle && mousePos && (
        <div
          style={{
            position: 'absolute',
            left: mousePos.x + 15,
            top: mousePos.y - 80,
            backgroundColor: 'rgba(30, 34, 45, 0.95)',
            border: '1px solid #363a45',
            borderRadius: '4px',
            padding: '8px 12px',
            zIndex: 10,
            pointerEvents: 'none',
            fontSize: '11px',
            color: '#d1d4dc',
            minWidth: '140px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
          }}
        >
          <div style={{ marginBottom: '4px', color: '#787b86', fontSize: '10px' }}>
            {new Date(hoveredCandle.time || hoveredCandle.openTime || hoveredCandle.t).toLocaleString('pt-BR')}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
            <span style={{ color: '#787b86' }}>O:</span>
            <span>{parseFloat(hoveredCandle.open || hoveredCandle.o).toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
            <span style={{ color: '#787b86' }}>H:</span>
            <span style={{ color: '#26a69a' }}>{parseFloat(hoveredCandle.high || hoveredCandle.h).toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
            <span style={{ color: '#787b86' }}>L:</span>
            <span style={{ color: '#ef5350' }}>{parseFloat(hoveredCandle.low || hoveredCandle.l).toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#787b86' }}>C:</span>
            <span style={{
              color: parseFloat(hoveredCandle.close || hoveredCandle.c) >= parseFloat(hoveredCandle.open || hoveredCandle.o)
                ? '#26a69a' : '#ef5350'
            }}>
              {parseFloat(hoveredCandle.close || hoveredCandle.c).toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

CanvasProChartMinimal.displayName = 'CanvasProChartMinimal'

export default CanvasProChartMinimal
export { CanvasProChartMinimal }
