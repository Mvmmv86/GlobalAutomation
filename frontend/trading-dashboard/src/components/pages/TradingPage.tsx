import React, { useState } from 'react'
import { TrendingUp, BarChart3, Bell } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { TradingPanel, OrderData } from '../organisms/TradingPanel'
import { PositionsTable, Position } from '../organisms/PositionsTable'
import { ChartContainer } from '../organisms/ChartContainer'
import { NotificationCenter, useNotifications } from '../organisms/NotificationCenter'
import { useExchangeAccounts, useActivePositions } from '@/hooks/useApiData'

const TradingPage: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT')
  const [showNotifications, setShowNotifications] = useState(false)
  
  // API hooks
  const { data: exchangeAccounts = [] } = useExchangeAccounts()
  const { data: positions = [] } = useActivePositions()
  
  // Notifications hook
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

  // Mock positions data for demo
  const mockPositions: Position[] = [
    {
      id: '1',
      symbol: 'BTCUSDT',
      side: 'long',
      status: 'open',
      size: 0.1,
      entryPrice: 44500,
      markPrice: 45234.56,
      unrealizedPnl: 73.46,
      realizedPnl: 0,
      percentage: 1.65,
      leverage: 10,
      liquidationPrice: 40050,
      openedAt: '2025-01-15T10:30:00Z',
      exchange: 'binance',
      margin: 445,
      fees: 4.45
    },
    {
      id: '2',
      symbol: 'ETHUSDT',
      side: 'short',
      status: 'open',
      size: 2.5,
      entryPrice: 2850,
      markPrice: 2835,
      unrealizedPnl: 37.5,
      realizedPnl: 0,
      percentage: 0.53,
      leverage: 5,
      liquidationPrice: 3135,
      openedAt: '2025-01-15T14:20:00Z',
      exchange: 'bybit',
      margin: 1425,
      fees: 7.125
    }
  ]

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
            <span className="text-lg font-semibold">{selectedSymbol}</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative"
          >
            <Bell className="h-4 w-4 mr-2" />
            Notifications
            {notifications.filter(n => !n.read).length > 0 && (
              <div className="absolute -top-1 -right-1 h-3 w-3 bg-destructive rounded-full" />
            )}
          </Button>
        </div>
      </div>

      {/* Main Trading Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Left Column - Chart */}
        <div className="xl:col-span-3 space-y-6">
          {/* Chart */}
          <ChartContainer
            symbol={selectedSymbol}
            height={500}
            onSymbolChange={setSelectedSymbol}
          />

          {/* Positions Table */}
          <PositionsTable
            positions={mockPositions}
            onClosePosition={handleClosePosition}
            onModifyPosition={handleModifyPosition}
          />
        </div>

        {/* Right Column - Trading Panel */}
        <div className="space-y-6">
          <TradingPanel
            symbol={selectedSymbol}
            currentPrice={currentPrice}
            accounts={exchangeAccounts}
            onOrderSubmit={handleOrderSubmit}
          />

          {/* Market Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="h-5 w-5" />
                <span>Market Summary</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground">24h Volume</div>
                  <div className="font-semibold">1.23M BTC</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">24h High</div>
                  <div className="font-semibold text-success">45,890</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">24h Low</div>
                  <div className="font-semibold text-destructive">44,120</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Market Cap</div>
                  <div className="font-semibold">895.2B</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start">
                Close All Positions
              </Button>
              <Button variant="outline" className="w-full justify-start">
                Cancel All Orders
              </Button>
              <Button variant="outline" className="w-full justify-start">
                Export Trade History
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Notification Center Overlay */}
      {showNotifications && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl">
            <NotificationCenter
              notifications={notifications}
              onMarkAsRead={markAsRead}
              onMarkAllAsRead={markAllAsRead}
              onDeleteNotification={deleteNotification}
              onClearAll={clearAll}
            />
            <div className="flex justify-center mt-4">
              <Button onClick={() => setShowNotifications(false)}>
                Close Notifications
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TradingPage