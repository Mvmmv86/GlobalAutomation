import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  BarChart3,
  Building2,
  FileText,
  Settings,
  Webhook,
  TrendingUp,
  Menu,
  X,
  LogOut,
  User,
  Moon,
  Sun,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { DemoBanner } from '../atoms/DemoBanner'
import { useCandlesPrefetch } from '@/hooks/useCandlesPrefetch'

interface DashboardLayoutProps {
  children: React.ReactNode
  fullWidth?: boolean
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: BarChart3 },
  { name: 'Trading', href: '/trading', icon: TrendingUp },
  { name: 'Exchange Accounts', href: '/accounts', icon: Building2 },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'Orders', href: '/orders', icon: FileText },
  { name: 'Positions', href: '/positions', icon: TrendingUp },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children, fullWidth = false }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false) // Desktop collapse
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()

  // 🚀 Prefetch popular symbols for ultra-fast chart loading
  useCandlesPrefetch()

  return (
    <div className="min-h-screen bg-background">
      <DemoBanner />
      {/* Mobile sidebar */}
      <div className={cn(
        'fixed inset-0 z-50 lg:hidden',
        sidebarOpen ? 'block' : 'hidden'
      )}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-card shadow-xl">
          <div className="flex items-center justify-between h-16 px-4 border-b border-border">
            <h1 className="text-xl font-semibold text-foreground">Trading Platform</h1>
            <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}>
              <X className="h-5 w-5" />
            </Button>
          </div>
          <nav className="flex-1 px-4 py-4 space-y-2">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  location.pathname === item.href
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className={cn(
        "hidden lg:fixed lg:inset-y-0 lg:flex lg:flex-col transition-all duration-300",
        sidebarCollapsed ? "lg:w-16" : "lg:w-64"
      )}>
        <div className="flex flex-col flex-grow bg-card border-r border-border">
          <div className="flex items-center justify-between h-16 px-4 border-b border-border">
            {!sidebarCollapsed && (
              <h1 className="text-xl font-semibold text-foreground">Trading Platform</h1>
            )}
            {!sidebarCollapsed && (
              <div className="flex items-center space-x-2">
                <Button variant="ghost" size="icon" onClick={toggleTheme}>
                  {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </Button>
              </div>
            )}
          </div>
          <nav className="flex-1 px-4 py-4 space-y-2">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                  location.pathname === item.href
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  sidebarCollapsed && 'justify-center px-2'
                )}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon className={cn("h-5 w-5", sidebarCollapsed ? "mr-0" : "mr-3")} />
                {!sidebarCollapsed && item.name}
              </Link>
            ))}
          </nav>

          {/* Toggle Button - Center of navbar */}
          <div className="flex justify-center py-4 border-t border-border bg-accent/20">
            <Button
              variant="secondary"
              size="icon"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="h-10 w-10 shadow-md hover:scale-105 transition-all duration-200"
              title={sidebarCollapsed ? "Expandir navbar" : "Recolher navbar"}
            >
              {sidebarCollapsed ? (
                <ChevronRight className="h-5 w-5" />
              ) : (
                <ChevronLeft className="h-5 w-5" />
              )}
            </Button>
          </div>
          
          {/* User section */}
          <div className="p-4 border-t border-border">
            {sidebarCollapsed ? (
              <div className="flex flex-col items-center space-y-2">
                <div className="flex items-center justify-center w-8 h-8 bg-primary text-primary-foreground rounded-full">
                  <User className="h-4 w-4" />
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={logout}
                  className="h-8 w-8"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <>
                <div className="flex items-center mb-3">
                  <div className="flex items-center justify-center w-8 h-8 bg-primary text-primary-foreground rounded-full">
                    <User className="h-4 w-4" />
                  </div>
                  <div className="ml-3 flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {user?.name || 'Demo User'}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {user?.email || 'demo@tradingplatform.com'}
                    </p>
                  </div>
                  <Badge variant="success" className="text-xs ml-2">
                    Verified
                  </Badge>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={logout}
                >
                  <LogOut className="h-4 w-4 mr-2" />
                  Logout
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className={cn(
        "transition-all duration-300",
        sidebarCollapsed ? "lg:pl-16" : "lg:pl-64"
      )}>
        {/* Top header */}
        <div className="sticky top-0 z-40 flex h-16 items-center gap-x-4 border-b border-border bg-card px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              {/* Add any header content here */}
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className={fullWidth ? "h-[calc(100vh-64px)]" : "py-6"}>
          {fullWidth ? (
            children
          ) : (
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              {children}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}