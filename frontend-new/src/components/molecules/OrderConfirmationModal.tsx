import React from 'react'
import { X, AlertTriangle, CheckCircle2 } from 'lucide-react'
import { Card } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import type { OrderFormData } from './OrderCreationModal'

interface OrderConfirmationModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  orderData: OrderFormData
  currentPrice: number
  isSubmitting?: boolean
}

export const OrderConfirmationModal: React.FC<OrderConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  orderData,
  currentPrice,
  isSubmitting = false
}) => {
  if (!isOpen) return null

  const orderPrice = orderData.orderType === 'market' ? currentPrice : orderData.price || currentPrice
  const leverageValue = orderData.operationType === 'futures' ? (orderData.leverage || 1) : 1

  const orderValue = orderData.operationType === 'futures'
    ? (orderData.quantity * orderPrice) / leverageValue
    : orderData.quantity * orderPrice

  const estimatedFee = orderValue * 0.001
  const totalCost = orderValue + estimatedFee

  const getOrderTypeLabel = () => {
    switch (orderData.orderType) {
      case 'market': return 'MERCADO'
      case 'limit': return 'LIMITADA'
      case 'stop_limit': return 'STOP-LIMIT'
      default: return orderData.orderType
    }
  }

  const getSideLabel = () => {
    return orderData.side === 'buy' ? 'COMPRA' : 'VENDA'
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-background border-2 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-accent/10">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            <h2 className="text-lg font-semibold">Confirmar Ordem</h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8"
            disabled={isSubmitting}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Warning */}
          <div className="bg-warning/10 border border-warning/20 p-3 rounded-lg">
            <div className="flex items-start space-x-2">
              <AlertTriangle className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-warning-foreground">
                  Atenção!
                </p>
                <p className="text-muted-foreground">
                  Você está prestes a executar uma ordem. Revise cuidadosamente os detalhes abaixo.
                </p>
              </div>
            </div>
          </div>

          {/* Order Details */}
          <div className="space-y-3 p-4 border rounded-lg bg-muted/30">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">Par:</span>
              <Badge variant="outline" className="text-base font-bold">
                {orderData.symbol}
              </Badge>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">Tipo:</span>
              <div className="flex items-center space-x-2">
                <Badge variant="secondary">{orderData.operationType.toUpperCase()}</Badge>
                <Badge variant="outline">{getOrderTypeLabel()}</Badge>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">Lado:</span>
              <Badge
                variant={orderData.side === 'buy' ? 'default' : 'destructive'}
                className={orderData.side === 'buy' ? 'bg-success' : ''}
              >
                {getSideLabel()}
              </Badge>
            </div>

            <div className="h-px bg-border my-2" />

            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Quantidade:</span>
              <span className="font-mono font-medium">{orderData.quantity.toFixed(8)}</span>
            </div>

            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Preço:</span>
              <span className="font-mono font-medium">${orderPrice.toFixed(2)}</span>
            </div>

            {orderData.operationType === 'futures' && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Alavancagem:</span>
                <span className="font-mono font-medium">{leverageValue}x</span>
              </div>
            )}

            {orderData.stopLoss && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Stop Loss:</span>
                <span className="font-mono font-medium text-red-600">
                  ${parseFloat(orderData.stopLoss.toString()).toFixed(2)}
                </span>
              </div>
            )}

            {orderData.takeProfit && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Take Profit:</span>
                <span className="font-mono font-medium text-green-600">
                  ${parseFloat(orderData.takeProfit.toString()).toFixed(2)}
                </span>
              </div>
            )}

            {orderData.trailingStop && (
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Trailing Stop:</span>
                <span className="font-mono font-medium text-blue-600">
                  {orderData.trailingDelta}
                  {orderData.trailingDeltaType === 'percent' ? '%' : ' USDT'}
                </span>
              </div>
            )}
          </div>

          {/* Cost Summary */}
          <div className="space-y-2 p-4 border-2 rounded-lg bg-accent/20">
            <h4 className="text-sm font-semibold mb-2">Resumo Financeiro</h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {orderData.operationType === 'futures' ? 'Margem:' : 'Valor:'}
                </span>
                <span className="font-mono">${orderValue.toFixed(2)} USDT</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Taxa:</span>
                <span className="font-mono">${estimatedFee.toFixed(2)} USDT</span>
              </div>
              <div className="flex justify-between pt-2 border-t">
                <span className="font-semibold">Total:</span>
                <span className="font-mono font-bold text-primary text-base">
                  ${totalCost.toFixed(2)} USDT
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-background">
          <div className="flex space-x-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button
              className={`flex-1 ${
                orderData.side === 'buy'
                  ? 'bg-success hover:bg-success/90'
                  : 'bg-destructive hover:bg-destructive/90'
              }`}
              onClick={onConfirm}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Processando...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Confirmar Ordem
                </>
              )}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
