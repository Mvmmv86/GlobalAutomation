/**
 * OverlayLayer - Renderiza SL/TP lines e posições
 * Atualizada quando posições ou ordens mudam
 */

import { Layer } from '../core/Layer'
import { ChartEngine } from '../Engine'
import { ChartTheme } from '../types'

export class OverlayLayer extends Layer {
  private engine: ChartEngine | null = null
  private theme: ChartTheme | null = null
  private stopLoss: number | null = null
  private takeProfit: number | null = null
  private positions: any[] = []

  constructor(name: string, zIndex: number) {
    super(name, zIndex)
  }

  /**
   * Define engine e theme
   */
  initialize(engine: ChartEngine, theme: ChartTheme): void {
    this.engine = engine
    this.theme = theme
  }

  /**
   * Define SL/TP
   */
  setSLTP(sl?: number, tp?: number): void {
    this.stopLoss = sl || null
    this.takeProfit = tp || null
    this.markDirty()
  }

  /**
   * Define posições
   */
  setPositions(positions: any[]): void {
    this.positions = positions
    this.markDirty()
  }

  /**
   * Renderiza SL/TP e posições
   */
  render(): void {
    if (!this.engine || !this.theme) return

    this.clear()

    const width = this.canvas.width / (window.devicePixelRatio || 1)

    // Desenhar Stop Loss
    if (this.stopLoss && this.stopLoss > 0) {
      const y = this.engine.priceToY(this.stopLoss)

      this.ctx.strokeStyle = this.theme.orders.stopLoss
      this.ctx.lineWidth = 2
      this.ctx.setLineDash([5, 5])
      this.ctx.beginPath()
      this.ctx.moveTo(0, y)
      this.ctx.lineTo(width, y)
      this.ctx.stroke()
      this.ctx.setLineDash([])

      // Label
      this.ctx.fillStyle = this.theme.orders.stopLoss
      this.ctx.font = `bold 11px ${this.theme.text.fontFamily}`
      this.ctx.textAlign = 'right'
      this.ctx.fillText(`SL: $${this.stopLoss.toFixed(2)}`, width - 10, y - 5)
    }

    // Desenhar Take Profit
    if (this.takeProfit && this.takeProfit > 0) {
      const y = this.engine.priceToY(this.takeProfit)

      this.ctx.strokeStyle = this.theme.orders.takeProfit
      this.ctx.lineWidth = 2
      this.ctx.setLineDash([5, 5])
      this.ctx.beginPath()
      this.ctx.moveTo(0, y)
      this.ctx.lineTo(width, y)
      this.ctx.stroke()
      this.ctx.setLineDash([])

      // Label
      this.ctx.fillStyle = this.theme.orders.takeProfit
      this.ctx.font = `bold 11px ${this.theme.text.fontFamily}`
      this.ctx.textAlign = 'right'
      this.ctx.fillText(`TP: $${this.takeProfit.toFixed(2)}`, width - 10, y - 5)
    }

    // Desenhar posições
    this.positions.forEach(position => {
      if (!position.entryPrice || !this.engine) return

      const y = this.engine.priceToY(position.entryPrice)

      this.ctx.strokeStyle = this.theme!.orders.position
      this.ctx.lineWidth = 2
      this.ctx.setLineDash([10, 5])
      this.ctx.beginPath()
      this.ctx.moveTo(0, y)
      this.ctx.lineTo(width, y)
      this.ctx.stroke()
      this.ctx.setLineDash([])

      // Label
      const side = position.side || 'LONG'
      this.ctx.fillStyle = this.theme!.orders.position
      this.ctx.font = `bold 11px ${this.theme!.text.fontFamily}`
      this.ctx.textAlign = 'left'
      this.ctx.fillText(`${side}: $${position.entryPrice.toFixed(2)}`, 10, y - 5)
    })
  }
}
