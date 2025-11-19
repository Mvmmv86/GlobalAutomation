/**
 * GridRendererMinimal - FASE 4
 *
 * Objetivo: Renderizar grid profissional com eixos X/Y
 *
 * O que faz:
 * - Grid horizontal e vertical
 * - Eixo X (tempo) com labels formatadas
 * - Eixo Y (preço) com labels formatadas
 * - Suporte a tema dark/light
 * - Performance otimizada
 */

import type { ChartTheme } from '../theme'

export interface GridConfig {
  width: number
  height: number
  priceMin: number
  priceMax: number
  timeStart: number
  timeEnd: number
}

export class GridRendererMinimal {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private theme: ChartTheme

  // Margens para os eixos
  private readonly MARGIN_LEFT = 80   // Espaço para labels de preço
  private readonly MARGIN_RIGHT = 20
  private readonly MARGIN_TOP = 20
  private readonly MARGIN_BOTTOM = 40 // Espaço para labels de tempo

  constructor(canvas: HTMLCanvasElement, theme: ChartTheme) {
    this.canvas = canvas
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      throw new Error('Failed to get 2D context')
    }
    this.ctx = ctx
    this.theme = theme

    console.log('📏 [GridRendererMinimal] Criado')
  }

  /**
   * Renderizar grid completo
   */
  render(config: GridConfig): void {
    const { width, height, priceMin, priceMax, timeStart, timeEnd } = config

    // Limpar canvas
    this.ctx.clearRect(0, 0, width, height)

    // Área de desenho (sem margens)
    const chartWidth = width - this.MARGIN_LEFT - this.MARGIN_RIGHT
    const chartHeight = height - this.MARGIN_TOP - this.MARGIN_BOTTOM

    console.log(`📊 [GridRendererMinimal] Renderizando grid ${chartWidth}x${chartHeight}`)

    // Desenhar background
    this.drawBackground(width, height)

    // Desenhar grid horizontal (linhas de preço)
    this.drawHorizontalGrid(chartWidth, chartHeight, priceMin, priceMax)

    // Desenhar grid vertical (linhas de tempo)
    this.drawVerticalGrid(chartWidth, chartHeight, timeStart, timeEnd)

    // Desenhar eixos
    this.drawAxes(chartWidth, chartHeight)
  }

  /**
   * Desenhar background
   */
  private drawBackground(width: number, height: number): void {
    this.ctx.fillStyle = this.theme.background
    this.ctx.fillRect(0, 0, width, height)
  }

  /**
   * Desenhar grid horizontal (linhas de preço)
   */
  private drawHorizontalGrid(
    chartWidth: number,
    chartHeight: number,
    priceMin: number,
    priceMax: number
  ): void {
    const priceRange = priceMax - priceMin

    // Calcular número ideal de linhas (aproximadamente a cada 80px)
    const idealLines = Math.floor(chartHeight / 80)
    const numLines = Math.max(5, Math.min(10, idealLines))

    // Calcular step de preço
    const priceStep = priceRange / numLines

    this.ctx.strokeStyle = this.theme.grid.main
    this.ctx.lineWidth = 1
    this.ctx.setLineDash([5, 5])

    this.ctx.fillStyle = this.theme.text.secondary
    this.ctx.font = '12px monospace'
    this.ctx.textAlign = 'right'
    this.ctx.textBaseline = 'middle'

    for (let i = 0; i <= numLines; i++) {
      const price = priceMin + (priceStep * i)
      const y = this.MARGIN_TOP + chartHeight - (chartHeight * (price - priceMin) / priceRange)

      // Linha horizontal
      this.ctx.beginPath()
      this.ctx.moveTo(this.MARGIN_LEFT, y)
      this.ctx.lineTo(this.MARGIN_LEFT + chartWidth, y)
      this.ctx.stroke()

      // Label de preço
      const priceLabel = this.formatPrice(price)
      this.ctx.fillText(priceLabel, this.MARGIN_LEFT - 10, y)
    }

    this.ctx.setLineDash([])
  }

  /**
   * Desenhar grid vertical (linhas de tempo)
   */
  private drawVerticalGrid(
    chartWidth: number,
    chartHeight: number,
    timeStart: number,
    timeEnd: number
  ): void {
    const timeRange = timeEnd - timeStart

    // Calcular número ideal de linhas (aproximadamente a cada 100px)
    const idealLines = Math.floor(chartWidth / 100)
    const numLines = Math.max(5, Math.min(12, idealLines))

    // Calcular step de tempo
    const timeStep = timeRange / numLines

    this.ctx.strokeStyle = this.theme.grid.main
    this.ctx.lineWidth = 1
    this.ctx.setLineDash([5, 5])

    this.ctx.fillStyle = this.theme.text.secondary
    this.ctx.font = '11px monospace'
    this.ctx.textAlign = 'center'
    this.ctx.textBaseline = 'top'

    for (let i = 0; i <= numLines; i++) {
      const time = timeStart + (timeStep * i)
      const x = this.MARGIN_LEFT + (chartWidth * i / numLines)

      // Linha vertical
      this.ctx.beginPath()
      this.ctx.moveTo(x, this.MARGIN_TOP)
      this.ctx.lineTo(x, this.MARGIN_TOP + chartHeight)
      this.ctx.stroke()

      // Label de tempo
      const timeLabel = this.formatTime(time)
      this.ctx.fillText(timeLabel, x, this.MARGIN_TOP + chartHeight + 5)
    }

    this.ctx.setLineDash([])
  }

  /**
   * Desenhar eixos (bordas)
   */
  private drawAxes(chartWidth: number, chartHeight: number): void {
    this.ctx.strokeStyle = this.theme.text.secondary
    this.ctx.lineWidth = 1

    // Borda da área de desenho
    this.ctx.strokeRect(
      this.MARGIN_LEFT,
      this.MARGIN_TOP,
      chartWidth,
      chartHeight
    )
  }

  /**
   * Formatar preço para exibição
   */
  private formatPrice(price: number): string {
    if (price >= 1000) {
      return price.toFixed(0)
    } else if (price >= 1) {
      return price.toFixed(2)
    } else {
      return price.toFixed(4)
    }
  }

  /**
   * Formatar tempo para exibição
   */
  private formatTime(timestamp: number): string {
    const date = new Date(timestamp)

    // Formato: DD/MM HH:mm
    const day = date.getDate().toString().padStart(2, '0')
    const month = (date.getMonth() + 1).toString().padStart(2, '0')
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')

    return `${day}/${month} ${hours}:${minutes}`
  }

  /**
   * Obter margens (para uso externo)
   */
  getMargins() {
    return {
      left: this.MARGIN_LEFT,
      right: this.MARGIN_RIGHT,
      top: this.MARGIN_TOP,
      bottom: this.MARGIN_BOTTOM
    }
  }

  /**
   * Obter área de desenho útil
   */
  getChartArea(width: number, height: number) {
    return {
      x: this.MARGIN_LEFT,
      y: this.MARGIN_TOP,
      width: width - this.MARGIN_LEFT - this.MARGIN_RIGHT,
      height: height - this.MARGIN_TOP - this.MARGIN_BOTTOM
    }
  }

  /**
   * Atualizar tema
   */
  updateTheme(theme: ChartTheme): void {
    this.theme = theme
    console.log('🎨 [GridRendererMinimal] Tema atualizado')
  }

  /**
   * Cleanup
   */
  destroy(): void {
    console.log('🧹 [GridRendererMinimal] Destruindo')
  }
}
