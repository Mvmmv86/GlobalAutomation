/**
 * Chart Engine - Core rendering and coordinate system
 * High-performance canvas-based chart engine
 */

import { Candle, Viewport, Point, ChartTheme } from './types'
import { DataManager } from './DataManager'
import { ViewportManager, ViewportListener } from './core/ViewportManager'

export class ChartEngine implements ViewportListener {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private dataManager: DataManager
  private theme: ChartTheme
  private viewport: Viewport
  private viewportManager: ViewportManager | null = null
  private dpr: number // Device pixel ratio

  constructor(
    canvas: HTMLCanvasElement,
    dataManager: DataManager,
    theme: ChartTheme
  ) {
    this.canvas = canvas
    const context = canvas.getContext('2d', { alpha: false })
    if (!context) {
      throw new Error('Could not get 2D context')
    }
    this.ctx = context
    this.dataManager = dataManager
    this.theme = theme
    this.dpr = window.devicePixelRatio || 1

    // Viewport inicial (será substituído pelo ViewportManager)
    this.viewport = {
      startIndex: 0,
      endIndex: 100,
      scale: 1,
      offset: { x: 0, y: 0 },
      width: canvas.width,
      height: canvas.height
    }

    this.setupCanvas()
  }

  /**
   * Conecta ao ViewportManager compartilhado
   */
  setViewportManager(viewportManager: ViewportManager): void {
    if (this.viewportManager) {
      this.viewportManager.removeListener(this)
    }
    this.viewportManager = viewportManager
    this.viewportManager.addListener(this)
    this.viewport = this.viewportManager.getViewport()
  }

  /**
   * Callback quando o viewport muda
   */
  onViewportChange(viewport: Viewport): void {
    this.viewport = viewport
  }

  /**
   * Configura o canvas com DPR correto para displays retina
   */
  private setupCanvas(): void {
    const rect = this.canvas.getBoundingClientRect()

    // Ajustar para device pixel ratio
    this.canvas.width = rect.width * this.dpr
    this.canvas.height = rect.height * this.dpr

    this.viewport.width = this.canvas.width
    this.viewport.height = this.canvas.height

    // Escalar o contexto
    this.ctx.scale(this.dpr, this.dpr)

    // Configurações de renderização para melhor qualidade
    this.ctx.imageSmoothingEnabled = true
    this.ctx.imageSmoothingQuality = 'high'
  }

  /**
   * Redimensiona o canvas
   */
  resize(width: number, height: number): void {
    this.canvas.width = width * this.dpr
    this.canvas.height = height * this.dpr
    this.viewport.width = this.canvas.width
    this.viewport.height = this.canvas.height

    this.ctx.scale(this.dpr, this.dpr)
    this.ctx.imageSmoothingEnabled = true
    this.ctx.imageSmoothingQuality = 'high'
  }

  /**
   * Converte coordenada X (pixel) para índice do candle
   */
  xToIndex(x: number): number {
    const logicalWidth = this.canvas.width / this.dpr
    const candleWidth = this.getCandleWidth()
    const offsetX = this.viewport.offset.x

    return Math.floor((x + offsetX) / candleWidth)
  }

  /**
   * Converte índice do candle para coordenada X (pixel)
   */
  indexToX(index: number): number {
    const candleWidth = this.getCandleWidth()
    const offsetX = this.viewport.offset.x

    return index * candleWidth - offsetX
  }

  /**
   * Converte coordenada Y (pixel) para preço
   */
  yToPrice(y: number): number {
    const logicalHeight = this.canvas.height / this.dpr
    const priceRange = this.getPriceRange()
    const pricePerPixel = (priceRange.max - priceRange.min) / logicalHeight

    return priceRange.max - (y * pricePerPixel)
  }

  /**
   * Converte preço para coordenada Y (pixel)
   */
  priceToY(price: number): number {
    const logicalHeight = this.canvas.height / this.dpr
    const priceRange = this.getPriceRange()
    const pricePerPixel = (priceRange.max - priceRange.min) / logicalHeight

    return (priceRange.max - price) / pricePerPixel
  }

  /**
   * Retorna a largura de cada candle em pixels
   */
  getCandleWidth(): number {
    const baseWidth = 8 // Largura base do candle
    return baseWidth * this.viewport.scale
  }

  /**
   * Retorna o range de preços visível
   */
  getPriceRange(): { min: number; max: number } {
    const startIndex = Math.max(0, this.viewport.startIndex)
    const endIndex = Math.min(this.dataManager.length, this.viewport.endIndex)

    return this.dataManager.getPriceRange(startIndex, endIndex)
  }

  /**
   * Calcula quantos candles cabem na tela
   */
  getVisibleCandleCount(): number {
    const logicalWidth = this.canvas.width / this.dpr
    const candleWidth = this.getCandleWidth()
    return Math.ceil(logicalWidth / candleWidth)
  }

  /**
   * Atualiza o viewport para mostrar os candles mais recentes
   */
  goToLatest(): void {
    if (this.viewportManager) {
      this.viewportManager.goToLatest()
    } else {
      // Fallback para quando não há ViewportManager
      const visibleCount = this.getVisibleCandleCount()
      const totalCandles = this.dataManager.length

      if (totalCandles > visibleCount) {
        this.viewport.endIndex = totalCandles
        this.viewport.startIndex = totalCandles - visibleCount
      } else {
        this.viewport.startIndex = 0
        this.viewport.endIndex = totalCandles
      }

      this.viewport.offset.x = 0
    }
  }

