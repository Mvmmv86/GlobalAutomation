/**
 * AlertToastPopup - Toast popup customizado para alertas de indicadores
 * Aparece no canto inferior esquerdo com animações e som
 */

import React, { useEffect, useState } from 'react'
import { X, Bell, TrendingUp, TrendingDown } from 'lucide-react'
import { playAlertSound, AlertSoundType } from '@/services/alertSoundService'
import { cn } from '@/lib/utils'

export interface AlertToastData {
  id: string
  title: string
  message: string
  symbol: string
  signalType: 'buy' | 'sell'
  indicator: string
  timeframe: string
  price?: number
  soundType?: AlertSoundType
}

interface AlertToastProps {
  alert: AlertToastData
  onDismiss: (id: string) => void
}

// Toast individual
const AlertToast: React.FC<AlertToastProps> = ({ alert, onDismiss }) => {
  const [isExiting, setIsExiting] = useState(false)

  const handleDismiss = () => {
    setIsExiting(true)
    setTimeout(() => onDismiss(alert.id), 300)
  }

  // Auto-dismiss after 10 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      handleDismiss()
    }, 10000)
    return () => clearTimeout(timer)
  }, [alert.id])

  const isBuy = alert.signalType === 'buy'

  return (
    <div
      className={cn(
        'relative flex items-start gap-3 p-4 rounded-lg shadow-xl border backdrop-blur-sm transition-all duration-300',
        'bg-gray-900/95 border-gray-700',
        isExiting ? 'animate-slide-out-left opacity-0' : 'animate-slide-in-left',
        isBuy ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-red-500'
      )}
      style={{ minWidth: '320px', maxWidth: '400px' }}
    >
      {/* Icon */}
      <div className={cn(
        'flex-shrink-0 p-2 rounded-full',
        isBuy ? 'bg-green-500/20' : 'bg-red-500/20'
      )}>
        {isBuy ? (
          <TrendingUp className="w-5 h-5 text-green-500" />
        ) : (
          <TrendingDown className="w-5 h-5 text-red-500" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={cn(
            'text-xs font-bold px-2 py-0.5 rounded',
            isBuy ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          )}>
            {isBuy ? 'COMPRA' : 'VENDA'}
          </span>
          <span className="text-sm font-semibold text-white">{alert.symbol}</span>
        </div>

        <p className="text-sm text-gray-300 truncate">
          {alert.indicator} - {alert.timeframe}
        </p>

        {alert.price && (
          <p className="text-xs text-gray-400 mt-1">
            Preco: ${alert.price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
          </p>
        )}

        <p className="text-xs text-gray-500 mt-1">
          {new Date().toLocaleTimeString('pt-BR')}
        </p>
      </div>

      {/* Close button */}
      <button
        onClick={handleDismiss}
        className="flex-shrink-0 p-1 text-gray-500 hover:text-white hover:bg-gray-700/50 rounded transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

// Container de toasts
interface AlertToastContainerProps {
  className?: string
}

// Store global para os toasts
let toastListeners: ((toasts: AlertToastData[]) => void)[] = []
let currentToasts: AlertToastData[] = []

// Funcao para disparar um alerta toast
export const showAlertToast = (alert: Omit<AlertToastData, 'id'>) => {
  const newToast: AlertToastData = {
    ...alert,
    id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  // Tocar som se configurado
  if (alert.soundType && alert.soundType !== 'none') {
    playAlertSound(alert.soundType, 0.7)
  }

  // Limitar a 5 toasts simultaneos
  currentToasts = [newToast, ...currentToasts].slice(0, 5)
  toastListeners.forEach(listener => listener([...currentToasts]))
}

// Funcao para remover um toast
const dismissToast = (id: string) => {
  currentToasts = currentToasts.filter(t => t.id !== id)
  toastListeners.forEach(listener => listener([...currentToasts]))
}

export const AlertToastContainer: React.FC<AlertToastContainerProps> = ({ className }) => {
  const [toasts, setToasts] = useState<AlertToastData[]>([])

  useEffect(() => {
    // Registrar listener
    toastListeners.push(setToasts)

    // Sincronizar com estado atual
    setToasts([...currentToasts])

    return () => {
      // Remover listener
      toastListeners = toastListeners.filter(l => l !== setToasts)
    }
  }, [])

  if (toasts.length === 0) return null

  return (
    <div
      className={cn(
        'fixed bottom-4 left-4 z-[200] flex flex-col gap-2',
        className
      )}
    >
      {toasts.map(toast => (
        <AlertToast
          key={toast.id}
          alert={toast}
          onDismiss={dismissToast}
        />
      ))}
    </div>
  )
}

export default AlertToastContainer
