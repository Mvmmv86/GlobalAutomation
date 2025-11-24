/**
 * DrawingManager - Gerenciador Central de Ferramentas de Desenho
 * FASE 11: Sistema profissional de desenho no gráfico
 */

import {
  AnyDrawing,
  DrawingType,
  DrawingState,
  DrawingManagerState,
  ChartPoint,
  CanvasPoint,
  AnchorPoint,
  TrendLineDrawing,
  HorizontalLineDrawing,
  VerticalLineDrawing,
  RectangleDrawing,
  FibonacciDrawing,
  TextDrawing,
  ArrowDrawing,
  ChannelDrawing,
  generateDrawingId,
  DEFAULT_DRAWING_STYLES,
  DEFAULT_FIBONACCI_LEVELS,
  distance,
  isPointNearLine,
  isPointInRect
} from './types'

export interface DrawingManagerConfig {
  hitThreshold?: number        // Distância para detectar clique (px)
  anchorRadius?: number        // Raio dos pontos de âncora (px)
  minDragDistance?: number     // Distância mínima para drag
}

const DEFAULT_CONFIG: DrawingManagerConfig = {
  hitThreshold: 8,
  anchorRadius: 6,
  minDragDistance: 3
}

export class DrawingManager {
  private state: DrawingManagerState
  private config: DrawingManagerConfig
  private listeners: Map<string, Set<Function>>

