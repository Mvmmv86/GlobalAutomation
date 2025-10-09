import React, { useState, useEffect } from 'react'
import { X, TrendingUp, TrendingDown, AlertTriangle, DollarSign } from 'lucide-react'
import { Card } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../atoms/Tabs'

interface OrderCreationModalProps {
  isOpen: boolean
  onClose: () => void
  symbol: string
  initialPrice?: number
  initialSide?: 'buy' | 'sell'
  accounts: Array<{ id: string; name: string; exchange: string }>
  selectedAccountId?: string
  onConfirm: (orderData: OrderFormData) => void
}

export interface OrderFormData {
  accountId: string
  symbol: string
  side: 'buy' | 'sell'
  orderType: 'market' | 'limit' | 'stop_limit'
  operationType: 'spot' | 'futures'
  quantity: number
  price?: number
  stopPrice?: number
  leverage?: number
  stopLoss?: number
  takeProfit?: number
  trailingStop?: boolean
  trailingDelta?: number
  trailingDeltaType?: 'amount' | 'percent'
}

export const OrderCreationModal: React.FC<OrderCreationModalProps> = ({
  isOpen,
  onClose,
  symbol,
  initialPrice = 0,
  initialSide = 'buy',
  accounts,
  selectedAccountId = '',
  onConfirm
}) => {
  // Form states
  const [accountId, setAccountId] = useState(selectedAccountId)
  const [side, setSide] = useState<'buy' | 'sell'>(initialSide)
  const [orderType, setOrderType] = useState<'market' | 'limit' | 'stop_limit'>('market')
  const [operationType, setOperationType] = useState<'spot' | 'futures'>('futures')
  const [quantity, setQuantity] = useState('')
  const [price, setPrice] = useState(initialPrice.toString())
  const [stopPrice, setStopPrice] = useState('')
  const [leverage, setLeverage] = useState(10)
  const [stopLoss, setStopLoss] = useState('')
  const [takeProfit, setTakeProfit] = useState('')
  const [useRiskManagement, setUseRiskManagement] = useState(false)
  const [trailingStop, setTrailingStop] = useState(false)
  const [trailingDelta, setTrailingDelta] = useState('1')
  const [trailingDeltaType, setTrailingDeltaType] = useState<'amount' | 'percent'>('percent')

  // Atualizar account quando prop mudar
  useEffect(() => {
    if (selectedAccountId) {
      setAccountId(selectedAccountId)
    }
  }, [selectedAccountId])

  // Atualizar preço quando prop mudar
  useEffect(() => {
    if (initialPrice > 0) {
      setPrice(initialPrice.toString())
    }
  }, [initialPrice])

  if (!isOpen) return null

  // Cálculos
  const orderPrice = orderType === 'market' ? initialPrice : parseFloat(price) || initialPrice
  const orderQuantity = parseFloat(quantity) || 0
  const leverageValue = operationType === 'futures' ? leverage : 1

  const orderValue = operationType === 'futures'
    ? (orderQuantity * orderPrice) / leverageValue // Margem necessária
    : orderQuantity * orderPrice // Valor total SPOT

  const estimatedFee = orderValue * 0.001 // 0.1% fee
  const totalCost = orderValue + estimatedFee

  const handleSubmit = () => {
    console.log('🟢 OrderCreationModal handleSubmit called!')

    const orderData: OrderFormData = {
      accountId,
      symbol,
      side,
      orderType,
      operationType,
      quantity: orderQuantity,
      ...(orderType !== 'market' && { price: parseFloat(price) }),
      ...(orderType === 'stop_limit' && { stopPrice: parseFloat(stopPrice) }),
      ...(operationType === 'futures' && { leverage: leverageValue }),
      ...(stopLoss && { stopLoss: parseFloat(stopLoss) }),
      ...(takeProfit && { takeProfit: parseFloat(takeProfit) }),
      ...(trailingStop && {
        trailingStop: true,
        trailingDelta: parseFloat(trailingDelta),
        trailingDeltaType
      })
    }

    console.log('✅ OrderCreationModal calling onConfirm with:', orderData)
    onConfirm(orderData)
  }

  const isFormValid = accountId && quantity && orderQuantity > 0 &&
    (orderType === 'market' || (price && parseFloat(price) > 0)) &&
    (orderType !== 'stop_limit' || (stopPrice && parseFloat(stopPrice) > 0))

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl bg-background border shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-background z-10">
          <div className="flex items-center space-x-2">
            <DollarSign className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold">Criar Ordem - {symbol}</h2>
            {initialPrice > 0 && (
              <Badge variant="outline" className="text-xs">
                ${initialPrice.toFixed(2)}
              </Badge>
            )}
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
          {/* Account Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Conta de Negociação</label>
            <select
              value={accountId}
              onChange={(e) => setAccountId(e.target.value)}
              className="w-full p-2 border rounded-md bg-background"
            >
              <option value="">Selecione uma conta</option>
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.exchange})
                </option>
              ))}
            </select>
          </div>

          {/* Operation Type */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Tipo de Operação</label>
            <Tabs value={operationType} onValueChange={(v) => setOperationType(v as 'spot' | 'futures')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="futures">FUTURES</TabsTrigger>
                <TabsTrigger value="spot">SPOT</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Side Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Lado</label>
            <Tabs value={side} onValueChange={(v) => setSide(v as 'buy' | 'sell')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="buy" className="text-success data-[state=active]:bg-success/20">
                  <TrendingUp className="h-4 w-4 mr-2" />
                  COMPRAR
                </TabsTrigger>
                <TabsTrigger value="sell" className="text-destructive data-[state=active]:bg-destructive/20">
                  <TrendingDown className="h-4 w-4 mr-2" />
                  VENDER
                </TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Order Type */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Tipo de Ordem</label>
            <Tabs value={orderType} onValueChange={(v) => setOrderType(v as any)}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="market">MARKET</TabsTrigger>
                <TabsTrigger value="limit">LIMIT</TabsTrigger>
                <TabsTrigger value="stop_limit">STOP</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Price Fields */}
          <div className="grid grid-cols-2 gap-4">
            {orderType !== 'market' && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Preço</label>
                <input
                  type="number"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  className="w-full p-2 border rounded-md bg-background"
                />
              </div>
            )}

            {orderType === 'stop_limit' && (
              <div className="space-y-2">
                <label className="text-sm font-medium">Preço Stop</label>
                <input
                  type="number"
                  value={stopPrice}
                  onChange={(e) => setStopPrice(e.target.value)}
                  placeholder="0.00"
                  step="0.01"
                  className="w-full p-2 border rounded-md bg-background"
                />
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium">Quantidade</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="0.00000000"
                step="0.00000001"
                className="w-full p-2 border rounded-md bg-background"
              />
              <p className="text-xs text-muted-foreground">
                ≈ ${(orderQuantity * orderPrice).toFixed(2)} USDT
              </p>
            </div>
          </div>

          {/* Leverage - Only for FUTURES */}
          {operationType === 'futures' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Alavancagem</label>
                <Badge variant="outline">{leverage}x</Badge>
              </div>
              <input
                type="range"
                min="1"
                max="125"
                value={leverage}
                onChange={(e) => setLeverage(Number(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1x</span>
                <span>25x</span>
                <span>50x</span>
                <span>75x</span>
                <span>125x</span>
              </div>
            </div>
          )}

          {/* Risk Management Toggle */}
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-4 w-4 text-warning" />
              <label className="text-sm font-medium">Gerenciamento de Risco</label>
            </div>
            <input
              type="checkbox"
              checked={useRiskManagement}
              onChange={(e) => setUseRiskManagement(e.target.checked)}
              className="w-4 h-4"
            />
          </div>

          {/* Risk Management Fields */}
          {useRiskManagement && (
            <div className="space-y-3 p-3 border rounded-lg bg-muted/50">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Stop Loss</label>
                  <input
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(e.target.value)}
                    placeholder="Preço de stop loss"
                    step="0.01"
                    className="w-full p-2 border rounded-md bg-background"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Take Profit</label>
                  <input
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(e.target.value)}
                    placeholder="Preço de take profit"
                    step="0.01"
                    className="w-full p-2 border rounded-md bg-background"
                  />
                </div>
              </div>

              {/* Trailing Stop */}
              <div className="flex items-center justify-between pt-2 border-t">
                <label className="text-sm font-medium">Trailing Stop</label>
                <input
                  type="checkbox"
                  checked={trailingStop}
                  onChange={(e) => setTrailingStop(e.target.checked)}
                  className="w-4 h-4"
                />
              </div>

              {trailingStop && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Delta</label>
                    <input
                      type="number"
                      value={trailingDelta}
                      onChange={(e) => setTrailingDelta(e.target.value)}
                      placeholder="1"
                      step="0.1"
                      className="w-full p-2 border rounded-md bg-background"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Tipo</label>
                    <select
                      value={trailingDeltaType}
                      onChange={(e) => setTrailingDeltaType(e.target.value as 'amount' | 'percent')}
                      className="w-full p-2 border rounded-md bg-background"
                    >
                      <option value="percent">Porcentagem (%)</option>
                      <option value="amount">USDT</option>
                    </select>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Order Summary */}
          <div className="space-y-2 p-4 border rounded-lg bg-accent/20">
            <h4 className="text-sm font-semibold mb-2">Resumo da Ordem</h4>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {operationType === 'futures' ? 'Margem Necessária:' : 'Valor da Ordem:'}
                </span>
                <span className="font-mono font-medium">${orderValue.toFixed(2)} USDT</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Taxa Estimada (0.1%):</span>
                <span className="font-mono">${estimatedFee.toFixed(2)} USDT</span>
              </div>
              <div className="flex justify-between pt-2 border-t">
                <span className="text-muted-foreground font-medium">Total:</span>
                <span className="font-mono font-bold text-primary">
                  ${totalCost.toFixed(2)} USDT
                </span>
              </div>
              {operationType === 'futures' && (
                <div className="flex justify-between text-xs text-muted-foreground pt-1">
                  <span>Posição total:</span>
                  <span>${(orderQuantity * orderPrice).toFixed(2)} USDT ({leverage}x)</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-background sticky bottom-0">
          <div className="flex space-x-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={onClose}
            >
              Cancelar
            </Button>
            <Button
              className={`flex-1 ${
                side === 'buy'
                  ? 'bg-success hover:bg-success/90'
                  : 'bg-destructive hover:bg-destructive/90'
              }`}
              onClick={handleSubmit}
              disabled={!isFormValid}
            >
              {side === 'buy' ? 'Comprar' : 'Vender'} {symbol}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
