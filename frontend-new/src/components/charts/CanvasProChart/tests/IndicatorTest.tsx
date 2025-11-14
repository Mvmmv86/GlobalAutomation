/**
 * IndicatorTest - Teste detalhado do sistema de indicadores
 */

import React, { useEffect, useRef, useState } from 'react'
import { CanvasProChart, CanvasProChartHandle } from '../index'
import { Candle } from '../types'
import { INDICATOR_PRESETS, AnyIndicatorConfig } from '../indicators/types'

// Gerar candles de teste com tendência
function generateTestCandles(count: number): Candle[] {
  const candles: Candle[] = []
  let price = 50000
  const startTime = Date.now() - count * 60000

  for (let i = 0; i < count; i++) {
    // Criar tendência de alta
    const trend = i * 5
    const change = (Math.random() - 0.45) * 500 + trend
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * 200
    const low = Math.min(open, close) - Math.random() * 200
    const volume = Math.random() * 1000000 + 500000

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

export const IndicatorTest: React.FC = () => {
  const [testCandles] = useState<Candle[]>(generateTestCandles(200))
  const [testResults, setTestResults] = useState<string[]>([])
  const [activeIndicators, setActiveIndicators] = useState<string[]>([])
  const chartHandleRef = useRef<CanvasProChartHandle>(null)

  const addTestResult = (message: string) => {
    console.log(`[IndicatorTest] ${message}`)
    setTestResults(prev => [...prev, message])
  }

  useEffect(() => {
    // Aguardar 2 segundos para o chart inicializar
    const timer = setTimeout(() => {
      runTests()
    }, 2000)

    return () => clearTimeout(timer)
  }, [])

  const runTests = () => {
    addTestResult('🧪 Iniciando testes de indicadores...')
    addTestResult(`📊 Candles de teste: ${testCandles.length}`)

    if (!chartHandleRef.current) {
      addTestResult('❌ Chart ref não disponível')
      return
    }

    addTestResult('✅ Chart ref OK')

    // Test 1: Verificar presets
    addTestResult(`✅ Presets carregados: ${Object.keys(INDICATOR_PRESETS).length} indicadores`)

    Object.entries(INDICATOR_PRESETS).forEach(([type, preset]) => {
      const params = JSON.stringify(preset.params).substring(0, 50)
      addTestResult(`  - ${type}: ${preset.displayType}, ${params}`)
    })

    addTestResult('✅ Todos os testes de API passaram!')
    addTestResult('👆 Clique nos botões acima para adicionar indicadores ao gráfico')
  }

  const handleAddEMA = () => {
    if (!chartHandleRef.current) {
      addTestResult('❌ Chart não inicializado')
      return
    }

    const config: AnyIndicatorConfig = {
      id: 'ema-20',
      type: 'EMA',
      enabled: true,
      displayType: 'overlay',
      color: '#FF9800',
      lineWidth: 2,
      params: { period: 20 }
    }

    try {
      chartHandleRef.current.addIndicator(config)
      setActiveIndicators(prev => [...prev, 'EMA(20)'])
      addTestResult('✅ EMA(20) adicionado com sucesso!')
    } catch (error) {
      addTestResult(`❌ Erro ao adicionar EMA: ${error}`)
    }
  }

  const handleAddSMA = () => {
    if (!chartHandleRef.current) return

    const config: AnyIndicatorConfig = {
      id: 'sma-50',
      type: 'SMA',
      enabled: true,
      displayType: 'overlay',
      color: '#2196F3',
      lineWidth: 2,
      params: { period: 50 }
    }

    try {
      chartHandleRef.current.addIndicator(config)
      setActiveIndicators(prev => [...prev, 'SMA(50)'])
      addTestResult('✅ SMA(50) adicionado com sucesso!')
    } catch (error) {
      addTestResult(`❌ Erro ao adicionar SMA: ${error}`)
    }
  }

  const handleAddBB = () => {
    if (!chartHandleRef.current) return

    const config: AnyIndicatorConfig = {
      id: 'bb-20',
      type: 'BB',
      enabled: true,
      displayType: 'overlay',
      color: '#00BCD4',
      lineWidth: 1,
      params: { period: 20, stdDev: 2 }
    }

    try {
      chartHandleRef.current.addIndicator(config)
      setActiveIndicators(prev => [...prev, 'BB(20,2)'])
      addTestResult('✅ Bollinger Bands(20,2) adicionado!')
    } catch (error) {
      addTestResult(`❌ Erro ao adicionar BB: ${error}`)
    }
  }

  const handleClearIndicators = () => {
    if (!chartHandleRef.current) return

    try {
      chartHandleRef.current.clearIndicators()
      setActiveIndicators([])
      addTestResult('🧹 Todos os indicadores removidos!')
    } catch (error) {
      addTestResult(`❌ Erro ao limpar indicadores: ${error}`)
    }
  }

  const handleListIndicators = () => {
    if (!chartHandleRef.current) return

    try {
      const indicators = chartHandleRef.current.getIndicators()
      addTestResult(`📋 Indicadores ativos: ${indicators.length}`)
      indicators.forEach(ind => {
        addTestResult(`  - ${ind.type} (${ind.id}): ${ind.enabled ? 'ON' : 'OFF'}`)
      })
    } catch (error) {
      addTestResult(`❌ Erro ao listar indicadores: ${error}`)
    }
  }

  return (
    <div style={{ padding: '20px', height: '100vh', display: 'flex', flexDirection: 'column', background: '#0a0a0a' }}>
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ color: 'white', marginBottom: '10px' }}>🧪 Teste Detalhado de Indicadores</h2>

        {/* Active Indicators */}
        <div style={{
          background: '#1a1a1a',
          padding: '10px',
          borderRadius: '4px',
          marginBottom: '10px',
          color: 'white'
        }}>
          <strong>Indicadores Ativos:</strong> {activeIndicators.length === 0 ? 'Nenhum' : activeIndicators.join(', ')}
        </div>

        {/* Test Results */}
        <div style={{
          background: '#1a1a1a',
          padding: '10px',
          borderRadius: '4px',
          maxHeight: '200px',
          overflowY: 'auto',
          fontFamily: 'monospace',
          fontSize: '12px'
        }}>
          {testResults.map((result, i) => (
            <div key={i} style={{
              color: result.includes('❌') ? '#ff4444' :
                     result.includes('✅') ? '#44ff44' :
                     result.includes('🧪') ? '#ffaa00' :
                     result.includes('👆') ? '#00aaff' : '#aaaaaa',
              marginBottom: '4px'
            }}>
              {result}
            </div>
          ))}
          {testResults.length === 0 && (
            <div style={{ color: '#666' }}>Aguardando inicialização do chart...</div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, position: 'relative', border: '2px solid #333', borderRadius: '4px', overflow: 'hidden' }}>
        <CanvasProChart
          ref={chartHandleRef}
          symbol="BTCUSDT"
          interval="1m"
          theme="dark"
          candles={testCandles}
          height="100%"
        />
      </div>

      {/* Control Buttons */}
      <div style={{ marginTop: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
        <button
          onClick={handleAddEMA}
          style={{
            padding: '10px 20px',
            background: '#FF9800',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          ➕ Adicionar EMA(20)
        </button>

        <button
          onClick={handleAddSMA}
          style={{
            padding: '10px 20px',
            background: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          ➕ Adicionar SMA(50)
        </button>

        <button
          onClick={handleAddBB}
          style={{
            padding: '10px 20px',
            background: '#00BCD4',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          ➕ Adicionar BB(20,2)
        </button>

        <button
          onClick={handleListIndicators}
          style={{
            padding: '10px 20px',
            background: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          📋 Listar Indicadores
        </button>

        <button
          onClick={handleClearIndicators}
          style={{
            padding: '10px 20px',
            background: '#F44336',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          🧹 Limpar Todos
        </button>

        <button
          onClick={runTests}
          style={{
            padding: '10px 20px',
            background: '#9C27B0',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          🔄 Re-executar Testes
        </button>
      </div>
    </div>
  )
}
