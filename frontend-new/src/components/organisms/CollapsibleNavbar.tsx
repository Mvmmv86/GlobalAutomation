import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Menu,
  X,
  BarChart3,
  TrendingUp,
  Link as LinkIcon,
  CreditCard,
  FileText,
  Target,
  Settings,
  LogOut,
  Home
} from 'lucide-react'
import { Button } from '../atoms/Button'
import { Avatar, AvatarFallback } from '../atoms/Avatar'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'

interface CollapsibleNavbarProps {
  className?: string
}

export const CollapsibleNavbar: React.FC<CollapsibleNavbarProps> = ({ className }) => {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { logout } = useAuth()

  const navItems = [
    { icon: Home, label: 'Dashboard', path: '/dashboard' },
    { icon: TrendingUp, label: 'Trading', path: '/trading' },
    { icon: Target, label: 'Positions', path: '/positions' },
    { icon: FileText, label: 'Orders', path: '/orders' },
    { icon: CreditCard, label: 'Accounts', path: '/accounts' },
    { icon: LinkIcon, label: 'Webhooks', path: '/webhooks' },
    { icon: Settings, label: 'Settings', path: '/settings' }
  ]

  const isCurrentPath = (path: string) => location.pathname === path

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <>
      {/* Navbar */}
      <div className={cn(
        "fixed top-0 left-0 h-full bg-background border-r transition-transform duration-300 z-40",
        isCollapsed ? "-translate-x-full" : "translate-x-0",
        "w-64",
        className
      )}>
        {/* Header with Toggle Button */}
        <div className="p-6 border-b relative">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 bg-primary rounded-lg flex items-center justify-center">
              <BarChart3 className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h2 className="font-semibold">Global Trading</h2>
              <p className="text-xs text-muted-foreground">Day Trading Platform</p>
            </div>
          </div>

          {/* Toggle Button - Inside Navbar Header */}
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-4 right-4 h-8 w-8"
            onClick={() => setIsCollapsed(!isCollapsed)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const isActive = isCurrentPath(item.path)
            return (
              <Button
                key={item.path}
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start",
                  isActive && "bg-primary/10 text-primary hover:bg-primary/20"
                )}
                onClick={() => navigate(item.path)}
              >
                <item.icon className="h-4 w-4 mr-3" />
                {item.label}
              </Button>
            )
          })}
        </nav>

        {/* User Section */}
        <div className="p-4 border-t">
          <div className="flex items-center space-x-3 mb-4">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs">GT</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <p className="text-sm font-medium">Global Trader</p>
              <p className="text-xs text-muted-foreground">Pro Account</p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>

      {/* Open Button - When navbar is collapsed */}
      {isCollapsed && (
        <Button
          variant="outline"
          size="icon"
          className="fixed top-4 left-4 z-50 bg-background/95 backdrop-blur-sm border shadow-lg"
          onClick={() => setIsCollapsed(false)}
        >
          <Menu className="h-4 w-4" />
        </Button>
      )}

      {/* Overlay for mobile */}
      {!isCollapsed && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-30 md:hidden"
          onClick={() => setIsCollapsed(true)}
        />
      )}
    </>
  )
}

export default CollapsibleNavbar