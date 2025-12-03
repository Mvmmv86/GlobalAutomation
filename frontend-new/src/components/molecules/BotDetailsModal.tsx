import React, { useEffect, useState } from 'react'
import { X, TrendingUp, Activity, DollarSign, Target, Calendar, Loader2, Filter, Share2, Info } from 'lucide-react'
import { BotSubscription, botsService, SubscriptionPerformance } from '@/services/botsService'
import { BotPnLChart } from './BotPnLChart'
import { BotWinRateChart } from './BotWinRateChart'
import { SharePnLModal } from './SharePnLModal'
import { useAuth } from '@/contexts/AuthContext'

// Tooltip component for info icons
interface InfoTooltipProps {
  text: string
}

const InfoTooltip: React.FC<InfoTooltipProps> = ({ text }) => {
  const [isVisible, setIsVisible] = useState(false)

  return (
    <div className="relative inline-block ml-1">
      <button
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onClick={(e) => {
          e.stopPropagation()
          setIsVisible(!isVisible)
        }}
        className="text-muted-foreground/60 hover:text-muted-foreground transition-colors"
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      {isVisible && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-popover border border-border rounded-lg shadow-lg text-xs text-popover-foreground">
          <div className="relative">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-border" />
          </div>
        </div>
      )}
    </div>
  )
}

interface BotDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  subscription: BotSubscription | null
}

// Period options for filtering
const PERIOD_OPTIONS = [
  { value: 7, label: '7 dias' },
  { value: 30, label: '30 dias' },
  { value: 90, label: '90 dias' },
  { value: 180, label: '6 meses' },
  { value: 365, label: '1 ano' },
]

