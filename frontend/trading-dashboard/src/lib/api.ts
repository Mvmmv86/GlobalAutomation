import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { ApiResponse } from '@/types/api'

class ApiClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create({
      baseURL: '/api/v1', // Usar proxy do Vite
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
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

    // Response interceptor - handle auth errors
    this.instance.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Try to refresh token
          try {
            await this.refreshToken()
            // Retry original request
            return this.instance.request(error.config)
          } catch (refreshError) {
            // Redirect to login
            localStorage.removeItem('accessToken')
            localStorage.removeItem('refreshToken')
            window.location.href = '/login'
            return Promise.reject(refreshError)
          }
        }
        return Promise.reject(error)
      }
    )
  }

  private async refreshToken(): Promise<void> {
    const refreshToken = localStorage.getItem('refreshToken')
    if (!refreshToken) {
      throw new Error('No refresh token')
    }

    const response = await axios.post(
      '/api/v1/auth/refresh',
      { refreshToken }
    )

    const { accessToken, refreshToken: newRefreshToken } = response.data
    localStorage.setItem('accessToken', accessToken)
    localStorage.setItem('refreshToken', newRefreshToken)
  }

  async get<T>(url: string): Promise<T> {
    const response = await this.instance.get<ApiResponse<T>>(url)
    return response.data as T
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.instance.post<ApiResponse<T>>(url, data)
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
}

export const apiClient = new ApiClient()
export default apiClient