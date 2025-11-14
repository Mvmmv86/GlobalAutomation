/**
 * Página de teste para o sistema de painéis com RSI e MACD
 */

import React, { useRef, useEffect, useState } from 'react'
import { CanvasProChart } from '../charts/CanvasProChart'

// Dados de teste com candles simulados mais realistas
const generateTestCandles = (count: number) => {
  const candles = []
  let basePrice = 50000
  const now = Date.now()

  for (let i = 0; i < count; i++) {
    // Simular tendências
    const trend = Math.sin(i / 20) * 2000
    const noise = (Math.random() - 0.5) * 500
    const change = trend + noise

    const open = basePrice
    const close = basePrice + change
    const high = Math.max(open, close) + Math.random() * 300
    const low = Math.min(open, close) - Math.random() * 300

    candles.push({
      time: now - (count - i) * 60000, // 1 minuto por candle
      open,
      high,
      low,
      close,
      volume: Math.random() * 1000000 + 500000
    })

    basePrice = close
  }

  return candles
}

export const PanelTestPage: React.FC = () => {
  const chartRef = useRef<any>(null)
  const [candles] = useState(() => generateTestCandles(200))
  const [testStatus, setTestStatus] = useState<string[]>([])
  const [panels, setPanels] = useState<any[]>([])

  // Adicionar status de teste
  const addStatus = (status: string) => {
    setTestStatus(prev => [...prev, `${new Date().toLocaleTimeString()}: ${status}`])
  }

  useEffect(() => {
    addStatus('🚀 Iniciando teste do sistema de painéis')
    addStatus('📊 200 candles simulados carregados')

    // Aguardar montagem do gráfico
    setTimeout(() => {
      if (chartRef.current) {
        addStatus('✅ Ref do gráfico obtida')
        addStatus('📈 Adicionando indicadores em painéis separados...')
      } else {
        addStatus('⚠️ Ref do gráfico não disponível')
      }
    }, 1000)
  }, [])

  // Adicionar RSI
  const addRSI = () => {
    if (!chartRef.current) {
      addStatus('❌ Gráfico não está pronto')
      return
    }

    const rsiConfig = {
      id: `RSI-${Date.now()}`,
      type: 'RSI',
      name: 'RSI (14)',
      enabled: true,
      separate: true, // Painel separado
      params: {
        period: 14
      },
      style: {
        color: '#FF6B6B',
        lineWidth: 2
      }
    }

    chartRef.current.addIndicator(rsiConfig)
    setPanels(prev => [...prev, rsiConfig])
    addStatus(`✅ RSI adicionado em painel separado`)
  }

  // Adicionar MACD
  const addMACD = () => {
    if (!chartRef.current) {
      addStatus('❌ Gráfico não está pronto')
      return
    }

    const macdConfig = {
      id: `MACD-${Date.now()}`,
      type: 'MACD',
      name: 'MACD (12,26,9)',
      enabled: true,
      separate: true, // Painel separado
      params: {
        fastPeriod: 12,
        slowPeriod: 26,
        signalPeriod: 9
      },
      style: {
        color: '#4ECDC4',
        lineWidth: 2
      }
    }

    chartRef.current.addIndicator(macdConfig)
    setPanels(prev => [...prev, macdConfig])
    addStatus(`✅ MACD adicionado em painel separado`)
  }

  // Adicionar indicadores overlay (no gráfico principal)
  const addOverlayIndicators = () => {
    if (!chartRef.current) {
      addStatus('❌ Gráfico não está pronto')
      return
    }

    // SMA 20
    chartRef.current.addIndicator({
      id: `SMA20-${Date.now()}`,
      type: 'SMA',
      name: 'SMA 20',
      enabled: true,
      separate: false, // No gráfico principal
      params: {
        period: 20
      },
      style: {
        color: '#00ff00',
        lineWidth: 2
      }
    })

    // Bollinger Bands
    chartRef.current.addIndicator({
      id: `BB-${Date.now()}`,
      type: 'BB',
      name: 'Bollinger Bands',
      enabled: true,
      separate: false, // No gráfico principal
      params: {
        period: 20,
        stdDev: 2
      },
      style: {
        color: '#ff00ff',
        lineWidth: 1.5
      }
    })

    addStatus('✅ SMA e Bollinger Bands adicionados ao gráfico principal')
  }

  // Testar zoom sincronizado
  const testZoomSync = () => {
    addStatus('🔍 Testando sincronização de zoom...')

    // Zoom in
    chartRef.current?.zoomIn()
    addStatus('➕ Zoom in executado')

    setTimeout(() => {
      // Zoom out
      chartRef.current?.zoomOut()
      addStatus('➖ Zoom out executado')

      setTimeout(() => {
        // Reset
        chartRef.current?.resetZoom()
        addStatus('🔄 Reset zoom executado')
        addStatus('✅ Teste de zoom sincronizado completo!')
      }, 1000)
    }, 1000)
  }

  // Limpar todos os painéis
  const clearPanels = () => {
    chartRef.current?.clearIndicators()
    setPanels([])
    addStatus('🧹 Todos os painéis e indicadores removidos')
  }

  return (
    <div style={{ padding: '20px', backgroundColor: '#1a1a1a', color: '#fff', minHeight: '100vh' }}>
      <h1>🧪 Teste do Sistema de Painéis - RSI e MACD</h1>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* Gráfico */}
        <div style={{ flex: 1 }}>
          <h2>Gráfico Multi-Painel</h2>

          {/* Controles */}
          <div style={{ marginBottom: '10px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button
              onClick={addRSI}
              style={{
                padding: '10px 20px',
                backgroundColor: '#FF6B6B',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Adicionar RSI
            </button>

            <button
              onClick={addMACD}
              style={{
                padding: '10px 20px',
                backgroundColor: '#4ECDC4',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Adicionar MACD
            </button>

            <button
              onClick={addOverlayIndicators}
              style={{
                padding: '10px 20px',
                backgroundColor: '#95E77E',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Add SMA + BB
            </button>

            <button
              onClick={testZoomSync}
              style={{
                padding: '10px 20px',
                backgroundColor: '#FFE66D',
                color: '#333',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Testar Zoom Sync
            </button>

            <button
              onClick={() => {
                chartRef.current?.zoomIn()
                addStatus('🔍+ Zoom in')
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
                addStatus('🔍- Zoom out')
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
                addStatus('🔄 Reset zoom')
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
              onClick={clearPanels}
              style={{
                padding: '10px 20px',
                backgroundColor: '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Limpar Tudo
            </button>
          </div>

          {/* Gráfico com altura dinâmica para acomodar painéis */}
          <div style={{
            border: '2px solid #444',
            borderRadius: '8px',
            overflow: 'hidden',
            backgroundColor: '#000'
          }}>
            <CanvasProChart
              ref={chartRef}
              symbol="BTCUSDT"
              interval="1m"
              candles={candles}
              theme="dark"
              width="100%"
              height={panels.length > 0 ? "700px" : "500px"}
            />
          </div>
        </div>

        {/* Painel de Status */}
        <div style={{ width: '400px' }}>
          <h2>Status do Teste</h2>

          {/* Painéis Ativos */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <h3>📊 Painéis Ativos</h3>
            {panels.length === 0 ? (
              <p style={{ color: '#999' }}>Nenhum painel ativo</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {panels.map((panel, i) => (
                  <li key={panel.id} style={{
                    padding: '8px',
                    marginBottom: '5px',
                    backgroundColor: '#333',
                    borderRadius: '4px',
                    borderLeft: `4px solid ${panel.style.color}`
                  }}>
                    <strong>{panel.name}</strong>
                    <br />
                    <small style={{ color: '#999' }}>
                      ID: {panel.id}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Informações do Sistema */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            marginBottom: '20px'
          }}>
            <h3>ℹ️ Informações</h3>
            <p><strong>Total de Candles:</strong> {candles.length}</p>
            <p><strong>Painéis Separados:</strong> {panels.filter(p => p.separate).length}</p>
            <p><strong>Indicadores Overlay:</strong> {panels.filter(p => !p.separate).length}</p>
            <p><strong>Sincronização:</strong> ✅ Ativa</p>
          </div>

          {/* Log de Execução */}
          <div style={{
            backgroundColor: '#2a2a2a',
            padding: '15px',
            borderRadius: '8px',
            height: '300px',
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

      {/* Instruções */}
      <div style={{
        marginTop: '30px',
        padding: '20px',
        backgroundColor: '#2a2a2a',
        borderRadius: '8px'
      }}>
        <h3>📖 Instruções de Teste</h3>
        <ol style={{ lineHeight: '1.8' }}>
          <li><strong>Adicionar RSI:</strong> Cria um painel separado com o indicador RSI (14)</li>
          <li><strong>Adicionar MACD:</strong> Cria outro painel com MACD (12,26,9)</li>
          <li><strong>Testar Zoom Sync:</strong> Verifica se o zoom é sincronizado entre todos os painéis</li>
          <li><strong>Observar:</strong> Os painéis devem manter alinhamento temporal ao fazer zoom/pan</li>
          <li><strong>Verificar:</strong> Cada painel tem sua própria escala Y mas compartilha o eixo X</li>
        </ol>

        <h4>✅ O que verificar:</h4>
        <ul>
          <li>RSI deve variar entre 0-100 com linhas em 30/70</li>
          <li>MACD deve mostrar 3 linhas: MACD, Signal e Histogram</li>
          <li>Zoom deve afetar todos os painéis simultaneamente</li>
          <li>Pan (arrastar) deve mover todos os painéis juntos</li>
          <li>Cada painel deve ter altura ajustável (se implementado drag)</li>
        </ul>
      </div>
    </div>
  )
}

export default PanelTestPage