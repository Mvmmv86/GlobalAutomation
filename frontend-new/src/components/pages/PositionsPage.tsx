import React, { useState, useRef, useEffect } from 'react'
import { Calendar, Filter, ChevronDown, Check, Building, Settings, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { Input } from '../atoms/Input'
import { formatCurrency, formatDate } from '@/lib/utils'
import { formatUTCToLocal } from '@/lib/timezone'
import { useOrders, usePositions, useExchangeAccounts, useAccountBalance } from '@/hooks/useApiData'
import { useQueryClient } from '@tanstack/react-query'

const PositionsPage: React.FC = () => {
  const queryClient = useQueryClient()

  // Filtros - Valores padrão: último 2 meses até hoje
  const getDefaultDateFrom = () => {
    const date = new Date()
    date.setMonth(date.getMonth() - 2)
    return date.toISOString().split('T')[0]
  }
  const getDefaultDateTo = () => {
    return new Date().toISOString().split('T')[0]
  }

  const [dateFrom, setDateFrom] = useState<string>(getDefaultDateFrom())
  const [dateTo, setDateTo] = useState<string>(getDefaultDateTo())
  const [selectedExchange, setSelectedExchange] = useState<string>('all')
  const [selectedOperationType, setSelectedOperationType] = useState<string>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('open')
  const [symbolFilter, setSymbolFilter] = useState<string>('')

  // Paginação
  const [currentPage, setCurrentPage] = useState<number>(1)
  const itemsPerPage = 10

  // Estados para dropdown customizado
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isFiltering, setIsFiltering] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // API Data hooks - ABORDAGEM HÍBRIDA: useOrders + usePositions + useAccountBalance
  const { data: ordersApi, isLoading: loadingOrders, error: ordersError } = useOrders({
    exchangeAccountId: selectedExchange !== 'all' ? selectedExchange : undefined,
    limit: 1000 // Volume alto para histórico
  })

  // Buscar posições reais da tabela positions (dados estruturados corretos)
  const { data: realPositionsApi, isLoading: loadingRealPositions } = usePositions({
    exchangeAccountId: selectedExchange !== 'all' ? selectedExchange : undefined,
    limit: 100 // Posições reais são poucas
  })

  // Buscar dados em tempo real da conta (mark prices, balance, etc.)
  const { data: accountBalanceData, isLoading: loadingBalance } = useAccountBalance(
    selectedExchange !== 'all' ? selectedExchange : undefined
  )

  const { data: exchangeAccounts, isLoading: loadingAccounts } = useExchangeAccounts()

  // Loading state combinado
  const loadingPositions = loadingOrders || loadingRealPositions || loadingBalance
  const positionsError = ordersError

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
  console.log('📋 PositionsPage: ordersApi:', ordersApi?.length, 'orders')
  console.log('🎯 PositionsPage: realPositionsApi:', realPositionsApi?.length, 'real positions')
  console.log('💰 PositionsPage: accountBalanceData:', accountBalanceData)
  console.log('📋 PositionsPage: loadingPositions:', loadingPositions)
  console.log('📋 PositionsPage: positionsError:', positionsError)
  console.log('🏦 PositionsPage: exchangeAccounts:', exchangeAccounts)
  console.log('🔍 PositionsPage: Filtros aplicados:', { dateFrom, dateTo, selectedExchange, selectedOperationType, selectedStatus, symbolFilter })

  const refreshPositions = () => {
    console.log('🔄 Refreshing orders (for positions)...')
    queryClient.invalidateQueries({ queryKey: ['orders'] })
  }

  const applyFilters = async () => {
    console.log('🔍 Aplicando filtros:', {
      dateFrom,
      dateTo,
      selectedExchange,
      selectedOperationType,
      selectedStatus,
      symbolFilter
    })
    setIsFiltering(true)
    setCurrentPage(1)

    // Invalidar cache para forçar refetch com novos filtros
    await queryClient.invalidateQueries({ queryKey: ['orders'] })
    await queryClient.invalidateQueries({ queryKey: ['positions'] })

    // Pequeno delay para feedback visual
    setTimeout(() => setIsFiltering(false), 500)
  }

  const clearFilters = () => {
    setDateFrom(getDefaultDateFrom())
    setDateTo(getDefaultDateTo())
    setSelectedExchange('all')
    setSelectedOperationType('all')
    setSelectedStatus('open')
    setSymbolFilter('')
    setCurrentPage(1)
    setIsDropdownOpen(false)
    refreshPositions()
  }

  const handleExchangeSelect = (exchangeId: string) => {
    setSelectedExchange(exchangeId)
    setCurrentPage(1)
    setIsDropdownOpen(false)
    console.log('🏦 Exchange selecionada:', exchangeId)
  }

  const handleOperationTypeSelect = (operationType: string) => {
    setSelectedOperationType(operationType)
    setCurrentPage(1)
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

  // SOLUÇÃO HÍBRIDA: Combinar ordens históricas + posições reais + dados tempo real
  const allOrdersRaw = ordersApi || []
  const realPositions = realPositionsApi || []

  // Função HÍBRIDA: Usar posições reais quando disponíveis, senão criar virtuais das ordens
  const createHybridPositions = (orders: any[], realPositions: any[], accountBalance: any) => {
    const positionsMap = new Map()

    // ETAPA 1: Adicionar posições REAIS da tabela positions (dados estruturados corretos)
    realPositions.forEach(realPos => {
      positionsMap.set(realPos.id, {
        id: realPos.id,
        symbol: realPos.symbol,
        side: realPos.side,
        status: realPos.status === 'closed' ? 'closed' : 'open', // Status direto da tabela positions
        operation_type: realPos.operationType || 'futures',
        openedAt: realPos.openedAt,
        closedAt: realPos.closedAt,
        size: realPos.quantity || realPos.size || 0,
        entryPrice: realPos.entryPrice || 0,
        markPrice: realPos.markPrice || realPos.entryPrice || 0, // Priorizar markPrice
        exitPrice: realPos.exitPrice || realPos.exit_price || realPos.close_price ||
                  (realPos.status === 'closed' ? realPos.markPrice : null), // Preço de saída real
        initialMargin: (() => {
          const margin = parseFloat(realPos.margin || realPos.initialMargin || realPos.initial_margin || '0')
          if (margin > 0) return margin
          // Calcular margem aproximada para FUTURES
          if (realPos.operationType === 'futures' || realPos.operation_type === 'futures') {
            const price = parseFloat(realPos.entryPrice || '0')
            const size = parseFloat(realPos.size || realPos.quantity || '0')
            const leverage = parseFloat(realPos.leverage || '1') || 1
            return (price * size) / leverage
          }
          return 0
        })(),
        unrealizedPnl: realPos.unrealizedPnl || 0,
        realizedPnl: realPos.realizedPnl || 0,
        liquidationPrice: parseFloat(realPos.liquidationPrice || realPos.liquidation_price || '0'),
        leverage: realPos.leverage || 1,
        exchangeAccountId: realPos.exchangeAccountId,
        isReal: true, // Flag para identificar posições reais
        orders: [] // Será preenchido abaixo se houver ordens relacionadas
      })
    })

    // ETAPA 2: Agrupar ordens por order_id para criar posições virtuais (histórico)
    orders.forEach(order => {
      const orderId = order.order_id || `${order.symbol}_${order.createdAt}`

      // Verificar se já existe uma posição real para este símbolo
      const existingRealPosition = Array.from(positionsMap.values()).find(pos =>
        pos.isReal && pos.symbol === order.symbol && pos.exchangeAccountId === order.exchangeAccountId
      )

      if (existingRealPosition) {
        // Adicionar ordem ao histórico da posição real
        existingRealPosition.orders.push(order)
      } else if (!positionsMap.has(orderId)) {
        // Criar posição virtual baseada na ordem (para histórico)
        // Status inteligente melhorado: verificar múltiplos critérios
        const isClosedOperation = (
          // Tem P&L realizado (posição fechada)
          (order.profit_loss !== undefined && order.profit_loss !== 0) ||
          // É uma ordem de saída explícita
          (order.side === 'sell' && order.entry_exit === 'saida') ||
          // Ordem preenchida com P&L definido
          (order.status === 'filled' && order.profit_loss !== undefined) ||
          // Verificar se há data de fechamento
          (order.updatedAt && order.profit_loss !== undefined)
        )

        positionsMap.set(orderId, {
          id: orderId,
          symbol: order.symbol,
          side: order.side,
          status: isClosedOperation ? 'closed' : 'open',
          operation_type: order.operation_type || 'spot',
          openedAt: order.createdAt,
          closedAt: order.profit_loss !== undefined && order.profit_loss !== 0 ? order.updatedAt : null,
          size: order.quantity || 0,
          entryPrice: order.price || order.averageFillPrice || 0,
          markPrice: order.price || order.averageFillPrice || 0,
          exitPrice: isClosedOperation ? (
            order.exit_price || order.close_price ||
            (order.side === 'sell' ? (order.price || order.averageFillPrice) : null)
          ) : null,
          initialMargin: (() => {
            const margin = parseFloat(order.margin_usdt || order.margin || order.initial_margin || '0')
            if (margin > 0) return margin
            // Calcular margem aproximada para FUTURES
            if (order.operation_type === 'futures') {
              const price = parseFloat(order.price || order.averageFillPrice || '0')
              const quantity = parseFloat(order.quantity || '0')
              const leverage = parseFloat(order.leverage || '1') || 1
              return (price * quantity) / leverage
            }
            return 0
          })(),
          unrealizedPnl: order.profit_loss || 0,
          realizedPnl: order.profit_loss || 0,
          liquidationPrice: 0, // Será calculado ou obtido do backend
          leverage: 1,
          exchangeAccountId: order.exchangeAccountId,
          isReal: false, // Posição virtual das ordens
          orders: [order]
        })
      } else {
        // Atualizar posição virtual existente
        const position = positionsMap.get(orderId)
        position.orders.push(order)

        // Atualizar status se encontrar evidência de fechamento
        if ((order.profit_loss !== undefined && order.profit_loss !== 0) ||
            (order.side === 'sell' && order.entry_exit === 'saida')) {
          position.status = 'closed'
          position.closedAt = order.updatedAt
          position.realizedPnl = order.profit_loss || position.realizedPnl
          // Capturar preço de saída se disponível
          if (order.side === 'sell' || order.entry_exit === 'saida') {
            position.exitPrice = order.exit_price || order.close_price ||
                               order.price || order.averageFillPrice || position.exitPrice
          }
        }
      }
    })

    return Array.from(positionsMap.values())
  }

  // Filtros no frontend (mesma lógica da OrdersPage)
  const allOrdersFiltered = allOrdersRaw.filter(order => {
    // Filtro de data
    let passesDateFilter = true
    if (dateFrom || dateTo) {
      const orderDate = order.createdAt ? new Date(order.createdAt) : null
      if (!orderDate) return false

      const orderDateStr = orderDate.toISOString().split('T')[0]
      let passesDateFrom = true
      let passesDateTo = true

      if (dateFrom) {
        passesDateFrom = orderDateStr >= dateFrom
      }

      if (dateTo) {
        passesDateTo = orderDateStr <= dateTo
      }

      passesDateFilter = passesDateFrom && passesDateTo
    }

    // Filtro de tipo de operação
    let passesOperationFilter = true
    if (selectedOperationType !== 'all') {
      const orderOperationType = order.operation_type?.toLowerCase() || 'spot'
      passesOperationFilter = orderOperationType === selectedOperationType
    }

    // Filtro de símbolo
    let passesSymbolFilter = true
    if (symbolFilter.trim() !== '') {
      passesSymbolFilter = order.symbol.toLowerCase().includes(symbolFilter.toLowerCase())
    }

    return passesDateFilter && passesOperationFilter && passesSymbolFilter
  })

  // Filtrar posições reais também pelos critérios de data/operação/símbolo
  const realPositionsFiltered = realPositions.filter(position => {
    // Filtro de data
    let passesDateFilter = true
    if (dateFrom || dateTo) {
      const posDate = position.openedAt ? new Date(position.openedAt) : null
      if (!posDate) return true // Manter posições sem data

      const posDateStr = posDate.toISOString().split('T')[0]
      if (dateFrom && posDateStr < dateFrom) passesDateFilter = false
      if (dateTo && posDateStr > dateTo) passesDateFilter = false
    }

    // Filtro de tipo de operação
    let passesOperationFilter = true
    if (selectedOperationType !== 'all') {
      const posOperationType = (position.operationType || position.operation_type || 'spot').toLowerCase()
      passesOperationFilter = posOperationType === selectedOperationType
    }

    // Filtro de símbolo
    let passesSymbolFilter = true
    if (symbolFilter.trim() !== '') {
      passesSymbolFilter = position.symbol?.toLowerCase().includes(symbolFilter.toLowerCase())
    }

    return passesDateFilter && passesOperationFilter && passesSymbolFilter
  })

  // Criar posições híbridas (reais filtradas + virtuais das ordens filtradas)
  const allPositionsGrouped = createHybridPositions(allOrdersFiltered, realPositionsFiltered, accountBalanceData)

  // Filtro de status das posições
  const allPositionsFiltered = allPositionsGrouped.filter(position => {
    if (selectedStatus === 'all') return true
    return position.status === selectedStatus
  })

  // Paginação
  const totalItems = allPositionsFiltered.length
  const totalPages = Math.ceil(totalItems / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const positions = allPositionsFiltered.slice(startIndex, endIndex)

  console.log('🔍 FINAL: Raw orders:', allOrdersRaw?.length)
  console.log('🔍 FINAL: Real positions:', realPositions?.length)
  console.log('🔍 FINAL: Real positions filtered:', realPositionsFiltered?.length)
  console.log('🔍 FINAL: Filtered orders:', allOrdersFiltered?.length)
  console.log('🔍 FILTERS: dateFrom=', dateFrom, 'dateTo=', dateTo, 'status=', selectedStatus, 'operation=', selectedOperationType, 'symbol=', symbolFilter)
  console.log('🔍 FINAL: Hybrid positions:', allPositionsGrouped?.length)
  console.log('🔍 FINAL: Real vs Virtual breakdown:', {
    real: allPositionsGrouped?.filter(p => p.isReal)?.length || 0,
    virtual: allPositionsGrouped?.filter(p => !p.isReal)?.length || 0
  })
  console.log('🔍 FINAL: Using positions:', positions)
  console.log('🔍 FINAL: Positions count:', positions?.length)
  console.log('🔍 FINAL: Total items:', totalItems, 'Current page:', currentPage)
  // Debug: Ver dados específicos das posições
  if (positions?.length > 0) {
    console.log('🔍 DEBUG: Primeira posição completa:', {
      symbol: positions[0].symbol,
      exitPrice: positions[0].exitPrice,
      initialMargin: positions[0].initialMargin,
      status: positions[0].status,
      operation_type: positions[0].operation_type,
      isReal: positions[0].isReal
    })
  }

  const getStatusBadge = (status: string) => {
    const normalizedStatus = status?.toLowerCase()
    switch (normalizedStatus) {
      case 'open':
        return <Badge variant="success" className="bg-green-100 text-green-800 border-green-200">🟢 Aberta</Badge>
      case 'closed':
        return <Badge variant="secondary" className="bg-gray-100 text-gray-800 border-gray-200">⚫ Fechada</Badge>
      case 'closing':
        return <Badge variant="warning" className="bg-yellow-100 text-yellow-800 border-yellow-200">🟡 Fechando</Badge>
      case 'liquidated':
        return <Badge variant="danger" className="bg-red-100 text-red-800 border-red-200">🔴 Liquidada</Badge>
      default:
        return <Badge variant="outline" className="bg-gray-50 text-gray-600 border-gray-300">❓ {normalizedStatus || 'Desconhecido'}</Badge>
    }
  }

  const getSideBadge = (side: string) => {
    // Normalizar valores possíveis da API
    const normalizedSide = side?.toLowerCase()
    const isLong = normalizedSide === 'long' || normalizedSide === 'buy' || normalizedSide === 'compra'

    return (
      <Badge variant={isLong ? 'success' : 'danger'}>
        {isLong ? 'LONG' : 'SHORT'}
      </Badge>
    )
  }

  const getOperationTypeBadge = (type: string) => {
    const normalizedType = type?.toUpperCase() || 'SPOT'
    return (
      <Badge variant={normalizedType === 'FUTURES' ? 'warning' : 'secondary'}>
        {normalizedType}
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
            Gerencie suas posições em SPOT e FUTURES
          </p>
        </div>
      </div>

      {/* Card de Filtros */}
      <Card className="shadow-sm border-border">
        <CardHeader className="border-b bg-muted/10">
          <CardTitle className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filtros
          </CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            Filtre as posições por exchange, data, tipo de operação e símbolo
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-4">
            {/* Filtro de Data From */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Data Inicial
              </label>
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full"
              />
            </div>

            {/* Filtro de Data To */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Data Final
              </label>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full"
              />
            </div>

            {/* Filtro Exchange Account - Dropdown Customizado */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <Building className="w-4 h-4" />
                Exchange
              </label>
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary hover:bg-muted transition-all duration-200 text-left flex items-center justify-between"
                  disabled={loadingAccounts}
                >
                  <span className="text-sm text-foreground truncate">
                    {loadingAccounts ? 'Carregando...' : getSelectedExchangeLabel()}
                  </span>
                  <ChevronDown className={`absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
                </button>

                {isDropdownOpen && !loadingAccounts && (
                  <div className="absolute z-50 w-full mt-1 bg-card border border-border rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    <div className="py-1">
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

            {/* Filtro Status */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Status
              </label>
              <div className="relative">
                <select
                  value={selectedStatus}
                  onChange={(e) => {
                    setSelectedStatus(e.target.value)
                    setCurrentPage(1)
                  }}
                  className="w-full px-4 py-2 pl-10 bg-background border border-border rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary hover:bg-muted transition-all duration-200 appearance-none"
                >
                  <option value="all">Todas</option>
                  <option value="open">Abertas</option>
                  <option value="closed">Fechadas</option>
                </select>
                <TrendingUp className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
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
                  <option value="all">Todas</option>
                  <option value="spot">SPOT</option>
                  <option value="futures">FUTURES</option>
                </select>
                <Settings className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
              </div>
            </div>

            {/* Filtro Símbolo */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Símbolo
              </label>
              <Input
                type="text"
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value)}
                placeholder="Ex: BTC, ETH..."
                className="w-full"
              />
            </div>

            {/* Botões */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Ações</label>
              <div className="flex gap-2">
                <Button
                  onClick={applyFilters}
                  variant="default"
                  disabled={isFiltering || loadingPositions}
                  className="flex-1 bg-primary hover:bg-primary/90 focus:ring-2 focus:ring-primary/20 transition-all duration-200"
                >
                  {isFiltering || loadingPositions ? (
                    <>
                      <LoadingSpinner className="w-4 h-4 mr-2" />
                      Filtrando...
                    </>
                  ) : (
                    <>
                      <Filter className="w-4 h-4 mr-2" />
                      Filtrar
                    </>
                  )}
                </Button>
                <Button
                  onClick={clearFilters}
                  variant="outline"
                  disabled={isFiltering}
                  className="flex-1 border-border hover:bg-muted transition-all duration-200"
                >
                  Limpar
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Card de Posições */}
      <Card className="shadow-sm border-border">
        <CardHeader className="border-b bg-muted/10">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-xl font-semibold text-foreground">Posições Abertas</CardTitle>
              <CardDescription className="text-sm text-muted-foreground mt-1">
                Todas as posições em aberto com informações detalhadas
              </CardDescription>
            </div>
            <Badge variant="outline" className="text-xs font-medium">
              {totalItems} posições • Página {currentPage} de {totalPages || 1}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loadingPositions ? (
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
                      Para visualizar as posições, selecione uma conta de exchange específica nos filtros acima.
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
                      Data Abertura
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Operação
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Lado
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Quantidade
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Preço Entrada
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Preço Atual
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Preço Saída
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Margem USDT
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      P&L Não Realizado
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Preço Liquidação
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-border">
                  {positions.length === 0 ? (
                    <tr>
                      <td colSpan={13} className="px-4 py-12 text-center text-sm text-muted-foreground">
                        Nenhuma posição encontrada com os filtros aplicados
                      </td>
                    </tr>
                  ) : (
                    positions.map((position: any) => (
                      <tr key={position.id} className="hover:bg-muted/50 transition-colors duration-150">
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                          <div className="flex items-center gap-2">
                            {exchangeAccounts?.find((acc: any) => acc.id === position.exchangeAccountId)?.exchange || position.exchangeAccountId}
                            {position.status === 'open' ? (
                              <Badge variant="success" className="text-xs">
                                🟢 Aberta
                              </Badge>
                            ) : (
                              <Badge variant="secondary" className="text-xs">
                                ⚫ Fechada
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                          {position.symbol}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {formatUTCToLocal(position.openedAt)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          {getOperationTypeBadge(position.operation_type || 'spot')}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          {getSideBadge(position.side)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground text-right">
                          {position.size}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground text-right">
                          {formatCurrency(position.entryPrice)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground text-right">
                          <div className="flex flex-col items-end">
                            <span className={position.isReal ? 'font-semibold text-green-600' : 'text-muted-foreground'}>
                              {position.markPrice ? formatCurrency(position.markPrice) : '-'}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-right">
                          <div className="flex flex-col items-end">
                            {position.status === 'closed' && position.exitPrice && position.exitPrice > 0 ? (
                              <>
                                <span className="font-medium text-blue-600">
                                  {formatCurrency(position.exitPrice)}
                                </span>
                                <span className="text-xs text-blue-500">fechamento</span>
                              </>
                            ) : position.status === 'open' ? (
                              <span className="text-muted-foreground text-xs">Em aberto</span>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-right">
                          <div className="flex flex-col items-end">
                            {position.operation_type === 'FUTURES' || position.operation_type === 'futures' ? (
                              <>
                                <span className={`font-medium ${
                                  position.isReal ? 'text-yellow-600' : 'text-muted-foreground'
                                }`}>
                                  {formatCurrency(position.initialMargin || 0)}
                                </span>
                                <span className="text-xs text-yellow-500">FUTURES</span>
                              </>
                            ) : (
                              <span className="text-muted-foreground">
                                N/A (SPOT)
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-right font-medium">
                          <div className="flex flex-col items-end">
                            {position.isReal && position.status === 'open' ? (
                              <span className={position.unrealizedPnl >= 0 ? 'text-green-600 font-bold' : 'text-red-600 font-bold'}>
                                {position.unrealizedPnl >= 0 ? '+' : ''}{formatCurrency(position.unrealizedPnl)}
                              </span>
                            ) : (
                              <span className={position.realizedPnl >= 0 ? 'text-green-600' : 'text-red-600'}>
                                {position.realizedPnl >= 0 ? '+' : ''}{formatCurrency(position.realizedPnl)}
                              </span>
                            )}
                            <span className="text-xs text-muted-foreground">
                              {position.isReal && position.status === 'open' ? 'não realizado' : 'realizado'}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-right">
                          <div className="flex flex-col items-end">
                            {position.liquidationPrice && position.liquidationPrice > 0 ? (
                              <>
                                <span className={`font-medium ${
                                  position.isReal ? 'text-orange-600' : 'text-muted-foreground'
                                }`}>
                                  {formatCurrency(position.liquidationPrice)}
                                </span>
                              </>
                            ) : (
                              <span className="text-muted-foreground">
                                {position.operation_type === 'FUTURES' || position.operation_type === 'futures' ?
                                  '-' : 'N/A (SPOT)'
                                }
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          {getStatusBadge(position.status)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              )}
            </div>
          )}

          {/* Paginação */}
          {!loadingPositions && totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-muted/10">
              <div className="text-sm text-muted-foreground">
                Mostrando {startIndex + 1} a {Math.min(endIndex, totalItems)} de {totalItems} posições
              </div>
              <div className="flex items-center gap-2">
                <Button
                  onClick={goToPreviousPage}
                  disabled={currentPage === 1}
                  variant="outline"
                  size="sm"
                  className="border-border"
                >
                  Anterior
                </Button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNumber
                    if (totalPages <= 5) {
                      pageNumber = i + 1
                    } else if (currentPage <= 3) {
                      pageNumber = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      pageNumber = totalPages - 4 + i
                    } else {
                      pageNumber = currentPage - 2 + i
                    }

                    return (
                      <Button
                        key={pageNumber}
                        onClick={() => goToPage(pageNumber)}
                        variant={currentPage === pageNumber ? 'default' : 'outline'}
                        size="sm"
                        className={currentPage === pageNumber ? 'bg-primary text-primary-foreground' : 'border-border'}
                      >
                        {pageNumber}
                      </Button>
                    )
                  })}
                </div>
                <Button
                  onClick={goToNextPage}
                  disabled={currentPage === totalPages}
                  variant="outline"
                  size="sm"
                  className="border-border"
                >
                  Próximo
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default PositionsPage