import React, { useState } from 'react'
import { TrendingUp, TrendingDown, Calculator, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../atoms/Tabs'
import { FormField } from '../molecules/FormField'
import { AccountSelector, ExchangeAccount } from '../molecules/AccountSelector'
import { PriceDisplay } from '../molecules/PriceDisplay'
import { RiskMeter } from '../molecules/RiskMeter'
import { Badge } from '../atoms/Badge'
import { Slider } from '../atoms/Slider'
import { Switch } from '../atoms/Switch'
import { cn } from '@/lib/utils'

interface TradingPanelProps {
  symbol: string
  currentPrice: number
  accounts: ExchangeAccount[]
  onOrderSubmit: (order: OrderData) => void
  className?: string
}

interface OrderData {
  accountId: string
  symbol: string
  side: 'buy' | 'sell'
  type: 'market' | 'limit' | 'stop'
  quantity: number
  price?: number
  stopPrice?: number
  leverage?: number
  stopLoss?: number
  takeProfit?: number
}

const TradingPanel: React.FC<TradingPanelProps> = ({
  symbol,
  currentPrice,
  accounts,
  onOrderSubmit,
  className
}) => {
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy')
  const [orderType, setOrderType] = useState<'market' | 'limit' | 'stop'>('market')
  const [quantity, setQuantity] = useState<string>('')
  const [price, setPrice] = useState<string>('')
  const [stopPrice, setStopPrice] = useState<string>('')
  const [leverage, setLeverage] = useState<number>(1)
  const [stopLoss, setStopLoss] = useState<string>('')
  const [takeProfit, setTakeProfit] = useState<string>('')
  const [useRiskManagement, setUseRiskManagement] = useState<boolean>(false)
  const [positionSize, setPositionSize] = useState<number>(25) // Percentage

  // Calculate order value and fees
  const orderPrice = orderType === 'market' ? currentPrice : parseFloat(price) || currentPrice
  const orderQuantity = parseFloat(quantity) || 0
  const orderValue = orderPrice * orderQuantity
  const estimatedFee = orderValue * 0.001 // 0.1% fee
  const riskLevel = Math.min((orderValue / 10000) * 100, 100) // Simplified risk calculation

  const handleSubmit = () => {
    if (!selectedAccount || !quantity) return

    const orderData: OrderData = {
      accountId: selectedAccount,
      symbol,
      side: orderSide,
      type: orderType,
      quantity: orderQuantity,
      ...(orderType !== 'market' && { price: parseFloat(price) }),
      ...(orderType === 'stop' && { stopPrice: parseFloat(stopPrice) }),
      leverage,
      ...(stopLoss && { stopLoss: parseFloat(stopLoss) }),
      ...(takeProfit && { takeProfit: parseFloat(takeProfit) })
    }

    onOrderSubmit(orderData)
  }

  return (
    <Card className={cn("w-full max-w-md", className)}>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center justify-between">
          <span>Trade {symbol}</span>
          <PriceDisplay 
            price={currentPrice} 
            size="sm" 
            showChange={false}
          />
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Account Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Trading Account</label>
          <AccountSelector
            accounts={accounts}
            selectedAccountId={selectedAccount}
            onAccountChange={setSelectedAccount}
            placeholder="Select account to trade"
          />
        </div>

        {/* Order Side Tabs */}
        <Tabs value={orderSide} onValueChange={(value) => setOrderSide(value as 'buy' | 'sell')}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="buy" className="text-success data-[state=active]:bg-success/20">
              <TrendingUp className="h-4 w-4 mr-2" />
              Buy
            </TabsTrigger>
            <TabsTrigger value="sell" className="text-destructive data-[state=active]:bg-destructive/20">
              <TrendingDown className="h-4 w-4 mr-2" />
              Sell
            </TabsTrigger>
          </TabsList>

          <TabsContent value={orderSide} className="space-y-4 mt-4">
            {/* Order Type */}
            <Tabs value={orderType} onValueChange={(value) => setOrderType(value as 'market' | 'limit' | 'stop')}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="market">Market</TabsTrigger>
                <TabsTrigger value="limit">Limit</TabsTrigger>
                <TabsTrigger value="stop">Stop</TabsTrigger>
              </TabsList>

              <TabsContent value="market" className="space-y-4 mt-4">
                <FormField
                  label="Quantity"
                  type="number"
                  placeholder="0.00000000"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  hint={`≈ ${(orderQuantity * currentPrice).toFixed(2)} USDT`}
                />
              </TabsContent>

              <TabsContent value="limit" className="space-y-4 mt-4">
                <FormField
                  label="Price"
                  type="number"
                  placeholder={currentPrice.toString()}
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
                <FormField
                  label="Quantity"
                  type="number"
                  placeholder="0.00000000"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  hint={`≈ ${orderValue.toFixed(2)} USDT`}
                />
              </TabsContent>

              <TabsContent value="stop" className="space-y-4 mt-4">
                <FormField
                  label="Stop Price"
                  type="number"
                  placeholder={currentPrice.toString()}
                  value={stopPrice}
                  onChange={(e) => setStopPrice(e.target.value)}
                />
                <FormField
                  label="Quantity"
                  type="number"
                  placeholder="0.00000000"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  hint={`≈ ${orderValue.toFixed(2)} USDT`}
                />
              </TabsContent>
            </Tabs>

            {/* Position Size Slider */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Position Size</label>
                <Badge variant="outline">{positionSize}%</Badge>
              </div>
              <Slider
                value={[positionSize]}
                onValueChange={(value) => setPositionSize(value[0])}
                max={100}
                step={5}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>25%</span>
                <span>50%</span>
                <span>75%</span>
                <span>100%</span>
              </div>
            </div>

            {/* Leverage */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Leverage</label>
                <Badge variant="outline">{leverage}x</Badge>
              </div>
              <Slider
                value={[leverage]}
                onValueChange={(value) => setLeverage(value[0])}
                max={125}
                min={1}
                step={1}
                className="w-full"
              />
            </div>

            {/* Risk Management Toggle */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="h-4 w-4 text-warning" />
                <label className="text-sm font-medium">Risk Management</label>
              </div>
              <Switch
                checked={useRiskManagement}
                onCheckedChange={setUseRiskManagement}
              />
            </div>

            {/* Risk Management Fields */}
            {useRiskManagement && (
              <div className="space-y-3 p-3 border rounded-lg bg-muted/50">
                <FormField
                  label="Stop Loss"
                  type="number"
                  placeholder="Stop loss price"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(e.target.value)}
                />
                <FormField
                  label="Take Profit"
                  type="number"
                  placeholder="Take profit price"
                  value={takeProfit}
                  onChange={(e) => setTakeProfit(e.target.value)}
                />
              </div>
            )}

            {/* Risk Meter */}
            <RiskMeter
              riskLevel={riskLevel}
              label="Order Risk"
              size="sm"
              variant="linear"
            />

            {/* Order Summary */}
            <div className="space-y-2 p-3 border rounded-lg bg-muted/30">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Order Value:</span>
                <span className="font-mono">{orderValue.toFixed(2)} USDT</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Est. Fee:</span>
                <span className="font-mono">{estimatedFee.toFixed(2)} USDT</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Total:</span>
                <span className="font-mono font-medium">
                  {(orderValue + estimatedFee).toFixed(2)} USDT
                </span>
              </div>
            </div>

            {/* Submit Button */}
            <Button
              onClick={handleSubmit}
              className={cn(
                "w-full",
                orderSide === 'buy' ? "bg-success hover:bg-success/90" : "bg-destructive hover:bg-destructive/90"
              )}
              disabled={!selectedAccount || !quantity}
            >
              <Calculator className="h-4 w-4 mr-2" />
              {orderSide === 'buy' ? 'Buy' : 'Sell'} {symbol}
            </Button>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export { TradingPanel }
export type { TradingPanelProps, OrderData }