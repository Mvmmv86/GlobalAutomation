import React, { useEffect, useRef, useState, useMemo } from 'react'
import { Maximize2, Minimize2, Settings, TrendingUp, Sun, Moon, BarChart3, Zap } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { PriceDisplay } from '../molecules/PriceDisplay'
import { SymbolSelector } from '../molecules/SymbolSelector'
// ✅ CUSTOMCHART TEMPORARIAMENTE REATIVADO PARA DEBUG
// import { TradingViewWidget } from '../atoms/TradingViewWidget'
// import { TradingViewFallback } from '../atoms/TradingViewFallback'
// import { SimpleChart } from '../atoms/SimpleChart'
import { CustomChart } from '../atoms/CustomChart'
import { CanvasProChart, CanvasProChartHandle } from '../charts/CanvasProChart'
import { CanvasProChartMinimal } from '../charts/CanvasProChart/CanvasProChartMinimal'
import { IndicatorPanel } from '../charts/CanvasProChart/components/IndicatorPanel'
import { AnyIndicatorConfig, IndicatorType, INDICATOR_PRESETS } from '../charts/CanvasProChart/indicators/types'
import { useChartPositions } from '@/hooks/useChartPositions'
import { useCandles } from '@/hooks/useCandles'
import { usePositionOrders } from '@/hooks/usePositionOrders'
import { cn } from '@/lib/utils'
import { updatePositionSLTP } from '@/lib/api'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'

interface ChartContainerProps {
  symbol: string
  interval?: string
  theme?: 'light' | 'dark'
  height?: number | string
  onSymbolChange?: (symbol: string) => void
  className?: string
  exchangeAccountId?: string
  onPositionAction?: (positionId: string, action: 'close' | 'modify', data?: any) => void
  onChartClick?: (price: number) => void
  onPositionClose?: (positionId: string) => void
  onPositionEdit?: (positionId: string) => void
}

