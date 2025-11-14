/**
 * Hook para fazer prefetch de candles dos símbolos mais populares
 * Isso garante que quando o usuário clicar em BTC, ETH, BNB, etc
 * os dados já estarão no cache do backend
 */

import { useEffect, useRef } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'
const POPULAR_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
const DEFAULT_INTERVALS = ['1h', '4h']  // Intervalos mais comuns

// 📅 Limite dinâmico baseado no timeframe (mesmo que CustomChart)
const getOptimalLimit = (interval: string): number => {
  const limits: Record<string, number> = {
    '1m': 500,
    '3m': 500,
    '5m': 500,
    '15m': 672,
    '30m': 720,
    '1h': 720,
    '4h': 720,
    '1d': 730,
    '1w': 520,
    '1M': 120
  }
  return limits[interval] || 500
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