import React, { useState, useMemo } from 'react'
import { X, Edit2, TrendingUp, TrendingDown, Clock, Activity } from 'lucide-react'
import { Card } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { cn } from '@/lib/utils'
import { EditPositionModal } from '../molecules/EditPositionModal'
import { ClosePositionModal } from '../molecules/ClosePositionModal'
import { useRealTimePrices } from '@/hooks/useRealTimePrice'
import { PositionsSkeleton } from '../atoms/PositionsSkeleton'

interface Position {
  id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  quantity: number
  entryPrice: number
  markPrice?: number
  unrealizedPnl?: number
  margin?: number
  leverage?: number
  status?: 'open' | 'closed'
  exitPrice?: number
  realizedPnl?: number
  closedAt?: string
  createdAt?: string
}

interface SpotBalance {
  asset: string
  free: number
  locked: number
  total: number
  in_order: number
}

interface PositionsCardProps {
  openPositions: Position[]
  closedPositions?: Position[]
  spotBalances?: SpotBalance[]
  onClosePosition?: (positionId: string, percentage?: number) => void
  onModifyPosition?: (positionId: string, data: any) => void
  selectedAccountId?: string
  isLoading?: boolean
  className?: string
}

type TabType = 'open' | 'closed' | 'spot' | 'all'

