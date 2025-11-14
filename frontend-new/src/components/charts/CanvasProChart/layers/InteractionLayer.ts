/**
 * InteractionLayer - Renderiza crosshair e tooltips
 * Atualizada a cada movimento do mouse
 */

import { Layer } from '../core/Layer'
import { ChartEngine } from '../Engine'
import { ChartTheme } from '../types'
import { Point } from '../types'

export class InteractionLayer extends Layer {
  private engine: ChartEngine | null = null
  private theme: ChartTheme | null = null
  private mousePos: Point | null = null

  constructor(name: string, zIndex: number) {
    super(name, zIndex)
  }

  /**
   * Inicializa engine e theme
   */
  initialize(engine: ChartEngine, theme: ChartTheme): void {
    this.engine = engine
    this.theme = theme
  }

  /**
   * Atualiza posição do mouse
   */
  setMousePosition(pos: Point | null): void {
    this.mousePos = pos
    this.markDirty()
  }

  /**
   * Renderiza crosshair e tooltips
   */
  render(): void {
    if (!this.engine || !this.theme || !this.mousePos) {
      this.clear()
      return
    }

    const width = this.canvas.width / (window.devicePixelRatio || 1)
    const height = this.canvas.height / (window.devicePixelRatio || 1)

    this.clear()

    const price = this.engine.yToPrice(this.mousePos.y)

    // Linha vertical
    this.ctx.strokeStyle = this.theme.crosshair.color
    this.ctx.lineWidth = 1
    this.ctx.setLineDash([3, 3])
    this.ctx.beginPath()
    this.ctx.moveTo(this.mousePos.x, 0)
    this.ctx.lineTo(this.mousePos.x, height)
    this.ctx.stroke()

    // Linha horizontal
    this.ctx.beginPath()
    this.ctx.moveTo(0, this.mousePos.y)
    this.ctx.lineTo(width, this.mousePos.y)
    this.ctx.stroke()
    this.ctx.setLineDash([])

    // Label de preço
    this.ctx.fillStyle = this.theme.crosshair.labelBackground
    this.ctx.fillRect(width - 80, this.mousePos.y - 12, 75, 20)

    this.ctx.fillStyle = this.theme.crosshair.labelText
    this.ctx.font = `12px ${this.theme.text.fontFamily}`
    this.ctx.textAlign = 'right'
    this.ctx.fillText(price.toFixed(2), width - 8, this.mousePos.y + 4)
  }
}
