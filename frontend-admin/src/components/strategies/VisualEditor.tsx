/**
 * VisualEditor Component
 * Visual drag-and-drop editor for creating strategies
 */
import { useState, useEffect } from 'react'
import { Settings, Zap, Target, Save, RotateCcw, Bot } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { Label } from '@/components/atoms/Label'
import { Badge } from '@/components/atoms/Badge'
import { IndicatorSelector, IndicatorConfig } from './IndicatorSelector'
import { ConditionBuilder, ConditionConfig } from './ConditionBuilder'
import { TIMEFRAMES } from '@/services/strategyService'
import { botsService, Bot as BotType } from '@/services/botsService'

// Common trading symbols
const POPULAR_SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
  'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT'
]

export interface VisualStrategyConfig {
  name: string
  description: string
  symbols: string[]
  timeframe: string
  bot_id: string | null
  indicators: IndicatorConfig[]
  conditions: ConditionConfig[]
}

interface VisualEditorProps {
  initialConfig?: Partial<VisualStrategyConfig>
  onSave: (config: VisualStrategyConfig) => void
  onCancel: () => void
  isSaving?: boolean
}

export function VisualEditor({ initialConfig, onSave, onCancel, isSaving }: VisualEditorProps) {
  const [activeTab, setActiveTab] = useState<'basic' | 'indicators' | 'conditions'>('basic')
  const [config, setConfig] = useState<VisualStrategyConfig>({
    name: initialConfig?.name || '',
    description: initialConfig?.description || '',
    symbols: initialConfig?.symbols || ['BTCUSDT'],
    timeframe: initialConfig?.timeframe || '5m',
    bot_id: initialConfig?.bot_id || null,
    indicators: initialConfig?.indicators || [],
    conditions: initialConfig?.conditions || [],
  })

  const [symbolInput, setSymbolInput] = useState('')
  const [availableBots, setAvailableBots] = useState<BotType[]>([])
  const [loadingBots, setLoadingBots] = useState(true)

  // Load available bots on mount
  useEffect(() => {
    const loadBots = async () => {
      try {
        const bots = await botsService.getAllBots()
        setAvailableBots(bots.filter(b => b.status === 'active'))
      } catch (error) {
        console.error('Error loading bots:', error)
      } finally {
        setLoadingBots(false)
      }
    }
    loadBots()
  }, [])

  const updateConfig = (updates: Partial<VisualStrategyConfig>) => {
    setConfig(prev => ({ ...prev, ...updates }))
  }

  const addSymbol = (symbol: string) => {
    const upperSymbol = symbol.toUpperCase().trim()
    if (upperSymbol && !config.symbols.includes(upperSymbol)) {
      updateConfig({ symbols: [...config.symbols, upperSymbol] })
    }
    setSymbolInput('')
  }

  const removeSymbol = (symbol: string) => {
    updateConfig({ symbols: config.symbols.filter(s => s !== symbol) })
  }

  const handleSave = () => {
    if (!config.name.trim()) {
      alert('Nome da estrategia e obrigatorio')
      return
    }
    if (config.symbols.length === 0) {
      alert('Selecione pelo menos um simbolo')
      return
    }
    if (config.indicators.length === 0) {
      alert('Adicione pelo menos um indicador')
      return
    }
    onSave(config)
  }

  const resetConfig = () => {
    setConfig({
      name: '',
      description: '',
      symbols: ['BTCUSDT'],
      timeframe: '5m',
      bot_id: null,
      indicators: [],
      conditions: [],
    })
  }

  const tabs = [
    { id: 'basic', label: 'Configuracao Basica', icon: <Settings className="w-4 h-4" /> },
    { id: 'indicators', label: 'Indicadores', icon: <Zap className="w-4 h-4" />, count: config.indicators.length },
    { id: 'conditions', label: 'Condicoes', icon: <Target className="w-4 h-4" />, count: config.conditions.length },
  ]

  const isValid = config.name.trim() && config.symbols.length > 0 && config.indicators.length > 0

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex gap-2 border-b border-[#2a2e39] pb-2">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-t-lg text-sm font-medium transition-colors
              ${activeTab === tab.id
                ? 'bg-[#2a2e39] text-white'
                : 'text-gray-400 hover:text-white hover:bg-[#1e222d]'
              }
            `}
          >
            {tab.icon}
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <Badge variant="default" className="bg-emerald-500/20 text-emerald-300 text-xs">
                {tab.count}
              </Badge>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {/* Basic Config Tab */}
        {activeTab === 'basic' && (
          <div className="space-y-6">
            {/* Name & Description */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label className="text-gray-300">Nome da Estrategia *</Label>
                <Input
                  value={config.name}
                  onChange={(e) => updateConfig({ name: e.target.value })}
                  placeholder="Ex: NDY + RSI Strategy"
                  className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white"
                />
              </div>
              <div>
                <Label className="text-gray-300">Timeframe *</Label>
                <select
                  value={config.timeframe}
                  onChange={(e) => updateConfig({ timeframe: e.target.value })}
                  className="mt-1 w-full bg-[#1e222d] border border-[#2a2e39] text-white rounded-md px-3 py-2"
                >
                  {TIMEFRAMES.map(tf => (
                    <option key={tf.value} value={tf.value}>{tf.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <Label className="text-gray-300">Descricao</Label>
              <textarea
                value={config.description}
                onChange={(e) => updateConfig({ description: e.target.value })}
                placeholder="Descreva a estrategia..."
                rows={3}
                className="mt-1 w-full bg-[#1e222d] border border-[#2a2e39] text-white rounded-md px-3 py-2 resize-none"
              />
            </div>

            {/* Symbols */}
            <div>
              <Label className="text-gray-300">Simbolos Monitorados *</Label>
              <div className="mt-2 flex flex-wrap gap-2">
                {config.symbols.map(symbol => (
                  <Badge
                    key={symbol}
                    variant="default"
                    className="bg-blue-500/20 text-blue-300 border-blue-500/50 cursor-pointer hover:bg-red-500/20 hover:text-red-300 hover:border-red-500/50"
                    onClick={() => removeSymbol(symbol)}
                  >
                    {symbol} x
                  </Badge>
                ))}
              </div>

              {/* Add symbol input */}
              <div className="mt-3 flex gap-2">
                <Input
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addSymbol(symbolInput)}
                  placeholder="Digite o simbolo (ex: BTCUSDT)"
                  className="flex-1 bg-[#1e222d] border-[#2a2e39] text-white"
                />
                <Button
                  variant="outline"
                  onClick={() => addSymbol(symbolInput)}
                  disabled={!symbolInput.trim()}
                >
                  Adicionar
                </Button>
              </div>

              {/* Popular symbols */}
              <div className="mt-3">
                <p className="text-xs text-gray-500 mb-2">Simbolos populares:</p>
                <div className="flex flex-wrap gap-1">
                  {POPULAR_SYMBOLS.filter(s => !config.symbols.includes(s)).slice(0, 6).map(symbol => (
                    <button
                      key={symbol}
                      onClick={() => addSymbol(symbol)}
                      className="text-xs px-2 py-1 bg-[#1e222d] text-gray-400 rounded hover:bg-[#2a2e39] hover:text-white"
                    >
                      + {symbol}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Bot Selector */}
            <div className="pt-4 border-t border-[#2a2e39]">
              <Label className="text-gray-300 flex items-center gap-2">
                <Bot className="w-4 h-4" />
                Bot Associado (Execucao Automatica)
              </Label>
              <p className="text-xs text-gray-500 mt-1 mb-2">
                Selecione um bot para executar trades automaticamente quando os sinais forem gerados.
                Se nenhum bot for selecionado, os sinais serao apenas registrados.
              </p>
              <select
                value={config.bot_id || ''}
                onChange={(e) => updateConfig({ bot_id: e.target.value || null })}
                className="mt-1 w-full bg-[#1e222d] border border-[#2a2e39] text-white rounded-md px-3 py-2"
                disabled={loadingBots}
              >
                <option value="">Nenhum (apenas registrar sinais)</option>
                {availableBots.map(bot => (
                  <option key={bot.id} value={bot.id}>
                    {bot.name} ({bot.market_type.toUpperCase()}) - {bot.default_leverage}x / SL: {bot.default_stop_loss_pct}% / TP: {bot.default_take_profit_pct}%
                  </option>
                ))}
              </select>
              {config.bot_id && (
                <div className="mt-3 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                  <p className="text-sm text-emerald-300 font-medium flex items-center gap-2">
                    <Bot className="w-4 h-4" />
                    Execucao automatica ativada
                  </p>
                  <p className="text-xs text-emerald-300/70 mt-1">
                    Quando a estrategia detectar um sinal, o bot executara a ordem automaticamente
                    usando as configuracoes de alavancagem, SL e TP definidas no bot.
                  </p>
                </div>
              )}
              {!config.bot_id && (
                <div className="mt-3 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <p className="text-sm text-yellow-300 font-medium">
                    Modo somente sinais
                  </p>
                  <p className="text-xs text-yellow-300/70 mt-1">
                    Os sinais serao registrados no historico mas nenhuma ordem sera executada.
                    Util para testes ou monitoramento.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Indicators Tab */}
        {activeTab === 'indicators' && (
          <div>
            <p className="text-gray-400 text-sm mb-4">
              Selecione os indicadores tecnicos que serao usados para gerar sinais.
              A ordem dos indicadores define a prioridade de calculo.
            </p>
            <IndicatorSelector
              indicators={config.indicators}
              onChange={(indicators) => updateConfig({ indicators })}
              maxIndicators={5}
            />
          </div>
        )}

        {/* Conditions Tab */}
        {activeTab === 'conditions' && (
          <div>
            <p className="text-gray-400 text-sm mb-4">
              Defina as condicoes de entrada e saida baseadas nos indicadores configurados.
            </p>
            <ConditionBuilder
              conditions={config.conditions}
              onChange={(conditions) => updateConfig({ conditions })}
              availableIndicators={config.indicators.map(i => i.type)}
            />
          </div>
        )}
      </div>

      {/* Summary Card */}
      <Card className="p-4 bg-[#131722] border-[#2a2e39]">
        <p className="text-xs text-gray-400 mb-2">Resumo da Estrategia</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-white">{config.symbols.length}</p>
            <p className="text-xs text-gray-500">Simbolos</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-emerald-400">{config.indicators.length}</p>
            <p className="text-xs text-gray-500">Indicadores</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-purple-400">{config.conditions.length}</p>
            <p className="text-xs text-gray-500">Condicoes</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-400">{config.timeframe}</p>
            <p className="text-xs text-gray-500">Timeframe</p>
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="flex justify-between pt-4 border-t border-[#2a2e39]">
        <Button
          variant="outline"
          onClick={resetConfig}
          className="border-[#2a2e39] text-gray-400"
        >
          <RotateCcw className="w-4 h-4 mr-2" />
          Resetar
        </Button>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={onCancel}
            className="border-[#2a2e39] text-gray-300"
          >
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            disabled={!isValid || isSaving}
            className="bg-emerald-600 hover:bg-emerald-700"
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? 'Salvando...' : 'Salvar Estrategia'}
          </Button>
        </div>
      </div>
    </div>
  )
}
