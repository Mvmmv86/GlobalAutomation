import React, { useState } from 'react'
import { Wifi, Calendar, Filter } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { Input } from '../atoms/Input'
import { Select } from '../atoms/Select'
import { formatCurrency, formatDate } from '@/lib/utils'
import { useOrders, useExchangeAccounts } from '@/hooks/useApiData'
import { useQueryClient } from '@tanstack/react-query'

const OrdersPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const queryClient = useQueryClient()

  // Filtros
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [selectedExchange, setSelectedExchange] = useState<string>('all')

  // API Data hooks - usar filtros
  const { data: ordersApi, isLoading: loadingOrders, error: ordersError } = useOrders({
    exchangeAccountId: selectedExchange,
    dateFrom: dateFrom,
    dateTo: dateTo,
  })
  const { data: exchangeAccounts, isLoading: loadingAccounts } = useExchangeAccounts()
  
  // Debug logs
  console.log('📋 OrdersPage: ordersApi:', ordersApi)
  console.log('📋 OrdersPage: loadingOrders:', loadingOrders)
  console.log('📋 OrdersPage: ordersError:', ordersError)
  console.log('🏦 OrdersPage: exchangeAccounts:', exchangeAccounts)
  console.log('🔍 OrdersPage: Filtros aplicados:', { dateFrom, dateTo, selectedExchange })
  
  const refreshOrders = () => {
    console.log('🔄 Refreshing orders...')
    queryClient.invalidateQueries({ queryKey: ['orders'] })
  }

  const applyFilters = () => {
    console.log('🔍 Aplicando filtros:', {
      dateFrom,
      dateTo,
      selectedExchange
    })
    // Os filtros são aplicados automaticamente via hook
    // Apenas invalidamos o cache para forçar uma nova busca
    queryClient.invalidateQueries({ queryKey: ['orders'] })
  }

  const clearFilters = () => {
    setDateFrom('')
    setDateTo('')
    setSelectedExchange('all')
    refreshOrders()
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

  // Mock data for fallback - estrutura completa para demonstração
  const mockOrders = [
    {
      id: '1',
      clientOrderId: 'BTC_BUY_001_12345678',
      symbol: 'BTCUSDT',
      side: 'buy',
      type: 'limit',
      status: 'filled',
      quantity: 0.01,
      price: 45000,
      filledQuantity: 0.01,
      averageFillPrice: 45000,
      feesPaid: 0.45,
      feeCurrency: 'USDT',
      exchange: 'Binance',
      exchangeAccountId: 'binance_001',
      source: 'webhook',
      createdAt: '2025-01-15T10:30:00Z',
    },
    {
      id: '2',
      clientOrderId: 'ETH_SELL_002_87654321',
      symbol: 'ETHUSDT',
      side: 'sell',
      type: 'market',
      status: 'filled',
      quantity: 0.5,
      price: null,
      filledQuantity: 0.5,
      averageFillPrice: 3200,
      feesPaid: 1.6,
      feeCurrency: 'USDT',
      exchange: 'Binance',
      exchangeAccountId: 'binance_001',
      source: 'manual',
      createdAt: '2025-01-15T09:15:00Z',
    },
    {
      id: '3',
      clientOrderId: 'SOL_BUY_003_11223344',
      symbol: 'SOLUSDT',
      side: 'buy',
      type: 'limit',
      status: 'partially_filled',
      quantity: 5.0,
      price: 120,
      filledQuantity: 2.5,
      averageFillPrice: 119.8,
      feesPaid: 0.3,
      feeCurrency: 'USDT',
      exchange: 'Bybit',
      exchangeAccountId: 'bybit_001',
      source: 'webhook',
      createdAt: '2025-01-14T16:45:00Z',
    },
    {
      id: '4',
      clientOrderId: 'ADA_BUY_004_99887766',
      symbol: 'ADAUSDT',
      side: 'buy',
      type: 'stop',
      status: 'cancelled',
      quantity: 100,
      price: 0.45,
      filledQuantity: 0,
      averageFillPrice: null,
      feesPaid: 0,
      feeCurrency: 'USDT',
      exchange: 'Binance',
      exchangeAccountId: 'binance_002',
      source: 'manual',
      createdAt: '2025-01-14T14:20:00Z',
    }
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

      {/* Filtros */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filtros de Busca
          </CardTitle>
          <CardDescription>
            Filtre as ordens por data e conta de exchange
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Filtro Data Início */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Data de Início</label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                placeholder="Data inicial"
              />
            </div>

            {/* Filtro Data Fim */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Data de Fim</label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                placeholder="Data final"
              />
            </div>

            {/* Filtro Exchange */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Conta de Exchange</label>
              <Select
                value={selectedExchange}
                onChange={(e) => setSelectedExchange(e.target.value)}
                disabled={loadingAccounts}
              >
                <option value="all">Todas as contas</option>
                {exchangeAccounts?.map((account: any) => (
                  <option key={account.id} value={account.id}>
                    {account.exchange} - {account.label || account.name}
                  </option>
                ))}
              </Select>
            </div>

            {/* Botões */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Ações</label>
              <div className="flex gap-2">
                <Button
                  onClick={applyFilters}
                  variant="default"
                  className="flex-1"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Filtrar
                </Button>
                <Button
                  onClick={clearFilters}
                  variant="outline"
                  className="flex-1"
                >
                  Limpar
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

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
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Exchange
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Símbolo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Lado
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Quantidade
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Preço
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Executado
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Taxa
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Data
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {orders && orders.length > 0 ? orders.map((order) => (
                  <tr key={order.id || Math.random()} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    {/* Exchange */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      <div className="flex items-center">
                        <Badge variant="outline" className="text-xs">
                          {order.exchange || 'Binance'}
                        </Badge>
                      </div>
                    </td>

                    {/* Símbolo */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {order.symbol || 'N/A'}
                    </td>

                    {/* Lado */}
                    <td className="px-4 py-4 whitespace-nowrap">
                      {getSideBadge(order.side || 'unknown')}
                    </td>

                    {/* Tipo */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400 capitalize">
                      {order.type || 'N/A'}
                    </td>

                    {/* Quantidade */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {order.quantity || 0}
                    </td>

                    {/* Preço */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {order.price ? formatCurrency(order.price) : 'Market'}
                    </td>

                    {/* Executado */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex flex-col">
                        <span>{order.filledQuantity || 0}</span>
                        {order.averageFillPrice && (
                          <span className="text-xs text-gray-400">
                            @ {formatCurrency(order.averageFillPrice)}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Taxa */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex flex-col">
                        <span>{formatCurrency(order.feesPaid || 0)}</span>
                        {order.feeCurrency && (
                          <span className="text-xs text-gray-400">{order.feeCurrency}</span>
                        )}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-4 py-4 whitespace-nowrap">
                      {getStatusBadge(order.status || 'unknown')}
                    </td>

                    {/* Data */}
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex flex-col">
                        <span>{order.createdAt ? formatDate(order.createdAt) : 'N/A'}</span>
                        {order.clientOrderId && (
                          <span className="text-xs text-gray-400">
                            ID: {order.clientOrderId.slice(-8)}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={10} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
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