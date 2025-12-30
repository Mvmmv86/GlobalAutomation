/**
 * StrategyDetailsModal Component
 * Modal with tabs for viewing strategy details, signals, chart and metrics
 */
import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  X,
  Info,
  BarChart3,
  LineChart,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Zap,
  Target,
  Loader2,
  Filter,
  Download,
  RefreshCw,
} from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import {
  strategyService,
  StrategyWithRelations,
  StrategySignal,
  StrategyMetrics,
  StrategyMetricsResponse,
  StrategyChartData,
  INDICATOR_TYPES,
} from '@/services/strategyService'
import { BacktestChart } from './BacktestChart'
import { format } from 'date-fns'

// Helper to format date simply
const formatDateTime = (dateStr: string): string => {
  try {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return '-'
    // Format: DD/MM/YY HH:mm:ss
    return format(date, 'dd/MM/yy HH:mm:ss')
  } catch (e) {
    console.error('Date format error:', e)
    return '-'
  }
}

// ============================================================================
// Types
// ============================================================================

interface StrategyDetailsModalProps {
  strategyId: string
  onClose: () => void
}

type TabType = 'info' | 'signals' | 'chart' | 'metrics'

interface StrategyMetrics {
  symbol: string
  win_rate: number
  total_pnl: number
  sharpe_ratio: number
  max_drawdown: number
  btc_correlation: number
  total_signals: number
  executed_signals: number
  failed_signals: number
  winning_signals: number
  losing_signals: number
  avg_pnl_per_trade: number
  best_trade: number
  worst_trade: number
  profit_factor: number
}

// Period filter options
const PERIOD_OPTIONS = [
  { value: 7, label: '7 dias' },
  { value: 30, label: '30 dias' },
  { value: 90, label: '90 dias' },
  { value: 180, label: '6 meses' },
  { value: 365, label: '1 ano' },
]

// Timeframe options for chart
const TIMEFRAME_OPTIONS = [
  { value: '5m', label: '5 min' },
  { value: '15m', label: '15 min' },
  { value: '30m', label: '30 min' },
  { value: '1h', label: '1 hora' },
  { value: '2h', label: '2 horas' },
  { value: '4h', label: '4 horas' },
  { value: '1d', label: '1 dia' },
  { value: '1w', label: '1 semana' },
  { value: '1M', label: '1 mês' },
]

// ============================================================================
// Tooltip Component
// ============================================================================

interface InfoTooltipProps {
  text: string
}

