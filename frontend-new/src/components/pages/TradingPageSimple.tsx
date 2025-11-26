import React, { useState } from 'react'
import { TrendingUp, BarChart3, Bell } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { TradingPanel, OrderData } from '../organisms/TradingPanel'
import { PositionsTable, Position } from '../organisms/PositionsTable'
import { ChartContainer } from '../organisms/ChartContainer'
import { NotificationCenter, useNotifications } from '../organisms/NotificationCenter'
import { useExchangeAccounts, useActivePositions } from '@/hooks/useApiData'

const TradingPageSimple: React.FC = () => {
  const [showNotifications, setShowNotifications] = useState(false)

  // Testar hooks de API
  const { data: exchangeAccounts = [], isLoading: loadingAccounts } = useExchangeAccounts()
  const { data: positions = [], isLoading: loadingPositions } = useActivePositions()

  // Test notifications hook
  const {
    notifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll
  } = useNotifications()

  // Mock current price
  const currentPrice = 45234.56
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT')

  const handleOrderSubmit = (orderData: OrderData) => {
    console.log('Order submitted:', orderData)

    // Add notification
    addNotification({
      type: 'success',
      title: 'Order Submitted',
      message: `${orderData.side.toUpperCase()} order for ${orderData.quantity} ${orderData.symbol} has been submitted successfully.`,
      category: 'order'
    })
  }

  const handleClosePosition = (positionId: string) => {
    console.log('Closing position:', positionId)

    addNotification({
      type: 'info',
      title: 'Position Closing',
      message: `Position ${positionId} is being closed.`,
      category: 'position'
    })
  }

  const handleModifyPosition = (positionId: string, data: { stopLoss?: number; takeProfit?: number }) => {
    console.log('Modifying position:', positionId, data)

    addNotification({
      type: 'success',
      title: 'Position Modified',
      message: `Position ${positionId} has been updated with new stop loss and take profit levels.`,
      category: 'position'
    })
  }

  return (
    <div className="min-h-screen bg-background p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-3xl font-bold">Trading</h1>
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-success" />
            <span className="text-lg font-semibold">BTCUSDT</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative"
          >
            <Bell className="h-4 w-4 mr-2" />
            Notificações
          </Button>
        </div>
      </div>

      {/* Test Content */}
      <Card>
        <CardHeader>
          <CardTitle>Teste - Header funcionando</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Se você está vendo isto, os componentes básicos funcionam.</p>
          <p>Testando hooks de API:</p>
          <ul className="list-disc pl-6 space-y-1">
            <li>Contas: {loadingAccounts ? 'Carregando...' : `${exchangeAccounts.length} contas`}</li>
            <li>Posições: {loadingPositions ? 'Carregando...' : `${positions.length} posições ativas`}</li>
          </ul>
        </CardContent>
      </Card>

      {/* TradingPanel Test */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <div className="xl:col-span-3">
          <ChartContainer
            symbol={selectedSymbol}
            height={500}
            onSymbolChange={setSelectedSymbol}
          />

          {/* Positions Table - TEMPORARIAMENTE DESABILITADO - CAUSANDO CRASH */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Posições (Temporariamente Desabilitado)</CardTitle>
            </CardHeader>
            <CardContent>
              <p>PositionsTable está causando crash. Será investigado separadamente.</p>
              <p>Posições carregadas: {positions.length}</p>
            </CardContent>
          </Card>
        </div>

        <div>
          <TradingPanel
            symbol="BTCUSDT"
            currentPrice={currentPrice}
            accounts={exchangeAccounts}
            onOrderSubmit={handleOrderSubmit}
          />
        </div>
      </div>
    </div>
  )
}

export default TradingPageSimple