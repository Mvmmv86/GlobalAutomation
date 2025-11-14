/**
 * Layer - Base class for all canvas layers
 * Optimized multi-canvas architecture with DIRTY REGIONS
 */

export interface DirtyRect {
  x: number
  y: number
  width: number
  height: number
}

export abstract class Layer {
  protected canvas: HTMLCanvasElement
  protected ctx: CanvasRenderingContext2D
  public isDirty: boolean = true
  protected zIndex: number
  protected visible: boolean = true
  protected name: string
  protected dirtyRect: DirtyRect | null = null

  constructor(name: string, zIndex: number) {
    this.name = name
    this.zIndex = zIndex
    this.canvas = document.createElement('canvas')

    // Otimização: desynchronized = true para melhor performance
    const context = this.canvas.getContext('2d', {
      alpha: zIndex > 0, // Apenas background sem alpha
      desynchronized: true, // Performance boost
      willReadFrequently: false // Otimização para write-only
    })

    if (!context) {
      throw new Error(`Could not get 2D context for layer ${name}`)
    }

    this.ctx = context
    this.setupCanvas()
  }

  /**
   * Setup canvas com posicionamento absoluto e z-index
   */
  private setupCanvas(): void {
    this.canvas.style.position = 'absolute'
    this.canvas.style.top = '0'
    this.canvas.style.left = '0'
    this.canvas.style.zIndex = this.zIndex.toString()

    // Apenas a layer de interação recebe eventos
    if (this.name !== 'interaction') {
      this.canvas.style.pointerEvents = 'none'
    }

    // Prevenir seleção de texto
    this.canvas.style.userSelect = 'none'
    this.canvas.style.webkitUserSelect = 'none'
  }

  /**
   * Redimensiona o canvas
   */
  resize(width: number, height: number): void {
    const dpr = window.devicePixelRatio || 1

    // Ajustar para device pixel ratio (displays retina)
    this.canvas.width = width * dpr
    this.canvas.height = height * dpr

    // Tamanho CSS
    this.canvas.style.width = `${width}px`
    this.canvas.style.height = `${height}px`

    // Escalar contexto
    this.ctx.scale(dpr, dpr)

    // Configurações de qualidade
    this.ctx.imageSmoothingEnabled = true
    this.ctx.imageSmoothingQuality = 'high'

    this.markDirty()
  }

  /**
   * Marca layer como dirty (precisa ser redesenhada)
   * @param rect - Região específica que precisa ser redesenhada (opcional)
   */
  markDirty(rect?: DirtyRect): void {
    this.isDirty = true

    if (rect) {
      // Se já existe uma dirty region, fazer merge
      if (this.dirtyRect) {
        this.dirtyRect = this.mergeDirtyRects(this.dirtyRect, rect)
      } else {
        this.dirtyRect = rect
      }
    } else {
      // null = redesenhar tudo
      this.dirtyRect = null
    }
  }

  /**
   * Faz merge de duas dirty regions em uma bounding box
   */
  private mergeDirtyRects(rect1: DirtyRect, rect2: DirtyRect): DirtyRect {
    const x1 = Math.min(rect1.x, rect2.x)
    const y1 = Math.min(rect1.y, rect2.y)
    const x2 = Math.max(rect1.x + rect1.width, rect2.x + rect2.width)
    const y2 = Math.max(rect1.y + rect1.height, rect2.y + rect2.height)

    return {
      x: x1,
      y: y1,
      width: x2 - x1,
      height: y2 - y1
    }
  }

  /**
   * Retorna a dirty region atual (ou null se full repaint)
   */
  getDirtyRect(): DirtyRect | null {
    return this.dirtyRect
  }

  /**
   * Limpa a dirty region (após renderizar)
   */
  clearDirtyRect(): void {
    this.dirtyRect = null
  }

  /**
   * Limpa o canvas (ou apenas uma região específica)
   * @param rect - Região para limpar (opcional, se não fornecida limpa tudo)
   */
  clear(rect?: DirtyRect): void {
    if (rect) {
      // Limpar apenas a dirty region
      this.ctx.clearRect(rect.x, rect.y, rect.width, rect.height)
    } else {
      // Limpar canvas inteiro
      const width = this.canvas.width / (window.devicePixelRatio || 1)
      const height = this.canvas.height / (window.devicePixelRatio || 1)
      this.ctx.clearRect(0, 0, width, height)
    }
  }

  /**
   * Método abstrato de renderização (cada layer implementa)
   */
  abstract render(): void

  /**
   * Retorna o canvas
   */
  getCanvas(): HTMLCanvasElement {
    return this.canvas
  }

  /**
   * Retorna o contexto
   */
  getContext(): CanvasRenderingContext2D {
    return this.ctx
  }

  /**
   * Retorna se está dirty
   */
  get dirty(): boolean {
    return this.isDirty
  }

  /**
   * Define visibilidade
   */
  setVisible(visible: boolean): void {
    this.visible = visible
    this.canvas.style.display = visible ? 'block' : 'none'
    if (visible) {
      this.markDirty()
    }
  }

  /**
   * Retorna nome da layer
   */
  getName(): string {
    return this.name
  }
}