  constructor(config: Partial<DrawingManagerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config }
    this.state = {
      drawings: [],
      activeDrawingType: null,
      selectedDrawingId: null,
      state: DrawingState.IDLE,
      tempPoints: [],
      hoveredDrawingId: null,
      hoveredAnchor: null
    }
    this.listeners = new Map()
  }

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  getState(): DrawingManagerState {
    return { ...this.state }
  }

  getDrawings(): AnyDrawing[] {
    return [...this.state.drawings]
  }

  getDrawingById(id: string): AnyDrawing | undefined {
    return this.state.drawings.find(d => d.id === id)
  }

  getSelectedDrawing(): AnyDrawing | undefined {
    if (!this.state.selectedDrawingId) return undefined
    return this.getDrawingById(this.state.selectedDrawingId)
  }

  // ============================================================================
  // DRAWING CREATION
  // ============================================================================

  /**
   * Inicia a criação de um novo desenho
   */
  startDrawing(type: DrawingType): void {
    console.log(`🎨 [DrawingManager] Starting ${type}`)
    this.state.activeDrawingType = type
    this.state.state = DrawingState.CREATING
    this.state.tempPoints = []
    this.emit('stateChange', this.state)
  }

  /**
   * Cancela a criação atual
   */
  cancelDrawing(): void {
    console.log('❌ [DrawingManager] Cancelled drawing')
    this.state.activeDrawingType = null
    this.state.state = DrawingState.IDLE
    this.state.tempPoints = []
    this.emit('stateChange', this.state)
  }

  /**
   * Adiciona um ponto durante a criação
   * Retorna true se o desenho foi completado
   */
  addPoint(point: ChartPoint): boolean {
    if (this.state.state !== DrawingState.CREATING || !this.state.activeDrawingType) {
      return false
    }

    this.state.tempPoints.push(point)
    const pointsNeeded = this.getRequiredPoints(this.state.activeDrawingType)

    console.log(`📍 [DrawingManager] Added point (${this.state.tempPoints.length}/${pointsNeeded})`, point)

    // Se temos pontos suficientes, criar o desenho
    if (this.state.tempPoints.length >= pointsNeeded) {
      this.completeDrawing()
      return true
    }

    this.emit('stateChange', this.state)
    return false
  }

  /**
   * Finaliza e adiciona o desenho
   */
  private completeDrawing(): void {
    if (!this.state.activeDrawingType || this.state.tempPoints.length === 0) {
      return
    }

    const drawing = this.createDrawingFromPoints(
      this.state.activeDrawingType,
      this.state.tempPoints
    )

    if (drawing) {
      this.state.drawings.push(drawing)
      console.log(`✅ [DrawingManager] Created ${drawing.type}:`, drawing.id)
      this.emit('drawingAdded', drawing)
    }

    // Reset state
    this.state.activeDrawingType = null
    this.state.state = DrawingState.IDLE
    this.state.tempPoints = []
    this.emit('stateChange', this.state)
  }

  /**
   * Cria objeto de desenho a partir dos pontos
   */
  private createDrawingFromPoints(type: DrawingType, points: ChartPoint[]): AnyDrawing | null {
    const id = generateDrawingId(type)
    const baseDrawing = {
      id,
      type,
      points,
      style: DEFAULT_DRAWING_STYLES[type],
      locked: false,
      visible: true,
      zIndex: this.state.drawings.length,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    switch (type) {
      case DrawingType.TREND_LINE:
        return {
          ...baseDrawing,
          type: DrawingType.TREND_LINE,
          points: points.slice(0, 2) as [ChartPoint, ChartPoint],
          extendLeft: false,
          extendRight: false,
          showAngle: true,
          showDistance: true
        } as TrendLineDrawing

      case DrawingType.HORIZONTAL_LINE:
        return {
          ...baseDrawing,
          type: DrawingType.HORIZONTAL_LINE,
          points: [points[0]] as [ChartPoint]
        } as HorizontalLineDrawing

      case DrawingType.VERTICAL_LINE:
        return {
          ...baseDrawing,
          type: DrawingType.VERTICAL_LINE,
          points: [points[0]] as [ChartPoint]
        } as VerticalLineDrawing

      case DrawingType.RECTANGLE:
        return {
          ...baseDrawing,
          type: DrawingType.RECTANGLE,
          points: points.slice(0, 2) as [ChartPoint, ChartPoint],
          filled: true,
          showPriceRange: true
        } as RectangleDrawing

      case DrawingType.FIBONACCI_RETRACEMENT:
        return {
          ...baseDrawing,
          type: DrawingType.FIBONACCI_RETRACEMENT,
          points: points.slice(0, 2) as [ChartPoint, ChartPoint],
          levels: DEFAULT_FIBONACCI_LEVELS.map(l => ({ ...l })),
          showLabels: true,
          showPrices: true
        } as FibonacciDrawing

      case DrawingType.TEXT:
        return {
          ...baseDrawing,
          type: DrawingType.TEXT,
          points: [points[0]] as [ChartPoint],
          text: 'Text',
          anchor: 'center'
        } as TextDrawing

      case DrawingType.ARROW:
        return {
          ...baseDrawing,
          type: DrawingType.ARROW,
          points: points.slice(0, 2) as [ChartPoint, ChartPoint],
          arrowHeadSize: 10
        } as ArrowDrawing

      case DrawingType.CHANNEL:
        return {
          ...baseDrawing,
          type: DrawingType.CHANNEL,
          points: points.slice(0, 3) as [ChartPoint, ChartPoint, ChartPoint],
          filled: true
        } as ChannelDrawing

      default:
        console.error(`❌ [DrawingManager] Unknown drawing type: ${type}`)
        return null
    }
  }

  /**
   * Retorna o número de pontos necessários para cada tipo de desenho
   */
  private getRequiredPoints(type: DrawingType): number {
    switch (type) {
      case DrawingType.HORIZONTAL_LINE:
      case DrawingType.VERTICAL_LINE:
      case DrawingType.TEXT:
        return 1

      case DrawingType.TREND_LINE:
      case DrawingType.RECTANGLE:
      case DrawingType.FIBONACCI_RETRACEMENT:
      case DrawingType.ARROW:
        return 2

      case DrawingType.CHANNEL:
        return 3

      default:
        return 2
    }
  }

  // ============================================================================
  // DRAWING MANIPULATION
  // ============================================================================

  /**
   * Remove um desenho
   */
  removeDrawing(id: string): boolean {
    const index = this.state.drawings.findIndex(d => d.id === id)
    if (index === -1) return false

    const drawing = this.state.drawings[index]
    this.state.drawings.splice(index, 1)

    console.log(`🗑️ [DrawingManager] Removed ${drawing.type}:`, id)
    this.emit('drawingRemoved', drawing)
    this.emit('stateChange', this.state)
    return true
  }

  /**
   * Limpa todos os desenhos
   */
  clearDrawings(): void {
    const count = this.state.drawings.length
    this.state.drawings = []
    console.log(`🧹 [DrawingManager] Cleared ${count} drawings`)
    this.emit('drawingsCleared')
    this.emit('stateChange', this.state)
  }

  /**
   * Atualiza um desenho
   */
  updateDrawing(id: string, updates: Partial<AnyDrawing>): boolean {
    const index = this.state.drawings.findIndex(d => d.id === id)
    if (index === -1) return false

    this.state.drawings[index] = {
      ...this.state.drawings[index],
      ...updates,
      updatedAt: Date.now()
    }

    console.log(`🔄 [DrawingManager] Updated ${this.state.drawings[index].type}:`, id)
    this.emit('drawingUpdated', this.state.drawings[index])
    this.emit('stateChange', this.state)
    return true
  }

  /**
   * Seleciona um desenho
   */
  selectDrawing(id: string | null): void {
    if (this.state.selectedDrawingId === id) return

    this.state.selectedDrawingId = id
    this.state.state = id ? DrawingState.SELECTED : DrawingState.IDLE

    console.log(`👆 [DrawingManager] Selected:`, id || 'none')
    this.emit('selectionChange', id)
    this.emit('stateChange', this.state)
  }

  /**
   * Move um desenho
   */
  moveDrawing(id: string, deltaX: number, deltaY: number): boolean {
    const drawing = this.getDrawingById(id)
    if (!drawing || drawing.locked) return false

    // Aplicar delta a todos os pontos
    const newPoints = drawing.points.map(p => ({
      timestamp: p.timestamp + deltaX,
      price: p.price + deltaY
    }))

    return this.updateDrawing(id, { points: newPoints } as Partial<AnyDrawing>)
  }

  /**
   * Redimensiona um desenho movendo uma âncora específica
   */
  resizeDrawing(id: string, anchor: AnchorPoint, newPoint: ChartPoint): boolean {
    const drawing = this.getDrawingById(id)
    if (!drawing || drawing.locked) return false

    const newPoints = [...drawing.points]

    switch (anchor) {
      case AnchorPoint.START:
        newPoints[0] = newPoint
        break
      case AnchorPoint.END:
        newPoints[1] = newPoint
        break
      case AnchorPoint.TOP_LEFT:
        newPoints[0] = newPoint
        break
      case AnchorPoint.BOTTOM_RIGHT:
        newPoints[1] = newPoint
        break
      // TODO: Implementar outros anchors conforme necessário
    }

    return this.updateDrawing(id, { points: newPoints } as Partial<AnyDrawing>)
  }

  // ============================================================================
  // HIT DETECTION
  // ============================================================================

  /**
   * Detecta qual desenho está sob o cursor
   */
  hitTest(canvasPoint: CanvasPoint, coordTransform: (cp: ChartPoint) => CanvasPoint): string | null {
    const threshold = this.config.hitThreshold || 8

    // Iterar de trás para frente (desenhos mais recentes primeiro)
    for (let i = this.state.drawings.length - 1; i >= 0; i--) {
      const drawing = this.state.drawings[i]
      if (!drawing.visible) continue

      const canvasPoints = drawing.points.map(coordTransform)

      switch (drawing.type) {
        case DrawingType.TREND_LINE:
        case DrawingType.ARROW:
          if (isPointNearLine(canvasPoint, canvasPoints[0], canvasPoints[1], threshold)) {
            return drawing.id
          }
          break

        case DrawingType.HORIZONTAL_LINE:
          // Linha horizontal atravessa toda a largura
          if (Math.abs(canvasPoint.y - canvasPoints[0].y) <= threshold) {
            return drawing.id
          }
          break

        case DrawingType.VERTICAL_LINE:
          // Linha vertical atravessa toda a altura
          if (Math.abs(canvasPoint.x - canvasPoints[0].x) <= threshold) {
            return drawing.id
          }
          break

        case DrawingType.RECTANGLE:
          const [topLeft, bottomRight] = canvasPoints
          if (isPointInRect(canvasPoint, topLeft, bottomRight)) {
            return drawing.id
          }
          break

        case DrawingType.FIBONACCI_RETRACEMENT:
          // Testar linha principal e linhas de nível
          if (isPointNearLine(canvasPoint, canvasPoints[0], canvasPoints[1], threshold)) {
            return drawing.id
          }
          break

        case DrawingType.TEXT:
          // Testar área de texto (aproximado)
          const textPoint = canvasPoints[0]
          if (distance(canvasPoint, textPoint) <= 50) {
            return drawing.id
          }
          break

        case DrawingType.CHANNEL:
          // Testar linhas do canal
          if (
            isPointNearLine(canvasPoint, canvasPoints[0], canvasPoints[1], threshold) ||
            isPointNearLine(canvasPoint, canvasPoints[1], canvasPoints[2], threshold)
          ) {
            return drawing.id
          }
          break
      }
    }

    return null
  }

  /**
   * Detecta qual âncora está sob o cursor (para resize)
   */
  hitTestAnchor(
    canvasPoint: CanvasPoint,
    drawingId: string,
    coordTransform: (cp: ChartPoint) => CanvasPoint
  ): AnchorPoint | null {
    const drawing = this.getDrawingById(drawingId)
    if (!drawing) return null

    const anchorRadius = this.config.anchorRadius || 6
    const canvasPoints = drawing.points.map(coordTransform)

    // Testar pontos de ancoragem
    if (canvasPoints[0] && distance(canvasPoint, canvasPoints[0]) <= anchorRadius) {
      return AnchorPoint.START
    }

    if (canvasPoints[1] && distance(canvasPoint, canvasPoints[1]) <= anchorRadius) {
      return AnchorPoint.END
    }

    // TODO: Adicionar outros anchors para retângulos, etc.

    return null
  }

  // ============================================================================
  // SERIALIZATION
  // ============================================================================

  /**
   * Exporta todos os desenhos para JSON
   */
  exportDrawings(): string {
    return JSON.stringify({
      version: '1.0',
      drawings: this.state.drawings,
      timestamp: Date.now()
    })
  }

  /**
   * Importa desenhos de JSON
   */
  importDrawings(json: string): boolean {
    try {
      const data = JSON.parse(json)
      if (!data.drawings || !Array.isArray(data.drawings)) {
        console.error('❌ [DrawingManager] Invalid import data')
        return false
      }

      this.state.drawings = data.drawings
      console.log(`📥 [DrawingManager] Imported ${data.drawings.length} drawings`)
      this.emit('drawingsImported', data.drawings)
      this.emit('stateChange', this.state)
      return true
    } catch (error) {
      console.error('❌ [DrawingManager] Import failed:', error)
      return false
    }
  }

  // ============================================================================
  // EVENT SYSTEM
  // ============================================================================

  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(callback)
  }

  off(event: string, callback: Function): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.delete(callback)
    }
  }

  private emit(event: string, ...args: any[]): void {
    const callbacks = this.listeners.get(event)
    if (callbacks) {
      callbacks.forEach(cb => cb(...args))
    }
  }
}
