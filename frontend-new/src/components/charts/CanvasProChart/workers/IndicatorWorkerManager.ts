/**
 * IndicatorWorkerManager - Gerencia cálculos de indicadores em Worker
 * Move cálculos pesados para thread separada
 */

import { Candle } from '../types'
import { AnyIndicatorConfig } from '../indicators/types'
import type {
  CalculateIndicatorMessage,
  CalculateBatchMessage,
  ClearCacheMessage,
  CalculateResponse,
  BatchCalculateResponse,
  ErrorResponse,
  IndicatorResult
} from './indicator.worker'

type WorkerResponse = CalculateResponse | BatchCalculateResponse | ErrorResponse

export interface IndicatorWorkerConfig {
  onCalculateComplete?: (result: IndicatorResult, time: number) => void
  onBatchComplete?: (results: IndicatorResult[], time: number) => void
  onError?: (error: Error) => void
}

export class IndicatorWorkerManager {
  private worker: Worker | null = null
  private pendingCallbacks: Map<string, (response: WorkerResponse) => void> = new Map()
  private messageIdCounter = 0
  private useWorker = false

  private onCalculateComplete?: (result: IndicatorResult, time: number) => void
  private onBatchComplete?: (results: IndicatorResult[], time: number) => void
  private onError?: (error: Error) => void

  // Cache para fallback
  private fallbackCache = new Map<string, IndicatorResult>()

  constructor(config?: IndicatorWorkerConfig) {
    this.onCalculateComplete = config?.onCalculateComplete
    this.onBatchComplete = config?.onBatchComplete
    this.onError = config?.onError

    this.initWorker()
  }

  /**
   * Inicializa o Worker
   */
  private initWorker(): void {
    try {
      // Verificar se Workers são suportados
      if (typeof Worker === 'undefined') {
        console.log('⚠️ Workers not supported, using main thread for indicators')
        this.useWorker = false
        return
      }

      // Criar Worker
      this.worker = new Worker(
        new URL('./indicator.worker.ts', import.meta.url),
        { type: 'module' }
      )

      // Setup listeners
      this.worker.addEventListener('message', this.handleWorkerMessage.bind(this))
      this.worker.addEventListener('error', this.handleWorkerError.bind(this))

      this.useWorker = true
      console.log('✅ Indicator Worker initialized')
    } catch (error) {
      console.error('Failed to initialize indicator worker:', error)
      this.useWorker = false
    }
  }

  /**
   * Calcula um único indicador
   */
  calculate(indicator: AnyIndicatorConfig, candles: Candle[]): Promise<IndicatorResult> {
    if (this.useWorker && this.worker) {
      return this.calculateWithWorker(indicator, candles)
    } else {
      return this.calculateFallback(indicator, candles)
    }
  }

  /**
   * Calcula múltiplos indicadores em lote
   */
  calculateBatch(indicators: AnyIndicatorConfig[], candles: Candle[]): Promise<IndicatorResult[]> {
    if (this.useWorker && this.worker) {
      return this.calculateBatchWithWorker(indicators, candles)
    } else {
      return this.calculateBatchFallback(indicators, candles)
    }
  }

  /**
   * Calcula com Worker
   */
  private calculateWithWorker(
    indicator: AnyIndicatorConfig,
    candles: Candle[]
  ): Promise<IndicatorResult> {
    return new Promise((resolve, reject) => {
      if (!this.worker) {
        reject(new Error('Worker not initialized'))
        return
      }

      const msgId = this.generateMessageId()

      // Registrar callback
      this.pendingCallbacks.set(msgId, (response) => {
        if (response.type === 'CALCULATE_COMPLETE') {
          const res = response as CalculateResponse
          if (this.onCalculateComplete) {
            this.onCalculateComplete(res.result, res.calculationTime)
          }
          resolve(res.result)
        } else if (response.type === 'ERROR') {
          const err = response as ErrorResponse
          reject(new Error(err.error))
        }
      })

      // Enviar mensagem
      const msg: CalculateIndicatorMessage = {
        type: 'CALCULATE',
        id: msgId,
        timestamp: Date.now(),
        indicator,
        candles
      }

      this.worker.postMessage(msg)
    })
  }

