/**
 * WorkerManager - Gerencia Web Worker com fallback automático
 * Se OffscreenCanvas não for suportado, usa renderização na main thread
 */

import { Candle, ChartTheme } from '../types'
import { DirtyRect } from '../core/Layer'
import { getOffscreenCanvasSupport } from '../utils/offscreenCanvasSupport'
import {
  InitMessage,
  RenderMessage,
  UpdateThemeMessage,
  ResizeMessage,
  AnyWorkerResponse,
  RenderCompleteResponse
} from './types'

export interface WorkerManagerConfig {
  canvas: HTMLCanvasElement
  theme: ChartTheme
  onRenderComplete?: (stats: { renderTime: number; candlesRendered: number }) => void
  onError?: (error: Error) => void
}

export class WorkerManager {
  private worker: Worker | null = null
  private canvas: HTMLCanvasElement
  private offscreenCanvas: OffscreenCanvas | null = null
  private ctx: CanvasRenderingContext2D | null = null
  private theme: ChartTheme
  private useWorker: boolean = false
  private pendingCallbacks: Map<string, (response: AnyWorkerResponse) => void> = new Map()
  private messageIdCounter = 0

  private onRenderComplete?: (stats: { renderTime: number; candlesRendered: number }) => void
  private onError?: (error: Error) => void

  constructor(config: WorkerManagerConfig) {
    this.canvas = config.canvas
    this.theme = config.theme
    this.onRenderComplete = config.onRenderComplete
    this.onError = config.onError

    // Detectar suporte
    const support = getOffscreenCanvasSupport()
    this.useWorker = support.supported

    if (this.useWorker) {
      console.log('✅ Using OffscreenCanvas + Worker')
      this.initWorker()
    } else {
      console.log('⚠️ Fallback to main thread rendering:', support.reason)
      this.initFallback()
    }
  }

  /**
   * Inicializa Worker com OffscreenCanvas
   */
  private initWorker(): void {
    try {
      // Criar Worker
      // IMPORTANTE: Vite precisa de URL especial para workers
      this.worker = new Worker(
        new URL('./candle.worker.ts', import.meta.url),
        { type: 'module' }
      )

      // Transferir controle do canvas para OffscreenCanvas
      this.offscreenCanvas = this.canvas.transferControlToOffscreen()

      // Setup message listener
      this.worker.addEventListener('message', this.handleWorkerMessage.bind(this))
      this.worker.addEventListener('error', this.handleWorkerError.bind(this))

      // Enviar inicialização
      const dpr = window.devicePixelRatio || 1
      const initMsg: InitMessage = {
        type: 'INIT',
        id: this.generateMessageId(),
        timestamp: Date.now(),
        canvas: this.offscreenCanvas,
        width: this.canvas.width,
        height: this.canvas.height,
        dpr,
        theme: this.theme
      }

      this.worker.postMessage(initMsg, [this.offscreenCanvas])
    } catch (error) {
      console.error('Failed to initialize worker, falling back:', error)
      this.useWorker = false
      this.initFallback()
    }
  }

  /**
   * Inicializa fallback (renderização na main thread)
   */
  private initFallback(): void {
    const context = this.canvas.getContext('2d', {
      alpha: true,
      desynchronized: true,
      willReadFrequently: false
    })

    if (!context) {
      throw new Error('Could not get 2D context')
    }

    this.ctx = context

    // Configurar DPR
    const dpr = window.devicePixelRatio || 1
    this.canvas.width = this.canvas.clientWidth * dpr
    this.canvas.height = this.canvas.clientHeight * dpr
    this.ctx.scale(dpr, dpr)

    // Qualidade
    this.ctx.imageSmoothingEnabled = true
    this.ctx.imageSmoothingQuality = 'high'
  }

  /**
   * Renderiza candles
   */
  render(
    candles: Candle[],
    viewport: { startIndex: number; endIndex: number; candleWidth: number },
    priceScale: { min: number; max: number; range: number },
    dirtyRect?: DirtyRect | null
  ): Promise<void> {
    if (this.useWorker && this.worker) {
      return this.renderWorker(candles, viewport, priceScale, dirtyRect)
    } else {
      return this.renderFallback(candles, viewport, priceScale, dirtyRect)
    }
  }

