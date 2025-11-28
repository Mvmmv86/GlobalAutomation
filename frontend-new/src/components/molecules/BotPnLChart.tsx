import React, { useMemo, useState, useCallback, useEffect } from 'react'
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  Brush,
  ReferenceArea,
} from 'recharts'
import { ZoomIn, ZoomOut, RotateCcw, Move } from 'lucide-react'

interface PnLDataPoint {
  date: string
  daily_pnl: number
  cumulative_pnl: number
  daily_trades?: number
  cumulative_trades?: number
  daily_wins?: number
  daily_losses?: number
}

interface BotPnLChartProps {
  data: PnLDataPoint[]
  height?: number
  showTrades?: boolean
}

// Format large numbers with K, M suffix
const formatCurrency = (value: number): string => {
  const absValue = Math.abs(value)
  if (absValue >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  }
  if (absValue >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`
  }
  if (absValue >= 100) {
    return `$${value.toFixed(0)}`
  }
  return `$${value.toFixed(2)}`
}

// Format currency for tooltip (more detailed)
const formatCurrencyDetailed = (value: number): string => {
  const absValue = Math.abs(value)
  const sign = value >= 0 ? '+' : ''
  if (absValue >= 1000000) {
    return `${sign}$${(value / 1000000).toFixed(2)}M`
  }
  if (absValue >= 10000) {
    return `${sign}$${(value / 1000).toFixed(1)}K`
  }
  return `${sign}$${value.toFixed(2)}`
}

export const BotPnLChart: React.FC<BotPnLChartProps> = ({ data, height = 300, showTrades = true }) => {
  // Zoom state
  const [zoomLevel, setZoomLevel] = useState(1)
  const [dataStartIndex, setDataStartIndex] = useState(0)
  const [dataEndIndex, setDataEndIndex] = useState(data.length - 1)
  const [refAreaLeft, setRefAreaLeft] = useState<string | null>(null)
  const [refAreaRight, setRefAreaRight] = useState<string | null>(null)
  const [isSelecting, setIsSelecting] = useState(false)

  // Reset zoom when data changes (e.g., when filter period changes)
  useEffect(() => {
    setDataStartIndex(0)
    setDataEndIndex(data.length - 1)
    setZoomLevel(1)
  }, [data.length])

  // Format date for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  }

  // Get visible data based on zoom
  const visibleData = useMemo(() => {
    if (data.length === 0) return []
    const start = Math.max(0, dataStartIndex)
    const end = Math.min(data.length - 1, dataEndIndex)
    return data.slice(start, end + 1)
  }, [data, dataStartIndex, dataEndIndex])

  // Calculate min/max values for dynamic Y-axis domain based on VISIBLE data
  // IMPORTANT: This recalculates on every zoom change (dataStartIndex/dataEndIndex change)
  const { minPnl, maxPnl, hasTrades, lastPnl, hasData, dataRange } = useMemo(() => {
    // Log for debugging
    console.log('[BotPnLChart] Recalculating Y-axis domain for visible range:', dataStartIndex, '-', dataEndIndex, 'points:', visibleData.length)

    if (visibleData.length === 0) {
      return { minPnl: -100, maxPnl: 100, hasTrades: false, lastPnl: 0, hasData: false, dataRange: 200 }
    }

    const pnlValues = visibleData.map(d => d.cumulative_pnl)
    const min = Math.min(...pnlValues)
    const max = Math.max(...pnlValues)
    const hasTradesData = visibleData.some(d => (d.cumulative_trades || 0) > 0)
    const last = visibleData[visibleData.length - 1].cumulative_pnl

    console.log('[BotPnLChart] Visible P&L range:', min, 'to', max)

    // Check if all values are zero or nearly zero
    const allZero = pnlValues.every(v => Math.abs(v) < 0.01)

    if (allZero) {
      return {
        minPnl: -100,
        maxPnl: 100,
        hasTrades: hasTradesData,
        lastPnl: 0,
        hasData: false,
        dataRange: 200
      }
    }

    // Calculate range for dynamic scaling
    const absMax = Math.max(Math.abs(min), Math.abs(max))

    // RESPONSIVE SCALE: Choose step based on ACTUAL data range, not fixed thresholds
    let scaleStep: number
    if (absMax >= 100000) {
      scaleStep = 25000 // $25K steps
    } else if (absMax >= 50000) {
      scaleStep = 10000 // $10K steps
    } else if (absMax >= 10000) {
      scaleStep = 2500 // $2.5K steps
    } else if (absMax >= 5000) {
      scaleStep = 1000 // $1K steps
    } else if (absMax >= 1000) {
      scaleStep = 250 // $250 steps
    } else if (absMax >= 500) {
      scaleStep = 100 // $100 steps
    } else if (absMax >= 100) {
      scaleStep = 25 // $25 steps
    } else if (absMax >= 50) {
      scaleStep = 10 // $10 steps
    } else if (absMax >= 10) {
      scaleStep = 5 // $5 steps
    } else if (absMax >= 1) {
      scaleStep = 1 // $1 steps
    } else {
      scaleStep = 0.5 // $0.50 steps for very small values
    }

    // Round min/max to nice values
    const niceMin = Math.floor(min / scaleStep) * scaleStep
    const niceMax = Math.ceil(max / scaleStep) * scaleStep

    // Add padding (one step on each side)
    const finalMin = niceMin - scaleStep
    const finalMax = niceMax + scaleStep

    console.log('[BotPnLChart] Y-axis domain:', finalMin, 'to', finalMax)

    // Ensure 0 is always included in the range
    return {
      minPnl: Math.min(finalMin, 0),
      maxPnl: Math.max(finalMax, 0),
      hasTrades: hasTradesData,
      lastPnl: last,
      hasData: true,
      dataRange: Math.abs(finalMax - finalMin)
    }
  }, [visibleData, dataStartIndex, dataEndIndex])

  // Zoom functions
  const zoomIn = useCallback(() => {
    if (data.length < 4) return
    const range = dataEndIndex - dataStartIndex
    const newRange = Math.max(3, Math.floor(range * 0.6))
    const center = Math.floor((dataStartIndex + dataEndIndex) / 2)
    const newStart = Math.max(0, center - Math.floor(newRange / 2))
    const newEnd = Math.min(data.length - 1, newStart + newRange)
    setDataStartIndex(newStart)
    setDataEndIndex(newEnd)
    setZoomLevel(prev => prev * 1.5)
  }, [data.length, dataStartIndex, dataEndIndex])

  const zoomOut = useCallback(() => {
    const range = dataEndIndex - dataStartIndex
    const newRange = Math.min(data.length - 1, Math.floor(range * 1.5))
    const center = Math.floor((dataStartIndex + dataEndIndex) / 2)
    const newStart = Math.max(0, center - Math.floor(newRange / 2))
    const newEnd = Math.min(data.length - 1, newStart + newRange)
    setDataStartIndex(newStart)
    setDataEndIndex(newEnd)
    setZoomLevel(prev => Math.max(1, prev / 1.5))
  }, [data.length, dataStartIndex, dataEndIndex])

  const resetZoom = useCallback(() => {
    setDataStartIndex(0)
    setDataEndIndex(data.length - 1)
    setZoomLevel(1)
  }, [data.length])

  // Mouse handlers for drag-to-zoom
  const handleMouseDown = useCallback((e: any) => {
    if (e?.activeLabel) {
      setRefAreaLeft(e.activeLabel)
      setIsSelecting(true)
    }
  }, [])

  const handleMouseMove = useCallback((e: any) => {
    if (isSelecting && e?.activeLabel) {
      setRefAreaRight(e.activeLabel)
    }
  }, [isSelecting])

  const handleMouseUp = useCallback(() => {
    if (refAreaLeft && refAreaRight && refAreaLeft !== refAreaRight) {
      // Find indices
      const leftIndex = data.findIndex(d => d.date === refAreaLeft)
      const rightIndex = data.findIndex(d => d.date === refAreaRight)

      if (leftIndex !== -1 && rightIndex !== -1) {
        const start = Math.min(leftIndex, rightIndex)
        const end = Math.max(leftIndex, rightIndex)
        if (end - start >= 2) {
          setDataStartIndex(start)
          setDataEndIndex(end)
          setZoomLevel(data.length / (end - start + 1))
        }
      }
    }
    setRefAreaLeft(null)
    setRefAreaRight(null)
    setIsSelecting(false)
  }, [refAreaLeft, refAreaRight, data])

  // Brush change handler
  const handleBrushChange = useCallback((brushData: any) => {
    if (brushData && typeof brushData.startIndex === 'number' && typeof brushData.endIndex === 'number') {
      setDataStartIndex(brushData.startIndex)
      setDataEndIndex(brushData.endIndex)
      const range = brushData.endIndex - brushData.startIndex + 1
      setZoomLevel(data.length / range)
    }
  }, [data.length])

  // Custom tooltip with improved styling
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const pnlData = payload.find((p: any) => p.dataKey === 'cumulative_pnl')
      const dailyPnlData = payload.find((p: any) => p.dataKey === 'daily_pnl')
      const tradesData = payload.find((p: any) => p.dataKey === 'cumulative_trades')
      const dailyTradesData = payload.find((p: any) => p.dataKey === 'daily_trades')

      const cumulativePnl = pnlData?.value || 0
      const dailyPnl = dailyPnlData?.value || payload[0]?.payload?.daily_pnl || 0
      const cumulativeTrades = tradesData?.value || 0
      const dailyTrades = dailyTradesData?.value || payload[0]?.payload?.daily_trades || 0

      return (
        <div className="bg-card/95 backdrop-blur-sm border border-border rounded-lg p-3 shadow-xl">
          <p className="text-xs font-medium text-foreground mb-2 border-b border-border pb-1">
            {formatDate(label)}
          </p>
          <div className="space-y-1">
            <div className="flex justify-between gap-4">
              <span className="text-xs text-muted-foreground">P&L Total:</span>
              <span className={`text-sm font-bold ${cumulativePnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                {formatCurrencyDetailed(cumulativePnl)}
              </span>
            </div>
            {dailyPnl !== 0 && (
              <div className="flex justify-between gap-4">
                <span className="text-xs text-muted-foreground">P&L Dia:</span>
                <span className={`text-xs font-medium ${dailyPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrencyDetailed(dailyPnl)}
                </span>
              </div>
            )}
            {showTrades && cumulativeTrades > 0 && (
              <>
                <div className="flex justify-between gap-4">
                  <span className="text-xs text-muted-foreground">Trades Total:</span>
                  <span className="text-xs font-medium text-blue-400">{cumulativeTrades}</span>
                </div>
                {dailyTrades > 0 && (
                  <div className="flex justify-between gap-4">
                    <span className="text-xs text-muted-foreground">Trades Dia:</span>
                    <span className="text-xs font-medium text-blue-300">{dailyTrades}</span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  // Determine colors based on P&L
  const isProfit = lastPnl >= 0
  const primaryColor = isProfit ? '#22c55e' : '#ef4444'

  // Generate unique gradient ID to avoid conflicts
  const gradientId = useMemo(() => `pnlGradient-${Math.random().toString(36).substr(2, 9)}`, [])

  return (
    <div style={{ width: '100%', height: height + 50 }} className="relative">
      {/* Zoom Controls */}
      <div className="absolute top-0 right-0 z-10 flex items-center gap-1 bg-card/80 backdrop-blur-sm rounded-lg p-1 border border-border">
        <button
          onClick={zoomIn}
          className="p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          title="Zoom In (ver detalhes)"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={zoomOut}
          className="p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          title="Zoom Out (ver mais)"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={resetZoom}
          className="p-1.5 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
          title="Reset Zoom"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        {zoomLevel > 1 && (
          <span className="text-xs text-muted-foreground px-1">
            {zoomLevel.toFixed(1)}x
          </span>
        )}
      </div>

      {/* Drag hint */}
      {data.length > 5 && (
        <div className="absolute top-0 left-0 z-10 flex items-center gap-1 text-xs text-muted-foreground/60 bg-card/60 rounded px-2 py-1">
          <Move className="w-3 h-3" />
          <span>Arraste para selecionar</span>
        </div>
      )}

      {/* Summary badge */}
      {visibleData.length > 0 && hasData && (
        <div className="absolute top-8 left-0 z-10 flex items-center gap-2">
          <div
            className={`px-2 py-1 rounded text-xs font-bold ${
              isProfit
                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }`}
          >
            {formatCurrencyDetailed(lastPnl)}
          </div>
          <div className="text-xs text-muted-foreground">
            {visibleData.length} dias
          </div>
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        {/* KEY forces complete re-render when domain changes - this is the fix for Y-axis not updating */}
        <ComposedChart
          key={`chart-${dataStartIndex}-${dataEndIndex}-${minPnl}-${maxPnl}`}
          data={visibleData}
          margin={{ top: 40, right: showTrades && hasTrades ? 60 : 20, left: 10, bottom: 5 }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          <defs>
            {/* Main gradient for P&L area */}
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={primaryColor} stopOpacity={0.4} />
              <stop offset="50%" stopColor={primaryColor} stopOpacity={0.15} />
              <stop offset="100%" stopColor={primaryColor} stopOpacity={0} />
            </linearGradient>
            {/* Glow filter for the line */}
            <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>

          {/* Grid lines */}
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#374151"
            vertical={false}
            opacity={0.5}
          />

          {/* Zero reference line */}
          <ReferenceLine
            y={0}
            yAxisId="pnl"
            stroke="#6b7280"
            strokeDasharray="5 5"
            strokeWidth={1}
          />

          {/* Selection area for zoom */}
          {refAreaLeft && refAreaRight && (
            <ReferenceArea
              yAxisId="pnl"
              x1={refAreaLeft}
              x2={refAreaRight}
              strokeOpacity={0.3}
              fill="#3b82f6"
              fillOpacity={0.2}
            />
          )}

          {/* X-Axis (dates) */}
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={{ stroke: '#374151' }}
            interval="preserveStartEnd"
            minTickGap={40}
          />

          {/* Y-Axis for P&L (left) - RESPONSIVE TO DATA
              KEY forces Recharts to re-render Y-axis when domain changes */}
          <YAxis
            key={`pnl-axis-${minPnl}-${maxPnl}`}
            yAxisId="pnl"
            orientation="left"
            domain={[minPnl, maxPnl]}
            tickFormatter={formatCurrency}
            tick={{ fill: '#9ca3af', fontSize: 11 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={{ stroke: '#374151' }}
            width={70}
            tickCount={7}
            allowDataOverflow={false}
          />

          {/* Y-Axis for Trades (right) */}
          {showTrades && hasTrades && (
            <YAxis
              yAxisId="trades"
              orientation="right"
              tick={{ fill: '#60a5fa', fontSize: 11 }}
              axisLine={{ stroke: '#374151' }}
              tickLine={{ stroke: '#374151' }}
              width={45}
              tickCount={5}
            />
          )}

          {/* Tooltip */}
          <Tooltip content={<CustomTooltip />} />

          {/* Legend */}
          {showTrades && hasTrades && (
            <Legend
              verticalAlign="top"
              align="right"
              height={30}
              iconType="line"
              wrapperStyle={{ top: 5, right: 70 }}
              formatter={(value: string) => {
                if (value === 'cumulative_pnl') return <span className="text-xs text-gray-400">P&L</span>
                if (value === 'cumulative_trades') return <span className="text-xs text-blue-400">Trades</span>
                return value
              }}
            />
          )}

          {/* P&L Area with gradient */}
          <Area
            yAxisId="pnl"
            type="monotone"
            dataKey="cumulative_pnl"
            stroke={primaryColor}
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            name="cumulative_pnl"
            dot={visibleData.length <= 30}
            activeDot={{
              r: 6,
              fill: primaryColor,
              stroke: '#1f2937',
              strokeWidth: 2
            }}
            style={{ filter: 'url(#glow)' }}
          />

          {/* Trades Line */}
          {showTrades && hasTrades && (
            <Line
              yAxisId="trades"
              type="monotone"
              dataKey="cumulative_trades"
              stroke="#60a5fa"
              strokeWidth={2}
              dot={false}
              name="cumulative_trades"
              activeDot={{
                r: 5,
                fill: '#60a5fa',
                stroke: '#1f2937',
                strokeWidth: 2
              }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Brush slider for navigation */}
      {data.length > 7 && (
        <div className="px-4 -mt-2">
          <ResponsiveContainer width="100%" height={40}>
            <ComposedChart data={data} margin={{ top: 0, right: 20, left: 10, bottom: 0 }}>
              <Brush
                dataKey="date"
                height={30}
                stroke="#374151"
                fill="#1f2937"
                tickFormatter={formatDate}
                startIndex={dataStartIndex}
                endIndex={dataEndIndex}
                onChange={handleBrushChange}
              >
                <ComposedChart data={data}>
                  <Area
                    type="monotone"
                    dataKey="cumulative_pnl"
                    stroke={primaryColor}
                    fill={primaryColor}
                    fillOpacity={0.3}
                  />
                </ComposedChart>
              </Brush>
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* No data message */}
      {!hasData && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-muted-foreground text-sm">Sem dados de P&L ainda</p>
            <p className="text-muted-foreground/60 text-xs mt-1">Os dados aparecerão quando houver trades fechados</p>
          </div>
        </div>
      )}
    </div>
  )
}
