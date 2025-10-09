import { useMemo, useEffect } from 'react'
import { useActivePositions, useBalancesSummary } from './useApiData'
import { usePositionOrders } from './usePositionOrders'

export interface ChartPosition {
  id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  entryPrice: number
  quantity: number
  markPrice?: number
  unrealizedPnl?: number
  stopLoss?: number
  takeProfit?: number
  allTakeProfits?: number[] // Múltiplos TPs
  liquidationPrice?: number
  leverage?: number
  margin?: number
  status: 'open' | 'closing'
}

interface UseChartPositionsParams {
  symbol: string
  exchangeAccountId?: string
}

/**
 * Hook para gerenciar posições específicas do símbolo atual no gráfico
 * Filtra apenas posições abertas do símbolo selecionado
 */
export const useChartPositions = ({ symbol, exchangeAccountId }: UseChartPositionsParams) => {
  // FALLBACK: Usar dados do dashboard quando endpoint /positions/active está quebrado
  const {
    data: dashboardData,
    isLoading: isDashboardLoading,
    error: dashboardError
  } = useBalancesSummary()

  // Buscar posições abertas da conta selecionada (endpoint que pode estar quebrado)
  const {
    data: openPositions = [],
    isLoading,
    error
  } = useActivePositions({
    ...(exchangeAccountId && { exchangeAccountId }),
    operationType: 'futures' // Apenas FUTURES têm SL/TP
  })

  // Buscar ordens de SL/TP para o símbolo
  const {
    data: ordersData,
    isLoading: isLoadingOrders
  } = usePositionOrders(exchangeAccountId, symbol)

  // DEBUG: Log sempre que exchangeAccountId ou openPositions mudarem
  useEffect(() => {
    console.log('🔍 useChartPositions DEBUG:', {
      exchangeAccountId,
      openPositionsCount: openPositions.length,
      hasError: !!error,
      isLoading,
      openPositions: openPositions.map(p => ({ symbol: p.symbol, side: p.side }))
    })
  }, [exchangeAccountId, openPositions, error, isLoading])

  // Filtrar e processar posições do símbolo atual
  const chartPositions = useMemo((): ChartPosition[] => {
    if (!symbol) {
      console.log('⚠️ useChartPositions: Símbolo vazio, retornando []')
      return []
    }

    console.log('🎯 useChartPositions: Filtrando posições para símbolo', symbol)
    console.log('📊 Total de posições recebidas:', openPositions.length)

    // Tentar usar dados do endpoint specific primeiro, fallback para dashboard
    let positionsToUse = openPositions

    // Se endpoint específico não funciona, usar posições do dashboard
    if ((!openPositions || openPositions.length === 0 || error) && dashboardData?.positions) {
      console.log('📊 Usando posições do dashboard como fallback')
      positionsToUse = dashboardData.positions
    } else {
      console.log('📊 Posições disponíveis do endpoint específico:', openPositions.length)
    }

    if (!positionsToUse || positionsToUse.length === 0) {
      console.log('⚠️ Nenhuma posição encontrada (nem endpoint nem dashboard)')
      return []
    }

    return positionsToUse
      .filter(position => {
        // Normalizar símbolos para comparação (remover espaços, etc.)
        const posSymbol = position.symbol?.toUpperCase().trim()
        const targetSymbol = symbol.toUpperCase().trim()

        const matches = posSymbol === targetSymbol
        if (matches) {
          console.log('✅ Posição encontrada para', targetSymbol, ':', position)
        }

        return matches
      })
      .map(position => {
        // Converter para formato do gráfico
        const chartPosition: ChartPosition = {
          id: position.id || `${position.symbol}-${Date.now()}`,
          symbol: position.symbol,
          side: position.side === 'LONG' ? 'LONG' : 'SHORT',
          entryPrice: Number(position.entryPrice || 0),
          quantity: Number(position.quantity || position.size || 0),
          markPrice: Number(position.markPrice || 0),
          unrealizedPnl: Number(position.unrealizedPnl || 0),
          liquidationPrice: Number(position.liquidationPrice || 0),
          leverage: Number(position.leverage || 1),
          margin: Number(position.margin || position.initialMargin || 0),
          status: position.status === 'open' ? 'open' : 'closing',

          // SL/TP das ordens ativas da exchange
          stopLoss: ordersData?.stopLoss,
          takeProfit: ordersData?.takeProfit,
          allTakeProfits: ordersData?.allTakeProfits
        }

        console.log('📈 Posição processada para gráfico:', chartPosition)
        return chartPosition
      })
  }, [symbol, openPositions, dashboardData, error, ordersData])

  // Estatísticas das posições
  const positionsStats = useMemo(() => {
    const totalPositions = chartPositions.length
    const longPositions = chartPositions.filter(p => p.side === 'LONG').length
    const shortPositions = chartPositions.filter(p => p.side === 'SHORT').length
    const totalPnl = chartPositions.reduce((sum, p) => sum + (p.unrealizedPnl || 0), 0)
    const totalMargin = chartPositions.reduce((sum, p) => sum + (p.margin || 0), 0)

    return {
      total: totalPositions,
      long: longPositions,
      short: shortPositions,
      totalPnl,
      totalMargin,
      hasPositions: totalPositions > 0
    }
  }, [chartPositions])

  // Combinar estados de loading e error
  const combinedLoading = isLoading || isDashboardLoading
  const combinedError = error || dashboardError

  // 🚀 PERFORMANCE: Logs commented out to reduce overhead
  // console.log('📊 useChartPositions stats:', positionsStats)

  return {
    positions: chartPositions,
    stats: positionsStats,
    isLoading: combinedLoading,
    error: combinedError,
    hasPositions: positionsStats.hasPositions
  }
}

export type { UseChartPositionsParams }