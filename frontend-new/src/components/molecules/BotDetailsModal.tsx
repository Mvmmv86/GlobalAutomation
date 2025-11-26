import React, { useEffect, useState } from 'react'
import { X, TrendingUp, Activity, DollarSign, Target, Calendar, Loader2 } from 'lucide-react'
import { BotSubscription, botsService, SubscriptionPerformance } from '@/services/botsService'
import { BotPnLChart } from './BotPnLChart'
import { BotWinRateChart } from './BotWinRateChart'
import { useAuth } from '@/contexts/AuthContext'

interface BotDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  subscription: BotSubscription | null
}

export const BotDetailsModal: React.FC<BotDetailsModalProps> = ({
  isOpen,
  onClose,
  subscription
}) => {
  const { user } = useAuth()
  const [performance, setPerformance] = useState<SubscriptionPerformance | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedDays, setSelectedDays] = useState(30)

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

  const getWinRate = () => {
    const total = subscription.win_count + subscription.loss_count
    if (total === 0) return 0
    return ((subscription.win_count / total) * 100).toFixed(1)
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
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-lg hover:bg-muted"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Main Stats */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-primary" />
                <p className="text-sm text-muted-foreground">Win Rate</p>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {getWinRate()}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {subscription.win_count}W / {subscription.loss_count}L
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-5 h-5 text-success" />
                <p className="text-sm text-muted-foreground">P&L Total</p>
              </div>
              <p className={`text-2xl font-bold ${subscription.total_pnl_usd >= 0 ? 'text-success' : 'text-danger'}`}>
                {subscription.total_pnl_usd >= 0 ? '+' : ''}${subscription.total_pnl_usd.toFixed(2)}
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-5 h-5 text-primary" />
                <p className="text-sm text-muted-foreground">Sinais</p>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {subscription.total_signals_received}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {subscription.total_orders_executed} executadas
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-5 h-5 text-warning" />
                <p className="text-sm text-muted-foreground">Posições</p>
              </div>
              <p className="text-2xl font-bold text-foreground">
                {subscription.current_positions}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                de {subscription.max_concurrent_positions} máx
              </p>
            </div>

            <div className="bg-secondary/50 p-4 rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-success" />
                <p className="text-sm text-muted-foreground">Taxa Vitória</p>
              </div>
              <p className={`text-2xl font-bold ${Number(getWinRate()) >= 50 ? 'text-success' : 'text-danger'}`}>
                {getWinRate()}%
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {subscription.win_count + subscription.loss_count} trades
              </p>
            </div>
          </div>

          {/* Performance Chart - Full Width */}
          <div className="bg-secondary/30 rounded-lg border border-border p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">
                P&L ao Longo do Tempo
              </h3>
              <select
                value={selectedDays}
                onChange={(e) => setSelectedDays(Number(e.target.value))}
                className="bg-secondary border border-border rounded-md px-2 py-1 text-sm text-foreground"
              >
                <option value={7}>7 dias</option>
                <option value={30}>30 dias</option>
                <option value={90}>90 dias</option>
              </select>
            </div>
            {isLoading ? (
              <div className="h-[250px] flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : performance?.pnl_history ? (
              <BotPnLChart data={performance.pnl_history} height={250} />
            ) : (
              <div className="h-[250px] flex items-center justify-center text-muted-foreground">
                Sem dados de performance ainda
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
    </div>
  )
}