  /**
   * Aplica zoom no gráfico
   */
  zoom(delta: number, centerX?: number): void {
    if (this.viewportManager) {
      // Converter delta para o formato esperado pelo ViewportManager
      const zoomDelta = delta > 0 ? 0.1 : -0.1
      this.viewportManager.zoom(zoomDelta, centerX)
    } else {
      // Fallback para quando não há ViewportManager
      const oldScale = this.viewport.scale
      const zoomFactor = delta > 0 ? 1.1 : 0.9

      // Limitar zoom entre 0.1x e 5x
      this.viewport.scale = Math.max(0.1, Math.min(5, this.viewport.scale * zoomFactor))

      // Ajustar offset para manter o centro visual
      if (centerX !== undefined) {
        const scaleRatio = this.viewport.scale / oldScale
        const logicalCenterX = centerX / this.dpr
        this.viewport.offset.x = logicalCenterX - (logicalCenterX - this.viewport.offset.x) * scaleRatio
      }

      // Recalcular índices visíveis
      const visibleCount = this.getVisibleCandleCount()
      const centerIndex = (this.viewport.startIndex + this.viewport.endIndex) / 2

      this.viewport.startIndex = Math.max(0, Math.floor(centerIndex - visibleCount / 2))
      this.viewport.endIndex = Math.min(this.dataManager.length, Math.ceil(centerIndex + visibleCount / 2))
    }
  }

  /**
   * Faz pan (arrastar) do gráfico
   */
  pan(deltaX: number): void {
    if (this.viewportManager) {
      const candleWidth = this.getCandleWidth()
      const deltaCandles = Math.round(deltaX / candleWidth)
      this.viewportManager.pan(-deltaCandles) // Inverter direção
    } else {
      // Fallback para quando não há ViewportManager
      const candleWidth = this.getCandleWidth()
      const candlesDelta = deltaX / candleWidth

      this.viewport.startIndex = Math.max(0, this.viewport.startIndex - candlesDelta)
      this.viewport.endIndex = Math.min(this.dataManager.length, this.viewport.endIndex - candlesDelta)

      this.viewport.offset.x += deltaX
    }
  }

  /**
   * Limpa o canvas
   */
  clear(): void {
    const logicalWidth = this.canvas.width / this.dpr
    const logicalHeight = this.canvas.height / this.dpr

    this.ctx.fillStyle = this.theme.background
    this.ctx.fillRect(0, 0, logicalWidth, logicalHeight)
  }

  /**
   * Desenha a grade do gráfico
   */
  drawGrid(): void {
    const logicalWidth = this.canvas.width / this.dpr
    const logicalHeight = this.canvas.height / this.dpr

    this.ctx.strokeStyle = this.theme.grid.color
    this.ctx.lineWidth = this.theme.grid.lineWidth

    // Linhas horizontais (preço)
    const priceRange = this.getPriceRange()
    const priceStep = this.calculatePriceStep(priceRange.max - priceRange.min)
    const startPrice = Math.floor(priceRange.min / priceStep) * priceStep

    for (let price = startPrice; price <= priceRange.max; price += priceStep) {
      const y = this.priceToY(price)

      this.ctx.beginPath()
      this.ctx.moveTo(0, y)
      this.ctx.lineTo(logicalWidth, y)
      this.ctx.stroke()

      // Label do preço
      this.ctx.fillStyle = this.theme.text.secondary
      this.ctx.font = `${this.theme.text.fontSize}px ${this.theme.text.fontFamily}`
      this.ctx.textAlign = 'right'
      this.ctx.fillText(price.toFixed(2), logicalWidth - 5, y - 3)
    }

    // Linhas verticais (tempo) - simplificado
    const visibleCandles = this.getVisibleCandleCount()
    const timeStep = Math.max(10, Math.floor(visibleCandles / 10))

    for (let i = Math.floor(this.viewport.startIndex); i <= this.viewport.endIndex; i += timeStep) {
      const x = this.indexToX(i)

      if (x < 0 || x > logicalWidth) continue

      this.ctx.beginPath()
      this.ctx.moveTo(x, 0)
      this.ctx.lineTo(x, logicalHeight)
      this.ctx.stroke()
    }
  }

  /**
   * Calcula o step ideal para as linhas de preço
   */
  private calculatePriceStep(range: number): number {
    const steps = [0.01, 0.05, 0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000]

    const targetSteps = 10
    const idealStep = range / targetSteps

    // Encontrar o step mais próximo
    return steps.reduce((prev, curr) => {
      return Math.abs(curr - idealStep) < Math.abs(prev - idealStep) ? curr : prev
    })
  }

  /**
   * Retorna informações do viewport
   */
  getViewport(): Viewport {
    return { ...this.viewport }
  }

  /**
   * Define novo viewport
   */
  setViewport(viewport: Partial<Viewport>): void {
    Object.assign(this.viewport, viewport)
  }

  /**
   * Atualiza o tema
   */
  setTheme(theme: ChartTheme): void {
    this.theme = theme
  }

  /**
   * Retorna o contexto do canvas
   */
  getContext(): CanvasRenderingContext2D {
    return this.ctx
  }

  /**
   * Retorna o canvas
   */
  getCanvas(): HTMLCanvasElement {
    return this.canvas
  }

  /**
   * Retorna todos os candles do DataManager
   */
  getCandles(): Candle[] {
    return this.dataManager.getCandles()
  }

  /**
   * Retorna o tema atual
   */
  getTheme(): ChartTheme {
    return this.theme
  }

  /**
   * Retorna o range visível de índices
   */
  getVisibleRange(): { start: number; end: number } {
    return {
      start: this.viewport.startIndex,
      end: this.viewport.endIndex
    }
  }
}
