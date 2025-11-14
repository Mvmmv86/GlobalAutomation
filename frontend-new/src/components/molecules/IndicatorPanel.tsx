/**
 * IndicatorPanel - Painel de seleção de 30+ indicadores técnicos
 */

import React, { useState } from 'react'
import { TrendingUp, X } from 'lucide-react'
import { Button } from '../atoms/Button'
import {
  INDICATOR_CATEGORIES,
  INDICATOR_NAMES,
  INDICATOR_PRESETS,
  IndicatorType,
  AnyIndicatorConfig
} from '../charts/CanvasProChart/indicators/types'

interface IndicatorPanelProps {
  isOpen: boolean
  onClose: () => void
  activeIndicators: string[]
  onAddIndicator: (type: IndicatorType) => void
  onRemoveIndicator: (type: IndicatorType) => void
  onClearAll: () => void
}

const CATEGORY_COLORS: Record<string, string> = {
  TREND: '#2196F3',
  MOMENTUM: '#9C27B0',
  VOLATILITY: '#FF5722',
  VOLUME: '#FF9800',
  OSCILLATORS: '#4CAF50',
  DIRECTIONAL: '#795548'
}

export const IndicatorPanel: React.FC<IndicatorPanelProps> = ({
  isOpen,
  onClose,
  activeIndicators,
  onAddIndicator,
  onRemoveIndicator,
  onClearAll
}) => {
  const [selectedCategory, setSelectedCategory] = useState<keyof typeof INDICATOR_CATEGORIES>('TREND')

  if (!isOpen) return null

  const indicators = INDICATOR_CATEGORIES[selectedCategory]
  const activeCount = activeIndicators.length

  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-gray-900 border-l border-gray-700 shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-blue-400" />
          <h3 className="text-lg font-bold text-white">Indicadores</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="text-gray-400 hover:text-white"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Stats */}
      <div className="px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-400">Ativos:</span>
          <span className="font-bold text-green-400">{activeCount}</span>
        </div>
        {activeCount > 0 && (
          <Button
            variant="destructive"
            size="sm"
            onClick={onClearAll}
            className="w-full mt-2"
          >
            Limpar Todos
          </Button>
        )}
      </div>

      {/* Category Tabs */}
      <div className="px-4 py-3 border-b border-gray-700 overflow-x-auto">
        <div className="flex gap-2 flex-wrap">
          {Object.keys(INDICATOR_CATEGORIES).map(cat => {
            const category = cat as keyof typeof INDICATOR_CATEGORIES
            const isActive = selectedCategory === category
            const color = CATEGORY_COLORS[cat]

            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(category)}
                className="px-3 py-1.5 rounded text-xs font-medium transition-all"
                style={{
                  background: isActive ? color : 'transparent',
                  color: isActive ? 'white' : color,
                  border: `1px solid ${color}`
                }}
              >
                {cat}
              </button>
            )
          })}
        </div>
      </div>

      {/* Indicators List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {indicators.map(type => {
            const isActive = activeIndicators.includes(type)
            const color = CATEGORY_COLORS[selectedCategory]
            const name = INDICATOR_NAMES[type]

            return (
              <button
                key={type}
                onClick={() => isActive ? onRemoveIndicator(type) : onAddIndicator(type)}
                className="w-full px-3 py-2 rounded text-left text-sm transition-all flex items-center justify-between"
                style={{
                  background: isActive ? color : 'rgba(255,255,255,0.05)',
                  border: `1px solid ${isActive ? color : 'rgba(255,255,255,0.1)'}`,
                  color: 'white'
                }}
              >
                <div className="flex items-center gap-2">
                  {isActive && (
                    <span className="w-2 h-2 rounded-full bg-green-400" />
                  )}
                  <span className="font-medium">{type}</span>
                </div>
                <span className="text-xs text-gray-400">{name}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-gray-700 bg-gray-800">
        <div className="text-xs text-gray-400">
          <p className="mb-1">
            <span className="font-bold text-white">{indicators.length}</span> indicadores em {selectedCategory}
          </p>
          <p>
            <span className="font-bold text-white">{Object.keys(INDICATOR_NAMES).length}</span> total disponível
          </p>
        </div>
      </div>
    </div>
  )
}
