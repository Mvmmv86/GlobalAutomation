import { useState, useEffect, useCallback } from 'react'
import { binanceWebSocket, type TickerData } from '@/services/binanceWebSocket'

interface RealTimePriceData {
  symbol: string
  price: number
  priceChange: number
  priceChangePercent: number
  volume: number
  lastUpdate: Date
  isConnected: boolean
}

/**
 * Hook para obter preços em tempo real via WebSocket
 * @param symbol - Símbolo para monitorar (ex: 'BTCUSDT')
 * @param enabled - Se deve ativar o monitoramento (default: true)
 */
export const useRealTimePrice = (symbol: string, enabled: boolean = true) => {
  const [priceData, setPriceData] = useState<RealTimePriceData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const handlePriceUpdate = useCallback((tickerData: TickerData) => {
    setPriceData({
      symbol: tickerData.symbol,
      price: parseFloat(tickerData.price),
      priceChange: parseFloat(tickerData.priceChange),
      priceChangePercent: parseFloat(tickerData.priceChangePercent),
      volume: parseFloat(tickerData.volume),
      lastUpdate: new Date(tickerData.timestamp),
      isConnected: binanceWebSocket.isConnected()
    })

    setIsLoading(false)
    setError(null)
  }, [])

  useEffect(() => {
    if (!enabled || !symbol) {
      return
    }

    console.log(`📡 useRealTimePrice: Iniciando monitoramento de ${symbol}`)

    // Subscribe to price updates
    const unsubscribe = binanceWebSocket.subscribe(symbol, handlePriceUpdate)

    // Cleanup function
    return () => {
      console.log(`📡 useRealTimePrice: Parando monitoramento de ${symbol}`)
      unsubscribe()
    }
  }, [symbol, enabled, handlePriceUpdate])

  // Reset states when symbol changes or is disabled
  useEffect(() => {
    if (!enabled) {
      setPriceData(null)
      setIsLoading(false)
      setError(null)
    } else {
      setIsLoading(true)
      setError(null)
    }
  }, [symbol, enabled])

  return {
    priceData,
    isLoading,
    error,
    isConnected: binanceWebSocket.isConnected()
  }
}

/**
 * Hook para monitorar múltiplos símbolos simultaneamente
 * @param symbols - Array de símbolos para monitorar
 * @param enabled - Se deve ativar o monitoramento
 */
export const useRealTimePrices = (symbols: string[], enabled: boolean = true) => {
  const [pricesData, setPricesData] = useState<Map<string, RealTimePriceData>>(new Map())
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || symbols.length === 0) {
      setPricesData(new Map())
      setIsLoading(false)
      return
    }

    console.log(`📡 useRealTimePrices: Monitorando ${symbols.length} símbolos:`, symbols)

    const unsubscribeFunctions: (() => void)[] = []

    // Subscribe to each symbol
    symbols.forEach(symbol => {
      const unsubscribe = binanceWebSocket.subscribe(symbol, (tickerData: TickerData) => {
        setPricesData(prev => {
          const newMap = new Map(prev)
          newMap.set(symbol, {
            symbol: tickerData.symbol,
            price: parseFloat(tickerData.price),
            priceChange: parseFloat(tickerData.priceChange),
            priceChangePercent: parseFloat(tickerData.priceChangePercent),
            volume: parseFloat(tickerData.volume),
            lastUpdate: new Date(tickerData.timestamp),
            isConnected: binanceWebSocket.isConnected()
          })
          return newMap
        })

        setIsLoading(false)
        setError(null)
      })

      unsubscribeFunctions.push(unsubscribe)
    })

    // Cleanup function
    return () => {
      console.log(`📡 useRealTimePrices: Parando monitoramento de ${symbols.length} símbolos`)
      unsubscribeFunctions.forEach(unsubscribe => unsubscribe())
    }
  }, [symbols.join(','), enabled])

  return {
    pricesData,
    isLoading,
    error,
    isConnected: binanceWebSocket.isConnected(),
    getPriceData: (symbol: string) => pricesData.get(symbol) || null
  }
}