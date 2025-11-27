import { apiClient } from '@/lib/api'
import { LoginRequest, LoginResponse, RegisterRequest, User } from '@/types/auth'

class AuthService {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Em produção, usar VITE_API_URL. Em dev, usar proxy do Vite
    const baseURL = import.meta.env.VITE_API_URL || ''
    const fullUrl = baseURL ? `${baseURL}/api/v1/auth/login` : '/api/v1/auth/login'

    try {
      // Criar AbortController para timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => {
        controller.abort()
      }, 30000) // 30 segundos timeout
      
      const response = await fetch(fullUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Login failed: ${response.status} ${errorText}`)
      }

      return await response.json()
    } catch (error: any) {
      if (error.name === 'AbortError') {
        throw new Error('Login request timed out')
      }

      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('Network error - unable to connect to server')
      }

      throw error
    }
  }

  async register(data: RegisterRequest): Promise<LoginResponse> {
    return apiClient.post<LoginResponse>('/auth/register', data)
  }

  async logout(): Promise<void> {
    return apiClient.post('/auth/logout')
  }

  async getCurrentUser(): Promise<User> {
    const token = localStorage.getItem('accessToken')
    if (!token) {
      throw new Error('No access token')
    }

    // Em produção, usar VITE_API_URL. Em dev, usar proxy do Vite
    const baseURL = import.meta.env.VITE_API_URL || ''
    const fullUrl = baseURL ? `${baseURL}/api/v1/auth/me` : '/api/v1/auth/me'

    const response = await fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error('Failed to get user')
    }

    return response.json()
  }

  async refreshToken(): Promise<{ accessToken: string; refreshToken: string }> {
    const refreshToken = localStorage.getItem('refreshToken')
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }

    return apiClient.post('/auth/refresh', { refreshToken })
  }

  async requestPasswordReset(email: string): Promise<void> {
    return apiClient.post('/auth/password-reset', { email })
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    return apiClient.post('/auth/password-reset/confirm', {
      token,
      newPassword,
    })
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return apiClient.post('/auth/change-password', {
      currentPassword,
      newPassword,
    })
  }

  async enableTwoFactor(): Promise<{ qrCode: string; secret: string }> {
    return apiClient.post('/auth/2fa/enable')
  }

  async confirmTwoFactor(totpCode: string): Promise<void> {
    return apiClient.post('/auth/2fa/confirm', { totpCode })
  }

  async disableTwoFactor(totpCode: string): Promise<void> {
    return apiClient.post('/auth/2fa/disable', { totpCode })
  }
}

export const authService = new AuthService()