/**
 * OffscreenCanvas Support Detection
 * Verifica se o browser suporta OffscreenCanvas e Workers
 */

export interface OffscreenCanvasSupportInfo {
  supported: boolean
  hasOffscreenCanvas: boolean
  hasWorkers: boolean
  reason?: string
}

/**
 * Verifica suporte para OffscreenCanvas
 */
export function checkOffscreenCanvasSupport(): OffscreenCanvasSupportInfo {
  // Verificar OffscreenCanvas
  const hasOffscreenCanvas = typeof OffscreenCanvas !== 'undefined'

  // Verificar Workers
  const hasWorkers = typeof Worker !== 'undefined'

  // Verificar transferControlToOffscreen
  const hasTransferControl = hasOffscreenCanvas &&
    typeof HTMLCanvasElement !== 'undefined' &&
    typeof HTMLCanvasElement.prototype.transferControlToOffscreen === 'function'

  const supported = hasOffscreenCanvas && hasWorkers && hasTransferControl

  let reason: string | undefined
  if (!supported) {
    if (!hasOffscreenCanvas) {
      reason = 'OffscreenCanvas not supported'
    } else if (!hasWorkers) {
      reason = 'Web Workers not supported'
    } else if (!hasTransferControl) {
      reason = 'transferControlToOffscreen not supported'
    }
  }

  return {
    supported,
    hasOffscreenCanvas,
    hasWorkers,
    reason
  }
}

/**
 * Singleton para armazenar resultado
 */
let cachedSupport: OffscreenCanvasSupportInfo | null = null

export function getOffscreenCanvasSupport(): OffscreenCanvasSupportInfo {
  if (!cachedSupport) {
    cachedSupport = checkOffscreenCanvasSupport()
    console.log('🎨 OffscreenCanvas Support:', cachedSupport)
  }
  return cachedSupport
}
