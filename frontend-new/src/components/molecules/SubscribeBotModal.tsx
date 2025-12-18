import React, { useState, useEffect } from 'react'
import { X, TrendingUp, Shield, DollarSign, Settings, Check } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { Bot, CreateMultiExchangeSubscriptionData, ExchangeConfig } from '@/services/botsService'

interface SubscribeBotModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateMultiExchangeSubscriptionData) => Promise<void>
  bot: Bot | null
  exchangeAccounts: Array<{ id: string; name: string; exchange: string }>
  isLoading?: boolean
}

// Default config for each exchange
const getDefaultExchangeConfig = (exchangeId: string): ExchangeConfig => ({
  exchange_account_id: exchangeId,
  custom_leverage: undefined,
  custom_margin_usd: undefined,
  custom_stop_loss_pct: undefined,
  custom_take_profit_pct: undefined,
  max_daily_loss_usd: 200.00,
  max_concurrent_positions: 3
})

export const SubscribeBotModal: React.FC<SubscribeBotModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  bot,
  exchangeAccounts,
  isLoading = false
}) => {
  // Selected exchanges (multi-select, max 3)
  const [selectedExchanges, setSelectedExchanges] = useState<string[]>([])

  // Config mode: true = same for all, false = individual
  const [useSameConfig, setUseSameConfig] = useState(true)

  // Selected tab for individual config (exchange account id)
  const [selectedConfigTab, setSelectedConfigTab] = useState<string>('')

  // Shared config settings (when useSameConfig=true)
  const [sharedConfig, setSharedConfig] = useState({
    custom_leverage: undefined as number | undefined,
    custom_margin_usd: undefined as number | undefined,
    custom_stop_loss_pct: undefined as number | undefined,
    custom_take_profit_pct: undefined as number | undefined,
    max_daily_loss_usd: 200.00,
    max_concurrent_positions: 3
  })

  const [useCustomSettings, setUseCustomSettings] = useState({
    leverage: false,
    margin: false,
    stopLoss: false,
    takeProfit: false
  })

  // Individual configs (when useSameConfig=false)
  const [individualConfigs, setIndividualConfigs] = useState<Record<string, ExchangeConfig>>({})
  const [individualCustomSettings, setIndividualCustomSettings] = useState<Record<string, typeof useCustomSettings>>({})

  // Reset form when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setSelectedExchanges([])
      setUseSameConfig(true)
      setSelectedConfigTab('')
      setSharedConfig({
        custom_leverage: undefined,
        custom_margin_usd: undefined,
        custom_stop_loss_pct: undefined,
        custom_take_profit_pct: undefined,
        max_daily_loss_usd: 200.00,
        max_concurrent_positions: 3
      })
      setUseCustomSettings({
        leverage: false,
        margin: false,
        stopLoss: false,
        takeProfit: false
      })
      setIndividualConfigs({})
      setIndividualCustomSettings({})
    }
  }, [isOpen])

  // Update selectedConfigTab when exchanges change
  useEffect(() => {
    if (selectedExchanges.length > 0 && !selectedExchanges.includes(selectedConfigTab)) {
      setSelectedConfigTab(selectedExchanges[0])
    }
    // Initialize individual configs for new exchanges
    selectedExchanges.forEach(exId => {
      if (!individualConfigs[exId]) {
        setIndividualConfigs(prev => ({
          ...prev,
          [exId]: getDefaultExchangeConfig(exId)
        }))
        setIndividualCustomSettings(prev => ({
          ...prev,
          [exId]: { leverage: false, margin: false, stopLoss: false, takeProfit: false }
        }))
      }
    })
  }, [selectedExchanges])

  const toggleExchange = (exchangeId: string) => {
    setSelectedExchanges(prev => {
      if (prev.includes(exchangeId)) {
        return prev.filter(id => id !== exchangeId)
      }
      if (prev.length >= 3) {
        alert('Maximo de 3 exchanges por bot!')
        return prev
      }
      return [...prev, exchangeId]
    })
  }

  const getExchangeName = (exchangeId: string) => {
    const account = exchangeAccounts.find(a => a.id === exchangeId)
    return account ? `${account.exchange.toUpperCase()} - ${account.name}` : exchangeId
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (selectedExchanges.length === 0) {
      alert('Por favor, selecione pelo menos uma conta de exchange')
      return
    }

    let dataToSubmit: CreateMultiExchangeSubscriptionData

    if (useSameConfig) {
      dataToSubmit = {
        bot_id: bot?.id || '',
        exchange_account_ids: selectedExchanges,
        use_same_config: true,
        custom_leverage: useCustomSettings.leverage ? sharedConfig.custom_leverage : undefined,
        custom_margin_usd: useCustomSettings.margin ? sharedConfig.custom_margin_usd : undefined,
        custom_stop_loss_pct: useCustomSettings.stopLoss ? sharedConfig.custom_stop_loss_pct : undefined,
        custom_take_profit_pct: useCustomSettings.takeProfit ? sharedConfig.custom_take_profit_pct : undefined,
        max_daily_loss_usd: sharedConfig.max_daily_loss_usd,
        max_concurrent_positions: sharedConfig.max_concurrent_positions
      }
    } else {
      // Build individual configs
      const configs: ExchangeConfig[] = selectedExchanges.map(exId => {
        const config = individualConfigs[exId] || getDefaultExchangeConfig(exId)
        const customSettings = individualCustomSettings[exId] || { leverage: false, margin: false, stopLoss: false, takeProfit: false }
        return {
          exchange_account_id: exId,
          custom_leverage: customSettings.leverage ? config.custom_leverage : undefined,
          custom_margin_usd: customSettings.margin ? config.custom_margin_usd : undefined,
          custom_stop_loss_pct: customSettings.stopLoss ? config.custom_stop_loss_pct : undefined,
          custom_take_profit_pct: customSettings.takeProfit ? config.custom_take_profit_pct : undefined,
          max_daily_loss_usd: config.max_daily_loss_usd,
          max_concurrent_positions: config.max_concurrent_positions
        }
      })
      dataToSubmit = {
        bot_id: bot?.id || '',
        exchange_account_ids: selectedExchanges,
        use_same_config: false,
        max_daily_loss_usd: 200, // fallback, will use individual
        max_concurrent_positions: 3, // fallback
        individual_configs: configs
      }
    }

    try {
      await onSubmit(dataToSubmit)
      onClose()
    } catch (error: any) {
      alert(error.message || 'Erro ao assinar bot')
    }
  }

  // Get current config based on mode
  const getCurrentConfig = () => {
    if (useSameConfig) {
      return sharedConfig
    }
    return individualConfigs[selectedConfigTab] || getDefaultExchangeConfig(selectedConfigTab)
  }

  const getCurrentCustomSettings = () => {
    if (useSameConfig) {
      return useCustomSettings
    }
    return individualCustomSettings[selectedConfigTab] || { leverage: false, margin: false, stopLoss: false, takeProfit: false }
  }

  const updateConfig = (field: string, value: any) => {
    if (useSameConfig) {
      setSharedConfig(prev => ({ ...prev, [field]: value }))
    } else {
      setIndividualConfigs(prev => ({
        ...prev,
        [selectedConfigTab]: { ...prev[selectedConfigTab], [field]: value }
      }))
    }
  }

  const updateCustomSetting = (field: string, value: boolean) => {
    if (useSameConfig) {
      setUseCustomSettings(prev => ({ ...prev, [field]: value }))
    } else {
      setIndividualCustomSettings(prev => ({
        ...prev,
        [selectedConfigTab]: { ...prev[selectedConfigTab], [field]: value }
      }))
    }
  }

  if (!bot) return null

  const currentConfig = getCurrentConfig()
  const currentCustomSettings = getCurrentCustomSettings()

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[650px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Configurar Bot: {bot.name}
            </DialogTitle>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              type="button"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            {bot.description}
          </p>
          <div className="flex items-center gap-2 mt-2">
            <Badge variant={bot.market_type === 'futures' ? 'default' : 'secondary'}>
              {bot.market_type === 'futures' ? 'FUTURES' : 'SPOT'}
            </Badge>
            <Badge variant="outline">
              {bot.total_subscribers} assinantes
            </Badge>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6 mt-4">
          {/* Exchange Selection - Multi-select checkboxes */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Contas de Exchange * (max 3)
            </label>
            <div className="border rounded-lg p-3 space-y-2 max-h-48 overflow-y-auto">
              {exchangeAccounts.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhuma conta de exchange cadastrada</p>
              ) : (
                exchangeAccounts.map((account) => {
                  const isSelected = selectedExchanges.includes(account.id)
                  return (
                    <label
                      key={account.id}
                      className={`flex items-center gap-3 p-2 rounded-md cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-primary/10 border border-primary'
                          : 'hover:bg-muted border border-transparent'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded border flex items-center justify-center ${
                        isSelected ? 'bg-primary border-primary' : 'border-input'
                      }`}>
                        {isSelected && <Check className="w-3 h-3 text-white" />}
                      </div>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleExchange(account.id)}
                        className="hidden"
                      />
                      <div className="flex-1">
                        <span className="font-medium text-sm">{account.exchange.toUpperCase()}</span>
                        <span className="text-muted-foreground text-sm ml-2">- {account.name}</span>
                      </div>
                    </label>
                  )
                })
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              Selecione ate 3 exchanges para executar as ordens simultaneamente
            </p>
            {selectedExchanges.length > 0 && (
              <p className="text-xs text-primary font-medium">
                {selectedExchanges.length} exchange(s) selecionada(s)
              </p>
            )}
          </div>

          {/* Config Mode Toggle (only show if 2+ exchanges selected) */}
          {selectedExchanges.length >= 2 && (
            <div className="border rounded-lg p-4 bg-secondary/30">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">Modo de Configuracao</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {useSameConfig
                      ? 'Todas exchanges usarao a mesma configuracao'
                      : 'Configure cada exchange individualmente'}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setUseSameConfig(true)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      useSameConfig
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
                    }`}
                  >
                    Mesma Config
                  </button>
                  <button
                    type="button"
                    onClick={() => setUseSameConfig(false)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      !useSameConfig
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary text-muted-foreground hover:bg-secondary/80'
                    }`}
                  >
                    Config Individual
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Exchange Tabs (only show if individual config mode) */}
          {!useSameConfig && selectedExchanges.length >= 2 && (
            <div className="flex gap-2 overflow-x-auto pb-2">
              {selectedExchanges.map((exId) => {
                const account = exchangeAccounts.find(a => a.id === exId)
                return (
                  <button
                    key={exId}
                    type="button"
                    onClick={() => setSelectedConfigTab(exId)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                      selectedConfigTab === exId
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-secondary/50 text-muted-foreground hover:bg-secondary'
                    }`}
                  >
                    {account?.exchange.toUpperCase()} - {account?.name}
                  </button>
                )
              })}
            </div>
          )}

          {/* Trading Settings */}
          <div className="border rounded-lg p-4 space-y-4">
            <h3 className="font-medium flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Configuracoes de Trading
              {useSameConfig && selectedExchanges.length > 1 && (
                <Badge variant="outline" className="ml-2 text-xs">
                  Mesma config para todas exchanges
                </Badge>
              )}
              {!useSameConfig && selectedConfigTab && (
                <Badge variant="default" className="ml-2 text-xs">
                  {getExchangeName(selectedConfigTab)}
                </Badge>
              )}
            </h3>

            {/* Leverage */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Alavancagem</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={currentCustomSettings.leverage}
                    onChange={(e) => updateCustomSetting('leverage', e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {currentCustomSettings.leverage ? (
                <input
                  type="number"
                  value={currentConfig.custom_leverage || ''}
                  onChange={(e) => updateConfig('custom_leverage', Number(e.target.value))}
                  placeholder={`Padrao: ${bot.default_leverage}x`}
                  min="1"
                  max="125"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrao do bot: <span className="font-semibold">{bot.default_leverage}x</span>
                </div>
              )}
            </div>

            {/* Margin */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Margem por Operacao (USD)</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={currentCustomSettings.margin}
                    onChange={(e) => updateCustomSetting('margin', e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {currentCustomSettings.margin ? (
                <input
                  type="number"
                  value={currentConfig.custom_margin_usd || ''}
                  onChange={(e) => updateConfig('custom_margin_usd', Number(e.target.value))}
                  placeholder={`Padrao: $${bot.default_margin_usd}`}
                  min="5"
                  step="0.01"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrao do bot: <span className="font-semibold">${bot.default_margin_usd}</span>
                </div>
              )}
            </div>

            {/* Stop Loss */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Stop Loss (%)</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={currentCustomSettings.stopLoss}
                    onChange={(e) => updateCustomSetting('stopLoss', e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {currentCustomSettings.stopLoss ? (
                <input
                  type="number"
                  value={currentConfig.custom_stop_loss_pct || ''}
                  onChange={(e) => updateConfig('custom_stop_loss_pct', Number(e.target.value))}
                  placeholder={`Padrao: ${bot.default_stop_loss_pct}%`}
                  min="0.1"
                  max="50"
                  step="0.1"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrao do bot: <span className="font-semibold">{bot.default_stop_loss_pct}%</span>
                </div>
              )}
            </div>

            {/* Take Profit */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Take Profit (%)</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={currentCustomSettings.takeProfit}
                    onChange={(e) => updateCustomSetting('takeProfit', e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {currentCustomSettings.takeProfit ? (
                <input
                  type="number"
                  value={currentConfig.custom_take_profit_pct || ''}
                  onChange={(e) => updateConfig('custom_take_profit_pct', Number(e.target.value))}
                  placeholder={`Padrao: ${bot.default_take_profit_pct}%`}
                  min="0.1"
                  max="100"
                  step="0.1"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrao do bot: <span className="font-semibold">{bot.default_take_profit_pct}%</span>
                </div>
              )}
            </div>
          </div>

          {/* Risk Management */}
          <div className="border rounded-lg p-4 space-y-4">
            <h3 className="font-medium flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Gestao de Risco
              {!useSameConfig && selectedConfigTab && (
                <Badge variant="default" className="ml-2 text-xs">
                  {getExchangeName(selectedConfigTab)}
                </Badge>
              )}
            </h3>

            <div className="space-y-2">
              <label className="text-sm font-medium">Perda Maxima Diaria (USD) *</label>
              <input
                type="number"
                value={currentConfig.max_daily_loss_usd}
                onChange={(e) => updateConfig('max_daily_loss_usd', Number(e.target.value))}
                min="10"
                step="0.01"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
              <p className="text-xs text-muted-foreground">
                Bot sera pausado automaticamente se atingir esta perda no dia
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Maximo de Posicoes Simultaneas *</label>
              <input
                type="number"
                value={currentConfig.max_concurrent_positions}
                onChange={(e) => updateConfig('max_concurrent_positions', Number(e.target.value))}
                min="1"
                max="10"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
              <p className="text-xs text-muted-foreground">
                Numero maximo de operacoes abertas ao mesmo tempo
              </p>
            </div>
          </div>

          {/* Summary for individual configs */}
          {!useSameConfig && selectedExchanges.length >= 2 && (
            <div className="border rounded-lg p-4 bg-secondary/20">
              <h4 className="font-medium text-sm mb-3">Resumo das Configuracoes</h4>
              <div className="space-y-2">
                {selectedExchanges.map(exId => {
                  const account = exchangeAccounts.find(a => a.id === exId)
                  const config = individualConfigs[exId]
                  const customSettings = individualCustomSettings[exId]
                  return (
                    <div key={exId} className="flex items-center justify-between text-xs bg-background rounded p-2">
                      <span className="font-medium">{account?.exchange.toUpperCase()}</span>
                      <div className="flex gap-3 text-muted-foreground">
                        <span>Alav: {customSettings?.leverage ? config?.custom_leverage : bot.default_leverage}x</span>
                        <span>Margem: ${customSettings?.margin ? config?.custom_margin_usd : bot.default_margin_usd}</span>
                        <span>Max Loss: ${config?.max_daily_loss_usd || 200}</span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading || selectedExchanges.length === 0}>
              {isLoading ? 'Ativando...' : `Ativar Bot ${selectedExchanges.length > 0 ? `(${selectedExchanges.length} exchange${selectedExchanges.length > 1 ? 's' : ''})` : ''}`}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
