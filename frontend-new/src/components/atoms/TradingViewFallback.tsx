import React, { useEffect, useRef } from 'react'

interface TradingViewFallbackProps {
  symbol: string
  theme?: 'light' | 'dark'
  width?: string | number
  height?: string | number
  className?: string
}

// Gerar ID único para cada widget
let widgetIdCounter = 0

const TradingViewFallback: React.FC<TradingViewFallbackProps> = ({
  symbol,
  theme = 'dark',
  width = '100%',
  height = 500,
  className = ''
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const widgetIdRef = useRef<string>('')

  useEffect(() => {
    if (!containerRef.current) return

    console.log('🎨 TradingView Widget Creating with theme:', theme)

    // Limpar conteúdo anterior - IMPORTANTE para recriar com novo tema
    containerRef.current.innerHTML = ''

    // Gerar ID único para este widget
    widgetIdRef.current = `tradingview-widget-${++widgetIdCounter}-${Date.now()}`

    // Usar o widget de advanced chart para candlesticks e indicadores
    const widgetScript = document.createElement('script')
    widgetScript.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
    widgetScript.async = true

    // Configuração avançada para day trading com candlesticks
    const config = {
      autosize: true,
      width: '100%',
      height: '100%',
      symbol: `BINANCE:${symbol}`,
      interval: "15", // 15 minutos padrão para day trading
      timezone: "Etc/UTC",
      theme: theme,
      style: "1", // 1 = Candlestick, 2 = OHLC, 3 = Line, 4 = Area
      locale: "pt",
      toolbar_bg: theme === 'dark' ? "#1e1e1e" : "#f0f0f0",
      enable_publishing: false,
      backgroundColor: theme === 'dark' ? "rgba(19, 23, 34, 1)" : "rgba(255, 255, 255, 1)",
      gridColor: theme === 'dark' ? "rgba(42, 46, 57, 0.06)" : "rgba(233, 233, 234, 0.06)",
      hide_top_toolbar: true, // Ocultar toolbar superior para mais espaço
      hide_legend: false,
      hide_side_toolbar: true, // Ocultar toolbar lateral para mais espaço
      allow_symbol_change: false,
      save_image: false,
      // Configurações avançadas para day trading
      studies: [
        "MASimple@tv-basicstudies", // Média móvel simples
        "Volume@tv-basicstudies",   // Volume
        "RSI@tv-basicstudies"       // RSI
      ],
      // Configurações de detalhes
      details: true,
      hotlist: true,
      calendar: false,
      // Timeframes disponíveis
      studies_overrides: {
        "volume.volume.color.0": "#ef4444",
        "volume.volume.color.1": "#22c55e"
      },
      overrides: {
        // Cores das velas
        "candleStyle.upColor": "#22c55e",
        "candleStyle.downColor": "#ef4444",
        "candleStyle.drawWick": true,
        "candleStyle.drawBorder": true,
        "candleStyle.borderColor": "#378658",
        "candleStyle.borderUpColor": "#22c55e",
        "candleStyle.borderDownColor": "#ef4444",
        "candleStyle.wickUpColor": "#22c55e",
        "candleStyle.wickDownColor": "#ef4444",
        // Grid e background
        "paneProperties.background": theme === 'dark' ? "#131722" : "#ffffff",
        "paneProperties.gridColor": theme === 'dark' ? "#363c4e" : "#e0e0e0",
        "scalesProperties.textColor": theme === 'dark' ? "#b2b5be" : "#333333"
      }
    }

    widgetScript.textContent = JSON.stringify(config)

    // Criar container do widget
    const widgetContainer = document.createElement('div')
    widgetContainer.className = 'tradingview-widget-container'
    widgetContainer.style.height = '100%'
    widgetContainer.style.width = '100%'

    const widgetDiv = document.createElement('div')
    widgetDiv.className = 'tradingview-widget-container__widget'
    widgetDiv.id = widgetIdRef.current

    // Não adicionar copyright para maximizar espaço do gráfico
    widgetContainer.appendChild(widgetDiv)
    widgetContainer.appendChild(widgetScript)

    containerRef.current.appendChild(widgetContainer)

    console.log('✅ TradingView Widget Created with config:', {
      theme: theme,
      backgroundColor: theme === 'dark' ? "rgba(19, 23, 34, 1)" : "rgba(255, 255, 255, 1)"
    })

    return () => {
      // Cleanup mais robusto
      if (containerRef.current) {
        containerRef.current.innerHTML = ''
      }
      // Remover scripts órfãos
      const orphanScripts = document.querySelectorAll('script[src*="tradingview"]')
      orphanScripts.forEach(script => {
        if (script.parentNode && !document.contains(script.parentNode)) {
          script.remove()
        }
      })
    }
  }, [symbol, width, height, theme])

  return (
    <div className={className} style={{ width: '100%', height: '100%' }}>
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: theme === 'dark' ? '#131722' : '#ffffff',
          overflow: 'hidden',
          transition: 'background-color 0.3s ease'
        }}
      />
    </div>
  )
}

export { TradingViewFallback }