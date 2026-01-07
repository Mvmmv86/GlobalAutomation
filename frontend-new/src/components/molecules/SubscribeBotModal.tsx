import React, { useState, useEffect } from 'react'
import { X, TrendingUp, Shield, DollarSign, Settings, Check, ChevronDown, ChevronUp, ToggleLeft, ToggleRight, RefreshCw, Layers, Webhook } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { Bot, CreateMultiExchangeSubscriptionData, ExchangeConfig, botsService, BotSymbolConfig } from '@/services/botsService'

/**
 * SubscribeBotModal - Modal para cliente ativar bot
 *
 * IMPORTANTE: Existem dois tipos de bots:
 * 1. Bots TradingView (webhook externo): tem trading_symbol definido, opera APENAS esse ativo
 *    - Interface simplificada: mostra só o ativo fixo com campos de configuração editáveis
 * 2. Bots de Estratégia Interna: NÃO tem trading_symbol, pode operar múltiplos ativos
 *    - Interface completa: mostra lista de ativos configurados pelo admin
 */

// Symbol config for client customization
interface SymbolConfigLocal {
  symbol: string
  is_active: boolean
  use_bot_default: boolean
  custom_leverage?: number
  custom_margin_usd?: number
  custom_stop_loss_pct?: number
  custom_take_profit_pct?: number
  bot_config?: BotSymbolConfig // Config from admin
}

interface SubscribeBotModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateMultiExchangeSubscriptionData) => Promise<void>
  bot: Bot | null
  exchangeAccounts: Array<{ id: string; name: string; exchange: string }>
  isLoading?: boolean
}

