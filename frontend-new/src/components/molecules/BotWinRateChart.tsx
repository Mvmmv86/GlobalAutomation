import React from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts'

interface WinRateDataPoint {
  date: string
  daily_wins: number
  daily_losses: number
  win_rate: number
}

interface BotWinRateChartProps {
  data: WinRateDataPoint[]
  totalWins: number
  totalLosses: number
  height?: number
  variant?: 'bar' | 'pie'
}

export const BotWinRateChart: React.FC<BotWinRateChartProps> = ({
  data,
  totalWins,
  totalLosses,
  height = 200,
  variant = 'pie'
}) => {
  // Pie chart data
  const pieData = [
    { name: 'Vitórias', value: totalWins, color: '#28a745' },
    { name: 'Derrotas', value: totalLosses, color: '#ef4444' },
  ]

  // Format date for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
  }

  // Custom tooltip for bar chart
  const BarTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-xs text-muted-foreground mb-1">{formatDate(label)}</p>
          <p className="text-sm text-success">Vitórias: {payload[0]?.value || 0}</p>
          <p className="text-sm text-danger">Derrotas: {payload[1]?.value || 0}</p>
        </div>
      )
    }
    return null
  }

  // Custom tooltip for pie chart
  const PieTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
          <p className="text-sm font-semibold" style={{ color: data.payload.color }}>
            {data.name}: {data.value}
          </p>
        </div>
      )
    }
    return null
  }

  // Calculate win rate percentage
  const total = totalWins + totalLosses
  const winRatePercentage = total > 0 ? ((totalWins / total) * 100).toFixed(1) : '0'

  if (variant === 'pie') {
    return (
      <div style={{ width: '100%', height }} className="flex items-center justify-center">
        <div className="relative">
          <ResponsiveContainer width={height} height={height}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={height * 0.25}
                outerRadius={height * 0.4}
                paddingAngle={2}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<PieTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-foreground">{winRatePercentage}%</span>
            <span className="text-xs text-muted-foreground">Win Rate</span>
          </div>
        </div>
        {/* Legend */}
        <div className="ml-4 space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-success"></div>
            <span className="text-sm text-muted-foreground">Vitórias: {totalWins}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-danger"></div>
            <span className="text-sm text-muted-foreground">Derrotas: {totalLosses}</span>
          </div>
        </div>
      </div>
    )
  }

  // Bar chart variant
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2e39" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fill: '#a1a1aa', fontSize: 10 }}
            axisLine={{ stroke: '#2a2e39' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#a1a1aa', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={30}
          />
          <Tooltip content={<BarTooltip />} />
          <Bar dataKey="daily_wins" fill="#28a745" stackId="stack" radius={[4, 4, 0, 0]} />
          <Bar dataKey="daily_losses" fill="#ef4444" stackId="stack" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
