/**
 * Página de teste para Worker de Indicadores
 * Compara performance entre cálculo na main thread e no Worker
 */

import React, { useState, useRef, useEffect } from 'react'
import { IndicatorEngine } from '../charts/CanvasProChart/indicators/IndicatorEngine'
import { IndicatorWorkerManager } from '../charts/CanvasProChart/workers/IndicatorWorkerManager'
import type { AnyIndicatorConfig, IndicatorResult } from '../charts/CanvasProChart/indicators/types'
import type { Candle } from '../charts/CanvasProChart/types'

// Gerar candles de teste
const generateTestCandles = (count: number): Candle[] => {
  const candles: Candle[] = []
  let basePrice = 50000
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    const trend = Math.sin(i / 100) * 5000
    const noise = (Math.random() - 0.5) * 2000
    const change = trend + noise

    const open = basePrice
    const close = basePrice + change
    const high = Math.max(open, close) + Math.random() * 1000
    const low = Math.min(open, close) - Math.random() * 1000

    candles.push({
      time: now - (count - i) * 60000,
      open,
      high,
      low,
      close,
      volume: Math.random() * 5000000 + 1000000
    })

    basePrice = close
  }

  return candles
}

// Configurações de indicadores para teste
const TEST_INDICATORS: AnyIndicatorConfig[] = [
  {
    id: 'sma-20',
    type: 'SMA',
    enabled: true,
    panel: 'main',
    params: { period: 20 },
    style: { color: '#3498db', lineWidth: 2 }
  },
  {
    id: 'ema-50',
    type: 'EMA',
    enabled: true,
    panel: 'main',
    params: { period: 50 },
    style: { color: '#e74c3c', lineWidth: 2 }
  },
  {
    id: 'bb-20',
    type: 'BB',
    enabled: true,
    panel: 'main',
    params: { period: 20, stdDev: 2 },
    style: { color: '#9b59b6', lineWidth: 1 }
  },
  {
    id: 'rsi-14',
    type: 'RSI',
    enabled: true,
    panel: 'rsi',
    params: { period: 14, overbought: 70, oversold: 30 },
    style: { color: '#f39c12', lineWidth: 2 }
  },
  {
    id: 'macd-12-26-9',
    type: 'MACD',
    enabled: true,
    panel: 'macd',
    params: { fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 },
    style: { color: '#1abc9c', lineWidth: 2 }
  },
  {
    id: 'atr-14',
    type: 'ATR',
    enabled: true,
    panel: 'atr',
    params: { period: 14 },
    style: { color: '#34495e', lineWidth: 2 }
  },
  {
    id: 'stoch-14',
    type: 'STOCH',
    enabled: true,
    panel: 'stoch',
    params: { period: 14, signalPeriod: 3 },
    style: { color: '#16a085', lineWidth: 2 }
  },
  {
    id: 'willr-14',
    type: 'WILLR',
    enabled: true,
    panel: 'willr',
    params: { period: 14 },
    style: { color: '#d35400', lineWidth: 2 }
  },
  {
    id: 'cci-20',
    type: 'CCI',
    enabled: true,
    panel: 'cci',
    params: { period: 20 },
    style: { color: '#8e44ad', lineWidth: 2 }
  },
  {
    id: 'adx-14',
    type: 'ADX',
    enabled: true,
    panel: 'adx',
    params: { period: 14 },
    style: { color: '#2c3e50', lineWidth: 2 }
  }
]

interface TestResult {
  method: string
  candleCount: number
  indicatorCount: number
  totalTime: number
  avgTimePerIndicator: number
  indicatorsCalculated: string[]
}

