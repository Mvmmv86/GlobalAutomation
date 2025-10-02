import React, { useState, useRef, useEffect } from 'react'
import { Calendar, Filter, ChevronDown, Check, Building, Settings, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { Input } from '../atoms/Input'
import { formatCurrency, formatDate } from '@/lib/utils'
import { usePositions, useExchangeAccounts } from '@/hooks/useApiData'
import { useQueryClient } from '@tanstack/react-query'

const PositionsPage: React.FC = () => {
  const queryClient = useQueryClient()

  // Filtros
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [selectedExchange, setSelectedExchange] = useState<string>('all')
  const [selectedOperationType, setSelectedOperationType] = useState<string>('all')
  const [symbolFilter, setSymbolFilter] = useState<string>('')

  // Paginação
  const [currentPage, setCurrentPage] = useState<number>(1)
  const itemsPerPage = 10

  // Estados para dropdown customizado
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // API Data hooks - buscar todas as posições
  const { data: positionsApi, isLoading: loadingPositions, error: positionsError } = usePositions()
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
  console.log('📋 PositionsPage: positionsApi:', positionsApi)
  console.log('📋 PositionsPage: loadingPositions:', loadingPositions)
  console.log('📋 PositionsPage: positionsError:', positionsError)
  console.log('🏦 PositionsPage: exchangeAccounts:', exchangeAccounts)
  console.log('🔍 PositionsPage: Filtros aplicados:', { dateFrom, dateTo, selectedExchange, selectedOperationType, symbolFilter })

  const refreshPositions = () => {
    console.log('🔄 Refreshing positions...')
    queryClient.invalidateQueries({ queryKey: ['positions'] })
  }

  const applyFilters = () => {
    console.log('🔍 Aplicando filtros:', {
      dateFrom,
      dateTo,
      selectedExchange,
      selectedOperationType,
      symbolFilter
    })
    setCurrentPage(1)
    queryClient.invalidateQueries({ queryKey: ['positions'] })
  }

  const clearFilters = () => {
    setDateFrom('')
    setDateTo('')
    setSelectedExchange('all')
    setSelectedOperationType('all')
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

  // Usar dados reais da API
  const allPositionsRaw = positionsApi || []

  // Filtros no frontend
  const allPositionsFiltered = allPositionsRaw.filter(position => {
    // Filtro de data
    let passesDateFilter = true
    if (dateFrom || dateTo) {
      const positionDate = position.openedAt ? new Date(position.openedAt) : null
      if (!positionDate) return false

      const positionDateStr = positionDate.toISOString().split('T')[0]
      let passesDateFrom = true
      let passesDateTo = true

      if (dateFrom) {
        passesDateFrom = positionDateStr >= dateFrom
      }

      if (dateTo) {
        passesDateTo = positionDateStr <= dateTo
      }

      passesDateFilter = passesDateFrom && passesDateTo
    }

    // Filtro de tipo de operação (FASE 1: usar campo que já existe ou 'spot' como padrão)
    let passesOperationFilter = true
    if (selectedOperationType !== 'all') {
      const positionOperationType = (position as any).operation_type?.toLowerCase() || 'spot'
      passesOperationFilter = positionOperationType === selectedOperationType
    }

    // Filtro de símbolo
    let passesSymbolFilter = true
    if (symbolFilter.trim() !== '') {
      passesSymbolFilter = position.symbol.toLowerCase().includes(symbolFilter.toLowerCase())
    }

    // Filtro de exchange (FASE 1: usar exchangeAccountId)
    let passesExchangeFilter = true
    if (selectedExchange !== 'all') {
      passesExchangeFilter = position.exchangeAccountId === selectedExchange
    }

    return passesDateFilter && passesOperationFilter && passesSymbolFilter && passesExchangeFilter
  })

  // Paginação
  const totalItems = allPositionsFiltered.length
  const totalPages = Math.ceil(totalItems / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const positions = allPositionsFiltered.slice(startIndex, endIndex)

  console.log('🔍 FINAL: Using positions:', positions)
  console.log('🔍 FINAL: Positions count:', positions?.length)
  console.log('🔍 FINAL: Total items:', totalItems, 'Current page:', currentPage)

  const getStatusBadge = (status: string) => {
    const normalizedStatus = status?.toLowerCase()
    switch (normalizedStatus) {
      case 'open':
        return <Badge variant="success">Aberta</Badge>
      case 'closed':
        return <Badge variant="secondary">Fechada</Badge>
      case 'closing':
        return <Badge variant="warning">Fechando</Badge>
      case 'liquidated':
        return <Badge variant="danger">Liquidada</Badge>
      default:
        return <Badge variant="outline">{normalizedStatus || 'Desconhecido'}</Badge>
    }
  }

  const getSideBadge = (side: string) => {
    return (
      <Badge variant={side === 'long' ? 'success' : 'danger'}>
        {side === 'long' ? 'LONG' : 'SHORT'}
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
            Posições Abertas
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Gerencie suas posições abertas em SPOT e FUTURES
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
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
                      <td colSpan={12} className="px-4 py-12 text-center text-sm text-muted-foreground">
                        Nenhuma posição encontrada com os filtros aplicados
                      </td>
                    </tr>
                  ) : (
                    positions.map((position: any) => (
                      <tr key={position.id} className="hover:bg-muted/50 transition-colors duration-150">
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                          {exchangeAccounts?.find((acc: any) => acc.id === position.exchangeAccountId)?.exchange || position.exchangeAccountId}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                          {position.symbol}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {formatDate(position.openedAt)}
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
                          {position.markPrice ? formatCurrency(position.markPrice) : '-'}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground text-right">
                          {formatCurrency(position.initialMargin || 0)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-right font-medium">
                          <span className={position.unrealizedPnl >= 0 ? 'text-success' : 'text-danger'}>
                            {position.unrealizedPnl >= 0 ? '+' : ''}{formatCurrency(position.unrealizedPnl)}
                          </span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground text-right">
                          {position.liquidationPrice ? formatCurrency(position.liquidationPrice) : '-'}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          {getStatusBadge(position.status)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
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