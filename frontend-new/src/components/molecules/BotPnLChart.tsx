import React from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface PnLDataPoint {
  date: string
  daily_pnl: number
  cumulative_pnl: number
}

interface BotPnLChartProps {
  data: PnLDataPoint[]
  height?: number
}

export const BotPnLChart: React.FC<BotPnLChartProps> = ({ data, height = 200 }) => {
  // Format date for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  }

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const cumulativePnl = payload[0]?.value || 0
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-xs text-muted-foreground mb-1">{formatDate(label)}</p>
          <p className={`text-sm font-semibold ${cumulativePnl >= 0 ? 'text-success' : 'text-danger'}`}>
            P&L: {cumulativePnl >= 0 ? '+' : ''}${cumulativePnl.toFixed(2)}
          </p>
        </div>
      )
    }
    return null
  }

  // Determine if overall P&L is positive or negative
  const lastPnl = data.length > 0 ? data[data.length - 1].cumulative_pnl : 0
  const gradientColor = lastPnl >= 0 ? '#28a745' : '#ef4444'
  const strokeColor = lastPnl >= 0 ? '#28a745' : '#ef4444'

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <AreaChart
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={gradientColor} stopOpacity={0.3} />
              <stop offset="95%" stopColor={gradientColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2e39" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fill: '#a1a1aa', fontSize: 10 }}
            axisLine={{ stroke: '#2a2e39' }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tickFormatter={(value) => `$${value}`}
            tick={{ fill: '#a1a1aa', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="cumulative_pnl"
            stroke={strokeColor}
            strokeWidth={2}
            fill="url(#pnlGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
