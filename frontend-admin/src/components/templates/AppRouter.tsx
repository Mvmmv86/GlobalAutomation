import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { AdminLayout } from '../layout/AdminLayout'
import { AuthLayout } from './AuthLayout'
import { LoginPage } from '../pages/LoginPage'
import { RegisterPage } from '../pages/RegisterPage'
import { AdminDashboard } from '../pages/AdminDashboard'
import { UsersPage } from '../pages/UsersPage'
import { BotsPage } from '../pages/BotsPage'
import { AdminExchangesPage } from '../pages/AdminExchangesPage'
import { AdminWebhooksPage } from '../pages/AdminWebhooksPage'
import { LoadingSpinner } from '../atoms/LoadingSpinner'

interface ProtectedRouteProps {
  children: React.ReactNode
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  console.log('🛡️ ProtectedRoute check:', { isAuthenticated, isLoading })

  if (isLoading) {
    console.log('⏳ Still loading, showing spinner...')
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    console.log('🚫 Not authenticated, redirecting to login...')
    return <Navigate to="/login" replace />
  }

  console.log('✅ Authenticated, rendering protected content...')
  return <>{children}</>
}

const PublicRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/admin" replace />
  }

  return <>{children}</>
}

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <AuthLayout>
              <LoginPage />
            </AuthLayout>
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <AuthLayout>
              <RegisterPage />
            </AuthLayout>
          </PublicRoute>
        }
      />

      {/* Protected Admin Routes */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <AdminDashboard />
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <UsersPage />
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/bots"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <BotsPage />
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/exchanges"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <AdminExchangesPage />
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/webhooks"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <AdminWebhooksPage />
            </AdminLayout>
          </ProtectedRoute>
        }
      />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/admin" replace />} />

      {/* 404 fallback */}
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  )
}