const ChartContainer: React.FC<ChartContainerProps> = ({
  symbol,
  interval: propInterval = '1h',
  theme = 'dark',
  height = 500,
  onSymbolChange,
  className,
  exchangeAccountId,
  onPositionAction,
  onChartClick,
  onPositionClose,
  onPositionEdit
}) => {
  const queryClient = useQueryClient()
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasProChartRef = useRef<CanvasProChartHandle>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isLoading, setIsLoading] = useState(false) // ✅ Iniciar com false para carregamento automático
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [priceChange, setPriceChange] = useState<number>(0)

  // ✅ Recuperar timeframe salvo do localStorage
  const [selectedInterval, setSelectedInterval] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('trading-timeframe')
      return saved || '60' // Default para 1h = 60 minutos
    }
    return '60'
  })

  // 🧪 FASE 1: CanvasProMinimal ATIVO por padrão para teste
  const [useCanvasProMinimal, setUseCanvasProMinimal] = useState(true)

  // const [retryCount, setRetryCount] = useState(0) // ❌ REMOVIDO - não precisa mais

  // ✅ Recuperar tema salvo do localStorage
  const [chartTheme, setChartTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('trading-theme')
      return (saved as 'light' | 'dark') || 'dark'
    }
    return 'dark'
  })

  const [chartKey, setChartKey] = useState(0) // Voltar para 0 para abordagem mais simples

  const [showIndicators, setShowIndicators] = useState(false)

  // ✅ NOVO: Estado para controlar indicadores do sistema profissional (30+)
  const [canvasIndicators, setCanvasIndicators] = useState<AnyIndicatorConfig[]>([])

  // Buscar posições do símbolo atual
  const {
    positions: chartPositions,
    isLoading: isLoadingPositions,
    error: positionsError
  } = useChartPositions({
    symbol,
    exchangeAccountId
  })

  // ✅ Buscar dados de candles usando hook simples (CanvasProChart tem seu próprio RealtimeManager)
  const { data: candleData } = useCandles(symbol, selectedInterval)

  // 🔥 NOVO: Buscar ordens de SL/TP para CanvasChart
  const { data: ordersData } = usePositionOrders(exchangeAccountId || '', symbol)

  // 🚨 DEBUG: Verificar estado do componente
  console.log('🔴 ChartContainer RENDERIZADO:', {
    useCanvasProMinimal,
    symbol,
    selectedInterval,
    chartTheme,
    chartPositionsLength: chartPositions?.length || 0,
    candlesCount: candleData?.candles?.length || 0
  })

  // ✅ Salvar configurações no localStorage quando mudarem
  // Handlers para gerenciar indicadores
  const handleAddIndicator = (type: IndicatorType) => {
    if (!canvasProChartRef.current) return

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

    canvasProChartRef.current.addIndicator(config)
    setCanvasIndicators(prev => [...prev, config])
    toast.success(`${type} adicionado ao gráfico`)
  }

  const handleRemoveIndicator = (id: string) => {
    if (!canvasProChartRef.current) return

    canvasProChartRef.current.removeIndicator(id)
    setCanvasIndicators(prev => prev.filter(ind => ind.id !== id))
    toast.info('Indicador removido')
  }

  const handleToggleIndicator = (id: string, enabled: boolean) => {
    if (!canvasProChartRef.current) return

    canvasProChartRef.current.updateIndicator(id, { enabled })
    setCanvasIndicators(prev => prev.map(ind =>
      ind.id === id ? { ...ind, enabled } : ind
    ))
  }

  useEffect(() => {
    localStorage.setItem('trading-timeframe', selectedInterval)
  }, [selectedInterval])

  useEffect(() => {
    localStorage.setItem('trading-theme', chartTheme)
  }, [chartTheme])

  // Mock data for price display - In real implementation, this would come from TradingView widget
  useEffect(() => {
    // ✅ Não definir loading como true automaticamente - deixar o widget carregar
    // Mock price data - em produção viria do TradingView
    setCurrentPrice(45234.56)
    setPriceChange(1.23)
  }, [symbol])

  const handleChartReady = () => {
    console.log('📈 Chart ready for', symbol, 'interval:', selectedInterval)
    setIsLoading(false)
  }

  // ✅ Carregamento automático imediato na montagem
  useEffect(() => {
    console.log('🚀 ChartContainer: MONTADO - Iniciando carregamento automático')
    console.log('📊 Configurações:', { symbol, selectedInterval, chartTheme })

    // Limpar localStorage se tem valor inválido
    const saved = localStorage.getItem('trading-timeframe')
    if (saved && !['1', '3', '5', '15', '30', '60', '240', '1D', '1W', '1M'].includes(saved)) {
      console.log('⚠️ Limpando timeframe inválido do localStorage:', saved)
      localStorage.removeItem('trading-timeframe')
      setSelectedInterval('60') // Reset para 1h
    }

    // NÃO incrementar chartKey na montagem - deixar o widget montar naturalmente
    // setChartKey(1) // ❌ REMOVIDO - causa re-render e loading infinito

    // Timeout de segurança para parar loading se demorar muito
    const fallbackTimer = setTimeout(() => {
      console.log('⚠️ Timeout de segurança: Forçando parar loading após 5 segundos')
      setIsLoading(false)
    }, 5000) // 5 segundos máximo

    return () => clearTimeout(fallbackTimer)
  }, []) // SOMENTE na montagem inicial

  // Removido timeout duplicado - já existe um timeout no useEffect inicial

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  // ❌ REMOVIDO - Apenas Canvas PRO disponível
  // const switchChartMode = () => {
  //   setChartMode('canvas')
  //   setRetryCount(retryCount + 1)
  // }

  // Fechar menu de indicadores ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (showIndicators && !target.closest('.indicators-menu')) {
        setShowIndicators(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showIndicators])


  // ❌ REMOVIDO - getChartModeLabel não é mais necessário (apenas CanvasProChart)

  // Intervalos completos - memoizados para evitar re-renders
  const intervals = useMemo(() => [
    { label: '1m', value: '1' },
    { label: '3m', value: '3' },
    { label: '5m', value: '5' },
    { label: '10m', value: '10' },  // ✅ NOVO: 10 minutos
    { label: '15m', value: '15' },
    { label: '30m', value: '30' },
    { label: '1h', value: '60' },
    { label: '2h', value: '120' },  // ✅ NOVO: 2 horas
    { label: '4h', value: '240' },
    { label: '1d', value: '1D' },
    { label: '3d', value: '3D' },   // ✅ NOVO: 3 dias
    { label: '1w', value: '1W' },
    { label: '1M', value: '1M' }
  ], [])

  return (
    <div className={cn("w-full h-full flex flex-col", className)}>
      <div className="px-2 py-1 border-b bg-background/95">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-4 w-4" />
            <span className="text-sm font-semibold">Gráfico</span>

            {/* Symbol Selector */}
            <SymbolSelector
              selectedSymbol={symbol}
              onSymbolChange={(newSymbol) => {
                console.log('📊 Symbol changing from', symbol, 'to', newSymbol)
                if (onSymbolChange) {
                  onSymbolChange(newSymbol)
                }
              }}
            />


            {/* Timeframes Funcionais */}
            <div className="flex items-center space-x-1 bg-accent/10 rounded-md px-2 py-1">
              <span className="text-xs text-muted-foreground mr-1">Tempo:</span>
              {intervals.slice(0, 6).map((interval) => ( // Mostra só os principais
                <Button
                  key={interval.value}
                  variant={selectedInterval === interval.value ? "default" : "ghost"}
                  size="sm"
                  className={cn(
                    "h-6 px-2 text-xs font-medium min-w-0",
                    selectedInterval === interval.value
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-accent text-muted-foreground"
                  )}
                  onClick={() => {
                    console.log(`🔄 Mudando timeframe de ${selectedInterval} para ${interval.value}`)
                    setSelectedInterval(interval.value)
                    setIsLoading(true) // Mostra loading apenas durante mudança
                    setChartKey(prev => {
                      const newKey = prev + 1
                      console.log(`🔑 ChartKey mudando de ${prev} para ${newKey}`)
                      return newKey
                    }) // Força recriação completa do widget
                  }}
                >
                  {interval.label}
                </Button>
              ))}
            </div>

            {!isLoading && (
              <PriceDisplay
                price={currentPrice}
                change={priceChange}
                size="sm"
              />
            )}
          </div>

          <div className="flex items-center space-x-1">
            {/* Chart Controls - Apenas essenciais */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => {
                const newTheme = chartTheme === 'dark' ? 'light' : 'dark'
                console.log(`🎨 Mudando tema de ${chartTheme} para ${newTheme}`)
                setChartTheme(newTheme)
                // Tema agora é aplicado dinamicamente via useEffect no CustomChart
              }}
              title={chartTheme === 'dark' ? 'Tema Claro' : 'Tema Escuro'}
            >
              {chartTheme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>

            {/* Indicadores */}
            <div className="relative indicators-menu">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => {
                  console.log('📊 Toggle Indicadores - Estado atual:', showIndicators, '→ Novo estado:', !showIndicators)
                  setShowIndicators(!showIndicators)
                }}
                title="Indicadores"
              >
                <BarChart3 className="h-4 w-4" />
              </Button>

              {/* PAINEL DE INDICADORES ANTIGO REMOVIDO - USANDO NOVO PAINEL PROFISSIONAL DO CANVASPROCHART */}
            </div>

            {/* 🧪 BOTÃO DE TESTE: Alternar entre CustomChart e CanvasProMinimal */}
            <Button
              variant={useCanvasProMinimal ? "default" : "ghost"}
              size="icon"
              className="h-8 w-8"
              onClick={() => {
                const newValue = !useCanvasProMinimal
                console.log(`🧪 Alternando gráfico: ${useCanvasProMinimal ? 'CanvasProMinimal → CustomChart' : 'CustomChart → CanvasProMinimal'}`)
                setUseCanvasProMinimal(newValue)
                toast.info(newValue ? 'Testando CanvasProMinimal (Passo 1)' : 'Voltando para CustomChart')
              }}
              title={useCanvasProMinimal ? 'Voltar para CustomChart' : 'Testar CanvasProMinimal (Passo 1)'}
            >
              <Zap className="h-4 w-4" />
            </Button>

            {/* ❌ BOTÃO DE TROCA DE GRÁFICO REMOVIDO - Apenas Canvas PRO disponível */}
            {false && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => {}}
              title="Apenas Canvas PRO disponível"
            >
              <Settings className="h-4 w-4" />
            </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={toggleFullscreen}
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

      </div>

      {/* ✅ FIX: Definir altura mínima explícita para o CanvasProChartMinimal */}
      <div className="flex-1 relative" style={{ minHeight: '500px' }}>
        <div className="relative w-full h-full">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm z-10">
              <div className="flex flex-col items-center space-y-4">
                <div className="h-8 w-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <div className="text-sm text-muted-foreground">Carregando gráfico {symbol}...</div>
              </div>
            </div>
          )}

          {/* ========================================
               🧪 TESTE INCREMENTAL: CustomChart OU CanvasProMinimal
               ======================================== */}

          {/* 🧪 PASSO 1: Renderizar CanvasProChartMinimal (canvas vazio) */}
          {useCanvasProMinimal && (
            <>
            {console.log('🧪 RENDERIZANDO CanvasProChartMinimal (Passo 1):', {
              symbol,
              interval: selectedInterval,
              candlesCount: candleData?.candles?.length || 0
            })}
            <CanvasProChartMinimal
              symbol={symbol}
              interval={selectedInterval}
              theme={chartTheme}
              width="100%"
              height="100%"
              candles={candleData?.candles || []}
              className="w-full h-full rounded-b-lg overflow-hidden"
            />
            </>
          )}

          {/* ✅ CustomChart (fallback seguro) */}
          {!useCanvasProMinimal && (
            <>
            {console.log('🟢 RENDERIZANDO CustomChart com props:', {
              symbol,
              interval: selectedInterval,
              chartPositions,
              chartPositionsLength: chartPositions?.length || 0
            })}
            <CustomChart
              key={`custom-${chartKey}-${symbol}-${selectedInterval}`}
              symbol={symbol}
              interval={selectedInterval}
              theme={chartTheme}
              width="100%"
              height="100%"
              positions={chartPositions}
              onReady={handleChartReady}
              className="w-full h-full rounded-b-lg overflow-hidden"
              indicators={[]}
              onChartClick={onChartClick}
              onPositionClose={onPositionClose}
              onPositionEdit={onPositionEdit}
              onSLTPDrag={async (positionId, type, newPrice) => {
                console.log(`🎯 Linha ${type} arrastada para $${newPrice.toFixed(2)} - posição ${positionId}`)

                const queryKey = ['position-orders', exchangeAccountId, symbol]

                try {
                  // ✅ OPTIMISTIC UPDATE: Atualizar UI ANTES da API call
                  await queryClient.cancelQueries({ queryKey })

                  // Salvar estado anterior para rollback
                  const previousData = queryClient.getQueryData(queryKey)

                  // Atualizar cache INSTANTANEAMENTE
                  queryClient.setQueryData(queryKey, (oldData: any) => {
                    if (!oldData) return oldData

                    return {
                      ...oldData,
                      [type === 'stopLoss' ? 'stopLoss' : 'takeProfit']: newPrice
                    }
                  })

                  console.log(`📝 UI atualizada otimisticamente: ${type} -> $${newPrice}`)

                  // Mostrar feedback visual
                  toast.loading(`Atualizando ${type === 'stopLoss' ? 'Stop Loss' : 'Take Profit'}...`, {
                    id: `sltp-update-${positionId}`
                  })

                  // Chamar API de forma assíncrona (não bloqueia UI)
                  const result = await updatePositionSLTP(positionId, type, newPrice)

                  // Sucesso! Atualizar com preço confirmado do backend
                  queryClient.setQueryData(queryKey, (oldData: any) => {
                    if (!oldData) return oldData

                    return {
                      ...oldData,
                      [type === 'stopLoss' ? 'stopLoss' : 'takeProfit']: result.new_price
                    }
                  })

                  // ✅ CRITICAL: Invalidar cache para forçar refetch imediato dos dados atualizados
                  await queryClient.invalidateQueries({ queryKey })
                  await queryClient.invalidateQueries({ queryKey: ['positions'] }) // Invalida cache de posições também

                  toast.success(result.message, {
                    id: `sltp-update-${positionId}`,
                    description: `Nova ordem criada: ${result.order_id}`
                  })

                  console.log('✅ SL/TP confirmado pelo backend:', result)

                  // ✅ REMOVIDO: onPositionAction causava chamada duplicada PUT /modify que falhava
                  // Agora usamos apenas optimistic update + PATCH /sltp
                  // if (onPositionAction) {
                  //   onPositionAction(positionId, 'modify', {
                  //     [type === 'stopLoss' ? 'stopLoss' : 'takeProfit']: result.new_price
                  //   })
                  // }

                } catch (error: any) {
                  console.error('❌ Erro ao atualizar SL/TP:', error)

                  // ✅ ROLLBACK: Reverter para estado anterior em caso de erro
                  const previousData = queryClient.getQueryData(queryKey)
                  queryClient.setQueryData(queryKey, previousData)

                  toast.error('Erro ao atualizar ordem', {
                    id: `sltp-update-${positionId}`,
                    description: error.response?.data?.detail || error.message || 'Erro desconhecido'
                  })

                  console.log('🔙 Rollback: linha revertida para posição anterior')
                }
              }}
            />
            </>
          )}

          {/* ❌❌❌ TRADINGVIEW REMOVIDO COMPLETAMENTE - APENAS CANVASPROCHART ❌❌❌ */}
          {false && (
            <>
            {/* Removido console.log para evitar re-renders */}
            <TradingViewWidget
              key={`tv-${chartKey}-${symbol}-${selectedInterval}`}
              symbol={symbol}
              interval={selectedInterval}
              theme={chartTheme}
              width="100%"
              height={height}
              onReady={handleChartReady}
              className="rounded-b-lg overflow-hidden"
              positions={chartPositions}
              onPositionAction={onPositionAction}
            />
            </>
          )}

          {/* ❌❌❌ TRADINGVIEW FALLBACK REMOVIDO - APENAS CANVASPROCHART ❌❌❌ */}
          {false && (
            <>
            {/* Removido console.log para evitar re-renders */}
            <div
              className="w-full h-full"
              style={{
                filter: chartTheme === 'light' ? 'invert(1) hue-rotate(180deg)' : 'none',
                transition: 'filter 0.3s ease'
              }}
            >
              <TradingViewFallback
                key={`${symbol}-${chartKey}`}
                symbol={symbol}
                theme="dark"
                width="100%"
                height="100%"
                className="w-full h-full"
              />
            </div>
            </>
          )}

          {/* ❌❌❌ SIMPLE CHART REMOVIDO - APENAS CANVASPROCHART ❌❌❌ */}
          {false && (
            <SimpleChart
              symbol={symbol}
              width="100%"
              height="100%"
              className="w-full h-full"
            />
          )}
        </div>

      </div>
    </div>
  )
}

export { ChartContainer }
export type { ChartContainerProps }