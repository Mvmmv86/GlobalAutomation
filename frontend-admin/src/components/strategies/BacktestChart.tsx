/**
 * BacktestChart Component
 * Displays backtest results with candlestick chart, indicators, and trade markers
 */
import React, { useEffect, useRef, useMemo } from 'react'
import { createChart, IChartApi, ISeriesApi, SeriesMarker, Time } from 'lightweight-charts'
import {
  BacktestCandle,
  BacktestTrade,
  BacktestIndicators,
} from '@/services/strategyService'

interface BacktestChartProps {
  candles: BacktestCandle[]
  trades: BacktestTrade[]
  indicators: BacktestIndicators
  symbol: string
  height?: number
}

// Indicator color mapping - All 16 platform indicators supported
const INDICATOR_COLORS: Record<string, string> = {
  // EMAs and SMAs
  'ema.value': '#2962FF',
  'ema_cross.fast': '#26a69a',
  'ema_cross.slow': '#ef5350',
  // RSI
  'rsi.value': '#9c27b0',
  // MACD
  'macd.macd': '#2196f3',
  'macd.signal': '#ff9800',
  'macd.histogram': '#4caf50',
  // Bollinger
  'bollinger.upper': '#42a5f5',
  'bollinger.middle': '#78909c',
  'bollinger.lower': '#42a5f5',
  // SuperTrend
  'supertrend.value': '#ff5722',
  'supertrend.direction': '#ff5722',
  // Nadaraya-Watson
  'nadaraya_watson.upper': '#00bcd4',
  'nadaraya_watson.lower': '#00bcd4',
  'nadaraya_watson.value': '#00acc1',
  // Stochastic
  'stochastic.k': '#7c4dff',
  'stochastic.d': '#ff4081',
  'stochastic_rsi.k': '#7c4dff',
  'stochastic_rsi.d': '#ff4081',
  // ADX
  'adx.adx': '#ffc107',
  'adx.plus_di': '#4caf50',
  'adx.minus_di': '#f44336',
  // ATR
  'atr.value': '#ff7043',
  // VWAP
  'vwap.value': '#e91e63',
  'vwap.upper': '#f48fb1',
  'vwap.lower': '#f48fb1',
  // OBV (On Balance Volume)
  'obv.value': '#8bc34a',
  // Ichimoku
  'ichimoku.tenkan': '#2196f3',
  'ichimoku.kijun': '#f44336',
  'ichimoku.senkou_a': '#4caf50',
  'ichimoku.senkou_b': '#ff9800',
  'ichimoku.chikou': '#9c27b0',
  // TPO (Time Price Opportunity / Volume Profile)
  'tpo.poc': '#e91e63',      // Point of Control
  'tpo.vah': '#4caf50',      // Value Area High
  'tpo.val': '#f44336',      // Value Area Low
  'volume_profile.poc': '#e91e63',
  'volume_profile.vah': '#4caf50',
  'volume_profile.val': '#f44336',
  // Default
  default: '#888888',
}

// Indicators that should be displayed in separate panels (oscillators)
// These have different scales than price and should not overlay on candlesticks
const OSCILLATOR_INDICATORS = ['rsi', 'macd', 'stochastic', 'stochastic_rsi', 'adx', 'obv', 'atr']

