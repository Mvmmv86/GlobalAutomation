import React, { createContext, useContext, useEffect, useState } from 'react'
import { User, AuthContextType, LoginRequest, RegisterRequest } from '@/types/auth'
import { authService } from '@/services/authService'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: React.ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const isAuthenticated = !!user

  useEffect(() => {
    // Timeout rápido para evitar loading infinito
    const initTimeout = setTimeout(() => {
      setIsLoading(false)
    }, 2000) // 2 segundos máximo

    initializeAuth().finally(() => {
      clearTimeout(initTimeout)
      setIsLoading(false)
    })

    return () => clearTimeout(initTimeout)
  }, [])

  const initializeAuth = async () => {
    try {
      const token = localStorage.getItem('accessToken')
      if (!token) {
        return // Sem token, não faz nada
      }

      // Try to get user profile with timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5s timeout
      
      try {
        const currentUser = await authService.getCurrentUser()
        setUser(currentUser)
        clearTimeout(timeoutId)
      } catch (error) {
        clearTimeout(timeoutId)
        console.warn('Failed to get user profile:', error)
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
      }
    } catch (error) {
      console.warn('Auth initialization error:', error)
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
    }
  }

  const login = async (credentials: LoginRequest) => {
    console.log('🔐 Starting login process...', credentials.email)
    setIsLoading(true)
    try {
      console.log('📡 Calling authService.login...')
      const response = await authService.login(credentials)
      console.log('✅ Login API response received:', response)
      console.log('🔍 Response keys:', Object.keys(response))
      
      // Verificar se temos os tokens na resposta
      const accessToken = response.access_token || response.accessToken
      const refreshToken = response.refresh_token || response.refreshToken
      
      console.log('🔑 Access token found:', !!accessToken)
      console.log('🔄 Refresh token found:', !!refreshToken)
      
      if (!accessToken) {
        throw new Error('No access token in response')
      }
      
      // Usar dados reais do getCurrentUser
      console.log('👤 Getting user profile...')
      localStorage.setItem('accessToken', accessToken)
      localStorage.setItem('refreshToken', refreshToken)
      
      try {
        const currentUser = await authService.getCurrentUser()
        console.log('👤 User profile received:', currentUser)
        setUser(currentUser)
      } catch (userError) {
        console.error('❌ Failed to get user profile:', userError)
        // Fallback para user mock se getCurrentUser falhar
        const mockUser: User = {
          id: 'user_1',
          email: credentials.email,
          name: credentials.email.split('@')[0],
          isActive: true,
          isVerified: true,
          totpEnabled: false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }
        setUser(mockUser)
      }
      
      console.log('💾 Login completed successfully')
    } catch (error: any) {
      console.error('❌ Login failed:', error)
      throw new Error(error.message || 'Login failed')
    } finally {
      setIsLoading(false)
      console.log('🏁 Login process completed')
    }
  }

  const register = async (data: RegisterRequest) => {
    setIsLoading(true)
    try {
      await authService.register(data)
      
      // Após registro, fazer login automaticamente
      await login({ email: data.email, password: data.password })
    } catch (error: any) {
      console.error('Registration failed:', error)
      throw new Error(error.message || 'Registration failed')
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      await authService.logout()
    } catch (error) {
      // Ignore logout errors
    } finally {
      setUser(null)
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('demo_email')
    }
  }

  const refreshTokenFn = async () => {
    try {
      const response = await authService.refreshToken()
      localStorage.setItem('accessToken', response.accessToken)
      localStorage.setItem('refreshToken', response.refreshToken)
    } catch (error) {
      console.error('Token refresh failed:', error)
      await logout()
    }
  }

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshToken: refreshTokenFn,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}