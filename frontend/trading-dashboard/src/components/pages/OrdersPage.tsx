import React, { useState } from 'react'
import { Wifi } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import { useOrders } from '@/hooks/useApiData'
import { useQueryClient } from '@tanstack/react-query'

const OrdersPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const queryClient = useQueryClient()

  // API Data hooks
  const { data: ordersApi, isLoading: loadingOrders, error: ordersError } = useOrders()
  
  // Debug logs
  console.log('📋 OrdersPage: ordersApi:', ordersApi)
  console.log('📋 OrdersPage: loadingOrders:', loadingOrders)
  console.log('📋 OrdersPage: ordersError:', ordersError)
  
  const refreshOrders = () => {
    console.log('🔄 Refreshing orders...')
    queryClient.invalidateQueries({ queryKey: ['orders'] })
  }

  const testApiConnection = async () => {
    setApiStatus('testing')
    try {
      const response = await fetch('/api/v1/../')  // Usar proxy do Vite
      if (response.ok) {
        setApiStatus('success')
      } else {
        setApiStatus('error')
      }
    } catch (error) {
      setApiStatus('error')
    }
  }

  // Mock data for fallback
  const mockOrders = [
    {
      id: '1',
      clientOrderId: 'order_001',
      symbol: 'BTCUSDT',
      side: 'buy',
      type: 'limit',
      status: 'filled',
      quantity: 0.01,
      price: 45000,
      filledQuantity: 0.01,
      averageFillPrice: 45000,
      feesPaid: 0.45,
      createdAt: '2025-01-15T10:30:00Z',
    },
    {
      id: '2',
      clientOrderId: 'order_002',
      symbol: 'ETHUSDT',
      side: 'sell',
      type: 'market',
      status: 'open',
      quantity: 0.5,
      price: null,
      filledQuantity: 0,
      averageFillPrice: null,
      feesPaid: 0,
      createdAt: '2025-01-15T09:15:00Z',
    },
  ]

  // Use real data when available, fallback to mock data
  const orders = ordersApi || mockOrders

  const getStatusBadge = (status: string) => {
    const normalizedStatus = status?.toLowerCase()
    switch (normalizedStatus) {
      case 'filled':
        return <Badge variant="success">Preenchida</Badge>
      case 'open':
      case 'pending':
        return <Badge variant="warning">Aberta</Badge>
      case 'partially_filled':
        return <Badge variant="secondary">Parcial</Badge>
      case 'canceled':
      case 'cancelled':
        return <Badge variant="secondary">Cancelada</Badge>
      case 'rejected':
      case 'failed':
        return <Badge variant="danger">Rejeitada</Badge>
      default:
        return <Badge variant="outline">{normalizedStatus || 'Desconhecido'}</Badge>
    }
  }

  const getSideBadge = (side: string) => {
    return (
      <Badge variant={side === 'buy' ? 'success' : 'danger'}>
        {side === 'buy' ? 'Compra' : 'Venda'}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Ordens
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Histórico de todas as suas ordens
          </p>
        </div>
        <div className="flex space-x-2">
          <Button 
            onClick={refreshOrders}
            variant="outline"
          >
            🔄 Atualizar Ordens
          </Button>
          <Button 
            onClick={testApiConnection}
            variant={apiStatus === 'success' ? 'success' : apiStatus === 'error' ? 'danger' : 'outline'}
            disabled={apiStatus === 'testing'}
          >
            <Wifi className="w-4 h-4 mr-2" />
            {apiStatus === 'testing' ? 'Testando...' : 'Testar API'}
          </Button>
        </div>
      </div>

      {/* API Error Banner */}
      {ordersError && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <p className="text-yellow-800 dark:text-yellow-200 text-sm">
            ⚠️ API indisponível - usando dados demo
          </p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Histórico de Ordens</CardTitle>
          <CardDescription>
            Todas as ordens executadas pela plataforma
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingOrders ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Símbolo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Lado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Quantidade
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Preço
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Data
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {orders && orders.length > 0 ? orders.map((order) => (
                  <tr key={order.id || Math.random()}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {order.symbol || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getSideBadge(order.side || 'unknown')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 capitalize">
                      {order.type || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {order.quantity || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {order.price ? formatCurrency(order.price) : 'Market'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(order.status || 'unknown')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {order.createdAt ? formatDate(order.createdAt) : 'N/A'}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                      {loadingOrders ? 'Carregando ordens...' : 'Nenhuma ordem encontrada'}
                    </td>
                  </tr>
                )}
              </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default OrdersPage