export function BacktestChart({
  candles,
  trades,
  indicators,
  symbol,
  height = 500,
}: BacktestChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const indicatorSeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map())

  // Convert trades to markers with clear win/loss indication
  const tradeMarkers = useMemo((): SeriesMarker<Time>[] => {
    if (!trades || trades.length === 0) return []

    const markers: SeriesMarker<Time>[] = []

    trades.forEach((trade, index) => {
      const isProfitable = trade.pnl && trade.pnl > 0
      const isLoss = trade.pnl && trade.pnl < 0

      // Entry marker - color based on final result (win/loss)
      const entryTime = new Date(trade.entry_time).getTime() / 1000
      const entryColor = isProfitable ? '#00ff88' : isLoss ? '#ff4466' : '#ffaa00'

      markers.push({
        time: entryTime as Time,
        position: trade.signal_type === 'long' ? 'belowBar' : 'aboveBar',
        color: entryColor,
        shape: trade.signal_type === 'long' ? 'arrowUp' : 'arrowDown',
        text: `#${index + 1} ${trade.signal_type.toUpperCase()} @ $${trade.entry_price.toFixed(2)}`,
        size: 2,
      })

      // Exit marker with profit/loss highlight
      if (trade.exit_time && trade.exit_price) {
        const exitTime = new Date(trade.exit_time).getTime() / 1000
        const pnlText = trade.pnl_percent
          ? `${trade.pnl_percent >= 0 ? '+' : ''}${trade.pnl_percent.toFixed(2)}%`
          : ''
        const exitColor = isProfitable ? '#00ff88' : isLoss ? '#ff4466' : '#ffaa00'

        markers.push({
          time: exitTime as Time,
          position: trade.signal_type === 'long' ? 'aboveBar' : 'belowBar',
          color: exitColor,
          shape: isProfitable ? 'circle' : 'square',
          text: `EXIT ${pnlText}`,
          size: 2,
        })
      }
    })

    // Sort by time
    return markers.sort((a, b) => (a.time as number) - (b.time as number))
  }, [trades])

  // Calculate trade statistics
  const tradeStats = useMemo(() => {
    const wins = trades.filter((t) => t.pnl && t.pnl > 0).length
    const losses = trades.filter((t) => t.pnl && t.pnl < 0).length
    const totalPnl = trades.reduce((sum, t) => sum + (t.pnl || 0), 0)
    return { wins, losses, total: trades.length, totalPnl }
  }, [trades])

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current || candles.length === 0) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#131722' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
        horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          width: 1,
          color: 'rgba(224, 227, 235, 0.3)',
          style: 0,
        },
        horzLine: {
          width: 1,
          color: 'rgba(224, 227, 235, 0.3)',
          style: 0,
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(42, 46, 57, 1)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: 'rgba(42, 46, 57, 1)',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    // Create candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })

    candlestickSeriesRef.current = candlestickSeries

    // Set candle data
    const candleData = candles.map((c) => ({
      time: c.time as Time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }))
    candlestickSeries.setData(candleData)

    // Add markers for trades
    if (tradeMarkers.length > 0) {
      candlestickSeries.setMarkers(tradeMarkers)
    }

    // Add indicator series (overlay indicators only)
    const overlayIndicators = Object.entries(indicators).filter(([key]) => {
      const indicatorName = key.split('.')[0]
      return !OSCILLATOR_INDICATORS.includes(indicatorName)
    })

    overlayIndicators.forEach(([key, data]) => {
      if (!data || data.length === 0) return

      const color = INDICATOR_COLORS[key] || INDICATOR_COLORS.default
      const lineWidth = key.includes('bollinger') ? 1 : 2

      const lineSeries = chart.addLineSeries({
        color: color,
        lineWidth: lineWidth,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
      })

      const lineData = data.map((point) => ({
        time: point.time as Time,
        value: point.value,
      }))

      lineSeries.setData(lineData)
      indicatorSeriesRef.current.set(key, lineSeries)
    })

    // Fit content
    chart.timeScale().fitContent()

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      indicatorSeriesRef.current.clear()
      chart.remove()
      chartRef.current = null
      candlestickSeriesRef.current = null
    }
  }, [candles, indicators, height, tradeMarkers])

  // Legend for indicators
  const indicatorLegend = useMemo(() => {
    return Object.keys(indicators)
      .filter((key) => {
        const indicatorName = key.split('.')[0]
        return !OSCILLATOR_INDICATORS.includes(indicatorName)
      })
      .map((key) => ({
        name: key.replace('.', ' ').replace('_', ' '),
        color: INDICATOR_COLORS[key] || INDICATOR_COLORS.default,
      }))
  }, [indicators])

  if (candles.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-[#1e222d] rounded-lg">
        <p className="text-gray-500">Nenhum dado de candles disponivel</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Header with Legend */}
      <div className="bg-[#1e222d] rounded-lg p-3">
        {/* Indicators Legend */}
        {indicatorLegend.length > 0 && (
          <div className="mb-3">
            <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Indicadores</p>
            <div className="flex flex-wrap gap-3">
              {indicatorLegend.map((ind) => (
                <div key={ind.name} className="flex items-center gap-1.5 bg-[#131722] px-2 py-1 rounded">
                  <div
                    className="w-4 h-1 rounded"
                    style={{ backgroundColor: ind.color }}
                  />
                  <span className="text-xs text-gray-300 capitalize">{ind.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Trades Legend - Always visible */}
        <div>
          <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide">Sinais de Trade</p>
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-1.5 bg-[#131722] px-2 py-1 rounded">
              <div className="w-0 h-0 border-l-[5px] border-r-[5px] border-b-[7px] border-l-transparent border-r-transparent border-b-[#00ff88]" />
              <span className="text-xs text-gray-300">Long WIN</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#131722] px-2 py-1 rounded">
              <div className="w-0 h-0 border-l-[5px] border-r-[5px] border-b-[7px] border-l-transparent border-r-transparent border-b-[#ff4466]" />
              <span className="text-xs text-gray-300">Long LOSS</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#131722] px-2 py-1 rounded">
              <div className="w-0 h-0 border-l-[5px] border-r-[5px] border-t-[7px] border-l-transparent border-r-transparent border-t-[#00ff88]" />
              <span className="text-xs text-gray-300">Short WIN</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#131722] px-2 py-1 rounded">
              <div className="w-0 h-0 border-l-[5px] border-r-[5px] border-t-[7px] border-l-transparent border-r-transparent border-t-[#ff4466]" />
              <span className="text-xs text-gray-300">Short LOSS</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#131722] px-2 py-1 rounded">
              <div className="w-2.5 h-2.5 rounded-full bg-[#00ff88]" />
              <span className="text-xs text-gray-300">Exit WIN</span>
            </div>
            <div className="flex items-center gap-1.5 bg-[#131722] px-2 py-1 rounded">
              <div className="w-2.5 h-2.5 bg-[#ff4466]" />
              <span className="text-xs text-gray-300">Exit LOSS</span>
            </div>
          </div>
        </div>

        {/* Trade Statistics */}
        {tradeStats.total > 0 && (
          <div className="mt-3 pt-3 border-t border-[#2a2e39]">
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Total Trades:</span>
                <span className="text-white font-bold">{tradeStats.total}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Wins:</span>
                <span className="text-[#00ff88] font-bold">{tradeStats.wins}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Losses:</span>
                <span className="text-[#ff4466] font-bold">{tradeStats.losses}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">Win Rate:</span>
                <span className={`font-bold ${tradeStats.wins / tradeStats.total >= 0.5 ? 'text-[#00ff88]' : 'text-[#ff4466]'}`}>
                  {((tradeStats.wins / tradeStats.total) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-500">P&L:</span>
                <span className={`font-bold ${tradeStats.totalPnl >= 0 ? 'text-[#00ff88]' : 'text-[#ff4466]'}`}>
                  {tradeStats.totalPnl >= 0 ? '+' : ''}{tradeStats.totalPnl.toFixed(2)} USDT
                </span>
              </div>
            </div>
          </div>
        )}

        {tradeStats.total === 0 && (
          <div className="mt-3 pt-3 border-t border-[#2a2e39]">
            <p className="text-yellow-500 text-sm">
              Nenhum trade executado neste periodo. Verifique se a estrategia tem indicadores e condicoes configurados.
            </p>
          </div>
        )}
      </div>

      {/* Chart */}
      <div
        ref={chartContainerRef}
        className="w-full rounded-lg overflow-hidden border border-[#2a2e39]"
      />

      {/* Period Info */}
      <div className="flex justify-between px-2 text-xs text-gray-500">
        <span>Candles: {candles.length}</span>
        <span>{symbol}</span>
      </div>
    </div>
  )
}
