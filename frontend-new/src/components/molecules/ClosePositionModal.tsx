import React, { useState } from 'react'
import { X, AlertTriangle, Activity } from 'lucide-react'
import { Card } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'

interface Position {
  id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  quantity: number
  entryPrice: number
  markPrice?: number
  unrealizedPnl?: number
}

interface ClosePositionModalProps {
  position: Position
  isOpen: boolean
  onClose: () => void
  onClosePosition: (positionId: string, percentage: number) => void
}

export const ClosePositionModal: React.FC<ClosePositionModalProps> = ({
  position,
  isOpen,
  onClose,
  onClosePosition
}) => {
  const [closePercentage, setClosePercentage] = useState(100)
  const [isConfirming, setIsConfirming] = useState(false)
  const [quickCloseConfirming, setQuickCloseConfirming] = useState(false)

  if (!isOpen) return null

  const currentPrice = position.markPrice || position.entryPrice
  const quantityToClose = (position.quantity * closePercentage) / 100

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price)
  }

  const formatPnl = (pnl: number) => {
    const formatted = formatPrice(Math.abs(pnl))
    return pnl >= 0 ? `+${formatted}` : `-${formatted}`
  }

  // Calcular P&L proporcional baseado na porcentagem
  const proportionalPnl = position.unrealizedPnl
    ? (position.unrealizedPnl * closePercentage) / 100
    : 0

  const handleClose = () => {
    onClosePosition(position.id, closePercentage)
    setIsConfirming(false)
    onClose()
  }

  const handleQuickClose = () => {
    onClosePosition(position.id, 100)
    setQuickCloseConfirming(false)
    onClose()
  }

  const getCloseTypeText = () => {
    if (closePercentage === 100) return 'Encerramento Total'
    return `Encerramento Parcial (${closePercentage}%)`
  }

  const getCloseButtonText = () => {
    if (closePercentage === 100) return 'Fechar Posição Completa'
    return `Fechar ${closePercentage}% da Posição`
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-background border shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-orange-500" />
            <h2 className="text-lg font-semibold">Encerrar Posição</h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Position Info */}
          <div className="bg-accent/20 p-3 rounded-lg">
            <div className="flex justify-between items-center text-sm">
              <span className="font-medium">{position.symbol}</span>
              <Badge
                variant={position.side === 'LONG' ? 'success' : 'destructive'}
                className="text-xs px-2 py-1"
              >
                {position.side}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
              <div>
                <span className="text-muted-foreground">Entrada:</span>
                <div className="font-medium">{formatPrice(position.entryPrice)}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Atual:</span>
                <div className="font-medium">{formatPrice(currentPrice)}</div>
              </div>
              <div>
                <span className="text-muted-foreground">Quantidade:</span>
                <div className="font-medium">{position.quantity}</div>
              </div>
              <div>
                <span className="text-muted-foreground">P&L Total:</span>
                <div className={`font-medium ${
                  (position.unrealizedPnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {position.unrealizedPnl ? formatPnl(position.unrealizedPnl) : '-'}
                </div>
              </div>
            </div>
          </div>

          {/* Close Type */}
          <div className="flex items-center justify-center">
            <Badge variant="outline" className="px-3 py-1">
              <Activity className="h-3 w-3 mr-1" />
              {getCloseTypeText()}
            </Badge>
          </div>

          {/* Percentage Slider */}
          <div className="space-y-3">
            <label className="text-sm font-medium">
              Porcentagem a Fechar: {closePercentage}%
            </label>

            <div className="space-y-2">
              <input
                type="range"
                min="1"
                max="100"
                step="1"
                value={closePercentage}
                onChange={(e) => setClosePercentage(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1%</span>
                <span>25%</span>
                <span>50%</span>
                <span>75%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Quick Buttons */}
            <div className="flex space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setClosePercentage(25)}
                className="flex-1 text-xs"
              >
                25%
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setClosePercentage(50)}
                className="flex-1 text-xs"
              >
                50%
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setClosePercentage(75)}
                className="flex-1 text-xs"
              >
                75%
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setClosePercentage(100)}
                className="flex-1 text-xs"
              >
                100%
              </Button>
            </div>
          </div>

          {/* Summary */}
          <div className="bg-accent/20 p-3 rounded-lg border">
            <h4 className="text-sm font-semibold mb-2">Resumo do Fechamento</h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Quantidade a fechar:</span>
                <span className="font-medium">{quantityToClose.toFixed(4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Preço estimado:</span>
                <span className="font-medium">{formatPrice(currentPrice)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">P&L estimado:</span>
                <span className={`font-medium ${
                  proportionalPnl >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {formatPnl(proportionalPnl)}
                </span>
              </div>
              {closePercentage < 100 && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Quantidade restante:</span>
                  <span className="font-medium">{(position.quantity - quantityToClose).toFixed(4)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Warning */}
          {!isConfirming && (
            <div className="bg-orange-500/10 border border-orange-500/20 p-3 rounded-lg">
              <div className="flex items-start space-x-2">
                <AlertTriangle className="h-4 w-4 text-orange-500 mt-0.5 flex-shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-orange-700 dark:text-orange-300">
                    Atenção!
                  </p>
                  <p className="text-orange-600 dark:text-orange-400">
                    Esta ação {closePercentage === 100 ? 'fechará completamente' : 'fechará parcialmente'} sua posição e não pode ser desfeita.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t">
          {!isConfirming && !quickCloseConfirming ? (
            <div className="space-y-2">
              {/* Botão de Encerramento Rápido */}
              <Button
                variant="destructive"
                className="w-full"
                onClick={() => setQuickCloseConfirming(true)}
              >
                <X className="h-4 w-4 mr-2" />
                Fechar Posição Completa (100%)
              </Button>

              {/* Separador */}
              <div className="flex items-center space-x-2">
                <div className="flex-1 border-t"></div>
                <span className="text-xs text-muted-foreground px-2">ou</span>
                <div className="flex-1 border-t"></div>
              </div>

              {/* Botões normais */}
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={onClose}
                >
                  Cancelar
                </Button>
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setIsConfirming(true)}
                >
                  Encerramento Personalizado
                </Button>
              </div>
            </div>
          ) : quickCloseConfirming ? (
            <div className="space-y-3">
              <div className="bg-red-500/10 border border-red-500/20 p-3 rounded-lg">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <div className="text-sm">
                    <p className="font-medium text-red-700 dark:text-red-300">
                      Confirmação Final
                    </p>
                    <p className="text-red-600 dark:text-red-400">
                      Você está prestes a fechar <strong>100%</strong> da posição {position.symbol}.
                      Esta ação não pode ser desfeita.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setQuickCloseConfirming(false)}
                >
                  Cancelar
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleQuickClose}
                >
                  Sim, Fechar Tudo
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-center text-sm text-muted-foreground">
                Confirme o fechamento personalizado da posição:
              </p>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setIsConfirming(false)}
                >
                  Voltar
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleClose}
                >
                  {getCloseButtonText()}
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}