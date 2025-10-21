import React, { useEffect, useRef, memo } from 'react'
import type { ChartPosition } from '@/hooks/useChartPositions'

interface TradingViewWidgetProps {
  symbol: string
  interval?: string
  theme?: 'light' | 'dark'
  width?: string | number
  height?: string | number
  locale?: string
  onReady?: () => void
  className?: string
  activeIndicators?: string[]
  positions?: ChartPosition[] // Nova prop para posições
  onPositionAction?: (positionId: string, action: 'close' | 'modify', data?: any) => void // Callback para ações
}

// Declarar o TradingView global
declare global {
  interface Window {
    TradingView: any
  }
}

const TradingViewWidget: React.FC<TradingViewWidgetProps> = memo(({
  symbol,
  interval = '60', // Default 1h
  theme = 'dark',
  width = '100%',
  height = 500,
  locale = 'pt',
  onReady,
  className = '',
  activeIndicators = ['Volume@tv-basicstudies', 'RSI@tv-basicstudies'],
  positions = [], // Nova prop
  onPositionAction // Nova prop
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const widgetRef = useRef<any>(null)
  const drawnShapesRef = useRef<string[]>([]) // Armazenar IDs das formas desenhadas

  // Função para limpar shapes antigos do gráfico
  const clearPreviousShapes = () => {
    try {
      if (widgetRef.current && widgetRef.current.chart && drawnShapesRef.current.length > 0) {
        console.log('🧹 Limpando shapes antigos:', drawnShapesRef.current.length, 'shapes')

        drawnShapesRef.current.forEach(shapeId => {
          try {
            widgetRef.current.chart().removeEntity(shapeId)
          } catch (error) {
            console.warn('⚠️ Erro ao remover shape:', shapeId, error)
          }
        })

        drawnShapesRef.current = [] // Limpar lista
        console.log('✅ Shapes antigos removidos')
      }
    } catch (error) {
      console.error('❌ Erro ao limpar shapes antigos:', error)
    }
  }

  // Função para desenhar posições no gráfico usando TradingView Chart API
  const drawPositionsOnChart = (chartPositions: ChartPosition[]) => {
    try {
      console.log('🎨 drawPositionsOnChart CHAMADO com:', chartPositions)

      if (!widgetRef.current || !widgetRef.current.chart) {
        console.warn('⚠️ Chart API não disponível para desenhar posições')
        console.log('   widgetRef.current:', !!widgetRef.current)
        console.log('   widgetRef.current.chart:', widgetRef.current?.chart ? 'existe' : 'não existe')
        return
      }

      // Limpar shapes antigos primeiro
      clearPreviousShapes()

      if (!chartPositions || chartPositions.length === 0) {
        console.log('📊 Nenhuma posição para desenhar no gráfico')
        return
      }

      console.log('🎨 Iniciando desenho de posições no gráfico:', chartPositions.length, 'posições')

      chartPositions.forEach((position, index) => {
        console.log(`🎯 Desenhando posição ${index + 1}:`, {
          id: position.id,
          symbol: position.symbol,
          side: position.side,
          entryPrice: position.entryPrice,
          quantity: position.quantity,
          unrealizedPnl: position.unrealizedPnl
        })

        try {
          // Cores baseadas no lado da posição
          const entryColor = position.side === 'LONG' ? '#10B981' : '#EF4444' // Verde para LONG, vermelho para SHORT
          const pnlText = position.unrealizedPnl ? `PnL: $${position.unrealizedPnl.toFixed(2)}` : ''

          // Linha de Entry Price (Preço de Entrada) - PRINCIPAL
          const entryLineId = widgetRef.current.chart().createShape(
            { time: Date.now() / 1000, value: position.entryPrice },
            {
              shape: 'horizontal_line',
              text: `${position.side} ${position.quantity} | Entry: $${position.entryPrice.toFixed(4)} ${pnlText}`,
              overrides: {
                linecolor: entryColor,
                linestyle: 0, // Linha sólida
                linewidth: 3, // Mais espessa para destacar
                showLabel: true,
                textcolor: entryColor,
                fontsize: 12,
                horzLabelsAlign: 'right',
                vertLabelsAlign: 'middle'
              }
            }
          )
          drawnShapesRef.current.push(entryLineId) // Armazenar ID

          // Linha de Liquidation Price (se disponível) - CRÍTICA
          if (position.liquidationPrice && position.liquidationPrice > 0) {
            const liquidationLineId = widgetRef.current.chart().createShape(
              { time: Date.now() / 1000, value: position.liquidationPrice },
              {
                shape: 'horizontal_line',
                text: `⚠️ Liquidation: $${position.liquidationPrice.toFixed(4)}`,
                overrides: {
                  linecolor: '#F59E0B', // Laranja
                  linestyle: 2, // Linha pontilhada
                  linewidth: 2,
                  showLabel: true,
                  textcolor: '#F59E0B',
                  fontsize: 11,
                  horzLabelsAlign: 'left'
                }
              }
            )
            drawnShapesRef.current.push(liquidationLineId)
          }

          // Stop Loss (se disponível) - PROTEÇÃO
          if (position.stopLoss && position.stopLoss > 0) {
            const stopLossLineId = widgetRef.current.chart().createShape(
              { time: Date.now() / 1000, value: position.stopLoss },
              {
                shape: 'horizontal_line',
                text: `🔴 Stop Loss: $${position.stopLoss.toFixed(4)}`,
                overrides: {
                  linecolor: '#DC2626', // Vermelho escuro
                  linestyle: 1, // Linha tracejada
                  linewidth: 2,
                  showLabel: true,
                  textcolor: '#DC2626',
                  fontsize: 10,
                  horzLabelsAlign: 'left'
                }
              }
            )
            drawnShapesRef.current.push(stopLossLineId)
          }

          // Take Profit (se disponível) - OBJETIVO
          if (position.takeProfit && position.takeProfit > 0) {
            const takeProfitLineId = widgetRef.current.chart().createShape(
              { time: Date.now() / 1000, value: position.takeProfit },
              {
                shape: 'horizontal_line',
                text: `🎯 Take Profit: $${position.takeProfit.toFixed(4)}`,
                overrides: {
                  linecolor: '#059669', // Verde escuro
                  linestyle: 1, // Linha tracejada
                  linewidth: 2,
                  showLabel: true,
                  textcolor: '#059669',
                  fontsize: 10,
                  horzLabelsAlign: 'left'
                }
              }
            )
            drawnShapesRef.current.push(takeProfitLineId)
          }

          // Mark Price atual (linha de referência)
          if (position.markPrice && position.markPrice > 0) {
            const markPriceLineId = widgetRef.current.chart().createShape(
              { time: Date.now() / 1000, value: position.markPrice },
              {
                shape: 'horizontal_line',
                text: `Current: $${position.markPrice.toFixed(4)}`,
                overrides: {
                  linecolor: '#6B7280', // Cinza
                  linestyle: 3, // Linha pontilhada fina
                  linewidth: 1,
                  showLabel: true,
                  textcolor: '#6B7280',
                  fontsize: 9,
                  horzLabelsAlign: 'center'
                }
              }
            )
            drawnShapesRef.current.push(markPriceLineId)
          }

          console.log(`✅ Posição ${position.id} desenhada com sucesso`)

        } catch (error) {
          console.error(`❌ Erro ao desenhar posição ${position.id}:`, error)
        }
      })

      console.log(`🎨 Finalizado desenho de todas as ${chartPositions.length} posições`)

    } catch (error) {
      console.error('❌ Erro geral ao desenhar posições:', error)
    }
  }

  // Converter símbolo para formato TradingView (ex: BTCUSDT -> BINANCE:BTCUSDT)
  const getTradingViewSymbol = (symbol: string) => {
    // Se já contém exchange, retorna como está
    if (symbol.includes(':')) {
      return symbol
    }

    // Adiciona BINANCE como exchange padrão
    return `BINANCE:${symbol}`
  }

  // Effect separado para desenhar posições quando mudarem
  useEffect(() => {
    console.log('🎨 Effect de positions mudou:', {
      positionsCount: positions?.length || 0,
      hasWidget: !!widgetRef.current,
      hasChart: !!widgetRef.current?.chart,
      positions: positions
    })

    if (!positions || positions.length === 0) {
      console.log('⚠️ Sem posições para desenhar')
      return
    }

    // Tentar desenhar múltiplas vezes até a Chart API estar pronta
    let attempts = 0
    const maxAttempts = 10

    const tryDrawPositions = () => {
      attempts++
      console.log(`🔄 Tentativa ${attempts}/${maxAttempts} de desenhar posições`)

      if (widgetRef.current?.chart) {
        console.log('✅ Chart API disponível! Desenhando posições...')
        drawPositionsOnChart(positions)
      } else if (attempts < maxAttempts) {
        console.log(`⏳ Chart API ainda não disponível, tentando novamente em 1s...`)
        setTimeout(tryDrawPositions, 1000) // Tentar novamente após 1 segundo
      } else {
        console.error('❌ Chart API não ficou disponível após', maxAttempts, 'tentativas')
        const widgetKeys = widgetRef.current ? Object.keys(widgetRef.current) : []
        console.log('Debug info:', {
          hasWidget: !!widgetRef.current,
          widgetKeys: widgetKeys,
          hasChart: !!widgetRef.current?.chart,
          hasActiveChart: !!widgetRef.current?.activeChart
        })

        // Último recurso: tentar todos os métodos possíveis para acessar chart
        if (widgetRef.current) {
          console.log('🔍 Tentando métodos alternativos...')

          // Log de todos os métodos disponíveis
          widgetKeys.forEach(key => {
            const value = (widgetRef.current as any)[key]
            console.log(`  - ${key}: ${typeof value}${typeof value === 'function' ? '()' : ''}`)
          })

          // Tentar activeChart()
          try {
            const activeChart = (widgetRef.current as any).activeChart?.()
            if (activeChart) {
              console.log('✅ Encontrou chart via activeChart()!')
              console.log('📊 ActiveChart methods:', Object.keys(activeChart))
              drawPositionsOnChart(positions)
              return
            }
          } catch (e) {
            console.log('❌ activeChart() falhou:', e)
          }

          // Tentar chart()
          try {
            const chart = (widgetRef.current as any).chart?.()
            if (chart) {
              console.log('✅ Encontrou chart via chart()!')
              console.log('📊 Chart methods:', Object.keys(chart))
              drawPositionsOnChart(positions)
              return
            }
          } catch (e) {
            console.log('❌ chart() falhou:', e)
          }

          // Tentar _innerAPI()
          try {
            const innerAPI = (widgetRef.current as any)._innerAPI?.()
            if (innerAPI) {
              console.log('✅ Encontrou _innerAPI()!')
              console.log('📊 InnerAPI methods:', Object.keys(innerAPI))
            }
          } catch (e) {
            console.log('❌ _innerAPI() falhou:', e)
          }
        }
      }
    }

    // Iniciar tentativas após 2 segundos
    const initialTimer = setTimeout(tryDrawPositions, 2000)

    return () => clearTimeout(initialTimer)
  }, [positions]) // Redesenhar quando positions mudarem

  useEffect(() => {
    console.log('🚀 TradingViewWidget useEffect executando', {
      symbol,
      interval,
      theme,
      positionsCount: positions?.length || 0,
      positions: positions
    })

    // Função para carregar o script do TradingView
    const loadTradingViewScript = () => {
      return new Promise<void>((resolve, reject) => {
        if (window.TradingView) {
          console.log('✅ TradingView já está carregado')
          resolve()
          return
        }

        console.log('📥 Carregando script do TradingView...')
        const script = document.createElement('script')
        // ✅ Usar Widget Library que suporta Chart API
        script.src = 'https://s3.tradingview.com/tv.js'
        script.async = true
        script.crossOrigin = 'anonymous'
        script.onload = () => {
          console.log('✅ Script TradingView carregado com sucesso')
          resolve()
        }
        script.onerror = () => {
          console.error('❌ Falha ao carregar script TradingView')
          reject(new Error('Failed to load TradingView script'))
        }

        document.head.appendChild(script)
      })
    }

    // Função para criar o widget
    const createWidget = () => {
      console.log('📊 createWidget chamado', {
        hasContainer: !!containerRef.current,
        hasTradingView: !!window.TradingView,
        symbol,
        interval,
        theme
      })

      if (!containerRef.current || !window.TradingView) {
        console.error('❌ Container ou TradingView não disponível', {
          container: !!containerRef.current,
          tradingView: !!window.TradingView
        })
        return
      }

      // Limpar widget anterior se existir
      if (widgetRef.current) {
        try {
          console.log('🧹 Removendo widget anterior')
          widgetRef.current.remove()
        } catch (error) {
          console.warn('Error removing previous widget:', error)
        }
      }

      // Limpar container
      containerRef.current.innerHTML = ''
      console.log('🧹 Container limpo')

      // Criar novo widget com configurações profissionais de day trading
      console.log('🔧 Criando TradingView widget com:', {
        symbol: getTradingViewSymbol(symbol),
        interval,
        theme,
        activeIndicators
      })

      try {
        widgetRef.current = new window.TradingView.widget({
          width: width,
          height: height,
          symbol: getTradingViewSymbol(symbol),
          interval: interval,
          timezone: 'Etc/UTC',
          theme: theme,
          style: '1',
          locale: 'pt',
          toolbar_bg: theme === 'dark' ? '#1e1e1e' : '#ffffff',
          enable_publishing: false,
          withdateranges: true,
          allow_symbol_change: false,
          save_image: false,
          container_id: containerRef.current.id,
          autosize: false,
          fullscreen: false,
          hide_top_toolbar: false,
          hide_legend: false,
          hide_side_toolbar: false,
          // ✅ CRUCIAL: Habilitar Chart API para desenhar shapes
          disabled_features: [],
          enabled_features: ['study_templates'],
          charts_storage_api_version: '1.1',
          client_id: 'tradingview.com',
          user_id: 'public_user',
          onChartReady: () => {
            console.log('📈 TradingView onChartReady callback executado!')
            console.log('📊 Symbol:', getTradingViewSymbol(symbol))
            console.log('📅 Interval:', interval)
            console.log('🎨 Theme:', theme)
            console.log('🎯 Positions to draw:', positions?.length || 0)

            // ✅ TÉCNICA CORRETA: Esperar iframe completamente carregar
            // O widget precisa de mais tempo após onChartReady para expor Chart API
            setTimeout(() => {
              console.log('🔍 [NOVO] Tentando acessar Chart API...')

              if (!widgetRef.current) {
                console.error('❌ widgetRef.current não existe!')
                return
              }

              // Debug: mostrar todas as propriedades disponíveis
              console.log('📦 Widget properties:', Object.keys(widgetRef.current))

              // Tentar diferentes métodos de acessar a Chart API
              let chart = null

              // Método 1: activeChart() - Recomendado pela documentação
              try {
                if (typeof widgetRef.current.activeChart === 'function') {
                  chart = widgetRef.current.activeChart()
                  console.log('✅ Método 1: activeChart() funcionou!')
                }
              } catch (e) {
                console.log('❌ Método 1 falhou:', e)
              }

              // Método 2: chart() - Alternativo
              if (!chart) {
                try {
                  if (typeof widgetRef.current.chart === 'function') {
                    chart = widgetRef.current.chart()
                    console.log('✅ Método 2: chart() funcionou!')
                  }
                } catch (e) {
                  console.log('❌ Método 2 falhou:', e)
                }
              }

              // Método 3: Acessar diretamente _innerAPI
              if (!chart) {
                try {
                  if (widgetRef.current._innerAPI) {
                    const api = widgetRef.current._innerAPI()
                    if (api && api.chart) {
                      chart = api.chart()
                      console.log('✅ Método 3: _innerAPI().chart() funcionou!')
                    }
                  }
                } catch (e) {
                  console.log('❌ Método 3 falhou:', e)
                }
              }

              if (chart) {
                console.log('✅✅✅ CHART API DISPONÍVEL! ✅✅✅')
                console.log('📊 Chart methods:', Object.keys(chart))

                // Desenhar posições usando a Chart API
                if (positions && positions.length > 0) {
                  console.log('🎨 Desenhando', positions.length, 'posições no gráfico')

                  positions.forEach((position, idx) => {
                    console.log(`📍 Desenhando posição ${idx + 1}:`, {
                      symbol: position.symbol,
                      side: position.side,
                      entry: position.entryPrice
                    })

                    try {
                      // Criar linha horizontal para entry price
                      const entryColor = position.side === 'LONG' ? '#10B981' : '#EF4444'

                      // Usar createMultipointShape para linha horizontal
                      const shapeId = chart.createMultipointShape(
                        [{ time: Date.now() / 1000, price: position.entryPrice }],
                        {
                          shape: 'horizontal_line',
                          lock: false,
                          disableSelection: false,
                          disableSave: true,
                          disableUndo: false,
                          overrides: {
                            linecolor: entryColor,
                            linewidth: 2,
                            linestyle: 0, // Solid line
                            showLabel: true,
                            textcolor: entryColor,
                            fontsize: 12,
                            bold: true,
                            text: `${position.side} ${position.quantity} @ $${position.entryPrice.toFixed(2)}`
                          }
                        }
                      )

                      console.log(`✅ Shape criado com ID: ${shapeId}`)
                      drawnShapesRef.current.push(shapeId)
                    } catch (err) {
                      console.error(`❌ Erro ao desenhar ${position.symbol}:`, err)
                    }
                  })
                } else {
                  console.log('ℹ️ Nenhuma posição para desenhar')
                }
              } else {
                console.error('❌❌❌ CHART API NÃO DISPONÍVEL ❌❌❌')
                console.log('Widget type:', typeof widgetRef.current)
                console.log('Widget constructor:', widgetRef.current?.constructor?.name)
              }
            }, 3000) // Aumentar para 3 segundos

            // Adicionar indicadores após o chart estar pronto
            if (activeIndicators && activeIndicators.length > 0) {
              console.log('📊 Adding indicators after chart ready:', activeIndicators)
            }

            setTimeout(() => {
              onReady?.()
            }, 500)
          }
        })
      } catch (error) {
        console.error('Error creating TradingView widget:', error)
        // Chama onReady mesmo em caso de erro para não travar a interface
        setTimeout(() => {
          onReady?.()
        }, 1000)
      }
    }

    // Carregar script e criar widget
    loadTradingViewScript()
      .then(() => {
        createWidget()
      })
      .catch((error) => {
        console.error('Error loading TradingView:', error)
        // Chama onReady mesmo se o script não carregar
        setTimeout(() => {
          onReady?.()
        }, 1000)
      })

    // Cleanup
    return () => {
      if (widgetRef.current) {
        try {
          widgetRef.current.remove()
        } catch (error) {
          console.warn('Error cleaning up widget:', error)
        }
      }
    }
  }, [symbol, interval, theme, width, height, locale, activeIndicators]) // ✅ REMOVIDO positions - evita recriação infinita

  // Gerar ID único para o container
  const containerId = `tradingview-widget-${symbol.replace(':', '-').toLowerCase()}`

  return (
    <div className={className}>
      <div
        ref={containerRef}
        id={containerId}
        style={{
          width: typeof width === 'number' ? `${width}px` : width,
          height: typeof height === 'number' ? `${height}px` : height,
          backgroundColor: theme === 'dark' ? '#1e1e1e' : '#ffffff'
        }}
      />
    </div>
  )
})

// Definir displayName para debug
TradingViewWidget.displayName = 'TradingViewWidget'

export { TradingViewWidget }
export type { TradingViewWidgetProps }