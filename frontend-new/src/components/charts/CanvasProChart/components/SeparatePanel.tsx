/**
 * SeparatePanel - Painel separado para indicadores (RSI, MACD, Stochastic, etc)
 * FASE 9: Painéis Separados
 * Renderiza indicadores em subchart independente abaixo do gráfico principal
 */

import React, { useRef, useEffect } from 'react'
import { RSI, MACD, Stochastic, ATR, ADX, CCI, MFI, OBV } from 'technicalindicators'
import type { AnyIndicatorConfig } from '../indicators/types'

interface SeparatePanelProps {
  /** Indicadores a renderizar neste painel */
  indicators: AnyIndicatorConfig[]
  /** Dados dos candles */
  candles: any[]
  /** Tema do gráfico */
  theme: 'dark' | 'light'
  /** Largura do painel */
  width: number
  /** Altura do painel */
  height: number
  /** Estado do viewport (zoom, pan) */
  viewport: {
    zoom: number
    offsetX: number
    offsetY: number
  }
  /** Índice do candle sob o mouse (para crosshair) */
  hoveredCandleIndex: number | null
  /** Posição do mouse */
  mousePos: { x: number; y: number } | null
}

// Margens do chart
const MARGIN = {
  top: 10,
  right: 60,
  bottom: 20,
  left: 10
}

const getThemeColors = (theme: 'dark' | 'light') => ({
  background: theme === 'dark' ? '#1e222d' : '#ffffff',
  grid: theme === 'dark' ? '#2a2e39' : '#e0e3eb',
  text: theme === 'dark' ? '#d1d4dc' : '#131722',
  bullish: '#26a69a',
  bearish: '#ef5350',
  crosshair: theme === 'dark' ? '#787b86' : '#9598a1'
})

