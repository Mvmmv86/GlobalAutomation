import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { DashboardLayout } from './DashboardLayout'
import { AuthLayout } from './AuthLayout'
import { LoginPage } from '../pages/LoginPage'
import { RegisterPage } from '../pages/RegisterPage'
import DashboardPage from '../pages/DashboardPage'
import TradingPage from '../pages/TradingPage'
import TradingPageSimple from '../pages/TradingPageSimple'
import ExchangeAccountsPage from '../pages/ExchangeAccountsPage'
import WebhooksPage from '../pages/WebhooksPage'
import BotsPage from '../pages/BotsPage'
import OrdersPage from '../pages/OrdersPage'
import PositionsPage from '../pages/PositionsPage'
import SettingsPage from '../pages/SettingsPage'
import DirtyRegionsTestPage from '../pages/DirtyRegionsTestPage'
import { IndicatorTestPage } from '../pages/IndicatorTestPage'
import { AllIndicatorsTestPage } from '../pages/AllIndicatorsTestPage'
import LayerTestPage from '../pages/LayerTestPage'
import PanelTestPage from '../pages/PanelTestPage'
import RenderersTestPage from '../pages/RenderersTestPage'
import WorkersTestPage from '../pages/WorkersTestPage'
import IndicatorWorkerTestPage from '../pages/IndicatorWorkerTestPage'
import ExtendedIndicatorsTestPage from '../pages/ExtendedIndicatorsTestPage'
import { RealtimeChartTestPage } from '../pages/RealtimeChartTestPage'
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
    return <Navigate to="/dashboard" replace />
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

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <DashboardPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/trading"
        element={
          <ProtectedRoute>
            <DashboardLayout fullWidth>
              <TradingPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/accounts"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <ExchangeAccountsPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/webhooks"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <WebhooksPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/bots"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <BotsPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/orders"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <OrdersPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/positions"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <PositionsPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <DashboardLayout>
              <SettingsPage />
            </DashboardLayout>
          </ProtectedRoute>
        }
      />

      {/* Test Routes - ALWAYS accessible (no auth check) */}
      <Route path="/test" element={<DirtyRegionsTestPage />} />
      <Route path="/test-indicators" element={<IndicatorTestPage />} />
      <Route path="/test-all-indicators" element={<AllIndicatorsTestPage />} />
      <Route path="/test-realtime" element={<RealtimeChartTestPage />} />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Test Routes - Development Only */}
      <Route path="/test/layers" element={<LayerTestPage />} />
      <Route path="/test/panels" element={<PanelTestPage />} />
      <Route path="/test/renderers" element={<RenderersTestPage />} />
      <Route path="/test/workers" element={<WorkersTestPage />} />
      <Route path="/test/indicator-workers" element={<IndicatorWorkerTestPage />} />
      <Route path="/test/extended-indicators" element={<ExtendedIndicatorsTestPage />} />

      {/* 404 fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}