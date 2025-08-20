import React, { useEffect, useRef, useState } from 'react'
import { Maximize2, Minimize2, Settings, TrendingUp } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { PriceDisplay } from '../molecules/PriceDisplay'
import { cn } from '@/lib/utils'

interface ChartContainerProps {
  symbol: string
  interval?: string
  theme?: 'light' | 'dark'
  height?: number
  onSymbolChange?: (symbol: string) => void
  className?: string
}

const ChartContainer: React.FC<ChartContainerProps> = ({
  symbol,
  interval = '1h',
  theme = 'dark',
  height = 500,
  onSymbolChange,
  className
}) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [priceChange, setPriceChange] = useState<number>(0)

  // Mock data for demo - In real implementation, this would come from TradingView widget
  useEffect(() => {
    // Simulate loading
    const timer = setTimeout(() => {
      setIsLoading(false)
      // Mock price data
      setCurrentPrice(45234.56)
      setPriceChange(1.23)
    }, 2000)

    return () => clearTimeout(timer)
  }, [symbol])

  // Initialize TradingView widget
  useEffect(() => {
    if (!containerRef.current || isLoading) return

    // In a real implementation, you would load the TradingView library here
    // For now, we'll create a placeholder
    const mockChart = document.createElement('div')
    mockChart.className = 'w-full h-full bg-muted/20 rounded-lg flex items-center justify-center border-2 border-dashed border-muted-foreground/20'
    mockChart.innerHTML = `
      <div class="text-center p-8">
        <div class="text-6xl mb-4">📈</div>
        <h3 class="text-lg font-semibold mb-2">TradingView Chart</h3>
        <p class="text-sm text-muted-foreground mb-4">${symbol} - ${interval}</p>
        <p class="text-xs text-muted-foreground">Chart widget would be loaded here</p>
      </div>
    `

    // Clear previous content
    containerRef.current.innerHTML = ''
    containerRef.current.appendChild(mockChart)

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = ''
      }
    }
  }, [symbol, interval, isLoading, theme])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen()
      setIsFullscreen(true)
    } else {
      document.exitFullscreen()
      setIsFullscreen(false)
    }
  }

  const intervals = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-3">
            <TrendingUp className="h-5 w-5" />
            <span>{symbol} Chart</span>
            {!isLoading && (
              <PriceDisplay 
                price={currentPrice} 
                change={priceChange}
                size="sm"
              />
            )}
          </CardTitle>

          <div className="flex items-center space-x-2">
            {/* Interval Selector */}
            <div className="flex items-center space-x-1">
              {intervals.map((int) => (
                <Button
                  key={int}
                  variant={interval === int ? "default" : "ghost"}
                  size="sm"
                  className="h-7 px-2 text-xs"
                  onClick={() => {
                    // Handle interval change
                    console.log('Interval changed to:', int)
                  }}
                >
                  {int}
                </Button>
              ))}
            </div>

            {/* Chart Controls */}
            <div className="flex items-center space-x-1">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <Settings className="h-4 w-4" />
              </Button>
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

        {/* Status Bar */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-4">
            <Badge variant="secondary">{interval}</Badge>
            <Badge variant="outline">Live</Badge>
            {!isLoading && (
              <div className="flex items-center space-x-2 text-muted-foreground">
                <span>Vol: 1.23M</span>
                <span>•</span>
                <span>24h High: 45,890</span>
                <span>•</span>
                <span>24h Low: 44,120</span>
              </div>
            )}
          </div>
          
          {isLoading && (
            <div className="flex items-center space-x-2">
              <div className="h-2 w-2 bg-primary rounded-full animate-pulse" />
              <span className="text-xs text-muted-foreground">Loading chart...</span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <div 
          ref={containerRef}
          className="relative w-full"
          style={{ height: `${height}px` }}
        >
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm">
              <div className="flex flex-col items-center space-y-4">
                <div className="h-8 w-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <div className="text-sm text-muted-foreground">Loading {symbol} chart...</div>
              </div>
            </div>
          )}
        </div>

        {/* Chart Footer */}
        {!isLoading && (
          <div className="p-3 border-t bg-muted/30">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <div className="flex items-center space-x-4">
                <span>Powered by TradingView</span>
                <span>•</span>
                <span>Real-time data</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="h-2 w-2 bg-success rounded-full" />
                <span>Connected</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export { ChartContainer }
export type { ChartContainerProps }