export const SeparatePanel: React.FC<SeparatePanelProps> = ({
  indicators,
  candles,
  theme,
  width,
  height,
  viewport,
  hoveredCandleIndex,
  mousePos
}) => {
  const backgroundCanvasRef = useRef<HTMLCanvasElement>(null)
  const indicatorCanvasRef = useRef<HTMLCanvasElement>(null)
  const crosshairCanvasRef = useRef<HTMLCanvasElement>(null)

  const colors = getThemeColors(theme)

  // ========== LAYER 1: BACKGROUND (Grid + Axes) ==========
  useEffect(() => {
    const canvas = backgroundCanvasRef.current
    if (!canvas || width === 0 || height === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    // Limpar
    ctx.fillStyle = colors.background
    ctx.fillRect(0, 0, width, height)

    const chartWidth = width - MARGIN.left - MARGIN.right
    const chartHeight = height - MARGIN.top - MARGIN.bottom

    // Grid horizontal
    ctx.strokeStyle = colors.grid
    ctx.lineWidth = 1
    const horizontalLines = 3
    for (let i = 0; i <= horizontalLines; i++) {
      const y = MARGIN.top + (chartHeight / horizontalLines) * i
      ctx.beginPath()
      ctx.moveTo(MARGIN.left, y)
      ctx.lineTo(MARGIN.left + chartWidth, y)
      ctx.stroke()
    }

    // Bordas
    ctx.strokeStyle = colors.grid
    ctx.strokeRect(MARGIN.left, MARGIN.top, chartWidth, chartHeight)

  }, [width, height, theme, colors])

  // ========== LAYER 2: INDICATORS ==========
  useEffect(() => {
    const canvas = indicatorCanvasRef.current
    if (!canvas || width === 0 || height === 0 || candles.length < 20) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    // Limpar
    ctx.clearRect(0, 0, width, height)

    const chartWidth = width - MARGIN.left - MARGIN.right
    const chartHeight = height - MARGIN.top - MARGIN.bottom
    const { zoom, offsetX } = viewport

    // Preparar dados
    const closePrices = candles.map(c => parseFloat(c.close || c.c || 0))
    const highPrices = candles.map(c => parseFloat(c.high || c.h || 0))
    const lowPrices = candles.map(c => parseFloat(c.low || c.l || 0))
    const volumes = candles.map(c => parseFloat(c.volume || c.v || 0))

    // Calcular largura dos candles COM ZOOM
    const candleCount = candles.length
    const baseWidth = chartWidth / candleCount
    const zoomedWidth = baseWidth * zoom
    const candleSpacing = zoomedWidth

    // Renderizar cada indicador
    indicators.forEach(indicator => {
      if (!indicator.enabled) return

      try {
        let values: any[] = []
        let minValue = 0
        let maxValue = 100

        // Calcular indicador baseado no tipo
        switch (indicator.type) {
          case 'RSI': {
            const period = (indicator.params as any).period || 14
            values = RSI.calculate({ period, values: closePrices })
            minValue = 0
            maxValue = 100
            break
          }

          case 'MACD': {
            const fast = (indicator.params as any).fastPeriod || 12
            const slow = (indicator.params as any).slowPeriod || 26
            const signal = (indicator.params as any).signalPeriod || 9
            values = MACD.calculate({
              values: closePrices,
              fastPeriod: fast,
              slowPeriod: slow,
              signalPeriod: signal,
              SimpleMAOscillator: false,
              SimpleMASignal: false
            })
            // MACD pode ter valores positivos e negativos
            const macdValues = values.map(v => v.MACD || 0)
            minValue = Math.min(...macdValues) * 1.1
            maxValue = Math.max(...macdValues) * 1.1
            break
          }

          case 'STOCH': {
            const period = (indicator.params as any).period || 14
            const signalPeriod = (indicator.params as any).signalPeriod || 3
            values = Stochastic.calculate({
              high: highPrices,
              low: lowPrices,
              close: closePrices,
              period,
              signalPeriod
            })
            minValue = 0
            maxValue = 100
            break
          }

          case 'ATR': {
            const period = (indicator.params as any).period || 14
            const atrInput = candles.map(c => ({
              high: parseFloat(c.high || c.h || 0),
              low: parseFloat(c.low || c.l || 0),
              close: parseFloat(c.close || c.c || 0)
            }))
            values = ATR.calculate({ period, high: highPrices, low: lowPrices, close: closePrices })
            const atrValues = values.filter(v => v)
            minValue = 0
            maxValue = Math.max(...atrValues) * 1.1
            break
          }

          case 'CCI': {
            const period = (indicator.params as any).period || 20
            values = CCI.calculate({
              high: highPrices,
              low: lowPrices,
              close: closePrices,
              period
            })
            const cciValues = values.filter(v => v)
            minValue = Math.min(...cciValues) * 1.1
            maxValue = Math.max(...cciValues) * 1.1
            break
          }

          case 'MFI': {
            const period = (indicator.params as any).period || 14
            values = MFI.calculate({
              high: highPrices,
              low: lowPrices,
              close: closePrices,
              volume: volumes,
              period
            })
            minValue = 0
            maxValue = 100
            break
          }

          case 'OBV': {
            values = OBV.calculate({ close: closePrices, volume: volumes })
            const obvValues = values.filter(v => v)
            minValue = Math.min(...obvValues)
            maxValue = Math.max(...obvValues)
            break
          }

          case 'ADX': {
            const period = (indicator.params as any).period || 14
            values = ADX.calculate({
              high: highPrices,
              low: lowPrices,
              close: closePrices,
              period
            })
            minValue = 0
            maxValue = 100
            break
          }
        }

        if (!values || values.length === 0) return

        const valueRange = maxValue - minValue

        // Função helper para converter valor em Y
        const valueToY = (value: number) => {
          return MARGIN.top + chartHeight - ((value - minValue) / valueRange) * chartHeight
        }

        // Renderizar baseado no tipo de indicador
        if (indicator.type === 'RSI' || indicator.type === 'MFI' || indicator.type === 'ATR' || indicator.type === 'CCI' || indicator.type === 'ADX') {
          // Linha simples
          ctx.strokeStyle = indicator.color
          ctx.lineWidth = indicator.lineWidth || 2
          ctx.globalAlpha = 0.9

          ctx.beginPath()
          values.forEach((value, i) => {
            if (!value || isNaN(value)) return

            const actualIndex = i + (closePrices.length - values.length)
            const x = MARGIN.left + actualIndex * candleSpacing + candleSpacing / 2 + offsetX

            if (x >= MARGIN.left - candleSpacing && x <= MARGIN.left + chartWidth + candleSpacing) {
              const y = valueToY(value)
              if (i === 0) ctx.moveTo(x, y)
              else ctx.lineTo(x, y)
            }
          })
          ctx.stroke()
          ctx.globalAlpha = 1

          // Linhas de referência para RSI/MFI (30, 50, 70)
          if (indicator.type === 'RSI' || indicator.type === 'MFI') {
            ctx.strokeStyle = colors.grid
            ctx.lineWidth = 1
            ctx.setLineDash([2, 2])
            ;[30, 50, 70].forEach(level => {
              const y = valueToY(level)
              ctx.beginPath()
              ctx.moveTo(MARGIN.left, y)
              ctx.lineTo(MARGIN.left + chartWidth, y)
              ctx.stroke()
            })
            ctx.setLineDash([])
          }

        } else if (indicator.type === 'MACD') {
          // MACD tem 3 componentes: MACD line, Signal line, Histogram
          ctx.globalAlpha = 0.9

          // Histogram (barras)
          values.forEach((macd, i) => {
            if (!macd || !macd.histogram) return

            const actualIndex = i + (closePrices.length - values.length)
            const x = MARGIN.left + actualIndex * candleSpacing + candleSpacing / 2 + offsetX

            if (x >= MARGIN.left - candleSpacing && x <= MARGIN.left + chartWidth + candleSpacing) {
              const zeroY = valueToY(0)
              const histY = valueToY(macd.histogram)
              const barHeight = zeroY - histY

              ctx.fillStyle = macd.histogram >= 0 ? colors.bullish : colors.bearish
              ctx.fillRect(x - candleSpacing / 3, histY, candleSpacing * 0.6, barHeight)
            }
          })

          // MACD Line
          ctx.strokeStyle = indicator.color
          ctx.lineWidth = 2
          ctx.beginPath()
          values.forEach((macd, i) => {
            if (!macd || !macd.MACD) return

            const actualIndex = i + (closePrices.length - values.length)
            const x = MARGIN.left + actualIndex * candleSpacing + candleSpacing / 2 + offsetX

            if (x >= MARGIN.left - candleSpacing && x <= MARGIN.left + chartWidth + candleSpacing) {
              const y = valueToY(macd.MACD)
              if (i === 0) ctx.moveTo(x, y)
              else ctx.lineTo(x, y)
            }
          })
          ctx.stroke()

          // Signal Line
          ctx.strokeStyle = '#ff9800'
          ctx.lineWidth = 2
          ctx.beginPath()
          values.forEach((macd, i) => {
            if (!macd || !macd.signal) return

            const actualIndex = i + (closePrices.length - values.length)
            const x = MARGIN.left + actualIndex * candleSpacing + candleSpacing / 2 + offsetX

            if (x >= MARGIN.left - candleSpacing && x <= MARGIN.left + chartWidth + candleSpacing) {
              const y = valueToY(macd.signal)
              if (i === 0) ctx.moveTo(x, y)
              else ctx.lineTo(x, y)
            }
          })
          ctx.stroke()

          // Linha zero
          ctx.strokeStyle = colors.grid
          ctx.lineWidth = 1
          ctx.setLineDash([2, 2])
          const zeroY = valueToY(0)
          ctx.beginPath()
          ctx.moveTo(MARGIN.left, zeroY)
          ctx.lineTo(MARGIN.left + chartWidth, zeroY)
          ctx.stroke()
          ctx.setLineDash([])

          ctx.globalAlpha = 1

        } else if (indicator.type === 'STOCH') {
          // Stochastic tem 2 linhas: %K e %D
          ctx.globalAlpha = 0.9

          // %K Line
          ctx.strokeStyle = indicator.color
          ctx.lineWidth = 2
          ctx.beginPath()
          values.forEach((stoch, i) => {
            if (!stoch || !stoch.k) return

            const actualIndex = i + (closePrices.length - values.length)
            const x = MARGIN.left + actualIndex * candleSpacing + candleSpacing / 2 + offsetX

            if (x >= MARGIN.left - candleSpacing && x <= MARGIN.left + chartWidth + candleSpacing) {
              const y = valueToY(stoch.k)
              if (i === 0) ctx.moveTo(x, y)
              else ctx.lineTo(x, y)
            }
          })
          ctx.stroke()

          // %D Line
          ctx.strokeStyle = '#ff9800'
          ctx.lineWidth = 2
          ctx.beginPath()
          values.forEach((stoch, i) => {
            if (!stoch || !stoch.d) return

            const actualIndex = i + (closePrices.length - values.length)
            const x = MARGIN.left + actualIndex * candleSpacing + candleSpacing / 2 + offsetX

            if (x >= MARGIN.left - candleSpacing && x <= MARGIN.left + chartWidth + candleSpacing) {
              const y = valueToY(stoch.d)
              if (i === 0) ctx.moveTo(x, y)
              else ctx.lineTo(x, y)
            }
          })
          ctx.stroke()

          // Linhas de referência (20, 50, 80)
          ctx.strokeStyle = colors.grid
          ctx.lineWidth = 1
          ctx.setLineDash([2, 2])
          ;[20, 50, 80].forEach(level => {
            const y = valueToY(level)
            ctx.beginPath()
            ctx.moveTo(MARGIN.left, y)
            ctx.lineTo(MARGIN.left + chartWidth, y)
            ctx.stroke()
          })
          ctx.setLineDash([])

          ctx.globalAlpha = 1
        }

        // Labels do eixo Y (valores min/max)
        ctx.fillStyle = colors.text
        ctx.font = '11px monospace'
        ctx.textAlign = 'left'
        ctx.fillText(maxValue.toFixed(2), MARGIN.left + chartWidth + 5, MARGIN.top + 12)
        ctx.fillText(minValue.toFixed(2), MARGIN.left + chartWidth + 5, MARGIN.top + chartHeight - 5)

      } catch (error) {
        console.error(`❌ Error rendering separate indicator ${indicator.type}:`, error)
      }
    })

  }, [candles, width, height, theme, viewport, indicators, colors])

  // ========== LAYER 3: CROSSHAIR ==========
  useEffect(() => {
    const canvas = crosshairCanvasRef.current
    if (!canvas || width === 0 || height === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    // Limpar
    ctx.clearRect(0, 0, width, height)

    if (!mousePos || hoveredCandleIndex === null) return

    const chartWidth = width - MARGIN.left - MARGIN.right
    const chartHeight = height - MARGIN.top - MARGIN.bottom

    // Crosshair vertical
    ctx.strokeStyle = colors.crosshair
    ctx.lineWidth = 1
    ctx.setLineDash([4, 4])

    ctx.beginPath()
    ctx.moveTo(mousePos.x, MARGIN.top)
    ctx.lineTo(mousePos.x, MARGIN.top + chartHeight)
    ctx.stroke()

    // Crosshair horizontal
    ctx.beginPath()
    ctx.moveTo(MARGIN.left, mousePos.y)
    ctx.lineTo(MARGIN.left + chartWidth, mousePos.y)
    ctx.stroke()

    ctx.setLineDash([])

  }, [mousePos, hoveredCandleIndex, width, height, colors])

  return (
    <div style={{ position: 'relative', width, height, borderTop: `1px solid ${colors.grid}` }}>
      {/* Layer 1: Background */}
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
      {/* Layer 2: Indicators */}
      <canvas
        ref={indicatorCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 2,
          pointerEvents: 'none'
        }}
      />
      {/* Layer 3: Crosshair */}
      <canvas
        ref={crosshairCanvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          zIndex: 3,
          pointerEvents: 'none'
        }}
      />

      {/* Label do indicador */}
      {indicators.length > 0 && (
        <div
          style={{
            position: 'absolute',
            top: 5,
            left: 15,
            fontSize: '12px',
            fontWeight: 600,
            color: colors.text,
            zIndex: 4,
            pointerEvents: 'none'
          }}
        >
          {indicators.map(ind => ind.type).join(', ')}
        </div>
      )}
    </div>
  )
}
