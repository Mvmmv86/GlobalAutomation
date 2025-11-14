/**
 * AllIndicatorsTest - Teste COMPLETO de TODOS os 30+ indicadores
 * Sistema PROFISSIONAL organizado por categorias
 */

import React, { useEffect, useRef, useState } from 'react'
import { CanvasProChart, CanvasProChartHandle } from '../index'
import { Candle } from '../types'
import {
  INDICATOR_PRESETS,
  INDICATOR_CATEGORIES,
  INDICATOR_NAMES,
  IndicatorType,
  AnyIndicatorConfig
} from '../indicators/types'

// Gerar 500 candles realísticos com múltiplos cenários
function generateTestCandles(count: number): Candle[] {
  const candles: Candle[] = []
  let price = 50000
  const startTime = Date.now() - count * 60000

  for (let i = 0; i < count; i++) {
    // Criar cenários variados
    let trend = 0
    if (i < count * 0.3) {
      // 30% inicial: Tendência de alta
      trend = i * 3
    } else if (i < count * 0.6) {
      // 30% meio: Lateral/consolidação
      trend = (count * 0.3) * 3 + Math.sin(i / 10) * 100
    } else {
      // 40% final: Tendência de baixa
      trend = (count * 0.6) * 3 - (i - count * 0.6) * 2
    }

    const volatility = Math.random() * 300
    const change = (Math.random() - 0.5) * volatility + trend / 10
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * volatility * 0.3
    const low = Math.min(open, close) - Math.random() * volatility * 0.3
    const volume = Math.random() * 2000000 + 500000

    candles.push({
      time: startTime + i * 60000,
      open,
      high,
      low,
      close,
      volume
    })

    price = close
  }

  return candles
}

