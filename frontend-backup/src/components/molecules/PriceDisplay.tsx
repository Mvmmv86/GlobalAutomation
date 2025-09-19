import React from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface PriceDisplayProps {
  price: number
  previousPrice?: number
  change?: number
  changePercent?: number
  currency?: string
  size?: 'sm' | 'md' | 'lg'
  showTrend?: boolean
  showChange?: boolean
  className?: string
}

const PriceDisplay: React.FC<PriceDisplayProps> = ({
  price,
  previousPrice,
  change,
  changePercent,
  currency = 'USDT',
  size = 'md',
  showTrend = true,
  showChange = true,
  className
}) => {
  // Calculate trend if previousPrice is provided
  let trend: 'up' | 'down' | 'neutral' = 'neutral'
  let calculatedChange = change
  let calculatedChangePercent = changePercent

  if (previousPrice !== undefined && previousPrice !== 0) {
    calculatedChange = calculatedChange ?? (price - previousPrice)
    calculatedChangePercent = calculatedChangePercent ?? ((calculatedChange / previousPrice) * 100)
    
    if (calculatedChange > 0) trend = 'up'
    else if (calculatedChange < 0) trend = 'down'
  }

  const sizeClasses = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl font-semibold'
  }

  const trendClasses = {
    up: 'text-success',
    down: 'text-destructive', 
    neutral: 'text-muted-foreground'
  }

  const formatPrice = (value: number, decimals: number = 2) => {
    return new Intl.NumberFormat('en-US', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(value)
  }

  const formatChange = (value: number) => {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${formatPrice(value)}`
  }

  const formatPercentChange = (value: number) => {
    const sign = value >= 0 ? '+' : ''
    return `${sign}${formatPrice(value, 2)}%`
  }

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus

  return (
    <div className={cn("flex items-center space-x-2", className)}>
      {/* Price */}
      <span className={cn(sizeClasses[size], "font-mono tabular-nums")}>
        {formatPrice(price, price < 1 ? 6 : 2)} {currency}
      </span>

      {/* Trend Icon */}
      {showTrend && (
        <TrendIcon className={cn(
          "h-4 w-4",
          trendClasses[trend],
          size === 'sm' && "h-3 w-3",
          size === 'lg' && "h-5 w-5"
        )} />
      )}

      {/* Change Display */}
      {showChange && calculatedChange !== undefined && calculatedChangePercent !== undefined && (
        <div className={cn(
          "flex flex-col text-xs",
          trendClasses[trend],
          size === 'lg' && "text-sm"
        )}>
          <span className="font-mono tabular-nums">
            {formatChange(calculatedChange)}
          </span>
          <span className="font-mono tabular-nums">
            ({formatPercentChange(calculatedChangePercent)})
          </span>
        </div>
      )}
    </div>
  )
}

export { PriceDisplay }
export type { PriceDisplayProps }