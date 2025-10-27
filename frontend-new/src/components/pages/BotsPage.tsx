import React, { useState } from 'react'
import { Bot, Activity, Pause, Play, Settings, TrendingUp, Info } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { botsService, Bot as BotType, BotSubscription, CreateSubscriptionData } from '@/services/botsService'
import { SubscribeBotModal } from '../molecules/SubscribeBotModal'
import { BotDetailsModal } from '../molecules/BotDetailsModal'
import { useExchangeAccounts } from '@/hooks/useExchangeAccounts'

const BotsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedBot, setSelectedBot] = useState<BotType | null>(null)
  const [selectedSubscription, setSelectedSubscription] = useState<BotSubscription | null>(null)
  const [isSubscribeModalOpen, setIsSubscribeModalOpen] = useState(false)
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false)

  const userId = 'd89ebba5-acfb-44b3-921e-8448dda599ba'

  const { data: availableBots = [], isLoading: loadingBots } = useQuery({
    queryKey: ['bots-available'],
    queryFn: () => botsService.getAvailableBots()
  })

  const { data: mySubscriptions = [], isLoading: loadingSubscriptions } = useQuery({
    queryKey: ['bot-subscriptions', userId],
    queryFn: () => botsService.getMySubscriptions(userId)
  })

  const { data: exchangeAccounts = [] } = useExchangeAccounts()

  const subscribeMutation = useMutation({
    mutationFn: (data: CreateSubscriptionData) => botsService.subscribeToBot(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bot-subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['bots-available'] })
      alert('✅ Bot ativado com sucesso!')
    },
    onError: (error: any) => {
      alert(`❌ Erro ao ativar bot: ${error.message}`)
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

  const handleSubscribe = (bot: BotType) => {
    setSelectedBot(bot)
    setIsSubscribeModalOpen(true)
  }

  const handleTogglePause = (subscription: BotSubscription, e: React.MouseEvent) => {
    e.stopPropagation()
    const action = subscription.status === 'active' ? 'pause' : 'resume'
    const message = action === 'pause'
      ? 'Deseja pausar este bot? Você deixará de receber sinais.'
      : 'Deseja reativar este bot? Você voltará a receber sinais.'

    if (confirm(message)) {
      toggleSubscriptionMutation.mutate({ subscriptionId: subscription.id, action })
    }
  }

  const handleViewDetails = (subscription: BotSubscription, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedSubscription(subscription)
    setIsDetailsModalOpen(true)
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
                      <p className="font-medium text-sm mb-2 text-gray-900 dark:text-white">Configurações Padrão:</p>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <p className="text-muted-foreground">Alavancagem</p>
                          <p className="font-medium text-gray-900 dark:text-white">{bot.default_leverage}x</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Margem</p>
                          <p className="font-medium text-gray-900 dark:text-white">${bot.default_margin_usd}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Stop Loss</p>
                          <p className="font-medium text-red-600">{bot.default_stop_loss_pct}%</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">Take Profit</p>
                          <p className="font-medium text-green-600">{bot.default_take_profit_pct}%</p>
                        </div>
                      </div>
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
                          <div className="flex items-center justify-center gap-2 p-3 bg-yellow-100 dark:bg-yellow-900/30 border-2 border-yellow-500 rounded-lg">
                            <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                            <span className="font-semibold text-yellow-700 dark:text-yellow-400">
                              {isActive ? 'Bot Ativado' : 'Bot Pausado'}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => handleTogglePause(subscription, e)}
                              disabled={toggleSubscriptionMutation.isPending}
                              className={isActive ? 'border-orange-500 text-orange-600 hover:bg-orange-50' : 'border-green-500 text-green-600 hover:bg-green-50'}
                            >
                              {isActive ? (
                                <><Pause className="w-4 h-4 mr-1" /> Pausar</>
                              ) : (
                                <><Play className="w-4 h-4 mr-1" /> Reativar</>
                              )}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => handleViewDetails(subscription, e)}
                              className="border-blue-500 text-blue-600 hover:bg-blue-50"
                            >
                              <Info className="w-4 h-4 mr-1" />
                              Detalhes
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