export const AllIndicatorsTest: React.FC = () => {
  const [testCandles] = useState<Candle[]>(generateTestCandles(500))
  const [testResults, setTestResults] = useState<string[]>([])
  const [activeIndicators, setActiveIndicators] = useState<Set<string>>(new Set())
  const [selectedCategory, setSelectedCategory] = useState<string>('TREND')
  const chartHandleRef = useRef<CanvasProChartHandle>(null)

  const addTestResult = (message: string) => {
    console.log(`[AllIndicatorsTest] ${message}`)
    setTestResults(prev => [...prev.slice(-20), message]) // Manter últimas 20 linhas
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      addTestResult('🧪 Sistema de 30+ indicadores inicializado!')
      addTestResult(`📊 ${testCandles.length} candles de teste carregados`)
      addTestResult('✅ Todos os presets configurados')
      addTestResult(`📈 Categorias: ${Object.keys(INDICATOR_CATEGORIES).length}`)
      addTestResult('👆 Selecione uma categoria e adicione indicadores!')
    }, 2000)

    return () => clearTimeout(timer)
  }, [testCandles.length])

  const handleAddIndicator = (type: IndicatorType) => {
    if (!chartHandleRef.current) {
      addTestResult('❌ Chart não inicializado')
      return
    }

    const preset = INDICATOR_PRESETS[type]
    const config: AnyIndicatorConfig = {
      id: `${type.toLowerCase()}-${Date.now()}`,
      type,
      enabled: true,
      displayType: preset.displayType || 'overlay',
      color: preset.color || '#FFFFFF',
      lineWidth: preset.lineWidth || 2,
      params: preset.params || {}
    } as AnyIndicatorConfig

    try {
      chartHandleRef.current.addIndicator(config)
      setActiveIndicators(prev => new Set(prev).add(type))
      addTestResult(`✅ ${INDICATOR_NAMES[type]} (${type}) adicionado!`)
    } catch (error) {
      addTestResult(`❌ Erro ao adicionar ${type}: ${error}`)
    }
  }

  const handleRemoveIndicator = (type: IndicatorType) => {
    if (!chartHandleRef.current) return

    try {
      const indicators = chartHandleRef.current.getIndicators()
      const toRemove = indicators.find(ind => ind.type === type)

      if (toRemove) {
        chartHandleRef.current.removeIndicator(toRemove.id)
        setActiveIndicators(prev => {
          const next = new Set(prev)
          next.delete(type)
          return next
        })
        addTestResult(`🗑️ ${INDICATOR_NAMES[type]} removido`)
      }
    } catch (error) {
      addTestResult(`❌ Erro ao remover ${type}: ${error}`)
    }
  }

  const handleClearAll = () => {
    if (!chartHandleRef.current) return

    try {
      chartHandleRef.current.clearIndicators()
      setActiveIndicators(new Set())
      addTestResult('🧹 Todos os indicadores removidos!')
    } catch (error) {
      addTestResult(`❌ Erro ao limpar: ${error}`)
    }
  }

  const handleAddAllInCategory = () => {
    const category = INDICATOR_CATEGORIES[selectedCategory as keyof typeof INDICATOR_CATEGORIES]
    if (!category) return

    category.forEach(type => {
      setTimeout(() => handleAddIndicator(type), 100)
    })
    addTestResult(`➕ Adicionando todos os ${category.length} indicadores de ${selectedCategory}...`)
  }

  const renderCategoryButtons = (category: keyof typeof INDICATOR_CATEGORIES) => {
    const indicators = INDICATOR_CATEGORIES[category]
    const categoryColors: Record<string, string> = {
      TREND: '#2196F3',
      MOMENTUM: '#9C27B0',
      VOLATILITY: '#FF5722',
      VOLUME: '#FF9800',
      OSCILLATORS: '#4CAF50',
      DIRECTIONAL: '#795548'
    }

    return (
      <div style={{ marginBottom: '20px' }}>
        <h3 style={{ color: categoryColors[category], marginBottom: '10px', fontSize: '16px' }}>
          {category} ({indicators.length} indicadores)
        </h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {indicators.map(type => {
            const isActive = activeIndicators.has(type)
            return (
              <button
                key={type}
                onClick={() => isActive ? handleRemoveIndicator(type) : handleAddIndicator(type)}
                style={{
                  padding: '6px 12px',
                  background: isActive ? '#4CAF50' : categoryColors[category],
                  color: 'white',
                  border: isActive ? '2px solid #81C784' : 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  transition: 'all 0.2s'
                }}
              >
                {isActive ? '✓ ' : '+ '}{type}
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div style={{
      padding: '20px',
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      background: '#0a0a0a',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '15px' }}>
        <h2 style={{ color: 'white', marginBottom: '8px', fontSize: '20px' }}>
          🚀 Teste Completo - 30+ Indicadores Técnicos
        </h2>

        {/* Stats */}
        <div style={{
          display: 'flex',
          gap: '15px',
          marginBottom: '10px',
          padding: '10px',
          background: '#1a1a1a',
          borderRadius: '4px'
        }}>
          <div style={{ color: '#4CAF50', fontWeight: 'bold' }}>
            ✅ Ativos: {activeIndicators.size}
          </div>
          <div style={{ color: '#2196F3' }}>
            📊 Candles: {testCandles.length}
          </div>
          <div style={{ color: '#FF9800' }}>
            📈 Total Disponível: {Object.keys(INDICATOR_NAMES).length}
          </div>
        </div>

        {/* Console */}
        <div style={{
          background: '#1a1a1a',
          padding: '8px',
          borderRadius: '4px',
          maxHeight: '120px',
          overflowY: 'auto',
          fontFamily: 'monospace',
          fontSize: '11px'
        }}>
          {testResults.map((result, i) => (
            <div key={i} style={{
              color: result.includes('❌') ? '#ff4444' :
                     result.includes('✅') ? '#44ff44' :
                     result.includes('🧪') ? '#ffaa00' : '#aaaaaa',
              marginBottom: '2px'
            }}>
              {result}
            </div>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div style={{
        flex: 1,
        display: 'flex',
        gap: '15px',
        overflow: 'hidden'
      }}>
        {/* Sidebar - Indicators */}
        <div style={{
          width: '380px',
          background: '#1a1a1a',
          padding: '15px',
          borderRadius: '4px',
          overflowY: 'auto'
        }}>
          <div style={{ marginBottom: '15px', display: 'flex', gap: '10px' }}>
            <button
              onClick={handleAddAllInCategory}
              style={{
                flex: 1,
                padding: '10px',
                background: '#2196F3',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              ➕ Adicionar Categoria
            </button>
            <button
              onClick={handleClearAll}
              style={{
                flex: 1,
                padding: '10px',
                background: '#F44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold'
              }}
            >
              🧹 Limpar Todos
            </button>
          </div>

          {/* Category Tabs */}
          <div style={{
            display: 'flex',
            gap: '5px',
            marginBottom: '15px',
            flexWrap: 'wrap'
          }}>
            {Object.keys(INDICATOR_CATEGORIES).map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                style={{
                  padding: '6px 12px',
                  background: selectedCategory === cat ? '#2196F3' : '#333',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: selectedCategory === cat ? 'bold' : 'normal'
                }}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Indicators by Category */}
          {selectedCategory && renderCategoryButtons(selectedCategory as keyof typeof INDICATOR_CATEGORIES)}
        </div>

        {/* Chart */}
        <div style={{
          flex: 1,
          position: 'relative',
          border: '2px solid #333',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          <CanvasProChart
            ref={chartHandleRef}
            symbol="BTCUSDT"
            interval="1m"
            theme="dark"
            candles={testCandles}
            height="100%"
          />
        </div>
      </div>
    </div>
  )
}
