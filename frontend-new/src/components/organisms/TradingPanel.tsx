import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react'
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
import { useAccountBalance, useSpotBalances } from '@/hooks/useApiData'

// Custom debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

interface TradingPanelProps {
  symbol: string
  currentPrice: number
  accounts: ExchangeAccount[]
  selectedAccountId?: string
  onAccountChange?: (accountId: string) => void
  onOrderSubmit: (order: OrderData) => void
  isSubmitting?: boolean
  className?: string
}

interface OrderData {
  accountId: string
  symbol: string
  side: 'buy' | 'sell'
  type: 'market' | 'limit' | 'stop'
  operationType: 'futures' | 'spot'
  quantity: number
  marginUsdt: number
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
  selectedAccountId = '',
  onAccountChange,
  onOrderSubmit,
  isSubmitting = false,
  className
}) => {
  // Get account balance for selected account
  const { data: accountBalance } = useAccountBalance(selectedAccountId)
  const { data: spotBalancesData } = useSpotBalances(selectedAccountId)

  // Available balance for calculation
  const availableFuturesBalance = accountBalance?.futures_balance_usdt || 0

  // SPOT: Extrair BASE e QUOTE do símbolo (ex: BTCUSDT → BTC=base, USDT=quote)
  const getBaseAndQuote = (symbol: string): { base: string; quote: string } => {
    // Para pares USDT: remove USDT do final
    if (symbol.endsWith('USDT')) {
      return { base: symbol.replace('USDT', ''), quote: 'USDT' }
    }
    // Para pares BUSD: remove BUSD do final
    if (symbol.endsWith('BUSD')) {
      return { base: symbol.replace('BUSD', ''), quote: 'BUSD' }
    }
    // Para pares BTC: remove BTC do final
    if (symbol.endsWith('BTC')) {
      return { base: symbol.replace('BTC', ''), quote: 'BTC' }
    }
    // Default: assume últimos 4 chars são quote
    return { base: symbol.slice(0, -4), quote: symbol.slice(-4) }
  }

  const { base: baseAsset, quote: quoteAsset } = getBaseAndQuote(symbol)

  // SPOT: Buscar saldo do ativo específico
  const getAssetBalance = (asset: string): number => {
    if (!spotBalancesData?.assets) return 0
    const assetData = spotBalancesData.assets.find(a => a.asset === asset)
    return assetData?.free || 0
  }

  const [operationType, setOperationType] = useState<'futures' | 'spot'>('futures')
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy')
  const [orderType, setOrderType] = useState<'market' | 'limit' | 'stop'>('market')
  const [quantity, setQuantity] = useState<string>('')
  const [marginUsdt, setMarginUsdt] = useState<string>('')
  const [price, setPrice] = useState<string>('')
  const [stopPrice, setStopPrice] = useState<string>('')
  const [leverage, setLeverage] = useState<number>(1)
  const [stopLoss, setStopLoss] = useState<string>('')
  const [takeProfit, setTakeProfit] = useState<string>('')
  const [useRiskManagement, setUseRiskManagement] = useState<boolean>(false)
  const [positionSize, setPositionSize] = useState<number>(25) // Percentage

  // SPOT: Calcular saldo disponível baseado em BUY/SELL
  const availableSpotBalance = useMemo(() => {
    if (operationType !== 'spot') return 0

    if (orderSide === 'buy') {
      // COMPRA: usar saldo REAL de USDT (quote)
      return getAssetBalance(quoteAsset)
    } else {
      // VENDA: usar saldo REAL do ativo base (convertido em USDT para exibição)
      const baseBalance = getAssetBalance(baseAsset)
      return baseBalance * currentPrice // Converter para USDT só para exibição
    }
  }, [operationType, orderSide, spotBalancesData, baseAsset, quoteAsset, currentPrice])

  // Auto-set initial margin/quantity when account balance loads OR when BUY/SELL changes
  React.useEffect(() => {
    if (operationType === 'futures' && availableFuturesBalance > 0 && currentPrice > 0) {
      const initialMargin = (availableFuturesBalance * positionSize / 100).toFixed(2)
      setMarginUsdt(initialMargin)
      const initialQuantity = (parseFloat(initialMargin) * leverage / currentPrice).toFixed(8)
      setQuantity(initialQuantity)
    } else if (operationType === 'spot' && currentPrice > 0) {
      if (orderSide === 'buy') {
        // BUY: usar USDT real
        const usdtBalance = getAssetBalance(quoteAsset)
        const initialUsdtAmount = (usdtBalance * positionSize / 100)
        const initialQuantity = (initialUsdtAmount / currentPrice).toFixed(8)
        setQuantity(initialQuantity)
        setMarginUsdt(initialUsdtAmount.toFixed(2))
      } else {
        // SELL: usar quantidade do ativo BASE
        const baseBalance = getAssetBalance(baseAsset)
        const initialQuantity = (baseBalance * positionSize / 100).toFixed(8)
        setQuantity(initialQuantity)
        const initialMargin = (parseFloat(initialQuantity) * currentPrice).toFixed(2)
        setMarginUsdt(initialMargin)
      }
    }
  }, [availableFuturesBalance, operationType, orderSide, currentPrice, positionSize, leverage, baseAsset, quoteAsset])

  // FASE 2: Debounce quantity and margin inputs (300ms delay)
  const debouncedQuantity = useDebounce(quantity, 300)
  const debouncedMarginUsdt = useDebounce(marginUsdt, 300)

  // FASE 2: Memoize expensive calculations to avoid re-computing on every render
  const orderPrice = useMemo(() => {
    return orderType === 'market' ? currentPrice : parseFloat(price) || currentPrice
  }, [orderType, currentPrice, price])

  const orderQuantity = useMemo(() => {
    return parseFloat(debouncedQuantity) || 0
  }, [debouncedQuantity])

  const marginUsdtValue = useMemo(() => {
    return parseFloat(debouncedMarginUsdt) || 0
  }, [debouncedMarginUsdt])

  // 🚀 PERFORMANCE: Debug logs commented out to reduce overhead
  // console.log('🔍 TradingPanel Debug:', {
  //   selectedAccountId,
  //   operationType,
  //   orderSide,
  //   symbol,
  //   baseAsset,
  //   quoteAsset,
  //   marginUsdt,
  //   quantity,
  //   marginUsdtValue,
  //   orderQuantity,
  //   availableFuturesBalance,
  //   availableSpotBalance,
  //   spotAssets: spotBalancesData?.assets?.map(a => ({ asset: a.asset, free: a.free })),
  //   accountBalance,
  //   buttonDisabled: !selectedAccountId || (operationType === 'futures' ? marginUsdtValue <= 0 : orderQuantity <= 0)
  // })

  // FASE 2: Memoize more expensive calculations
  const orderValue = useMemo(() => {
    return operationType === 'futures' ? marginUsdtValue : orderPrice * orderQuantity
  }, [operationType, marginUsdtValue, orderPrice, orderQuantity])

  const estimatedFee = useMemo(() => {
    return orderValue * 0.001 // 0.1% fee
  }, [orderValue])

  const riskLevel = useMemo(() => {
    return Math.min((orderValue / 10000) * 100, 100) // Simplified risk calculation
  }, [orderValue])

  // Synchronize quantity and margin USDT
  const handleQuantityChange = (value: string) => {
    setQuantity(value)
    if (value && orderPrice) {
      if (operationType === 'futures') {
        const calculatedMargin = parseFloat(value) * orderPrice / leverage
        setMarginUsdt(calculatedMargin.toFixed(2))
      } else {
        // SPOT: marginUsdt = quantidade * preço (valor total em USDT)
        const calculatedTotal = parseFloat(value) * orderPrice
        setMarginUsdt(calculatedTotal.toFixed(2))
      }
    }
  }

  const handleMarginUsdtChange = (value: string) => {
    setMarginUsdt(value)
    if (value && orderPrice) {
      if (operationType === 'futures') {
        const calculatedQuantity = parseFloat(value) * leverage / orderPrice
        setQuantity(calculatedQuantity.toFixed(8))
      } else {
        // SPOT BUY: quantidade = valor USDT / preço
        // SPOT SELL: marginUsdt é valor em USDT, precisa converter para quantidade do ativo
        if (orderSide === 'buy') {
          const calculatedQuantity = parseFloat(value) / orderPrice
          setQuantity(calculatedQuantity.toFixed(8))
        } else {
          // SELL: já digitou em USDT, converter para quantidade do ativo
          const calculatedQuantity = parseFloat(value) / orderPrice
          setQuantity(calculatedQuantity.toFixed(8))
        }
      }
    }
  }

  const handleSubmit = () => {
    console.log('🔵 TradingPanel handleSubmit called!', {
      selectedAccountId,
      quantity,
      marginUsdt,
      operationType
    })

    if (!selectedAccountId || !quantity) {
      console.log('❌ TradingPanel validation failed:', {
        hasAccount: !!selectedAccountId,
        hasQuantity: !!quantity
      })
      return
    }

    const orderData: OrderData = {
      accountId: selectedAccountId,
      symbol,
      side: orderSide,
      type: orderType,
      operationType,
      quantity: orderQuantity,
      marginUsdt: marginUsdtValue,
      ...(orderType !== 'market' && { price: parseFloat(price) }),
      ...(orderType === 'stop' && { stopPrice: parseFloat(stopPrice) }),
      leverage,
      ...(stopLoss && { stopLoss: parseFloat(stopLoss) }),
      ...(takeProfit && { takeProfit: parseFloat(takeProfit) })
    }

    console.log('✅ TradingPanel calling onOrderSubmit with:', orderData)
    onOrderSubmit(orderData)
  }

  return (
    <Card className={cn("w-full max-w-lg", className)}>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center justify-between">
          <span>Trade</span>
          <Badge variant="outline" className="text-sm font-semibold px-2 py-0.5 mr-4">
            {symbol}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Account Selection */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Conta de Negociação</label>
            {selectedAccountId && (
              <div className="text-xs text-muted-foreground">
                <span className="font-mono">
                  {operationType === 'futures' ?
                    (accountBalance ? `${accountBalance.futures_balance_usdt?.toFixed(2) || '0.00'} USDT` : 'Carregando...') :
                    (spotBalancesData ? `${spotBalancesData.total_usd_value?.toFixed(2) || '0.00'} USDT` : 'Carregando...')
                  }
                </span>
              </div>
            )}
          </div>
          <AccountSelector
            accounts={accounts}
            selectedAccountId={selectedAccountId}
            onAccountChange={onAccountChange}
            placeholder="Selecionar conta para negociar"
          />
        </div>

        {/* Operation Type Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Tipo de Operação</label>
          <Tabs value={operationType} onValueChange={(value) => setOperationType(value as 'futures' | 'spot')}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="futures">FUTURES</TabsTrigger>
              <TabsTrigger value="spot">SPOT</TabsTrigger>
            </TabsList>
          </Tabs>
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
                  label="Quantidade"
                  type="number"
                  placeholder="0.00000000"
                  value={quantity}
                  onChange={(e) => handleQuantityChange(e.target.value)}
                  hint={`≈ ${(orderQuantity * currentPrice).toFixed(2)} USDT`}
                />
                <FormField
                  label={operationType === 'futures' ? 'Margem USDT' : 'Valor em USDT'}
                  type="number"
                  placeholder="0.00"
                  value={marginUsdt}
                  onChange={(e) => handleMarginUsdtChange(e.target.value)}
                  hint={operationType === 'futures' ? `Leverage ${leverage}x` : 'Valor total da ordem'}
                />
              </TabsContent>

              <TabsContent value="limit" className="space-y-4 mt-4">
                <FormField
                  label="Preço"
                  type="number"
                  placeholder={currentPrice.toString()}
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
                <FormField
                  label="Quantidade"
                  type="number"
                  placeholder="0.00000000"
                  value={quantity}
                  onChange={(e) => handleQuantityChange(e.target.value)}
                  hint={`≈ ${orderValue.toFixed(2)} USDT`}
                />
                <FormField
                  label={operationType === 'futures' ? 'Margem USDT' : 'Valor em USDT'}
                  type="number"
                  placeholder="0.00"
                  value={marginUsdt}
                  onChange={(e) => handleMarginUsdtChange(e.target.value)}
                  hint={operationType === 'futures' ? `Leverage ${leverage}x` : 'Valor total da ordem'}
                />
              </TabsContent>

              <TabsContent value="stop" className="space-y-4 mt-4">
                <FormField
                  label="Preço Stop"
                  type="number"
                  placeholder={currentPrice.toString()}
                  value={stopPrice}
                  onChange={(e) => setStopPrice(e.target.value)}
                />
                <FormField
                  label="Quantidade"
                  type="number"
                  placeholder="0.00000000"
                  value={quantity}
                  onChange={(e) => handleQuantityChange(e.target.value)}
                  hint={`≈ ${orderValue.toFixed(2)} USDT`}
                />
                <FormField
                  label={operationType === 'futures' ? 'Margem USDT' : 'Valor em USDT'}
                  type="number"
                  placeholder="0.00"
                  value={marginUsdt}
                  onChange={(e) => handleMarginUsdtChange(e.target.value)}
                  hint={operationType === 'futures' ? `Leverage ${leverage}x` : 'Valor total da ordem'}
                />
              </TabsContent>
            </Tabs>

            {/* Position Size Slider */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Tamanho da Posição</label>
                <div className="flex space-x-2">
                  <Badge variant="outline">{positionSize}%</Badge>
                  {operationType === 'futures' && availableFuturesBalance > 0 && (
                    <Badge variant="secondary">
                      {(availableFuturesBalance * positionSize / 100).toFixed(2)} USDT
                    </Badge>
                  )}
                  {operationType === 'spot' && availableSpotBalance > 0 && (
                    <Badge variant="secondary">
                      {(availableSpotBalance * positionSize / 100).toFixed(2)} USDT
                    </Badge>
                  )}
                </div>
              </div>
              <Slider
                value={[positionSize]}
                onValueChange={(value) => {
                  setPositionSize(value[0])

                  if (operationType === 'futures') {
                    // FUTURES: usar margin
                    if (availableFuturesBalance > 0) {
                      const newMargin = (availableFuturesBalance * value[0] / 100).toFixed(2)
                      setMarginUsdt(newMargin)

                      if (orderPrice) {
                        const newQuantity = (parseFloat(newMargin) * leverage / orderPrice).toFixed(8)
                        setQuantity(newQuantity)
                      }
                    }
                  } else {
                    // SPOT: diferente para BUY e SELL
                    if (orderSide === 'buy') {
                      // BUY: usar % do saldo USDT real
                      const usdtBalance = getAssetBalance(quoteAsset)
                      const newMargin = (usdtBalance * value[0] / 100).toFixed(2)
                      setMarginUsdt(newMargin)

                      if (orderPrice) {
                        const newQuantity = (parseFloat(newMargin) / orderPrice).toFixed(8)
                        setQuantity(newQuantity)
                      }
                    } else {
                      // SELL: usar % do saldo do ativo BASE
                      const baseBalance = getAssetBalance(baseAsset)
                      const newQuantity = (baseBalance * value[0] / 100).toFixed(8)
                      setQuantity(newQuantity)

                      if (orderPrice) {
                        const newMargin = (parseFloat(newQuantity) * orderPrice).toFixed(2)
                        setMarginUsdt(newMargin)
                      }
                    }
                  }
                }}
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

            {/* Leverage - Only for FUTURES */}
            {operationType === 'futures' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Alavancagem</label>
                  <Badge variant="outline">{leverage}x</Badge>
                </div>
                <Slider
                  value={[leverage]}
                  onValueChange={(value) => {
                    setLeverage(value[0])

                    // Recalculate quantity when leverage changes
                    const currentMargin = parseFloat(marginUsdt) || 0
                    if (currentMargin > 0 && orderPrice) {
                      const newQuantity = (currentMargin * value[0] / orderPrice).toFixed(8)
                      setQuantity(newQuantity)
                    }
                  }}
                  max={125}
                  min={1}
                  step={1}
                  className="w-full"
                />
              </div>
            )}

            {/* Risk Management Toggle - Only for FUTURES */}
            {operationType === 'futures' && (
              <>
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="h-4 w-4 text-warning" />
                    <label className="text-sm font-medium">Gerenciamento de Risco</label>
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
                      placeholder="Preço de stop loss"
                      value={stopLoss}
                      onChange={(e) => setStopLoss(e.target.value)}
                    />
                    <FormField
                      label="Take Profit"
                      type="number"
                      placeholder="Preço de take profit"
                      value={takeProfit}
                      onChange={(e) => setTakeProfit(e.target.value)}
                    />
                  </div>
                )}
              </>
            )}

            {/* Risk Meter */}
            <RiskMeter
              riskLevel={riskLevel}
              label="Risco da Ordem"
              size="sm"
              variant="linear"
            />

            {/* Order Summary */}
            <div className="space-y-2 p-3 border rounded-lg bg-muted/30">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">
                  {operationType === 'futures' ? 'Margem:' : 'Valor Total:'}
                </span>
                <span className="font-mono">{orderValue.toFixed(2)} USDT</span>
              </div>
              {operationType === 'futures' && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Tamanho Posição:</span>
                  <span className="font-mono">{(orderValue * leverage).toFixed(2)} USDT</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Taxa Est.:</span>
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
              onClick={() => {
                console.log('🟡 BOTÃO CLICADO!')
                handleSubmit()
              }}
              className={cn(
                "w-full",
                orderSide === 'buy' ? "bg-success hover:bg-success/90" : "bg-destructive hover:bg-destructive/90"
              )}
              disabled={
                isSubmitting ||
                !selectedAccountId ||
                (operationType === 'futures' ? marginUsdtValue <= 0 : orderQuantity <= 0)
              }
            >
              {isSubmitting ? (
                <>
                  <div className="h-4 w-4 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processando...
                </>
              ) : (
                <>
                  <Calculator className="h-4 w-4 mr-2" />
                  {orderSide === 'buy' ? 'Comprar' : 'Vender'} {symbol}
                </>
              )}
            </Button>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export { TradingPanel }
export type { TradingPanelProps, OrderData }