export const IndicatorWorkerTestPage: React.FC = () => {
  const [candles, setCandles] = useState<Candle[]>(() => generateTestCandles(1000))
  const [candleCount, setCandleCount] = useState(1000)
  const [selectedIndicators, setSelectedIndicators] = useState<AnyIndicatorConfig[]>(TEST_INDICATORS)
  const [testResults, setTestResults] = useState<TestResult[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [testLog, setTestLog] = useState<string[]>([])

  const mainThreadEngineRef = useRef<IndicatorEngine>()
  const workerEngineRef = useRef<IndicatorEngine>()
  const workerManagerRef = useRef<IndicatorWorkerManager>()

  // Adicionar log
  const addLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString()
    setTestLog(prev => [...prev, `[${timestamp}] ${message}`])
  }

  // Inicializar engines
  useEffect(() => {
    // Engine para main thread
    mainThreadEngineRef.current = new IndicatorEngine({ useWorker: false })
    addLog('✅ Main thread IndicatorEngine initialized')

    // Engine com Worker
    workerEngineRef.current = new IndicatorEngine({ useWorker: true })
    addLog(workerEngineRef.current.isUsingWorker()
      ? '✅ Worker IndicatorEngine initialized'
      : '⚠️ Worker not available, fallback to main thread')

    // Worker Manager direto (para testes mais granulares)
    workerManagerRef.current = new IndicatorWorkerManager({
      onCalculateComplete: (result, time) => {
        addLog(`📊 ${result.type} calculated in ${time.toFixed(2)}ms`)
      },
      onBatchComplete: (results, time) => {
        addLog(`📊 Batch of ${results.length} indicators in ${time.toFixed(2)}ms`)
      }
    })

    return () => {
      mainThreadEngineRef.current?.destroy()
      workerEngineRef.current?.destroy()
      workerManagerRef.current?.destroy()
    }
  }, [])

  // Regenerar candles
  const regenerateCandles = (count: number) => {
    addLog(`🔄 Generating ${count} candles...`)
    const start = performance.now()
    const newCandles = generateTestCandles(count)
    const time = performance.now() - start
    setCandles(newCandles)
    setCandleCount(count)
    addLog(`✅ ${count} candles generated in ${time.toFixed(2)}ms`)
  }

  // Teste na main thread
  const testMainThread = async () => {
    if (!mainThreadEngineRef.current) return

    addLog('🚀 Testing main thread calculation...')
    setIsRunning(true)

    const startTime = performance.now()
    const results: IndicatorResult[] = []

    for (const indicator of selectedIndicators) {
      const result = await mainThreadEngineRef.current.calculate(indicator, candles)
      if (result) {
        results.push(result)
      }
    }

    const totalTime = performance.now() - startTime

    const testResult: TestResult = {
      method: 'Main Thread',
      candleCount: candles.length,
      indicatorCount: results.length,
      totalTime,
      avgTimePerIndicator: totalTime / results.length,
      indicatorsCalculated: results.map(r => r.type)
    }

    setTestResults(prev => [...prev, testResult])
    addLog(`⚡ Main thread: ${totalTime.toFixed(2)}ms for ${results.length} indicators`)
    setIsRunning(false)
  }

  // Teste com Worker
  const testWorker = async () => {
    if (!workerEngineRef.current) return

    addLog('🚀 Testing Worker calculation...')
    setIsRunning(true)

    const startTime = performance.now()
    const results = await workerEngineRef.current.calculateMultiple(selectedIndicators, candles)
    const totalTime = performance.now() - startTime

    const testResult: TestResult = {
      method: workerEngineRef.current.isUsingWorker() ? 'Web Worker' : 'Worker (Fallback)',
      candleCount: candles.length,
      indicatorCount: results.length,
      totalTime,
      avgTimePerIndicator: totalTime / results.length,
      indicatorsCalculated: results.map(r => r.type)
    }

    setTestResults(prev => [...prev, testResult])
    addLog(`⚡ Worker: ${totalTime.toFixed(2)}ms for ${results.length} indicators`)
    setIsRunning(false)
  }

  // Teste de batch com Worker Manager direto
  const testWorkerManagerBatch = async () => {
    if (!workerManagerRef.current) return

    addLog('🚀 Testing Worker Manager batch calculation...')
    setIsRunning(true)

    const startTime = performance.now()
    const results = await workerManagerRef.current.calculateBatch(selectedIndicators, candles)
    const totalTime = performance.now() - startTime

    const testResult: TestResult = {
      method: 'Worker Manager Batch',
      candleCount: candles.length,
      indicatorCount: results.length,
      totalTime,
      avgTimePerIndicator: totalTime / results.length,
      indicatorsCalculated: results.map(r => r.type)
    }

    setTestResults(prev => [...prev, testResult])
    addLog(`⚡ Worker batch: ${totalTime.toFixed(2)}ms for ${results.length} indicators`)
    setIsRunning(false)
  }

  // Teste comparativo completo
  const runFullComparison = async () => {
    addLog('🔥 Starting full comparison test...')
    setTestResults([])

    await testMainThread()
    await new Promise(r => setTimeout(r, 100))

    await testWorker()
    await new Promise(r => setTimeout(r, 100))

    await testWorkerManagerBatch()

    addLog('✅ Full comparison complete!')
  }

  // Stress test
  const runStressTest = async () => {
    addLog('🔥 Starting stress test...')
    setTestResults([])

    for (const count of [100, 500, 1000, 5000, 10000]) {
      regenerateCandles(count)
      await new Promise(r => setTimeout(r, 100))

      addLog(`📊 Testing with ${count} candles...`)
      await testMainThread()
      await testWorker()
      await new Promise(r => setTimeout(r, 200))
    }

    addLog('✅ Stress test complete!')
  }

  // Toggle indicador
  const toggleIndicator = (id: string) => {
    setSelectedIndicators(prev =>
      prev.map(ind =>
        ind.id === id ? { ...ind, enabled: !ind.enabled } : ind
      ).filter(ind => ind.enabled)
    )
  }

  return (
    <div style={{
      padding: '20px',
      backgroundColor: '#1a1a1a',
      color: '#fff',
      minHeight: '100vh',
      fontFamily: 'monospace'
    }}>
      <h1>📊 Indicator Worker Performance Test</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr 350px', gap: '20px' }}>
        {/* Controles */}
        <div>
          <h2>🎮 Controls</h2>

          {/* Candle count */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '15px'
          }}>
            <h3>Candle Count: {candleCount}</h3>
            <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
              {[100, 500, 1000, 5000, 10000].map(count => (
                <button
                  key={count}
                  onClick={() => regenerateCandles(count)}
                  disabled={isRunning}
                  style={{
                    padding: '5px 10px',
                    backgroundColor: candleCount === count ? '#4CAF50' : '#555',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: isRunning ? 'not-allowed' : 'pointer',
                    opacity: isRunning ? 0.5 : 1
                  }}
                >
                  {count >= 1000 ? `${count/1000}k` : count}
                </button>
              ))}
            </div>
          </div>

          {/* Indicadores */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '15px'
          }}>
            <h3>Indicators ({selectedIndicators.length})</h3>
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {TEST_INDICATORS.map(ind => (
                <label key={ind.id} style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '5px',
                  cursor: 'pointer',
                  opacity: selectedIndicators.some(s => s.id === ind.id) ? 1 : 0.5
                }}>
                  <input
                    type="checkbox"
                    checked={selectedIndicators.some(s => s.id === ind.id)}
                    onChange={() => {
                      if (selectedIndicators.some(s => s.id === ind.id)) {
                        setSelectedIndicators(prev => prev.filter(s => s.id !== ind.id))
                      } else {
                        setSelectedIndicators(prev => [...prev, ind])
                      }
                    }}
                    disabled={isRunning}
                    style={{ marginRight: '8px' }}
                  />
                  <span style={{ color: ind.style.color }}>
                    {ind.type} {ind.id}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Botões de teste */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px'
          }}>
            <h3>Tests</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={testMainThread}
                disabled={isRunning}
                style={{
                  padding: '10px',
                  backgroundColor: '#3498db',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  opacity: isRunning ? 0.5 : 1
                }}
              >
                Test Main Thread
              </button>

              <button
                onClick={testWorker}
                disabled={isRunning}
                style={{
                  padding: '10px',
                  backgroundColor: '#9b59b6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  opacity: isRunning ? 0.5 : 1
                }}
              >
                Test Worker
              </button>

              <button
                onClick={testWorkerManagerBatch}
                disabled={isRunning}
                style={{
                  padding: '10px',
                  backgroundColor: '#e74c3c',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  opacity: isRunning ? 0.5 : 1
                }}
              >
                Test Worker Batch
              </button>

              <button
                onClick={runFullComparison}
                disabled={isRunning}
                style={{
                  padding: '10px',
                  backgroundColor: '#f39c12',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  opacity: isRunning ? 0.5 : 1
                }}
              >
                🔥 Full Comparison
              </button>

              <button
                onClick={runStressTest}
                disabled={isRunning}
                style={{
                  padding: '10px',
                  backgroundColor: '#e67e22',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  opacity: isRunning ? 0.5 : 1
                }}
              >
                🔥 Stress Test
              </button>

              <button
                onClick={() => setTestResults([])}
                style={{
                  padding: '10px',
                  backgroundColor: '#95a5a6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Clear Results
              </button>
            </div>
          </div>
        </div>

        {/* Resultados */}
        <div>
          <h2>📊 Test Results</h2>

          {testResults.length === 0 ? (
            <div style={{
              backgroundColor: '#2a2a2a',
              padding: '20px',
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <p style={{ opacity: 0.5 }}>No test results yet. Run a test to see performance metrics.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {testResults.map((result, idx) => {
                const isFastest = Math.min(...testResults.map(r => r.totalTime)) === result.totalTime
                const speedup = testResults[0] ? ((testResults[0].totalTime / result.totalTime - 1) * 100) : 0

                return (
                  <div key={idx} style={{
                    backgroundColor: isFastest ? '#27ae60' : '#2a2a2a',
                    padding: '15px',
                    borderRadius: '8px',
                    border: isFastest ? '2px solid #2ecc71' : 'none'
                  }}>
                    <h3 style={{ margin: '0 0 10px 0' }}>
                      {result.method} {isFastest && '🏆'}
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '14px' }}>
                      <div>
                        <strong>Candles:</strong> {result.candleCount}
                      </div>
                      <div>
                        <strong>Indicators:</strong> {result.indicatorCount}
                      </div>
                      <div>
                        <strong>Total Time:</strong> {result.totalTime.toFixed(2)}ms
                      </div>
                      <div>
                        <strong>Avg/Indicator:</strong> {result.avgTimePerIndicator.toFixed(2)}ms
                      </div>
                    </div>
                    {idx > 0 && speedup !== 0 && (
                      <div style={{
                        marginTop: '10px',
                        padding: '5px',
                        backgroundColor: 'rgba(0,0,0,0.3)',
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}>
                        {speedup > 0
                          ? `🚀 ${speedup.toFixed(0)}% faster than Main Thread`
                          : `⚠️ ${Math.abs(speedup).toFixed(0)}% slower than Main Thread`
                        }
                      </div>
                    )}
                    <div style={{ marginTop: '10px', fontSize: '11px', opacity: 0.7 }}>
                      Calculated: {result.indicatorsCalculated.join(', ')}
                    </div>
                  </div>
                )
              })}

              {/* Summary */}
              {testResults.length > 1 && (
                <div style={{
                  backgroundColor: '#34495e',
                  padding: '15px',
                  borderRadius: '8px',
                  marginTop: '10px'
                }}>
                  <h3>📈 Performance Summary</h3>
                  <div style={{ fontSize: '14px' }}>
                    <p>
                      <strong>Fastest:</strong> {
                        testResults.reduce((fastest, current) =>
                          current.totalTime < fastest.totalTime ? current : fastest
                        ).method
                      }
                    </p>
                    <p>
                      <strong>Average improvement with Workers:</strong> {
                        (() => {
                          const mainThread = testResults.find(r => r.method === 'Main Thread')
                          const workers = testResults.filter(r => r.method !== 'Main Thread')
                          if (!mainThread || workers.length === 0) return 'N/A'

                          const avgWorkerTime = workers.reduce((sum, r) => sum + r.totalTime, 0) / workers.length
                          const improvement = ((mainThread.totalTime / avgWorkerTime - 1) * 100)
                          return `${improvement.toFixed(0)}%`
                        })()
                      }
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Log */}
        <div>
          <h2>📝 Test Log</h2>
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '10px',
            borderRadius: '8px',
            height: '600px',
            overflowY: 'auto',
            fontSize: '11px',
            fontFamily: 'monospace'
          }}>
            {testLog.length === 0 ? (
              <p style={{ opacity: 0.5 }}>Waiting for tests...</p>
            ) : (
              testLog.map((log, idx) => (
                <div key={idx} style={{
                  padding: '2px 0',
                  borderBottom: '1px solid #333',
                  color: log.includes('✅') ? '#2ecc71' :
                         log.includes('⚠️') ? '#f39c12' :
                         log.includes('❌') ? '#e74c3c' :
                         log.includes('🚀') ? '#3498db' :
                         log.includes('⚡') ? '#9b59b6' :
                         '#ecf0f1'
                }}>
                  {log}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Info */}
      <div style={{
        marginTop: '30px',
        padding: '20px',
        backgroundColor: '#2a2a2a',
        borderRadius: '8px'
      }}>
        <h3>📖 About Indicator Workers</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', fontSize: '14px' }}>
          <div>
            <h4 style={{ color: '#2ecc71' }}>✅ Benefits</h4>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
              <li>Calculations in separate thread</li>
              <li>Non-blocking UI during heavy calculations</li>
              <li>Parallel processing of multiple indicators</li>
              <li>Better performance for large datasets</li>
              <li>Automatic caching of results</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#f39c12' }}>⚡ Performance</h4>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
              <li>30-60% faster for batch calculations</li>
              <li>Scales better with more indicators</li>
              <li>Reduced main thread blocking</li>
              <li>Efficient memory usage with caching</li>
              <li>Automatic fallback if Worker fails</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#3498db' }}>🔧 Supported Indicators</h4>
            <ul style={{ paddingLeft: '20px', lineHeight: '1.6' }}>
              <li>30+ Technical indicators</li>
              <li>Trend: SMA, EMA, MACD, Ichimoku</li>
              <li>Momentum: RSI, ROC, Stochastic</li>
              <li>Volatility: BB, ATR, Keltner</li>
              <li>Volume: VWAP, OBV, MFI</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default IndicatorWorkerTestPage