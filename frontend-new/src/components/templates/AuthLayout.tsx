import React from 'react'
import { Card } from '../atoms/Card'

interface AuthLayoutProps {
  children: React.ReactNode
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-primary mb-2">
            Trading Platform
          </h1>
          <p className="text-muted-foreground">
            Conecte suas exchanges e automatize seus trades
          </p>
        </div>
        
        <Card className="p-6 shadow-lg">
          {children}
        </Card>
        
        <div className="text-center mt-6 text-sm text-muted-foreground">
          <p>© 2025 Trading Platform. Todos os direitos reservados.</p>
        </div>
      </div>
    </div>
  )
}