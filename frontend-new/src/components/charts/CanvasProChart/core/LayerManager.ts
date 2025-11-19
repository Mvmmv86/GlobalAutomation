/**
 * LayerManager - Sistema central de gerenciamento de layers
 * Integra todas as layers existentes com o PanelManager
 */

import { Layer } from './Layer'
import { BackgroundLayer } from '../layers/BackgroundLayer'
import { MainLayer } from '../layers/MainLayer'
import { IndicatorLayer } from '../layers/IndicatorLayer'
import { OverlayLayer } from '../layers/OverlayLayer'
import { InteractionLayer } from '../layers/InteractionLayer'
import { SeparatePanelLayer } from '../layers/SeparatePanelLayer'
import { PanelManager } from '../PanelManager'
import { DataManager } from '../DataManager'
import { ChartEngine } from '../Engine'
import { ViewportManager, ViewportListener } from './ViewportManager'
import { Viewport } from '../types'

export interface LayerManagerConfig {
  container: HTMLDivElement
  dataManager: DataManager
  panelManager: PanelManager
  engine: ChartEngine
  theme: any
}

export class LayerManager implements ViewportListener {
  private container: HTMLDivElement
  private layers: Map<string, Layer> = new Map()
  private panelManager: PanelManager
  private dataManager: DataManager
  private engine: ChartEngine
  private theme: any
  private animationFrameId: number | null = null
  private viewportManager: ViewportManager

  constructor(config: LayerManagerConfig) {
    this.container = config.container
    this.panelManager = config.panelManager
    this.dataManager = config.dataManager
    this.engine = config.engine
    this.theme = config.theme

    // ✅ Limpar container apenas se não estiver vazio E se tiver elementos criados por nós
    // Evitar conflito com React que pode estar gerenciando o container
    if (this.container.childNodes.length > 0) {
      // Remover apenas elementos canvas criados anteriormente
      Array.from(this.container.childNodes).forEach(node => {
        if (node instanceof HTMLCanvasElement) {
          try {
            this.container.removeChild(node)
          } catch (e) {
            // Ignorar - React pode já ter removido
          }
        }
      })
    }
    this.container.style.position = 'relative'

    // Criar ViewportManager compartilhado
    const rect = this.container.getBoundingClientRect()
    this.viewportManager = new ViewportManager(rect.width, rect.height)
    this.viewportManager.addListener(this)

    // Conectar ViewportManager ao Engine
    this.engine.setViewportManager(this.viewportManager)

    // Inicializar layers padrão
    this.initializeLayers()
  }

  /**
   * Callback quando o viewport muda
   */
  onViewportChange(viewport: Viewport): void {
    // Propagar mudança para todas as layers
    this.markAllDirty()
  }

  /**
   * Inicializa as layers do sistema
   */
  private initializeLayers(): void {
    // Layer 0: Background (grid, axes)
    const backgroundLayer = new BackgroundLayer('background', 0)
    backgroundLayer.initialize(this.engine, this.theme)
    this.addLayer('background', backgroundLayer)

    // Layer 1: Main (candles)
    const mainLayer = new MainLayer('main', 1)
    mainLayer.initialize(this.engine, this.dataManager, this.theme)
    this.addLayer('main', mainLayer)

    // Layer 2: Indicators (overlay indicators like MA, BB)
    const indicatorLayer = new IndicatorLayer('indicators', 2)
    indicatorLayer.initialize(this.engine)
    this.addLayer('indicators', indicatorLayer)

    // Layer 3: Overlays (orders, positions, SL/TP)
    const overlayLayer = new OverlayLayer('overlays', 3)
    overlayLayer.initialize(this.engine, this.theme)
    this.addLayer('overlays', overlayLayer)

    // Layer 4: Interaction (crosshair, tooltips, drag)
    const interactionLayer = new InteractionLayer('interaction', 4)
    interactionLayer.initialize(this.engine, this.theme)
    this.addLayer('interaction', interactionLayer)
  }

  /**
   * Adiciona uma layer ao manager
   */
  addLayer(name: string, layer: Layer): void {
    this.layers.set(name, layer)
    this.container.appendChild(layer.getCanvas())
  }

  /**
   * Remove uma layer
   */
  removeLayer(name: string): void {
    const layer = this.layers.get(name)
    if (layer) {
      const canvas = layer.getCanvas()
      // ✅ Verificar se o canvas ainda está no DOM antes de remover
      if (canvas && canvas.parentNode === this.container) {
        try {
          this.container.removeChild(canvas)
        } catch (e) {
          console.warn(`[LayerManager] Não foi possível remover layer ${name}:`, e)
        }
      }
      this.layers.delete(name)
    }
  }

