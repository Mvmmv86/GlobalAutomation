/**
 * Candle Worker - Renderiza candles em OffscreenCanvas
 * Roda em thread separada para não bloquear UI
 */

import { Candle, ChartTheme } from '../types'
import {
  AnyWorkerMessage,
  RenderMessage,
  InitMessage,
  UpdateThemeMessage,
  ResizeMessage,
  RenderCompleteResponse,
  ReadyResponse,
  ErrorResponse
} from './types'
import { DirtyRect } from '../core/Layer'

// Estado do worker
let ctx: OffscreenCanvasRenderingContext2D | null = null
let theme: ChartTheme | null = null
let width = 0
let height = 0
let dpr = 1
let priceScale: { min: number; max: number; range: number } | null = null

/**
 * Inicializa o worker com canvas e configurações
 */
function handleInit(msg: InitMessage): void {
  try {
    const canvas = msg.canvas
    width = msg.width
    height = msg.height
    dpr = msg.dpr
    theme = msg.theme

    // Ajustar tamanho do canvas
    canvas.width = width * dpr
    canvas.height = height * dpr

    // Obter contexto
    const context = canvas.getContext('2d', {
      alpha: true,
      desynchronized: true,
      willReadFrequently: false
    })

    if (!context) {
      throw new Error('Could not get 2D context')
    }

    ctx = context

    // Escalar para DPR
    ctx.scale(dpr, dpr)

    // Configurações de qualidade
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'

    // Enviar confirmação
    const response: ReadyResponse = {
      type: 'READY',
      id: msg.id,
      timestamp: Date.now()
    }

    self.postMessage(response)

    console.log('🧵 Worker initialized:', { width, height, dpr })
  } catch (error) {
    const errorResponse: ErrorResponse = {
      type: 'ERROR',
      id: msg.id,
      timestamp: Date.now(),
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    }
    self.postMessage(errorResponse)
  }
}

/**
 * Renderiza candles com batch rendering
 */
function handleRender(msg: RenderMessage): void {
  if (!ctx || !theme) {
    console.error('Worker not initialized')
    return
  }

  const startTime = performance.now()
  const { candles, viewport, priceScale: scale, dirtyRect } = msg

  // Atualizar escala de preços
  priceScale = scale

  try {
    // Limpar (apenas dirty region se fornecida)
    if (dirtyRect) {
      ctx.clearRect(dirtyRect.x, dirtyRect.y, dirtyRect.width, dirtyRect.height)
    } else {
      ctx.clearRect(0, 0, width, height)
    }

    // Renderizar candles
    const result = renderCandles(ctx, candles, viewport, theme, dirtyRect)

    const endTime = performance.now()
    const renderTime = endTime - startTime

    // Enviar resposta
    const response: RenderCompleteResponse = {
      type: 'RENDER_COMPLETE',
      id: msg.id,
      timestamp: Date.now(),
      renderTime,
      candlesRendered: result.rendered,
      candlesSkipped: result.skipped
    }

    self.postMessage(response)
  } catch (error) {
    const errorResponse: ErrorResponse = {
      type: 'ERROR',
      id: msg.id,
      timestamp: Date.now(),
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined
    }
    self.postMessage(errorResponse)
  }
}

/**
 * Renderiza candles com batch rendering
 */
function renderCandles(
  context: OffscreenCanvasRenderingContext2D,
  candles: Candle[],
  viewport: { startIndex: number; endIndex: number; candleWidth: number },
  currentTheme: ChartTheme,
  dirtyRect?: DirtyRect | null
): { rendered: number; skipped: number } {
  const candleWidth = viewport.candleWidth

  // Separar candles por cor
  const upCandles: Array<{ candle: Candle; x: number }> = []
  const downCandles: Array<{ candle: Candle; x: number }> = []

  let rendered = 0
  let skipped = 0

  // Calcular posições e filtrar
  candles.forEach((candle, i) => {
    const index = Math.floor(viewport.startIndex) + i
    const x = indexToX(index, viewport.startIndex, candleWidth)

    // Culling: pular candles fora da tela
    if (x < -candleWidth || x > width + candleWidth) {
      skipped++
      return
    }

    // Dirty region culling
    if (dirtyRect) {
      const candleRight = x + candleWidth / 2
      const candleLeft = x - candleWidth / 2
      const dirtyRight = dirtyRect.x + dirtyRect.width

      if (candleRight < dirtyRect.x || candleLeft > dirtyRight) {
        skipped++
        return
      }
    }

    const isUp = candle.close >= candle.open

    if (isUp) {
      upCandles.push({ candle, x })
    } else {
      downCandles.push({ candle, x })
    }
    rendered++
  })

  // Renderizar wicks (todos de uma vez)
  renderWicks(context, [...upCandles, ...downCandles], candleWidth, currentTheme)

  // Renderizar corpos (separados por cor)
  renderBodies(context, upCandles, candleWidth, currentTheme.candle.up)
  renderBodies(context, downCandles, candleWidth, currentTheme.candle.down)

  return { rendered, skipped }
}

