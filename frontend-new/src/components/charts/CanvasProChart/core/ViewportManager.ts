/**
 * ViewportManager - Sistema centralizado de gerenciamento de viewport
 * Sincroniza zoom e pan entre todos os painéis
 */

import { Viewport } from '../types'

export interface ViewportListener {
  onViewportChange: (viewport: Viewport) => void
}

export class ViewportManager {
  private viewport: Viewport
  private listeners: Set<ViewportListener> = new Set()
  private dataLength: number = 0
  private candleWidth: number = 10
  private minCandleWidth: number = 2
  private maxCandleWidth: number = 50

  constructor(width: number, height: number) {
    this.viewport = {
      startIndex: 0,
      endIndex: 100,
      scale: 1,
      offset: { x: 0, y: 0 },
      width,
      height
    }
  }

  /**
   * Registra um listener para mudanças no viewport
   */
  addListener(listener: ViewportListener): void {
    this.listeners.add(listener)
    // Notifica imediatamente com o viewport atual
    listener.onViewportChange(this.viewport)
  }

  /**
   * Remove um listener
   */
  removeListener(listener: ViewportListener): void {
    this.listeners.delete(listener)
  }

  /**
   * Obtém o viewport atual
   */
  getViewport(): Viewport {
    return { ...this.viewport }
  }

  /**
   * Atualiza o viewport e notifica todos os listeners
   */
  private updateViewport(updates: Partial<Viewport>): void {
    const oldViewport = { ...this.viewport }
    this.viewport = { ...this.viewport, ...updates }

    // Validar limites
    this.validateViewport()

    // Só notificar se houve mudança real
    if (JSON.stringify(oldViewport) !== JSON.stringify(this.viewport)) {
      this.notifyListeners()
    }
  }

  /**
   * Valida e ajusta os limites do viewport
   */
  private validateViewport(): void {
    // Garantir índices válidos
    this.viewport.startIndex = Math.max(0, this.viewport.startIndex)
    this.viewport.endIndex = Math.min(this.dataLength - 1, this.viewport.endIndex)

    // Garantir pelo menos 10 candles visíveis
    if (this.viewport.endIndex - this.viewport.startIndex < 10) {
      this.viewport.startIndex = Math.max(0, this.viewport.endIndex - 10)
    }

    // Ajustar scale baseado na largura dos candles
    const visibleCandles = this.viewport.endIndex - this.viewport.startIndex + 1
    if (visibleCandles > 0) {
      this.candleWidth = Math.floor(this.viewport.width / visibleCandles)
      this.candleWidth = Math.max(this.minCandleWidth, Math.min(this.maxCandleWidth, this.candleWidth))
      this.viewport.scale = this.candleWidth / 10 // 10 é a largura base
    }
  }

  /**
   * Notifica todos os listeners sobre mudança no viewport
   */
  private notifyListeners(): void {
    const viewportCopy = { ...this.viewport }
    this.listeners.forEach(listener => {
      listener.onViewportChange(viewportCopy)
    })
  }

  /**
   * Atualiza o tamanho total de dados
   */
  setDataLength(length: number): void {
    this.dataLength = length

    // Se é a primeira vez, posicionar no final
    if (this.viewport.endIndex === 100 && length > 100) {
      this.viewport.endIndex = length - 1
      this.viewport.startIndex = Math.max(0, length - 100)
    }

    this.validateViewport()
    this.notifyListeners()
  }

  /**
   * Aplica zoom
   * @param delta Valor do zoom (negativo = zoom in, positivo = zoom out)
   * @param centerX Ponto central do zoom no eixo X
   */
  zoom(delta: number, centerX?: number): void {
    const visibleCandles = this.viewport.endIndex - this.viewport.startIndex + 1
    const newVisibleCandles = Math.round(visibleCandles * (1 + delta))

    // Limitar entre 10 e todos os candles
    const clampedVisible = Math.max(10, Math.min(this.dataLength, newVisibleCandles))

    if (centerX !== undefined) {
      // Zoom com centro específico
      const ratio = centerX / this.viewport.width
      const pivotIndex = this.viewport.startIndex + Math.floor(ratio * visibleCandles)

      const newStart = pivotIndex - Math.floor(clampedVisible * ratio)
      const newEnd = newStart + clampedVisible - 1

      this.updateViewport({
        startIndex: newStart,
        endIndex: newEnd
      })
    } else {
      // Zoom centralizado
      const center = (this.viewport.startIndex + this.viewport.endIndex) / 2
      const halfVisible = clampedVisible / 2

      this.updateViewport({
        startIndex: Math.floor(center - halfVisible),
        endIndex: Math.floor(center + halfVisible)
      })
    }
  }

  /**
   * Aplica pan (movimento horizontal)
   * @param deltaCandles Número de candles para mover (negativo = esquerda)
   */
  pan(deltaCandles: number): void {
    this.updateViewport({
      startIndex: this.viewport.startIndex + deltaCandles,
      endIndex: this.viewport.endIndex + deltaCandles
    })
  }

  /**
   * Move para o final dos dados (candles mais recentes)
   */
  goToLatest(): void {
    const visibleCandles = this.viewport.endIndex - this.viewport.startIndex + 1
    this.updateViewport({
      endIndex: this.dataLength - 1,
      startIndex: this.dataLength - visibleCandles
    })
  }

  /**
   * Move para o início dos dados
   */
  goToStart(): void {
    const visibleCandles = this.viewport.endIndex - this.viewport.startIndex + 1
    this.updateViewport({
      startIndex: 0,
      endIndex: Math.min(visibleCandles - 1, this.dataLength - 1)
    })
  }

  /**
   * Redimensiona o viewport
   */
  resize(width: number, height: number): void {
    this.updateViewport({
      width,
      height
    })
  }

  /**
   * Obtém a largura atual dos candles
   */
  getCandleWidth(): number {
    return this.candleWidth
  }

  /**
   * Converte índice para coordenada X
   */
  indexToX(index: number): number {
    const visibleIndex = index - this.viewport.startIndex
    return visibleIndex * this.candleWidth
  }

  /**
   * Converte coordenada X para índice
   */
  xToIndex(x: number): number {
    const visibleIndex = Math.floor(x / this.candleWidth)
    return this.viewport.startIndex + visibleIndex
  }

  /**
   * Obtém o range visível
   */
  getVisibleRange(): { start: number; end: number } {
    return {
      start: this.viewport.startIndex,
      end: this.viewport.endIndex
    }
  }

  /**
   * Define o range visível
   */
  setVisibleRange(start: number, end: number): void {
    this.updateViewport({
      startIndex: start,
      endIndex: end
    })
  }
}