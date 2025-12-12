/**
 * IndicatorSelector - Dropdown para selecionar indicadores técnicos
 * Organizado por categorias com UI profissional
 */

import React, { useState, useRef, useEffect } from 'react'
import {
  IndicatorType,
  INDICATOR_CATEGORIES,
  INDICATOR_NAMES,
  INDICATOR_PRESETS
} from '@/utils/indicators'

interface IndicatorSelectorProps {
  onSelect: (type: IndicatorType) => void
  activeIndicators?: string[]
  className?: string
}

const CATEGORY_LABELS: Record<keyof typeof INDICATOR_CATEGORIES, string> = {
  TREND: 'Trend',
  MOMENTUM: 'Momentum',
  VOLATILITY: 'Volatility',
  MARKET_PROFILE: 'Market Profile',
  VOLUME: 'Volume',
  OSCILLATORS: 'Oscillators',
  DIRECTIONAL: 'Directional'
}

const CATEGORY_ICONS: Record<keyof typeof INDICATOR_CATEGORIES, string> = {
  TREND: '📈',
  MOMENTUM: '⚡',
  VOLATILITY: '📊',
  MARKET_PROFILE: '🏛️',
  VOLUME: '📦',
  OSCILLATORS: '🔄',
  DIRECTIONAL: '🧭'
}

export const IndicatorSelector: React.FC<IndicatorSelectorProps> = ({
  onSelect,
  activeIndicators = [],
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (type: IndicatorType) => {
    onSelect(type)
    setIsOpen(false)
    setSearchTerm('')
  }

  // Filter indicators based on search
  const filteredCategories = Object.entries(INDICATOR_CATEGORIES).map(([category, types]) => ({
    category: category as keyof typeof INDICATOR_CATEGORIES,
    types: types.filter(type =>
      INDICATOR_NAMES[type].toLowerCase().includes(searchTerm.toLowerCase()) ||
      type.toLowerCase().includes(searchTerm.toLowerCase())
    )
  })).filter(({ types }) => types.length > 0)

  const isIndicatorActive = (type: IndicatorType) => {
    return activeIndicators.some(id => id.toLowerCase().startsWith(type.toLowerCase()))
  }

  return (
    <div ref={dropdownRef} className={`relative ${className}`}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700
                   border border-gray-600 rounded-lg text-sm text-gray-200
                   transition-colors duration-150"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <span>Indicators</span>
        <svg
          className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 w-72 bg-gray-800 border border-gray-700
                     rounded-lg shadow-xl z-50 overflow-hidden"
        >
          {/* Search */}
          <div className="p-2 border-b border-gray-700">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search indicators..."
              className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded
                         text-sm text-gray-200 placeholder-gray-500
                         focus:outline-none focus:border-blue-500"
              autoFocus
            />
          </div>

          {/* Categories */}
          <div className="max-h-80 overflow-y-auto">
            {filteredCategories.map(({ category, types }) => (
              <div key={category} className="border-b border-gray-700 last:border-b-0">
                {/* Category Header */}
                <button
                  onClick={() => setExpandedCategory(
                    expandedCategory === category ? null : category
                  )}
                  className="w-full flex items-center justify-between px-3 py-2
                             hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span>{CATEGORY_ICONS[category]}</span>
                    <span className="text-sm font-medium text-gray-200">
                      {CATEGORY_LABELS[category]}
                    </span>
                    <span className="text-xs text-gray-500">
                      ({types.length})
                    </span>
                  </div>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform duration-200
                              ${expandedCategory === category ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* Indicator List */}
                {expandedCategory === category && (
                  <div className="bg-gray-900/50">
                    {types.map(type => {
                      const preset = INDICATOR_PRESETS[type]
                      const isActive = isIndicatorActive(type)

                      return (
                        <button
                          key={type}
                          onClick={() => handleSelect(type)}
                          className={`w-full flex items-center justify-between px-4 py-2
                                     text-left hover:bg-gray-700/50 transition-colors
                                     ${isActive ? 'bg-blue-900/20' : ''}`}
                        >
                          <div className="flex items-center gap-2">
                            <div
                              className="w-3 h-3 rounded-full"
                              style={{ backgroundColor: preset.color }}
                            />
                            <div>
                              <div className="text-sm text-gray-200">
                                {INDICATOR_NAMES[type]}
                              </div>
                              <div className="text-xs text-gray-500">
                                {type} - {preset.displayType}
                              </div>
                            </div>
                          </div>
                          {isActive && (
                            <span className="text-xs text-blue-400">Active</span>
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="p-2 border-t border-gray-700 bg-gray-900/50">
            <div className="text-xs text-gray-500 text-center">
              {Object.values(INDICATOR_CATEGORIES).flat().length} indicators available
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default IndicatorSelector
