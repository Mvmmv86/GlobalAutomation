import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { ApiResponse } from '@/types/api'

class ApiClient {
  private instance: AxiosInstance
  private isRefreshing = false
  private failedQueue: Array<{
    resolve: (value?: unknown) => void
    reject: (reason?: any) => void
  }> = []

  constructor() {
    // Em produção, usar VITE_API_URL. Em dev, usar proxy do Vite
    const baseURL = import.meta.env.VITE_API_URL
      ? `${import.meta.env.VITE_API_URL}/api/v1`
      : '/api/v1'

    this.instance = axios.create({
      baseURL,
      timeout: 180000, // 60 seconds timeout (increased from 30s for exchange account creation)
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private processQueue(error: any, token: string | null = null) {
    this.failedQueue.forEach((prom) => {
      if (error) {
        prom.reject(error)
      } else {
        prom.resolve(token)
      }
    })
    this.failedQueue = []
  }

  private setupInterceptors() {
    // Request interceptor - add auth token
    this.instance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('accessToken')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor - handle auth errors with improved mutex
    this.instance.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => response,
      async (error) => {
        const originalRequest = error.config

        // Evitar loop infinito - se já tentou refresh, não tenta de novo
        if (error.response?.status === 401 && !originalRequest._retry) {
          // Se já está fazendo refresh, adiciona à fila e aguarda
          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject })
            })
              .then((token) => {
                originalRequest.headers.Authorization = `Bearer ${token}`
                return this.instance.request(originalRequest)
              })
              .catch((err) => Promise.reject(err))
          }

          originalRequest._retry = true
          this.isRefreshing = true

          try {
            await this.doRefreshToken()
            const newToken = localStorage.getItem('accessToken')

            // Processar fila de requisições que estavam esperando
            this.processQueue(null, newToken)

            // Atualizar o header Authorization com o novo token
            if (newToken) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
            }

            // Retry original request with new token
            return this.instance.request(originalRequest)
          } catch (refreshError) {
            // Processar fila com erro
            this.processQueue(refreshError, null)

            // Redirect to login
            localStorage.removeItem('accessToken')
            localStorage.removeItem('refreshToken')
            window.location.href = '/login'
            return Promise.reject(refreshError)
          } finally {
            this.isRefreshing = false
          }
        }
        return Promise.reject(error)
      }
    )
  }

  private async doRefreshToken(): Promise<void> {
    try {
      const refreshToken = localStorage.getItem('refreshToken')
      if (!refreshToken) {
        throw new Error('No refresh token')
      }

      const response = await axios.post(
        `${this.instance.defaults.baseURL}/auth/refresh`,
        { refresh_token: refreshToken }  // Backend espera snake_case
      )

      // Backend retorna snake_case (access_token), mas também aceita camelCase
      const accessToken = response.data.access_token || response.data.accessToken
      const newRefreshToken = response.data.refresh_token || response.data.refreshToken

      if (accessToken) {
        localStorage.setItem('accessToken', accessToken)
        console.log('[API] Token refreshed successfully')
      } else {
        console.error('[API] Refresh response missing access_token:', response.data)
        throw new Error('No access token in refresh response')
      }
      if (newRefreshToken) {
        localStorage.setItem('refreshToken', newRefreshToken)
      }
    } finally {
      // Reset mutex after refresh completes (success or failure)
      this.isRefreshing = false
      this.refreshPromise = null
    }
  }

  async get<T>(url: string): Promise<T> {
    const response = await this.instance.get<ApiResponse<T>>(url)
    // Nossa API retorna { success: true, data: {...} }
    const apiResponse = response.data as any
    if (apiResponse.success && apiResponse.data) {
      return apiResponse.data as T
    }
    return response.data as T
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.instance.post<ApiResponse<T>>(url, data)
    // Nossa API retorna { success: true, data: {...} }
    const apiResponse = response.data as any
    if (apiResponse.success && apiResponse.data) {
      return apiResponse.data as T
    }
    return response.data as T
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.instance.put<ApiResponse<T>>(url, data)
    return response.data as T
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.instance.delete<ApiResponse<T>>(url)
    return response.data as T
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    const response = await this.instance.patch<ApiResponse<T>>(url, data)
    return response.data as T
  }

  // Método público para acessar a instância do Axios (necessário para headers customizados)
  getAxiosInstance(): AxiosInstance {
    return this.instance
  }
}

export const apiClient = new ApiClient()
export default apiClient

// ==================== SL/TP Update Functions ====================

export interface UpdateSLTPRequest {
  position_id: string
  type: 'stopLoss' | 'takeProfit'
  price: number
}

export interface UpdateSLTPResponse {
  success: boolean
  message: string
  order_id: string
  new_price: number
}

/**
 * Gerar idempotency key única para requisição
 */
function generateIdempotencyKey(positionId: string, type: string, price: number): string {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2, 8)
  return `sltp_${positionId}_${type}_${price}_${timestamp}_${random}`
}

/**
 * Atualiza Stop Loss ou Take Profit de uma posição
 * Esta função:
 * 1. Gera idempotency key (previne duplicação)
 * 2. Cancela a ordem antiga na Binance
 * 3. Cria uma nova ordem com o novo preço
 * 4. Atualiza o banco de dados
 */
export const updatePositionSLTP = async (
  positionId: string,
  type: 'stopLoss' | 'takeProfit',
  price: number
): Promise<UpdateSLTPResponse> => {
  // Gerar idempotency key
  const idempotencyKey = generateIdempotencyKey(positionId, type, price)

  const response = await apiClient.getAxiosInstance().patch<UpdateSLTPResponse>(
    `/orders/positions/${positionId}/sltp`,
    { position_id: positionId, type, price },
    {
      headers: {
        'X-Idempotency-Key': idempotencyKey
      }
    }
  )

  return response.data
}

/**
 * Cria Stop Loss ou Take Profit para uma posição existente
 * Usado quando o usuário arrasta a linha de entrada para criar SL/TP
 */
export const createPositionSLTP = async (
  positionId: string,
  type: 'stopLoss' | 'takeProfit',
  price: number,
  side: 'LONG' | 'SHORT'
): Promise<UpdateSLTPResponse> => {
  // Gerar idempotency key
  const idempotencyKey = generateIdempotencyKey(positionId, type, price)

  const response = await apiClient.getAxiosInstance().post<UpdateSLTPResponse>(
    `/orders/positions/${positionId}/sltp`,
    { position_id: positionId, type, price, side },
    {
      headers: {
        'X-Idempotency-Key': idempotencyKey
      }
    }
  )

  return response.data
}

export interface CancelSLTPResponse {
  success: boolean
  message: string
  cancelled_order_id?: string
}

/**
 * Cancela Stop Loss ou Take Profit de uma posição
 * Usado quando o usuário clica no X para cancelar uma ordem
 */
export const cancelPositionSLTP = async (
  positionId: string,
  type: 'stopLoss' | 'takeProfit'
): Promise<CancelSLTPResponse> => {
  const response = await apiClient.getAxiosInstance().delete<CancelSLTPResponse>(
    `/orders/positions/${positionId}/sltp`,
    {
      data: { position_id: positionId, type }
    }
  )

  return response.data
}