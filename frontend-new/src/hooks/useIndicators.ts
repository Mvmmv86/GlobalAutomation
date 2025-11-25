/**
 * useIndicators Hook - Gerencia estado e cálculo de indicadores técnicos
 * Para uso com CustomChart (lightweight-charts)
 */

import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import {
  indicatorEngine,
  IndicatorType,
  AnyIndicatorConfig,
  IndicatorResult,
  INDICATOR_PRESETS,
  INDICATOR_CATEGORIES,
  INDICATOR_NAMES,
  createIndicatorConfig,
  Candle
} from '@/utils/indicators'

export interface UseIndicatorsOptions {
  defaultIndicators?: IndicatorType[]
}

export interface UseIndicatorsReturn {
  // State
  indicators: AnyIndicatorConfig[]
  results: Map<string, IndicatorResult>
  isCalculating: boolean

  // Actions
  addIndicator: (type: IndicatorType, params?: Record<string, any>) => void
  removeIndicator: (id: string) => void
  toggleIndicator: (id: string) => void
  updateIndicatorParams: (id: string, params: Record<string, any>) => void
  updateIndicatorColor: (id: string, color: string) => void
  calculate: (candles: Candle[]) => Promise<void>
  clearAll: () => void

  // Helpers
  getOverlayIndicators: () => AnyIndicatorConfig[]
  getSeparateIndicators: () => AnyIndicatorConfig[]
  getIndicatorResult: (id: string) => IndicatorResult | undefined

  // Info
  availableIndicators: typeof INDICATOR_CATEGORIES
  indicatorNames: typeof INDICATOR_NAMES
}

export function useIndicators(options: UseIndicatorsOptions = {}): UseIndicatorsReturn {
  const { defaultIndicators = [] } = options

  // State
  const [indicators, setIndicators] = useState<AnyIndicatorConfig[]>(() => {
    return defaultIndicators.map(type => createIndicatorConfig(type))
  })
  const [results, setResults] = useState<Map<string, IndicatorResult>>(new Map())
  const [isCalculating, setIsCalculating] = useState(false)

  // Ref for cancellation
  const calculationRef = useRef<number>(0)

  // Add indicator
  const addIndicator = useCallback((type: IndicatorType, customParams?: Record<string, any>) => {
    const preset = INDICATOR_PRESETS[type]
    const newConfig = createIndicatorConfig(type, undefined, customParams ? { params: { ...preset.params, ...customParams } } : undefined)

    setIndicators(prev => [...prev, newConfig])
  }, [])

  // Remove indicator
  const removeIndicator = useCallback((id: string) => {
    setIndicators(prev => prev.filter(ind => ind.id !== id))
    setResults(prev => {
      const newMap = new Map(prev)
      newMap.delete(id)
      return newMap
    })
  }, [])

  // Toggle indicator enabled/disabled
  const toggleIndicator = useCallback((id: string) => {
    setIndicators(prev => prev.map(ind =>
      ind.id === id ? { ...ind, enabled: !ind.enabled } : ind
    ))
  }, [])

  // Update indicator parameters
  const updateIndicatorParams = useCallback((id: string, params: Record<string, any>) => {
    setIndicators(prev => prev.map(ind =>
      ind.id === id ? { ...ind, params: { ...ind.params, ...params } } as AnyIndicatorConfig : ind
    ))
  }, [])

  // Update indicator color
  const updateIndicatorColor = useCallback((id: string, color: string) => {
    setIndicators(prev => prev.map(ind =>
      ind.id === id ? { ...ind, color } : ind
    ))
  }, [])

  // Calculate all indicators
  const calculate = useCallback(async (candles: Candle[]) => {
    if (candles.length === 0) return

    const currentCalculation = ++calculationRef.current
    setIsCalculating(true)

    try {
      const enabledIndicators = indicators.filter(ind => ind.enabled)
      const calculatedResults = await indicatorEngine.calculateMultiple(enabledIndicators, candles)

      // Check if this calculation is still valid
      if (currentCalculation !== calculationRef.current) return

      const newResults = new Map<string, IndicatorResult>()
      calculatedResults.forEach(result => {
        newResults.set(result.id, result)
      })

      setResults(newResults)
    } catch (error) {
      console.error('Error calculating indicators:', error)
    } finally {
      if (currentCalculation === calculationRef.current) {
        setIsCalculating(false)
      }
    }
  }, [indicators])

  // Clear all indicators
  const clearAll = useCallback(() => {
    setIndicators([])
    setResults(new Map())
  }, [])

  // Get overlay indicators (displayed on main chart)
  const getOverlayIndicators = useCallback(() => {
    return indicators.filter(ind => ind.displayType === 'overlay' && ind.enabled)
  }, [indicators])

  // Get separate panel indicators (RSI, MACD, etc)
  const getSeparateIndicators = useCallback(() => {
    return indicators.filter(ind => ind.displayType === 'separate' && ind.enabled)
  }, [indicators])

  // Get specific indicator result
  const getIndicatorResult = useCallback((id: string) => {
    return results.get(id)
  }, [results])

  return {
    // State
    indicators,
    results,
    isCalculating,

    // Actions
    addIndicator,
    removeIndicator,
    toggleIndicator,
    updateIndicatorParams,
    updateIndicatorColor,
    calculate,
    clearAll,

    // Helpers
    getOverlayIndicators,
    getSeparateIndicators,
    getIndicatorResult,

    // Info
    availableIndicators: INDICATOR_CATEGORIES,
    indicatorNames: INDICATOR_NAMES
  }
}

// Hook for rendering indicators on lightweight-charts
export interface IndicatorSeriesData {
  time: number
  value: number
}

export interface PreparedIndicatorData {
  id: string
  type: string
  color: string
  lineWidth: number
  displayType: 'overlay' | 'separate'
  mainLine: IndicatorSeriesData[]
  additionalLines?: Record<string, IndicatorSeriesData[]>
}

export function useIndicatorData(
  results: Map<string, IndicatorResult>,
  indicators: AnyIndicatorConfig[],
  candles: Candle[]
): PreparedIndicatorData[] {
  return useMemo(() => {
    if (candles.length === 0) return []

    const prepared: PreparedIndicatorData[] = []

    indicators.forEach(config => {
      const result = results.get(config.id)
      if (!result || !config.enabled) return

      // Prepare main line data
      const mainLine: IndicatorSeriesData[] = []
      for (let i = 0; i < candles.length; i++) {
        const value = result.values[i]
        if (!isNaN(value) && value !== null && value !== undefined) {
          mainLine.push({
            time: candles[i].time,
            value
          })
        }
      }

      // Prepare additional lines
      const additionalLines: Record<string, IndicatorSeriesData[]> = {}
      if (result.additionalLines) {
        Object.entries(result.additionalLines).forEach(([key, values]) => {
          const lineData: IndicatorSeriesData[] = []
          for (let i = 0; i < candles.length; i++) {
            const value = values[i]
            if (!isNaN(value) && value !== null && value !== undefined) {
              lineData.push({
                time: candles[i].time,
                value
              })
            }
          }
          additionalLines[key] = lineData
        })
      }

      prepared.push({
        id: config.id,
        type: config.type,
        color: config.color,
        lineWidth: config.lineWidth,
        displayType: config.displayType,
        mainLine,
        additionalLines: Object.keys(additionalLines).length > 0 ? additionalLines : undefined
      })
    })

    return prepared
  }, [results, indicators, candles])
}

export default useIndicators
