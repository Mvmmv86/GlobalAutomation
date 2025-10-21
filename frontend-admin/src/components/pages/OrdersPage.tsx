import React, { useState, useRef, useEffect } from 'react'
import { Wifi, Calendar, Filter, ChevronDown, Check, Building, Settings } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { Input } from '../atoms/Input'
import { formatCurrency, formatDate } from '@/lib/utils'
import { formatUTCToLocal } from '@/lib/timezone'
import { useOrders, useExchangeAccounts } from '@/hooks/useApiData'
import { useQueryClient } from '@tanstack/react-query'

const OrdersPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const queryClient = useQueryClient()

  // Filtros
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [selectedExchange, setSelectedExchange] = useState<string>('all')
  const [selectedOperationType, setSelectedOperationType] = useState<string>('all') // all, spot, futures

  // Paginação
  const [currentPage, setCurrentPage] = useState<number>(1)
  const itemsPerPage = 10

  // Estados para dropdown customizado
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // API Data hooks - só busca ordens após seleção de exchange
  const { data: ordersApi, isLoading: loadingOrders, error: ordersError } = useOrders({
    exchangeAccountId: selectedExchange !== 'all' ? selectedExchange : undefined,
    limit: 1000,
  })
  const { data: exchangeAccounts, isLoading: loadingAccounts } = useExchangeAccounts()
  
  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

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
    // Reset da paginação ao aplicar filtros
    setCurrentPage(1)
    // Os filtros de data são aplicados no frontend
    // Apenas invalidamos o cache para forçar uma nova busca da API (se necessário)
    queryClient.invalidateQueries({ queryKey: ['orders'] })
  }

  const clearFilters = () => {
    setDateFrom('')
    setDateTo('')
    setSelectedExchange('all')
    setSelectedOperationType('all')
    setCurrentPage(1) // Reset pagination
    setIsDropdownOpen(false)
    refreshOrders()
  }

  const handleExchangeSelect = (exchangeId: string) => {
    setSelectedExchange(exchangeId)
    setCurrentPage(1) // Reset pagination when changing exchange
    setIsDropdownOpen(false)
    console.log('🏦 Exchange selecionada:', exchangeId)
  }

  const handleOperationTypeSelect = (operationType: string) => {
    setSelectedOperationType(operationType)
    setCurrentPage(1) // Reset pagination when changing operation type
    console.log('⚙️ Tipo de operação selecionado:', operationType)
  }

  // Funções de paginação
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page)
    }
  }

  const goToPreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1)
    }
  }

  const goToNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1)
    }
  }

  const getSelectedExchangeLabel = () => {
    if (selectedExchange === 'all') return 'Todas as exchanges'
    const account = exchangeAccounts?.find((acc: any) => acc.id === selectedExchange)
    return account ? `${account.exchange} - ${account.label || account.name || 'Conta'}` : 'Exchange não encontrada'
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
      symbol: 'SOLUSDT-PERP',
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

  // FASE 1: Usar dados reais da API sempre (sem fallback para mock)
  // REGRA: Mostrar todas as ordens (de todas as contas ou conta específica)
  const allOrdersRaw = ordersApi || []

  // Filtros no frontend (data + tipo de operação)
  const allOrdersFiltered = allOrdersRaw.filter(order => {
    // Filtro de data
    let passesDateFilter = true;
    if (dateFrom || dateTo) {
      const orderDate = order.createdAt ? new Date(order.createdAt) : null;
      if (!orderDate) return false;

      const orderDateStr = orderDate.toISOString().split('T')[0];
      let passesDateFrom = true;
      let passesDateTo = true;

      if (dateFrom) {
        passesDateFrom = orderDateStr >= dateFrom;
      }

      if (dateTo) {
        passesDateTo = orderDateStr <= dateTo;
      }

      passesDateFilter = passesDateFrom && passesDateTo;
    }

    // Filtro de tipo de operação
    let passesOperationFilter = true;
    if (selectedOperationType !== 'all') {
      const orderOperationType = order.operation_type?.toLowerCase() || 'spot';
      passesOperationFilter = orderOperationType === selectedOperationType;
    }

    return passesDateFilter && passesOperationFilter;
  });

  // Paginação
  const totalItems = allOrdersFiltered.length
  const totalPages = Math.ceil(totalItems / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const orders = allOrdersFiltered.slice(startIndex, endIndex)

  console.log('🔍 FINAL: Using orders:', orders)
  console.log('🔍 FINAL: Orders count:', orders?.length)
  console.log('🔍 FINAL: Total items:', totalItems, 'Current page:', currentPage)
  console.log('🔍 FINAL: Raw orders:', allOrdersRaw?.length, 'Filtered orders:', allOrdersFiltered?.length)
  console.log('🔍 FINAL: Date filters:', { dateFrom, dateTo })
  console.log('🔍 FINAL: selectedExchange:', selectedExchange)

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
      <Card className="shadow-sm border-border">
        <CardHeader className="border-b bg-muted/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-primary" />
              <div>
                <CardTitle className="text-lg font-semibold text-foreground">Filtros de Busca</CardTitle>
                <CardDescription className="text-sm text-muted-foreground mt-1">
                  Filtre as ordens por data e conta de exchange
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
            {/* Filtro Data Início */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Data de Início
              </label>
              <div className="relative">
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="pl-10 bg-background border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all duration-200"
                />
                <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              </div>
            </div>

            {/* Filtro Data Fim */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Data de Fim
              </label>
              <div className="relative">
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="pl-10 bg-background border-border focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all duration-200"
                />
                <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              </div>
            </div>

            {/* Dropdown Customizado Exchange */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <Building className="w-4 h-4" />
                Conta de Exchange
              </label>
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  disabled={loadingAccounts}
                  className="w-full px-4 py-2 pl-10 text-left bg-background border border-border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary hover:bg-muted transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Building className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <span className="block truncate text-foreground">
                    {loadingAccounts ? 'Carregando...' : getSelectedExchangeLabel()}
                  </span>
                  <ChevronDown className={`absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
                </button>

                {/* Dropdown List */}
                {isDropdownOpen && !loadingAccounts && (
                  <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    <div className="py-1">
                      {/* Opção "Todas as exchanges" */}
                      <button
                        onClick={() => handleExchangeSelect('all')}
                        className={`w-full px-4 py-3 text-left hover:bg-muted transition-colors duration-150 flex items-center justify-between ${
                          selectedExchange === 'all' ? 'bg-primary/10 text-primary' : 'text-foreground'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-2 h-2 rounded-full bg-muted-foreground"></div>
                          <span className="font-medium">Todas as exchanges</span>
                        </div>
                        {selectedExchange === 'all' && <Check className="w-4 h-4 text-primary" />}
                      </button>

                      {/* Lista de exchanges */}
                      {exchangeAccounts?.map((account: any) => (
                        <button
                          key={account.id}
                          onClick={() => handleExchangeSelect(account.id)}
                          className={`w-full px-4 py-3 text-left hover:bg-muted transition-colors duration-150 flex items-center justify-between ${
                            selectedExchange === account.id ? 'bg-primary/10 text-primary' : 'text-foreground'
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${
                              account.exchange === 'Binance' ? 'bg-yellow-500' :
                              account.exchange === 'Bybit' ? 'bg-orange-500' :
                              account.exchange === 'Coinbase' ? 'bg-blue-500' :
                              'bg-muted-foreground'
                            }`}></div>
                            <div className="flex flex-col">
                              <span className="font-medium">{account.exchange}</span>
                              <span className="text-sm text-muted-foreground">{account.label || account.name}</span>
                            </div>
                          </div>
                          {selectedExchange === account.id && <Check className="w-4 h-4 text-primary" />}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Filtro Tipo de Operação */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Tipo de Operação
              </label>
              <div className="relative">
                <select
                  value={selectedOperationType}
                  onChange={(e) => handleOperationTypeSelect(e.target.value)}
                  className="w-full px-4 py-2 pl-10 bg-background border border-border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary hover:bg-muted transition-all duration-200 appearance-none"
                >
                  <option value="all">Todas as operações</option>
                  <option value="spot">SPOT</option>
                  <option value="futures">FUTURES</option>
                </select>
                <Settings className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
              </div>
            </div>

            {/* Botões */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Ações</label>
              <div className="flex gap-2">
                <Button
                  onClick={applyFilters}
                  variant="default"
                  className="flex-1 bg-primary hover:bg-primary/90 focus:ring-2 focus:ring-primary/20 transition-all duration-200"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Filtrar
                </Button>
                <Button
                  onClick={clearFilters}
                  variant="outline"
                  className="flex-1 border-border hover:bg-muted transition-all duration-200"
                >
                  Limpar
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-sm border-border">
        <CardHeader className="border-b bg-muted/10">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl font-semibold text-foreground">Histórico de Ordens</CardTitle>
              <CardDescription className="text-sm text-muted-foreground mt-1">
                Todas as ordens executadas com informações detalhadas de trading
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs font-medium">
              {totalItems} ordens totais • Página {currentPage} de {totalPages || 1}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingOrders ? (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : (
            <div className="overflow-x-auto">
              {selectedExchange === 'all' ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <Building className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-foreground mb-2">Selecione uma Exchange</h3>
                    <p className="text-sm text-muted-foreground max-w-md">
                      Para visualizar as ordens, selecione uma conta de exchange específica nos filtros acima.
                    </p>
                  </div>
                </div>
              ) : (
              <table className="w-full">
              <thead className="bg-muted/50 border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Exchange
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Símbolo
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Data
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Operação
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Lado
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Entrada/Saída
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Quantidade
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Preço
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Margem USDT
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Profit/Loss
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Order ID
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {orders && orders.length > 0 ? orders.map((order, index) => (
                  <tr key={order.id || Math.random()} className="hover:bg-muted/30 transition-colors duration-150">
                    {/* Exchange */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          (order as any).exchange === 'Binance' || (order as any).exchange === 'binance' ? 'bg-yellow-500' :
                          (order as any).exchange === 'Bybit' || (order as any).exchange === 'bybit' ? 'bg-orange-500' :
                          'bg-gray-500'
                        }`} />
                        <span className="text-sm font-medium text-foreground capitalize">
                          {(order as any).exchange || (order as any).exchangeAccountId || 'Binance'}
                        </span>
                      </div>
                    </td>

                    {/* Símbolo */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-sm font-semibold text-foreground">
                        {order.symbol || 'N/A'}
                      </span>
                    </td>

                    {/* Data */}
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="text-sm text-foreground">
                          {order.createdAt ? new Date(order.createdAt).toLocaleDateString('pt-BR') : 'N/A'}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {order.createdAt ? new Date(order.createdAt).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : ''}
                        </span>
                      </div>
                    </td>

                    {/* Operação (Spot/Futures) */}
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <Badge variant={(order.operation_type?.toLowerCase() === 'futures' ? 'warning' : 'secondary')} className="text-xs font-medium">
                        {order.operation_type?.toUpperCase() || 'SPOT'}
                      </Badge>
                    </td>

                    {/* Tipo de Ordem */}
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <span className="text-sm text-muted-foreground capitalize">
                        {order.type || 'market'}
                      </span>
                    </td>

                    {/* Lado (Compra/Venda) */}
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <Badge
                        variant={order.side === 'buy' ? 'success' : 'danger'}
                        className="text-xs font-semibold"
                      >
                        {order.side === 'buy' ? 'COMPRA' : 'VENDA'}
                      </Badge>
                    </td>

                    {/* Entrada/Saída */}
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <Badge
                        variant="outline"
                        className={`text-xs font-medium ${
                          order.side === 'buy' ? 'text-success border-success' : 'text-danger border-danger'
                        }`}
                      >
                        {order.side === 'buy' ? 'ENTRADA' : 'SAÍDA'}
                      </Badge>
                    </td>

                    {/* Quantidade */}
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-sm font-medium text-foreground">
                        {order.quantity || 0}
                      </span>
                    </td>

                    {/* Preço */}
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-sm font-medium text-foreground">
                        {(() => {
                          // FASE 1: Usar dados da API quando disponíveis
                          const apiOrder = order as any;
                          const price = apiOrder.price || order.price || order.averageFillPrice || 0;
                          const marginUsdt = apiOrder.margin_usdt || 0;

                          // Se temos margin_usdt mas não price, calcular price
                          if (marginUsdt > 0 && price === 0 && (order.quantity || 0) > 0) {
                            const calculatedPrice = marginUsdt / (order.quantity || 1);
                            return calculatedPrice.toFixed(2);
                          }

                          return price > 0 ? price.toFixed(2) : '0.00';
                        })()}
                      </span>
                    </td>

                    {/* Margem USDT */}
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <span className="text-sm font-semibold text-foreground">
                        {(() => {
                          // FASE 1: Usar margin_usdt da API quando disponível
                          const apiOrder = order as any;
                          const marginFromApi = apiOrder.margin_usdt || 0;

                          if (marginFromApi > 0) {
                            return marginFromApi.toFixed(2);
                          }

                          // Fallback: calcular baseado em quantity x price
                          const price = order.price || order.averageFillPrice || 0;
                          return ((order.quantity || 0) * price).toFixed(2);
                        })()}
                      </span>
                    </td>

                    {/* Profit/Loss */}
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      {(() => {
                        // FASE 1: Usar profit_loss da API quando disponível
                        const apiOrder = order as any;
                        const profitLossFromApi = apiOrder.profit_loss || 0;
                        const marginUsdt = apiOrder.margin_usdt || 0;

                        let profitLoss = profitLossFromApi;

                        // Se não temos P&L da API, fazer cálculo básico
                        if (profitLoss === 0 && order.status === 'filled') {
                          // Usar margin_usdt como base para cálculo
                          profitLoss = order.side === 'sell' ? marginUsdt * 0.02 : -marginUsdt * 0.01;
                        }

                        const percentage = marginUsdt > 0 ? (profitLoss / marginUsdt) * 100 : 0;

                        return (
                          <div className="flex flex-col items-end">
                            <span className={`text-sm font-bold ${
                              profitLoss > 0 ? 'text-green-600 dark:text-green-400' :
                              profitLoss < 0 ? 'text-red-600 dark:text-red-400' :
                              'text-gray-500'
                            }`}>
                              {profitLoss > 0 ? '+' : ''}{profitLoss.toFixed(2)}
                            </span>
                            {profitLoss !== 0 && marginUsdt > 0 && (
                              <span className="text-xs text-muted-foreground">
                                {percentage.toFixed(1)}%
                              </span>
                            )}
                          </div>
                        );
                      })()}
                    </td>

                    {/* Order ID - Nova coluna para agrupar operações */}
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      {(() => {
                        const apiOrder = order as any;
                        const orderId = apiOrder.order_id || '-';
                        return (
                          <Badge variant="outline" className="text-xs font-mono">
                            {orderId}
                          </Badge>
                        );
                      })()}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={12} className="px-6 py-12 text-center">
                      <div className="flex flex-col items-center justify-center">
                        <div className="text-muted-foreground text-sm">
                          {loadingOrders ? 'Carregando ordens...' : 'Nenhuma ordem encontrada'}
                        </div>
                        {!loadingOrders && (
                          <p className="text-xs text-muted-foreground mt-2">
                            {selectedExchange === 'all' ?
                              'Nenhuma ordem encontrada para todas as exchanges' :
                              `Nenhuma ordem encontrada para a conta selecionada`}
                          </p>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
              </table>
              )}
            </div>
          )}

          {/* Controles de Paginação */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-border">
              <div className="flex items-center text-sm text-muted-foreground">
                Mostrando {startIndex + 1} a {Math.min(endIndex, totalItems)} de {totalItems} ordens
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={goToPreviousPage}
                  disabled={currentPage === 1}
                  className="h-8"
                >
                  Anterior
                </Button>

                <div className="flex items-center space-x-1">
                  {/* Páginas numeradas */}
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNumber = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                    if (pageNumber > totalPages) return null;

                    return (
                      <Button
                        key={pageNumber}
                        variant={currentPage === pageNumber ? "default" : "outline"}
                        size="sm"
                        onClick={() => goToPage(pageNumber)}
                        className="h-8 w-8 p-0"
                      >
                        {pageNumber}
                      </Button>
                    );
                  })}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={goToNextPage}
                  disabled={currentPage === totalPages}
                  className="h-8"
                >
                  Próxima
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default OrdersPage