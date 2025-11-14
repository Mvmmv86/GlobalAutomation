/**
 * MainLayer - Renderiza candles e volume
 * Atualizada quando novos dados chegam ou viewport muda
 * Com suporte a DIRTY REGIONS para otimização
 */

import { Layer, DirtyRect } from '../core/Layer'
import { CandleRenderer } from '../renderers/CandleRenderer'
import { VolumeRenderer } from '../renderers/VolumeRenderer'
import { ChartEngine } from '../Engine'
import { DataManager } from '../DataManager'
import { ChartTheme } from '../types'

export class MainLayer extends Layer {
  private candleRenderer: CandleRenderer | null = null
  private volumeRenderer: VolumeRenderer | null = null
  private engine: ChartEngine | null = null
  private dataManager: DataManager | null = null
  private theme: ChartTheme | null = null

  constructor(name: string, zIndex: number) {
    super(name, zIndex)
  }

  /**
   * Inicializa os renderers
   */
  initialize(engine: ChartEngine, dataManager: DataManager, theme: ChartTheme): void {
    this.engine = engine
    this.dataManager = dataManager
    this.theme = theme

    this.candleRenderer = new CandleRenderer(engine, dataManager, theme)
    this.volumeRenderer = new VolumeRenderer(engine, dataManager, theme)

    this.markDirty()
  }

  /**
   * Inicializa com renderers externos (para reutilizar instâncias)
   */
  initializeWithRenderers(
    engine: ChartEngine,
    theme: ChartTheme,
    candleRenderer: CandleRenderer,
    volumeRenderer: VolumeRenderer
  ): void {
    this.engine = engine
    this.theme = theme
    this.candleRenderer = candleRenderer
    this.volumeRenderer = volumeRenderer

    this.markDirty()
  }

  /**
   * Renderiza candles e volume (com dirty regions)
   */
  render(): void {
    if (!this.candleRenderer || !this.volumeRenderer) {
      console.warn('⚠️ [MainLayer] Renderers not initialized')
      return
    }

    const dirtyRect = this.getDirtyRect()

    // Limpar apenas a dirty region (ou tudo se null)
    this.clear(dirtyRect)

    // Renderizar candles
    this.candleRenderer.render(this.ctx, dirtyRect)

    // Renderizar volume
    this.volumeRenderer.render(this.ctx, 0.15, dirtyRect)

    // Limpar dirty rect após renderizar
    this.clearDirtyRect()
  }

  /**
   * Atualiza o tema
   */
  setTheme(theme: ChartTheme): void {
    this.theme = theme

    if (this.candleRenderer) {
      this.candleRenderer.setTheme(theme)
    }

    if (this.volumeRenderer) {
      this.volumeRenderer.setTheme(theme)
    }

    this.markDirty()
  }
}