/**
 * Renderiza wicks em batch
 */
function renderWicks(
  context: OffscreenCanvasRenderingContext2D,
  candles: Array<{ candle: Candle; x: number }>,
  candleWidth: number,
  currentTheme: ChartTheme
): void {
  if (candles.length === 0) return

  context.save()
  context.strokeStyle = currentTheme.candle.up.wick
  context.lineWidth = Math.max(1, candleWidth * 0.1)
  context.beginPath()

  candles.forEach(({ candle, x }) => {
    const highY = priceToY(candle.high)
    const lowY = priceToY(candle.low)

    context.moveTo(x, highY)
    context.lineTo(x, lowY)
  })

  context.stroke()
  context.restore()
}

/**
 * Renderiza corpos em batch
 */
function renderBodies(
  context: OffscreenCanvasRenderingContext2D,
  candles: Array<{ candle: Candle; x: number }>,
  candleWidth: number,
  colors: { body: string; wick: string; border: string }
): void {
  if (candles.length === 0) return

  const bodyWidth = Math.max(1, candleWidth * 0.8)

  // Desenhar corpos preenchidos
  context.save()
  context.fillStyle = colors.body
  context.beginPath()

  candles.forEach(({ candle, x }) => {
    const openY = priceToY(candle.open)
    const closeY = priceToY(candle.close)

    const bodyHeight = Math.abs(closeY - openY)
    const bodyY = Math.min(openY, closeY)
    const bodyX = x - bodyWidth / 2

    if (bodyHeight >= 1) {
      context.rect(bodyX, bodyY, bodyWidth, bodyHeight)
    }
  })

  context.fill()
  context.restore()

  // Desenhar bordas
  if (candleWidth > 3) {
    context.save()
    context.strokeStyle = colors.border
    context.lineWidth = 1
    context.beginPath()

    candles.forEach(({ candle, x }) => {
      const openY = priceToY(candle.open)
      const closeY = priceToY(candle.close)

      const bodyHeight = Math.abs(closeY - openY)
      const bodyY = Math.min(openY, closeY)
      const bodyX = x - bodyWidth / 2

      if (bodyHeight >= 1) {
        context.rect(bodyX, bodyY, bodyWidth, bodyHeight)
      }
    })

    context.stroke()
    context.restore()
  }

  // Desenhar doji (open === close)
  context.save()
  context.strokeStyle = colors.border
  context.lineWidth = 1
  context.beginPath()

  candles.forEach(({ candle, x }) => {
    const openY = priceToY(candle.open)
    const closeY = priceToY(candle.close)

    const bodyHeight = Math.abs(closeY - openY)
    const bodyX = x - bodyWidth / 2

    if (bodyHeight < 1) {
      const bodyY = openY
      context.moveTo(bodyX, bodyY)
      context.lineTo(bodyX + bodyWidth, bodyY)
    }
  })

  context.stroke()
  context.restore()
}

/**
 * Helpers de coordenadas (simplificados)
 */
function indexToX(index: number, startIndex: number, candleWidth: number): number {
  return (index - startIndex) * candleWidth + candleWidth / 2
}

function priceToY(price: number): number {
  if (!priceScale) return height / 2

  // Converter preço para coordenada Y
  const ratio = (price - priceScale.min) / priceScale.range
  return height - (ratio * height) // Inverter Y (0 está no topo)
}

/**
 * Atualiza tema
 */
function handleUpdateTheme(msg: UpdateThemeMessage): void {
  theme = msg.theme
  console.log('🎨 Worker theme updated')
}

/**
 * Redimensiona canvas
 */
function handleResize(msg: ResizeMessage): void {
  if (!ctx) return

  width = msg.width
  height = msg.height
  dpr = msg.dpr

  console.log('📐 Worker resized:', { width, height, dpr })
}

/**
 * Message handler principal
 */
self.addEventListener('message', (event: MessageEvent<AnyWorkerMessage>) => {
  const msg = event.data

  switch (msg.type) {
    case 'INIT':
      handleInit(msg as InitMessage)
      break
    case 'RENDER':
      handleRender(msg as RenderMessage)
      break
    case 'UPDATE_THEME':
      handleUpdateTheme(msg as UpdateThemeMessage)
      break
    case 'RESIZE':
      handleResize(msg as ResizeMessage)
      break
    case 'DESTROY':
      // Cleanup
      ctx = null
      theme = null
      console.log('🧹 Worker destroyed')
      break
    default:
      console.warn('Unknown message type:', (msg as any).type)
  }
})

console.log('🧵 Candle Worker loaded')
