/**
 * DrawingRenderer - Renderização Profissional de Desenhos em Canvas
 * FASE 11: Renderiza todos os tipos de desenhos com estilo TradingView
 */

import {
  AnyDrawing,
  DrawingType,
  LineStyle,
  CanvasPoint,
  ChartPoint,
  TrendLineDrawing,
  HorizontalLineDrawing,
  VerticalLineDrawing,
  RectangleDrawing,
  FibonacciDrawing,
  TextDrawing,
  ArrowDrawing,
  ChannelDrawing
} from './types'

export interface RenderContext {
  ctx: CanvasRenderingContext2D
  width: number
  height: number
  dpr: number
  chartArea: {
    left: number
    right: number
    top: number
    bottom: number
  }
}

export class DrawingRenderer {
  /**
   * Renderiza todos os desenhos
   */
  static renderAll(
    drawings: AnyDrawing[],
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint,
    selectedId: string | null = null,
    hoveredId: string | null = null
  ): void {
    const { ctx } = renderCtx

    // Salvar estado do canvas
    ctx.save()

    // Renderizar desenhos em ordem de zIndex
    const sortedDrawings = [...drawings].sort((a, b) => a.zIndex - b.zIndex)

    for (const drawing of sortedDrawings) {
      if (!drawing.visible) continue

      const isSelected = drawing.id === selectedId
      const isHovered = drawing.id === hoveredId

      this.renderDrawing(drawing, renderCtx, coordTransform, isSelected, isHovered)
    }

    ctx.restore()
  }

  /**
   * Renderiza um desenho específico
   */
  static renderDrawing(
    drawing: AnyDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint,
    isSelected: boolean = false,
    isHovered: boolean = false
  ): void {
    const { ctx } = renderCtx

    ctx.save()

    // Aplicar estilo de linha
    this.applyLineStyle(ctx, drawing.style.lineStyle)
    ctx.strokeStyle = drawing.style.color
    ctx.lineWidth = drawing.style.lineWidth * (isHovered ? 1.5 : 1)

    if (drawing.style.fillColor && drawing.style.fillOpacity) {
      ctx.fillStyle = this.hexToRgba(drawing.style.fillColor, drawing.style.fillOpacity)
    }

    // Renderizar baseado no tipo
    switch (drawing.type) {
      case DrawingType.TREND_LINE:
        this.renderTrendLine(drawing as TrendLineDrawing, renderCtx, coordTransform)
        break

      case DrawingType.HORIZONTAL_LINE:
        this.renderHorizontalLine(drawing as HorizontalLineDrawing, renderCtx, coordTransform)
        break

      case DrawingType.VERTICAL_LINE:
        this.renderVerticalLine(drawing as VerticalLineDrawing, renderCtx, coordTransform)
        break

      case DrawingType.RECTANGLE:
        this.renderRectangle(drawing as RectangleDrawing, renderCtx, coordTransform)
        break

      case DrawingType.FIBONACCI_RETRACEMENT:
        this.renderFibonacci(drawing as FibonacciDrawing, renderCtx, coordTransform)
        break

      case DrawingType.TEXT:
        this.renderText(drawing as TextDrawing, renderCtx, coordTransform)
        break

      case DrawingType.ARROW:
        this.renderArrow(drawing as ArrowDrawing, renderCtx, coordTransform)
        break

      case DrawingType.CHANNEL:
        this.renderChannel(drawing as ChannelDrawing, renderCtx, coordTransform)
        break
    }

    // Renderizar âncoras se selecionado
    if (isSelected) {
      this.renderAnchors(drawing, renderCtx, coordTransform)
    }

    ctx.restore()
  }

  // ============================================================================
  // SPECIFIC RENDERERS
  // ============================================================================

  /**
   * Renderiza linha de tendência
   */
  private static renderTrendLine(
    drawing: TrendLineDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx, chartArea } = renderCtx
    const [p1, p2] = drawing.points.map(coordTransform)

    // Calcular extensões
    let startX = p1.x
    let startY = p1.y
    let endX = p2.x
    let endY = p2.y

    if (drawing.extendLeft || drawing.extendRight) {
      const dx = p2.x - p1.x
      const dy = p2.y - p1.y
      const slope = dx !== 0 ? dy / dx : 0

      if (drawing.extendLeft) {
        startX = chartArea.left
        startY = p1.y - slope * (p1.x - chartArea.left)
      }

      if (drawing.extendRight) {
        endX = chartArea.right
        endY = p2.y + slope * (chartArea.right - p2.x)
      }
    }

    // Desenhar linha
    ctx.beginPath()
    ctx.moveTo(startX, startY)
    ctx.lineTo(endX, endY)
    ctx.stroke()

