import React, { useState } from 'react'
import { RefreshCw, Download, CheckCircle, XCircle, AlertCircle, Activity, DollarSign, TrendingUp, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { useExchangeAccounts } from '@/hooks/useApiData'

interface SyncResult {
  success: boolean
  message: string
  synced_count?: number
  total_orders?: number
  total_trades?: number
  total_positions?: number
  balances?: any[]
  errors?: string[]
  demo?: boolean
}

interface FullSyncResult {
  success: boolean
  message: string
  results: {
    orders: SyncResult
    balances: SyncResult
    positions: SyncResult
  }
}

const SyncPage: React.FC = () => {
  const { data: exchangeAccounts, isLoading: loadingAccounts } = useExchangeAccounts()
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [syncStatus, setSyncStatus] = useState<Record<string, 'idle' | 'syncing' | 'success' | 'error'>>({})
  const [syncResults, setSyncResults] = useState<Record<string, any>>({})
  const [connectionTests, setConnectionTests] = useState<Record<string, any>>({})

  const performSync = async (accountId: string, syncType: 'orders' | 'balances' | 'positions' | 'all') => {
    const key = `${accountId}-${syncType}`
    setSyncStatus(prev => ({ ...prev, [key]: 'syncing' }))
    
    try {
      const token = localStorage.getItem('accessToken')
      const response = await fetch(`http://localhost:3001/api/v1/sync/${syncType}/${accountId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      })

      const result = await response.json()
      
      if (response.ok) {
        setSyncStatus(prev => ({ ...prev, [key]: 'success' }))
        setSyncResults(prev => ({ ...prev, [key]: result }))
      } else {
        setSyncStatus(prev => ({ ...prev, [key]: 'error' }))
        setSyncResults(prev => ({ ...prev, [key]: { error: result.detail || 'Sync failed' } }))
      }
    } catch (error) {
      setSyncStatus(prev => ({ ...prev, [key]: 'error' }))
      setSyncResults(prev => ({ ...prev, [key]: { error: 'Network error' } }))
    }
  }

  const testConnection = async (accountId: string) => {
    setSyncStatus(prev => ({ ...prev, [`${accountId}-test`]: 'syncing' }))
    
    try {
      const token = localStorage.getItem('accessToken')
      const response = await fetch(`http://localhost:3001/api/v1/sync/test/${accountId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      const result = await response.json()
      
      setConnectionTests(prev => ({ ...prev, [accountId]: result }))
      setSyncStatus(prev => ({ 
        ...prev, 
        [`${accountId}-test`]: result.success ? 'success' : 'error' 
      }))
    } catch (error) {
      setConnectionTests(prev => ({ 
        ...prev, 
        [accountId]: { success: false, error: 'Network error' } 
      }))
      setSyncStatus(prev => ({ ...prev, [`${accountId}-test`]: 'error' }))
    }
  }

  const getSyncStatusIcon = (status: string) => {
    switch (status) {
      case 'syncing':
        return <RefreshCw className="h-4 w-4 animate-spin text-blue-500" />
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'syncing':
        return <Badge variant="secondary">Sincronizando...</Badge>
      case 'success':
        return <Badge variant="success">Sucesso</Badge>
      case 'error':
        return <Badge variant="destructive">Erro</Badge>
      default:
        return <Badge variant="outline">Pendente</Badge>
    }
  }

  if (loadingAccounts) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" />
        <span className="ml-2 text-lg">Carregando contas...</span>
      </div>
    )
  }

  const accounts = Array.isArray(exchangeAccounts) ? exchangeAccounts : (exchangeAccounts?.data || [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sincronização de Dados</h1>
          <p className="text-muted-foreground">
            Sincronize ordens, posições, saldos e trades das suas contas de exchange
          </p>
        </div>
      </div>

      {accounts.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Nenhuma conta encontrada</h3>
            <p className="text-muted-foreground text-center">
              Você precisa adicionar contas de exchange antes de sincronizar dados.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {accounts.map((account: any) => {
            const testKey = `${account.id}-test`
            const connectionTest = connectionTests[account.id]
            
            return (
              <Card key={account.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Activity className="h-5 w-5" />
                        {account.name}
                      </CardTitle>
                      <CardDescription>
                        {account.exchange} • {account.environment}
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => testConnection(account.id)}
                        disabled={syncStatus[testKey] === 'syncing'}
                      >
                        {syncStatus[testKey] === 'syncing' ? (
                          <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <AlertCircle className="h-4 w-4 mr-2" />
                        )}
                        Testar Conexão
                      </Button>
                      
                      <Button
                        onClick={() => performSync(account.id, 'all')}
                        disabled={syncStatus[`${account.id}-all`] === 'syncing'}
                        className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                      >
                        {syncStatus[`${account.id}-all`] === 'syncing' ? (
                          <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                        ) : (
                          <Download className="h-4 w-4 mr-2" />
                        )}
                        Sincronizar Tudo
                      </Button>
                    </div>
                  </div>
                  
                  {/* Connection Status */}
                  {connectionTest && (
                    <div className={`p-3 rounded-lg border ${
                      connectionTest.success 
                        ? 'bg-green-50 border-green-200 text-green-700' 
                        : 'bg-red-50 border-red-200 text-red-700'
                    }`}>
                      <div className="flex items-center gap-2">
                        {connectionTest.success ? (
                          <CheckCircle className="h-4 w-4" />
                        ) : (
                          <XCircle className="h-4 w-4" />
                        )}
                        <span className="font-medium">
                          {connectionTest.success ? 'Conectado com sucesso' : 'Falha na conexão'}
                        </span>
                      </div>
                      {connectionTest.error && (
                        <p className="text-sm mt-1">{connectionTest.error}</p>
                      )}
                      {connectionTest.demo && (
                        <Badge variant="secondary" className="mt-2">Modo Demo</Badge>
                      )}
                    </div>
                  )}
                </CardHeader>
                
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Orders Sync */}
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="h-4 w-4 text-blue-500" />
                        <h4 className="font-medium">Ordens</h4>
                      </div>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => performSync(account.id, 'orders')}
                        disabled={syncStatus[`${account.id}-orders`] === 'syncing'}
                      >
                        {getSyncStatusIcon(syncStatus[`${account.id}-orders`])}
                        <span className="ml-2">Sincronizar Ordens</span>
                      </Button>
                      
                      {getStatusBadge(syncStatus[`${account.id}-orders`])}
                      
                      {syncResults[`${account.id}-orders`] && (
                        <div className="text-sm text-muted-foreground">
                          {syncResults[`${account.id}-orders`].synced_count !== undefined ? (
                            <p>{syncResults[`${account.id}-orders`].synced_count} ordens sincronizadas</p>
                          ) : (
                            <p className="text-red-500">{syncResults[`${account.id}-orders`].error}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Balances Sync */}
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <DollarSign className="h-4 w-4 text-green-500" />
                        <h4 className="font-medium">Saldos</h4>
                      </div>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => performSync(account.id, 'balances')}
                        disabled={syncStatus[`${account.id}-balances`] === 'syncing'}
                      >
                        {getSyncStatusIcon(syncStatus[`${account.id}-balances`])}
                        <span className="ml-2">Sincronizar Saldos</span>
                      </Button>
                      
                      {getStatusBadge(syncStatus[`${account.id}-balances`])}
                      
                      {syncResults[`${account.id}-balances`] && (
                        <div className="text-sm text-muted-foreground">
                          {syncResults[`${account.id}-balances`].balances ? (
                            <p>{syncResults[`${account.id}-balances`].balances.length} saldos encontrados</p>
                          ) : (
                            <p className="text-red-500">{syncResults[`${account.id}-balances`].error}</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Positions Sync */}
                    <div className="space-y-3">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-purple-500" />
                        <h4 className="font-medium">Posições</h4>
                      </div>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => performSync(account.id, 'positions')}
                        disabled={syncStatus[`${account.id}-positions`] === 'syncing'}
                      >
                        {getSyncStatusIcon(syncStatus[`${account.id}-positions`])}
                        <span className="ml-2">Sincronizar Posições</span>
                      </Button>
                      
                      {getStatusBadge(syncStatus[`${account.id}-positions`])}
                      
                      {syncResults[`${account.id}-positions`] && (
                        <div className="text-sm text-muted-foreground">
                          {syncResults[`${account.id}-positions`].synced_count !== undefined ? (
                            <p>{syncResults[`${account.id}-positions`].synced_count} posições sincronizadas</p>
                          ) : (
                            <p className="text-red-500">{syncResults[`${account.id}-positions`].error}</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Full Sync Results */}
                  {syncResults[`${account.id}-all`] && (
                    <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                      <h4 className="font-medium mb-2">Resultado da Sincronização Completa</h4>
                      {syncResults[`${account.id}-all`].results ? (
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span>Ordens:</span>
                            <span className={syncResults[`${account.id}-all`].results.orders?.success ? 'text-green-600' : 'text-red-600'}>
                              {syncResults[`${account.id}-all`].results.orders?.success ? 
                                `${syncResults[`${account.id}-all`].results.orders.synced_count} sincronizadas` : 
                                'Erro'
                              }
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Saldos:</span>
                            <span className={syncResults[`${account.id}-all`].results.balances?.success ? 'text-green-600' : 'text-red-600'}>
                              {syncResults[`${account.id}-all`].results.balances?.success ? 
                                `${syncResults[`${account.id}-all`].results.balances.balances?.length || 0} encontrados` : 
                                'Erro'
                              }
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span>Posições:</span>
                            <span className={syncResults[`${account.id}-all`].results.positions?.success ? 'text-green-600' : 'text-red-600'}>
                              {syncResults[`${account.id}-all`].results.positions?.success ? 
                                `${syncResults[`${account.id}-all`].results.positions.synced_count} sincronizadas` : 
                                'Erro'
                              }
                            </span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-red-500 text-sm">{syncResults[`${account.id}-all`].error}</p>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default SyncPage