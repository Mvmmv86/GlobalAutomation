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

// Limites dinâmicos baseados no timeframe - OTIMIZADO PARA PERFORMANCE
// Reduzido para garantir carregamento rápido em todos os timeframes
const getOptimalLimit = (interval: string): number => {
  const limits: Record<string, number> = {
    '1': 2000,    // 1m = ~1.4 dias
    '3': 2000,    // 3m = ~4 dias
    '5': 2000,    // 5m = ~7 dias
    '15': 2000,   // 15m = ~21 dias
    '30': 2000,   // 30m = ~42 dias
    '60': 2000,   // 1h = ~83 dias
    '120': 1500,  // 2h = ~125 dias
    '240': 1000,  // 4h = ~166 dias
    '360': 1000,  // 6h = ~250 dias
    '480': 800,   // 8h = ~266 dias
    '720': 500,   // 12h = ~250 dias (REDUZIDO)
    '1D': 365,    // 1d = ~1 ano (REDUZIDO)
    '3D': 240,    // 3d = ~2 anos (REDUZIDO)
    '1W': 104,    // 1w = ~2 anos (REDUZIDO)
    '1M': 48      // 1M = ~4 anos (REDUZIDO)
  }
  return limits[interval] || 1000
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
      const startTime = Date.now()
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
        const errorText = await response.text()
        console.error(`❌ useCandles ERROR: ${response.status} ${response.statusText}`, errorText)
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

      const elapsed = Date.now() - startTime
      console.log(`✅ useCandles: Loaded ${candles.length} candles for ${symbol} in ${elapsed}ms`)

      return {
        candles,
        symbol,
        interval: apiInterval,
        count: candles.length
      }
    },
    // 🚀 RATE LIMIT FIX: Increased from 5s/10s to 15s/30s to reduce API calls
    staleTime: 15000, // 15 segundos (was 5s)
    gcTime: 300000, // 5 minutos no cache
    refetchInterval: 30000, // Re-fetch a cada 30 segundos (was 10s)
    refetchOnWindowFocus: true,
    enabled: !!symbol && !!interval,
    retry: 2, // Tentar apenas 2 vezes em caso de erro
    retryDelay: 1000 // Esperar 1s entre tentativas
  })
}
