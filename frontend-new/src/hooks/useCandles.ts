/**
 * Hook para buscar dados de candles para o CanvasChart
 * Utiliza React Query para cache e auto-refetch
 */

import { useQuery } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export interface Candle {
  time: number // Unix timestamp em milissegundos
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface CandlesResponse {
  candles: Candle[]
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
  '1D': '1d',
  '1W': '1w',
  '1M': '1M'
}

// Limites dinâmicos baseados no timeframe
const getOptimalLimit = (interval: string): number => {
  const limits: Record<string, number> = {
    '1': 500,
    '3': 500,
    '5': 500,
    '15': 672,
    '30': 720,
    '60': 720,    // 1h = 30 dias
    '120': 720,   // 2h = 60 dias
    '240': 720,   // 4h = 120 dias
    '1D': 730,    // 1d = 2 anos
    '1W': 520,    // 1w = 10 anos
    '1M': 120     // 1M = 10 anos
  }
  return limits[interval] || 720
}

/**
 * Hook para buscar candles de um símbolo e intervalo específico
 */
export const useCandles = (symbol: string, interval: string) => {
  const apiInterval = intervalMap[interval] || interval
  const limit = getOptimalLimit(interval)

  return useQuery<CandlesResponse>({
    queryKey: ['candles', symbol, interval],
    queryFn: async () => {
      console.log(`🔥 useCandles: Fetching ${symbol} ${apiInterval} (limit: ${limit})`)

      const response = await fetch(
        `${API_URL}/api/v1/market/candles?symbol=${symbol}&interval=${apiInterval}&limit=${limit}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json'
          },
          credentials: 'include'
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch candles: ${response.statusText}`)
      }

      const data = await response.json()

      // Transformar timestamps para milissegundos se necessário
      const candles: Candle[] = (data.candles || data).map((candle: any) => ({
        time: candle.time < 10000000000 ? candle.time * 1000 : candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volume: candle.volume || 0
      }))

      console.log(`✅ useCandles: Loaded ${candles.length} candles for ${symbol}`)

      return {
        candles,
        symbol,
        interval: apiInterval,
        count: candles.length
      }
    },
    staleTime: 30000, // 30 segundos
    gcTime: 300000, // 5 minutos no cache
    refetchInterval: 60000, // Re-fetch a cada 1 minuto
    refetchOnWindowFocus: true,
    enabled: !!symbol && !!interval
  })
}
