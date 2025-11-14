/**
 * VolumeRenderer - Volume bars rendering with batch optimization
 * With DIRTY REGIONS support
 */

import { ChartTheme } from '../types'
import { ChartEngine } from '../Engine'
import { DataManager } from '../DataManager'
import { DirtyRect } from '../core/Layer'

export class VolumeRenderer {
  private engine: ChartEngine
  private dataManager: DataManager
  private theme: ChartTheme

  constructor(engine: ChartEngine, dataManager: DataManager, theme: ChartTheme) {
    this.engine = engine
    this.dataManager = dataManager
    this.theme = theme
  }

  /**
   * Renderiza volume bars na parte inferior com batch rendering
   * @param ctx - Canvas context
   * @param heightPercent - Porcentagem da altura para volume
   * @param dirtyRect - Região suja para otimizar (opcional)
   */
  render(ctx: CanvasRenderingContext2D, heightPercent: number = 0.15, dirtyRect?: DirtyRect | null): void {
    const canvas = this.engine.getCanvas()
    const logicalHeight = canvas.height / (window.devicePixelRatio || 1)
    const logicalWidth = canvas.width / (window.devicePixelRatio || 1)
    const volumeHeight = logicalHeight * heightPercent

    const viewport = this.engine.getViewport()
    const visibleCandles = this.dataManager.getVisibleCandles(
      Math.floor(viewport.startIndex),
      Math.ceil(viewport.endIndex)
    )

    if (visibleCandles.length === 0) return

    // Encontrar volume máximo
    const maxVolume = Math.max(...visibleCandles.map(c => c.volume))
    if (maxVolume === 0) return

    const candleWidth = this.engine.getCandleWidth()

    // Separar por cor para batch rendering
    const upBars: Array<{ x: number; barHeight: number }> = []
    const downBars: Array<{ x: number; barHeight: number }> = []

    visibleCandles.forEach((candle, i) => {
      const index = Math.floor(viewport.startIndex) + i
      const x = this.engine.indexToX(index)

      // Dirty region culling: pular volumes fora da região suja
      if (dirtyRect) {
        const barRight = x + (candleWidth * 0.4)
        const barLeft = x - (candleWidth * 0.4)
        const dirtyRight = dirtyRect.x + dirtyRect.width

        // Se volume bar está completamente fora da dirty region, pular
        if (barRight < dirtyRect.x || barLeft > dirtyRight) {
          return
        }
      }

      const isUp = candle.close >= candle.open
      const barHeight = (candle.volume / maxVolume) * volumeHeight

      if (isUp) {
        upBars.push({ x, barHeight })
      } else {
        downBars.push({ x, barHeight })
      }
    })

    // Batch render: volume de alta
    ctx.save()
    ctx.fillStyle = this.theme.volume.up
    upBars.forEach(({ x, barHeight }) => {
      const barY = logicalHeight - barHeight
      ctx.fillRect(
        x - (candleWidth * 0.4),
        barY,
        candleWidth * 0.8,
        barHeight
      )
    })
    ctx.restore()

    // Batch render: volume de baixa
    ctx.save()
    ctx.fillStyle = this.theme.volume.down
    downBars.forEach(({ x, barHeight }) => {
      const barY = logicalHeight - barHeight
      ctx.fillRect(
        x - (candleWidth * 0.4),
        barY,
        candleWidth * 0.8,
        barHeight
      )
    })
    ctx.restore()

    // Linha divisória
    ctx.strokeStyle = this.theme.grid.color
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, logicalHeight - volumeHeight)
    ctx.lineTo(logicalWidth, logicalHeight - volumeHeight)
    ctx.stroke()
  }

  /**
   * Atualiza o tema
   */
  setTheme(theme: ChartTheme): void {
    this.theme = theme
  }
}
