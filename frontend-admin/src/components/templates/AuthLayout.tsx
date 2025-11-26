import React from 'react'
import { Card } from '../atoms/Card'

interface AuthLayoutProps {
  children: React.ReactNode
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="p-8 shadow-2xl bg-white">
          {children}
        </Card>

        <div className="text-center mt-6 text-sm text-gray-400">
          <p>© 2025 Trading Platform - Admin Portal. Todos os direitos reservados.</p>
        </div>
      </div>
    </div>
  )
}