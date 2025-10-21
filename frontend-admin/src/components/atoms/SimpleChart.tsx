import React, { useEffect, useRef } from 'react'
import { TrendingUp } from 'lucide-react'

interface SimpleChartProps {
  symbol: string
  width?: string | number
  height?: string | number
  className?: string
}

const SimpleChart: React.FC<SimpleChartProps> = ({
  symbol,
  width = '100%',
  height = 500,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Mock data para candlesticks - em produção viria da API
  const generateMockCandlestickData = () => {
    const data = []
    let basePrice = 45000

    for (let i = 0; i < 50; i++) {
      // Simular movimento de preço
      const priceChange = (Math.random() - 0.5) * 2000
      basePrice = Math.max(basePrice + priceChange, 20000)

      // Gerar OHLC para cada vela
      const open = basePrice
      const volatility = Math.random() * 800 + 200 // Entre 200-1000 de volatilidade
      const high = open + Math.random() * volatility
      const low = open - Math.random() * volatility
      const close = low + Math.random() * (high - low)

      data.push({
        time: Date.now() - (50 - i) * 15 * 60000, // 15 minutos de intervalo
        open: Math.max(open, 20000),
        high: Math.max(high, 20000),
        low: Math.max(low, 20000),
        close: Math.max(close, 20000),
        volume: Math.random() * 1000000 + 100000
      })

      basePrice = close
    }
    return data
  }

  useEffect(() => {
    if (!canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Configurar canvas para preencher 100% do container
    const container = canvas.parentElement
    if (!container) return

    const rect = container.getBoundingClientRect()
    canvas.style.width = '100%'
    canvas.style.height = '100%'
    canvas.width = rect.width
    canvas.height = rect.height

    // Limpar canvas
    ctx.fillStyle = '#131722'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Gerar dados mock de candlesticks
    const data = generateMockCandlestickData()

    // Calcular limites de preço
    const allPrices = data.flatMap(d => [d.open, d.high, d.low, d.close])
    const minPrice = Math.min(...allPrices)
    const maxPrice = Math.max(...allPrices)
    const priceRange = maxPrice - minPrice

    // Desenhar grid
    ctx.strokeStyle = '#2A2E39'
    ctx.lineWidth = 1

    // Linhas horizontais
    for (let i = 0; i <= 5; i++) {
      const y = (canvas.height / 5) * i
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(canvas.width, y)
      ctx.stroke()
    }

    // Linhas verticais (menos linhas para melhor visualização das velas)
    for (let i = 0; i <= 8; i++) {
      const x = (canvas.width / 8) * i
      ctx.beginPath()
      ctx.moveTo(x, 0)
      ctx.lineTo(x, canvas.height)
      ctx.stroke()
    }

    // Desenhar candlesticks (velas)
    const candleWidth = Math.max(canvas.width / data.length * 0.6, 3) // Largura das velas

    data.forEach((candle, index) => {
      const x = (index + 0.5) / data.length * canvas.width

      // Calcular posições Y
      const openY = canvas.height - ((candle.open - minPrice) / priceRange) * canvas.height
      const highY = canvas.height - ((candle.high - minPrice) / priceRange) * canvas.height
      const lowY = canvas.height - ((candle.low - minPrice) / priceRange) * canvas.height
      const closeY = canvas.height - ((candle.close - minPrice) / priceRange) * canvas.height

      // Determinar se é vela de alta ou baixa
      const isGreen = candle.close >= candle.open
      const bodyTop = Math.min(openY, closeY)
      const bodyBottom = Math.max(openY, closeY)
      const bodyHeight = Math.abs(closeY - openY)

      // Desenhar pavio (high-low line)
      ctx.strokeStyle = isGreen ? '#22c55e' : '#ef4444'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(x, highY)
      ctx.lineTo(x, lowY)
      ctx.stroke()

      // Desenhar corpo da vela
      if (bodyHeight > 1) {
        // Vela com corpo
        if (isGreen) {
          // Vela verde (alta) - corpo oco
          ctx.fillStyle = '#131722' // Fundo
          ctx.fillRect(x - candleWidth/2, bodyTop, candleWidth, bodyHeight)
          ctx.strokeStyle = '#22c55e'
          ctx.lineWidth = 1
          ctx.strokeRect(x - candleWidth/2, bodyTop, candleWidth, bodyHeight)
        } else {
          // Vela vermelha (baixa) - corpo preenchido
          ctx.fillStyle = '#ef4444'
          ctx.fillRect(x - candleWidth/2, bodyTop, candleWidth, bodyHeight)
        }
      } else {
        // Doji (abertura = fechamento) - linha horizontal
        ctx.strokeStyle = isGreen ? '#22c55e' : '#ef4444'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(x - candleWidth/2, openY)
        ctx.lineTo(x + candleWidth/2, openY)
        ctx.stroke()
      }
    })

    // Desenhar volume no fundo (barras mais transparentes)
    const maxVolume = Math.max(...data.map(d => d.volume))
    ctx.fillStyle = 'rgba(100, 100, 100, 0.2)'

    data.forEach((candle, index) => {
      const x = (index + 0.5) / data.length * canvas.width
      const volumeHeight = (candle.volume / maxVolume) * (canvas.height * 0.2) // 20% da altura
      const volumeY = canvas.height - volumeHeight

      ctx.fillRect(x - candleWidth/2, volumeY, candleWidth, volumeHeight)
    })

    // Labels de preço
    ctx.fillStyle = '#787B86'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'right'

    for (let i = 0; i <= 4; i++) {
      const price = minPrice + (priceRange / 4) * (4 - i)
      const y = (canvas.height / 4) * i + 4
      ctx.fillText(`$${price.toFixed(0)}`, canvas.width - 5, y)
    }

  }, [symbol, width, height])

  const currentPrice = 45234.56
  const priceChange = 1.23
  const isPositive = priceChange >= 0

  return (
    <div className={className}>
      {/* Header com informações do símbolo */}
      <div className="p-4 bg-muted/30 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span className="font-mono font-semibold text-lg">{symbol}</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="font-mono font-semibold text-xl">
                ${currentPrice.toLocaleString()}
              </span>
              <span className={`text-sm font-medium ${
                isPositive ? 'text-success' : 'text-destructive'
              }`}>
                {isPositive ? '+' : ''}{priceChange}%
              </span>
            </div>
          </div>
          <div className="text-sm text-muted-foreground">
            Gráfico Simplificado • Dados Demo
          </div>
        </div>
      </div>

      {/* Canvas do gráfico */}
      <div className="relative">
        <canvas
          ref={canvasRef}
          style={{
            width: typeof width === 'number' ? `${width}px` : width,
            height: typeof height === 'number' ? `${height}px` : height,
          }}
          className="w-full"
        />

        {/* Overlay com informações */}
        <div className="absolute top-4 left-4 bg-background/80 backdrop-blur-sm border rounded px-3 py-2">
          <div className="text-xs space-y-1">
            <div className="flex items-center justify-between space-x-4">
              <span className="text-muted-foreground">Alta 24h:</span>
              <span className="font-mono">$45,890</span>
            </div>
            <div className="flex items-center justify-between space-x-4">
              <span className="text-muted-foreground">Baixa 24h:</span>
              <span className="font-mono">$44,120</span>
            </div>
            <div className="flex items-center justify-between space-x-4">
              <span className="text-muted-foreground">Volume:</span>
              <span className="font-mono">1.23M</span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-3 bg-muted/30 border-t">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Gráfico Demo • Atualização em tempo real em desenvolvimento</span>
          <div className="flex items-center space-x-2">
            <div className="h-2 w-2 bg-orange-500 rounded-full animate-pulse" />
            <span>Demo Mode</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export { SimpleChart }
export type { SimpleChartProps }