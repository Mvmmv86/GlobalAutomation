/**
 * Hook para lazy loading de candles (infinite scroll)
 * Permite carregar histórico extenso de candles sob demanda
 * Similar ao comportamento do TradingView
 */

import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useMemo } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export interface Candle {
  time: number // Unix timestamp em segundos
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface CandlesPage {
  candles: Candle[]
  has_more: boolean
  oldest_time: number | null
  symbol: string
  interval: string
  count: number
}

// Mapeamento de intervalos minutos para formato da API
const intervalMap: Record<string, string> = {
  '1': '1m',
  '3': '3m',
  '5': '5m',
  '15': '15m',
  '30': '30m',
  '60': '1h',
  '120': '2h',
  '240': '4h',
  '360': '6h',
  '480': '8h',
  '720': '12h',
  '1D': '1d',
  '3D': '3d',
  '1W': '1w',
  '1M': '1M'
}

// Quantidade inicial de candles para carregar
const INITIAL_CANDLES = 1000
// Quantidade de candles para carregar em cada página
const PAGE_SIZE = 1000

/**
 * Hook para infinite scroll de candles
 *
 * @param symbol - Par de trading (ex: BTCUSDT)
 * @param interval - Intervalo do gráfico (1, 5, 15, 30, 60, 240, 1D, etc)
 * @returns Query com candles e função para carregar mais
 */
export const useInfiniteCandles = (symbol: string, interval: string) => {
  const queryClient = useQueryClient()
  const apiInterval = intervalMap[interval] || interval

  const query = useInfiniteQuery<CandlesPage>({
    queryKey: ['infinite-candles', symbol, interval],
    queryFn: async ({ pageParam }) => {
      const startTime = Date.now()

      // Primeira página: buscar candles iniciais
      if (!pageParam) {
        console.log(`🔥 useInfiniteCandles: Initial fetch ${symbol} ${apiInterval}`)

        const response = await fetch(
          `${API_URL}/api/v1/market/candles?symbol=${symbol}&interval=${apiInterval}&limit=${INITIAL_CANDLES}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
          }
        )

        if (!response.ok) {
          throw new Error(`Failed to fetch candles: ${response.statusText}`)
        }

        const data = await response.json()

        // Normalizar timestamps para segundos
        const candles: Candle[] = (data.candles || []).map((c: any) => ({
          time: c.time < 10000000000 ? c.time : Math.floor(c.time / 1000),
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
          volume: c.volume || 0
        }))

        const elapsed = Date.now() - startTime
        console.log(`✅ useInfiniteCandles: Initial load ${candles.length} candles in ${elapsed}ms`)

        return {
          candles,
          has_more: candles.length >= INITIAL_CANDLES,
          oldest_time: candles.length > 0 ? candles[0].time * 1000 : null,
          symbol,
          interval: apiInterval,
          count: candles.length
        }
      }

      // Páginas subsequentes: buscar histórico antes do endTime
      const endTime = pageParam as number
      console.log(`📜 useInfiniteCandles: Loading history before ${new Date(endTime).toISOString()}`)

      const response = await fetch(
        `${API_URL}/api/v1/market/candles/history?symbol=${symbol}&interval=${apiInterval}&end_time=${endTime}&limit=${PAGE_SIZE}`,
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include'
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch historical candles: ${response.statusText}`)
      }

      const data = await response.json()

      // Normalizar timestamps
      const candles: Candle[] = (data.candles || []).map((c: any) => ({
        time: c.time < 10000000000 ? c.time : Math.floor(c.time / 1000),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: c.volume || 0
      }))

      const elapsed = Date.now() - startTime
      console.log(`✅ useInfiniteCandles: Loaded ${candles.length} historical candles in ${elapsed}ms`)

      return {
        candles,
        has_more: data.has_more,
        oldest_time: data.oldest_time,
        symbol,
        interval: apiInterval,
        count: candles.length
      }
    },
    initialPageParam: null as number | null,
    getNextPageParam: (lastPage) => {
      // Se não há mais dados, retorna undefined para parar
      if (!lastPage.has_more || !lastPage.oldest_time) {
        return undefined
      }
      // Próxima página começa 1ms antes do candle mais antigo
      return lastPage.oldest_time - 1
    },
    staleTime: 30000, // 30 segundos antes de considerar stale
    gcTime: 600000, // 10 minutos no cache
    refetchOnWindowFocus: false, // Não recarregar ao focar janela
    enabled: !!symbol && !!interval
  })

  // Combinar todas as páginas em um único array de candles
  const allCandles = useMemo(() => {
    if (!query.data?.pages) return []

    // Combinar candles de todas as páginas (histórico primeiro, depois recente)
    const combined: Candle[] = []

    // Páginas são carregadas da mais recente para a mais antiga
    // Precisamos inverter para ter ordem cronológica correta
    for (let i = query.data.pages.length - 1; i >= 0; i--) {
      combined.push(...query.data.pages[i].candles)
    }

    // Ordenar por tempo e remover duplicatas
    const uniqueMap = new Map<number, Candle>()
    for (const candle of combined) {
      uniqueMap.set(candle.time, candle)
    }

    return Array.from(uniqueMap.values()).sort((a, b) => a.time - b.time)
  }, [query.data?.pages])

  // Função para carregar mais dados históricos
  const loadMore = useCallback(() => {
    if (query.hasNextPage && !query.isFetchingNextPage) {
      console.log('📚 useInfiniteCandles: Loading more historical data...')
      query.fetchNextPage()
    }
  }, [query])

  // Função para invalidar cache e recarregar
  const refresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['infinite-candles', symbol, interval] })
  }, [queryClient, symbol, interval])

  return {
    // Dados
    candles: allCandles,
    totalCount: allCandles.length,

    // Estado
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage ?? false,

    // Ações
    loadMore,
    refresh,

    // Meta
    pagesLoaded: query.data?.pages.length ?? 0
  }
}
