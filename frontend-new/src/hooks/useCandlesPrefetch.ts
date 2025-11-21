/**
 * Hook para fazer prefetch de candles dos símbolos mais populares
 * Isso garante que quando o usuário clicar em BTC, ETH, BNB, etc
 * os dados já estarão no cache do backend
 */

import { useEffect, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'
const POPULAR_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
const DEFAULT_INTERVALS = ['1h', '4h']  // Intervalos mais comuns

// 📅 Limite dinâmico baseado no timeframe - Max 1000 (limite da API Binance)
const getOptimalLimit = (interval: string): number => {
  const limits: Record<string, number> = {
    '1m': 1000,
    '3m': 1000,
    '5m': 1000,
    '15m': 1000,
    '30m': 1000,
    '1h': 1000,
    '2h': 1000,
    '4h': 1000,
    '6h': 1000,
    '8h': 1000,
    '12h': 1000,
    '1d': 1000,
    '3d': 1000,
    '1w': 1000,
    '1M': 500
  }
  return limits[interval] || 1000
}

export const useCandlesPrefetch = () => {
  const hasPrefetched = useRef(false)

  useEffect(() => {
    // Só fazer prefetch uma vez
    if (hasPrefetched.current) return
    hasPrefetched.current = true

    const prefetchCandles = async () => {
      console.log('🚀 Starting prefetch of popular symbols...')

      // Aguardar 2 segundos para não congestionar o carregamento inicial
      await new Promise(resolve => setTimeout(resolve, 2000))

      const prefetchPromises = []

      for (const symbol of POPULAR_SYMBOLS) {
        for (const interval of DEFAULT_INTERVALS) {
          const optimalLimit = getOptimalLimit(interval)

          // Criar promise de prefetch com limite dinâmico
          const promise = fetch(
            `${API_URL}/api/v1/market/candles?symbol=${symbol}&interval=${interval}&limit=${optimalLimit}`,
            { method: 'GET', cache: 'default' }
          )
            .then(() => {
              console.log(`✅ Prefetched ${symbol} ${interval}`)
            })
            .catch(err => {
              console.warn(`⚠️ Failed to prefetch ${symbol} ${interval}:`, err)
            })

          prefetchPromises.push(promise)

          // Adicionar pequeno delay entre requests para não sobrecarregar
          await new Promise(resolve => setTimeout(resolve, 100))
        }
      }

      // Aguardar todos os prefetches completarem
      await Promise.allSettled(prefetchPromises)
      console.log('✨ Prefetch complete! Popular symbols are now cached.')
    }

    // Executar prefetch em background
    prefetchCandles()
  }, [])
}