import React from 'react'
import { MoreVertical, X, RefreshCw } from 'lucide-react'
import { Card, CardContent } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { Button } from '../atoms/Button'
import { PriceDisplay } from './PriceDisplay'
import { cn, formatDate } from '@/lib/utils'

interface OrderCardProps {
  id: string
  clientOrderId: string
  symbol: string
  side: 'buy' | 'sell'
  type: 'market' | 'limit' | 'stop' | 'stop_limit'
  status: 'pending' | 'open' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected'
  quantity: number
  price?: number
  filledQuantity?: number
  averageFillPrice?: number
  feesPaid?: number
  createdAt: string
  onCancel?: (orderId: string) => void
  onModify?: (orderId: string) => void
  className?: string
}

const OrderCard: React.FC<OrderCardProps> = ({
  id,
  clientOrderId,
  symbol,
  side,
  type,
  status,
  quantity,
  price,
  filledQuantity = 0,
  averageFillPrice,
  feesPaid = 0,
  createdAt,
  onCancel,
  onModify,
  className
}) => {
  const sideColors = {
    buy: 'text-success border-success/20 bg-success/5',
    sell: 'text-destructive border-destructive/20 bg-destructive/5'
  }

  const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    pending: 'outline',
    open: 'secondary', 
    filled: 'default',
    partially_filled: 'secondary',
    cancelled: 'destructive',
    rejected: 'destructive'
  }

  const canCancel = ['pending', 'open', 'partially_filled'].includes(status)
  const canModify = ['open'].includes(status) && type !== 'market'

  const fillPercentage = quantity > 0 ? (filledQuantity / quantity) * 100 : 0

  return (
    <Card className={cn("relative overflow-hidden", className)}>
      {/* Progress bar for partial fills */}
      {fillPercentage > 0 && fillPercentage < 100 && (
        <div className="absolute top-0 left-0 h-1 bg-primary/20">
          <div 
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${fillPercentage}%` }}
          />
        </div>
      )}

      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Badge variant={statusVariants[status]} className="text-xs">
              {status.replace('_', ' ').toUpperCase()}
            </Badge>
            <span className={cn(
              "text-xs font-medium px-2 py-1 rounded border",
              sideColors[side]
            )}>
              {side.toUpperCase()}
            </span>
          </div>

          <div className="flex items-center space-x-1">
            {canModify && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => onModify?.(id)}
              >
                <RefreshCw className="h-3 w-3" />
              </Button>
            )}
            {canCancel && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() => onCancel?.(id)}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
            <Button variant="ghost" size="icon" className="h-6 w-6">
              <MoreVertical className="h-3 w-3" />
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          {/* Symbol and Type */}
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">{symbol}</h3>
            <span className="text-xs text-muted-foreground uppercase">{type}</span>
          </div>

          {/* Price Information */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-muted-foreground">Quantity:</span>
              <div className="font-mono">
                {new Intl.NumberFormat('en-US', { 
                  minimumFractionDigits: 8,
                  maximumFractionDigits: 8 
                }).format(quantity)}
              </div>
            </div>
            {price && (
              <div>
                <span className="text-muted-foreground">Price:</span>
                <PriceDisplay 
                  price={price} 
                  size="sm" 
                  showTrend={false} 
                  showChange={false}
                  className="justify-end"
                />
              </div>
            )}
          </div>

          {/* Filled Information */}
          {filledQuantity > 0 && (
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground">Filled:</span>
                <div className="font-mono">
                  {new Intl.NumberFormat('en-US', { 
                    minimumFractionDigits: 8,
                    maximumFractionDigits: 8 
                  }).format(filledQuantity)} ({fillPercentage.toFixed(1)}%)
                </div>
              </div>
              {averageFillPrice && (
                <div>
                  <span className="text-muted-foreground">Avg Price:</span>
                  <PriceDisplay 
                    price={averageFillPrice} 
                    size="sm" 
                    showTrend={false} 
                    showChange={false}
                    className="justify-end"
                  />
                </div>
              )}
            </div>
          )}

          {/* Fees and Time */}
          <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
            <span>
              Fee: {new Intl.NumberFormat('en-US', { 
                minimumFractionDigits: 2,
                maximumFractionDigits: 8 
              }).format(feesPaid)}
            </span>
            <span>{formatDate(createdAt)}</span>
          </div>

          {/* Order ID */}
          <div className="text-xs text-muted-foreground">
            #{clientOrderId.slice(-8)}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export { OrderCard }
export type { OrderCardProps }