// Default config for each exchange (uses bot's default_max_positions if available)
const getDefaultExchangeConfig = (exchangeId: string, botDefaultMaxPositions?: number): ExchangeConfig => ({
  exchange_account_id: exchangeId,
  custom_leverage: undefined,
  custom_margin_usd: undefined,
  custom_stop_loss_pct: undefined,
  custom_take_profit_pct: undefined,
  max_daily_loss_usd: 200.00,
  max_concurrent_positions: botDefaultMaxPositions || 3
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
  // Uses bot's default_max_positions if available
  const [sharedConfig, setSharedConfig] = useState({
    custom_leverage: undefined as number | undefined,
    custom_margin_usd: undefined as number | undefined,
    custom_stop_loss_pct: undefined as number | undefined,
    custom_take_profit_pct: undefined as number | undefined,
    max_daily_loss_usd: 200.00,
    max_concurrent_positions: bot?.default_max_positions || 3
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

  // Symbol configs (per-asset configuration)
  const [symbolConfigs, setSymbolConfigs] = useState<SymbolConfigLocal[]>([])
  const [isLoadingSymbols, setIsLoadingSymbols] = useState(false)
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null)
  const [selectedSymbolExchange, setSelectedSymbolExchange] = useState<string>('')

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
        max_concurrent_positions: bot?.default_max_positions || 3
      })
      setUseCustomSettings({
        leverage: false,
        margin: false,
        stopLoss: false,
        takeProfit: false
      })
      setIndividualConfigs({})
      setIndividualCustomSettings({})
      setSymbolConfigs([])
      setExpandedSymbol(null)
      setSelectedSymbolExchange('')
      // Load symbols from bot
      if (bot?.id) {
        loadBotSymbols(bot.id)
      }
    }
  }, [isOpen, bot?.id])

  // Load symbols configured by admin for this bot
  const loadBotSymbols = async (botId: string) => {
    setIsLoadingSymbols(true)
    console.log('🔄 [SubscribeBotModal] Loading symbols for bot:', botId)
    try {
      // Fetch bot symbol configs from public endpoint
      const apiUrl = import.meta.env.VITE_API_URL || ''
      const url = `${apiUrl}/api/v1/bot-subscriptions/bot/${botId}/symbol-configs`
      console.log('🌐 [SubscribeBotModal] Fetching from:', url)
      const response = await fetch(url)
      console.log('📡 [SubscribeBotModal] Response status:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('📦 [SubscribeBotModal] Response data:', data)
        if (data.success && data.data?.configs) {
          console.log('✅ [SubscribeBotModal] Found', data.data.configs.length, 'symbol configs')
          // Convert admin configs to local format - all active by default, using bot defaults
          const configs: SymbolConfigLocal[] = data.data.configs.map((cfg: any) => ({
            symbol: cfg.symbol,
            is_active: cfg.is_active,
            use_bot_default: true,
            bot_config: {
              symbol: cfg.symbol,
              leverage: cfg.leverage,
              margin_usd: cfg.margin_usd,
              stop_loss_pct: cfg.stop_loss_pct,
              take_profit_pct: cfg.take_profit_pct,
              max_positions: cfg.max_positions,
              is_active: cfg.is_active
            }
          }))
          setSymbolConfigs(configs)
          console.log('✅ [SubscribeBotModal] Symbol configs set:', configs)
        } else {
          console.log('⚠️ [SubscribeBotModal] No configs in response or success=false')
        }
      } else {
        console.error('❌ [SubscribeBotModal] Response not OK:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('❌ [SubscribeBotModal] Error loading bot symbols:', error)
    } finally {
      setIsLoadingSymbols(false)
    }
  }

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
          [exId]: getDefaultExchangeConfig(exId, bot?.default_max_positions)
        }))
        setIndividualCustomSettings(prev => ({
          ...prev,
          [exId]: { leverage: false, margin: false, stopLoss: false, takeProfit: false }
        }))
      }
    })
  }, [selectedExchanges, bot?.default_max_positions])

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

    // Note: custom_leverage/margin/sl/tp are now configured per-symbol (bot_symbol_configs)
    // We still send the subscription data with risk management settings
    if (useSameConfig) {
      dataToSubmit = {
        bot_id: bot?.id || '',
        exchange_account_ids: selectedExchanges,
        use_same_config: true,
        custom_leverage: undefined, // Now uses per-symbol config from admin
        custom_margin_usd: undefined, // Now uses per-symbol config from admin
        custom_stop_loss_pct: undefined, // Now uses per-symbol config from admin
        custom_take_profit_pct: undefined, // Now uses per-symbol config from admin
        max_daily_loss_usd: sharedConfig.max_daily_loss_usd,
        max_concurrent_positions: sharedConfig.max_concurrent_positions
      }
    } else {
      // Build individual configs (per exchange)
      const configs: ExchangeConfig[] = selectedExchanges.map(exId => {
        const config = individualConfigs[exId] || getDefaultExchangeConfig(exId, bot?.default_max_positions)
        return {
          exchange_account_id: exId,
          custom_leverage: undefined, // Now uses per-symbol config from admin
          custom_margin_usd: undefined, // Now uses per-symbol config from admin
          custom_stop_loss_pct: undefined, // Now uses per-symbol config from admin
          custom_take_profit_pct: undefined, // Now uses per-symbol config from admin
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
    return individualConfigs[selectedConfigTab] || getDefaultExchangeConfig(selectedConfigTab, bot?.default_max_positions)
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

  // Symbol config handlers
  const toggleSymbolActive = (symbol: string) => {
    setSymbolConfigs(prev => prev.map(cfg =>
      cfg.symbol === symbol ? { ...cfg, is_active: !cfg.is_active } : cfg
    ))
  }

  const toggleSymbolUseDefault = (symbol: string) => {
    setSymbolConfigs(prev => prev.map(cfg =>
      cfg.symbol === symbol ? { ...cfg, use_bot_default: !cfg.use_bot_default } : cfg
    ))
  }

  const updateSymbolConfig = (symbol: string, field: string, value: any) => {
    setSymbolConfigs(prev => prev.map(cfg =>
      cfg.symbol === symbol ? { ...cfg, [field]: value } : cfg
    ))
  }

  const activeSymbolsCount = symbolConfigs.filter(s => s.is_active).length

  if (!bot) return null

  const currentConfig = getCurrentConfig()
  const currentCustomSettings = getCurrentCustomSettings()

  // Detectar se é um bot TradingView (tem trading_symbol definido)
  const isTradingViewBot = Boolean(bot.trading_symbol)

  // Para bots TradingView, buscar ou criar config do ativo fixo
  const getTradingViewConfig = () => {
    if (!isTradingViewBot || !bot.trading_symbol) return null
    const existing = symbolConfigs.find(c => c.symbol === bot.trading_symbol)
    if (existing) return existing
    // Return default config based on bot defaults
    return {
      symbol: bot.trading_symbol,
      is_active: true,
      use_bot_default: false, // Cliente pode personalizar
      custom_leverage: bot.default_leverage || 10,
      custom_margin_usd: bot.default_margin_usd || 20,
      custom_stop_loss_pct: bot.default_stop_loss_pct || 3,
      custom_take_profit_pct: bot.default_take_profit_pct || 5,
      bot_config: undefined
    }
  }

  const tradingViewConfig = getTradingViewConfig()

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[650px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              {isTradingViewBot ? <Webhook className="w-5 h-5 text-orange-500" /> : <Settings className="w-5 h-5" />}
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
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <Badge variant={bot.market_type === 'futures' ? 'default' : 'secondary'}>
              {bot.market_type === 'futures' ? 'FUTURES' : 'SPOT'}
            </Badge>
            <Badge variant="outline">
              {bot.total_subscribers} assinantes
            </Badge>
            {isTradingViewBot && (
              <>
                <Badge variant="outline" className="bg-orange-500/10 text-orange-500 border-orange-500/30">
                  <Webhook className="w-3 h-3 mr-1" />
                  TradingView
                </Badge>
                <Badge variant="outline" className="bg-blue-500/10 text-blue-500 border-blue-500/30 font-mono">
                  {bot.trading_symbol}
                </Badge>
              </>
            )}
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

          {/* TradingView Bot Config - Interface Simplificada */}
          {isTradingViewBot && tradingViewConfig && (
            <div className="border rounded-lg p-4 space-y-4 border-orange-500/30 bg-orange-500/5">
              <div className="flex items-center justify-between">
                <h3 className="font-medium flex items-center gap-2">
                  <Webhook className="w-4 h-4 text-orange-500" />
                  Configuracao de Trading - {bot.trading_symbol}
                </h3>
                <Badge variant="outline" className="bg-orange-500/10 text-orange-500 border-orange-500/30 text-xs">
                  Bot TradingView
                </Badge>
              </div>

              <p className="text-xs text-muted-foreground">
                Este bot recebe sinais do TradingView para o ativo <strong>{bot.trading_symbol}</strong>.
                Configure abaixo os parametros de trading.
              </p>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Alavancagem</label>
                  <input
                    type="number"
                    value={tradingViewConfig.custom_leverage || bot.default_leverage || 10}
                    onChange={(e) => {
                      const value = Number(e.target.value)
                      if (symbolConfigs.find(c => c.symbol === bot.trading_symbol)) {
                        updateSymbolConfig(bot.trading_symbol!, 'custom_leverage', value)
                      } else {
                        // Add new config
                        setSymbolConfigs([{
                          symbol: bot.trading_symbol!,
                          is_active: true,
                          use_bot_default: false,
                          custom_leverage: value,
                          custom_margin_usd: bot.default_margin_usd || 20,
                          custom_stop_loss_pct: bot.default_stop_loss_pct || 3,
                          custom_take_profit_pct: bot.default_take_profit_pct || 5
                        }])
                      }
                    }}
                    min={1}
                    max={125}
                    className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <p className="text-xs text-muted-foreground">1x a 125x</p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Margem (USD)</label>
                  <input
                    type="number"
                    value={tradingViewConfig.custom_margin_usd || bot.default_margin_usd || 20}
                    onChange={(e) => {
                      const value = Number(e.target.value)
                      if (symbolConfigs.find(c => c.symbol === bot.trading_symbol)) {
                        updateSymbolConfig(bot.trading_symbol!, 'custom_margin_usd', value)
                      } else {
                        setSymbolConfigs([{
                          symbol: bot.trading_symbol!,
                          is_active: true,
                          use_bot_default: false,
                          custom_leverage: bot.default_leverage || 10,
                          custom_margin_usd: value,
                          custom_stop_loss_pct: bot.default_stop_loss_pct || 3,
                          custom_take_profit_pct: bot.default_take_profit_pct || 5
                        }])
                      }
                    }}
                    min={5}
                    step={0.01}
                    className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <p className="text-xs text-muted-foreground">Minimo $5</p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Stop Loss (%)</label>
                  <input
                    type="number"
                    value={tradingViewConfig.custom_stop_loss_pct || bot.default_stop_loss_pct || 3}
                    onChange={(e) => {
                      const value = Number(e.target.value)
                      if (symbolConfigs.find(c => c.symbol === bot.trading_symbol)) {
                        updateSymbolConfig(bot.trading_symbol!, 'custom_stop_loss_pct', value)
                      } else {
                        setSymbolConfigs([{
                          symbol: bot.trading_symbol!,
                          is_active: true,
                          use_bot_default: false,
                          custom_leverage: bot.default_leverage || 10,
                          custom_margin_usd: bot.default_margin_usd || 20,
                          custom_stop_loss_pct: value,
                          custom_take_profit_pct: bot.default_take_profit_pct || 5
                        }])
                      }
                    }}
                    min={0.1}
                    max={50}
                    step={0.1}
                    className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <p className="text-xs text-muted-foreground">0.1% a 50%</p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Take Profit (%)</label>
                  <input
                    type="number"
                    value={tradingViewConfig.custom_take_profit_pct || bot.default_take_profit_pct || 5}
                    onChange={(e) => {
                      const value = Number(e.target.value)
                      if (symbolConfigs.find(c => c.symbol === bot.trading_symbol)) {
                        updateSymbolConfig(bot.trading_symbol!, 'custom_take_profit_pct', value)
                      } else {
                        setSymbolConfigs([{
                          symbol: bot.trading_symbol!,
                          is_active: true,
                          use_bot_default: false,
                          custom_leverage: bot.default_leverage || 10,
                          custom_margin_usd: bot.default_margin_usd || 20,
                          custom_stop_loss_pct: bot.default_stop_loss_pct || 3,
                          custom_take_profit_pct: value
                        }])
                      }
                    }}
                    min={0.1}
                    max={100}
                    step={0.1}
                    className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <p className="text-xs text-muted-foreground">0.1% a 100%</p>
                </div>
              </div>
            </div>
          )}

          {/* Per-Symbol Configuration (Pastinhas) - Only for Strategy Bots */}
          {!isTradingViewBot && symbolConfigs.length > 0 && (
            <div className="border rounded-lg p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Configuracao por Ativo
                </h3>
                <div className="text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">{activeSymbolsCount}</span> de{' '}
                  <span className="font-medium text-foreground">{symbolConfigs.length}</span> ativos
                </div>
              </div>

              <p className="text-xs text-muted-foreground">
                Ative/desative ativos individualmente ou personalize as configuracoes. Por padrao, todos usam a config do admin.
              </p>

              {/* Symbol tabs/folders (pastinhas) */}
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {symbolConfigs.map((symbolCfg) => (
                  <div
                    key={symbolCfg.symbol}
                    className={`border rounded-lg overflow-hidden transition-all ${
                      symbolCfg.is_active ? 'border-border bg-card' : 'border-muted/50 bg-muted/20 opacity-70'
                    }`}
                  >
                    {/* Symbol Header (Pastinha) */}
                    <button
                      type="button"
                      onClick={() => setExpandedSymbol(expandedSymbol === symbolCfg.symbol ? null : symbolCfg.symbol)}
                      className="w-full flex items-center justify-between p-3 hover:bg-accent/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {/* Active/Inactive Toggle */}
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleSymbolActive(symbolCfg.symbol)
                          }}
                          className={`p-1 rounded transition-colors ${
                            symbolCfg.is_active ? 'text-green-500 hover:text-green-400' : 'text-muted-foreground hover:text-foreground'
                          }`}
                          title={symbolCfg.is_active ? 'Clique para desativar' : 'Clique para ativar'}
                        >
                          {symbolCfg.is_active ? (
                            <ToggleRight className="w-5 h-5" />
                          ) : (
                            <ToggleLeft className="w-5 h-5" />
                          )}
                        </button>

                        {/* Symbol Name */}
                        <span className="font-mono font-bold text-sm">{symbolCfg.symbol}</span>

                        {/* Status Badges */}
                        {!symbolCfg.is_active && (
                          <Badge variant="secondary" className="text-xs">Desativado</Badge>
                        )}
                        {symbolCfg.is_active && symbolCfg.use_bot_default && (
                          <Badge variant="outline" className="text-xs bg-blue-500/10 border-blue-500/30 text-blue-400">
                            Padrao Admin
                          </Badge>
                        )}
                        {symbolCfg.is_active && !symbolCfg.use_bot_default && (
                          <Badge variant="outline" className="text-xs bg-purple-500/10 border-purple-500/30 text-purple-400">
                            Personalizado
                          </Badge>
                        )}
                      </div>

                      <div className="flex items-center gap-3">
                        {/* Quick Stats */}
                        {symbolCfg.bot_config && (
                          <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground">
                            <span>{symbolCfg.use_bot_default ? symbolCfg.bot_config.leverage : (symbolCfg.custom_leverage || symbolCfg.bot_config.leverage)}x</span>
                            <span>${symbolCfg.use_bot_default ? symbolCfg.bot_config.margin_usd : (symbolCfg.custom_margin_usd || symbolCfg.bot_config.margin_usd)}</span>
                          </div>
                        )}
                        {expandedSymbol === symbolCfg.symbol ? (
                          <ChevronUp className="w-4 h-4 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-muted-foreground" />
                        )}
                      </div>
                    </button>

                    {/* Expanded Content */}
                    {expandedSymbol === symbolCfg.symbol && symbolCfg.is_active && (
                      <div className="p-3 border-t border-border space-y-3 bg-background/50">
                        {/* Use Bot Default Toggle */}
                        <div className="flex items-center justify-between p-2 bg-accent/30 rounded-lg">
                          <div>
                            <span className="font-medium text-sm">Usar config do Admin</span>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {symbolCfg.use_bot_default
                                ? 'Usando configuracao definida pelo administrador'
                                : 'Voce pode personalizar abaixo'}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => toggleSymbolUseDefault(symbolCfg.symbol)}
                            className={`p-1 rounded-lg transition-colors ${
                              symbolCfg.use_bot_default
                                ? 'bg-blue-500/20 text-blue-400'
                                : 'bg-purple-500/20 text-purple-400'
                            }`}
                          >
                            {symbolCfg.use_bot_default ? (
                              <ToggleRight className="w-5 h-5" />
                            ) : (
                              <ToggleLeft className="w-5 h-5" />
                            )}
                          </button>
                        </div>

                        {/* Admin Config Preview */}
                        {symbolCfg.bot_config && symbolCfg.use_bot_default && (
                          <div className="bg-blue-500/10 p-2 rounded-lg">
                            <p className="text-xs font-medium text-blue-400 mb-2">Config do Admin:</p>
                            <div className="grid grid-cols-4 gap-2 text-xs">
                              <div className="text-center">
                                <span className="text-muted-foreground block">Alav.</span>
                                <span className="font-bold">{symbolCfg.bot_config.leverage}x</span>
                              </div>
                              <div className="text-center">
                                <span className="text-muted-foreground block">Margem</span>
                                <span className="font-bold">${symbolCfg.bot_config.margin_usd}</span>
                              </div>
                              <div className="text-center">
                                <span className="text-muted-foreground block">SL</span>
                                <span className="font-bold text-red-400">{symbolCfg.bot_config.stop_loss_pct}%</span>
                              </div>
                              <div className="text-center">
                                <span className="text-muted-foreground block">TP</span>
                                <span className="font-bold text-green-400">{symbolCfg.bot_config.take_profit_pct}%</span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Custom Config Fields (only if not using bot default) */}
                        {!symbolCfg.use_bot_default && (
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-xs text-muted-foreground mb-1">Alavancagem</label>
                              <input
                                type="number"
                                value={symbolCfg.custom_leverage || ''}
                                onChange={(e) => updateSymbolConfig(symbolCfg.symbol, 'custom_leverage', Number(e.target.value) || undefined)}
                                placeholder={symbolCfg.bot_config ? `Padrao: ${symbolCfg.bot_config.leverage}x` : '10'}
                                min={1}
                                max={125}
                                className="w-full px-2 py-1.5 text-sm bg-input border border-border rounded focus:outline-none focus:ring-1 focus:ring-ring"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-muted-foreground mb-1">Margem (USD)</label>
                              <input
                                type="number"
                                value={symbolCfg.custom_margin_usd || ''}
                                onChange={(e) => updateSymbolConfig(symbolCfg.symbol, 'custom_margin_usd', Number(e.target.value) || undefined)}
                                placeholder={symbolCfg.bot_config ? `Padrao: $${symbolCfg.bot_config.margin_usd}` : '20'}
                                min={5}
                                step={0.01}
                                className="w-full px-2 py-1.5 text-sm bg-input border border-border rounded focus:outline-none focus:ring-1 focus:ring-ring"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-muted-foreground mb-1">Stop Loss (%)</label>
                              <input
                                type="number"
                                value={symbolCfg.custom_stop_loss_pct || ''}
                                onChange={(e) => updateSymbolConfig(symbolCfg.symbol, 'custom_stop_loss_pct', Number(e.target.value) || undefined)}
                                placeholder={symbolCfg.bot_config ? `Padrao: ${symbolCfg.bot_config.stop_loss_pct}%` : '3'}
                                min={0.1}
                                max={50}
                                step={0.1}
                                className="w-full px-2 py-1.5 text-sm bg-input border border-border rounded focus:outline-none focus:ring-1 focus:ring-ring"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-muted-foreground mb-1">Take Profit (%)</label>
                              <input
                                type="number"
                                value={symbolCfg.custom_take_profit_pct || ''}
                                onChange={(e) => updateSymbolConfig(symbolCfg.symbol, 'custom_take_profit_pct', Number(e.target.value) || undefined)}
                                placeholder={symbolCfg.bot_config ? `Padrao: ${symbolCfg.bot_config.take_profit_pct}%` : '5'}
                                min={0.1}
                                max={100}
                                step={0.1}
                                className="w-full px-2 py-1.5 text-sm bg-input border border-border rounded focus:outline-none focus:ring-1 focus:ring-ring"
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {isLoadingSymbols && (
                <div className="flex items-center justify-center py-4 text-muted-foreground">
                  <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                  Carregando ativos...
                </div>
              )}
            </div>
          )}

          {/* No symbols message - Only for Strategy Bots */}
          {!isTradingViewBot && !isLoadingSymbols && symbolConfigs.length === 0 && (
            <div className="border rounded-lg p-4 bg-secondary/20">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Layers className="w-4 h-4" />
                <span className="text-sm">Nenhum ativo configurado para este bot</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                O administrador precisa configurar os ativos na estrategia do bot.
              </p>
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
