/**
 * LayerManagerMinimal - FASE 2 → FASE 5
 *
 * Gerenciador ultra-simplificado de layers
 * ATUALIZADO PARA FASE 5: Renderização de Candles
 *
 * Features:
 * - 2 layers (background + candles)
 * - Grid profissional com eixos X/Y
 * - Renderização de candles
 * - Criação/destruição segura
 */

import { ChartTheme } from '../theme'
import { GridRendererMinimal } from './GridRendererMinimal'
import { CandleRendererMinimal } from './CandleRendererMinimal'
import type { CandleData } from './DataManagerMinimal'

/**
 * Layer básica - FASE 4: Grid Profissional
 */
class BackgroundLayer {
  private canvas: HTMLCanvasElement
  private theme: ChartTheme
  private width: number
  private height: number
  private gridRenderer: GridRendererMinimal
  private priceMin: number = 0
  private priceMax: number = 0
  private timeStart: number = 0
  private timeEnd: number = 0

  constructor(width: number, height: number, theme: ChartTheme) {
    this.width = width
    this.height = height
    this.theme = theme

    // Criar canvas
    this.canvas = document.createElement('canvas')
    this.canvas.width = Math.floor(width)
    this.canvas.height = Math.floor(height)
    this.canvas.style.position = 'absolute'
    this.canvas.style.top = '0'
    this.canvas.style.left = '0'
    this.canvas.style.width = '100%'
    this.canvas.style.height = '100%'
    this.canvas.style.zIndex = '0'

    // Criar GridRenderer
    this.gridRenderer = new GridRendererMinimal(this.canvas, theme)

    console.log('✅ [BackgroundLayer] Layer criada com GridRenderer:', { width, height })
  }

  /**
   * Renderiza o background com grid profissional
   */
  render(priceMin?: number, priceMax?: number, timeStart?: number, timeEnd?: number): void {
    const w = Math.floor(this.width)
    const h = Math.floor(this.height)

    // Se não tem dados de preço/tempo, usar valores padrão
    if (priceMin !== undefined) this.priceMin = priceMin
    if (priceMax !== undefined) this.priceMax = priceMax
    if (timeStart !== undefined) this.timeStart = timeStart
    if (timeEnd !== undefined) this.timeEnd = timeEnd

    // Renderizar grid profissional
    if (this.priceMin > 0 && this.priceMax > 0 && this.timeStart > 0 && this.timeEnd > 0) {
      this.gridRenderer.render({
        width: w,
        height: h,
        priceMin: this.priceMin,
        priceMax: this.priceMax,
        timeStart: this.timeStart,
        timeEnd: this.timeEnd
      })
    } else {
      // Se ainda não tem dados, mostrar grid vazio
      const ctx = this.canvas.getContext('2d')
      if (ctx) {
        ctx.clearRect(0, 0, w, h)
        ctx.fillStyle = this.theme.background
        ctx.fillRect(0, 0, w, h)

        ctx.fillStyle = this.theme.text.primary
        ctx.font = '14px monospace'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText('Aguardando dados...', w / 2, h / 2)
      }
    }
  }

  /**
   * Redimensiona a layer
   */
  resize(width: number, height: number): void {
    this.width = width
    this.height = height
    this.canvas.width = Math.floor(width)
    this.canvas.height = Math.floor(height)
    console.log(`📐 [BackgroundLayer] Resize: ${width}x${height}`)

    // Re-renderizar após resize
    this.render()
  }

  /**
   * Retorna o canvas
   */
  getCanvas(): HTMLCanvasElement {
    return this.canvas
  }

  /**
   * Cleanup
   */
  destroy(): void {
    console.log('🧹 [BackgroundLayer] Destruindo layer')
    this.gridRenderer.destroy()
    // Não remover do DOM aqui - LayerManagerMinimal cuida disso
  }
}

/**
 * Layer de Candles - FASE 5: Renderização de Candles
 */
class CandlesLayer {
  private canvas: HTMLCanvasElement
  private theme: ChartTheme
  private width: number
  private height: number
  private candleRenderer: CandleRendererMinimal
  private priceMin: number = 0
  private priceMax: number = 0
  private timeStart: number = 0
  private timeEnd: number = 0

  constructor(width: number, height: number, theme: ChartTheme) {
    this.width = width
    this.height = height
    this.theme = theme

    // Criar canvas
    this.canvas = document.createElement('canvas')
    this.canvas.width = Math.floor(width)
    this.canvas.height = Math.floor(height)
    this.canvas.style.position = 'absolute'
    this.canvas.style.top = '0'
    this.canvas.style.left = '0'
    this.canvas.style.width = '100%'
    this.canvas.style.height = '100%'
    this.canvas.style.zIndex = '1' // Acima do background (z-index=0)

    // Criar CandleRenderer
    this.candleRenderer = new CandleRendererMinimal(this.canvas, theme)

    console.log('✅ [CandlesLayer] Layer criada com CandleRenderer:', { width, height })
  }

  /**
   * Renderiza os candles
   */
  render(candles: CandleData[], priceMin: number, priceMax: number, timeStart: number, timeEnd: number): void {
    const w = Math.floor(this.width)
    const h = Math.floor(this.height)

    // Limpar canvas
    this.candleRenderer.clear()

    // Se não tem dados, não renderizar
    if (candles.length === 0 || priceMin === 0 || priceMax === 0) {
      return
    }

    // Armazenar valores
    this.priceMin = priceMin
    this.priceMax = priceMax
    this.timeStart = timeStart
    this.timeEnd = timeEnd

    // Renderizar candles
    this.candleRenderer.render({
      width: w,
      height: h,
      candles,
      priceMin,
      priceMax,
      timeStart,
      timeEnd
    })
  }

