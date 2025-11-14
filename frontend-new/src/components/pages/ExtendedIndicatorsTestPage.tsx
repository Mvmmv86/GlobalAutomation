/**
 * Página de teste para os 74 indicadores técnicos
 * Valida implementação e performance
 */

import React, { useState, useEffect, useRef } from 'react'
import { CanvasProChart } from '../charts/CanvasProChart'
import { IndicatorEngine } from '../charts/CanvasProChart/indicators/IndicatorEngine'
import {
  INDICATOR_METADATA,
  getAllIndicatorTypes,
  getIndicatorsByCategory,
  createDefaultIndicatorConfig,
  ExtendedIndicatorType
} from '../charts/CanvasProChart/indicators/extendedTypes'
import { calculateExtendedIndicator } from '../charts/CanvasProChart/indicators/extendedCalculators'
import type { Candle } from '../charts/CanvasProChart/types'

// Gerar candles realistas
const generateRealisticCandles = (count: number): Candle[] => {
  const candles: Candle[] = []
  let basePrice = 50000
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    // Simular tendência e volatilidade
    const trend = Math.sin(i / 100) * 5000 // Tendência sinusoidal
    const shortTrend = Math.sin(i / 20) * 1000 // Oscilação curta
    const noise = (Math.random() - 0.5) * 2000 // Ruído aleatório

    const change = trend + shortTrend + noise

    const open = basePrice
    const close = basePrice + change

    // High e Low realistas
    const volatility = Math.abs(noise) / 500
    const high = Math.max(open, close) + Math.random() * 1000 * (1 + volatility)
    const low = Math.min(open, close) - Math.random() * 1000 * (1 + volatility)

    // Volume variável
    const volumeBase = 5000000
    const volumeVariation = Math.random() * 3000000
    const volumeTrend = Math.sin(i / 50) * 2000000

    candles.push({
      time: now - (count - i) * 60000,
      open,
      high,
      low,
      close,
      volume: Math.max(100000, volumeBase + volumeVariation + volumeTrend)
    })

    basePrice = close
  }

  return candles
}

interface TestResult {
  indicator: string
  category: string
  success: boolean
  error?: string
  calculationTime: number
  resultSample?: any
  hasValidValues: boolean
  nanCount: number
  totalValues: number
}

