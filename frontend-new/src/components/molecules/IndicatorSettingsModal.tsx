/**
 * IndicatorSettingsModal - Modal para configurar parâmetros de indicadores
 * Permite ajustar cores, períodos e outros parâmetros específicos de cada indicador
 */

import React, { useState, useEffect, useMemo } from 'react'
import { X, RotateCcw, Check, Palette } from 'lucide-react'
import {
  AnyIndicatorConfig,
  IndicatorType,
  INDICATOR_NAMES,
  INDICATOR_PRESETS
} from '@/utils/indicators'

interface IndicatorSettingsModalProps {
  indicator: AnyIndicatorConfig | null
  isOpen: boolean
  onClose: () => void
  onSave: (indicator: AnyIndicatorConfig) => void
}

// Cores predefinidas para seleção rápida
const PRESET_COLORS = [
  '#2196F3', // Blue
  '#4CAF50', // Green
  '#F44336', // Red
  '#FF9800', // Orange
  '#9C27B0', // Purple
  '#00BCD4', // Cyan
  '#E91E63', // Pink
  '#FFEB3B', // Yellow
  '#795548', // Brown
  '#607D8B', // Gray
  '#FF5722', // Deep Orange
  '#8BC34A', // Light Green
]

// Definição dos parâmetros por tipo de indicador
const INDICATOR_PARAMS_CONFIG: Record<string, {
  label: string
  key: string
  type: 'number' | 'color'
  min?: number
  max?: number
  step?: number
  description?: string
}[]> = {
  // TREND
  SMA: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 500, step: 1, description: 'Número de períodos para calcular a média' }
  ],
  EMA: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 500, step: 1, description: 'Número de períodos para calcular a média exponencial' }
  ],
  WMA: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 500, step: 1, description: 'Número de períodos para calcular a média ponderada' }
  ],
  WEMA: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 500, step: 1, description: 'Número de períodos para suavização de Wilder' }
  ],
  TRIX: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período do TRIX' }
  ],
  MACD: [
    { label: 'Período Rápido', key: 'fastPeriod', type: 'number', min: 1, max: 100, step: 1, description: 'EMA rápida (geralmente 12)' },
    { label: 'Período Lento', key: 'slowPeriod', type: 'number', min: 1, max: 100, step: 1, description: 'EMA lenta (geralmente 26)' },
    { label: 'Período Sinal', key: 'signalPeriod', type: 'number', min: 1, max: 50, step: 1, description: 'Linha de sinal (geralmente 9)' }
  ],
  ICHIMOKU: [
    { label: 'Conversão (Tenkan)', key: 'conversionPeriod', type: 'number', min: 1, max: 100, step: 1, description: 'Período da linha de conversão' },
    { label: 'Base (Kijun)', key: 'basePeriod', type: 'number', min: 1, max: 100, step: 1, description: 'Período da linha base' },
    { label: 'Span', key: 'spanPeriod', type: 'number', min: 1, max: 200, step: 1, description: 'Período do span' },
    { label: 'Deslocamento', key: 'displacement', type: 'number', min: 1, max: 100, step: 1, description: 'Deslocamento para frente' }
  ],

  // MOMENTUM
  RSI: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Períodos para cálculo do RSI' },
    { label: 'Sobrecomprado', key: 'overbought', type: 'number', min: 50, max: 100, step: 1, description: 'Nível de sobrecompra' },
    { label: 'Sobrevendido', key: 'oversold', type: 'number', min: 0, max: 50, step: 1, description: 'Nível de sobrevenda' }
  ],
  ROC: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período para taxa de mudança' }
  ],
  KST: [
    { label: 'ROC 1', key: 'roc1', type: 'number', min: 1, max: 50, step: 1 },
    { label: 'ROC 2', key: 'roc2', type: 'number', min: 1, max: 50, step: 1 },
    { label: 'ROC 3', key: 'roc3', type: 'number', min: 1, max: 50, step: 1 },
    { label: 'ROC 4', key: 'roc4', type: 'number', min: 1, max: 100, step: 1 },
    { label: 'SMA 1', key: 'sma1', type: 'number', min: 1, max: 50, step: 1 },
    { label: 'SMA 2', key: 'sma2', type: 'number', min: 1, max: 50, step: 1 },
    { label: 'SMA 3', key: 'sma3', type: 'number', min: 1, max: 50, step: 1 },
    { label: 'SMA 4', key: 'sma4', type: 'number', min: 1, max: 50, step: 1 },
    { label: 'Sinal', key: 'signalPeriod', type: 'number', min: 1, max: 50, step: 1 }
  ],
  PSAR: [
    { label: 'Step', key: 'step', type: 'number', min: 0.001, max: 0.1, step: 0.001, description: 'Fator de aceleração inicial' },
    { label: 'Max', key: 'max', type: 'number', min: 0.1, max: 0.5, step: 0.01, description: 'Fator de aceleração máximo' }
  ],
  WILLR: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período do Williams %R' }
  ],
  STOCHRSI: [
    { label: 'Período RSI', key: 'rsiPeriod', type: 'number', min: 1, max: 100, step: 1, description: 'Período para RSI' },
    { label: 'Período Stoch', key: 'stochPeriod', type: 'number', min: 1, max: 100, step: 1, description: 'Período para Stochastic' },
    { label: 'K', key: 'kPeriod', type: 'number', min: 1, max: 50, step: 1, description: 'Período da linha K' },
    { label: 'D', key: 'dPeriod', type: 'number', min: 1, max: 50, step: 1, description: 'Período da linha D' }
  ],

  // VOLATILITY
  BB: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período da média móvel' },
    { label: 'Desvio Padrão', key: 'stdDev', type: 'number', min: 0.5, max: 5, step: 0.1, description: 'Multiplicador do desvio padrão' }
  ],
  ATR: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período do ATR' }
  ],
  KC: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período da EMA central' },
    { label: 'Período ATR', key: 'atrPeriod', type: 'number', min: 1, max: 50, step: 1, description: 'Período do ATR' },
    { label: 'Multiplicador', key: 'multiplier', type: 'number', min: 0.5, max: 5, step: 0.1, description: 'Multiplicador do canal' }
  ],

  // VOLUME
  VWAP: [],
  OBV: [],
  ADL: [],
  FI: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 50, step: 1, description: 'Período de suavização' }
  ],
  MFI: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período do MFI' }
  ],
  VP: [
    { label: 'Barras', key: 'numberOfBars', type: 'number', min: 10, max: 500, step: 10, description: 'Número de barras para análise' },
    { label: 'Zonas', key: 'priceZones', type: 'number', min: 6, max: 48, step: 1, description: 'Número de zonas de preço' }
  ],

  // OSCILLATORS
  STOCH: [
    { label: 'Período K', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período da linha %K' },
    { label: 'Período D', key: 'signalPeriod', type: 'number', min: 1, max: 50, step: 1, description: 'Período da linha %D (sinal)' }
  ],
  CCI: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período do CCI' }
  ],
  AO: [
    { label: 'Período Rápido', key: 'fastPeriod', type: 'number', min: 1, max: 50, step: 1, description: 'SMA rápida' },
    { label: 'Período Lento', key: 'slowPeriod', type: 'number', min: 10, max: 100, step: 1, description: 'SMA lenta' }
  ],

  // DIRECTIONAL
  ADX: [
    { label: 'Período', key: 'period', type: 'number', min: 1, max: 100, step: 1, description: 'Período do ADX' }
  ]
}