    // Mostrar ângulo e distância
    if (drawing.showAngle || drawing.showDistance) {
      const midX = (p1.x + p2.x) / 2
      const midY = (p1.y + p2.y) / 2

      let label = ''
      if (drawing.showAngle) {
        const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * (180 / Math.PI)
        label += `${angle.toFixed(1)}°`
      }

      if (drawing.showDistance && drawing.showAngle) {
        label += ' | '
      }

      if (drawing.showDistance) {
        // Calcular distância em % (aproximação - precisa de dados de preço)
        const distance = Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2))
        label += `${distance.toFixed(0)}px`
      }

      this.renderLabel(ctx, label, midX, midY - 10, drawing.style.color)
    }
  }

  /**
   * Renderiza linha horizontal
   */
  private static renderHorizontalLine(
    drawing: HorizontalLineDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx, chartArea } = renderCtx
    const p = coordTransform(drawing.points[0])

    ctx.beginPath()
    ctx.moveTo(chartArea.left, p.y)
    ctx.lineTo(chartArea.right, p.y)
    ctx.stroke()

    // Renderizar label se houver
    if (drawing.label) {
      this.renderLabel(ctx, drawing.label, chartArea.left + 10, p.y - 5, drawing.style.color)
    }
  }

  /**
   * Renderiza linha vertical
   */
  private static renderVerticalLine(
    drawing: VerticalLineDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx, chartArea } = renderCtx
    const p = coordTransform(drawing.points[0])

    ctx.beginPath()
    ctx.moveTo(p.x, chartArea.top)
    ctx.lineTo(p.x, chartArea.bottom)
    ctx.stroke()

    // Renderizar label se houver
    if (drawing.label) {
      this.renderLabel(ctx, drawing.label, p.x + 5, chartArea.top + 15, drawing.style.color)
    }
  }

  /**
   * Renderiza retângulo
   */
  private static renderRectangle(
    drawing: RectangleDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx } = renderCtx
    const [p1, p2] = drawing.points.map(coordTransform)

    const x = Math.min(p1.x, p2.x)
    const y = Math.min(p1.y, p2.y)
    const width = Math.abs(p2.x - p1.x)
    const height = Math.abs(p2.y - p1.y)

    // Preencher se enabled
    if (drawing.filled && drawing.style.fillColor) {
      ctx.fillRect(x, y, width, height)
    }

    // Desenhar borda
    ctx.strokeRect(x, y, width, height)

    // Mostrar range de preço
    if (drawing.showPriceRange) {
      const priceRange = Math.abs(drawing.points[1].price - drawing.points[0].price)
      const percent = (priceRange / drawing.points[0].price) * 100
      const label = `${percent.toFixed(2)}%`
      this.renderLabel(ctx, label, x + width / 2, y - 5, drawing.style.color)
    }
  }

  /**
   * Renderiza Fibonacci Retracement
   */
  private static renderFibonacci(
    drawing: FibonacciDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx, chartArea } = renderCtx
    const [p1, p2] = drawing.points.map(coordTransform)

    const priceStart = drawing.points[0].price
    const priceEnd = drawing.points[1].price
    const priceRange = priceEnd - priceStart

    // Renderizar linhas de níveis de Fibonacci
    for (const level of drawing.levels) {
      const price = priceStart + priceRange * level.ratio
      level.price = price // Atualizar preço calculado

      // Transformar preço para coordenada Y
      const y = p1.y + (p2.y - p1.y) * level.ratio

      // Aplicar estilo do nível
      ctx.save()
      ctx.strokeStyle = level.color
      this.applyLineStyle(ctx, level.lineStyle)

      ctx.beginPath()
      ctx.moveTo(chartArea.left, y)
      ctx.lineTo(chartArea.right, y)
      ctx.stroke()

      ctx.restore()

      // Renderizar labels
      if (drawing.showLabels) {
        let label = level.label
        if (drawing.showPrices) {
          label += ` (${price.toFixed(2)})`
        }
        this.renderLabel(ctx, label, chartArea.left + 10, y - 5, level.color)
      }
    }

    // Renderizar linha principal (do ponto 1 ao ponto 2)
    ctx.save()
    ctx.strokeStyle = drawing.style.color
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(p1.x, p1.y)
    ctx.lineTo(p2.x, p2.y)
    ctx.stroke()
    ctx.restore()
  }

  /**
   * Renderiza texto
   */
  private static renderText(
    drawing: TextDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx } = renderCtx
    const p = coordTransform(drawing.points[0])

    const fontSize = drawing.style.fontSize || 14
    const fontFamily = drawing.style.fontFamily || 'Arial, sans-serif'
    const textColor = drawing.style.textColor || '#FFFFFF'
    const padding = drawing.padding || 8

    ctx.font = `${fontSize}px ${fontFamily}`
    const textMetrics = ctx.measureText(drawing.text)
    const textWidth = textMetrics.width
    const textHeight = fontSize

    // Calcular posição baseado em anchor
    let x = p.x
    let y = p.y

    switch (drawing.anchor) {
      case 'top':
        x -= textWidth / 2
        y += padding
        break
      case 'bottom':
        x -= textWidth / 2
        y -= textHeight + padding
        break
      case 'left':
        x += padding
        y += textHeight / 2
        break
      case 'right':
        x -= textWidth + padding
        y += textHeight / 2
        break
      case 'center':
      default:
        x -= textWidth / 2
        y += textHeight / 2
        break
    }

    // Desenhar background
    if (drawing.backgroundColor) {
      ctx.fillStyle = this.hexToRgba(
        drawing.backgroundColor,
        drawing.style.fillOpacity || 0.7
      )
      ctx.fillRect(
        x - padding,
        y - textHeight - padding / 2,
        textWidth + padding * 2,
        textHeight + padding
      )
    }

    // Desenhar borda
    if (drawing.borderColor) {
      ctx.strokeStyle = drawing.borderColor
      ctx.lineWidth = 1
      ctx.strokeRect(
        x - padding,
        y - textHeight - padding / 2,
        textWidth + padding * 2,
        textHeight + padding
      )
    }

    // Desenhar texto
    ctx.fillStyle = textColor
    ctx.fillText(drawing.text, x, y)
  }

  /**
   * Renderiza seta
   */
  private static renderArrow(
    drawing: ArrowDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx } = renderCtx
    const [p1, p2] = drawing.points.map(coordTransform)

    // Desenhar linha
    ctx.beginPath()
    ctx.moveTo(p1.x, p1.y)
    ctx.lineTo(p2.x, p2.y)
    ctx.stroke()

    // Desenhar cabeça da seta
    const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x)
    const arrowSize = drawing.arrowHeadSize

    ctx.beginPath()
    ctx.moveTo(p2.x, p2.y)
    ctx.lineTo(
      p2.x - arrowSize * Math.cos(angle - Math.PI / 6),
      p2.y - arrowSize * Math.sin(angle - Math.PI / 6)
    )
    ctx.moveTo(p2.x, p2.y)
    ctx.lineTo(
      p2.x - arrowSize * Math.cos(angle + Math.PI / 6),
      p2.y - arrowSize * Math.sin(angle + Math.PI / 6)
    )
    ctx.stroke()
  }

  /**
   * Renderiza canal paralelo
   */
  private static renderChannel(
    drawing: ChannelDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx } = renderCtx
    const [p1, p2, p3] = drawing.points.map(coordTransform)

    // Calcular linha paralela
    const dx = p2.x - p1.x
    const dy = p2.y - p1.y
    const offsetX = p3.x - p1.x
    const offsetY = p3.y - p1.y

    const p4 = { x: p2.x + offsetX, y: p2.y + offsetY }

    // Desenhar linha base
    ctx.beginPath()
    ctx.moveTo(p1.x, p1.y)
    ctx.lineTo(p2.x, p2.y)
    ctx.stroke()

    // Desenhar linha paralela
    ctx.beginPath()
    ctx.moveTo(p3.x, p3.y)
    ctx.lineTo(p4.x, p4.y)
    ctx.stroke()

    // Preencher canal
    if (drawing.filled && drawing.style.fillColor) {
      ctx.fillStyle = this.hexToRgba(
        drawing.style.fillColor,
        drawing.style.fillOpacity || 0.05
      )
      ctx.beginPath()
      ctx.moveTo(p1.x, p1.y)
      ctx.lineTo(p2.x, p2.y)
      ctx.lineTo(p4.x, p4.y)
      ctx.lineTo(p3.x, p3.y)
      ctx.closePath()
      ctx.fill()
    }
  }

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  /**
   * Renderiza âncoras de seleção
   */
  private static renderAnchors(
    drawing: AnyDrawing,
    renderCtx: RenderContext,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): void {
    const { ctx } = renderCtx
    const points = drawing.points.map(coordTransform)

    ctx.save()
    ctx.fillStyle = '#2196F3'
    ctx.strokeStyle = '#FFFFFF'
    ctx.lineWidth = 2

    for (const point of points) {
      ctx.beginPath()
      ctx.arc(point.x, point.y, 6, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
    }

    ctx.restore()
  }

  /**
   * Renderiza um label de texto
   */
  private static renderLabel(
    ctx: CanvasRenderingContext2D,
    text: string,
    x: number,
    y: number,
    color: string
  ): void {
    ctx.save()

    ctx.font = '12px Arial, sans-serif'
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
    ctx.strokeStyle = color
    ctx.lineWidth = 1

    const metrics = ctx.measureText(text)
    const padding = 4

    // Background
    ctx.fillRect(
      x - padding,
      y - 12 - padding,
      metrics.width + padding * 2,
      14 + padding
    )

    // Border
    ctx.strokeRect(
      x - padding,
      y - 12 - padding,
      metrics.width + padding * 2,
      14 + padding
    )

    // Text
    ctx.fillStyle = '#FFFFFF'
    ctx.fillText(text, x, y)

    ctx.restore()
  }

  /**
   * Aplica estilo de linha (solid, dashed, dotted)
   */
  private static applyLineStyle(ctx: CanvasRenderingContext2D, lineStyle: LineStyle): void {
    switch (lineStyle) {
      case LineStyle.SOLID:
        ctx.setLineDash([])
        break
      case LineStyle.DASHED:
        ctx.setLineDash([5, 5])
        break
      case LineStyle.DOTTED:
        ctx.setLineDash([2, 3])
        break
    }
  }

  /**
   * Converte hex para rgba
   */
  private static hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }
}
