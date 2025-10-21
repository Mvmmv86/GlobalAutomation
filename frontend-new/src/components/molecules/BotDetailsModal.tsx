import React from 'react'
import { X, TrendingUp, Activity, DollarSign, Target, Calendar } from 'lucide-react'
import { BotSubscription } from '@/services/botsService'

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
  if (!isOpen || !subscription) return null

  const getWinRate = () => {
    const total = subscription.win_count + subscription.loss_count
    if (total === 0) return 0
    return ((subscription.win_count / total) * 100).toFixed(1)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {subscription.bot_name}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Detalhes e Performance do Bot
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Main Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-5 h-5 text-blue-500" />
                <p className="text-sm text-gray-600 dark:text-gray-400">Win Rate</p>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {getWinRate()}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {subscription.win_count}W / {subscription.loss_count}L
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-5 h-5 text-green-500" />
                <p className="text-sm text-gray-600 dark:text-gray-400">P&L Total</p>
              </div>
              <p className={`text-2xl font-bold ${subscription.total_pnl_usd >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {subscription.total_pnl_usd >= 0 ? '+' : ''}${subscription.total_pnl_usd.toFixed(2)}
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-5 h-5 text-purple-500" />
                <p className="text-sm text-gray-600 dark:text-gray-400">Sinais</p>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {subscription.total_signals_received}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {subscription.total_orders_executed} executadas
              </p>
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-5 h-5 text-orange-500" />
                <p className="text-sm text-gray-600 dark:text-gray-400">Posições</p>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {subscription.current_positions}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                de {subscription.max_concurrent_positions} máx
              </p>
            </div>
          </div>

          {/* Configuration Details */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Configurações
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Alavancagem</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {subscription.custom_leverage || subscription.default_leverage}x
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Margem USD</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  ${subscription.custom_margin_usd || subscription.default_margin_usd}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Stop Loss</p>
                <p className="text-lg font-semibold text-red-600">
                  {subscription.custom_stop_loss_pct || subscription.default_stop_loss_pct}%
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Take Profit</p>
                <p className="text-lg font-semibold text-green-600">
                  {subscription.custom_take_profit_pct || subscription.default_take_profit_pct}%
                </p>
              </div>
            </div>
          </div>

          {/* Risk Management */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Gestão de Risco
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Perda Diária Máxima</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  ${subscription.max_daily_loss_usd.toFixed(2)}
                </p>
                <div className="mt-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">Perda Atual</span>
                    <span className={subscription.current_daily_loss_usd > 0 ? 'text-red-600' : 'text-gray-500'}>
                      ${subscription.current_daily_loss_usd.toFixed(2)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        subscription.current_daily_loss_usd / subscription.max_daily_loss_usd > 0.8
                          ? 'bg-red-600'
                          : subscription.current_daily_loss_usd / subscription.max_daily_loss_usd > 0.5
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                      }`}
                      style={{
                        width: `${Math.min((subscription.current_daily_loss_usd / subscription.max_daily_loss_usd) * 100, 100)}%`
                      }}
                    ></div>
                  </div>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Posições Simultâneas</p>
                <p className="text-lg font-semibold text-gray-900 dark:text-white">
                  {subscription.current_positions} / {subscription.max_concurrent_positions}
                </p>
                <div className="mt-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500">Utilização</span>
                    <span className="text-gray-900 dark:text-white">
                      {((subscription.current_positions / subscription.max_concurrent_positions) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
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
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
            <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
              Informações da Conta
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-600 dark:text-gray-400">Exchange</p>
                <p className="font-semibold text-gray-900 dark:text-white capitalize">
                  {subscription.exchange}
                </p>
              </div>
              <div>
                <p className="text-gray-600 dark:text-gray-400">Conta</p>
                <p className="font-semibold text-gray-900 dark:text-white">
                  {subscription.account_name}
                </p>
              </div>
              <div>
                <p className="text-gray-600 dark:text-gray-400">Mercado</p>
                <p className="font-semibold text-gray-900 dark:text-white capitalize">
                  {subscription.market_type}
                </p>
              </div>
            </div>
          </div>

          {/* Timeline */}
          {subscription.last_signal_at && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-5">
              <div className="flex items-center gap-2 mb-3">
                <Calendar className="w-5 h-5 text-gray-600" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Atividade
                </h3>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Inscrito em</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {new Date(subscription.created_at).toLocaleString('pt-BR')}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Último Sinal</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {new Date(subscription.last_signal_at).toLocaleString('pt-BR')}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 dark:bg-gray-700 dark:hover:bg-gray-600"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}
