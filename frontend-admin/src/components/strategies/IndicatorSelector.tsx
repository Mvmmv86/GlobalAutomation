/**
 * IndicatorSelector Component
 * Allows selecting and configuring indicators for a strategy
 */
import { useState } from 'react'
import { Plus, Trash2, Settings, ChevronDown, ChevronUp } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { Label } from '@/components/atoms/Label'
import { Badge } from '@/components/atoms/Badge'

// Available indicator types with their default parameters
export const AVAILABLE_INDICATORS = [
  {
    type: 'nadaraya_watson',
    label: 'Nadaraya-Watson Envelope',
    description: 'Envelope baseado em regressao kernel',
    category: 'trend',
    params: [
      { name: 'bandwidth', label: 'Bandwidth', type: 'number', default: 8, min: 1, max: 50 },
      { name: 'mult', label: 'Multiplicador', type: 'number', default: 3.0, min: 0.5, max: 5, step: 0.1 },
    ],
    outputs: ['upper', 'lower', 'middle'],
  },
  {
    type: 'tpo',
    label: 'TPO (Market Profile)',
    description: 'Time Price Opportunity - Perfil de mercado com POC, VAH e VAL',
    category: 'volume',
    params: [
      { name: 'session_hours', label: 'Horas da Sessao', type: 'number', default: 24, min: 1, max: 168 },
      { name: 'tick_size', label: 'Tick Size', type: 'number', default: 0.5, min: 0.01, max: 10, step: 0.01 },
      { name: 'value_area_percent', label: 'Value Area (%)', type: 'number', default: 70, min: 50, max: 90 },
    ],
    outputs: ['poc', 'vah', 'val', 'profile'],
  },
  {
    type: 'rsi',
    label: 'RSI (Relative Strength Index)',
    description: 'Indicador de forca relativa',
    category: 'momentum',
    params: [
      { name: 'period', label: 'Periodo', type: 'number', default: 14, min: 2, max: 50 },
      { name: 'overbought', label: 'Sobrecomprado', type: 'number', default: 70, min: 50, max: 90 },
      { name: 'oversold', label: 'Sobrevendido', type: 'number', default: 30, min: 10, max: 50 },
    ],
    outputs: ['value'],
  },
  {
    type: 'macd',
    label: 'MACD',
    description: 'Moving Average Convergence Divergence',
    category: 'momentum',
    params: [
      { name: 'fast', label: 'EMA Rapida', type: 'number', default: 12, min: 2, max: 50 },
      { name: 'slow', label: 'EMA Lenta', type: 'number', default: 26, min: 10, max: 100 },
      { name: 'signal', label: 'Linha de Sinal', type: 'number', default: 9, min: 2, max: 20 },
    ],
    outputs: ['macd', 'signal', 'histogram'],
  },
  {
    type: 'ema',
    label: 'EMA (Exponential Moving Average)',
    description: 'Media movel exponencial',
    category: 'trend',
    params: [
      { name: 'period', label: 'Periodo', type: 'number', default: 20, min: 2, max: 200 },
    ],
    outputs: ['value'],
  },
  {
    type: 'ema_cross',
    label: 'EMA Cross (Cruzamento de Medias)',
    description: 'Sinal de cruzamento entre EMA rapida e lenta',
    category: 'trend',
    params: [
      { name: 'fast_period', label: 'EMA Rapida', type: 'number', default: 9, min: 2, max: 50 },
      { name: 'slow_period', label: 'EMA Lenta', type: 'number', default: 21, min: 5, max: 200 },
    ],
    outputs: ['fast', 'slow', 'cross'],
  },
  {
    type: 'sma',
    label: 'SMA (Simple Moving Average)',
    description: 'Media movel simples',
    category: 'trend',
    params: [
      { name: 'period', label: 'Periodo', type: 'number', default: 20, min: 2, max: 200 },
    ],
    outputs: ['value'],
  },
  {
    type: 'bollinger',
    label: 'Bollinger Bands',
    description: 'Bandas de Bollinger',
    category: 'volatility',
    params: [
      { name: 'period', label: 'Periodo', type: 'number', default: 20, min: 5, max: 50 },
      { name: 'std_dev', label: 'Desvio Padrao', type: 'number', default: 2, min: 1, max: 4, step: 0.5 },
    ],
    outputs: ['upper', 'middle', 'lower'],
  },
  {
    type: 'atr',
    label: 'ATR (Average True Range)',
    description: 'Volatilidade media',
    category: 'volatility',
    params: [
      { name: 'period', label: 'Periodo', type: 'number', default: 14, min: 2, max: 50 },
    ],
    outputs: ['value'],
  },
  {
    type: 'stochastic',
    label: 'Stochastic Oscillator',
    description: 'Oscilador estocastico',
    category: 'momentum',
    params: [
      { name: 'k_period', label: 'Periodo %K', type: 'number', default: 14, min: 2, max: 50 },
      { name: 'd_period', label: 'Periodo %D', type: 'number', default: 3, min: 1, max: 10 },
      { name: 'overbought', label: 'Sobrecomprado', type: 'number', default: 80, min: 60, max: 95 },
      { name: 'oversold', label: 'Sobrevendido', type: 'number', default: 20, min: 5, max: 40 },
    ],
    outputs: ['k', 'd'],
  },
  {
    type: 'volume_profile',
    label: 'Volume Profile',
    description: 'Perfil de volume',
    category: 'volume',
    params: [
      { name: 'lookback', label: 'Lookback (candles)', type: 'number', default: 24, min: 10, max: 100 },
    ],
    outputs: ['poc', 'vah', 'val'],
  },
]

