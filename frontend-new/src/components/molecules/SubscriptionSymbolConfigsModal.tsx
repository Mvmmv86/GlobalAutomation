/**
 * SubscriptionSymbolConfigsModal Component
 * Modal for clients to manage per-symbol trading configuration for their subscription
 * Features exchange tabs and symbol "tabs/folders" (pastinhas) for each symbol
 * Supports per-exchange configuration
 */
import React, { useState, useEffect } from 'react'
import { X, Settings, RefreshCw, Check, ChevronDown, ChevronUp, ToggleLeft, ToggleRight } from 'lucide-react'
import { botsService, BotSubscription, SymbolConfigView, SubscriptionSymbolConfigCreate, ExchangeInfo } from '@/services/botsService'
import { useAuth } from '@/contexts/AuthContext'
import { Badge } from '../atoms/Badge'
import { toast } from 'sonner'

interface SubscriptionSymbolConfigsModalProps {
  isOpen: boolean
  onClose: () => void
  subscription: BotSubscription | null
}

// Individual symbol "tab/folder" component
interface SymbolTabProps {
  symbol: SymbolConfigView
  isExpanded: boolean
  onToggleExpand: () => void
  onConfigChange: (symbol: string, field: string, value: any) => void
  onToggleActive: (symbol: string, isActive: boolean) => void
  onToggleUseDefault: (symbol: string, useDefault: boolean) => void
}

