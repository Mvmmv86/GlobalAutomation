/**
 * AdminLayout Component
 * Main layout for admin portal with sidebar navigation
 */
import { ReactNode, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  Building2,
  Bot,
  Webhook,
  Settings,
  LogOut,
  Menu,
  X
} from 'lucide-react'
import { Button } from '@/components/atoms/Button'
import { useAuth } from '@/contexts/AuthContext'

interface AdminLayoutProps {
  children: ReactNode
}

interface NavItem {
  label: string
  path: string
  icon: ReactNode
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/admin', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Clientes', path: '/admin/users', icon: <Users className="w-5 h-5" /> },
  { label: 'Exchanges', path: '/admin/exchanges', icon: <Building2 className="w-5 h-5" /> },
  { label: 'Bots', path: '/admin/bots', icon: <Bot className="w-5 h-5" /> },
  { label: 'Webhooks', path: '/admin/webhooks', icon: <Webhook className="w-5 h-5" /> },
  { label: 'Configurações', path: '/admin/settings', icon: <Settings className="w-5 h-5" /> },
]

export function AdminLayout({ children }: AdminLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isActiveRoute = (path: string) => {
    if (path === '/admin') {
      return location.pathname === '/admin'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-[#1a1d24] flex">
      {/* Sidebar - Desktop */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 bg-[#1e222d] border-r border-[#2a2e39] fixed h-full">
        {/* Logo/Title */}
        <div className="h-16 flex items-center px-6 border-b border-[#2a2e39]">
          <Bot className="w-8 h-8 text-emerald-500 mr-3" />
          <h1 className="text-xl font-bold text-white">Admin Portal</h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 overflow-y-auto">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <button
                  onClick={() => navigate(item.path)}
                  className={`
                    w-full flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-colors
                    ${isActiveRoute(item.path)
                      ? 'bg-emerald-600 text-white'
                      : 'text-gray-300 hover:bg-[#2a2e39]'
                    }
                  `}
                >
                  {item.icon}
                  <span className="ml-3">{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-[#2a2e39]">
          <div className="flex items-center mb-3">
            <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center">
              <span className="text-white font-semibold text-sm">
                {user?.name?.charAt(0).toUpperCase() || 'A'}
              </span>
            </div>
            <div className="ml-3 flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.name || 'Admin'}
              </p>
              <p className="text-xs text-gray-400 truncate">
                {user?.email || 'admin@example.com'}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="w-full justify-start border-[#2a2e39] text-gray-300 hover:bg-[#2a2e39]"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sair
          </Button>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-[#1e222d] border-b border-[#2a2e39] flex items-center px-4 z-30">
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="p-2 rounded-lg hover:bg-[#2a2e39]"
        >
          {isMobileMenuOpen ? (
            <X className="w-6 h-6 text-gray-300" />
          ) : (
            <Menu className="w-6 h-6 text-gray-300" />
          )}
        </button>
        <Bot className="w-6 h-6 text-emerald-500 ml-4 mr-2" />
        <h1 className="text-lg font-bold text-white">Admin Portal</h1>
      </div>

      {/* Mobile Sidebar Overlay */}
      {isMobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Mobile Sidebar */}
      <aside
        className={`
          lg:hidden fixed inset-y-0 left-0 w-64 bg-[#1e222d] transform transition-transform duration-300 ease-in-out z-50
          ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo/Title */}
        <div className="h-16 flex items-center px-6 border-b border-[#2a2e39]">
          <Bot className="w-8 h-8 text-emerald-500 mr-3" />
          <h1 className="text-xl font-bold text-white">Admin Portal</h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 overflow-y-auto">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <button
                  onClick={() => {
                    navigate(item.path)
                    setIsMobileMenuOpen(false)
                  }}
                  className={`
                    w-full flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-colors
                    ${isActiveRoute(item.path)
                      ? 'bg-emerald-600 text-white'
                      : 'text-gray-300 hover:bg-[#2a2e39]'
                    }
                  `}
                >
                  {item.icon}
                  <span className="ml-3">{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* User Info & Logout */}
        <div className="p-4 border-t border-[#2a2e39]">
          <div className="flex items-center mb-3">
            <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center">
              <span className="text-white font-semibold text-sm">
                {user?.name?.charAt(0).toUpperCase() || 'A'}
              </span>
            </div>
            <div className="ml-3 flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.name || 'Admin'}
              </p>
              <p className="text-xs text-gray-400 truncate">
                {user?.email || 'admin@example.com'}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="w-full justify-start border-[#2a2e39] text-gray-300 hover:bg-[#2a2e39]"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sair
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 lg:ml-64">
        <div className="pt-16 lg:pt-0">
          {children}
        </div>
      </main>
    </div>
  )
}
