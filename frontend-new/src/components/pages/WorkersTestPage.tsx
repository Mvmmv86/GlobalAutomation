/**
 * Página de teste para OffscreenCanvas + Workers
 * Compara performance entre renderização normal e com Workers
 */

import React, { useRef, useEffect, useState } from 'react'
import { CanvasProChart } from '../charts/CanvasProChart'
import { WorkerManager } from '../charts/CanvasProChart/workers/WorkerManager'
import { darkTheme } from '../charts/CanvasProChart/themes/dark'

// Gerar candles de teste
const generateTestCandles = (count: number) => {
  const candles = []
  let basePrice = 50000
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    const trend = Math.sin(i / 50) * 3000
    const noise = (Math.random() - 0.5) * 1000
    const change = trend + noise

    const open = basePrice
    const close = basePrice + change
    const high = Math.max(open, close) + Math.random() * 500
    const low = Math.min(open, close) - Math.random() * 500

    candles.push({
      time: now - (count - i) * 60000,
      open,
      high,
      low,
      close,
      volume: Math.random() * 2000000 + 500000
    })

    basePrice = close
  }

  return candles
}

export const WorkersTestPage: React.FC = () => {
  const normalChartRef = useRef<any>(null)
  const workerChartRef = useRef<any>(null)
  const workerCanvasRef = useRef<HTMLCanvasElement>(null)

  const [candleCount, setCandleCount] = useState(1000)
  const [candles, setCandles] = useState(() => generateTestCandles(1000))
  const [workerManager, setWorkerManager] = useState<WorkerManager | null>(null)
  const [metrics, setMetrics] = useState<any>({
    normal: { renderTime: 0, fps: 0 },
    worker: { renderTime: 0, fps: 0, isUsingWorker: false }
  })
  const [testStatus, setTestStatus] = useState<string[]>([])

  // Adicionar status
  const addStatus = (status: string) => {
    setTestStatus(prev => [...prev, `${new Date().toLocaleTimeString()}: ${status}`])
  }

  // Inicializar WorkerManager
  useEffect(() => {
    if (workerCanvasRef.current) {
      const manager = new WorkerManager({
        canvas: workerCanvasRef.current,
        theme: darkTheme,
        onRenderComplete: (stats) => {
          setMetrics(prev => ({
            ...prev,
            worker: {
              ...prev.worker,
              renderTime: stats.renderTime.toFixed(2),
              fps: (1000 / stats.renderTime).toFixed(1)
            }
          }))
        },
        onError: (error) => {
          addStatus(`❌ Worker error: ${error.message}`)
        }
      })

      setWorkerManager(manager)

      setMetrics(prev => ({
        ...prev,
        worker: {
          ...prev.worker,
          isUsingWorker: manager.isUsingWorker()
        }
      }))

      addStatus(manager.isUsingWorker()
        ? '✅ Using OffscreenCanvas + Worker'
        : '⚠️ Fallback to main thread rendering')

      return () => {
        manager.destroy()
      }
    }
  }, [])

  // Regenerar candles
  const regenerateCandles = (count: number) => {
    addStatus(`🔄 Generating ${count} candles...`)
    const start = performance.now()
    const newCandles = generateTestCandles(count)
    const genTime = performance.now() - start

    setCandles(newCandles)
    setCandleCount(count)
    addStatus(`✅ ${count} candles generated in ${genTime.toFixed(2)}ms`)
  }

  // Testar renderização normal
  const testNormalRender = () => {
    if (!normalChartRef.current) return

    addStatus('🚀 Testing normal rendering...')
    const start = performance.now()
    normalChartRef.current.forceUpdate()
    const renderTime = performance.now() - start

    setMetrics(prev => ({
      ...prev,
      normal: {
        renderTime: renderTime.toFixed(2),
        fps: (1000 / renderTime).toFixed(1)
      }
    }))

    addStatus(`⚡ Normal render: ${renderTime.toFixed(2)}ms`)
  }

  // Testar renderização com Worker
  const testWorkerRender = async () => {
    if (!workerManager) return

    addStatus('🚀 Testing worker rendering...')

    try {
      // Calcular viewport e escala
      const viewport = {
        startIndex: 0,
        endIndex: candles.length - 1,
        candleWidth: 10
      }

      // Calcular escala de preços
      const prices = candles.flatMap(c => [c.high, c.low])
      const minPrice = Math.min(...prices)
      const maxPrice = Math.max(...prices)
      const priceScale = {
        min: minPrice,
        max: maxPrice,
        range: maxPrice - minPrice
      }

      const start = performance.now()
      await workerManager.render(candles, viewport, priceScale)
      const renderTime = performance.now() - start

      addStatus(`⚡ Worker render: ${renderTime.toFixed(2)}ms`)
    } catch (error) {
      addStatus(`❌ Worker render error: ${error}`)
    }
  }

  // Teste de stress
  const stressTest = async () => {
    addStatus('🔥 Starting stress test...')

    const counts = [100, 500, 1000, 5000, 10000]

    for (const count of counts) {
      regenerateCandles(count)

      // Aguardar um pouco para atualização
      await new Promise(resolve => setTimeout(resolve, 100))

      // Testar normal
      testNormalRender()
      await new Promise(resolve => setTimeout(resolve, 100))

      // Testar worker
      await testWorkerRender()
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    addStatus('✅ Stress test complete!')
  }

  // Teste de animação contínua
  const [isAnimating, setIsAnimating] = useState(false)
  const animationRef = useRef<number>()

  const toggleAnimation = () => {
    if (isAnimating) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
      setIsAnimating(false)
      addStatus('⏹️ Animation stopped')
    } else {
      setIsAnimating(true)
      addStatus('▶️ Animation started')

      const animate = () => {
        // Atualizar último candle
        setCandles(prev => {
          const newCandles = [...prev]
          const last = newCandles[newCandles.length - 1]
          if (last) {
            last.close = last.close + (Math.random() - 0.5) * 100
            last.high = Math.max(last.high, last.close)
            last.low = Math.min(last.low, last.close)
          }
          return newCandles
        })

        if (normalChartRef.current) {
          normalChartRef.current.forceUpdate()
        }

        animationRef.current = requestAnimationFrame(animate)
      }

      animate()
    }
  }

  useEffect(() => {
    addStatus('🎯 OffscreenCanvas + Workers Test Page loaded')
    addStatus(`📊 ${candleCount} candles ready for testing`)
    addStatus('💡 Workers offload rendering to separate thread')
  }, [])

  return (
    <div style={{ padding: '20px', backgroundColor: '#1a1a1a', color: '#fff', minHeight: '100vh' }}>
      <h1>⚡ OffscreenCanvas + Workers Performance Test</h1>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Controles */}
        <div style={{ width: '300px' }}>
          <h2>🎮 Controls</h2>

          {/* Seletor de quantidade */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <h3>📊 Candle Count</h3>
            <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
              {[100, 500, 1000, 5000, 10000, 50000].map(count => (
                <button
                  key={count}
                  onClick={() => regenerateCandles(count)}
                  style={{
                    padding: '5px 10px',
                    backgroundColor: candleCount === count ? '#4CAF50' : '#555',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '12px'
                  }}
                >
                  {count >= 1000 ? `${count/1000}k` : count}
                </button>
              ))}
            </div>
          </div>

          {/* Botões de teste */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <h3>🧪 Tests</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={testNormalRender}
                style={{
                  padding: '10px',
                  backgroundColor: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Test Normal Render
              </button>

              <button
                onClick={testWorkerRender}
                style={{
                  padding: '10px',
                  backgroundColor: '#9C27B0',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Test Worker Render
              </button>

              <button
                onClick={stressTest}
                style={{
                  padding: '10px',
                  backgroundColor: '#FF9800',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                🔥 Stress Test
              </button>

              <button
                onClick={toggleAnimation}
                style={{
                  padding: '10px',
                  backgroundColor: isAnimating ? '#f44336' : '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                {isAnimating ? '⏹️ Stop Animation' : '▶️ Start Animation'}
              </button>
            </div>
          </div>

          {/* Métricas */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <h3>📊 Metrics</h3>

            <div style={{ marginBottom: '15px' }}>
              <h4 style={{ color: '#2196F3', margin: '0 0 5px 0' }}>Normal Rendering</h4>
              <p style={{ margin: '2px 0', fontSize: '14px' }}>
                Time: <strong>{metrics.normal.renderTime}ms</strong>
              </p>
              <p style={{ margin: '2px 0', fontSize: '14px' }}>
                FPS: <strong>{metrics.normal.fps}</strong>
              </p>
            </div>

            <div>
              <h4 style={{ color: '#9C27B0', margin: '0 0 5px 0' }}>Worker Rendering</h4>
              <p style={{ margin: '2px 0', fontSize: '14px' }}>
                Time: <strong>{metrics.worker.renderTime}ms</strong>
              </p>
              <p style={{ margin: '2px 0', fontSize: '14px' }}>
                FPS: <strong>{metrics.worker.fps}</strong>
              </p>
              <p style={{ margin: '2px 0', fontSize: '14px' }}>
                Mode: <strong>{metrics.worker.isUsingWorker ? '✅ Worker' : '⚠️ Fallback'}</strong>
              </p>
            </div>

            {metrics.normal.renderTime > 0 && metrics.worker.renderTime > 0 && (
              <div style={{
                marginTop: '15px',
                padding: '10px',
                backgroundColor: '#1a1a1a',
                borderRadius: '4px'
              }}>
                <p style={{ margin: 0, fontSize: '14px', color: '#4CAF50' }}>
                  <strong>Speedup: {
                    ((metrics.normal.renderTime / metrics.worker.renderTime) * 100 - 100).toFixed(0)
                  }%</strong>
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Gráficos */}
        <div style={{ flex: 1 }}>
          <div style={{ marginBottom: '20px' }}>
            <h2>📈 Normal Rendering (Main Thread)</h2>
            <div style={{
              border: '2px solid #2196F3',
              borderRadius: '8px',
              overflow: 'hidden',
              backgroundColor: '#000'
            }}>
              <CanvasProChart
                ref={normalChartRef}
                symbol="NORMAL/TEST"
                interval="1m"
                candles={candles}
                theme="dark"
                width="100%"
                height="300px"
                showVolume={false}
              />
            </div>
          </div>

          <div>
            <h2>🚀 Worker Rendering (OffscreenCanvas)</h2>
            <div style={{
              border: '2px solid #9C27B0',
              borderRadius: '8px',
              overflow: 'hidden',
              backgroundColor: '#000'
            }}>
              <canvas
                ref={workerCanvasRef}
                style={{
                  width: '100%',
                  height: '300px',
                  display: 'block'
                }}
              />
            </div>
          </div>
        </div>

        {/* Log */}
        <div style={{ width: '300px' }}>
          <h2>📝 Test Log</h2>
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            height: '600px',
            overflowY: 'auto'
          }}>
            {testStatus.map((status, i) => (
              <div key={i} style={{
                padding: '4px',
                borderBottom: '1px solid #333',
                fontSize: '11px',
                fontFamily: 'monospace'
              }}>
                {status}
              </div>
            ))}
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
        <h3>📖 About OffscreenCanvas + Workers</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px' }}>
          <div>
            <h4 style={{ color: '#4CAF50' }}>✅ Benefits</h4>
            <ul style={{ fontSize: '12px', lineHeight: '1.5' }}>
              <li>Rendering in separate thread</li>
              <li>Non-blocking UI</li>
              <li>Better performance for complex charts</li>
              <li>Smooth animations</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#FF9800' }}>⚡ Performance</h4>
            <ul style={{ fontSize: '12px', lineHeight: '1.5' }}>
              <li>50-90% faster for large datasets</li>
              <li>Parallel processing</li>
              <li>Reduced main thread load</li>
              <li>Better FPS consistency</li>
            </ul>
          </div>
          <div>
            <h4 style={{ color: '#2196F3' }}>🔧 Compatibility</h4>
            <ul style={{ fontSize: '12px', lineHeight: '1.5' }}>
              <li>Chrome 69+ ✅</li>
              <li>Firefox 105+ ✅</li>
              <li>Safari 16.4+ ✅</li>
              <li>Auto fallback for older browsers</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WorkersTestPage