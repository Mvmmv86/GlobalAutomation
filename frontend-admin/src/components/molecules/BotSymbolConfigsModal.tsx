/**
 * BotSymbolConfigsModal Component
 * Modal for managing per-symbol trading configuration for bots
 */
import { useState, useEffect } from 'react'
import { Bot, adminService, BotSymbolConfig, SymbolConfigCreate } from '@/services/adminService'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Label } from '@/components/atoms/Label'
import { Input } from '@/components/atoms/Input'
import { Switch } from '@/components/atoms/Switch'
import { X, RefreshCw, Copy, Plus, Trash2, Settings } from 'lucide-react'
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

export function BotSymbolConfigsModal({ isOpen, onClose, bot }: BotSymbolConfigsModalProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [configs, setConfigs] = useState<SymbolConfigRow[]>([])
  const [strategySymbols, setStrategySymbols] = useState<string[]>([])
  const [unconfiguredSymbols, setUnconfiguredSymbols] = useState<string[]>([])
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
    if (configs.find(c => c.symbol === symbol)) {
      toast.error('Simbolo ja configurado')
      return
    }

    const newConfig: SymbolConfigRow = {
      symbol: symbol.toUpperCase(),
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
    setUnconfiguredSymbols(unconfiguredSymbols.filter(s => s !== symbol))
  }

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

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <Card className="max-w-6xl w-full max-h-[90vh] overflow-hidden bg-gray-900 border-gray-800 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-800 flex justify-between items-center sticky top-0 bg-gray-900 z-10">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Settings className="w-6 h-6 text-blue-400" />
              Configuracao por Simbolo
            </h2>
            <p className="text-gray-400 text-sm mt-1">{bot.name}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
            </div>
          ) : (
            <>
              {/* Actions Bar */}
              <div className="flex flex-wrap gap-3 items-center justify-between bg-gray-800/50 p-4 rounded-lg">
                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleSyncFromStrategy}
                    className="border-blue-600 text-blue-400 hover:bg-blue-900/30"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Sincronizar da Estrategia
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleApplyToAll}
                    className="border-purple-600 text-purple-400 hover:bg-purple-900/30"
                  >
                    <Copy className="w-4 h-4 mr-2" />
                    Aplicar Config em Todos
                  </Button>
                </div>

                <div className="text-sm text-gray-400">
                  {configs.length} simbolos configurados | {unconfiguredSymbols.length} pendentes
                </div>
              </div>

              {/* Template Config (for Apply to All) */}
              <div className="bg-gray-800/30 p-4 rounded-lg space-y-4">
                <h3 className="text-white font-semibold flex items-center gap-2">
                  <Settings className="w-4 h-4 text-purple-400" />
                  Template de Configuracao (para "Aplicar em Todos")
                </h3>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <Label className="text-gray-400 text-xs">Alavancagem</Label>
                    <Input
                      type="number"
                      value={templateConfig.leverage}
                      onChange={(e) => setTemplateConfig({ ...templateConfig, leverage: Number(e.target.value) })}
                      min={1}
                      max={125}
                      className="bg-gray-800 border-gray-700 text-white h-9"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-400 text-xs">Margem (USD)</Label>
                    <Input
                      type="number"
                      value={templateConfig.margin_usd}
                      onChange={(e) => setTemplateConfig({ ...templateConfig, margin_usd: Number(e.target.value) })}
                      min={5}
                      step={0.01}
                      className="bg-gray-800 border-gray-700 text-white h-9"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-400 text-xs">Stop Loss %</Label>
                    <Input
                      type="number"
                      value={templateConfig.stop_loss_pct}
                      onChange={(e) => setTemplateConfig({ ...templateConfig, stop_loss_pct: Number(e.target.value) })}
                      min={0.1}
                      max={50}
                      step={0.1}
                      className="bg-gray-800 border-gray-700 text-white h-9"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-400 text-xs">Take Profit %</Label>
                    <Input
                      type="number"
                      value={templateConfig.take_profit_pct}
                      onChange={(e) => setTemplateConfig({ ...templateConfig, take_profit_pct: Number(e.target.value) })}
                      min={0.1}
                      max={100}
                      step={0.1}
                      className="bg-gray-800 border-gray-700 text-white h-9"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-400 text-xs">Max Posicoes</Label>
                    <Input
                      type="number"
                      value={templateConfig.max_positions}
                      onChange={(e) => setTemplateConfig({ ...templateConfig, max_positions: Number(e.target.value) })}
                      min={1}
                      max={20}
                      className="bg-gray-800 border-gray-700 text-white h-9"
                    />
                  </div>
                </div>
              </div>

              {/* Unconfigured Symbols */}
              {unconfiguredSymbols.length > 0 && (
                <div className="bg-yellow-900/20 border border-yellow-800/50 p-4 rounded-lg">
                  <h3 className="text-yellow-400 font-semibold mb-3 flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    Simbolos da Estrategia sem Configuracao
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {unconfiguredSymbols.map(symbol => (
                      <button
                        key={symbol}
                        onClick={() => handleAddSymbol(symbol)}
                        className="px-3 py-1 bg-yellow-800/30 hover:bg-yellow-700/40 text-yellow-300 rounded-md text-sm flex items-center gap-1 transition-colors"
                      >
                        <Plus className="w-3 h-3" />
                        {symbol}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Configs Table */}
              {configs.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase">
                      <tr>
                        <th className="px-4 py-3 text-left">Simbolo</th>
                        <th className="px-4 py-3 text-center">Alavancagem</th>
                        <th className="px-4 py-3 text-center">Margem USD</th>
                        <th className="px-4 py-3 text-center">SL %</th>
                        <th className="px-4 py-3 text-center">TP %</th>
                        <th className="px-4 py-3 text-center">Max Pos</th>
                        <th className="px-4 py-3 text-center">Ativo</th>
                        <th className="px-4 py-3 text-center">Acoes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800">
                      {configs.map(config => (
                        <tr
                          key={config.symbol}
                          className={`${config.hasChanges ? 'bg-blue-900/10' : ''} ${config.isNew ? 'bg-green-900/10' : ''}`}
                        >
                          <td className="px-4 py-3">
                            <span className="font-mono text-white font-semibold">
                              {config.symbol}
                            </span>
                            {config.isNew && (
                              <span className="ml-2 text-xs bg-green-600/30 text-green-400 px-2 py-0.5 rounded">
                                Novo
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <Input
                              type="number"
                              value={config.leverage}
                              onChange={(e) => handleUpdateConfig(config.symbol, 'leverage', Number(e.target.value))}
                              min={1}
                              max={125}
                              className="bg-gray-800 border-gray-700 text-white h-8 text-center w-20 mx-auto"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <Input
                              type="number"
                              value={config.margin_usd}
                              onChange={(e) => handleUpdateConfig(config.symbol, 'margin_usd', Number(e.target.value))}
                              min={5}
                              step={0.01}
                              className="bg-gray-800 border-gray-700 text-white h-8 text-center w-24 mx-auto"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <Input
                              type="number"
                              value={config.stop_loss_pct}
                              onChange={(e) => handleUpdateConfig(config.symbol, 'stop_loss_pct', Number(e.target.value))}
                              min={0.1}
                              max={50}
                              step={0.1}
                              className="bg-gray-800 border-gray-700 text-white h-8 text-center w-20 mx-auto"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <Input
                              type="number"
                              value={config.take_profit_pct}
                              onChange={(e) => handleUpdateConfig(config.symbol, 'take_profit_pct', Number(e.target.value))}
                              min={0.1}
                              max={100}
                              step={0.1}
                              className="bg-gray-800 border-gray-700 text-white h-8 text-center w-20 mx-auto"
                            />
                          </td>
                          <td className="px-4 py-3">
                            <Input
                              type="number"
                              value={config.max_positions}
                              onChange={(e) => handleUpdateConfig(config.symbol, 'max_positions', Number(e.target.value))}
                              min={1}
                              max={20}
                              className="bg-gray-800 border-gray-700 text-white h-8 text-center w-16 mx-auto"
                            />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <Switch
                              checked={config.is_active}
                              onCheckedChange={(checked) => handleUpdateConfig(config.symbol, 'is_active', checked)}
                            />
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button
                              onClick={() => handleDeleteConfig(config.symbol)}
                              className="p-1.5 text-red-400 hover:bg-red-900/30 rounded transition-colors"
                              title="Remover configuracao"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-gray-400">
                  <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Nenhuma configuracao por simbolo</p>
                  <p className="text-sm mt-1">
                    Clique em "Sincronizar da Estrategia" para importar os simbolos
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-800 flex justify-between items-center sticky bottom-0 bg-gray-900">
          <div className="text-sm text-gray-400">
            {hasChanges && (
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
              onClick={handleSaveAll}
              disabled={!hasChanges || isSaving}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isSaving ? 'Salvando...' : 'Salvar Alteracoes'}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}
