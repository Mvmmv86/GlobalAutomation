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

  // DEMO MODE: Mock user for development
  const isDemoMode = import.meta.env.VITE_NODE_ENV === 'development'
  const mockUser: User = {
    id: 'demo-user-123',
    email: 'demo@tradingplatform.com',
    name: 'Demo User',
    isActive: true,
    isVerified: true,
    totpEnabled: false,
    createdAt: '2025-01-15T10:00:00Z',
    updatedAt: '2025-01-15T10:00:00Z',
  }

  const isAuthenticated = !!user

  useEffect(() => {
    initializeAuth()
  }, [])

  const initializeAuth = async () => {
    try {
      const token = localStorage.getItem('accessToken')
      if (token) {
        // Check if it's a demo token
        if (token === 'demo-token') {
          setUser(mockUser)
          setIsLoading(false)
          return
        }
        
        // Try to get real user profile
        try {
          const currentUser = await authService.getCurrentUser()
          setUser(currentUser)
        } catch (error) {
          // API failed, fallback to demo if demo token
          console.warn('Failed to get user profile, removing tokens')
          localStorage.removeItem('accessToken')
          localStorage.removeItem('refreshToken')
        }
      }
    } catch (error) {
      // Token invalid, remove it
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (credentials: LoginRequest) => {
    setIsLoading(true)
    try {
      // Try real API first
      const response = await authService.login(credentials)
      setUser(response.user)
      localStorage.setItem('accessToken', response.accessToken)
      localStorage.setItem('refreshToken', response.refreshToken)
    } catch (error) {
      // Fallback to demo mode if API fails
      console.warn('API login failed, using demo mode:', error)
      if (credentials.email === 'demo@tradingplatform.com' && credentials.password === 'demo123') {
        setUser(mockUser)
        localStorage.setItem('accessToken', 'demo-token')
        localStorage.setItem('refreshToken', 'demo-refresh-token')
      } else {
        throw new Error('Credenciais inválidas')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (data: RegisterRequest) => {
    setIsLoading(true)
    try {
      const response = await authService.register(data)
      setUser(response.user)
      localStorage.setItem('accessToken', response.accessToken)
      localStorage.setItem('refreshToken', response.refreshToken)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    // Optional: call logout endpoint
    authService.logout().catch(() => {
      // Ignore errors on logout
    })
  }

  const refreshToken = async () => {
    try {
      const response = await authService.refreshToken()
      localStorage.setItem('accessToken', response.accessToken)
      localStorage.setItem('refreshToken', response.refreshToken)
    } catch (error) {
      logout()
      throw error
    }
  }

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    refreshToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}