  /**
   * Calcula batch com Worker
   */
  private calculateBatchWithWorker(
    indicators: AnyIndicatorConfig[],
    candles: Candle[]
  ): Promise<IndicatorResult[]> {
    return new Promise((resolve, reject) => {
      if (!this.worker) {
        reject(new Error('Worker not initialized'))
        return
      }

      const msgId = this.generateMessageId()

      // Registrar callback
      this.pendingCallbacks.set(msgId, (response) => {
        if (response.type === 'BATCH_COMPLETE') {
          const res = response as BatchCalculateResponse
          if (this.onBatchComplete) {
            this.onBatchComplete(res.results, res.calculationTime)
          }
          resolve(res.results)
        } else if (response.type === 'ERROR') {
          const err = response as ErrorResponse
          reject(new Error(err.error))
        }
      })

      // Enviar mensagem
      const msg: CalculateBatchMessage = {
        type: 'CALCULATE_BATCH',
        id: msgId,
        timestamp: Date.now(),
        indicators,
        candles
      }

      this.worker.postMessage(msg)
    })
  }

  /**
   * Fallback - calcula na main thread
   * Usa o IndicatorEngine existente
   */
  private async calculateFallback(
    indicator: AnyIndicatorConfig,
    candles: Candle[]
  ): Promise<IndicatorResult> {
    const startTime = performance.now()

    // Importar dinamicamente para evitar carregar se Worker funcionar
    const { IndicatorEngine } = await import('../indicators/IndicatorEngine')
    const engine = new IndicatorEngine()

    const result = engine.calculate(indicator, candles)

    const calculationTime = performance.now() - startTime

    if (this.onCalculateComplete && result) {
      this.onCalculateComplete(result, calculationTime)
    }

    return result || {
      id: indicator.id,
      type: indicator.type,
      values: new Array(candles.length).fill(NaN)
    }
  }

  /**
   * Fallback batch - calcula na main thread
   */
  private async calculateBatchFallback(
    indicators: AnyIndicatorConfig[],
    candles: Candle[]
  ): Promise<IndicatorResult[]> {
    const startTime = performance.now()
    const results: IndicatorResult[] = []

    // Importar dinamicamente
    const { IndicatorEngine } = await import('../indicators/IndicatorEngine')
    const engine = new IndicatorEngine()

    for (const indicator of indicators) {
      if (indicator.enabled) {
        const result = engine.calculate(indicator, candles)
        if (result) {
          results.push(result)
        }
      }
    }

    const calculationTime = performance.now() - startTime

    if (this.onBatchComplete) {
      this.onBatchComplete(results, calculationTime)
    }

    return results
  }

  /**
   * Limpa o cache
   */
  clearCache(): void {
    if (this.worker) {
      const msg: ClearCacheMessage = {
        type: 'CLEAR_CACHE',
        id: this.generateMessageId(),
        timestamp: Date.now()
      }
      this.worker.postMessage(msg)
    }
    this.fallbackCache.clear()
  }

  /**
   * Handle worker messages
   */
  private handleWorkerMessage(event: MessageEvent<WorkerResponse>): void {
    const response = event.data
    const callback = this.pendingCallbacks.get(response.id)

    if (callback) {
      callback(response)
      this.pendingCallbacks.delete(response.id)
    }

    if (response.type === 'ERROR') {
      console.error('Indicator worker error:', (response as ErrorResponse).error)
      if (this.onError) {
        this.onError(new Error((response as ErrorResponse).error))
      }
    }
  }

  /**
   * Handle worker errors
   */
  private handleWorkerError(error: ErrorEvent): void {
    console.error('Indicator worker error event:', error)
    if (this.onError) {
      this.onError(new Error(error.message))
    }

    // Tentar reinicializar
    this.destroy()
    setTimeout(() => {
      console.log('Attempting to restart indicator worker...')
      this.initWorker()
    }, 1000)
  }

  /**
   * Gera ID único para mensagem
   */
  private generateMessageId(): string {
    return `ind_${Date.now()}_${this.messageIdCounter++}`
  }

  /**
   * Retorna se está usando worker
   */
  isUsingWorker(): boolean {
    return this.useWorker
  }

  /**
   * Destrói o worker
   */
  destroy(): void {
    if (this.worker) {
      this.worker.terminate()
      this.worker = null
    }
    this.pendingCallbacks.clear()
    this.fallbackCache.clear()
    this.useWorker = false
  }

  /**
   * Retorna estatísticas
   */
  getStats(): {
    usingWorker: boolean
    pendingCalculations: number
    cacheSize: number
  } {
    return {
      usingWorker: this.useWorker,
      pendingCalculations: this.pendingCallbacks.size,
      cacheSize: this.fallbackCache.size
    }
  }
}