const SymbolTab: React.FC<SymbolTabProps> = ({
  symbol,
  isExpanded,
  onToggleExpand,
  onConfigChange,
  onToggleActive,
  onToggleUseDefault
}) => {
  const config = symbol.client_config || {
    leverage: symbol.effective_config.leverage,
    margin_usd: symbol.effective_config.margin_usd,
    stop_loss_pct: symbol.effective_config.stop_loss_pct,
    take_profit_pct: symbol.effective_config.take_profit_pct
  }

  const sourceLabels: Record<string, string> = {
    'custom': 'Personalizado',
    'bot_symbol': 'Padrao do Bot (por simbolo)',
    'bot_default': 'Padrao Global do Bot'
  }

  return (
    <div className={`border rounded-lg overflow-hidden transition-all ${
      symbol.is_active ? 'border-border bg-card' : 'border-muted/50 bg-muted/20 opacity-70'
    }`}>
      {/* Tab Header */}
      <button
        onClick={onToggleExpand}
        className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {/* Active/Inactive Toggle */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggleActive(symbol.symbol, !symbol.is_active)
            }}
            className={`p-1 rounded transition-colors ${
              symbol.is_active ? 'text-green-500 hover:text-green-400' : 'text-muted-foreground hover:text-foreground'
            }`}
            title={symbol.is_active ? 'Clique para desativar' : 'Clique para ativar'}
          >
            {symbol.is_active ? (
              <ToggleRight className="w-6 h-6" />
            ) : (
              <ToggleLeft className="w-6 h-6" />
            )}
          </button>

          {/* Symbol Name */}
          <span className="font-mono font-bold text-foreground">{symbol.symbol}</span>

          {/* Status Badges */}
          {!symbol.is_active && (
            <Badge variant="secondary" className="text-xs">Desativado</Badge>
          )}
          {symbol.use_bot_default ? (
            <Badge variant="outline" className="text-xs bg-blue-500/10 border-blue-500/30 text-blue-400">
              Padrao do Bot
            </Badge>
          ) : (
            <Badge variant="outline" className="text-xs bg-purple-500/10 border-purple-500/30 text-purple-400">
              Personalizado
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-4">
          {/* Quick Stats */}
          <div className="hidden sm:flex items-center gap-4 text-sm text-muted-foreground">
            <span>Alav: {symbol.effective_config.leverage}x</span>
            <span>Margem: ${symbol.effective_config.margin_usd}</span>
          </div>

          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-5 h-5 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && symbol.is_active && (
        <div className="p-4 border-t border-border space-y-4 bg-background/50">
          {/* Use Bot Default Toggle */}
          <div className="flex items-center justify-between p-3 bg-accent/30 rounded-lg">
            <div>
              <span className="font-medium text-foreground">Usar configuracao padrao do Bot</span>
              <p className="text-xs text-muted-foreground mt-1">
                {symbol.use_bot_default
                  ? 'Usando configuracao definida pelo administrador'
                  : 'Configuracao personalizada ativada'}
              </p>
            </div>
            <button
              onClick={() => onToggleUseDefault(symbol.symbol, !symbol.use_bot_default)}
              className={`p-1.5 rounded-lg transition-colors ${
                symbol.use_bot_default
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-purple-500/20 text-purple-400'
              }`}
            >
              {symbol.use_bot_default ? (
                <ToggleRight className="w-6 h-6" />
              ) : (
                <ToggleLeft className="w-6 h-6" />
              )}
            </button>
          </div>

          {/* Config Source Info */}
          <div className="text-xs text-muted-foreground bg-accent/20 p-2 rounded">
            Fonte atual: <span className="font-medium text-foreground">{sourceLabels[symbol.effective_config.source]}</span>
          </div>

          {/* Custom Config Fields (only if not using bot default) */}
          {!symbol.use_bot_default && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-muted-foreground mb-1">Alavancagem</label>
                <input
                  type="number"
                  value={config.leverage || ''}
                  onChange={(e) => onConfigChange(symbol.symbol, 'leverage', Number(e.target.value) || null)}
                  min={1}
                  max={125}
                  className="w-full px-3 py-2 bg-input border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Ex: 10"
                />
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-1">Margem (USD)</label>
                <input
                  type="number"
                  value={config.margin_usd || ''}
                  onChange={(e) => onConfigChange(symbol.symbol, 'margin_usd', Number(e.target.value) || null)}
                  min={5}
                  step={0.01}
                  className="w-full px-3 py-2 bg-input border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Ex: 20"
                />
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-1">Stop Loss (%)</label>
                <input
                  type="number"
                  value={config.stop_loss_pct || ''}
                  onChange={(e) => onConfigChange(symbol.symbol, 'stop_loss_pct', Number(e.target.value) || null)}
                  min={0.1}
                  max={50}
                  step={0.1}
                  className="w-full px-3 py-2 bg-input border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Ex: 3"
                />
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-1">Take Profit (%)</label>
                <input
                  type="number"
                  value={config.take_profit_pct || ''}
                  onChange={(e) => onConfigChange(symbol.symbol, 'take_profit_pct', Number(e.target.value) || null)}
                  min={0.1}
                  max={100}
                  step={0.1}
                  className="w-full px-3 py-2 bg-input border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="Ex: 5"
                />
              </div>
            </div>
          )}

          {/* Effective Config Preview */}
          <div className="bg-accent/30 p-3 rounded-lg">
            <h4 className="text-sm font-medium text-foreground mb-2">Configuracao Efetiva</h4>
            <div className="grid grid-cols-4 gap-2 text-sm">
              <div className="text-center">
                <span className="text-muted-foreground block">Alavancagem</span>
                <span className="font-bold text-foreground">{symbol.effective_config.leverage}x</span>
              </div>
              <div className="text-center">
                <span className="text-muted-foreground block">Margem</span>
                <span className="font-bold text-foreground">${symbol.effective_config.margin_usd}</span>
              </div>
              <div className="text-center">
                <span className="text-muted-foreground block">Stop Loss</span>
                <span className="font-bold text-red-400">{symbol.effective_config.stop_loss_pct}%</span>
              </div>
              <div className="text-center">
                <span className="text-muted-foreground block">Take Profit</span>
                <span className="font-bold text-green-400">{symbol.effective_config.take_profit_pct}%</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export const SubscriptionSymbolConfigsModal: React.FC<SubscriptionSymbolConfigsModalProps> = ({
  isOpen,
  onClose,
  subscription
}) => {
  const { user } = useAuth()
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [symbols, setSymbols] = useState<SymbolConfigView[]>([])
  const [exchanges, setExchanges] = useState<ExchangeInfo[]>([])
  const [selectedExchangeId, setSelectedExchangeId] = useState<string | null>(null)
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [pendingChanges, setPendingChanges] = useState<Map<string, Partial<SubscriptionSymbolConfigCreate>>>(new Map())

  const subscriptionId = subscription?.exchanges?.[0]?.subscription_id || subscription?.id

  const loadConfigs = async (exchangeId?: string) => {
    if (!subscriptionId || !user?.id) return

    setIsLoading(true)
    try {
      const data = await botsService.getSubscriptionSymbolConfigs(subscriptionId, user.id, exchangeId)
      setSymbols(data.symbols || [])
      setExchanges(data.exchanges || [])

      // Set selected exchange if not set yet
      if (!selectedExchangeId && data.exchanges?.length > 0) {
        setSelectedExchangeId(data.current_exchange_id || data.exchanges[0].id)
      }

      setPendingChanges(new Map())
      setHasChanges(false)
    } catch (error) {
      toast.error(`Erro ao carregar: ${(error as Error).message}`)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && subscriptionId) {
      loadConfigs()
    }
  }, [isOpen, subscriptionId])

  // Reload when exchange changes
  useEffect(() => {
    if (isOpen && subscriptionId && selectedExchangeId) {
      loadConfigs(selectedExchangeId)
    }
  }, [selectedExchangeId])

  const handleExchangeChange = (exchangeId: string) => {
    // Save pending changes before switching? For now, discard
    if (hasChanges) {
      const confirmSwitch = window.confirm('Voce tem alteracoes nao salvas. Deseja descartar?')
      if (!confirmSwitch) return
    }
    setSelectedExchangeId(exchangeId)
    setExpandedSymbol(null)
    setPendingChanges(new Map())
    setHasChanges(false)
  }

  const handleSyncFromBot = async () => {
    if (!subscriptionId || !user?.id) return

    try {
      const result = await botsService.syncSubscriptionSymbolsFromBot(subscriptionId, user.id, selectedExchangeId || undefined)
      toast.success(`Sincronizado ${result.created} novos simbolos para ${result.exchanges_synced} exchange(s)`)
      await loadConfigs(selectedExchangeId || undefined)
    } catch (error) {
      toast.error(`Erro: ${(error as Error).message}`)
    }
  }

  const handleConfigChange = (symbol: string, field: string, value: any) => {
    const current = pendingChanges.get(symbol) || {}
    pendingChanges.set(symbol, { ...current, [field]: value })
    setPendingChanges(new Map(pendingChanges))
    setHasChanges(true)

    // Also update local state for immediate feedback
    setSymbols(symbols.map(s => {
      if (s.symbol === symbol) {
        return {
          ...s,
          effective_config: {
            ...s.effective_config,
            [field]: value,
            source: 'custom' as const
          }
        }
      }
      return s
    }))
  }

  const handleToggleActive = async (symbol: string, isActive: boolean) => {
    if (!subscriptionId || !user?.id) return

    try {
      await botsService.toggleSubscriptionSymbol(subscriptionId, user.id, symbol, isActive, selectedExchangeId || undefined)
      toast.success(`${symbol} ${isActive ? 'ativado' : 'desativado'}`)
      await loadConfigs(selectedExchangeId || undefined)
    } catch (error) {
      toast.error(`Erro: ${(error as Error).message}`)
    }
  }

  const handleToggleUseDefault = (symbol: string, useDefault: boolean) => {
    const current = pendingChanges.get(symbol) || {}
    pendingChanges.set(symbol, { ...current, use_bot_default: useDefault })
    setPendingChanges(new Map(pendingChanges))
    setHasChanges(true)

    // Update local state
    setSymbols(symbols.map(s => {
      if (s.symbol === symbol) {
        return { ...s, use_bot_default: useDefault }
      }
      return s
    }))
  }

  const handleSaveAll = async () => {
    if (!subscriptionId || !user?.id || pendingChanges.size === 0) return

    setIsSaving(true)
    try {
      const configs: SubscriptionSymbolConfigCreate[] = []

      pendingChanges.forEach((changes, symbol) => {
        const symbolData = symbols.find(s => s.symbol === symbol)
        configs.push({
          symbol,
          exchange_account_id: selectedExchangeId || undefined,
          leverage: changes.leverage ?? symbolData?.effective_config.leverage ?? null,
          margin_usd: changes.margin_usd ?? symbolData?.effective_config.margin_usd ?? null,
          stop_loss_pct: changes.stop_loss_pct ?? symbolData?.effective_config.stop_loss_pct ?? null,
          take_profit_pct: changes.take_profit_pct ?? symbolData?.effective_config.take_profit_pct ?? null,
          use_bot_default: changes.use_bot_default ?? symbolData?.use_bot_default ?? true,
          is_active: symbolData?.is_active ?? true
        })
      })

      const result = await botsService.saveSubscriptionSymbolConfigs(subscriptionId, user.id, configs, selectedExchangeId || undefined)
      toast.success(`Salvo: ${result.created} criados, ${result.updated} atualizados`)
      await loadConfigs(selectedExchangeId || undefined)
    } catch (error) {
      toast.error(`Erro: ${(error as Error).message}`)
    } finally {
      setIsSaving(false)
    }
  }

  if (!isOpen) return null

  const activeSymbols = symbols.filter(s => s.is_active).length
  const selectedExchange = exchanges.find(e => e.id === selectedExchangeId)

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-card border border-border rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-border flex justify-between items-center bg-card sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Settings className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">Configuracao por Ativo</h2>
              <p className="text-sm text-muted-foreground">{subscription?.bot_name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-accent rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Exchange Tabs (if multiple exchanges) */}
        {exchanges.length > 1 && (
          <div className="px-6 pt-4 border-b border-border">
            <div className="flex gap-2 overflow-x-auto pb-3">
              {exchanges.map(exchange => (
                <button
                  key={exchange.id}
                  onClick={() => handleExchangeChange(exchange.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                    selectedExchangeId === exchange.id
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-accent/50 text-muted-foreground hover:bg-accent hover:text-foreground'
                  }`}
                >
                  {exchange.exchange.toUpperCase()} - {exchange.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Current Exchange Info */}
        {selectedExchange && exchanges.length > 1 && (
          <div className="px-6 pt-3">
            <div className="text-xs text-muted-foreground bg-accent/20 p-2 rounded">
              Configurando ativos para: <span className="font-medium text-foreground">{selectedExchange.exchange.toUpperCase()} - {selectedExchange.name}</span>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : (
            <>
              {/* Stats & Actions */}
              <div className="flex items-center justify-between bg-accent/30 p-4 rounded-lg">
                <div className="text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">{activeSymbols}</span> de{' '}
                  <span className="font-medium text-foreground">{symbols.length}</span> ativos habilitados
                </div>
                <button
                  onClick={handleSyncFromBot}
                  className="flex items-center gap-2 px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-sm transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  Sincronizar do Bot
                </button>
              </div>

              {/* Symbol Tabs */}
              {symbols.length > 0 ? (
                <div className="space-y-3">
                  {symbols.map(symbol => (
                    <SymbolTab
                      key={symbol.symbol}
                      symbol={symbol}
                      isExpanded={expandedSymbol === symbol.symbol}
                      onToggleExpand={() => setExpandedSymbol(
                        expandedSymbol === symbol.symbol ? null : symbol.symbol
                      )}
                      onConfigChange={handleConfigChange}
                      onToggleActive={handleToggleActive}
                      onToggleUseDefault={handleToggleUseDefault}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Nenhum ativo disponivel</p>
                  <p className="text-sm mt-1">
                    Clique em "Sincronizar do Bot" para importar os ativos
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-border flex justify-between items-center bg-card sticky bottom-0">
          <div className="text-sm text-muted-foreground">
            {hasChanges && (
              <span className="text-yellow-500">
                * Alteracoes nao salvas
              </span>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 border border-border text-muted-foreground hover:bg-accent rounded-lg transition-colors"
            >
              Fechar
            </button>
            <button
              onClick={handleSaveAll}
              disabled={!hasChanges || isSaving}
              className="px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSaving ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Salvando...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Salvar
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
