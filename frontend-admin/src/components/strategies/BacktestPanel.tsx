/**
 * BacktestPanel Component
 * Interface for running and viewing backtest results
 */
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  Play,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Calendar,
  DollarSign,
  Percent,
  Activity,
  AlertCircle,
  RefreshCw,
  Download
} from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { Label } from '@/components/atoms/Label'
import { Badge } from '@/components/atoms/Badge'
import { strategyService, StrategyBacktestResult } from '@/services/strategyService'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { toast } from 'sonner'

interface BacktestPanelProps {
  strategyId: string
  strategyName: string
  symbols: string[]
  onClose?: () => void
}

interface BacktestConfig {
  symbol: string
  start_date: string
  end_date: string
  initial_capital: number
  leverage: number
}

export function BacktestPanel({ strategyId, strategyName, symbols, onClose }: BacktestPanelProps) {
  const [config, setConfig] = useState<BacktestConfig>({
    symbol: symbols[0] || 'BTCUSDT',
    start_date: getDefaultStartDate(),
    end_date: getDefaultEndDate(),
    initial_capital: 10000,
    leverage: 10,
  })
  const [selectedResult, setSelectedResult] = useState<StrategyBacktestResult | null>(null)

  // Fetch existing backtest results
  const { data: results, isLoading, refetch } = useQuery({
    queryKey: ['backtest-results', strategyId],
    queryFn: () => strategyService.getBacktestResults(strategyId),
  })

  // Run backtest mutation (placeholder - backend would need this endpoint)
  const runBacktestMutation = useMutation({
    mutationFn: async (config: BacktestConfig) => {
      // TODO: Implement actual backtest API call
      // For now, simulate a backtest result
      toast.info('Backtest iniciado... (simulacao)')
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Simulated result
      return {
        id: `bt_${Date.now()}`,
        strategy_id: strategyId,
        start_date: config.start_date,
        end_date: config.end_date,
        symbol: config.symbol,
        initial_capital: config.initial_capital,
        leverage: config.leverage,
        total_trades: Math.floor(Math.random() * 50) + 10,
        winning_trades: Math.floor(Math.random() * 30) + 5,
        losing_trades: Math.floor(Math.random() * 20) + 5,
        win_rate: Math.random() * 30 + 40,
        profit_factor: Math.random() * 1.5 + 0.8,
        total_pnl: (Math.random() - 0.3) * 5000,
        total_pnl_percent: (Math.random() - 0.3) * 50,
        max_drawdown: Math.random() * 20 + 5,
        sharpe_ratio: Math.random() * 2,
        created_at: new Date().toISOString(),
      } as StrategyBacktestResult
    },
    onSuccess: (result) => {
      toast.success('Backtest concluido!')
      setSelectedResult(result)
      refetch()
    },
    onError: (error: Error) => {
      toast.error(`Erro no backtest: ${error.message}`)
    },
  })

  function getDefaultStartDate(): string {
    const date = new Date()
    date.setMonth(date.getMonth() - 3)
    return date.toISOString().split('T')[0]
  }

  function getDefaultEndDate(): string {
    return new Date().toISOString().split('T')[0]
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">Backtest</h3>
          <p className="text-gray-400 text-sm">{strategyName}</p>
        </div>
        <Button variant="outline" onClick={onClose} className="border-[#2a2e39] text-gray-400">
          Fechar
        </Button>
      </div>

      {/* Config Panel */}
      <Card className="p-4 bg-[#131722] border-[#2a2e39]">
        <h4 className="text-white font-medium mb-4 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-blue-400" />
          Configuracao do Backtest
        </h4>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <Label className="text-gray-400 text-xs">Simbolo</Label>
            <select
              value={config.symbol}
              onChange={(e) => setConfig(prev => ({ ...prev, symbol: e.target.value }))}
              className="mt-1 w-full bg-[#1e222d] border border-[#2a2e39] text-white rounded px-2 py-1.5 text-sm"
            >
              {symbols.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div>
            <Label className="text-gray-400 text-xs">Data Inicio</Label>
            <Input
              type="date"
              value={config.start_date}
              onChange={(e) => setConfig(prev => ({ ...prev, start_date: e.target.value }))}
              className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white h-8 text-sm"
            />
          </div>

          <div>
            <Label className="text-gray-400 text-xs">Data Fim</Label>
            <Input
              type="date"
              value={config.end_date}
              onChange={(e) => setConfig(prev => ({ ...prev, end_date: e.target.value }))}
              className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white h-8 text-sm"
            />
          </div>

          <div>
            <Label className="text-gray-400 text-xs">Capital Inicial ($)</Label>
            <Input
              type="number"
              value={config.initial_capital}
              onChange={(e) => setConfig(prev => ({ ...prev, initial_capital: parseFloat(e.target.value) || 0 }))}
              className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white h-8 text-sm"
            />
          </div>

          <div>
            <Label className="text-gray-400 text-xs">Alavancagem</Label>
            <Input
              type="number"
              value={config.leverage}
              onChange={(e) => setConfig(prev => ({ ...prev, leverage: parseInt(e.target.value) || 1 }))}
              min={1}
              max={125}
              className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white h-8 text-sm"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <Button
            onClick={() => runBacktestMutation.mutate(config)}
            disabled={runBacktestMutation.isPending}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {runBacktestMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Executando...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Executar Backtest
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Results Display */}
      {selectedResult && (
        <Card className="p-4 bg-[#131722] border-[#2a2e39]">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-white font-medium flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              Resultado do Backtest
            </h4>
            <Badge variant="default" className="bg-blue-500/20 text-blue-300">
              {selectedResult.symbol}
            </Badge>
          </div>

          {/* Main Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="p-3 bg-[#1e222d] rounded-lg text-center">
              <DollarSign className="w-5 h-5 text-gray-400 mx-auto mb-1" />
              <p className={`text-xl font-bold ${selectedResult.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatCurrency(selectedResult.total_pnl)}
              </p>
              <p className="text-xs text-gray-500">P&L Total</p>
            </div>

            <div className="p-3 bg-[#1e222d] rounded-lg text-center">
              <Percent className="w-5 h-5 text-gray-400 mx-auto mb-1" />
              <p className={`text-xl font-bold ${selectedResult.total_pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatPercent(selectedResult.total_pnl_percent)}
              </p>
              <p className="text-xs text-gray-500">Retorno</p>
            </div>

            <div className="p-3 bg-[#1e222d] rounded-lg text-center">
              <TrendingUp className="w-5 h-5 text-gray-400 mx-auto mb-1" />
              <p className={`text-xl font-bold ${selectedResult.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                {selectedResult.win_rate.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">Win Rate</p>
            </div>

            <div className="p-3 bg-[#1e222d] rounded-lg text-center">
              <TrendingDown className="w-5 h-5 text-gray-400 mx-auto mb-1" />
              <p className="text-xl font-bold text-red-400">
                -{selectedResult.max_drawdown.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500">Max Drawdown</p>
            </div>
          </div>

          {/* Detailed Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Total Trades:</span>
              <span className="text-white font-medium">{selectedResult.total_trades}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Trades Ganhos:</span>
              <span className="text-green-400 font-medium">{selectedResult.winning_trades}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Trades Perdidos:</span>
              <span className="text-red-400 font-medium">{selectedResult.losing_trades}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Profit Factor:</span>
              <span className={`font-medium ${selectedResult.profit_factor >= 1 ? 'text-green-400' : 'text-red-400'}`}>
                {selectedResult.profit_factor.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Sharpe Ratio:</span>
              <span className="text-white font-medium">{selectedResult.sharpe_ratio.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Capital Inicial:</span>
              <span className="text-white font-medium">{formatCurrency(selectedResult.initial_capital)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Alavancagem:</span>
              <span className="text-white font-medium">{selectedResult.leverage}x</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Periodo:</span>
              <span className="text-white font-medium text-xs">
                {format(new Date(selectedResult.start_date), 'dd/MM/yy')} - {format(new Date(selectedResult.end_date), 'dd/MM/yy')}
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* Historical Results */}
      {results && results.length > 0 && (
        <Card className="p-4 bg-[#131722] border-[#2a2e39]">
          <h4 className="text-white font-medium mb-4 flex items-center gap-2">
            <Calendar className="w-4 h-4 text-purple-400" />
            Historico de Backtests
          </h4>

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {results.map((result) => (
              <button
                key={result.id}
                onClick={() => setSelectedResult(result)}
                className={`
                  w-full p-3 rounded-lg text-left transition-colors
                  ${selectedResult?.id === result.id
                    ? 'bg-blue-500/20 border border-blue-500/50'
                    : 'bg-[#1e222d] hover:bg-[#2a2e39]'
                  }
                `}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="default" className="bg-gray-700 text-gray-300">
                      {result.symbol}
                    </Badge>
                    <span className="text-gray-400 text-sm">
                      {format(new Date(result.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`font-medium ${result.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(result.total_pnl)}
                    </span>
                    <span className={`text-sm ${result.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}`}>
                      WR: {result.win_rate.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </Card>
      )}

      {/* Empty state */}
      {(!results || results.length === 0) && !selectedResult && (
        <Card className="p-8 bg-[#131722] border-[#2a2e39] text-center">
          <BarChart3 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 mb-2">Nenhum backtest realizado</p>
          <p className="text-gray-500 text-sm">Configure os parametros acima e execute um backtest para ver os resultados.</p>
        </Card>
      )}

      {/* Warning */}
      <div className="flex items-start gap-2 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
        <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5" />
        <p className="text-yellow-300 text-sm">
          <strong>Aviso:</strong> Resultados de backtests sao baseados em dados historicos e nao garantem performance futura.
          Trading envolve riscos significativos.
        </p>
      </div>
    </div>
  )
}
