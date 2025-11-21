/**
 * Hook para buscar dados de candles para o CanvasChart
 * Utiliza React Query para cache e auto-refetch
 * FONTE: API PÚBLICA da Binance (sem autenticação necessária)
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
  market_type?: string
  source?: string
}

// Mapeamento de intervalos minutos para formato da API (Binance supported intervals)
// Binance suporta: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
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

// Limites dinâmicos baseados no timeframe - Backend suporta até 20000 via paginação
// Otimizado para histórico profissional MÁXIMO (anos de dados)
const getOptimalLimit = (interval: string): number => {
  const limits: Record<string, number> = {
    '1': 5000,    // 1m = ~3.5 dias
    '3': 8000,    // 3m = ~16 dias
    '5': 10000,   // 5m = ~35 dias
    '15': 15000,  // 15m = ~156 dias (~5 meses)
    '30': 15000,  // 30m = ~312 dias (~10 meses)
    '60': 15000,  // 1h = ~625 dias (~1.7 anos)
    '120': 10000, // 2h = ~833 dias (~2.3 anos)
    '240': 8000,  // 4h = ~1333 dias (~3.6 anos)
    '360': 6000,  // 6h = ~1500 dias (~4.1 anos)
    '480': 5000,  // 8h = ~1666 dias (~4.5 anos)
    '720': 4000,  // 12h = ~2000 dias (~5.4 anos)
    '1D': 3000,   // 1d = ~8.2 anos (todo histórico)
    '3D': 2000,   // 3d = ~16 anos
    '1W': 1000,   // 1w = ~19 anos
    '1M': 500     // 1M = ~41 anos
  }
  return limits[interval] || 10000
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
    staleTime: 5000, // 5 segundos - dados ficam stale rapidamente para real-time
    gcTime: 300000, // 5 minutos no cache
    refetchInterval: 10000, // Re-fetch a cada 10 segundos para real-time updates
    refetchOnWindowFocus: true,
    enabled: !!symbol && !!interval
  })
}