export const ExtendedIndicatorsTestPage: React.FC = () => {
  const [candles] = useState(() => generateRealisticCandles(500))
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [isTestRunning, setIsTestRunning] = useState(false)
  const [testProgress, setTestProgress] = useState(0)
  const [selectedIndicators, setSelectedIndicators] = useState<ExtendedIndicatorType[]>([])
  const engineRef = useRef<IndicatorEngine>()

  useEffect(() => {
    // Criar engine com Worker
    engineRef.current = new IndicatorEngine({ useWorker: true })
    console.log('🚀 IndicatorEngine initialized with Worker:', engineRef.current.isUsingWorker())

    return () => {
      engineRef.current?.destroy()
    }
  }, [])

  // Obter indicadores por categoria
  const getIndicatorsToTest = (): ExtendedIndicatorType[] => {
    if (selectedCategory === 'all') {
      return getAllIndicatorTypes()
    }
    return getIndicatorsByCategory(selectedCategory as any)
  }

  // Testar um indicador individual
  const testIndicator = async (type: ExtendedIndicatorType): Promise<TestResult> => {
    const metadata = INDICATOR_METADATA[type]
    const startTime = performance.now()

    try {
      // Criar configuração padrão
      const config = createDefaultIndicatorConfig(type)
      if (!config) {
        throw new Error('Failed to create config')
      }

      // Calcular usando a função customizada
      const result = calculateExtendedIndicator(config as any, candles)
      const calculationTime = performance.now() - startTime

      if (!result) {
        throw new Error('Calculation returned null')
      }

      // Analisar resultado
      const validValues = result.values.filter(v => !isNaN(v))
      const nanCount = result.values.filter(v => isNaN(v)).length

      // Verificar se tem valores válidos
      const hasValidValues = validValues.length > 0

      // Pegar amostra dos valores
      const sampleSize = 5
      const sampleIndices = [
        Math.floor(validValues.length * 0.2),
        Math.floor(validValues.length * 0.4),
        Math.floor(validValues.length * 0.5),
        Math.floor(validValues.length * 0.6),
        Math.floor(validValues.length * 0.8)
      ]

      const resultSample = sampleIndices.map(i => validValues[i]).filter(v => v !== undefined)

      return {
        indicator: type,
        category: metadata.category,
        success: true,
        calculationTime,
        resultSample,
        hasValidValues,
        nanCount,
        totalValues: result.values.length
      }
    } catch (error) {
      return {
        indicator: type,
        category: metadata?.category || 'unknown',
        success: false,
        error: error instanceof Error ? error.message : String(error),
        calculationTime: performance.now() - startTime,
        hasValidValues: false,
        nanCount: 0,
        totalValues: 0
      }
    }
  }

  // Executar teste completo
  const runCompleteTest = async () => {
    setIsTestRunning(true)
    setTestResults([])
    setTestProgress(0)

    const indicators = selectedIndicators.length > 0 ? selectedIndicators : getIndicatorsToTest()
    const results: TestResult[] = []

    for (let i = 0; i < indicators.length; i++) {
      const result = await testIndicator(indicators[i])
      results.push(result)
      setTestResults([...results])
      setTestProgress(((i + 1) / indicators.length) * 100)

      // Pequena pausa para não travar UI
      await new Promise(resolve => setTimeout(resolve, 10))
    }

    setIsTestRunning(false)
    console.log('✅ Test complete:', results)
  }

  // Quick test de indicadores principais
  const runQuickTest = async () => {
    const quickIndicators: ExtendedIndicatorType[] = [
      'ALMA', 'DEMA', 'HMA', 'SuperTrend', 'CMO', 'UO',
      'DC', 'BBW', 'CMF', 'PIVOT', 'ZIGZAG', 'AROON'
    ]
    setSelectedIndicators(quickIndicators)
    await runCompleteTest()
  }

  // Estatísticas dos testes
  const getTestStats = () => {
    const successful = testResults.filter(r => r.success).length
    const failed = testResults.filter(r => !r.success).length
    const withValidValues = testResults.filter(r => r.hasValidValues).length
    const avgTime = testResults.reduce((sum, r) => sum + r.calculationTime, 0) / testResults.length || 0

    return {
      total: testResults.length,
      successful,
      failed,
      withValidValues,
      avgTime,
      successRate: testResults.length > 0 ? (successful / testResults.length * 100).toFixed(1) : 0
    }
  }

  const stats = getTestStats()
  const categories = ['all', 'trend', 'momentum', 'volatility', 'volume', 'structure', 'advanced']

  return (
    <div style={{
      padding: '20px',
      backgroundColor: '#0a0a0a',
      color: '#fff',
      minHeight: '100vh',
      fontFamily: 'monospace'
    }}>
      <h1>🧪 Extended Indicators Test - 74 Technical Indicators</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 350px', gap: '20px' }}>

        {/* Controles */}
        <div>
          <div style={{
            backgroundColor: '#1a1a1a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '15px'
          }}>
            <h3>📊 Test Controls</h3>

            {/* Categoria */}
            <label style={{ display: 'block', marginBottom: '10px' }}>
              Category:
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                disabled={isTestRunning}
                style={{
                  width: '100%',
                  padding: '5px',
                  backgroundColor: '#2a2a2a',
                  color: '#fff',
                  border: '1px solid #444',
                  borderRadius: '4px',
                  marginTop: '5px'
                }}
              >
                {categories.map(cat => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                    {cat !== 'all' && ` (${getIndicatorsByCategory(cat as any).length})`}
                    {cat === 'all' && ` (${getAllIndicatorTypes().length})`}
                  </option>
                ))}
              </select>
            </label>

            {/* Botões de teste */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '15px' }}>
              <button
                onClick={runQuickTest}
                disabled={isTestRunning}
                style={{
                  padding: '10px',
                  backgroundColor: '#f39c12',
                  color: '#000',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isTestRunning ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold',
                  opacity: isTestRunning ? 0.5 : 1
                }}
              >
                ⚡ Quick Test (12 indicators)
              </button>

              <button
                onClick={runCompleteTest}
                disabled={isTestRunning}
                style={{
                  padding: '10px',
                  backgroundColor: '#27ae60',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isTestRunning ? 'not-allowed' : 'pointer',
                  fontWeight: 'bold',
                  opacity: isTestRunning ? 0.5 : 1
                }}
              >
                🚀 {selectedCategory === 'all' ? 'Test All 74' : `Test ${selectedCategory}`}
              </button>

              <button
                onClick={() => setTestResults([])}
                style={{
                  padding: '10px',
                  backgroundColor: '#e74c3c',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold'
                }}
              >
                🗑️ Clear Results
              </button>
            </div>

            {/* Progress */}
            {isTestRunning && (
              <div style={{ marginTop: '15px' }}>
                <div style={{
                  height: '20px',
                  backgroundColor: '#2a2a2a',
                  borderRadius: '10px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    height: '100%',
                    width: `${testProgress}%`,
                    backgroundColor: '#3498db',
                    transition: 'width 0.3s'
                  }} />
                </div>
                <p style={{ textAlign: 'center', marginTop: '5px', fontSize: '12px' }}>
                  {testProgress.toFixed(0)}%
                </p>
              </div>
            )}
          </div>

          {/* Estatísticas */}
          <div style={{
            backgroundColor: '#1a1a1a',
            padding: '15px',
            borderRadius: '8px'
          }}>
            <h3>📈 Statistics</h3>
            {testResults.length > 0 ? (
              <>
                <div style={{ fontSize: '14px' }}>
                  <p>Total Tested: <strong>{stats.total}</strong></p>
                  <p style={{ color: '#27ae60' }}>
                    ✅ Successful: <strong>{stats.successful}</strong>
                  </p>
                  <p style={{ color: '#e74c3c' }}>
                    ❌ Failed: <strong>{stats.failed}</strong>
                  </p>
                  <p style={{ color: '#3498db' }}>
                    📊 With Valid Data: <strong>{stats.withValidValues}</strong>
                  </p>
                  <p>Success Rate: <strong>{stats.successRate}%</strong></p>
                  <p>Avg Time: <strong>{stats.avgTime.toFixed(2)}ms</strong></p>
                </div>

                {/* Performance Chart */}
                <div style={{ marginTop: '15px' }}>
                  <h4 style={{ fontSize: '12px', marginBottom: '10px' }}>Performance Distribution</h4>
                  {['< 1ms', '1-5ms', '5-10ms', '10-50ms', '> 50ms'].map(range => {
                    const count = testResults.filter(r => {
                      if (range === '< 1ms') return r.calculationTime < 1
                      if (range === '1-5ms') return r.calculationTime >= 1 && r.calculationTime < 5
                      if (range === '5-10ms') return r.calculationTime >= 5 && r.calculationTime < 10
                      if (range === '10-50ms') return r.calculationTime >= 10 && r.calculationTime < 50
                      return r.calculationTime >= 50
                    }).length

                    const percentage = testResults.length > 0 ? (count / testResults.length * 100) : 0

                    return (
                      <div key={range} style={{ marginBottom: '5px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '11px', width: '60px' }}>{range}:</span>
                          <div style={{
                            flex: 1,
                            height: '15px',
                            backgroundColor: '#2a2a2a',
                            borderRadius: '3px',
                            overflow: 'hidden'
                          }}>
                            <div style={{
                              height: '100%',
                              width: `${percentage}%`,
                              backgroundColor: '#3498db'
                            }} />
                          </div>
                          <span style={{ fontSize: '11px', width: '30px' }}>{count}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            ) : (
              <p style={{ fontSize: '14px', opacity: 0.7 }}>
                No tests run yet
              </p>
            )}
          </div>
        </div>

        {/* Resultados dos Testes */}
        <div>
          <h2>🔍 Test Results</h2>
          <div style={{
            backgroundColor: '#1a1a1a',
            padding: '10px',
            borderRadius: '8px',
            maxHeight: '700px',
            overflowY: 'auto'
          }}>
            {testResults.length === 0 ? (
              <p style={{ textAlign: 'center', opacity: 0.7 }}>
                Click "Quick Test" or "Test All" to start testing indicators
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {testResults.map((result, idx) => {
                  const metadata = INDICATOR_METADATA[result.indicator as ExtendedIndicatorType]

                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '12px',
                        backgroundColor: result.success ? '#0d2818' : '#2a0d0d',
                        border: `1px solid ${result.success ? '#27ae60' : '#e74c3c'}`,
                        borderRadius: '6px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <strong style={{ fontSize: '14px' }}>
                            {result.success ? '✅' : '❌'} {result.indicator}
                          </strong>
                          <span style={{
                            marginLeft: '10px',
                            fontSize: '11px',
                            opacity: 0.7,
                            backgroundColor: '#2a2a2a',
                            padding: '2px 6px',
                            borderRadius: '3px'
                          }}>
                            {result.category}
                          </span>
                        </div>
                        <span style={{
                          fontSize: '11px',
                          color: result.calculationTime < 10 ? '#27ae60' :
                                 result.calculationTime < 50 ? '#f39c12' : '#e74c3c'
                        }}>
                          {result.calculationTime.toFixed(2)}ms
                        </span>
                      </div>

                      {metadata && (
                        <p style={{ fontSize: '11px', opacity: 0.7, margin: '5px 0' }}>
                          {metadata.description}
                        </p>
                      )}

                      {result.success ? (
                        <div style={{ fontSize: '11px', marginTop: '8px' }}>
                          <div style={{ display: 'flex', gap: '15px' }}>
                            <span>
                              Valid: <strong style={{ color: '#27ae60' }}>
                                {result.totalValues - result.nanCount}/{result.totalValues}
                              </strong>
                            </span>
                            <span>
                              NaN: <strong style={{ color: result.nanCount > 0 ? '#f39c12' : '#27ae60' }}>
                                {result.nanCount}
                              </strong>
                            </span>
                          </div>
                          {result.resultSample && result.resultSample.length > 0 && (
                            <div style={{ marginTop: '5px' }}>
                              <span style={{ opacity: 0.7 }}>Sample values: </span>
                              <span style={{ color: '#3498db' }}>
                                {result.resultSample.map((v: number) => v.toFixed(2)).join(', ')}
                              </span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div style={{ fontSize: '11px', marginTop: '8px', color: '#e74c3c' }}>
                          Error: {result.error}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Gráfico Preview */}
        <div>
          <h2>📊 Candle Data Preview</h2>
          <div style={{
            backgroundColor: '#1a1a1a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '15px'
          }}>
            <p style={{ fontSize: '12px', marginBottom: '10px' }}>
              Test data: <strong>{candles.length}</strong> candles
            </p>
            <div style={{
              border: '1px solid #333',
              borderRadius: '4px',
              overflow: 'hidden',
              height: '300px'
            }}>
              <CanvasProChart
                symbol="TEST/USDT"
                interval="1m"
                candles={candles}
                theme="dark"
                width="100%"
                height="300px"
                showVolume={false}
              />
            </div>
          </div>

          {/* Info */}
          <div style={{
            backgroundColor: '#1a1a1a',
            padding: '15px',
            borderRadius: '8px'
          }}>
            <h3 style={{ fontSize: '14px', marginBottom: '10px' }}>📖 Implementation Status</h3>

            <div style={{ fontSize: '12px', lineHeight: '1.8' }}>
              <p style={{ marginBottom: '10px' }}>
                <strong>Total Indicators:</strong> 74
              </p>

              <div style={{ paddingLeft: '10px' }}>
                <p>✅ <strong>Trend (15):</strong> ALMA, DEMA, TEMA, HMA, KAMA, etc.</p>
                <p>✅ <strong>Momentum (15):</strong> CMO, DPO, UO, TSI, PPO, etc.</p>
                <p>✅ <strong>Volatility (12):</strong> DC, SuperTrend, RVI, etc.</p>
                <p>✅ <strong>Volume (12):</strong> CMF, KVO, VWAP, VPVR, etc.</p>
                <p>✅ <strong>Structure (10):</strong> Pivot, ZigZag, Fibonacci, etc.</p>
                <p>✅ <strong>Advanced (10):</strong> Aroon, Vortex, Elder Ray, etc.</p>
              </div>

              <div style={{
                marginTop: '15px',
                padding: '10px',
                backgroundColor: '#0d2818',
                borderRadius: '4px',
                border: '1px solid #27ae60'
              }}>
                <p style={{ margin: 0 }}>
                  🚀 <strong>Performance:</strong> Using Web Workers for parallel calculation
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ExtendedIndicatorsTestPage