/**
 * IndicatorPanel - Painel flutuante para gerenciar indicadores
 * Permite adicionar/remover/configurar indicadores de forma visual
 */

import React, { useState } from 'react'
import { X, Plus, Settings, Eye, EyeOff, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { AnyIndicatorConfig, IndicatorType, INDICATOR_CATEGORIES, INDICATOR_NAMES, INDICATOR_PRESETS } from '../indicators/types'

interface IndicatorPanelProps {
  activeIndicators: AnyIndicatorConfig[]
  onAddIndicator: (type: IndicatorType) => void
  onRemoveIndicator: (id: string) => void
  onToggleIndicator: (id: string, enabled: boolean) => void
  onUpdateIndicator?: (id: string, updates: Partial<AnyIndicatorConfig>) => void
  theme?: 'dark' | 'light'
  onClose: () => void
}

export const IndicatorPanel: React.FC<IndicatorPanelProps> = ({
  activeIndicators,
  onAddIndicator,
  onRemoveIndicator,
  onToggleIndicator,
  onUpdateIndicator,
  theme = 'dark',
  onClose
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('TREND')
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['active', 'add']))

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(section)) {
      newExpanded.delete(section)
    } else {
      newExpanded.add(section)
    }
    setExpandedSections(newExpanded)
  }

  const bgColor = theme === 'dark' ? '#1a1a1a' : '#ffffff'
  const textColor = theme === 'dark' ? '#d1d4dc' : '#131722'
  const borderColor = theme === 'dark' ? '#2a2e39' : '#e0e3eb'

  const categoryColors: Record<string, string> = {
    TREND: '#2196F3',
    MOMENTUM: '#9C27B0',
    VOLATILITY: '#FF5722',
    VOLUME: '#FF9800',
    OSCILLATORS: '#4CAF50',
    DIRECTIONAL: '#795548'
  }

  return (
    <div style={{
      position: 'absolute',
      top: 60,
      right: 10,
      width: 380,
      maxHeight: 'calc(100% - 70px)',
      background: bgColor,
      border: `1px solid ${borderColor}`,
      borderRadius: '8px',
      boxShadow: theme === 'dark'
        ? '0 8px 32px rgba(0,0,0,0.6)'
        : '0 8px 32px rgba(0,0,0,0.15)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 16px',
        borderBottom: `1px solid ${borderColor}`,
        background: theme === 'dark' ? '#242731' : '#f5f5f5'
      }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: textColor }}>
          📊 Indicadores Técnicos
        </h3>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: textColor,
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center'
          }}
        >
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>

        {/* Active Indicators Section */}
        <div style={{ marginBottom: '16px' }}>
          <button
            onClick={() => toggleSection('active')}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'transparent',
              border: 'none',
              color: textColor,
              padding: '8px 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 600
            }}
          >
            <span>Ativos ({activeIndicators.length})</span>
            {expandedSections.has('active') ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {expandedSections.has('active') && (
            <div style={{ marginTop: '8px' }}>
              {activeIndicators.length === 0 ? (
                <div style={{
                  padding: '16px',
                  textAlign: 'center',
                  color: theme === 'dark' ? '#787b86' : '#999',
                  fontSize: '13px'
                }}>
                  Nenhum indicador ativo
                </div>
              ) : (
                activeIndicators.map(indicator => (
                  <div
                    key={indicator.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '10px 12px',
                      marginBottom: '6px',
                      background: theme === 'dark' ? '#242731' : '#f9f9f9',
                      border: `1px solid ${borderColor}`,
                      borderRadius: '6px'
                    }}
                  >
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '12px',
                          height: '12px',
                          borderRadius: '2px',
                          background: indicator.color
                        }}
                      />
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 500, color: textColor }}>
                          {INDICATOR_NAMES[indicator.type as IndicatorType] || indicator.type}
                        </div>
                        <div style={{ fontSize: '11px', color: theme === 'dark' ? '#787b86' : '#999' }}>
                          {indicator.displayType === 'separate' ? '📊 Painel Separado' : '📈 Overlay'}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '4px' }}>
                      <button
                        onClick={() => onToggleIndicator(indicator.id, !indicator.enabled)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: indicator.enabled ? '#4CAF50' : theme === 'dark' ? '#787b86' : '#999',
                          cursor: 'pointer',
                          padding: '4px'
                        }}
                        title={indicator.enabled ? 'Ocultar' : 'Mostrar'}
                      >
                        {indicator.enabled ? <Eye size={16} /> : <EyeOff size={16} />}
                      </button>

                      <button
                        onClick={() => onRemoveIndicator(indicator.id)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: '#ef5350',
                          cursor: 'pointer',
                          padding: '4px'
                        }}
                        title="Remover"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Add Indicators Section */}
        <div>
          <button
            onClick={() => toggleSection('add')}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: 'transparent',
              border: 'none',
              color: textColor,
              padding: '8px 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 600
            }}
          >
            <span>Adicionar Indicador</span>
            {expandedSections.has('add') ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {expandedSections.has('add') && (
            <div style={{ marginTop: '8px' }}>
              {/* Category Tabs */}
              <div style={{
                display: 'flex',
                gap: '4px',
                marginBottom: '12px',
                flexWrap: 'wrap'
              }}>
                {Object.keys(INDICATOR_CATEGORIES).map(cat => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    style={{
                      padding: '6px 10px',
                      background: selectedCategory === cat ? categoryColors[cat] : 'transparent',
                      color: selectedCategory === cat ? 'white' : textColor,
                      border: `1px solid ${selectedCategory === cat ? categoryColors[cat] : borderColor}`,
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px',
                      fontWeight: selectedCategory === cat ? 600 : 400,
                      transition: 'all 0.2s'
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              {/* Indicators List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {INDICATOR_CATEGORIES[selectedCategory as keyof typeof INDICATOR_CATEGORIES]?.map(type => {
                  const isActive = activeIndicators.some(ind => ind.type === type)

                  return (
                    <button
                      key={type}
                      onClick={() => !isActive && onAddIndicator(type)}
                      disabled={isActive}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '10px 12px',
                        background: isActive
                          ? (theme === 'dark' ? '#1a3a1a' : '#e8f5e9')
                          : (theme === 'dark' ? '#242731' : '#f9f9f9'),
                        border: `1px solid ${isActive ? '#4CAF50' : borderColor}`,
                        borderRadius: '6px',
                        cursor: isActive ? 'not-allowed' : 'pointer',
                        fontSize: '13px',
                        color: textColor,
                        opacity: isActive ? 0.6 : 1,
                        transition: 'all 0.2s'
                      }}
                    >
                      <span>{INDICATOR_NAMES[type] || type}</span>
                      {isActive ? (
                        <span style={{ fontSize: '11px', color: '#4CAF50' }}>✓ Ativo</span>
                      ) : (
                        <Plus size={16} style={{ color: categoryColors[selectedCategory] }} />
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{
        padding: '12px 16px',
        borderTop: `1px solid ${borderColor}`,
        background: theme === 'dark' ? '#242731' : '#f5f5f5',
        fontSize: '11px',
        color: theme === 'dark' ? '#787b86' : '#999',
        textAlign: 'center'
      }}>
        Total: {Object.values(INDICATOR_CATEGORIES).flat().length} indicadores disponíveis
      </div>
    </div>
  )
}
