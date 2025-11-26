import React, { useState, useEffect, useCallback } from 'react'
import { TrendingUp, Bell } from 'lucide-react'
import { Card } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { TradingPanel, OrderData } from '../organisms/TradingPanel'
import { ChartContainer } from '../organisms/ChartContainer'
import { NotificationCenter } from '../organisms/NotificationCenter'
import { useExchangeAccounts, useActivePositions, useClosedPositions, useSpotBalances } from '@/hooks/useApiData'
import { PositionsCard } from '../organisms/PositionsCard'
import { useRealTimePrice } from '@/hooks/useRealTimePrice'
import { OrderCreationModal, OrderFormData } from '../molecules/OrderCreationModal'
import { OrderConfirmationModal } from '../molecules/OrderConfirmationModal'
import { ClosePositionModal } from '../molecules/ClosePositionModal'
import { EditPositionModal } from '../molecules/EditPositionModal'
import { useCreateOrder, useClosePosition, useModifyOrder } from '@/hooks/useOrderActions'
import { usePositionsWebSocket } from '@/hooks/usePositionsWebSocket'

const TradingPage: React.FC = () => {
  // API hooks - buscar contas primeiro
  const { data: exchangeAccounts = [] } = useExchangeAccounts()

  // Recuperar estado salvo do localStorage
  const [selectedSymbol, setSelectedSymbol] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('trading-symbol') || 'BTCUSDT'
    }
    return 'BTCUSDT'
  })
  const [showNotifications, setShowNotifications] = useState(false)
  const [selectedAccount, setSelectedAccount] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const savedAccount = localStorage.getItem('trading-account')
      if (savedAccount) return savedAccount
    }
    return '' // Será definido pelo useEffect após carregar contas
  })

  // Salvar estados no localStorage quando mudarem
  useEffect(() => {
    localStorage.setItem('trading-symbol', selectedSymbol)
  }, [selectedSymbol])

  useEffect(() => {
    if (selectedAccount) {
      localStorage.setItem('trading-account', selectedAccount)
    }
  }, [selectedAccount])

  // Auto-selecionar conta principal quando contas carregarem
  useEffect(() => {
    if (!selectedAccount && exchangeAccounts.length > 0) {
      // Buscar conta principal (is_main = true)
      const mainAccount = exchangeAccounts.find(acc => acc.isMain)
      // Fallback: primeira conta ativa se não tiver main
      const defaultAccount = mainAccount || exchangeAccounts[0]

      if (defaultAccount?.id) {
        console.log('🏦 Auto-selecionando conta principal:', defaultAccount.name)
        setSelectedAccount(defaultAccount.id)
      }
    }
  }, [exchangeAccounts, selectedAccount])

  // Posições FUTURES filtradas por conta selecionada
  const {
    data: openPositions = [],
    isLoading: isLoadingOpen
  } = useActivePositions({
    ...(selectedAccount && { exchangeAccountId: selectedAccount }),
    operationType: 'futures' // Apenas FUTURES
  })

  const {
    data: closedPositions = [],
    isLoading: isLoadingClosed
  } = useClosedPositions({
    ...(selectedAccount && { exchangeAccountId: selectedAccount }),
    operationType: 'futures', // Apenas FUTURES
    // Últimos 30 dias
    dateFrom: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  })

  // Saldos SPOT (ativos em carteira)
  const {
    data: spotBalances,
    isLoading: isLoadingSpot
  } = useSpotBalances(selectedAccount)

  const isLoadingPositions = selectedAccount && (isLoadingOpen || isLoadingClosed || isLoadingSpot)
  
  // Notification helper - logs to console for now (real notifications go to backend)
  const addNotification = useCallback((notification: { type: string; title: string; message: string; category?: string }) => {
    console.log('📢 Notification:', notification)
  }, [])

  // WebSocket para preço em tempo real do símbolo selecionado
  const { priceData, isConnected: isPriceConnected } = useRealTimePrice(selectedSymbol)
  const currentPrice = priceData?.price || 0

  // WebSocket para notificações de posições/ordens (FASE 2)
  // TODO: Substituir 'mock-user-id' pelo user_id real do contexto de autenticação
  const {
    isConnected: isWsConnected,
    connectionError: wsError
  } = usePositionsWebSocket({
    userId: 'mock-user-id', // TODO: Pegar do contexto de auth
    enabled: true,
    onOrderUpdate: (data) => {
      console.log('📦 Order update received:', data)
      // Adicionar notificação visual
      addNotification({
        type: 'success',
        title: 'Ordem Atualizada',
        message: `Ordem ${data.symbol} ${data.side.toUpperCase()} ${data.status}`,
        category: 'order'
      })
    },
    onPositionUpdate: (data) => {
      console.log('📊 Position update received:', data)
      // Adicionar notificação visual
      addNotification({
        type: 'info',
        title: 'Posição Atualizada',
        message: `Posição ${data.symbol} ${data.action}`,
        category: 'position'
      })
    }
  })

  // Order modals state
  const [isOrderCreationModalOpen, setIsOrderCreationModalOpen] = useState(false)
  const [isOrderConfirmationModalOpen, setIsOrderConfirmationModalOpen] = useState(false)
  const [pendingOrderData, setPendingOrderData] = useState<OrderFormData | null>(null)
  const [clickedPrice, setClickedPrice] = useState<number | undefined>(undefined)

  // Position modals state
  const [isClosePositionModalOpen, setIsClosePositionModalOpen] = useState(false)
  const [isEditPositionModalOpen, setIsEditPositionModalOpen] = useState(false)
  const [selectedPositionId, setSelectedPositionId] = useState<string | null>(null)

  // Order mutations
  const createOrderMutation = useCreateOrder()
  const modifyOrderMutation = useModifyOrder()
  const closePositionMutation = useClosePosition()

  // Success modal state
  const [showSuccessModal, setShowSuccessModal] = useState(false)
  const [successOrderData, setSuccessOrderData] = useState<any>(null)

  const handleOrderSubmit = async (orderData: OrderData) => {
    console.log('🔵 Order submitted:', orderData)

    try {
      // Preparar payload para a API
      const payload = {
        accountId: orderData.accountId,
        symbol: orderData.symbol,
        side: orderData.side,
        orderType: orderData.type,
        operationType: orderData.operationType,
        quantity: orderData.quantity,
        ...(orderData.price && { price: orderData.price }),
        ...(orderData.stopPrice && { stopPrice: orderData.stopPrice }),
        ...(orderData.leverage && orderData.leverage > 1 && { leverage: orderData.leverage }),
        ...(orderData.stopLoss && { stopLoss: orderData.stopLoss }),
        ...(orderData.takeProfit && { takeProfit: orderData.takeProfit })
      }

      console.log('🔵 Sending to API:', payload)

      const result = await createOrderMutation.mutateAsync(payload)

      console.log('✅ Order result:', result)
      console.log('📊 Result data:', result.data)
      console.log('🆔 Exchange order ID:', result.data?.exchange_order_id)
      console.log('🔍 Full result object:', JSON.stringify(result, null, 2))

      // Show success modal
      const modalData = {
        ...orderData,
        orderId: result.data?.exchange_order_id
      }
      console.log('🎨 Setting modal data:', modalData)

      setSuccessOrderData(modalData)
      setShowSuccessModal(true)

      console.log('🎯 Modal state set to TRUE - should appear now!')

      // Auto-hide after 3 seconds
      setTimeout(() => {
        console.log('⏱️ Hiding modal after 3s')
        setShowSuccessModal(false)
      }, 3000)

      addNotification({
        type: 'success',
        title: 'Ordem Executada',
        message: `Ordem ${orderData.side.toUpperCase()} de ${orderData.quantity} ${orderData.symbol} executada com sucesso!`,
        category: 'order'
      })
    } catch (error) {
      console.error('❌ Erro ao executar ordem:', error)
      addNotification({
        type: 'error',
        title: 'Erro ao Executar Ordem',
        message: error instanceof Error ? error.message : 'Erro desconhecido ao executar ordem',
        category: 'order'
      })
    }
  }

  // Handle chart click to create order - Memoized to prevent re-renders
  const handleChartClick = useCallback((price: number) => {
    setClickedPrice(price)
    setIsOrderCreationModalOpen(true)
  }, [])

  // Handle order creation confirmation
  const handleOrderCreation = (orderData: OrderFormData) => {
    setPendingOrderData(orderData)
    setIsOrderCreationModalOpen(false)
    setIsOrderConfirmationModalOpen(true)
  }

  // Handle final order confirmation
  const handleOrderConfirmation = async () => {
    if (!pendingOrderData) return

    try {
      const result = await createOrderMutation.mutateAsync(pendingOrderData)

      if (result.success) {
        addNotification({
          type: 'success',
          title: 'Ordem Criada',
          message: `Ordem de ${pendingOrderData.side === 'buy' ? 'COMPRA' : 'VENDA'} para ${pendingOrderData.symbol} criada com sucesso!`,
          category: 'order'
        })
      }

      setIsOrderConfirmationModalOpen(false)
      setPendingOrderData(null)
      setClickedPrice(undefined)
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Erro ao Criar Ordem',
        message: error instanceof Error ? error.message : 'Erro desconhecido',
        category: 'order'
      })
    }
  }

  // Handle order cancellation
  const handleOrderCancel = () => {
    setIsOrderConfirmationModalOpen(false)
    setIsOrderCreationModalOpen(false)
    setPendingOrderData(null)
    setClickedPrice(undefined)
  }

  // Handle position close from chart - Memoized to prevent re-renders
  const handleChartPositionClose = useCallback((positionId: string) => {
    setSelectedPositionId(positionId)
    setIsClosePositionModalOpen(true)
  }, [])

  // Handle position edit from chart - Memoized to prevent re-renders
  const handleChartPositionEdit = useCallback((positionId: string) => {
    setSelectedPositionId(positionId)
    setIsEditPositionModalOpen(true)
  }, [])

  const handleClosePosition = async (positionId: string, percentage: number = 100) => {
    console.log('🔄 Closing position:', positionId, `${percentage}%`)

    const closeType = percentage === 100 ? 'completamente' : `parcialmente (${percentage}%)`

    try {
      await closePositionMutation.mutateAsync({
        positionId,
        percentage
      })

      addNotification({
        type: 'success',
        title: 'Posição Fechada',
        message: `Posição fechada ${closeType} com sucesso!`,
        category: 'position'
      })
    } catch (error) {
      console.error('❌ Erro ao fechar posição:', error)
      addNotification({
        type: 'error',
        title: 'Erro ao Fechar Posição',
        message: error instanceof Error ? error.message : 'Erro desconhecido ao fechar posição',
        category: 'position'
      })
    }
  }

  const handleModifyPosition = async (positionId: string, data: { stopLoss?: number; takeProfit?: number }) => {
    console.log('🔧 Modificando posição:', positionId, data)

    try {
      // Chamar API para modificar SL/TP
      await modifyOrderMutation.mutateAsync({
        orderId: positionId,
        stopLoss: data.stopLoss,
        takeProfit: data.takeProfit
      })

      addNotification({
        type: 'success',
        title: 'Posição Modificada',
        message: `SL/TP atualizados: ${data.stopLoss ? `SL=${data.stopLoss.toFixed(2)}` : ''} ${data.takeProfit ? `TP=${data.takeProfit.toFixed(2)}` : ''}`,
        category: 'position'
      })
    } catch (error) {
      console.error('❌ Erro ao modificar posição:', error)
      addNotification({
        type: 'error',
        title: 'Erro ao Modificar',
        message: error instanceof Error ? error.message : 'Erro desconhecido',
        category: 'position'
      })
    }
  }

  return (
    <div className="h-full overflow-hidden flex flex-col pl-2.5">
      {/* Header - Ultra compacto */}
      <div className="flex items-center justify-between h-10 pr-2 border-b">
        <div className="flex items-center space-x-2">
          <h1 className="text-lg font-bold">Trading</h1>
          <div className="flex items-center space-x-2">
            <div className="flex items-center space-x-1">
              <TrendingUp className="h-3 w-3 text-success" />
              <span className="text-sm font-semibold">{selectedSymbol}</span>
            </div>
            {currentPrice > 0 && (
              <div className="flex items-center space-x-1">
                <span className="text-xs text-muted-foreground">$</span>
                <span className={`text-sm font-bold ${isPriceConnected ? 'text-primary' : 'text-muted-foreground'}`}>
                  {currentPrice.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 4
                  })}
                </span>
                {isPriceConnected && (
                  <span className="h-1 w-1 bg-green-500 rounded-full animate-pulse" title="Real-time price" />
                )}
              </div>
            )}
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowNotifications(!showNotifications)}
          className="relative h-7 px-2"
        >
          <Bell className="h-3 w-3" />
        </Button>
      </div>

      {/* Main Trading Layout - Com 1cm (10px) de espaço da navbar */}
      <div className="flex-1 flex overflow-hidden pr-2.5 gap-2.5">
        {/* Left Section - Chart Máximo */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {/* Chart - Ocupando tudo com overflow-hidden para conter indicadores */}
          <div className="flex-1 py-2.5 min-h-0 overflow-hidden">
            <ChartContainer
              symbol={selectedSymbol}
              height="100%"
              onSymbolChange={(newSymbol) => {
                console.log('📈 TradingPage: Symbol changing to', newSymbol)
                setSelectedSymbol(newSymbol)
              }}
              className="h-full"
              exchangeAccountId={selectedAccount}
              onPositionAction={(positionId, action, data) => {
                if (action === 'close') {
                  handleClosePosition(positionId, data?.percentage || 100)
                } else if (action === 'modify') {
                  handleModifyPosition(positionId, data)
                }
              }}
              onChartClick={handleChartClick}
              onPositionClose={handleChartPositionClose}
              onPositionEdit={handleChartPositionEdit}
            />
          </div>

          {/* Positions Card com Abas (FUTURES/SPOT) - altura fixa, não encolhe */}
          <div className="h-48 pb-2.5 flex-shrink-0">
            <PositionsCard
              openPositions={openPositions}
              closedPositions={closedPositions}
              spotBalances={spotBalances?.assets || []}
              onClosePosition={handleClosePosition}
              onModifyPosition={handleModifyPosition}
              selectedAccountId={selectedAccount}
              isLoading={isLoadingPositions}
            />
          </div>
        </div>

        {/* Right Section - Trading Panel */}
        <div className="w-72 border-l overflow-y-auto">
          <TradingPanel
            symbol={selectedSymbol}
            currentPrice={currentPrice}
            accounts={exchangeAccounts}
            selectedAccountId={selectedAccount}
            onAccountChange={setSelectedAccount}
            onOrderSubmit={handleOrderSubmit}
            isSubmitting={createOrderMutation.isPending}
            className="h-full"
          />
        </div>
      </div>

      {/* Success Modal */}
      {showSuccessModal && successOrderData && (() => {
        console.log('🎨 Rendering success modal:', { showSuccessModal, successOrderData })
        return (
          <div className="fixed top-0 left-0 right-0 bottom-0 z-[9999] flex items-center justify-center pointer-events-none">
            <div className="bg-success text-white px-8 py-6 rounded-xl shadow-2xl border-2 border-white/20 pointer-events-auto max-w-md mx-4">
              <div className="flex items-center space-x-4">
                <div className="h-12 w-12 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="h-7 w-7" />
                </div>
                <div className="flex-1">
                  <div className="font-bold text-xl mb-1">Ordem Executada!</div>
                  <div className="text-sm opacity-90">
                    <span className="font-semibold">{successOrderData.side.toUpperCase()}</span> {successOrderData.quantity} {successOrderData.symbol}
                    {successOrderData.orderId && (
                      <div className="text-xs mt-1 opacity-75 font-mono">ID: {successOrderData.orderId}</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Notification Center Overlay */}
      {showNotifications && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl">
            <NotificationCenter />
            <div className="flex justify-center mt-4">
              <Button onClick={() => setShowNotifications(false)}>
                Close Notifications
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Order Creation Modal */}
      <OrderCreationModal
        isOpen={isOrderCreationModalOpen}
        onClose={handleOrderCancel}
        symbol={selectedSymbol}
        initialPrice={clickedPrice || currentPrice}
        accounts={exchangeAccounts.map(acc => ({
          id: acc.id,
          name: acc.name,
          exchange: acc.exchange
        }))}
        selectedAccountId={selectedAccount}
        onConfirm={handleOrderCreation}
      />

      {/* Order Confirmation Modal */}
      {pendingOrderData && (
        <OrderConfirmationModal
          isOpen={isOrderConfirmationModalOpen}
          onClose={handleOrderCancel}
          onConfirm={handleOrderConfirmation}
          orderData={pendingOrderData}
          currentPrice={currentPrice}
          isSubmitting={createOrderMutation.isPending}
        />
      )}

      {/* Close Position Modal */}
      {selectedPositionId && openPositions.find(p => p.id === selectedPositionId) && (() => {
        const pos = openPositions.find(p => p.id === selectedPositionId)!
        return (
          <ClosePositionModal
            isOpen={isClosePositionModalOpen}
            onClose={() => {
              setIsClosePositionModalOpen(false)
              setSelectedPositionId(null)
            }}
            position={{
              id: pos.id,
              symbol: pos.symbol,
              side: pos.side === 'LONG' ? 'LONG' : 'SHORT',
              quantity: pos.size || 0,
              entryPrice: pos.entryPrice,
              markPrice: pos.markPrice,
              unrealizedPnl: pos.unrealizedPnl
            }}
            onClosePosition={handleClosePosition}
          />
        )
      })()}

      {/* Edit Position Modal */}
      {selectedPositionId && openPositions.find(p => p.id === selectedPositionId) && (() => {
        const pos = openPositions.find(p => p.id === selectedPositionId)!
        return (
          <EditPositionModal
            isOpen={isEditPositionModalOpen}
            onClose={() => {
              setIsEditPositionModalOpen(false)
              setSelectedPositionId(null)
            }}
            position={{
              id: pos.id,
              symbol: pos.symbol,
              side: pos.side === 'LONG' ? 'LONG' : 'SHORT',
              quantity: pos.size || 0,
              entryPrice: pos.entryPrice,
              markPrice: pos.markPrice,
              unrealizedPnl: pos.unrealizedPnl,
              stopLoss: undefined,
              takeProfit: undefined
            }}
            onSave={handleModifyPosition}
          />
        )
      })()}
    </div>
  )
}

export default TradingPage