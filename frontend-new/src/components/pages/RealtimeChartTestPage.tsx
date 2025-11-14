/**
 * RealtimeChartTestPage - Página de teste para WebSocket Real-time
 * Demonstra toda a implementação FASE 3 funcionando
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { CanvasProChart } from '../charts/CanvasProChart'
import {
  RealtimeManager,
  RealtimeConfig,
  RealtimeStatus,
  Timeframe
} from '../charts/CanvasProChart/realtime'
import { Candle } from '../charts/CanvasProChart/types'

// Mock de indicadores para teste
const mockIndicators = [
  { type: 'SMA' as const, period: 20, color: '#ff9800' },
  { type: 'EMA' as const, period: 50, color: '#4caf50' },
  { type: 'RSI' as const, period: 14, color: '#2196f3' }
]

export const RealtimeChartTestPage: React.FC = () => {
  const chartRef = useRef<CanvasProChart | null>(null)
  const realtimeManagerRef = useRef<RealtimeManager | null>(null)

  // Estados
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [timeframe, setTimeframe] = useState<Timeframe>('5m')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [status, setStatus] = useState<RealtimeStatus | null>(null)
  const [candles, setCandles] = useState<Candle[]>([])
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Estatísticas
  const [stats, setStats] = useState({
    candleCount: 0,
    wsStatus: 'disconnected' as 'connected' | 'disconnected' | 'error',
    lastPrice: 0,
    priceChange: 0,
    volume24h: 0,
    trades: [] as Array<{ time: number; price: number; quantity: number; side: 'buy' | 'sell' }>
  })

  // Timeframes disponíveis
  const availableTimeframes: Timeframe[] = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

  // Símbolos populares
  const popularSymbols = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
    'XRPUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT'
  ]

  /**
   * Inicializa o RealtimeManager
   */
  const initializeRealtime = useCallback(async () => {
    console.log('🚀 Inicializando RealtimeManager...')
    setIsLoading(true)

    try {
      // Configuração do RealtimeManager
      const config: RealtimeConfig = {
        symbol,
        initialTimeframe: timeframe,
        enabledTimeframes: availableTimeframes,
        testnet: false,
        historicalCandles: 500,
        cacheStrategy: 'hybrid',
        autoReconnect: true,
        reconnectDelay: 3000,

        // Callbacks
        onDataReady: (receivedCandles) => {
          console.log(`📊 Dados prontos: ${receivedCandles.length} candles`)
          setCandles(receivedCandles)
          setLastUpdate(new Date())

          // Atualizar chart se existir
          if (chartRef.current) {
            chartRef.current.updateCandles(receivedCandles)
            if (autoScroll) {
              chartRef.current.scrollToEnd()
            }
          }
        },

        onDataUpdate: (updatedCandles) => {
          console.log(`🔄 Atualização: ${updatedCandles.length} candles`)
          setCandles(updatedCandles)
          setLastUpdate(new Date())

          // Atualizar última cotação
          if (updatedCandles.length > 0) {
            const lastCandle = updatedCandles[updatedCandles.length - 1]
            setStats(prev => ({
              ...prev,
              lastPrice: lastCandle.close,
              priceChange: ((lastCandle.close - lastCandle.open) / lastCandle.open) * 100
            }))
          }

          // Atualizar chart
          if (chartRef.current) {
            chartRef.current.updateCandles(updatedCandles)
            if (autoScroll) {
              chartRef.current.scrollToEnd()
            }
          }
        },

        onTimeframeChange: (from, to) => {
          console.log(`⏰ Timeframe mudou de ${from} para ${to}`)
        },

        onTradeUpdate: (trade) => {
          // Adicionar trade à lista (manter últimos 50)
          setStats(prev => ({
            ...prev,
            trades: [
              {
                time: trade.time,
                price: trade.price,
                quantity: trade.quantity,
                side: trade.isBuyerMaker ? 'sell' : 'buy'
              },
              ...prev.trades.slice(0, 49)
            ]
          }))
        },

        onStatusChange: (newStatus) => {
          console.log('📊 Status:', newStatus)
          setStatus(newStatus)
          setIsConnected(newStatus.isConnected)
          setStats(prev => ({
            ...prev,
            candleCount: newStatus.candleCount,
            wsStatus: newStatus.isConnected ? 'connected' : newStatus.error ? 'error' : 'disconnected'
          }))
        },

        onError: (error) => {
          console.error('❌ Erro:', error)
          alert(`Erro: ${error.message}`)
        }
      }

      // Criar RealtimeManager
      const manager = new RealtimeManager(config)
      realtimeManagerRef.current = manager

      // Inicializar conexão
      await manager.initialize()

      console.log('✅ RealtimeManager inicializado com sucesso!')
      setIsLoading(false)

    } catch (error) {
      console.error('❌ Erro ao inicializar:', error)
      setIsLoading(false)
      alert('Erro ao conectar com Binance WebSocket')
    }
  }, [symbol, timeframe, autoScroll])

  /**
   * Desconecta do WebSocket
   */
  const disconnect = useCallback(() => {
    if (realtimeManagerRef.current) {
      realtimeManagerRef.current.destroy()
      realtimeManagerRef.current = null
      setIsConnected(false)
      setCandles([])
      setStatus(null)
      console.log('🔌 Desconectado')
    }
  }, [])

  /**
   * Muda o timeframe
   */
  const changeTimeframe = useCallback(async (newTimeframe: Timeframe) => {
    if (!realtimeManagerRef.current) return

    console.log(`🔄 Mudando para ${newTimeframe}...`)
    setIsLoading(true)

    try {
      await realtimeManagerRef.current.switchTimeframe(newTimeframe)
      setTimeframe(newTimeframe)
    } catch (error) {
      console.error('Erro ao mudar timeframe:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * Muda o símbolo
   */
  const changeSymbol = useCallback(async (newSymbol: string) => {
    if (!realtimeManagerRef.current) return

    console.log(`🔄 Mudando para ${newSymbol}...`)
    disconnect()
    setSymbol(newSymbol)

    // Aguardar um pouco antes de reconectar
    setTimeout(() => {
      initializeRealtime()
    }, 500)
  }, [disconnect, initializeRealtime])

  /**
   * Carrega mais dados históricos
   */
  const loadMoreHistory = useCallback(async () => {
    if (!realtimeManagerRef.current) return

    console.log('📚 Carregando mais histórico...')
    setIsLoading(true)

    try {
      await realtimeManagerRef.current.loadMoreHistory(500)
    } catch (error) {
      console.error('Erro ao carregar histórico:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * Inicializa o chart quando o componente monta
   */
  useEffect(() => {
    const initChart = async () => {
      const container = document.getElementById('realtime-chart-container')
      if (!container) return

      // Criar chart
      const chart = new CanvasProChart(container, {
        width: container.clientWidth,
        height: 600,
        theme: 'dark',
        indicators: mockIndicators,
        enablePanels: true,
        enableWorkers: true,
        enableOffscreen: true
      })

      chartRef.current = chart
      await chart.initialize()

      console.log('📈 Chart inicializado')
    }

    initChart()

    // Cleanup
    return () => {
      if (chartRef.current) {
        chartRef.current.destroy()
        chartRef.current = null
      }
      if (realtimeManagerRef.current) {
        realtimeManagerRef.current.destroy()
        realtimeManagerRef.current = null
      }
    }
  }, [])

  // Formatação de valores
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: price < 1 ? 6 : 2
    }).format(price)
  }

  const formatVolume = (volume: number) => {
    if (volume > 1e9) return `${(volume / 1e9).toFixed(2)}B`
    if (volume > 1e6) return `${(volume / 1e6).toFixed(2)}M`
    if (volume > 1e3) return `${(volume / 1e3).toFixed(2)}K`
    return volume.toFixed(2)
  }

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-4">
      <div className="max-w-[1920px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">
            🚀 WebSocket Real-time Chart Test
          </h1>
          <p className="text-gray-400">
            FASE 3: Demonstração completa com WebSocket Binance, TimeframeManager e HistoricalLoader
          </p>
        </div>

        {/* Controles */}
        <div className="bg-gray-800 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Símbolo */}
            <div>
              <label className="block text-sm font-medium mb-2">Símbolo</label>
              <select
                value={symbol}
                onChange={(e) => changeSymbol(e.target.value)}
                disabled={isLoading}
                className="w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500"
              >
                {popularSymbols.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Timeframe */}
            <div>
              <label className="block text-sm font-medium mb-2">Timeframe</label>
              <div className="flex gap-1">
                {availableTimeframes.map(tf => (
                  <button
                    key={tf}
                    onClick={() => changeTimeframe(tf)}
                    disabled={isLoading || !isConnected}
                    className={`px-3 py-2 rounded text-sm font-medium transition ${
                      timeframe === tf
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 hover:bg-gray-600'
                    } ${(isLoading || !isConnected) ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </div>

            {/* Conexão */}
            <div>
              <label className="block text-sm font-medium mb-2">Conexão</label>
              <div className="flex gap-2">
                {!isConnected ? (
                  <button
                    onClick={initializeRealtime}
                    disabled={isLoading}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded font-medium disabled:opacity-50"
                  >
                    {isLoading ? 'Conectando...' : 'Conectar'}
                  </button>
                ) : (
                  <button
                    onClick={disconnect}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded font-medium"
                  >
                    Desconectar
                  </button>
                )}

                <button
                  onClick={loadMoreHistory}
                  disabled={!isConnected || isLoading}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded font-medium disabled:opacity-50"
                >
                  + Histórico
                </button>
              </div>
            </div>

            {/* Auto Scroll */}
            <div>
              <label className="block text-sm font-medium mb-2">Opções</label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="w-4 h-4"
                />
                <span>Auto Scroll</span>
              </label>
            </div>
          </div>
        </div>

        {/* Status Bar */}
        <div className="bg-gray-800 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {/* Status WebSocket */}
            <div>
              <div className="text-xs text-gray-400 mb-1">WebSocket</div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  stats.wsStatus === 'connected' ? 'bg-green-500' :
                  stats.wsStatus === 'error' ? 'bg-red-500' : 'bg-gray-500'
                }`} />
                <span className="text-sm font-medium">
                  {stats.wsStatus === 'connected' ? 'Conectado' :
                   stats.wsStatus === 'error' ? 'Erro' : 'Desconectado'}
                </span>
              </div>
            </div>

            {/* Candles */}
            <div>
              <div className="text-xs text-gray-400 mb-1">Candles</div>
              <div className="text-sm font-medium">{stats.candleCount}</div>
            </div>

            {/* Última Cotação */}
            <div>
              <div className="text-xs text-gray-400 mb-1">Última Cotação</div>
              <div className={`text-sm font-medium ${
                stats.priceChange > 0 ? 'text-green-400' :
                stats.priceChange < 0 ? 'text-red-400' : 'text-gray-300'
              }`}>
                {formatPrice(stats.lastPrice)}
              </div>
            </div>

            {/* Variação */}
            <div>
              <div className="text-xs text-gray-400 mb-1">Variação</div>
              <div className={`text-sm font-medium ${
                stats.priceChange > 0 ? 'text-green-400' :
                stats.priceChange < 0 ? 'text-red-400' : 'text-gray-300'
              }`}>
                {stats.priceChange > 0 ? '+' : ''}{stats.priceChange.toFixed(2)}%
              </div>
            </div>

            {/* Última Atualização */}
            <div>
              <div className="text-xs text-gray-400 mb-1">Última Atualização</div>
              <div className="text-sm font-medium">
                {lastUpdate ? lastUpdate.toLocaleTimeString() : '--:--:--'}
              </div>
            </div>

            {/* Estado */}
            <div>
              <div className="text-xs text-gray-400 mb-1">Estado</div>
              <div className="text-sm font-medium">
                {status?.historicalStatus === 'loading' ? 'Carregando...' :
                 status?.historicalStatus === 'loaded' ? 'Pronto' :
                 status?.historicalStatus === 'error' ? 'Erro' : 'Idle'}
              </div>
            </div>
          </div>
        </div>

        {/* Chart Container */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Main Chart */}
          <div className="lg:col-span-3">
            <div className="bg-gray-800 rounded-lg p-4">
              <div id="realtime-chart-container" className="w-full" style={{ height: '600px' }}>
                {!isConnected && (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <div className="text-6xl mb-4">📊</div>
                      <p className="text-xl font-medium mb-2">WebSocket Real-time Chart</p>
                      <p className="text-gray-400 mb-4">Clique em "Conectar" para iniciar</p>
                      <button
                        onClick={initializeRealtime}
                        disabled={isLoading}
                        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium disabled:opacity-50"
                      >
                        {isLoading ? 'Conectando...' : 'Conectar Agora'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Trades em Tempo Real */}
          <div className="lg:col-span-1">
            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-lg font-medium mb-3">Trades em Tempo Real</h3>
              <div className="space-y-1 max-h-[550px] overflow-y-auto">
                {stats.trades.length > 0 ? (
                  stats.trades.map((trade, i) => (
                    <div
                      key={`${trade.time}-${i}`}
                      className={`flex justify-between items-center p-2 rounded ${
                        trade.side === 'buy' ? 'bg-green-900/20' : 'bg-red-900/20'
                      }`}
                    >
                      <div className="flex-1">
                        <div className={`text-sm font-medium ${
                          trade.side === 'buy' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {formatPrice(trade.price)}
                        </div>
                        <div className="text-xs text-gray-400">
                          {formatTime(trade.time)}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm text-gray-300">
                          {trade.quantity.toFixed(4)}
                        </div>
                        <div className={`text-xs ${
                          trade.side === 'buy' ? 'text-green-400' : 'text-red-400'
                        }`}>
                          {trade.side.toUpperCase()}
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center text-gray-400 py-8">
                    <p className="text-sm">Aguardando trades...</p>
                    <p className="text-xs mt-2">
                      {isConnected ? 'Conectado, aguardando dados' : 'Conecte para ver trades'}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Informações Técnicas */}
        {status && (
          <div className="bg-gray-800 rounded-lg p-4 mt-4">
            <h3 className="text-lg font-medium mb-3">🔧 Informações Técnicas</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-400">WebSocket:</span>{' '}
                <span className={status.websocketStatus === 'connected' ? 'text-green-400' : 'text-gray-300'}>
                  {status.websocketStatus}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Histórico:</span>{' '}
                <span className={status.historicalStatus === 'loaded' ? 'text-green-400' : 'text-gray-300'}>
                  {status.historicalStatus}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Timeframe:</span>{' '}
                <span className="text-blue-400">{status.activeTimeframe}</span>
              </div>
              <div>
                <span className="text-gray-400">Candles:</span>{' '}
                <span className="text-yellow-400">{status.candleCount}</span>
              </div>
              {status.error && (
                <div className="col-span-full">
                  <span className="text-gray-400">Erro:</span>{' '}
                  <span className="text-red-400">{status.error}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Features Implementadas */}
        <div className="bg-gray-800 rounded-lg p-4 mt-4">
          <h3 className="text-lg font-medium mb-3">✅ Features Implementadas (FASE 3)</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <h4 className="font-medium text-green-400 mb-2">WebSocketManager</h4>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Conexão real-time Binance</li>
                <li>• Auto-reconnect exponencial</li>
                <li>• Múltiplos streams (kline, trades)</li>
                <li>• Buffer de candles</li>
                <li>• Ping/pong keepalive</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-blue-400 mb-2">TimeframeManager</h4>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Múltiplos timeframes</li>
                <li>• Cache inteligente</li>
                <li>• Agregação de candles</li>
                <li>• IndexedDB persistência</li>
                <li>• Switch sem perda de dados</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-purple-400 mb-2">HistoricalLoader</h4>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Carregamento em batches</li>
                <li>• Rate limiting</li>
                <li>• Cache de requisições</li>
                <li>• Preenchimento de gaps</li>
                <li>• Validação de dados</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}