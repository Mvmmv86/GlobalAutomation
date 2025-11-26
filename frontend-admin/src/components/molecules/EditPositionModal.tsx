import React, { useState } from 'react'
import { X, Edit2, Percent } from 'lucide-react'
import { Card } from '../atoms/Card'
import { Button } from '../atoms/Button'

interface Position {
  id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  quantity: number
  entryPrice: number
  markPrice?: number
  unrealizedPnl?: number
  stopLoss?: number
  takeProfit?: number
}

interface EditPositionModalProps {
  position: Position
  isOpen: boolean
  onClose: () => void
  onSave: (positionId: string, data: { stopLoss?: number; takeProfit?: number }) => void
}

export const EditPositionModal: React.FC<EditPositionModalProps> = ({
  position,
  isOpen,
  onClose,
  onSave
}) => {
  const [usePercentage, setUsePercentage] = useState(false)

  // Estados para valores absolutos
  const [stopLossValue, setStopLossValue] = useState(position.stopLoss || 0)
  const [takeProfitValue, setTakeProfitValue] = useState(position.takeProfit || 0)

  // Estados para percentuais
  const [stopLossPercent, setStopLossPercent] = useState(5)
  const [takeProfitPercent, setTakeProfitPercent] = useState(10)

  if (!isOpen) return null

  const currentPrice = position.markPrice || position.entryPrice
  const isLong = position.side === 'LONG'

  // Calcular preços baseados em percentual
  const calculateStopLossFromPercent = (percent: number) => {
    if (isLong) {
      return currentPrice * (1 - percent / 100)
    } else {
      return currentPrice * (1 + percent / 100)
    }
  }

  const calculateTakeProfitFromPercent = (percent: number) => {
    if (isLong) {
      return currentPrice * (1 + percent / 100)
    } else {
      return currentPrice * (1 - percent / 100)
    }
  }

  const handleSave = () => {
    const finalStopLoss = usePercentage
      ? calculateStopLossFromPercent(stopLossPercent)
      : stopLossValue

    const finalTakeProfit = usePercentage
      ? calculateTakeProfitFromPercent(takeProfitPercent)
      : takeProfitValue

    onSave(position.id, {
      stopLoss: finalStopLoss > 0 ? finalStopLoss : undefined,
      takeProfit: finalTakeProfit > 0 ? finalTakeProfit : undefined
    })
    onClose()
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price)
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-background border shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center space-x-2">
            <Edit2 className="h-4 w-4 text-primary" />
            <h2 className="text-lg font-semibold">Editar Posição</h2>
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
              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                position.side === 'LONG'
                  ? 'bg-green-500/20 text-green-600'
                  : 'bg-red-500/20 text-red-600'
              }`}>
                {position.side}
              </span>
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
                <span className="text-muted-foreground">P&L:</span>
                <div className={`font-medium ${
                  (position.unrealizedPnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {position.unrealizedPnl ? formatPrice(position.unrealizedPnl) : '-'}
                </div>
              </div>
            </div>
          </div>

          {/* Toggle Mode */}
          <div className="flex items-center justify-center space-x-2">
            <Button
              variant={!usePercentage ? "default" : "outline"}
              size="sm"
              onClick={() => setUsePercentage(false)}
              className="flex items-center space-x-1"
            >
              <span>Valores</span>
            </Button>
            <Button
              variant={usePercentage ? "default" : "outline"}
              size="sm"
              onClick={() => setUsePercentage(true)}
              className="flex items-center space-x-1"
            >
              <Percent className="h-3 w-3" />
              <span>Percentual</span>
            </Button>
          </div>

          {/* Stop Loss */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center space-x-2">
              <span>Stop Loss</span>
              {usePercentage && (
                <span className="text-xs text-muted-foreground">
                  (≈ {formatPrice(calculateStopLossFromPercent(stopLossPercent))})
                </span>
              )}
            </label>

            {usePercentage ? (
              <div className="space-y-2">
                <div className="relative">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="0.5"
                    value={stopLossPercent}
                    onChange={(e) => setStopLossPercent(Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider yellow-thumb"
                    style={{
                      background: `linear-gradient(to right, #ef4444 0%, #ef4444 ${stopLossPercent}%, #e5e7eb ${stopLossPercent}%, #e5e7eb 100%)`
                    }}
                  />
                  <style jsx>{`
                    .yellow-thumb::-webkit-slider-thumb {
                      appearance: none;
                      height: 16px;
                      width: 16px;
                      border-radius: 50%;
                      background: #eab308;
                      cursor: pointer;
                      border: 2px solid #ffffff;
                      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    }
                    .yellow-thumb::-moz-range-thumb {
                      height: 16px;
                      width: 16px;
                      border-radius: 50%;
                      background: #eab308;
                      cursor: pointer;
                      border: 2px solid #ffffff;
                      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    }
                  `}</style>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0%</span>
                  <span className="font-semibold">{stopLossPercent}%</span>
                  <span>100%</span>
                </div>
              </div>
            ) : (
              <input
                type="number"
                value={stopLossValue}
                onChange={(e) => setStopLossValue(Number(e.target.value))}
                placeholder="0.00"
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            )}
          </div>

          {/* Take Profit */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center space-x-2">
              <span>Take Profit</span>
              {usePercentage && (
                <span className="text-xs text-muted-foreground">
                  (≈ {formatPrice(calculateTakeProfitFromPercent(takeProfitPercent))})
                </span>
              )}
            </label>

            {usePercentage ? (
              <div className="space-y-2">
                <div className="relative">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="1"
                    value={takeProfitPercent}
                    onChange={(e) => setTakeProfitPercent(Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider yellow-thumb"
                    style={{
                      background: `linear-gradient(to right, #22c55e 0%, #22c55e ${takeProfitPercent}%, #e5e7eb ${takeProfitPercent}%, #e5e7eb 100%)`
                    }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>0%</span>
                  <span className="font-semibold">{takeProfitPercent}%</span>
                  <span>100%</span>
                </div>
              </div>
            ) : (
              <input
                type="number"
                value={takeProfitValue}
                onChange={(e) => setTakeProfitValue(Number(e.target.value))}
                placeholder="0.00"
                className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex space-x-2 p-4 border-t">
          <Button
            variant="outline"
            className="flex-1"
            onClick={onClose}
          >
            Cancelar
          </Button>
          <Button
            className="flex-1"
            onClick={handleSave}
          >
            Salvar Alterações
          </Button>
        </div>
      </Card>
    </div>
  )
}