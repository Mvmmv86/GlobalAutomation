import React, { useState, useEffect, useMemo } from 'react'
import { Bot, Activity, Pause, Play, Settings, TrendingUp, Info, XCircle, Sliders, Layers } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { botsService, Bot as BotType, BotSubscription, CreateMultiExchangeSubscriptionData, BotSymbolConfig } from '@/services/botsService'
import { SubscribeBotModal } from '../molecules/SubscribeBotModal'
import { BotDetailsModal } from '../molecules/BotDetailsModal'
import { SubscriptionSymbolConfigsModal } from '../molecules/SubscriptionSymbolConfigsModal'
import { useExchangeAccounts } from '@/hooks/useExchangeAccounts'
import { useAuth } from '@/contexts/AuthContext'

// Interface for symbol configs cache
interface BotSymbolConfigsCache {
  [botId: string]: BotSymbolConfig[]
}

// Helper component to display symbol configs summary
const SymbolConfigsSummary: React.FC<{ configs: BotSymbolConfig[], botDefaults: BotType }> = ({ configs, botDefaults }) => {
  if (!configs || configs.length === 0) {
    // No per-symbol configs, show bot defaults
    return (
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-muted-foreground">Alavancagem</p>
          <p className="font-medium text-gray-900 dark:text-white">{botDefaults.default_leverage}x</p>
        </div>
        <div>
          <p className="text-muted-foreground">Margem</p>
          <p className="font-medium text-gray-900 dark:text-white">${botDefaults.default_margin_usd}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Stop Loss</p>
          <p className="font-medium text-red-600">{botDefaults.default_stop_loss_pct}%</p>
        </div>
        <div>
          <p className="text-muted-foreground">Take Profit</p>
          <p className="font-medium text-green-600">{botDefaults.default_take_profit_pct}%</p>
        </div>
      </div>
    )
  }

  // Get active configs
  const activeConfigs = configs.filter(c => c.is_active)
  if (activeConfigs.length === 0) {
    return (
      <div className="text-center text-muted-foreground text-xs py-2">
        Nenhum ativo configurado
      </div>
    )
  }

  // Check if all configs have same values
  const firstConfig = activeConfigs[0]
  const allSameMargin = activeConfigs.every(c => c.margin_usd === firstConfig.margin_usd)
  const allSameLeverage = activeConfigs.every(c => c.leverage === firstConfig.leverage)
  const allSameSL = activeConfigs.every(c => c.stop_loss_pct === firstConfig.stop_loss_pct)
  const allSameTP = activeConfigs.every(c => c.take_profit_pct === firstConfig.take_profit_pct)

  // Calculate min/max for ranges
  const margins = activeConfigs.map(c => Number(c.margin_usd))
  const leverages = activeConfigs.map(c => c.leverage)
  const stopLosses = activeConfigs.map(c => Number(c.stop_loss_pct))
  const takeProfits = activeConfigs.map(c => Number(c.take_profit_pct))

  const formatRange = (values: number[], prefix = '', suffix = '') => {
    const min = Math.min(...values)
    const max = Math.max(...values)
    if (min === max) return `${prefix}${min}${suffix}`
    return `${prefix}${min}-${max}${suffix}`
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1 text-xs text-blue-500 mb-2">
        <Layers className="w-3 h-3" />
        <span>{activeConfigs.length} ativos configurados</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <p className="text-muted-foreground">Alavancagem</p>
          <p className="font-medium text-gray-900 dark:text-white">
            {allSameLeverage ? `${firstConfig.leverage}x` : formatRange(leverages, '', 'x')}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Margem</p>
          <p className="font-medium text-gray-900 dark:text-white">
            {allSameMargin ? `$${firstConfig.margin_usd}` : formatRange(margins, '$')}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Stop Loss</p>
          <p className="font-medium text-red-600">
            {allSameSL ? `${firstConfig.stop_loss_pct}%` : formatRange(stopLosses, '', '%')}
          </p>
        </div>
        <div>
          <p className="text-muted-foreground">Take Profit</p>
          <p className="font-medium text-green-600">
            {allSameTP ? `${firstConfig.take_profit_pct}%` : formatRange(takeProfits, '', '%')}
          </p>
        </div>
      </div>
    </div>
  )
}

const BotsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const [selectedBot, setSelectedBot] = useState<BotType | null>(null)
  const [selectedSubscription, setSelectedSubscription] = useState<BotSubscription | null>(null)
  const [isSubscribeModalOpen, setIsSubscribeModalOpen] = useState(false)
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false)
  const [isSymbolConfigsModalOpen, setIsSymbolConfigsModalOpen] = useState(false)
  const [subscriptionForSymbolConfigs, setSubscriptionForSymbolConfigs] = useState<BotSubscription | null>(null)
  const [botSymbolConfigs, setBotSymbolConfigs] = useState<BotSymbolConfigsCache>({})

  const userId = user?.id || ''

  const { data: availableBots = [], isLoading: loadingBots } = useQuery({
    queryKey: ['bots-available'],
    queryFn: () => botsService.getAvailableBots()
  })

  // Fetch symbol configs for all available bots
  useEffect(() => {
    const fetchAllSymbolConfigs = async () => {
      if (!availableBots || availableBots.length === 0) return

      const apiUrl = import.meta.env.VITE_API_URL || ''
      const newConfigs: BotSymbolConfigsCache = {}

      await Promise.all(
        availableBots.map(async (bot) => {
          try {
            const response = await fetch(`${apiUrl}/api/v1/bot-subscriptions/bot/${bot.id}/symbol-configs`)
            if (response.ok) {
              const data = await response.json()
              if (data.success && data.data?.configs) {
                newConfigs[bot.id] = data.data.configs
              }
            }
          } catch (error) {
            console.error(`Error fetching symbol configs for bot ${bot.id}:`, error)
          }
        })
      )

      setBotSymbolConfigs(newConfigs)
    }

    fetchAllSymbolConfigs()
  }, [availableBots])

  const { data: mySubscriptions = [], isLoading: loadingSubscriptions } = useQuery({
    queryKey: ['bot-subscriptions', userId],
    queryFn: () => botsService.getMySubscriptions(userId),
    staleTime: 0, // Always fetch fresh data
    gcTime: 30 * 1000, // 30 seconds cache
    refetchOnWindowFocus: true
  })

  const { data: exchangeAccounts = [] } = useExchangeAccounts()

  const subscribeMutation = useMutation({
    mutationFn: (data: CreateMultiExchangeSubscriptionData) => botsService.subscribeToBotMultiExchange(userId, data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['bot-subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['bots-available'] })
      alert(`Bot ativado com sucesso em ${result.exchanges_count} exchange(s)!`)
    },
    onError: (error: any) => {
      alert(`Erro ao ativar bot: ${error.message}`)
    }
  })

  const toggleSubscriptionMutation = useMutation({
    mutationFn: ({ subscriptionId, action }: { subscriptionId: string, action: 'pause' | 'resume' }) => {
      if (action === 'pause') {
        return botsService.pauseSubscription(subscriptionId, userId)
      } else {
        return botsService.resumeSubscription(subscriptionId, userId)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bot-subscriptions'] })
    }
  })

  const unsubscribeMutation = useMutation({
    mutationFn: (subscriptionId: string) => botsService.unsubscribeFromBot(subscriptionId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bot-subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['bots-available'] })
      alert('Bot desativado com sucesso!')
    },
    onError: (error: any) => {
      alert(`Erro ao desativar bot: ${error.message}`)
    }
  })

  const handleSubscribe = (bot: BotType) => {
    setSelectedBot(bot)
    setIsSubscribeModalOpen(true)
  }

  const handlePause = (subscription: BotSubscription, e: React.MouseEvent) => {
    e.stopPropagation()
    // For multi-exchange, pause all exchanges
    const subscriptionIds = subscription.exchanges?.map(ex => ex.subscription_id) || [subscription.id]
    if (confirm(`Deseja pausar este bot? ${subscriptionIds.length > 1 ? `(${subscriptionIds.length} exchanges serao pausadas)` : ''}`)) {
      // Pause all subscriptions
      subscriptionIds.forEach(subId => {
        if (subId) toggleSubscriptionMutation.mutate({ subscriptionId: subId, action: 'pause' })
      })
    }
  }

  const handleReactivate = async (subscription: BotSubscription, bot: BotType, e: React.MouseEvent) => {
    e.stopPropagation()
    // Delete all existing subscriptions and open modal for new config
    const subscriptionIds = subscription.exchanges?.map(ex => ex.subscription_id) || [subscription.id]
    const exchangesText = subscriptionIds.length > 1 ? ` (${subscriptionIds.length} exchanges)` : ''
    if (confirm(`Para reconfigurar o bot${exchangesText}, a(s) assinatura(s) atual(is) sera(o) removida(s).\n\nVoce podera configurar novamente com as novas opcoes.`)) {
      try {
        // Unsubscribe from all exchanges
        for (const subId of subscriptionIds) {
          if (subId) await botsService.unsubscribeFromBot(subId, userId)
        }
        queryClient.invalidateQueries({ queryKey: ['bot-subscriptions'] })
        // Open modal for new config
        setSelectedBot(bot)
        setIsSubscribeModalOpen(true)
      } catch (error: any) {
        alert(`Erro ao preparar reconfiguracao: ${error.message}`)
      }
    }
  }

  const handleViewDetails = (subscription: BotSubscription, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedSubscription(subscription)
    setIsDetailsModalOpen(true)
  }

  const handleUnsubscribe = (subscription: BotSubscription, e: React.MouseEvent) => {
    e.stopPropagation()
    const subscriptionIds = subscription.exchanges?.map(ex => ex.subscription_id) || [subscription.id]
    const exchangesText = subscriptionIds.length > 1 ? ` de ${subscriptionIds.length} exchanges` : ''
    if (confirm(`Tem certeza que deseja DESATIVAR este bot${exchangesText}?\n\nIsso ira cancelar sua(s) assinatura(s) e voce precisara reconfigurar o bot para ativa-lo novamente.`)) {
      // Unsubscribe from all exchanges
      subscriptionIds.forEach(subId => {
        if (subId) unsubscribeMutation.mutate(subId)
      })
    }
  }

  const getSubscription = (botId: string): BotSubscription | undefined => {
    return mySubscriptions.find(sub => sub.bot_id === botId)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Bot className="w-8 h-8" />
          Bots Gerenciados
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Bots automatizados de copy-trading gerenciados pela plataforma
        </p>
      </div>

      <div className="space-y-4">
        {loadingBots || loadingSubscriptions ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner />
          </div>
        ) : availableBots.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-muted-foreground">Nenhum bot disponível no momento</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {availableBots.map((bot) => {
              const subscription = getSubscription(bot.id)
              const isSubscribed = !!subscription
              const isActive = subscription?.status === 'active'

              return (
                <Card key={bot.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex items-center justify-between mb-2">
                      <CardTitle className="text-xl">{bot.name}</CardTitle>
                      <Badge variant={bot.market_type === 'futures' ? 'default' : 'secondary'}>
                        {bot.market_type === 'futures' ? '⚡ FUTURES' : '💰 SPOT'}
                      </Badge>
                    </div>
                    <CardDescription className="min-h-[60px]">
                      {bot.description}
                    </CardDescription>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-3 text-sm border-t pt-4">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-4 h-4 text-muted-foreground" />
                        <div>
                          <p className="text-muted-foreground text-xs">Assinantes</p>
                          <p className="font-medium text-gray-900 dark:text-white">{bot.total_subscribers}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Activity className="w-4 h-4 text-muted-foreground" />
                        <div>
                          <p className="text-muted-foreground text-xs">Sinais</p>
                          <p className="font-medium text-gray-900 dark:text-white">{bot.total_signals_sent}</p>
                        </div>
                      </div>
                    </div>

                    <div className="border rounded-lg p-3 space-y-2 text-xs bg-gray-50 dark:bg-gray-900">
                      <p className="font-medium text-sm mb-2 text-gray-900 dark:text-white">
                        {isSubscribed ? 'Suas Configurações:' : 'Configurações Padrão:'}
                      </p>

                      {/* Mostrar ativo específico se for bot TradingView */}
                      {bot.trading_symbol && (
                        <div className="flex items-center gap-1 text-xs text-blue-500 mb-2">
                          <Layers className="w-3 h-3" />
                          <span>Ativo: <strong>{bot.trading_symbol}</strong></span>
                        </div>
                      )}

                      {/* Se inscrito com múltiplas exchanges, mostrar cada uma */}
                      {isSubscribed && subscription?.exchanges && subscription.exchanges.length > 1 ? (
                        <div className="space-y-3">
                          {subscription.exchanges.map((ex) => (
                            <div key={ex.subscription_id} className="border-t pt-2 first:border-t-0 first:pt-0">
                              <p className="font-medium text-xs text-primary mb-1">{ex.exchange.toUpperCase()} - {ex.account_name}</p>
                              <div className="grid grid-cols-4 gap-1 text-xs">
                                <div>
                                  <p className="text-muted-foreground text-[10px]">Alav.</p>
                                  <p className="font-medium text-gray-900 dark:text-white">{ex.custom_leverage || bot.default_leverage}x</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground text-[10px]">Margem</p>
                                  <p className="font-medium text-gray-900 dark:text-white">${ex.custom_margin_usd || bot.default_margin_usd}</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground text-[10px]">SL</p>
                                  <p className="font-medium text-red-600">{ex.custom_stop_loss_pct || bot.default_stop_loss_pct}%</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground text-[10px]">TP</p>
                                  <p className="font-medium text-green-600">{ex.custom_take_profit_pct || bot.default_take_profit_pct}%</p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : botSymbolConfigs[bot.id] && botSymbolConfigs[bot.id].length > 0 ? (
                        /* Bot com configuração por símbolo (estratégia interna) */
                        <SymbolConfigsSummary configs={botSymbolConfigs[bot.id]} botDefaults={bot} />
                      ) : (
                        /* Bot TradingView ou sem configs - mostrar valores padrão do bot */
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <p className="text-muted-foreground">Alavancagem</p>
                            <p className="font-medium text-gray-900 dark:text-white">
                              {isSubscribed && subscription?.exchanges?.[0]?.custom_leverage
                                ? subscription.exchanges[0].custom_leverage
                                : bot.default_leverage}x
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Margem</p>
                            <p className="font-medium text-gray-900 dark:text-white">
                              ${isSubscribed && subscription?.exchanges?.[0]?.custom_margin_usd
                                ? subscription.exchanges[0].custom_margin_usd
                                : bot.default_margin_usd}
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Stop Loss</p>
                            <p className="font-medium text-red-600">
                              {isSubscribed && subscription?.exchanges?.[0]?.custom_stop_loss_pct
                                ? subscription.exchanges[0].custom_stop_loss_pct
                                : bot.default_stop_loss_pct}%
                            </p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Take Profit</p>
                            <p className="font-medium text-green-600">
                              {isSubscribed && subscription?.exchanges?.[0]?.custom_take_profit_pct
                                ? subscription.exchanges[0].custom_take_profit_pct
                                : bot.default_take_profit_pct}%
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      {!isSubscribed ? (
                        <Button
                          className="w-full bg-green-600 hover:bg-green-700 text-white"
                          onClick={() => handleSubscribe(bot)}
                          disabled={subscribeMutation.isPending}
                        >
                          <Settings className="w-4 h-4 mr-2" />
                          Ativar Bot
                        </Button>
                      ) : (
                        <>
                          <div className="flex flex-col gap-2 p-3 bg-yellow-100 dark:bg-yellow-900/30 border-2 border-yellow-500 rounded-lg">
                            <div className="flex items-center justify-center gap-2">
                              <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                              <span className="font-semibold text-yellow-700 dark:text-yellow-400">
                                {isActive ? 'Bot Ativado' : 'Bot Pausado'}
                              </span>
                            </div>
                            {/* Show active exchanges */}
                            {subscription.exchanges && subscription.exchanges.length > 0 && (
                              <div className="flex items-center justify-center gap-1 flex-wrap">
                                {subscription.exchanges.map((ex) => (
                                  <Badge
                                    key={ex.subscription_id}
                                    variant={ex.status === 'active' ? 'default' : 'secondary'}
                                    className="text-xs"
                                  >
                                    {ex.exchange.toUpperCase()}
                                  </Badge>
                                ))}
                              </div>
                            )}
                            {/* Fallback for old single-exchange structure */}
                            {!subscription.exchanges && subscription.exchange && (
                              <div className="flex items-center justify-center">
                                <Badge variant="default" className="text-xs">
                                  {subscription.exchange.toUpperCase()}
                                </Badge>
                              </div>
                            )}
                          </div>

                          <div className="grid grid-cols-3 gap-2">
                            {isActive ? (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => handlePause(subscription, e)}
                                disabled={toggleSubscriptionMutation.isPending}
                                className="border-orange-500 text-orange-600 hover:bg-orange-50"
                              >
                                <Pause className="w-4 h-4 mr-1" /> Pausar
                              </Button>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={(e) => handleReactivate(subscription, bot, e)}
                                disabled={subscribeMutation.isPending}
                                className="border-green-500 text-green-600 hover:bg-green-50"
                              >
                                <Settings className="w-4 h-4 mr-1" /> Reconfigurar
                              </Button>
                            )}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => handleViewDetails(subscription, e)}
                              className="border-blue-500 text-blue-600 hover:bg-blue-50"
                            >
                              <Info className="w-4 h-4 mr-1" />
                              Detalhes
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => handleUnsubscribe(subscription, e)}
                              disabled={unsubscribeMutation.isPending}
                              className="border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                            >
                              <XCircle className="w-4 h-4 mr-1" />
                              Desativar
                            </Button>
                          </div>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <SubscribeBotModal
        isOpen={isSubscribeModalOpen}
        onClose={() => {
          setIsSubscribeModalOpen(false)
          setSelectedBot(null)
        }}
        onSubmit={(data) => subscribeMutation.mutateAsync(data)}
        bot={selectedBot}
        exchangeAccounts={exchangeAccounts.map(acc => ({
          id: acc.id,
          name: acc.name,
          exchange: acc.exchange
        }))}
        isLoading={subscribeMutation.isPending}
      />

      <BotDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => {
          setIsDetailsModalOpen(false)
          setSelectedSubscription(null)
        }}
        subscription={selectedSubscription}
      />
    </div>
  )
}

export default BotsPage
