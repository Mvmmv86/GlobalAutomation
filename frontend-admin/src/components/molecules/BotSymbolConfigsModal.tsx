/**
 * BotSymbolConfigsModal Component
 * Modal for managing per-symbol trading configuration for bots
 *
 * IMPORTANTE: Existem dois tipos de bots:
 * 1. Bots TradingView (webhook externo): tem trading_symbol definido, opera APENAS esse ativo
 *    - Interface simplificada: mostra só o ativo fixo com campos de configuração
 * 2. Bots de Estratégia Interna: NÃO tem trading_symbol, pode operar múltiplos ativos
 *    - Interface completa: permite adicionar/remover múltiplos símbolos
 */
import { useState, useEffect } from 'react'
import { Bot, adminService, BotSymbolConfig, SymbolConfigCreate } from '@/services/adminService'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Label } from '@/components/atoms/Label'
import { Input } from '@/components/atoms/Input'
import { Switch } from '@/components/atoms/Switch'
import { X, RefreshCw, Copy, Plus, Trash2, Settings, Webhook, Layers } from 'lucide-react'
import { toast } from 'sonner'

interface BotSymbolConfigsModalProps {
  isOpen: boolean
  onClose: () => void
  bot: Bot | null
}

interface SymbolConfigRow {
  symbol: string
  leverage: number
  margin_usd: number
  stop_loss_pct: number
  take_profit_pct: number
  max_positions: number
  is_active: boolean
  isNew: boolean
  hasChanges: boolean
}

// Lista de simbolos populares para sugestao rapida
const POPULAR_SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
  'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT',
  'MATICUSDT', 'LTCUSDT', 'ATOMUSDT', 'NEARUSDT', 'ARBUSDT',
  'OPUSDT', 'APTUSDT', 'SUIUSDT', 'INJUSDT', 'AAVEUSDT',
  'UNIUSDT', 'FILUSDT', 'LDOUSDT', 'MKRUSDT', 'RUNEUSDT',
  'WIFUSDT', 'PEPEUSDT', 'SHIBUSDT', 'BONKUSDT', 'FLOKIUSDT'
]

