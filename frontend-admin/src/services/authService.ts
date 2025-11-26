import { apiClient } from '@/lib/api'
import { LoginRequest, LoginResponse, RegisterRequest, User } from '@/types/auth'

class AuthService {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Usar proxy do Vite para conectar ao backend
    const fullUrl = '/api/v1/auth/login'
    
    console.log('🌐 AuthService: Making request to:', fullUrl)
    console.log('📋 AuthService: Credentials:', { email: credentials.email, password: '***' })
    
    try {
      // Criar AbortController para timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => {
        console.log('⏰ AuthService: Request timeout, aborting...')
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
      
      console.log('📊 AuthService: Response status:', response.status)
      console.log('📊 AuthService: Response ok:', response.ok)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ AuthService: Error response:', errorText)
        throw new Error(`Login failed: ${response.status} ${errorText}`)
      }
      
      const data = await response.json()
      console.log('✅ AuthService: Success response:', data)
      return data
    } catch (error) {
      console.error('❌ AuthService: Exception:', error)
      
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
    return apiClient.post<LoginResponse>('/api/v1/auth/register', data)
  }

  async logout(): Promise<void> {
    return apiClient.post('/api/v1/auth/logout')
  }

  async getCurrentUser(): Promise<User> {
    const token = localStorage.getItem('accessToken')
    if (!token) {
      throw new Error('No access token')
    }
    
    const response = await fetch('/api/v1/auth/me', {
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

    return apiClient.post('/api/v1/auth/refresh', { refreshToken })
  }

  async requestPasswordReset(email: string): Promise<void> {
    return apiClient.post('/api/v1/auth/password-reset', { email })
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    return apiClient.post('/api/v1/auth/password-reset/confirm', {
      token,
      newPassword,
    })
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return apiClient.post('/api/v1/auth/change-password', {
      currentPassword,
      newPassword,
    })
  }

  async enableTwoFactor(): Promise<{ qrCode: string; secret: string }> {
    return apiClient.post('/api/v1/auth/2fa/enable')
  }

  async confirmTwoFactor(totpCode: string): Promise<void> {
    return apiClient.post('/api/v1/auth/2fa/confirm', { totpCode })
  }

  async disableTwoFactor(totpCode: string): Promise<void> {
    return apiClient.post('/api/v1/auth/2fa/disable', { totpCode })
  }
}

export const authService = new AuthService()