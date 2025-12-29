import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy, memo } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { AdminLayout } from '../layout/AdminLayout'
import { AuthLayout } from './AuthLayout'
import { LoadingSpinner } from '../atoms/LoadingSpinner'

// Lazy load das páginas para melhor performance
const LoginPage = lazy(() => import('../pages/LoginPage').then(m => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import('../pages/RegisterPage').then(m => ({ default: m.RegisterPage })))
const AdminDashboard = lazy(() => import('../pages/AdminDashboard').then(m => ({ default: m.AdminDashboard })))
const UsersPage = lazy(() => import('../pages/UsersPage').then(m => ({ default: m.UsersPage })))
const BotsPage = lazy(() => import('../pages/BotsPage').then(m => ({ default: m.BotsPage })))
const AdminExchangesPage = lazy(() => import('../pages/AdminExchangesPage').then(m => ({ default: m.AdminExchangesPage })))
const AdminWebhooksPage = lazy(() => import('../pages/AdminWebhooksPage').then(m => ({ default: m.AdminWebhooksPage })))
const StrategiesPage = lazy(() => import('../pages/StrategiesPage').then(m => ({ default: m.StrategiesPage })))

// Loading fallback component
const PageLoader = () => (
  <div className="min-h-[400px] flex items-center justify-center">
    <LoadingSpinner size="lg" />
  </div>
)

// Full page loading (para auth check)
const FullPageLoader = () => (
  <div className="min-h-screen flex items-center justify-center bg-[#0a0e17]">
    <LoadingSpinner size="lg" />
  </div>
)

interface ProtectedRouteProps {
  children: React.ReactNode
}

// Memoized para evitar re-renders desnecessários
const ProtectedRoute = memo<ProtectedRouteProps>(({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <FullPageLoader />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
})

ProtectedRoute.displayName = 'ProtectedRoute'

const PublicRoute = memo<ProtectedRouteProps>(({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <FullPageLoader />
  }

  if (isAuthenticated) {
    return <Navigate to="/admin" replace />
  }

  return <>{children}</>
})

PublicRoute.displayName = 'PublicRoute'

export const AppRouter: React.FC = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <AuthLayout>
              <Suspense fallback={<PageLoader />}>
                <LoginPage />
              </Suspense>
            </AuthLayout>
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <AuthLayout>
              <Suspense fallback={<PageLoader />}>
                <RegisterPage />
              </Suspense>
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
              <Suspense fallback={<PageLoader />}>
                <AdminDashboard />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <Suspense fallback={<PageLoader />}>
                <UsersPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/bots"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <Suspense fallback={<PageLoader />}>
                <BotsPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/exchanges"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <Suspense fallback={<PageLoader />}>
                <AdminExchangesPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/webhooks"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <Suspense fallback={<PageLoader />}>
                <AdminWebhooksPage />
              </Suspense>
            </AdminLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/strategies"
        element={
          <ProtectedRoute>
            <AdminLayout>
              <Suspense fallback={<PageLoader />}>
                <StrategiesPage />
              </Suspense>
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
