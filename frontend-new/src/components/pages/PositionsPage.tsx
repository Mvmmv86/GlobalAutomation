import React, { useState } from 'react'
import { Wifi } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { formatCurrency, formatDate } from '@/lib/utils'
import { usePositions } from '@/hooks/useApiData'

const PositionsPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')

  // API Data hooks
  const { data: positionsApi, isLoading: loadingPositions, error: positionsError } = usePositions()

  const testApiConnection = async () => {
    setApiStatus('testing')
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/`)
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
  const mockPositions = [
    {
      id: '1',
      symbol: 'BTCUSDT',
      side: 'long',
      status: 'open',
      size: 0.01,
      entryPrice: 45000,
      markPrice: 46000,
      unrealizedPnl: 10.00,
      realizedPnl: 0,
      leverage: 10,
      openedAt: '2025-01-15T08:30:00Z',
    },
    {
      id: '2',
      symbol: 'ETHUSDT',
      side: 'long',
      status: 'open',
      size: 0.1,
      entryPrice: 2800,
      markPrice: 2850,
      unrealizedPnl: 5.00,
      realizedPnl: 0,
      leverage: 5,
      openedAt: '2025-01-15T07:15:00Z',
    },
  ]

  // Use real data when available, fallback to mock data
  const positions = positionsApi || mockPositions

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'open':
        return <Badge variant="success">Aberta</Badge>
      case 'closed':
        return <Badge variant="secondary">Fechada</Badge>
      case 'closing':
        return <Badge variant="warning">Fechando</Badge>
      case 'liquidated':
        return <Badge variant="danger">Liquidada</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const getSideBadge = (side: string) => {
    return (
      <Badge variant={side === 'long' ? 'success' : 'danger'}>
        {side === 'long' ? 'Long' : 'Short'}
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Posições
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Suas posições abertas e fechadas
          </p>
        </div>
        <Button 
          onClick={testApiConnection}
          variant={apiStatus === 'success' ? 'success' : apiStatus === 'error' ? 'danger' : 'outline'}
          disabled={apiStatus === 'testing'}
        >
          <Wifi className="w-4 h-4 mr-2" />
          {apiStatus === 'testing' ? 'Testando...' : 'Testar API'}
        </Button>
      </div>

      {/* API Error Banner */}
      {positionsError && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <p className="text-yellow-800 dark:text-yellow-200 text-sm">
            ⚠️ API indisponível - usando dados demo
          </p>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Posições Abertas</CardTitle>
          <CardDescription>
            Todas as suas posições em aberto
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingPositions ? (
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
                    Tamanho
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Preço de Entrada
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Preço Atual
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    P&L Não Realizado
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Alavancagem
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Aberta em
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {positions.map((position) => (
                  <tr key={position.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {position.symbol}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getSideBadge(position.side)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {position.size}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatCurrency(position.entryPrice)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {position.markPrice ? formatCurrency(position.markPrice) : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={position.unrealizedPnl >= 0 ? 'text-success' : 'text-danger'}>
                        {position.unrealizedPnl >= 0 ? '+' : ''}{formatCurrency(position.unrealizedPnl)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {position.leverage}x
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(position.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatDate(position.openedAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default PositionsPage