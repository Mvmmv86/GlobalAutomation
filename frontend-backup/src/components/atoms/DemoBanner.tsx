import React from 'react'
import { Badge } from './Badge'

export const DemoBanner: React.FC = () => {
  if (import.meta.env.VITE_NODE_ENV !== 'development') {
    return null
  }

  return (
    <div className="bg-orange-50 dark:bg-orange-950/20 border-b border-orange-200 dark:border-orange-800/30 px-4 py-2">
      <div className="flex items-center justify-center space-x-2">
        <Badge variant="warning">DEMO MODE</Badge>
        <span className="text-sm text-orange-800 dark:text-orange-300">
          Dados fictícios para demonstração • Autenticação desabilitada
        </span>
      </div>
    </div>
  )
}