export function BotSymbolConfigsModal({ isOpen, onClose, bot }: BotSymbolConfigsModalProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [configs, setConfigs] = useState<SymbolConfigRow[]>([])
  const [strategySymbols, setStrategySymbols] = useState<string[]>([])
  const [unconfiguredSymbols, setUnconfiguredSymbols] = useState<string[]>([])
  const [manualSymbolInput, setManualSymbolInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [botDefaults, setBotDefaults] = useState<{
    default_leverage: number
    default_margin_usd: number
    default_stop_loss_pct: number
    default_take_profit_pct: number
    default_max_positions: number
  } | null>(null)

  // Template config for "Apply to All"
  const [templateConfig, setTemplateConfig] = useState({
    leverage: 10,
    margin_usd: 20,
    stop_loss_pct: 3,
    take_profit_pct: 5,
    max_positions: 3,
    is_active: true
  })

  const loadConfigs = async () => {
    if (!bot) return

    setIsLoading(true)
    try {
      const data = await adminService.getBotSymbolConfigs(bot.id)

      setStrategySymbols(data.strategy_symbols || [])
      setUnconfiguredSymbols(data.unconfigured_symbols || [])
      setBotDefaults(data.bot_defaults)

      // Convert to row format
      const rows: SymbolConfigRow[] = (data.configs || []).map(c => ({
        symbol: c.symbol,
        leverage: c.leverage,
        margin_usd: Number(c.margin_usd),
        stop_loss_pct: Number(c.stop_loss_pct),
        take_profit_pct: Number(c.take_profit_pct),
        max_positions: c.max_positions,
        is_active: c.is_active,
        isNew: false,
        hasChanges: false
      }))

      setConfigs(rows)

      // Set template from bot defaults
      if (data.bot_defaults) {
        setTemplateConfig({
          leverage: data.bot_defaults.default_leverage || 10,
          margin_usd: Number(data.bot_defaults.default_margin_usd) || 20,
          stop_loss_pct: Number(data.bot_defaults.default_stop_loss_pct) || 3,
          take_profit_pct: Number(data.bot_defaults.default_take_profit_pct) || 5,
          max_positions: data.bot_defaults.default_max_positions || 3,
          is_active: true
        })
      }
    } catch (error) {
      toast.error(`Erro ao carregar configs: ${(error as Error).message}`)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen && bot) {
      loadConfigs()
    }
  }, [isOpen, bot])

  const handleSyncFromStrategy = async () => {
    if (!bot) return

    try {
      const result = await adminService.syncBotSymbolsFromStrategy(bot.id)
      toast.success(`Sincronizado ${result.created} novos simbolos da estrategia`)
      await loadConfigs()
    } catch (error) {
      toast.error(`Erro ao sincronizar: ${(error as Error).message}`)
    }
  }

  const handleApplyToAll = async () => {
    if (!bot) return

    try {
      const result = await adminService.applyConfigToAllSymbols(bot.id, {
        symbol: 'ALL', // Will be replaced by backend
        ...templateConfig
      })
      toast.success(`Configuracao aplicada em ${result.updated} simbolos`)
      await loadConfigs()
    } catch (error) {
      toast.error(`Erro ao aplicar: ${(error as Error).message}`)
    }
  }

  const handleAddSymbol = (symbol: string) => {
    const symbolUpper = symbol.toUpperCase().trim()

    if (!symbolUpper) {
      toast.error('Digite um simbolo valido')
      return
    }

    if (configs.find(c => c.symbol === symbolUpper)) {
      toast.error('Simbolo ja configurado')
      return
    }

    const newConfig: SymbolConfigRow = {
      symbol: symbolUpper,
      leverage: templateConfig.leverage,
      margin_usd: templateConfig.margin_usd,
      stop_loss_pct: templateConfig.stop_loss_pct,
      take_profit_pct: templateConfig.take_profit_pct,
      max_positions: templateConfig.max_positions,
      is_active: true,
      isNew: true,
      hasChanges: true
    }

    setConfigs([...configs, newConfig])
    setUnconfiguredSymbols(unconfiguredSymbols.filter(s => s !== symbolUpper))
    setManualSymbolInput('')
    setShowSuggestions(false)
    toast.success(`Simbolo ${symbolUpper} adicionado`)
  }

  const handleManualSymbolSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (manualSymbolInput.trim()) {
      handleAddSymbol(manualSymbolInput)
    }
  }

  // Filtrar sugestoes baseado no input
  const filteredSuggestions = POPULAR_SYMBOLS.filter(s =>
    s.toLowerCase().includes(manualSymbolInput.toLowerCase()) &&
    !configs.find(c => c.symbol === s)
  ).slice(0, 10)

  const handleUpdateConfig = (symbol: string, field: keyof SymbolConfigRow, value: any) => {
    setConfigs(configs.map(c => {
      if (c.symbol === symbol) {
        return { ...c, [field]: value, hasChanges: true }
      }
      return c
    }))
  }

  const handleDeleteConfig = async (symbol: string) => {
    if (!bot) return

    const config = configs.find(c => c.symbol === symbol)
    if (config?.isNew) {
      // Just remove from local state
      setConfigs(configs.filter(c => c.symbol !== symbol))
      if (strategySymbols.includes(symbol)) {
        setUnconfiguredSymbols([...unconfiguredSymbols, symbol])
      }
      return
    }

    try {
      await adminService.deleteBotSymbolConfig(bot.id, symbol)
      toast.success(`Config do simbolo ${symbol} removida`)
      await loadConfigs()
    } catch (error) {
      toast.error(`Erro ao remover: ${(error as Error).message}`)
    }
  }

  const handleSaveAll = async () => {
    if (!bot) return

    const changedConfigs = configs.filter(c => c.hasChanges)
    if (changedConfigs.length === 0) {
      toast.info('Nenhuma alteracao para salvar')
      return
    }

    setIsSaving(true)
    try {
      const toSave: SymbolConfigCreate[] = changedConfigs.map(c => ({
        symbol: c.symbol,
        leverage: c.leverage,
        margin_usd: c.margin_usd,
        stop_loss_pct: c.stop_loss_pct,
        take_profit_pct: c.take_profit_pct,
        max_positions: c.max_positions,
        is_active: c.is_active
      }))

      const result = await adminService.saveBotSymbolConfigs(bot.id, toSave)
      toast.success(`Salvo: ${result.created} criados, ${result.updated} atualizados`)
      await loadConfigs()
    } catch (error) {
      toast.error(`Erro ao salvar: ${(error as Error).message}`)
    } finally {
      setIsSaving(false)
    }
  }

  if (!isOpen || !bot) return null

  const hasChanges = configs.some(c => c.hasChanges)

  // DEBUG: Ver o que está chegando
  console.log('🔍 BotSymbolConfigsModal - bot:', bot)
  console.log('🔍 BotSymbolConfigsModal - bot.trading_symbol:', bot.trading_symbol)
  console.log('🔍 BotSymbolConfigsModal - typeof trading_symbol:', typeof bot.trading_symbol)

  // Detectar se é um bot TradingView (tem trading_symbol definido)
  const isTradingViewBot = Boolean(bot.trading_symbol)

  // Para bots TradingView, renderizar interface simplificada
  if (isTradingViewBot) {
    const tradingSymbol = bot.trading_symbol!
    const existingConfig = configs.find(c => c.symbol === tradingSymbol)

    // Se não existe config para o símbolo do TradingView, criar uma com defaults
    const currentConfig = existingConfig || {
      symbol: tradingSymbol,
      leverage: bot.default_leverage || 10,
      margin_usd: bot.default_margin_usd || 20,
      stop_loss_pct: bot.default_stop_loss_pct || 3,
      take_profit_pct: bot.default_take_profit_pct || 5,
      max_positions: bot.default_max_positions || 3,
      is_active: true,
      isNew: true,
      hasChanges: false
    }

    // Handler para atualizar config do TradingView bot
    const handleTVConfigUpdate = (field: keyof SymbolConfigRow, value: any) => {
      if (existingConfig) {
        handleUpdateConfig(tradingSymbol, field, value)
      } else {
        // Adicionar novo config
        const newConfig: SymbolConfigRow = {
          ...currentConfig,
          [field]: value,
          hasChanges: true
        }
        setConfigs([newConfig])
      }
    }

    // Handler para salvar config do TradingView
    const handleTVSave = async () => {
      if (!bot) return

      setIsSaving(true)
      try {
        const toSave: SymbolConfigCreate[] = [{
          symbol: tradingSymbol,
          leverage: currentConfig.leverage,
          margin_usd: currentConfig.margin_usd,
          stop_loss_pct: currentConfig.stop_loss_pct,
          take_profit_pct: currentConfig.take_profit_pct,
          max_positions: currentConfig.max_positions,
          is_active: currentConfig.is_active
        }]

        const result = await adminService.saveBotSymbolConfigs(bot.id, toSave)
        toast.success(`Configuracao do ${tradingSymbol} salva com sucesso!`)
        await loadConfigs()
      } catch (error) {
        toast.error(`Erro ao salvar: ${(error as Error).message}`)
      } finally {
        setIsSaving(false)
      }
    }

    const tvHasChanges = existingConfig?.hasChanges || (!existingConfig && configs.length === 1 && configs[0].hasChanges)

    return (
      <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
        <Card className="max-w-xl w-full max-h-[90vh] overflow-hidden bg-gray-900 border-gray-800 flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-gray-800 flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <Webhook className="w-6 h-6 text-orange-400" />
                Configuracao do Bot TradingView
              </h2>
              <p className="text-gray-400 text-sm mt-1">{bot.name}</p>
              <div className="flex items-center gap-2 mt-2">
                <span className="px-2 py-1 bg-orange-500/20 text-orange-400 rounded text-xs flex items-center gap-1">
                  <Webhook className="w-3 h-3" />
                  Webhook Externo
                </span>
                <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs font-mono">
                  {tradingSymbol}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          {/* Content - Interface Simplificada para TradingView Bot */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
              </div>
            ) : (
              <>
                {/* Info Box */}
                <div className="bg-orange-900/20 border border-orange-800/50 p-4 rounded-lg">
                  <p className="text-orange-300 text-sm">
                    Este bot recebe sinais do TradingView para o ativo <strong>{tradingSymbol}</strong>.
                    Configure abaixo os parametros de trading para este ativo.
                  </p>
                </div>

                {/* Configuração do Ativo */}
                <div className="bg-gray-800/50 p-6 rounded-lg space-y-6">
                  <h3 className="text-white font-semibold flex items-center gap-2 text-lg">
                    <Settings className="w-5 h-5 text-blue-400" />
                    Configuracao de Trading - {tradingSymbol}
                  </h3>

                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <Label className="text-gray-300 text-sm mb-2 block">Alavancagem</Label>
                      <Input
                        type="number"
                        value={currentConfig.leverage}
                        onChange={(e) => handleTVConfigUpdate('leverage', Number(e.target.value))}
                        min={1}
                        max={125}
                        className="bg-gray-800 border-gray-700 text-white h-12 text-lg"
                      />
                      <p className="text-gray-500 text-xs mt-1">1x a 125x</p>
                    </div>
                    <div>
                      <Label className="text-gray-300 text-sm mb-2 block">Margem (USD)</Label>
                      <Input
                        type="number"
                        value={currentConfig.margin_usd}
                        onChange={(e) => handleTVConfigUpdate('margin_usd', Number(e.target.value))}
                        min={5}
                        step={0.01}
                        className="bg-gray-800 border-gray-700 text-white h-12 text-lg"
                      />
                      <p className="text-gray-500 text-xs mt-1">Minimo $5</p>
                    </div>
                    <div>
                      <Label className="text-gray-300 text-sm mb-2 block">Stop Loss (%)</Label>
                      <Input
                        type="number"
                        value={currentConfig.stop_loss_pct}
                        onChange={(e) => handleTVConfigUpdate('stop_loss_pct', Number(e.target.value))}
                        min={0.1}
                        max={50}
                        step={0.1}
                        className="bg-gray-800 border-gray-700 text-white h-12 text-lg"
                      />
                      <p className="text-gray-500 text-xs mt-1">0.1% a 50%</p>
                    </div>
                    <div>
                      <Label className="text-gray-300 text-sm mb-2 block">Take Profit (%)</Label>
                      <Input
                        type="number"
                        value={currentConfig.take_profit_pct}
                        onChange={(e) => handleTVConfigUpdate('take_profit_pct', Number(e.target.value))}
                        min={0.1}
                        max={100}
                        step={0.1}
                        className="bg-gray-800 border-gray-700 text-white h-12 text-lg"
                      />
                      <p className="text-gray-500 text-xs mt-1">0.1% a 100%</p>
                    </div>
                    <div>
                      <Label className="text-gray-300 text-sm mb-2 block">Max Posicoes</Label>
                      <Input
                        type="number"
                        value={currentConfig.max_positions}
                        onChange={(e) => handleTVConfigUpdate('max_positions', Number(e.target.value))}
                        min={1}
                        max={20}
                        className="bg-gray-800 border-gray-700 text-white h-12 text-lg"
                      />
                      <p className="text-gray-500 text-xs mt-1">1 a 20</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div>
                        <Label className="text-gray-300 text-sm mb-2 block">Ativo</Label>
                        <Switch
                          checked={currentConfig.is_active}
                          onCheckedChange={(checked) => handleTVConfigUpdate('is_active', checked)}
                        />
                      </div>
                      <span className={`text-sm ${currentConfig.is_active ? 'text-green-400' : 'text-gray-500'}`}>
                        {currentConfig.is_active ? 'Habilitado' : 'Desabilitado'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Status da Config */}
                {existingConfig && !existingConfig.isNew && (
                  <div className="bg-green-900/20 border border-green-800/50 p-3 rounded-lg">
                    <p className="text-green-400 text-sm flex items-center gap-2">
                      <Settings className="w-4 h-4" />
                      Configuracao salva no banco de dados
                    </p>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-gray-800 flex justify-between items-center">
            <div className="text-sm text-gray-400">
              {tvHasChanges && (
                <span className="text-yellow-400">
                  * Existem alteracoes nao salvas
                </span>
              )}
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={onClose}
                className="border-gray-700 text-gray-300 hover:bg-gray-800"
              >
                Fechar
              </Button>
              <Button
                onClick={handleTVSave}
                disabled={isSaving}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isSaving ? 'Salvando...' : 'Salvar Configuracao'}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  // Interface para bots de Estratégia Interna - SEM configuração manual
  // Bots de estratégia já conectam automaticamente com suas estratégias
  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <Card className="max-w-xl w-full max-h-[90vh] overflow-hidden bg-gray-900 border-gray-800 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-800 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Layers className="w-6 h-6 text-purple-400" />
              Bot de Estrategia Interna
            </h2>
            <p className="text-gray-400 text-sm mt-1">{bot.name}</p>
            <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-xs flex items-center gap-1 mt-2 w-fit">
              <Layers className="w-3 h-3" />
              Estrategia Interna - Multiplos Ativos
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content - Mensagem Informativa */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          <div className="bg-purple-900/20 border border-purple-800/50 p-6 rounded-lg">
            <h3 className="text-purple-300 font-semibold text-lg mb-4 flex items-center gap-2">
              <Layers className="w-5 h-5" />
              Configuracao Automatica via Estrategia
            </h3>
            <p className="text-purple-200/80 mb-4">
              Este bot esta conectado a uma <strong>estrategia interna</strong> que gerencia automaticamente os ativos e configuracoes.
            </p>
            <div className="space-y-2 text-sm text-purple-300/70">
              <p>• Os ativos sao definidos pela estrategia conectada</p>
              <p>• As configuracoes de trading sao herdadas da estrategia</p>
              <p>• Nao e necessario configurar manualmente neste modal</p>
            </div>
          </div>

          {/* Configurações Padrão do Bot (apenas informativo) */}
          <div className="bg-gray-800/50 p-4 rounded-lg">
            <h4 className="text-gray-300 font-medium mb-3 flex items-center gap-2">
              <Settings className="w-4 h-4 text-gray-400" />
              Parametros Padrao do Bot
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Alavancagem</p>
                <p className="text-white font-medium">{bot.default_leverage}x</p>
              </div>
              <div>
                <p className="text-gray-500">Margem</p>
                <p className="text-white font-medium">${bot.default_margin_usd}</p>
              </div>
              <div>
                <p className="text-gray-500">Max Posicoes</p>
                <p className="text-white font-medium">{bot.default_max_positions}</p>
              </div>
              <div>
                <p className="text-gray-500">Stop Loss</p>
                <p className="text-red-400 font-medium">{bot.default_stop_loss_pct}%</p>
              </div>
              <div>
                <p className="text-gray-500">Take Profit</p>
                <p className="text-green-400 font-medium">{bot.default_take_profit_pct}%</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-3">
              Estes valores podem ser sobrescritos pela estrategia conectada
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-800 flex justify-end">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-gray-700 text-gray-300 hover:bg-gray-800"
          >
            Fechar
          </Button>
        </div>
      </Card>
    </div>
  )
}