  /**
   * Renderiza usando Worker
   */
  private renderWorker(
    candles: Candle[],
    viewport: { startIndex: number; endIndex: number; candleWidth: number },
    priceScale: { min: number; max: number; range: number },
    dirtyRect?: DirtyRect | null
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.worker) {
        reject(new Error('Worker not initialized'))
        return
      }

      const msgId = this.generateMessageId()

      // Registrar callback
      this.pendingCallbacks.set(msgId, (response) => {
        if (response.type === 'RENDER_COMPLETE') {
          const stats = response as RenderCompleteResponse
          if (this.onRenderComplete) {
            this.onRenderComplete({
              renderTime: stats.renderTime,
              candlesRendered: stats.candlesRendered
            })
          }
          resolve()
        } else if (response.type === 'ERROR') {
          reject(new Error(response.error))
        }
      })

      // Enviar mensagem
      const msg: RenderMessage = {
        type: 'RENDER',
        id: msgId,
        timestamp: Date.now(),
        candles,
        viewport,
        priceScale,
        dirtyRect
      }

      this.worker.postMessage(msg)
    })
  }

  /**
   * Renderiza na main thread (fallback)
   */
  private renderFallback(
    candles: Candle[],
    viewport: { startIndex: number; endIndex: number; candleWidth: number },
    priceScale: { min: number; max: number; range: number },
    dirtyRect?: DirtyRect | null
  ): Promise<void> {
    return new Promise((resolve) => {
      if (!this.ctx) {
        resolve()
        return
      }

      const startTime = performance.now()

      // Limpar
      if (dirtyRect) {
        this.ctx.clearRect(dirtyRect.x, dirtyRect.y, dirtyRect.width, dirtyRect.height)
      } else {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
      }

      // Renderizar candles (simplificado - substituir pela lógica real)
      const rendered = candles.length

      const endTime = performance.now()

      if (this.onRenderComplete) {
        this.onRenderComplete({
          renderTime: endTime - startTime,
          candlesRendered: rendered
        })
      }

      resolve()
    })
  }

  /**
   * Atualiza tema
   */
  updateTheme(theme: ChartTheme): void {
    this.theme = theme

    if (this.useWorker && this.worker) {
      const msg: UpdateThemeMessage = {
        type: 'UPDATE_THEME',
        id: this.generateMessageId(),
        timestamp: Date.now(),
        theme
      }
      this.worker.postMessage(msg)
    }
  }

  /**
   * Redimensiona
   */
  resize(width: number, height: number): void {
    const dpr = window.devicePixelRatio || 1

    if (this.useWorker && this.worker) {
      const msg: ResizeMessage = {
        type: 'RESIZE',
        id: this.generateMessageId(),
        timestamp: Date.now(),
        width,
        height,
        dpr
      }
      this.worker.postMessage(msg)
    } else if (this.ctx) {
      // Fallback resize
      this.canvas.width = width * dpr
      this.canvas.height = height * dpr
      this.ctx.scale(dpr, dpr)
    }
  }

  /**
   * Destrói worker
   */
  destroy(): void {
    if (this.worker) {
      this.worker.postMessage({ type: 'DESTROY', id: this.generateMessageId(), timestamp: Date.now() })
      this.worker.terminate()
      this.worker = null
    }

    this.pendingCallbacks.clear()
    this.offscreenCanvas = null
    this.ctx = null
  }

  /**
   * Handle worker messages
   */
  private handleWorkerMessage(event: MessageEvent<AnyWorkerResponse>): void {
    const response = event.data
    const callback = this.pendingCallbacks.get(response.id)

    if (callback) {
      callback(response)
      this.pendingCallbacks.delete(response.id)
    }

    if (response.type === 'ERROR') {
      console.error('Worker error:', response.error)
      if (this.onError) {
        this.onError(new Error(response.error))
      }
    }
  }

  /**
   * Handle worker errors
   */
  private handleWorkerError(error: ErrorEvent): void {
    console.error('Worker error event:', error)
    if (this.onError) {
      this.onError(new Error(error.message))
    }
  }

  /**
   * Gera ID único para mensagem
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${this.messageIdCounter++}`
  }

  /**
   * Retorna se está usando worker
   */
  isUsingWorker(): boolean {
    return this.useWorker
  }
}