export interface IndicatorConfig {
  id: string
  type: string
  parameters: Record<string, number>
  order_index: number
}

interface IndicatorSelectorProps {
  indicators: IndicatorConfig[]
  onChange: (indicators: IndicatorConfig[]) => void
  maxIndicators?: number
}

export function IndicatorSelector({ indicators, onChange, maxIndicators = 5 }: IndicatorSelectorProps) {
  const [showAddPanel, setShowAddPanel] = useState(false)
  const [expandedIndicator, setExpandedIndicator] = useState<string | null>(null)

  const getIndicatorInfo = (type: string) => {
    return AVAILABLE_INDICATORS.find(i => i.type === type)
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'trend': return 'bg-blue-500/20 text-blue-300 border-blue-500/50'
      case 'momentum': return 'bg-purple-500/20 text-purple-300 border-purple-500/50'
      case 'volatility': return 'bg-orange-500/20 text-orange-300 border-orange-500/50'
      case 'volume': return 'bg-green-500/20 text-green-300 border-green-500/50'
      default: return 'bg-gray-500/20 text-gray-300 border-gray-500/50'
    }
  }

  const addIndicator = (type: string) => {
    const indicatorInfo = getIndicatorInfo(type)
    if (!indicatorInfo) return

    const defaultParams: Record<string, number> = {}
    indicatorInfo.params.forEach(p => {
      defaultParams[p.name] = p.default
    })

    const newIndicator: IndicatorConfig = {
      id: `${type}_${Date.now()}`,
      type,
      parameters: defaultParams,
      order_index: indicators.length,
    }

    onChange([...indicators, newIndicator])
    setShowAddPanel(false)
  }

  const removeIndicator = (id: string) => {
    const filtered = indicators.filter(i => i.id !== id)
    // Reindex
    const reindexed = filtered.map((ind, idx) => ({ ...ind, order_index: idx }))
    onChange(reindexed)
  }

  const updateParameter = (id: string, paramName: string, value: number) => {
    onChange(indicators.map(ind => {
      if (ind.id === id) {
        return {
          ...ind,
          parameters: { ...ind.parameters, [paramName]: value }
        }
      }
      return ind
    }))
  }

  const moveIndicator = (id: string, direction: 'up' | 'down') => {
    const idx = indicators.findIndex(i => i.id === id)
    if (idx === -1) return
    if (direction === 'up' && idx === 0) return
    if (direction === 'down' && idx === indicators.length - 1) return

    const newIndicators = [...indicators]
    const swapIdx = direction === 'up' ? idx - 1 : idx + 1

    // Swap
    const temp = newIndicators[idx]
    newIndicators[idx] = newIndicators[swapIdx]
    newIndicators[swapIdx] = temp

    // Reindex
    const reindexed = newIndicators.map((ind, i) => ({ ...ind, order_index: i }))
    onChange(reindexed)
  }

  return (
    <div className="space-y-4">
      {/* Current Indicators */}
      <div className="space-y-3">
        {indicators.length === 0 ? (
          <Card className="p-6 bg-[#131722] border-[#2a2e39] text-center">
            <Settings className="w-8 h-8 text-gray-600 mx-auto mb-2" />
            <p className="text-gray-400 text-sm">Nenhum indicador adicionado</p>
            <p className="text-gray-500 text-xs mt-1">Clique em "Adicionar Indicador" para comecar</p>
          </Card>
        ) : (
          indicators.map((indicator, idx) => {
            const info = getIndicatorInfo(indicator.type)
            const isExpanded = expandedIndicator === indicator.id

            return (
              <Card key={indicator.id} className="p-4 bg-[#131722] border-[#2a2e39]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500 text-sm font-mono">#{idx + 1}</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{info?.label || indicator.type}</span>
                        <Badge variant="default" className={getCategoryColor(info?.category || '')}>
                          {info?.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">{info?.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => moveIndicator(indicator.id, 'up')}
                      disabled={idx === 0}
                      className="p-1 h-7 w-7"
                    >
                      <ChevronUp className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => moveIndicator(indicator.id, 'down')}
                      disabled={idx === indicators.length - 1}
                      className="p-1 h-7 w-7"
                    >
                      <ChevronDown className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedIndicator(isExpanded ? null : indicator.id)}
                      className="p-1 h-7 w-7"
                    >
                      <Settings className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeIndicator(indicator.id)}
                      className="p-1 h-7 w-7 text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Parameters (expandable) */}
                {isExpanded && info && (
                  <div className="mt-4 pt-4 border-t border-[#2a2e39]">
                    <p className="text-xs text-gray-400 mb-3">Parametros</p>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {info.params.map(param => (
                        <div key={param.name}>
                          <Label className="text-xs text-gray-300">{param.label}</Label>
                          <Input
                            type="number"
                            value={indicator.parameters[param.name] || param.default}
                            onChange={(e) => updateParameter(indicator.id, param.name, parseFloat(e.target.value))}
                            min={param.min}
                            max={param.max}
                            step={param.step || 1}
                            className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white h-8 text-sm"
                          />
                        </div>
                      ))}
                    </div>
                    <div className="mt-3">
                      <p className="text-xs text-gray-400">Outputs disponiveis:</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {info.outputs.map(output => (
                          <code key={output} className="text-xs bg-[#2a2e39] text-cyan-300 px-2 py-0.5 rounded">
                            {indicator.type}.{output}
                          </code>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </Card>
            )
          })
        )}
      </div>

      {/* Add Button */}
      {indicators.length < maxIndicators && (
        <div>
          {!showAddPanel ? (
            <Button
              variant="outline"
              onClick={() => setShowAddPanel(true)}
              className="w-full border-dashed border-[#3a3f4b] text-gray-300 hover:bg-[#2a2e39]"
            >
              <Plus className="w-4 h-4 mr-2" />
              Adicionar Indicador ({indicators.length}/{maxIndicators})
            </Button>
          ) : (
            <Card className="p-4 bg-[#131722] border-[#2a2e39]">
              <div className="flex justify-between items-center mb-3">
                <p className="text-white font-medium">Selecionar Indicador</p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAddPanel(false)}
                  className="text-gray-400"
                >
                  Cancelar
                </Button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                {AVAILABLE_INDICATORS.map(indicator => {
                  const alreadyAdded = indicators.some(i => i.type === indicator.type)
                  return (
                    <button
                      key={indicator.type}
                      onClick={() => !alreadyAdded && addIndicator(indicator.type)}
                      disabled={alreadyAdded}
                      className={`
                        p-3 rounded-lg text-left transition-colors
                        ${alreadyAdded
                          ? 'bg-[#1e222d] opacity-50 cursor-not-allowed'
                          : 'bg-[#1e222d] hover:bg-[#2a2e39] cursor-pointer'
                        }
                      `}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-white text-sm font-medium">{indicator.label}</span>
                        <Badge variant="default" className={`text-xs ${getCategoryColor(indicator.category)}`}>
                          {indicator.category}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{indicator.description}</p>
                      {alreadyAdded && (
                        <span className="text-xs text-yellow-500 mt-1 block">Ja adicionado</span>
                      )}
                    </button>
                  )
                })}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