  /**
   * Adiciona layer para painel separado
   */
  addSeparatePanelLayer(panelId: string, _indicators: string[]): void {
    const layerName = `panel-${panelId}`

    // Remover layer anterior se existir
    this.removeLayer(layerName)

    // Obter configuração do painel do PanelManager
    const panelConfig = this.panelManager.getLayout().panels.find(p => p.id === panelId)
    if (!panelConfig) {
      console.warn(`[LayerManager] Panel config not found for ${panelId}`)
      return
    }

    // Criar nova layer para o painel
    const layer = new SeparatePanelLayer(layerName, 10 + this.layers.size, panelConfig)
    layer.initialize(this.engine, this.theme)
    this.addLayer(layerName, layer)
  }

  /**
   * Remove layer de painel separado
   */
  removeSeparatePanelLayer(panelId: string): void {
    const layerName = `panel-${panelId}`
    this.removeLayer(layerName)
  }

  /**
   * Obtém uma layer específica
   */
  getLayer(name: string): Layer | undefined {
    return this.layers.get(name)
  }

  /**
   * Obtém todas as layers
   */
  getAllLayers(): Layer[] {
    return Array.from(this.layers.values())
  }

  /**
   * Marca layer como dirty
   */
  markLayerDirty(name: string, rect?: any): void {
    const layer = this.layers.get(name)
    if (layer) {
      layer.markDirty(rect)
      this.scheduleRender()
    }
  }

  /**
   * Marca todas as layers como dirty
   */
  markAllDirty(): void {
    this.layers.forEach(layer => layer.markDirty())
    this.scheduleRender()
  }

  /**
   * Agenda renderização no próximo frame
   */
  private scheduleRender(): void {
    if (this.animationFrameId !== null) return

    this.animationFrameId = requestAnimationFrame(() => {
      this.render()
      this.animationFrameId = null
    })
  }

  /**
   * Renderiza todas as layers dirty
   */
  render(): void {
    // Renderizar apenas layers que estão dirty
    this.layers.forEach(layer => {
      if (layer.isDirty) {
        const dirtyRect = layer.getDirtyRect()

        // Limpar região dirty ou tudo
        layer.clear(dirtyRect || undefined)

        // Renderizar
        layer.render()

        // Limpar flag dirty
        layer.isDirty = false
        layer.clearDirtyRect()
      }
    })
  }

  /**
   * Força renderização completa
   */
  forceRender(): void {
    this.markAllDirty()
    this.render()
  }

  /**
   * Redimensiona todas as layers
   */
  resize(width: number, height: number): void {
    // Atualizar container
    this.container.style.width = `${width}px`
    this.container.style.height = `${height}px`

    // Redimensionar todas as layers
    this.layers.forEach(layer => {
      layer.resize(width, height)
    })

    // Forçar re-render
    this.forceRender()
  }

  /**
   * Atualiza tema
   */
  updateTheme(theme: any): void {
    this.theme = theme
    this.markAllDirty()
  }

  /**
   * Limpa todas as layers
   */
  clear(): void {
    this.layers.forEach(layer => layer.clear())
  }

  /**
   * Obtém o ViewportManager
   */
  getViewportManager(): ViewportManager {
    return this.viewportManager
  }

  /**
   * Atualiza o número de candles
   */
  updateDataLength(length: number): void {
    this.viewportManager.setDataLength(length)
  }

  /**
   * Aplica zoom
   */
  zoom(delta: number, centerX?: number): void {
    this.viewportManager.zoom(delta, centerX)
  }

  /**
   * Aplica pan
   */
  pan(deltaCandles: number): void {
    this.viewportManager.pan(deltaCandles)
  }

  /**
   * Move para os candles mais recentes
   */
  goToLatest(): void {
    this.viewportManager.goToLatest()
  }

  /**
   * Destrói o manager
   */
  destroy(): void {
    console.log('🔥🔥🔥 [LayerManager] DESTROY CHAMADO - CÓDIGO NOVO V2 🔥🔥🔥')

    // Remover listener do viewport
    this.viewportManager.removeListener(this)

    // Cancelar animação pendente
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId)
      this.animationFrameId = null
    }

    // Limpar layers de forma segura para React
    this.layers.forEach(layer => {
      const canvas = layer.getCanvas()
      // ✅ VERIFICAR se o canvas ainda está no DOM antes de remover
      if (canvas && canvas.parentNode === this.container) {
        try {
          this.container.removeChild(canvas)
        } catch (e) {
          console.warn('[LayerManager] Canvas já foi removido:', e)
        }
      }
    })
    this.layers.clear()
  }
}
