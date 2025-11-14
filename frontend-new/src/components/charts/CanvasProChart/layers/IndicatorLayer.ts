/**
 * IndicatorLayer - Camada para renderizar indicadores técnicos
 */

import { Layer } from '../core/Layer'
import { ChartEngine } from '../Engine'
import { IndicatorEngine } from '../indicators/IndicatorEngine'
import { IndicatorRenderer } from '../renderers/IndicatorRenderer'
import { AnyIndicatorConfig, IndicatorResult } from '../indicators/types'

export class IndicatorLayer extends Layer {
  private indicatorEngine: IndicatorEngine
  private indicatorRenderer: IndicatorRenderer | null = null
  private engine: ChartEngine | null = null
  private indicators: AnyIndicatorConfig[] = []
  private cachedResults: Map<string, IndicatorResult> = new Map()
  private isCalculating: boolean = false

  constructor(name: string, zIndex: number, useWorker: boolean = true) {
    super(name, zIndex)
    // Criar IndicatorEngine com Worker habilitado por padrão
    this.indicatorEngine = new IndicatorEngine({ useWorker })
    console.log(`📊 [IndicatorLayer] Created with Worker: ${this.indicatorEngine.isUsingWorker()}`)
  }

  /**
   * Inicializa com o ChartEngine
   */
  initialize(engine: ChartEngine): void {
    this.engine = engine
    this.indicatorRenderer = new IndicatorRenderer(engine)
    this.markDirty()
  }

  /**
   * Adiciona um indicador
   */
  addIndicator(config: AnyIndicatorConfig): void {
    // Verificar se já existe
    const existingIndex = this.indicators.findIndex(i => i.id === config.id)

    if (existingIndex >= 0) {
      // Atualizar existente
      this.indicators[existingIndex] = config
    } else {
      // Adicionar novo
      this.indicators.push(config)
    }

    // Invalidar cache
    this.cachedResults.delete(config.id)
    this.markDirty()
  }

  /**
   * Remove um indicador
   */
  removeIndicator(id: string): void {
    this.indicators = this.indicators.filter(i => i.id !== id)
    this.cachedResults.delete(id)
    this.markDirty()
  }

  /**
   * Atualiza configuração de um indicador
   */
  updateIndicator(id: string, updates: Partial<AnyIndicatorConfig>): void {
    const indicator = this.indicators.find(i => i.id === id)
    if (indicator) {
      Object.assign(indicator, updates)
      this.cachedResults.delete(id)
      this.markDirty()
    }
  }

  /**
   * Obtém todos os indicadores
   */
  getIndicators(): AnyIndicatorConfig[] {
    return [...this.indicators]
  }

  /**
   * Obtém um indicador específico
   */
  getIndicator(id: string): AnyIndicatorConfig | undefined {
    return this.indicators.find(i => i.id === id)
  }

  /**
   * Limpa todos os indicadores
   */
  clearIndicators(): void {
    this.indicators = []
    this.cachedResults.clear()
    this.markDirty()
  }

  /**
   * Renderiza os indicadores (APENAS OVERLAY)
   * Indicadores 'separate' são renderizados em SeparatePanelLayer
   * Agora assíncrono para suportar Workers
   */
  async render(): Promise<void> {
    if (!this.isDirty || this.isCalculating) {
      return
    }

    // Verificar se está inicializado
    if (!this.engine || !this.indicatorRenderer) {
      console.warn('⚠️ [IndicatorLayer] Not initialized')
      return
    }

    // Obter candles do engine
    const candles = this.engine.getCandles()
    if (candles.length === 0) {
      return
    }

    // Obter dirty rect
    const dirtyRect = this.getDirtyRect()

    // Limpar camada (apenas dirty region se houver)
    this.clear(dirtyRect)

    // Filtrar APENAS indicadores habilitados do tipo 'overlay'
    // Indicadores 'separate' (RSI, MACD, etc) vão para painéis próprios
    const overlayIndicators = this.indicators.filter(
      i => i.enabled && i.displayType === 'overlay'
    )

    if (overlayIndicators.length === 0) {
      this.clearDirtyRect()
      return
    }

    console.log(`🎨 [IndicatorLayer] Rendering ${overlayIndicators.length} overlay indicators`)

    // Marcar que está calculando
    this.isCalculating = true

    try {
      // Separar indicadores que precisam recalcular
      const toCalculate: AnyIndicatorConfig[] = []
      const cached: IndicatorResult[] = []

      for (const indicator of overlayIndicators) {
        const cachedResult = this.cachedResults.get(indicator.id)
        if (cachedResult) {
          cached.push(cachedResult)
        } else {
          toCalculate.push(indicator)
        }
      }

      // Calcular indicadores em batch usando Worker se disponível
      let newResults: IndicatorResult[] = []
      if (toCalculate.length > 0) {
        console.log(`📊 [IndicatorLayer] Calculating ${toCalculate.length} indicators with Worker`)
        newResults = await this.indicatorEngine.calculateMultiple(toCalculate, candles)

        // Adicionar ao cache
        for (const result of newResults) {
          const indicator = toCalculate.find(i => i.id === result.id)
          if (indicator) {
            this.cachedResults.set(indicator.id, result)
          }
        }
      }

      // Combinar resultados
      const allResults = [...cached, ...newResults]

      // Renderizar todos os indicadores overlay
      if (allResults.length > 0) {
        this.indicatorRenderer.renderMultiple(this.ctx, allResults, overlayIndicators)
      }
    } catch (error) {
      console.error('❌ [IndicatorLayer] Error calculating indicators:', error)
    } finally {
      this.isCalculating = false
      // Limpar dirty flag
      this.clearDirtyRect()
    }
  }

  /**
   * Obtém apenas indicadores do tipo 'separate'
   * Útil para criar painéis separados
   */
  getSeparateIndicators(): AnyIndicatorConfig[] {
    return this.indicators.filter(i => i.displayType === 'separate')
  }

  /**
   * Obtém apenas indicadores do tipo 'overlay'
   */
  getOverlayIndicators(): AnyIndicatorConfig[] {
    return this.indicators.filter(i => i.displayType === 'overlay')
  }

  /**
   * Invalida cache de indicadores (chamar quando candles mudarem)
   */
  invalidateCache(): void {
    this.cachedResults.clear()
    this.markDirty()
  }

  /**
   * Resize - invalida cache pois coordenadas mudam
   */
  resize(width: number, height: number): void {
    super.resize(width, height)
    this.invalidateCache()
  }

  /**
   * Destroy - cleanup e libera Workers
   */
  destroy(): void {
    // Limpar cache
    this.cachedResults.clear()

    // Destruir o IndicatorEngine e seus Workers
    this.indicatorEngine.destroy()

    // Limpar referências
    this.indicators = []
    this.engine = null
    this.indicatorRenderer = null

    console.log('🧹 [IndicatorLayer] Destroyed and cleaned up Workers')
  }
}
