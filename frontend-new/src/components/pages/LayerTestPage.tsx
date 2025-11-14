/**
 * Página de teste para o sistema de layers do CanvasProChart
 */

import React, { useRef, useEffect, useState } from 'react'
import { CanvasProChart } from '../charts/CanvasProChart'

// Dados de teste com candles simulados
const generateTestCandles = (count: number) => {
  const candles = []
  let basePrice = 50000
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    const change = (Math.random() - 0.5) * 1000
    const open = basePrice
    const close = basePrice + change
    const high = Math.max(open, close) + Math.random() * 500
    const low = Math.min(open, close) - Math.random() * 500

    candles.push({
      time: now - (count - i) * 60000, // 1 minuto por candle
      open,
      high,
      low,
      close,
      volume: Math.random() * 1000000
    })

    basePrice = close
  }

  return candles
}

export const LayerTestPage: React.FC = () => {
  const chartRef = useRef<any>(null)
  const [candles] = useState(() => generateTestCandles(100))
  const [testStatus, setTestStatus] = useState<string[]>([])
  const [layerInfo, setLayerInfo] = useState<any>({})

  // Adicionar status de teste
  const addStatus = (status: string) => {
    setTestStatus(prev => [...prev, `${new Date().toLocaleTimeString()}: ${status}`])
  }

  useEffect(() => {
    addStatus('🚀 Iniciando teste do sistema de layers')

    // Verificar se o gráfico foi montado
    setTimeout(() => {
      if (chartRef.current) {
        addStatus('✅ Ref do gráfico obtida')

        // Testar métodos do gráfico
        try {
          // Adicionar um indicador de teste
          chartRef.current.addIndicator({
            type: 'SMA',
            name: 'SMA 20',
            period: 20,
            color: '#00ff00'
          })
          addStatus('✅ Indicador SMA adicionado')

          // Testar zoom
          chartRef.current.zoomIn()
          addStatus('✅ Zoom in executado')

          setTimeout(() => {
            chartRef.current.zoomOut()
            addStatus('✅ Zoom out executado')
          }, 1000)

        } catch (error) {
          addStatus(`❌ Erro ao testar métodos: ${error}`)
        }
      } else {
        addStatus('⚠️ Ref do gráfico não disponível')
      }
    }, 1000)

    // Verificar elementos DOM das layers
    setTimeout(() => {
      const container = document.querySelector('.chart-layers-container')
      if (container) {
        addStatus(`✅ Container de layers encontrado`)

        const canvases = container.querySelectorAll('canvas')
        addStatus(`📊 ${canvases.length} canvas elements encontrados`)

        // Verificar cada canvas
        canvases.forEach((canvas, index) => {
          const style = window.getComputedStyle(canvas)
          const info = {
            width: canvas.width,
            height: canvas.height,
            zIndex: style.zIndex,
            position: style.position,
            display: style.display
          }

          addStatus(`Canvas ${index}: z-index=${info.zIndex}, ${info.width}x${info.height}`)

          // Verificar se tem conteúdo renderizado
          const ctx = canvas.getContext('2d')
          if (ctx) {
            const imageData = ctx.getImageData(0, 0, 10, 10)
            const hasContent = imageData.data.some(pixel => pixel !== 0)
            addStatus(`Canvas ${index}: ${hasContent ? 'tem conteúdo' : 'vazio'}`)
          }
        })

        setLayerInfo({
          totalCanvases: canvases.length,
          containerFound: true
        })

      } else {
        addStatus('❌ Container de layers NÃO encontrado')
        setLayerInfo({
          totalCanvases: 0,
          containerFound: false
        })
      }
    }, 2000)

  }, [])

  return (
    <div style={{ padding: '20px', backgroundColor: '#1a1a1a', color: '#fff', minHeight: '100vh' }}>
      <h1>🧪 Teste do Sistema de Layers - CanvasProChart</h1>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Gráfico */}
        <div style={{ flex: 1 }}>
          <h2>Gráfico com Layers</h2>
          <div style={{ border: '2px solid #444', borderRadius: '8px', overflow: 'hidden' }}>
            <CanvasProChart
              ref={chartRef}
              symbol="BTCUSDT"
              interval="1m"
              candles={candles}
              theme="dark"
              width="100%"
              height="500px"
              stopLoss={48000}
              takeProfit={52000}
            />
          </div>
        </div>

        {/* Painel de Status */}
        <div style={{ width: '400px' }}>
          <h2>Status do Teste</h2>

          {/* Info das Layers */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '10px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <h3>📊 Informações das Layers</h3>
            <p>Container encontrado: {layerInfo.containerFound ? '✅' : '❌'}</p>
            <p>Total de Canvas: {layerInfo.totalCanvases || 0}</p>
            <p>Esperado: 5 layers (Background, Main, Indicators, Overlays, Interaction)</p>
          </div>

          {/* Log de Status */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '10px',
            borderRadius: '8px',
            height: '400px',
            overflowY: 'auto'
          }}>
            <h3>📝 Log de Execução</h3>
            {testStatus.map((status, i) => (
              <div key={i} style={{
                padding: '4px',
                borderBottom: '1px solid #333',
                fontSize: '12px',
                fontFamily: 'monospace'
              }}>
                {status}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Botões de Teste */}
      <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
        <button
          onClick={() => {
            chartRef.current?.zoomIn()
            addStatus('🔍 Zoom in executado via botão')
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Zoom In
        </button>

        <button
          onClick={() => {
            chartRef.current?.zoomOut()
            addStatus('🔍 Zoom out executado via botão')
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Zoom Out
        </button>

        <button
          onClick={() => {
            chartRef.current?.resetZoom()
            addStatus('🔄 Reset zoom executado via botão')
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#FF9800',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Reset Zoom
        </button>

        <button
          onClick={() => {
            const indicatorId = `IND-${Date.now()}`
            chartRef.current?.addIndicator({
              id: indicatorId,
              type: 'BB',
              name: 'Bollinger Bands',
              period: 20,
              color: '#ff00ff'
            })
            addStatus(`📈 Indicador BB adicionado: ${indicatorId}`)
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#9C27B0',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Add Bollinger Bands
        </button>

        <button
          onClick={() => {
            // Verificar layers novamente
            const container = document.querySelector('.chart-layers-container')
            if (container) {
              const canvases = container.querySelectorAll('canvas')
              addStatus(`🔍 Re-verificação: ${canvases.length} canvas encontrados`)

              // Verificar conteúdo de cada canvas
              canvases.forEach((canvas, index) => {
                const ctx = canvas.getContext('2d')
                if (ctx) {
                  const imageData = ctx.getImageData(
                    canvas.width / 2,
                    canvas.height / 2,
                    1,
                    1
                  )
                  const pixel = imageData.data
                  addStatus(`Canvas ${index}: RGBA(${pixel[0]}, ${pixel[1]}, ${pixel[2]}, ${pixel[3]})`)
                }
              })
            }
          }}
          style={{
            padding: '10px 20px',
            backgroundColor: '#607D8B',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Verificar Layers
        </button>
      </div>
    </div>
  )
}

export default LayerTestPage