const InfoTooltip: React.FC<InfoTooltipProps> = ({ text }) => {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="relative inline-flex items-center flex-shrink-0">
      <button
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={(e) => {
          e.stopPropagation()
          setIsVisible(!isVisible)
        }}
        className="text-gray-500 hover:text-gray-400 transition-colors p-0.5"
      >
        <Info className="w-3 h-3" />
      </button>
      {isVisible && (
        <div className="absolute z-50 bottom-full right-0 mb-2 w-48 p-2 bg-[#1e222d] border border-[#2a2e39] rounded-lg shadow-lg text-xs text-gray-300 whitespace-normal">
          <div className="relative">
            {text}
            <div className="absolute top-full right-2 border-4 border-transparent border-t-[#2a2e39]" />
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Tab Components
// ============================================================================

// Tab 1: Strategy Info
function StrategyInfoTab({ strategy }: { strategy: StrategyWithRelations }) {
  const getIndicatorLabel = (type: string): string => {
    const indicator = INDICATOR_TYPES.find(i => i.value === type)
    return indicator?.label || type
  }

  const symbols = Array.isArray(strategy.symbols) ? strategy.symbols : []

  return (
    <div className="space-y-6">
      {/* Config Info */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-[#131722] rounded-lg">
          <p className="text-xs text-gray-400 mb-1">Tipo de Configuracao</p>
          <p className="text-white font-medium">{strategy.config_type}</p>
        </div>
        <div className="p-4 bg-[#131722] rounded-lg">
          <p className="text-xs text-gray-400 mb-1">Timeframe</p>
          <p className="text-white font-medium">{strategy.timeframe}</p>
        </div>
      </div>

      {/* Symbols */}
      <div>
        <p className="text-sm text-gray-400 mb-2">Simbolos Monitorados</p>
        <div className="flex flex-wrap gap-2">
          {symbols.length > 0 ? (
            symbols.map((symbol: string, idx: number) => (
              <Badge key={idx} variant="default" className="bg-blue-500/20 text-blue-300">
                {symbol}
              </Badge>
            ))
          ) : (
            <span className="text-gray-500">Nenhum simbolo configurado</span>
          )}
        </div>
      </div>

      {/* Indicators */}
      <div>
        <p className="text-sm text-gray-400 mb-2">Indicadores ({strategy.indicators?.length || 0})</p>
        {strategy.indicators && strategy.indicators.length > 0 ? (
          <div className="space-y-2">
            {strategy.indicators.map((ind) => (
              <div key={ind.id} className="p-3 bg-[#131722] rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-emerald-400 font-medium">{getIndicatorLabel(ind.indicator_type)}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Parametros: {JSON.stringify(ind.parameters)}
                    </p>
                  </div>
                  <Badge variant="default" className="text-xs">#{ind.order_index}</Badge>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Nenhum indicador configurado</p>
        )}
      </div>

      {/* Conditions */}
      <div>
        <p className="text-sm text-gray-400 mb-2">Condicoes ({strategy.conditions?.length || 0})</p>
        {strategy.conditions && strategy.conditions.length > 0 ? (
          <div className="space-y-2">
            {strategy.conditions.map((cond) => (
              <div key={cond.id} className="p-3 bg-[#131722] rounded-lg">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-purple-400 font-medium">
                      {cond.condition_type.replace('_', ' ').toUpperCase()}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Operador: {cond.logic_operator} | Regras: {cond.conditions?.length || 0}
                    </p>
                    {cond.conditions && cond.conditions.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {cond.conditions.map((rule, idx) => (
                          <p key={idx} className="text-xs text-gray-300 font-mono">
                            {rule.left} {rule.operator} {rule.right}
                          </p>
                        ))}
                      </div>
                    )}
                  </div>
                  <Badge variant="default" className="text-xs">#{cond.order_index}</Badge>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Nenhuma condicao configurada</p>
        )}
      </div>

      {/* YAML Config */}
      {strategy.config_yaml && (
        <div>
          <p className="text-sm text-gray-400 mb-2">Configuracao YAML</p>
          <pre className="p-3 bg-[#131722] rounded-lg text-xs text-gray-300 overflow-x-auto max-h-48 overflow-y-auto">
            {strategy.config_yaml}
          </pre>
        </div>
      )}
    </div>
  )
}

// Tab 2: Signals & Execution
function SignalsTab({ strategyId }: { strategyId: string }) {
  const [selectedDays, setSelectedDays] = useState(30)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data: signals, isLoading, refetch } = useQuery({
    queryKey: ['strategy-signals', strategyId, selectedDays],
    queryFn: () => strategyService.getSignals(strategyId, { limit: 100 }),
  })

  const filteredSignals = useMemo(() => {
    if (!signals || !Array.isArray(signals)) {
      console.log('SignalsTab: No signals or not array', signals)
      return []
    }

    console.log('SignalsTab: Raw signals count:', signals.length)

    let filtered = [...signals]

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter(s => s.status === statusFilter)
    }

    // Filter by date
    const cutoffDate = new Date()
    cutoffDate.setDate(cutoffDate.getDate() - selectedDays)

    // Debug: log first signal date
    if (filtered.length > 0) {
      const firstSignal = filtered[0]
      const testDate = new Date(firstSignal.created_at)
      console.log('SignalsTab: First signal created_at:', firstSignal.created_at)
      console.log('SignalsTab: Parsed date:', testDate.toISOString())
      console.log('SignalsTab: Cutoff date:', cutoffDate.toISOString())
      console.log('SignalsTab: Is valid date?', !isNaN(testDate.getTime()))
      console.log('SignalsTab: Is after cutoff?', testDate >= cutoffDate)
    }

    filtered = filtered.filter(s => {
      const signalDate = new Date(s.created_at)
      return !isNaN(signalDate.getTime()) && signalDate >= cutoffDate
    })

    console.log('SignalsTab: Filtered signals count:', filtered.length, 'days:', selectedDays)

    return filtered
  }, [signals, statusFilter, selectedDays])

  const stats = useMemo(() => {
    if (!filteredSignals.length) return { total: 0, executed: 0, pending: 0, failed: 0 }
    return {
      total: filteredSignals.length,
      executed: filteredSignals.filter(s => s.status === 'executed').length,
      pending: filteredSignals.filter(s => s.status === 'pending').length,
      failed: filteredSignals.filter(s => s.status === 'failed').length,
    }
  }, [filteredSignals])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'executed': return 'text-green-400 bg-green-500/20'
      case 'pending': return 'text-yellow-400 bg-yellow-500/20'
      case 'failed': return 'text-red-400 bg-red-500/20'
      default: return 'text-gray-400 bg-gray-500/20'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'executed': return <CheckCircle className="w-3 h-3" />
      case 'pending': return <Clock className="w-3 h-3" />
      case 'failed': return <XCircle className="w-3 h-3" />
      default: return null
    }
  }

  const exportToCSV = () => {
    if (!filteredSignals.length) return

    const headers = ['Data/Hora', 'Simbolo', 'Tipo', 'Preco', 'Status']
    const rows = filteredSignals.map(s => [
      formatDateTime(s.created_at),
      s.symbol,
      s.signal_type,
      s.entry_price?.toFixed(2) || '-',
      s.status
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `strategy_signals_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#131722] rounded-lg px-3 py-2 border border-[#2a2e39]">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={selectedDays}
              onChange={(e) => setSelectedDays(Number(e.target.value))}
              className="bg-transparent border-none text-sm text-white focus:outline-none cursor-pointer"
            >
              {PERIOD_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-1">
            {['all', 'executed', 'pending', 'failed'].map(status => (
              <Button
                key={status}
                variant={statusFilter === status ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter(status)}
                className="text-xs"
              >
                {status === 'all' ? 'Todos' : status.charAt(0).toUpperCase() + status.slice(1)}
              </Button>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="border-[#2a2e39] text-gray-400"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={exportToCSV}
            disabled={!filteredSignals.length}
            className="border-[#2a2e39] text-gray-400"
          >
            <Download className="w-4 h-4 mr-1" />
            CSV
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-3 bg-[#131722] rounded-lg text-center">
          <p className="text-2xl font-bold text-white">{stats.total}</p>
          <p className="text-xs text-gray-400">Total</p>
        </div>
        <div className="p-3 bg-[#131722] rounded-lg text-center">
          <p className="text-2xl font-bold text-green-400">{stats.executed}</p>
          <p className="text-xs text-gray-400">Executados</p>
        </div>
        <div className="p-3 bg-[#131722] rounded-lg text-center">
          <p className="text-2xl font-bold text-yellow-400">{stats.pending}</p>
          <p className="text-xs text-gray-400">Pendentes</p>
        </div>
        <div className="p-3 bg-[#131722] rounded-lg text-center">
          <p className="text-2xl font-bold text-red-400">{stats.failed}</p>
          <p className="text-xs text-gray-400">Falharam</p>
        </div>
      </div>

      {/* Signals Table */}
      {filteredSignals.length > 0 ? (
        <div className="bg-[#131722] rounded-lg border border-[#2a2e39] overflow-hidden">
          <div className="max-h-[400px] overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="bg-[#1e222d] sticky top-0">
                <tr>
                  <th className="text-left py-3 px-4 font-medium text-gray-400">Data/Hora</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-400">Simbolo</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-400">Tipo</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-400">Preco</th>
                  <th className="text-center py-3 px-4 font-medium text-gray-400">Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredSignals.map((signal) => (
                  <tr
                    key={signal.id}
                    className="border-t border-[#2a2e39] hover:bg-[#1e222d] transition-colors"
                  >
                    <td className="py-3 px-4 text-gray-300 font-mono text-xs">
                      {formatDateTime(signal.created_at)}
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant="default" className="bg-blue-500/20 text-blue-300">
                        {signal.symbol}
                      </Badge>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`font-medium ${signal.signal_type === 'long' ? 'text-green-400' : 'text-red-400'}`}>
                        {signal.signal_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-white font-mono">
                      ${signal.entry_price?.toFixed(2) || '-'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(signal.status)}`}>
                        {getStatusIcon(signal.status)}
                        {signal.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="p-8 bg-[#131722] rounded-lg text-center">
          <Zap className="w-8 h-8 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">Nenhum sinal encontrado no periodo selecionado</p>
        </div>
      )}
    </div>
  )
}

// Tab 3: Chart
function ChartTab({ strategy }: { strategy: StrategyWithRelations }) {
  const [selectedSymbol, setSelectedSymbol] = useState<string>(
    Array.isArray(strategy.symbols) && strategy.symbols.length > 0
      ? strategy.symbols[0]
      : 'BTCUSDT'
  )
  const [selectedDays, setSelectedDays] = useState(7)
  const [selectedTimeframe, setSelectedTimeframe] = useState<string>(
    strategy.timeframe || '15m'
  )

  const symbols = Array.isArray(strategy.symbols) ? strategy.symbols : []

  // Fetch chart data from API - only when tab is active
  const { data: chartData, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['strategy-chart', strategy.id, selectedSymbol, selectedDays, selectedTimeframe],
    queryFn: () => strategyService.getChartData(strategy.id, selectedSymbol, selectedDays, selectedTimeframe),
    enabled: !!strategy.id && !!selectedSymbol,
    staleTime: 60000, // 1 minute cache
    refetchOnWindowFocus: false,
  })

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Symbol selector */}
          <div className="flex items-center gap-2 bg-[#131722] rounded-lg px-3 py-2 border border-[#2a2e39]">
            <BarChart3 className="w-4 h-4 text-gray-400" />
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="bg-transparent border-none text-sm text-white focus:outline-none cursor-pointer"
            >
              {symbols.map(symbol => (
                <option key={symbol} value={symbol}>{symbol}</option>
              ))}
            </select>
          </div>
          {/* Timeframe selector */}
          <div className="flex items-center gap-2 bg-[#131722] rounded-lg px-3 py-2 border border-[#2a2e39]">
            <Clock className="w-4 h-4 text-gray-400" />
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="bg-transparent border-none text-sm text-white focus:outline-none cursor-pointer"
            >
              {TIMEFRAME_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          {/* Period selector */}
          <div className="flex items-center gap-2 bg-[#131722] rounded-lg px-3 py-2 border border-[#2a2e39]">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={selectedDays}
              onChange={(e) => setSelectedDays(Number(e.target.value))}
              className="bg-transparent border-none text-sm text-white focus:outline-none cursor-pointer"
            >
              {PERIOD_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="border-[#2a2e39] text-gray-400"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Chart Info */}
      {chartData && (
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>Candles: {chartData.candles?.length || 0}</span>
          <span>Sinais: {chartData.trades?.length || 0}</span>
          <span>Timeframe: {chartData.timeframe}</span>
        </div>
      )}

      {/* Chart */}
      {isLoading || isFetching ? (
        <div className="flex flex-col items-center justify-center h-[500px] bg-[#131722] rounded-lg">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mb-4" />
          <p className="text-gray-400">Carregando grafico...</p>
          <p className="text-gray-500 text-sm mt-1">Buscando candles da Binance e calculando indicadores</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center h-[500px] bg-[#131722] rounded-lg border border-red-500/30">
          <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
          <p className="text-red-400 mb-2">Erro ao carregar grafico</p>
          <p className="text-gray-500 text-sm mb-4">{(error as Error).message}</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Tentar novamente
          </Button>
        </div>
      ) : chartData && chartData.candles && chartData.candles.length > 0 ? (
        <BacktestChart
          candles={chartData.candles}
          trades={chartData.trades || []}
          indicators={chartData.indicators || {}}
          symbol={selectedSymbol}
          height={500}
        />
      ) : (
        <div className="flex flex-col items-center justify-center h-[500px] bg-[#131722] rounded-lg border border-[#2a2e39]">
          <LineChart className="w-12 h-12 text-gray-600 mb-4" />
          <p className="text-gray-400 mb-2">Nenhum dado disponivel</p>
          <p className="text-gray-500 text-sm mb-4">Nao foi possivel carregar os candles para este periodo</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Recarregar
          </Button>
        </div>
      )}
    </div>
  )
}

// Tab 4: Metrics
function MetricsTab({ strategy }: { strategy: StrategyWithRelations }) {
  const [selectedSymbol, setSelectedSymbol] = useState<string>(
    Array.isArray(strategy.symbols) && strategy.symbols.length > 0
      ? strategy.symbols[0]
      : 'BTCUSDT'
  )
  const [selectedDays, setSelectedDays] = useState(30)

  const symbols = Array.isArray(strategy.symbols) ? strategy.symbols : []

  // Fetch metrics from API
  const { data: metricsData, isLoading } = useQuery({
    queryKey: ['strategy-metrics', strategy.id, selectedSymbol, selectedDays],
    queryFn: () => strategyService.getMetrics(strategy.id, { symbol: selectedSymbol, days: selectedDays }),
    enabled: !!strategy.id && !!selectedSymbol,
  })

  // Extract metrics for selected symbol
  const metrics: StrategyMetrics | undefined = useMemo(() => {
    if (!metricsData) return undefined
    // If metricsData is a single StrategyMetrics (when symbol filter is used)
    if ('symbol' in metricsData && metricsData.symbol === selectedSymbol) {
      return metricsData as StrategyMetrics
    }
    // If metricsData is StrategyMetricsResponse
    if ('metrics' in metricsData) {
      return (metricsData as StrategyMetricsResponse).metrics.find(m => m.symbol === selectedSymbol)
    }
    return undefined
  }, [metricsData, selectedSymbol])

  const formatCurrency = (value: number) => {
    const sign = value >= 0 ? '+' : ''
    return `${sign}$${Math.abs(value).toFixed(2)}`
  }

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Symbol Selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-[#131722] rounded-lg px-3 py-2 border border-[#2a2e39]">
          <Target className="w-4 h-4 text-gray-400" />
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="bg-transparent border-none text-sm text-white focus:outline-none cursor-pointer"
          >
            {symbols.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2 bg-[#131722] rounded-lg px-3 py-2 border border-[#2a2e39]">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={selectedDays}
            onChange={(e) => setSelectedDays(Number(e.target.value))}
            className="bg-transparent border-none text-sm text-white focus:outline-none cursor-pointer"
          >
            {PERIOD_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <Badge variant="default" className="bg-cyan-500/20 text-cyan-300">
          {selectedSymbol}
        </Badge>
      </div>

      {/* Main Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {/* Win Rate */}
        <div className="p-4 bg-[#131722] rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            <span className="text-sm text-gray-400">Win Rate</span>
            <InfoTooltip text="Percentual de trades lucrativos sobre o total de trades fechados" />
          </div>
          <p className={`text-2xl font-bold ${(metrics?.win_rate || 0) >= 50 ? 'text-green-400' : 'text-red-400'}`}>
            {(metrics?.win_rate || 0).toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {metrics?.winning_signals || 0}W / {metrics?.losing_signals || 0}L
          </p>
        </div>

        {/* P&L Total */}
        <div className="p-4 bg-[#131722] rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-sm text-gray-400">P&L Total</span>
            <InfoTooltip text="Lucro ou prejuizo total em USD de todos os trades fechados" />
          </div>
          <p className={`text-2xl font-bold ${(metrics?.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatCurrency(metrics?.total_pnl || 0)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Avg: {formatCurrency(metrics?.avg_pnl_per_trade || 0)}/trade
          </p>
        </div>

        {/* Sharpe Ratio */}
        <div className="p-4 bg-[#131722] rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-gray-400">Sharpe Ratio</span>
            <InfoTooltip text="Mede o retorno ajustado ao risco. Valores > 1 sao considerados bons, > 2 excelentes" />
          </div>
          <p className={`text-2xl font-bold ${(metrics?.sharpe_ratio || 0) >= 1 ? 'text-green-400' : (metrics?.sharpe_ratio || 0) >= 0 ? 'text-yellow-400' : 'text-red-400'}`}>
            {(metrics?.sharpe_ratio || 0).toFixed(2)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {(metrics?.sharpe_ratio || 0) >= 2 ? 'Excelente' : (metrics?.sharpe_ratio || 0) >= 1 ? 'Bom' : (metrics?.sharpe_ratio || 0) >= 0 ? 'Moderado' : 'Ruim'}
          </p>
        </div>

        {/* Max Drawdown */}
        <div className="p-4 bg-[#131722] rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-sm text-gray-400">Max Drawdown</span>
            <InfoTooltip text="Maior queda percentual do pico ao vale no periodo" />
          </div>
          <p className="text-2xl font-bold text-red-400">
            -{(metrics?.max_drawdown || 0).toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500 mt-1">
            Worst: {formatCurrency(metrics?.worst_trade || 0)}
          </p>
        </div>

        {/* BTC Correlation */}
        <div className="p-4 bg-[#131722] rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-orange-400" />
            <span className="text-sm text-gray-400">Correl. BTC</span>
            <InfoTooltip text="Correlacao dos resultados com o preco do Bitcoin. 1 = mesma direcao, -1 = direcao oposta" />
          </div>
          <p className={`text-2xl font-bold ${Math.abs(metrics?.btc_correlation || 0) > 0.7 ? 'text-orange-400' : 'text-gray-300'}`}>
            {(metrics?.btc_correlation || 0).toFixed(2)}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {Math.abs(metrics?.btc_correlation || 0) > 0.7 ? 'Alta' : Math.abs(metrics?.btc_correlation || 0) > 0.3 ? 'Media' : 'Baixa'}
          </p>
        </div>
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-2 gap-4">
        {/* Execution Stats */}
        <div className="p-4 bg-[#131722] rounded-lg">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Execucao</h4>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Total Sinais</span>
              <span className="text-white font-medium">{metrics?.total_signals || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Executados</span>
              <span className="text-green-400 font-medium">{metrics?.executed_signals || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Falharam</span>
              <span className="text-red-400 font-medium">{metrics?.failed_signals || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Taxa Execucao</span>
              <span className="text-cyan-400 font-medium">
                {metrics?.total_signals ? ((metrics.executed_signals / metrics.total_signals) * 100).toFixed(1) : 0}%
              </span>
            </div>
          </div>
        </div>

        {/* Trade Stats */}
        <div className="p-4 bg-[#131722] rounded-lg">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Performance</h4>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Profit Factor</span>
              <span className={`font-medium ${(metrics?.profit_factor || 0) >= 1 ? 'text-green-400' : 'text-red-400'}`}>
                {(metrics?.profit_factor || 0).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Melhor Trade</span>
              <span className="text-green-400 font-medium">{formatCurrency(metrics?.best_trade || 0)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Pior Trade</span>
              <span className="text-red-400 font-medium">{formatCurrency(metrics?.worst_trade || 0)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Media/Trade</span>
              <span className={`font-medium ${(metrics?.avg_pnl_per_trade || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(metrics?.avg_pnl_per_trade || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Note for metrics */}
      <div className="flex items-start gap-2 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
        <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
        <p className="text-yellow-300 text-sm">
          <strong>Nota:</strong> As metricas sao calculadas com base nos sinais executados e seus resultados reais.
          Para metricas mais precisas, execute backtests com diferentes periodos.
        </p>
      </div>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function StrategyDetailsModal({ strategyId, onClose }: StrategyDetailsModalProps) {
  const [activeTab, setActiveTab] = useState<TabType>('info')

  const { data: strategy, isLoading, error } = useQuery({
    queryKey: ['strategy', strategyId],
    queryFn: () => strategyService.getStrategy(strategyId),
  })

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'info', label: 'Informacoes', icon: <Info className="w-4 h-4" /> },
    { id: 'signals', label: 'Sinais', icon: <Zap className="w-4 h-4" /> },
    { id: 'chart', label: 'Grafico', icon: <LineChart className="w-4 h-4" /> },
    { id: 'metrics', label: 'Metricas', icon: <BarChart3 className="w-4 h-4" /> },
  ]

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <Card className="max-w-4xl w-full p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
          </div>
        </Card>
      </div>
    )
  }

  if (error || !strategy) {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <Card className="max-w-md w-full p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center text-red-300 mb-4">
            <AlertCircle className="w-5 h-5 mr-2" />
            <p>Erro ao carregar estrategia</p>
          </div>
          <Button onClick={onClose} className="w-full">Fechar</Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
      <Card className="max-w-5xl w-full bg-[#1e222d] border-[#2a2e39] my-8">
        {/* Header */}
        <div className="flex justify-between items-start p-6 border-b border-[#2a2e39]">
          <div>
            <h3 className="text-xl font-semibold text-cyan-400 mb-1">{strategy.name}</h3>
            <p className="text-gray-300 text-sm">{strategy.description || 'Sem descricao'}</p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={strategy.is_active ? 'success' : 'default'}>
              {strategy.is_active ? 'Ativa' : 'Inativa'}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-[#2a2e39]">
          <div className="flex gap-1 px-6 pt-2">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-3 text-sm font-medium rounded-t-lg transition-colors
                  ${activeTab === tab.id
                    ? 'bg-[#131722] text-cyan-400 border-t border-l border-r border-[#2a2e39]'
                    : 'text-gray-400 hover:text-gray-300 hover:bg-[#131722]/50'
                  }
                `}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[calc(100vh-300px)] overflow-y-auto">
          {activeTab === 'info' && <StrategyInfoTab strategy={strategy} />}
          {activeTab === 'signals' && <SignalsTab strategyId={strategyId} />}
          {activeTab === 'chart' && <ChartTab strategy={strategy} />}
          {activeTab === 'metrics' && <MetricsTab strategy={strategy} />}
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t border-[#2a2e39]">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-[#2a2e39] text-gray-300 hover:bg-[#2a2e39]"
          >
            Fechar
          </Button>
        </div>
      </Card>
    </div>
  )
}
