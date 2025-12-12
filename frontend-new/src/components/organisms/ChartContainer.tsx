import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import {
  Maximize2, Minimize2, TrendingUp, Sun, Moon, BarChart3, X, ChevronDown, Settings
} from 'lucide-react'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { SymbolSelector } from '../molecules/SymbolSelector'
import { SeparateIndicatorPanels } from '../molecules/SeparateIndicatorPanels'
import { IndicatorSettingsModal } from '../molecules/IndicatorSettingsModal'
import { CustomChart } from '../atoms/CustomChart'
import type { Candle } from '@/utils/indicators'
import { useChartPositions } from '@/hooks/useChartPositions'
import { useCandles } from '@/hooks/useCandles'
import { usePositionOrders } from '@/hooks/usePositionOrders'
import { cn } from '@/lib/utils'
import { updatePositionSLTP, createPositionSLTP, cancelPositionSLTP } from '@/lib/api'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import {
  IndicatorType,
  AnyIndicatorConfig,
  INDICATOR_CATEGORIES,
  INDICATOR_NAMES,
  INDICATOR_PRESETS,
  createIndicatorConfig
} from '@/utils/indicators'

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

// Helper function para fazer merge de indicadores salvos com defaults atuais
// Isso garante que novos params adicionados ao código apareçam nos indicadores salvos
const mergeIndicatorsWithDefaults = (savedIndicators: AnyIndicatorConfig[]): AnyIndicatorConfig[] => {
  return savedIndicators.map(ind => {
    const preset = INDICATOR_PRESETS[ind.type]
    if (!preset) return ind

    // Merge: defaults primeiro, depois params salvos (sobrescrevem)
    return {
      ...ind,
      params: {
        ...preset.params,  // Defaults atuais (incluindo novos params)
        ...ind.params      // Params salvos (sobrescrevem os defaults)
      }
    }
  })
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
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
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

  // ✅ Estado para controlar indicadores ativos - carrega do localStorage por símbolo
  // 🔥 FIX: Faz merge com defaults atuais para garantir que novos params apareçam
  const [activeIndicators, setActiveIndicators] = useState<AnyIndicatorConfig[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem(`indicators-${symbol}`)
        if (saved) {
          const parsed = JSON.parse(saved)
          const merged = mergeIndicatorsWithDefaults(parsed)
          console.log(`📊 Carregando indicadores salvos para ${symbol}:`, parsed)
          console.log(`📊 Após merge com defaults:`, merged)
          return merged
        }
      } catch (e) {
        console.warn('Erro ao carregar indicadores do localStorage:', e)
      }
    }
    return []
  })
  const [showIndicatorDropdown, setShowIndicatorDropdown] = useState(false)

  // ✅ NOVO: Estado para ferramentas de desenho
  const [activeDrawingTool, setActiveDrawingTool] = useState<string | null>(null)
  const [showAlerts, setShowAlerts] = useState(false)

  // ✅ NOVO: Estado para modal de configurações de indicador
  const [settingsModalIndicator, setSettingsModalIndicator] = useState<AnyIndicatorConfig | null>(null)
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false)

  // Handlers para indicadores
  const handleAddIndicator = useCallback((type: IndicatorType) => {
    const newIndicator = createIndicatorConfig(type)
    setActiveIndicators(prev => {
      // Verificar se já existe
      if (prev.some(ind => ind.type === type)) {
        toast.info(`${INDICATOR_NAMES[type]} já está ativo`)
        return prev
      }
      toast.success(`${INDICATOR_NAMES[type]} adicionado`)
      return [...prev, newIndicator]
    })
    setShowIndicatorDropdown(false)
  }, [])

  const handleRemoveIndicator = useCallback((id: string) => {
    setActiveIndicators(prev => prev.filter(ind => ind.id !== id))
    toast.info('Indicador removido')
  }, [])

  const handleClearAllIndicators = useCallback(() => {
    setActiveIndicators([])
    toast.info('Todos indicadores removidos')
  }, [])

  // ✅ NOVO: Handler para abrir configurações do indicador
  const handleIndicatorSettings = useCallback((id: string) => {
    const indicator = activeIndicators.find(ind => ind.id === id)
    if (indicator) {
      setSettingsModalIndicator(indicator)
      setIsSettingsModalOpen(true)
    }
  }, [activeIndicators])

  // ✅ NOVO: Handler para salvar configurações do indicador
  const handleSaveIndicatorSettings = useCallback((updatedIndicator: AnyIndicatorConfig) => {
    console.log('🔧 handleSaveIndicatorSettings CHAMADO com:', updatedIndicator)

    // 🔥 FIX: Criar cópia profunda do indicador para garantir que React detecte a mudança
    const indicatorCopy: AnyIndicatorConfig = {
      ...updatedIndicator,
      params: { ...updatedIndicator.params }  // Cópia profunda dos params
    }

    setActiveIndicators(prev => {
      console.log('🔧 Estado anterior:', prev)

      // Criar novo array com cópia profunda de cada item
      const newIndicators = prev.map(ind => {
        if (ind.id === indicatorCopy.id) {
          console.log('🔧 Atualizando indicador:', ind.id, '→', indicatorCopy)
          return indicatorCopy
        }
        return ind
      })

      console.log('🔧 Novo estado:', newIndicators)
      return newIndicators
    })

    // Fechar modal após salvar
    setIsSettingsModalOpen(false)
    setSettingsModalIndicator(null)

    toast.success(`Configurações de ${updatedIndicator.type} aplicadas!`)
  }, [])

  // Converter indicadores ativos para o formato do CustomChart
  const chartIndicators = useMemo(() => {
    const result: Record<string, boolean> = {}

    activeIndicators.forEach(ind => {
      // EMA com diferentes períodos
      if (ind.type === 'EMA') {
        const period = ind.params?.period || 20
        if (period === 9) result.ema9 = true
        else if (period === 20) result.ema20 = true
        else if (period === 50) result.ema50 = true
        else result.ema20 = true // Default
      }
      // SMA com diferentes períodos
      else if (ind.type === 'SMA') {
        const period = ind.params?.period || 20
        if (period === 20) result.sma20 = true
        else if (period === 50) result.sma50 = true
        else if (period === 200) result.sma200 = true
        else result.sma20 = true // Default
      }
      // Bollinger Bands
      else if (ind.type === 'BB') {
        result.bollingerBands = true
      }
    })

    return result
  }, [activeIndicators])

  // Buscar posições do símbolo atual
  const {
    positions: chartPositions,
    isLoading: isLoadingPositions,
    error: positionsError
  } = useChartPositions({
    symbol,
    exchangeAccountId
  })

  // 🔥 NOVO: Buscar ordens de SL/TP para CanvasChart
  const { data: ordersData } = usePositionOrders(exchangeAccountId || '', symbol)

  // Buscar candles para indicadores separados
  const { data: candlesData, isLoading: isCandlesLoading } = useCandles(symbol, selectedInterval)

  // ✅ Salvar configurações no localStorage quando mudarem
  useEffect(() => {
    localStorage.setItem('trading-timeframe', selectedInterval)
  }, [selectedInterval])

  useEffect(() => {
    localStorage.setItem('trading-theme', chartTheme)
  }, [chartTheme])

  // ✅ NOVO: Salvar indicadores no localStorage quando mudarem
  useEffect(() => {
    if (activeIndicators.length > 0) {
      console.log(`💾 Salvando indicadores para ${symbol}:`, activeIndicators)
      localStorage.setItem(`indicators-${symbol}`, JSON.stringify(activeIndicators))
    } else {
      // Se não tem indicadores, remover do localStorage
      localStorage.removeItem(`indicators-${symbol}`)
    }
  }, [activeIndicators, symbol])

  // ✅ NOVO: Carregar indicadores quando o símbolo muda
  // 🔥 FIX: Faz merge com defaults atuais para garantir que novos params apareçam
  useEffect(() => {
    console.log(`🔄 Símbolo mudou para ${symbol}, carregando indicadores salvos...`)
    try {
      const saved = localStorage.getItem(`indicators-${symbol}`)
      if (saved) {
        const parsed = JSON.parse(saved)
        const merged = mergeIndicatorsWithDefaults(parsed)
        console.log(`📊 Indicadores carregados para ${symbol}:`, parsed)
        console.log(`📊 Após merge com defaults:`, merged)
        setActiveIndicators(merged)
      } else {
        console.log(`📊 Nenhum indicador salvo para ${symbol}, limpando lista`)
        setActiveIndicators([])
      }
    } catch (e) {
      console.warn('Erro ao carregar indicadores:', e)
      setActiveIndicators([])
    }
  }, [symbol])

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

    // Limpar localStorage se tem valor inválido (BingX supported: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
    const saved = localStorage.getItem('trading-timeframe')
    if (saved && !['1', '3', '5', '15', '30', '60', '240', '1D', '1W'].includes(saved)) {
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

  // Fechar dropdown de indicadores ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (showIndicatorDropdown && !target.closest('.indicators-dropdown')) {
        setShowIndicatorDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showIndicatorDropdown])

  // Intervalos completos - memoizados para evitar re-renders
  // Todos os intervalos suportados pela Binance API pública
  const intervals = useMemo(() => [
    { label: '1m', value: '1' },
    { label: '3m', value: '3' },
    { label: '5m', value: '5' },
    { label: '15m', value: '15' },
    { label: '30m', value: '30' },
    { label: '1h', value: '60' },
    { label: '2h', value: '120' },
    { label: '4h', value: '240' },
    { label: '6h', value: '360' },
    { label: '8h', value: '480' },
    { label: '12h', value: '720' },
    { label: '1d', value: '1D' },
    { label: '3d', value: '3D' },
    { label: '1w', value: '1W' },
    { label: '1M', value: '1M' }
  ], [])

  return (
    <div className={cn("w-full h-full flex flex-col overflow-hidden", className)}>
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


            {/* Timeframes Funcionais - Duas linhas para caber todos */}
            <div className="flex flex-wrap items-center bg-accent/10 rounded-md px-1 py-0.5 gap-0.5">
              {intervals.map((interval) => (
                <Button
                  key={interval.value}
                  variant={selectedInterval === interval.value ? "default" : "ghost"}
                  size="sm"
                  className={cn(
                    "h-5 px-1 text-[9px] font-medium",
                    selectedInterval === interval.value
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-accent text-muted-foreground"
                  )}
                  onClick={() => {
                    console.log(`🔄 Mudando timeframe de ${selectedInterval} para ${interval.value}`)
                    setSelectedInterval(interval.value)
                    setIsLoading(true)
                    setChartKey(prev => prev + 1)
                  }}
                >
                  {interval.label}
                </Button>
              ))}
            </div>

            {/* 📊 Dropdown de Indicadores Profissional */}
            <div className="relative indicators-dropdown ml-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs gap-1"
                onClick={() => setShowIndicatorDropdown(!showIndicatorDropdown)}
              >
                <BarChart3 className="h-3 w-3" />
                Indicadores
                {activeIndicators.length > 0 && (
                  <Badge variant="secondary" className="h-4 px-1 text-[10px]">
                    {activeIndicators.length}
                  </Badge>
                )}
                <ChevronDown className={cn("h-3 w-3 transition-transform", showIndicatorDropdown && "rotate-180")} />
              </Button>

              {/* Dropdown Menu */}
              {showIndicatorDropdown && (
                <div className="absolute top-full left-0 mt-1 w-64 bg-background border rounded-lg shadow-xl z-50 max-h-80 overflow-y-auto">
                  <div className="p-2 border-b">
                    <div className="text-xs font-semibold text-muted-foreground mb-1">INDICADORES TÉCNICOS</div>
                    {activeIndicators.length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full h-6 text-xs text-destructive hover:text-destructive"
                        onClick={handleClearAllIndicators}
                      >
                        Limpar todos ({activeIndicators.length})
                      </Button>
                    )}
                  </div>

                  {/* Categorias de Indicadores */}
                  {Object.entries(INDICATOR_CATEGORIES).map(([category, indicators]) => (
                    <div key={category} className="p-2 border-b last:border-b-0">
                      <div className="text-[10px] font-bold text-muted-foreground mb-1 uppercase">{category}</div>
                      <div className="flex flex-wrap gap-1">
                        {indicators.map((type) => {
                          const isActive = activeIndicators.some(ind => ind.type === type)
                          const preset = INDICATOR_PRESETS[type]
                          return (
                            <button
                              key={type}
                              onClick={() => isActive
                                ? handleRemoveIndicator(activeIndicators.find(ind => ind.type === type)?.id || '')
                                : handleAddIndicator(type)
                              }
                              className={cn(
                                "px-2 py-0.5 text-[10px] rounded transition-colors",
                                isActive
                                  ? "text-white"
                                  : "bg-accent/50 hover:bg-accent text-foreground"
                              )}
                              style={isActive ? { backgroundColor: preset.color } : undefined}
                              title={INDICATOR_NAMES[type]}
                            >
                              {type}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Badges dos indicadores ativos */}
            {activeIndicators.length > 0 && (
              <div className="flex items-center gap-1 ml-1">
                {activeIndicators.slice(0, 4).map((ind) => (
                  <div
                    key={ind.id}
                    className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] text-white"
                    style={{ backgroundColor: ind.color }}
                  >
                    {ind.type}
                    {/* Botão de configuração */}
                    <button
                      onClick={() => handleIndicatorSettings(ind.id)}
                      className="hover:bg-white/20 rounded-full p-0.5"
                      title="Configurar indicador"
                    >
                      <Settings className="h-2 w-2" />
                    </button>
                    {/* Botão de remover */}
                    <button
                      onClick={() => handleRemoveIndicator(ind.id)}
                      className="hover:bg-white/20 rounded-full p-0.5"
                      title="Remover indicador"
                    >
                      <X className="h-2 w-2" />
                    </button>
                  </div>
                ))}
                {activeIndicators.length > 4 && (
                  <span className="text-[9px] text-muted-foreground">+{activeIndicators.length - 4}</span>
                )}
              </div>
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

            </div>

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

      {/* ✅ FIX: Container do gráfico com flex-1 e overflow-hidden para conter o gráfico dentro do espaço disponível */}
      <div className="flex-1 relative min-h-0 overflow-hidden">
        <div className="relative w-full h-full">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm z-10">
              <div className="flex flex-col items-center space-y-4">
                <div className="h-8 w-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <div className="text-sm text-muted-foreground">Carregando gráfico {symbol}...</div>
              </div>
            </div>
          )}

          {/* CustomChart - Gráfico principal */}
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
              indicators={activeIndicators}
              onChartClick={onChartClick}
              onPositionClose={onPositionClose}
              onPositionEdit={onPositionEdit}
              onIndicatorClick={handleIndicatorSettings}
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

                } catch (error: any) {
                  console.error('Erro ao atualizar SL/TP:', error)

                  // Rollback: Reverter para estado anterior em caso de erro
                  const previousData = queryClient.getQueryData(queryKey)
                  queryClient.setQueryData(queryKey, previousData)

                  toast.error('Erro ao atualizar ordem', {
                    id: `sltp-update-${positionId}`,
                    description: error.response?.data?.detail || error.message || 'Erro desconhecido'
                  })
                }
              }}
              onCreateSLTP={async (positionId, type, price, side) => {
                console.log(`🎯 Criando ${type} para posição ${positionId} @ $${price.toFixed(2)} (${side})`)

                const queryKey = ['position-orders', exchangeAccountId, symbol]

                try {
                  // Mostrar feedback visual
                  toast.loading(`Criando ${type === 'stopLoss' ? 'Stop Loss' : 'Take Profit'}...`, {
                    id: `sltp-create-${positionId}`
                  })

                  // Chamar API para criar SL/TP
                  const result = await createPositionSLTP(positionId, type, price, side)

                  // ✅ Invalidar cache para forçar refetch
                  await queryClient.invalidateQueries({ queryKey })
                  await queryClient.invalidateQueries({ queryKey: ['positions'] })
                  await queryClient.invalidateQueries({ queryKey: ['chart-positions'] })

                  toast.success(`${type === 'stopLoss' ? 'Stop Loss' : 'Take Profit'} criado!`, {
                    id: `sltp-create-${positionId}`,
                    description: `Ordem criada: ${result.order_id} @ $${price.toFixed(2)}`
                  })

                  console.log('✅ SL/TP criado:', result)

                } catch (error: any) {
                  console.error('Erro ao criar SL/TP:', error)

                  toast.error('Erro ao criar ordem', {
                    id: `sltp-create-${positionId}`,
                    description: error.response?.data?.detail || error.message || 'Erro desconhecido'
                  })
                }
              }}
              onCancelOrder={async (positionId, type) => {
                console.log(`❌ Cancelando ${type} para posição ${positionId}`)

                const queryKey = ['position-orders', exchangeAccountId, symbol]

                try {
                  // Mostrar feedback visual
                  toast.loading(`Cancelando ${type === 'stopLoss' ? 'Stop Loss' : 'Take Profit'}...`, {
                    id: `sltp-cancel-${positionId}`
                  })

                  // Chamar API para cancelar SL/TP
                  const result = await cancelPositionSLTP(positionId, type)

                  // ✅ Invalidar cache para forçar refetch
                  await queryClient.invalidateQueries({ queryKey })
                  await queryClient.invalidateQueries({ queryKey: ['positions'] })
                  await queryClient.invalidateQueries({ queryKey: ['chart-positions'] })

                  toast.success(`${type === 'stopLoss' ? 'Stop Loss' : 'Take Profit'} cancelado!`, {
                    id: `sltp-cancel-${positionId}`,
                    description: result.message
                  })

                  console.log('✅ SL/TP cancelado:', result)

                } catch (error: any) {
                  console.error('Erro ao cancelar SL/TP:', error)

                  toast.error('Erro ao cancelar ordem', {
                    id: `sltp-cancel-${positionId}`,
                    description: error.response?.data?.detail || error.message || 'Erro desconhecido'
                  })
                }
              }}
            />
        </div>
      </div>

      {/* Painéis de Indicadores Separados (RSI, MACD, etc.) */}
      {candlesData?.candles && candlesData.candles.length > 0 && (
        <SeparateIndicatorPanels
          indicators={activeIndicators}
          candles={candlesData.candles.map(c => ({
            time: c.time,
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
            volume: c.volume || 0
          }))}
          theme={chartTheme}
          onRemoveIndicator={handleRemoveIndicator}
          onIndicatorSettings={handleIndicatorSettings}
          className="flex-shrink-0"
        />
      )}

      {/* 🔧 Modal de Configurações de Indicador */}
      <IndicatorSettingsModal
        indicator={settingsModalIndicator}
        isOpen={isSettingsModalOpen}
        onClose={() => {
          setIsSettingsModalOpen(false)
          setSettingsModalIndicator(null)
        }}
        onSave={handleSaveIndicatorSettings}
      />
    </div>
  )
}

export { ChartContainer }
export type { ChartContainerProps }