export const PositionsCard: React.FC<PositionsCardProps> = ({
  openPositions = [],
  closedPositions = [],
  spotBalances = [],
  onClosePosition,
  onModifyPosition,
  selectedAccountId,
  isLoading = false,
  className
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('open')
  const [editingPosition, setEditingPosition] = useState<Position | null>(null)
  const [closingPosition, setClosingPosition] = useState<Position | null>(null)

  // Extrair símbolos únicos das posições abertas para WebSocket
  const openSymbols = useMemo(() =>
    [...new Set(openPositions.map(pos => pos.symbol))],
    [openPositions]
  )

  // WebSocket para preços em tempo real (apenas posições abertas)
  const { pricesData, isConnected } = useRealTimePrices(openSymbols, openSymbols.length > 0)

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price)
  }

  const formatPnl = (pnl: number) => {
    const formatted = formatPrice(Math.abs(pnl))
    return pnl >= 0 ? `+${formatted}` : `-${formatted}`
  }

  const calculatePnlPercentage = (position: Position, pnl: number): number => {
    // P&L % = (P&L / (Entry Price * Quantity)) * 100
    const investmentValue = position.entryPrice * position.quantity
    if (investmentValue === 0) return 0
    return (pnl / investmentValue) * 100
  }

  const formatPnlPercentage = (percentage: number): string => {
    const formatted = Math.abs(percentage).toFixed(2)
    return percentage >= 0 ? `+${formatted}%` : `-${formatted}%`
  }

  const formatDate = (dateString: string | undefined): string => {
    if (!dateString) return '-'

    try {
      const date = new Date(dateString)
      // Formato: DD/MM/YY HH:MM (formato curto)
      const day = date.getDate().toString().padStart(2, '0')
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const year = date.getFullYear().toString().substr(-2) // Últimos 2 dígitos do ano
      const hours = date.getHours().toString().padStart(2, '0')
      const minutes = date.getMinutes().toString().padStart(2, '0')

      return `${day}/${month}/${year} ${hours}:${minutes}`
    } catch (error) {
      return '-'
    }
  }

  // Calcular P&L em tempo real para posições abertas
  const calculateRealTimePnl = (position: Position): number => {
    if (position.status === 'closed') {
      // Para posições fechadas:
      // 1. Se tiver realizedPnl e for diferente de 0, usar ele
      // 2. Se não, usar unrealizedPnl (que tem o valor correto do P&L final)
      // 3. Se tiver exitPrice, calcular P&L = (exitPrice - entryPrice) × quantity × direction
      if (position.realizedPnl && position.realizedPnl !== 0) {
        return position.realizedPnl
      } else if (position.unrealizedPnl !== undefined) {
        return position.unrealizedPnl
      } else if (position.exitPrice) {
        const direction = position.side.toUpperCase() === 'LONG' ? 1 : -1
        const priceDiff = position.exitPrice - position.entryPrice
        return priceDiff * position.quantity * direction
      }
      return 0
    }

    // Para posições abertas: buscar preço em tempo real do WebSocket
    const realTimePrice = pricesData.get(position.symbol)
    const currentPrice = realTimePrice?.price || position.markPrice || position.entryPrice

    // Cálculo P&L: (Preço Atual - Preço Entrada) × Quantidade × Direção
    const direction = position.side.toUpperCase() === 'LONG' ? 1 : -1
    const priceDiff = currentPrice - position.entryPrice
    const unrealizedPnl = priceDiff * position.quantity * direction

    return unrealizedPnl
  }

  const getPositionsForTab = (): Position[] => {
    switch (activeTab) {
      case 'open':
        return openPositions
      case 'closed':
        return closedPositions
      case 'all':
        return [...openPositions, ...closedPositions]
      case 'spot':
        return [] // SPOT usa spotBalances, não positions
      default:
        return openPositions
    }
  }

  const positions = getPositionsForTab()

  const tabs = [
    {
      key: 'open' as TabType,
      label: 'Abertas (FUTURES)',
      count: openPositions.length,
      icon: Activity
    },
    {
      key: 'spot' as TabType,
      label: 'Carteira (SPOT)',
      count: spotBalances.length,
      icon: TrendingUp
    },
    {
      key: 'closed' as TabType,
      label: 'Fechadas',
      count: closedPositions.length,
      icon: Clock
    }
  ]

  return (
    <Card className={cn("h-full overflow-hidden", className)}>
      {/* Header com Tabs */}
      <div className="px-2 py-1 border-b bg-background/50">
        <div className="flex items-center space-x-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  "flex items-center space-x-1 px-2 py-1 rounded text-xs font-medium transition-colors",
                  activeTab === tab.key
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <Icon className="h-3 w-3" />
                <span>{tab.label}</span>
                <Badge
                  variant={activeTab === tab.key ? "secondary" : "outline"}
                  className="text-[9px] px-1 h-3 ml-1"
                >
                  {tab.count}
                </Badge>
              </button>
            )
          })}
        </div>
      </div>

      {/* Conteúdo da Tab */}
      <div className="flex-1 overflow-hidden">
        {!selectedAccountId ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-muted-foreground text-xs">
                Selecione uma conta de negociação
              </p>
              <p className="text-[10px] text-muted-foreground mt-1">
                Para visualizar suas posições FUTURES
              </p>
            </div>
          </div>
        ) : isLoading ? (
          <div className="p-4">
            {/* FASE 2: Usar skeleton loader em vez de spinner */}
            <PositionsSkeleton count={3} />
          </div>
        ) : activeTab === 'spot' ? (
          // Tab SPOT: Exibir saldos da carteira
          spotBalances.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <p className="text-muted-foreground text-xs">
                  Nenhum ativo SPOT encontrado
                </p>
                <p className="text-[10px] text-muted-foreground mt-1">
                  Compre ativos SPOT para visualizar aqui
                </p>
              </div>
            </div>
          ) : (
            <div className="overflow-auto" style={{ maxHeight: '400px' }}>
              <table className="w-full text-[10px]">
                <thead className="sticky top-0 border-b bg-background">
                  <tr className="text-left text-muted-foreground">
                    <th className="px-2 py-1 font-medium">Ativo</th>
                    <th className="px-2 py-1 font-medium text-right">Disponível</th>
                    <th className="px-2 py-1 font-medium text-right">Em Ordem</th>
                    <th className="px-2 py-1 font-medium text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {spotBalances.map((balance) => (
                    <tr
                      key={balance.asset}
                      className="border-b hover:bg-accent/50 transition-colors"
                    >
                      <td className="px-2 py-1.5">
                        <div className="flex items-center space-x-1">
                          <span className="font-mono font-semibold">{balance.asset}</span>
                        </div>
                      </td>
                      <td className="px-2 py-1.5 text-right">
                        <span className="font-mono">{balance.free.toFixed(8)}</span>
                      </td>
                      <td className="px-2 py-1.5 text-right">
                        <span className="font-mono text-muted-foreground">{balance.in_order.toFixed(8)}</span>
                      </td>
                      <td className="px-2 py-1.5 text-right">
                        <div>
                          <div className="font-mono font-semibold">{balance.total.toFixed(8)}</div>
                          {balance.usd_value > 0 && (
                            <div className="text-[9px] text-muted-foreground">
                              ${balance.usd_value.toFixed(2)}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : positions.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-muted-foreground text-xs">
                {activeTab === 'open' && 'Nenhuma posição FUTURES aberta'}
                {activeTab === 'closed' && 'Nenhuma posição fechada (30 dias)'}
                {activeTab === 'all' && 'Nenhuma posição encontrada'}
              </p>
              {activeTab === 'open' && (
                <p className="text-[10px] text-muted-foreground mt-1">
                  Abra uma posição FUTURES para começar
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="overflow-auto" style={{ maxHeight: '400px' }}>
            <table className="w-full text-[10px]">
              <thead className="sticky top-0 border-b bg-background">
                <tr className="text-left text-muted-foreground">
                  <th className="px-2 py-1 font-medium">Símbolo</th>
                  <th className="px-2 py-1 font-medium">Lado</th>
                  <th className="px-2 py-1 font-medium text-right">Qtd</th>
                  <th className="px-2 py-1 font-medium text-right">Entrada</th>
                  {activeTab !== 'closed' && (
                    <th className="px-2 py-1 font-medium text-right">Atual</th>
                  )}
                  {activeTab === 'closed' && (
                    <th className="px-2 py-1 font-medium text-right">Saída</th>
                  )}
                  <th className="px-2 py-1 font-medium text-right">P&L</th>
                  <th className="px-2 py-1 font-medium text-right">P&L %</th>
                  {activeTab === 'closed' && (
                    <th className="px-2 py-1 font-medium text-center">Data</th>
                  )}
                  {activeTab !== 'closed' && (
                    <th className="px-2 py-1 font-medium text-center">Ações</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => {
                  const isOpen = position.status !== 'closed'

                  // Usar P&L calculado em tempo real
                  const pnl = calculateRealTimePnl(position)
                  const pnlPercentage = calculatePnlPercentage(position, pnl)

                  // Obter preço atual do WebSocket para posições abertas
                  const realTimePrice = pricesData.get(position.symbol)
                  const currentPrice = isOpen && realTimePrice
                    ? realTimePrice.price
                    : (position.markPrice || position.entryPrice)

                  return (
                    <tr key={position.id} className="border-b last:border-0 hover:bg-accent/50">
                      <td className="px-2 py-1 font-semibold">
                        {position.symbol}
                        {isOpen && isConnected && realTimePrice && (
                          <span className="ml-1 inline-block h-1 w-1 bg-green-500 rounded-full animate-pulse" title="Real-time data" />
                        )}
                      </td>
                      <td className="px-2 py-1">
                        <Badge
                          variant={position.side.toLowerCase() === 'long' ? 'success' : 'danger'}
                          className={`text-[9px] px-1 h-3 position-badge ${
                            position.side.toLowerCase() === 'long' ? 'position-badge-long' : 'position-badge-short'
                          }`}
                        >
                          {position.side.toLowerCase() === 'long' ? (
                            <TrendingUp className="h-2 w-2 mr-0.5" />
                          ) : (
                            <TrendingDown className="h-2 w-2 mr-0.5" />
                          )}
                          {position.side.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="px-2 py-1 text-right">{position.quantity}</td>
                      <td className="px-2 py-1 text-right">{formatPrice(position.entryPrice)}</td>

                      {/* Preço atual ou de saída */}
                      {activeTab !== 'closed' && (
                        <td className="px-2 py-1 text-right">
                          <span className={isOpen && realTimePrice ? 'font-semibold text-primary' : ''}>
                            {formatPrice(currentPrice)}
                          </span>
                        </td>
                      )}
                      {activeTab === 'closed' && (
                        <td className="px-2 py-1 text-right">
                          {position.exitPrice ? formatPrice(position.exitPrice) : '-'}
                        </td>
                      )}

                      {/* P&L em tempo real */}
                      <td className={cn(
                        "px-2 py-1 text-right font-semibold",
                        pnl >= 0 ? "text-success" : "text-destructive",
                        isOpen && realTimePrice ? 'animate-pulse' : ''
                      )}>
                        {formatPnl(pnl)}
                      </td>

                      {/* P&L Percentage */}
                      <td className={cn(
                        "px-2 py-1 text-right font-semibold",
                        pnlPercentage >= 0 ? "text-success" : "text-destructive",
                        isOpen && realTimePrice ? 'animate-pulse' : ''
                      )}>
                        {formatPnlPercentage(pnlPercentage)}
                      </td>

                      {/* Data - apenas para posições fechadas */}
                      {activeTab === 'closed' && (
                        <td className="px-2 py-1 text-center text-[9px] text-muted-foreground">
                          {formatDate(position.closedAt || position.createdAt)}
                        </td>
                      )}

                      {/* Ações - apenas para posições abertas */}
                      {activeTab !== 'closed' && isOpen && (
                        <td className="px-2 py-1">
                          <div className="flex items-center justify-center space-x-0.5">
                            {onModifyPosition && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-5 w-5"
                                onClick={() => setEditingPosition(position)}
                                title="Editar posição"
                              >
                                <Edit2 className="h-3 w-3" />
                              </Button>
                            )}
                            {onClosePosition && (
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-5 w-5 text-destructive hover:text-destructive"
                                onClick={() => setClosingPosition(position)}
                                title="Fechar posição"
                              >
                                <X className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        </td>
                      )}
                      {activeTab !== 'closed' && !isOpen && (
                        <td className="px-2 py-1 text-center">
                          <Badge variant="outline" className="text-[9px] px-1 h-3">
                            Fechada
                          </Badge>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {editingPosition && (
        <EditPositionModal
          position={editingPosition}
          isOpen={!!editingPosition}
          onClose={() => setEditingPosition(null)}
          onSave={(positionId, data) => {
            onModifyPosition?.(positionId, data)
            setEditingPosition(null)
          }}
        />
      )}

      {closingPosition && (
        <ClosePositionModal
          position={closingPosition}
          isOpen={!!closingPosition}
          onClose={() => setClosingPosition(null)}
          onClosePosition={(positionId, percentage) => {
            onClosePosition?.(positionId, percentage)
            setClosingPosition(null)
          }}
        />
      )}
    </Card>
  )
}