export const IndicatorSettingsModal: React.FC<IndicatorSettingsModalProps> = ({
  indicator,
  isOpen,
  onClose,
  onSave
}) => {
  // Estado local para edição
  const [localIndicator, setLocalIndicator] = useState<AnyIndicatorConfig | null>(null)
  const [showColorPicker, setShowColorPicker] = useState(false)

  // Sincronizar estado local quando o indicador muda
  useEffect(() => {
    if (indicator) {
      setLocalIndicator({ ...indicator })
    }
  }, [indicator])

  // Configurações de parâmetros para o tipo de indicador atual
  const paramsConfig = useMemo(() => {
    if (!localIndicator) return []
    return INDICATOR_PARAMS_CONFIG[localIndicator.type] || []
  }, [localIndicator?.type])

  // Handler para atualizar parâmetro
  const handleParamChange = (key: string, value: number) => {
    if (!localIndicator) return
    setLocalIndicator({
      ...localIndicator,
      params: {
        ...localIndicator.params,
        [key]: value
      }
    })
  }

  // Handler para atualizar cor
  const handleColorChange = (color: string) => {
    if (!localIndicator) return
    setLocalIndicator({
      ...localIndicator,
      color
    })
  }

  // Handler para atualizar espessura da linha
  const handleLineWidthChange = (lineWidth: number) => {
    if (!localIndicator) return
    setLocalIndicator({
      ...localIndicator,
      lineWidth
    })
  }

  // Handler para resetar aos valores padrão
  const handleReset = () => {
    if (!localIndicator) return
    const preset = INDICATOR_PRESETS[localIndicator.type as IndicatorType]
    if (preset) {
      setLocalIndicator({
        ...localIndicator,
        color: preset.color || localIndicator.color,
        lineWidth: preset.lineWidth || localIndicator.lineWidth,
        params: { ...preset.params } as any
      })
    }
  }

  // Handler para salvar
  const handleSave = () => {
    if (localIndicator) {
      onSave(localIndicator)
      onClose()
    }
  }

  if (!isOpen || !localIndicator) return null

  const indicatorName = INDICATOR_NAMES[localIndicator.type as IndicatorType] || localIndicator.type

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-md mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 rounded-full border-2 border-white/20"
              style={{ backgroundColor: localIndicator.color }}
            />
            <h2 className="text-lg font-semibold text-white">
              {indicatorName}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh] space-y-6">
          {/* Cor do Indicador */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm font-medium text-gray-300">
              <Palette className="w-4 h-4" />
              Cor do Indicador
            </label>
            <div className="flex flex-wrap gap-2">
              {PRESET_COLORS.map(color => (
                <button
                  key={color}
                  onClick={() => handleColorChange(color)}
                  className={`w-8 h-8 rounded-lg border-2 transition-all hover:scale-110 ${
                    localIndicator.color === color
                      ? 'border-white shadow-lg shadow-white/20'
                      : 'border-transparent hover:border-gray-500'
                  }`}
                  style={{ backgroundColor: color }}
                  title={color}
                />
              ))}
            </div>
            {/* Input de cor customizada */}
            <div className="flex items-center gap-2 mt-2">
              <input
                type="color"
                value={localIndicator.color}
                onChange={(e) => handleColorChange(e.target.value)}
                className="w-10 h-8 rounded cursor-pointer bg-transparent"
              />
              <input
                type="text"
                value={localIndicator.color}
                onChange={(e) => handleColorChange(e.target.value)}
                className="flex-1 px-3 py-1.5 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white font-mono focus:border-blue-500 focus:outline-none"
                placeholder="#FFFFFF"
              />
            </div>
          </div>

          {/* Espessura da Linha */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">
              Espessura da Linha: {localIndicator.lineWidth}px
            </label>
            <input
              type="range"
              min="1"
              max="5"
              step="1"
              value={localIndicator.lineWidth}
              onChange={(e) => handleLineWidthChange(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>Fino</span>
              <span>Grosso</span>
            </div>
          </div>

          {/* Parâmetros Específicos */}
          {paramsConfig.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                Parâmetros
              </h3>
              {paramsConfig.map(param => (
                <div key={param.key} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-medium text-gray-300">
                      {param.label}
                    </label>
                    <span className="text-sm text-blue-400 font-mono">
                      {localIndicator.params[param.key]}
                    </span>
                  </div>
                  {param.description && (
                    <p className="text-xs text-gray-500">{param.description}</p>
                  )}
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={param.min || 1}
                      max={param.max || 100}
                      step={param.step || 1}
                      value={localIndicator.params[param.key] || 0}
                      onChange={(e) => handleParamChange(param.key, parseFloat(e.target.value))}
                      className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                    />
                    <input
                      type="number"
                      min={param.min || 1}
                      max={param.max || 100}
                      step={param.step || 1}
                      value={localIndicator.params[param.key] || 0}
                      onChange={(e) => handleParamChange(param.key, parseFloat(e.target.value))}
                      className="w-20 px-2 py-1 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white text-center focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Mensagem se não há parâmetros configuráveis */}
          {paramsConfig.length === 0 && (
            <div className="text-center py-4 text-gray-500 text-sm">
              Este indicador não possui parâmetros configuráveis.
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700 bg-gray-800/30">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Resetar
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
            >
              <Check className="w-4 h-4" />
              Aplicar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default IndicatorSettingsModal
