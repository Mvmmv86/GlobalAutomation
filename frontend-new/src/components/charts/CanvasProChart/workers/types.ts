/**
 * Worker Message Types
 * Define todas as mensagens entre main thread e worker
 */

import { Candle, ChartTheme } from '../types'
import { DirtyRect } from '../core/Layer'

// ========================================
// Main → Worker Messages
// ========================================

export type WorkerMessageType =
  | 'INIT'
  | 'RENDER'
  | 'UPDATE_THEME'
  | 'UPDATE_VIEWPORT'
  | 'RESIZE'
  | 'DESTROY'

export interface WorkerMessage {
  type: WorkerMessageType
  id: string
  timestamp: number
}

export interface InitMessage extends WorkerMessage {
  type: 'INIT'
  canvas: OffscreenCanvas
  width: number
  height: number
  dpr: number
  theme: ChartTheme
}

export interface RenderMessage extends WorkerMessage {
  type: 'RENDER'
  candles: Candle[]
  viewport: {
    startIndex: number
    endIndex: number
    candleWidth: number
  }
  priceScale: {
    min: number
    max: number
    range: number
  }
  dirtyRect?: DirtyRect | null
}

export interface UpdateThemeMessage extends WorkerMessage {
  type: 'UPDATE_THEME'
  theme: ChartTheme
}

export interface UpdateViewportMessage extends WorkerMessage {
  type: 'UPDATE_VIEWPORT'
  viewport: {
    startIndex: number
    endIndex: number
    candleWidth: number
  }
}

export interface ResizeMessage extends WorkerMessage {
  type: 'RESIZE'
  width: number
  height: number
  dpr: number
}

export interface DestroyMessage extends WorkerMessage {
  type: 'DESTROY'
}

export type AnyWorkerMessage =
  | InitMessage
  | RenderMessage
  | UpdateThemeMessage
  | UpdateViewportMessage
  | ResizeMessage
  | DestroyMessage

// ========================================
// Worker → Main Messages (Responses)
// ========================================

export type WorkerResponseType =
  | 'READY'
  | 'RENDER_COMPLETE'
  | 'ERROR'
  | 'PERFORMANCE'

export interface WorkerResponse {
  type: WorkerResponseType
  id: string
  timestamp: number
}

export interface ReadyResponse extends WorkerResponse {
  type: 'READY'
}

export interface RenderCompleteResponse extends WorkerResponse {
  type: 'RENDER_COMPLETE'
  renderTime: number
  candlesRendered: number
  candlesSkipped: number
}

export interface ErrorResponse extends WorkerResponse {
  type: 'ERROR'
  error: string
  stack?: string
}

export interface PerformanceResponse extends WorkerResponse {
  type: 'PERFORMANCE'
  fps: number
  avgRenderTime: number
  maxRenderTime: number
}

export type AnyWorkerResponse =
  | ReadyResponse
  | RenderCompleteResponse
  | ErrorResponse
  | PerformanceResponse