export const BotDetailsModal: React.FC<BotDetailsModalProps> = ({
  isOpen,
  onClose,
  subscription
}) => {
  const { user } = useAuth()
  const [performance, setPerformance] = useState<SubscriptionPerformance | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedDays, setSelectedDays] = useState(30)
  const [isShareModalOpen, setIsShareModalOpen] = useState(false)

  // Fetch performance data when modal opens
  useEffect(() => {
    if (isOpen && subscription && user?.id) {
      setIsLoading(true)
      botsService.getSubscriptionPerformance(subscription.id, user.id, selectedDays)
        .then(data => {
          setPerformance(data)
        })
        .catch(err => {
          console.error('Error fetching performance:', err)
        })
        .finally(() => {
          setIsLoading(false)
        })
    }
  }, [isOpen, subscription, user?.id, selectedDays])

  if (!isOpen || !subscription) return null

  // Get filtered stats from performance API (or fallback to subscription data)
  const filteredStats = performance?.filtered_summary
  const currentState = performance?.current_state

  const getWinRate = () => {
    if (filteredStats) {
      return filteredStats.win_rate.toFixed(1)
    }
    const total = subscription.win_count + subscription.loss_count
    if (total === 0) return '0'
    return ((subscription.win_count / total) * 100).toFixed(1)
  }

  const getTotalPnl = () => {
    return filteredStats?.total_pnl_usd ?? subscription.total_pnl_usd
  }

  const getSignals = () => {
    return filteredStats?.total_signals ?? subscription.total_signals_received
  }

  const getExecuted = () => {
    return filteredStats?.total_orders_executed ?? subscription.total_orders_executed
  }

  const getWinCount = () => {
    return filteredStats?.total_wins ?? subscription.win_count
  }

  const getLossCount = () => {
    return filteredStats?.total_losses ?? subscription.loss_count
  }

  // Total trades (open + closed)
  const getTotalTrades = () => {
    return filteredStats?.total_trades ?? (subscription.win_count + subscription.loss_count)
  }

  // Only closed trades
  const getClosedTrades = () => {
    return filteredStats?.closed_trades ?? (getWinCount() + getLossCount())
  }

  // Open trades (positions abertas)
  const getOpenTrades = () => {
    return filteredStats?.open_trades ?? 0
  }

  const getCurrentPositions = () => {
    return currentState?.current_positions ?? subscription.current_positions
  }

  const getMaxPositions = () => {
    return currentState?.max_concurrent_positions ?? subscription.max_concurrent_positions
  }

  const getPositionsData = () => {
    return currentState?.positions_data ?? []
  }

  const getPeriodLabel = () => {
    const option = PERIOD_OPTIONS.find(o => o.value === selectedDays)
    return option ? option.label : `${selectedDays} dias`
  }

  // Calculate P&L percentage based on total volume traded
  const getPnlPercent = () => {
    const pnl = getTotalPnl()
    const tradesCount = getWinCount() + getLossCount()
    const marginPerTrade = subscription.custom_margin_usd || subscription.default_margin_usd || 100

    // If no trades, return undefined (no percentage to show)
    if (tradesCount === 0) return undefined

    // Calculate percentage: P&L / (trades * margin) * 100
    const totalInvested = tradesCount * marginPerTrade
    if (totalInvested === 0) return undefined

    return (pnl / totalInvested) * 100
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border sticky top-0 bg-card z-10">
          <div>
            <h2 className="text-2xl font-bold text-foreground">
              {subscription.bot_name}
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Detalhes e Performance do Bot
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Period Filter - applies to ALL stats */}
            <div className="flex items-center gap-2 bg-secondary/50 rounded-lg px-3 py-2 border border-border">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <select
                value={selectedDays}
                onChange={(e) => setSelectedDays(Number(e.target.value))}
                className="bg-transparent border-none text-sm text-foreground focus:outline-none cursor-pointer"
              >
                {PERIOD_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            {/* Share Button */}
            <button
              onClick={() => setIsShareModalOpen(true)}
              className="flex items-center gap-2 bg-primary/10 text-primary border border-primary/30 rounded-lg px-3 py-2 hover:bg-primary/20 transition-colors"
            >
              <Share2 className="w-4 h-4" />
              <span className="text-sm font-medium">Compartilhar</span>
            </button>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-lg hover:bg-muted"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Period indicator */}
          {isLoading && (
            <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              Carregando dados...
            </div>
          )}

          {/* Main Stats - Using filtered data */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-secondary/50 p-4 rounded-lg border border-border relative">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-primary" />
                <p className="text-sm text-muted-foreground">Win Rate</p>
                <InfoTooltip text="Percentual de trades lucrativos. Calculado como: Wins / (Wins + Losses) x 100" />
              </div>
              <p className={`text-2xl font-bold ${Number(getWinRate()) >= 50 ? 'text-success' : 'text-danger'}`}>
                {getWinRate()}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {getWinCount()}W / {getLossCount()}L
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-5 h-5 text-success" />
                <p className="text-sm text-muted-foreground">P&L</p>
                <InfoTooltip text="Lucro ou Prejuizo total em USD. Soma de todos os trades fechados no periodo selecionado." />
              </div>
              <p className={`text-2xl font-bold ${getTotalPnl() >= 0 ? 'text-success' : 'text-danger'}`}>
                {getTotalPnl() >= 0 ? '+' : ''}${getTotalPnl().toFixed(2)}
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-5 h-5 text-primary" />
                <p className="text-sm text-muted-foreground">Sinais</p>
                <InfoTooltip text="Total de sinais recebidos do bot. Executadas = sinais que abriram posicoes na exchange." />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {getSignals()}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {getExecuted()} executadas
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-5 h-5 text-warning" />
                <p className="text-sm text-muted-foreground">Posicoes Atuais</p>
                <InfoTooltip text="Posicoes abertas por ESTE bot especifico (nao inclui outras posicoes da conta)." />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {getCurrentPositions()}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                de {getMaxPositions()} max
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-5 h-5 text-blue-400" />
                <p className="text-sm text-muted-foreground">Trades</p>
                <InfoTooltip text="Total de trades executados. Fechados = trades com SL/TP atingido. Abertos = posicoes ainda ativas." />
              </div>
              <p className="text-2xl font-bold text-foreground">
                {getTotalTrades()}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {getClosedTrades()} fechados, {getOpenTrades()} abertos
              </p>
            </div>
          </div>

          {/* Performance Chart - Full Width */}
          <div className="bg-secondary/30 rounded-lg border border-border p-5">
            <h3 className="text-lg font-semibold text-foreground mb-4">
              P&L ao Longo do Tempo
            </h3>
            {isLoading ? (
              <div className="h-[250px] flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : performance?.pnl_history && performance.pnl_history.length > 0 ? (
              <BotPnLChart data={performance.pnl_history} height={250} />
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                Sem dados de performance neste periodo
              </div>
            )}
          </div>

          {/* Configuration Details */}
          <div className="bg-secondary/30 rounded-lg border border-border p-5">
            <h3 className="text-lg font-semibold mb-4 text-foreground">
              Configurações
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Alavancagem</p>
                <p className="text-lg font-semibold text-foreground">
                  {subscription.custom_leverage || subscription.default_leverage}x
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Margem USD</p>
                <p className="text-lg font-semibold text-foreground">
                  ${subscription.custom_margin_usd || subscription.default_margin_usd}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Stop Loss</p>
                <p className="text-lg font-semibold text-danger">
                  {subscription.custom_stop_loss_pct || subscription.default_stop_loss_pct}%
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Take Profit</p>
                <p className="text-lg font-semibold text-success">
                  {subscription.custom_take_profit_pct || subscription.default_take_profit_pct}%
                </p>
              </div>
            </div>
          </div>

          {/* Risk Management */}
          <div className="bg-secondary/30 rounded-lg border border-border p-5">
            <h3 className="text-lg font-semibold mb-4 text-foreground">
              Gestão de Risco
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Perda Diária Máxima</p>
                <p className="text-lg font-semibold text-foreground">
                  ${subscription.max_daily_loss_usd.toFixed(2)}
                </p>
                <div className="mt-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Perda Atual</span>
                    <span className={subscription.current_daily_loss_usd > 0 ? 'text-danger' : 'text-muted-foreground'}>
                      ${subscription.current_daily_loss_usd.toFixed(2)}
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${
                        subscription.current_daily_loss_usd / subscription.max_daily_loss_usd > 0.8
                          ? 'bg-danger'
                          : subscription.current_daily_loss_usd / subscription.max_daily_loss_usd > 0.5
                          ? 'bg-warning'
                          : 'bg-success'
                      }`}
                      style={{
                        width: `${Math.min((subscription.current_daily_loss_usd / subscription.max_daily_loss_usd) * 100, 100)}%`
                      }}
                    ></div>
                  </div>
                </div>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Posições Simultâneas</p>
                <p className="text-lg font-semibold text-foreground">
                  {subscription.current_positions} / {subscription.max_concurrent_positions}
                </p>
                <div className="mt-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Utilização</span>
                    <span className="text-foreground">
                      {((subscription.current_positions / subscription.max_concurrent_positions) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{
                        width: `${(subscription.current_positions / subscription.max_concurrent_positions) * 100}%`
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Exchange Info */}
          <div className="bg-secondary/30 rounded-lg border border-border p-5">
            <h3 className="text-lg font-semibold mb-4 text-foreground">
              Informações da Conta
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Exchange</p>
                <p className="font-semibold text-foreground capitalize">
                  {subscription.exchange}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Conta</p>
                <p className="font-semibold text-foreground">
                  {subscription.account_name}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Mercado</p>
                <p className="font-semibold text-foreground capitalize">
                  {subscription.market_type}
                </p>
              </div>
            </div>
          </div>

          {/* Timeline */}
          {subscription.last_signal_at && (
            <div className="bg-secondary/30 rounded-lg border border-border p-5">
              <div className="flex items-center gap-2 mb-3">
                <Calendar className="w-5 h-5 text-muted-foreground" />
                <h3 className="text-lg font-semibold text-foreground">
                  Atividade
                </h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Inscrito em</span>
                  <span className="font-medium text-foreground">
                    {new Date(subscription.created_at).toLocaleString('pt-BR')}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Último Sinal</span>
                  <span className="font-medium text-foreground">
                    {new Date(subscription.last_signal_at).toLocaleString('pt-BR')}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border p-6 flex justify-end sticky bottom-0 bg-card">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors font-medium"
          >
            Fechar
          </button>
        </div>
      </div>

      {/* Share P&L Modal */}
      <SharePnLModal
        isOpen={isShareModalOpen}
        onClose={() => setIsShareModalOpen(false)}
        botName={subscription.bot_name}
        pnlUsd={getTotalPnl()}
        pnlPercent={getPnlPercent()}
        winRate={Number(getWinRate())}
        totalTrades={getWinCount() + getLossCount()}
        period={getPeriodLabel()}
      />
    </div>
  )
}