  /**
   * Redimensiona a layer
   */
  resize(width: number, height: number): void {
    this.width = width
    this.height = height
    this.canvas.width = Math.floor(width)
    this.canvas.height = Math.floor(height)
    console.log(`📐 [CandlesLayer] Resize: ${width}x${height}`)
  }

  /**
   * Retorna o canvas
   */
  getCanvas(): HTMLCanvasElement {
    return this.canvas
  }

  /**
   * Cleanup
   */
  destroy(): void {
    console.log('🧹 [CandlesLayer] Destruindo layer')
    this.candleRenderer.destroy()
    // Não remover do DOM aqui - LayerManagerMinimal cuida disso
  }
}

/**
 * LayerManagerMinimal - Gerenciador ultra-simplificado
 */
export class LayerManagerMinimal {
  private container: HTMLDivElement
  private backgroundLayer: BackgroundLayer | null = null
  private candlesLayer: CandlesLayer | null = null
  private theme: ChartTheme
  private resizeObserver: ResizeObserver | null = null

  constructor(container: HTMLDivElement, theme: ChartTheme) {
    this.container = container
    this.theme = theme

    console.log('🎨 [LayerManagerMinimal] Inicializando...')

    // ✅ Limpar container (remover apenas canvas anteriores)
    if (this.container.childNodes.length > 0) {
      Array.from(this.container.childNodes).forEach(node => {
        if (node instanceof HTMLCanvasElement) {
          try {
            this.container.removeChild(node)
          } catch (e) {
            console.warn('[LayerManagerMinimal] Canvas já removido')
          }
        }
      })
    }

    this.container.style.position = 'relative'

    // Obter dimensões
    const rect = this.container.getBoundingClientRect()

    if (!rect.width || !rect.height || rect.width < 100 || rect.height < 100) {
      console.warn('⚠️ [LayerManagerMinimal] Dimensões inválidas:', rect)
      return
    }

    // Criar background layer
    this.backgroundLayer = new BackgroundLayer(rect.width, rect.height, this.theme)
    this.container.appendChild(this.backgroundLayer.getCanvas())

    // ✅ FASE 5: Criar candles layer
    this.candlesLayer = new CandlesLayer(rect.width, rect.height, this.theme)
    this.container.appendChild(this.candlesLayer.getCanvas())

    // Renderizar background
    this.backgroundLayer.render()

    // Setup resize observer
    this.setupResizeObserver()

    console.log('✅ [LayerManagerMinimal] Inicializado com 2 layers (background + candles)')
  }

  /**
   * Setup ResizeObserver
   */
  private setupResizeObserver(): void {
    this.resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect

        if (width < 100 || height < 100) return

        console.log(`📐 [LayerManagerMinimal] Container resize: ${width}x${height}`)

        if (this.backgroundLayer) {
          this.backgroundLayer.resize(width, height)
          this.backgroundLayer.render()
        }

        if (this.candlesLayer) {
          this.candlesLayer.resize(width, height)
          // Re-renderizar candles será feito no próximo updateCandles()
        }
      }
    })

    this.resizeObserver.observe(this.container)
  }

  /**
   * Atualizar grid com dados de preço/tempo
   */
  updateGrid(priceMin: number, priceMax: number, timeStart: number, timeEnd: number): void {
    if (this.backgroundLayer) {
      this.backgroundLayer.render(priceMin, priceMax, timeStart, timeEnd)
    }
  }

  /**
   * ✅ FASE 5: Atualizar candles
   */
  updateCandles(candles: CandleData[], priceMin: number, priceMax: number, timeStart: number, timeEnd: number): void {
    if (this.candlesLayer) {
      this.candlesLayer.render(candles, priceMin, priceMax, timeStart, timeEnd)
    }
  }

  /**
   * @deprecated Usar updateGrid() em vez disso
   */
  updateMessage(message: string): void {
    // Manter compatibilidade com FASE 3
    // Não faz nada - updateGrid() deve ser usado agora
  }

  /**
   * Cleanup completo
   */
  destroy(): void {
    console.log('🧹 [LayerManagerMinimal] Destruindo LayerManager')

    // Desconectar resize observer
    if (this.resizeObserver) {
      this.resizeObserver.disconnect()
      this.resizeObserver = null
    }

    // Destruir background layer
    if (this.backgroundLayer) {
      const canvas = this.backgroundLayer.getCanvas()

      // ✅ Remover canvas do DOM (verificar se ainda está lá)
      if (canvas && canvas.parentNode === this.container) {
        try {
          this.container.removeChild(canvas)
          console.log('✅ [LayerManagerMinimal] Background canvas removido do DOM')
        } catch (e) {
          console.warn('[LayerManagerMinimal] Background canvas já foi removido:', e)
        }
      }

      this.backgroundLayer.destroy()
      this.backgroundLayer = null
    }

    // ✅ FASE 5: Destruir candles layer
    if (this.candlesLayer) {
      const canvas = this.candlesLayer.getCanvas()

      // ✅ Remover canvas do DOM (verificar se ainda está lá)
      if (canvas && canvas.parentNode === this.container) {
        try {
          this.container.removeChild(canvas)
          console.log('✅ [LayerManagerMinimal] Candles canvas removido do DOM')
        } catch (e) {
          console.warn('[LayerManagerMinimal] Candles canvas já foi removido:', e)
        }
      }

      this.candlesLayer.destroy()
      this.candlesLayer = null
    }

    console.log('✅ [LayerManagerMinimal] Cleanup completo')
  }
}
