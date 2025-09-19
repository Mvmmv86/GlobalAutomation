import React, { useState } from 'react'
import { MoreVertical, TrendingUp, TrendingDown, X, Edit3, DollarSign, Percent } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { PriceDisplay } from '../molecules/PriceDisplay'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../atoms/Dialog'
import { FormField } from '../molecules/FormField'
import { cn, formatDate } from '@/lib/utils'

interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  status: 'open' | 'closed'
  size: number
  entryPrice: number
  markPrice: number
  unrealizedPnl: number
  realizedPnl: number
  percentage: number
  leverage: number
  liquidationPrice?: number
  openedAt: string
  exchange: string
  margin: number
  fees: number
}

interface PositionsTableProps {
  positions: Position[]
  onClosePosition: (positionId: string) => void
  onModifyPosition: (positionId: string, data: { stopLoss?: number; takeProfit?: number }) => void
  className?: string
}

const PositionsTable: React.FC<PositionsTableProps> = ({
  positions,
  onClosePosition,
  onModifyPosition,
  className
}) => {
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null)
  const [stopLoss, setStopLoss] = useState<string>('')
  const [takeProfit, setTakeProfit] = useState<string>('')

  const activePositions = positions.filter(p => p.status === 'open')
  const totalUnrealizedPnl = activePositions.reduce((sum, p) => sum + p.unrealizedPnl, 0)

  const handleModifyPosition = () => {
    if (!selectedPosition) return

    onModifyPosition(selectedPosition.id, {
      ...(stopLoss && { stopLoss: parseFloat(stopLoss) }),
      ...(takeProfit && { takeProfit: parseFloat(takeProfit) })
    })

    setSelectedPosition(null)
    setStopLoss('')
    setTakeProfit('')
  }

  const PositionRow: React.FC<{ position: Position }> = ({ position }) => {
    const pnlColor = position.unrealizedPnl >= 0 ? 'text-success' : 'text-destructive'
    const sideColor = position.side === 'long' ? 'text-success' : 'text-destructive'
    const SideIcon = position.side === 'long' ? TrendingUp : TrendingDown

    return (
      <div className="grid grid-cols-1 md:grid-cols-7 gap-4 p-4 border-b last:border-b-0 hover:bg-muted/50 transition-colors">
        {/* Symbol & Side */}
        <div className="flex items-center space-x-3">
          <div className={cn("p-2 rounded-full", position.side === 'long' ? 'bg-success/10' : 'bg-destructive/10')}>
            <SideIcon className={cn("h-4 w-4", sideColor)} />
          </div>
          <div>
            <div className="font-semibold">{position.symbol}</div>
            <div className="flex items-center space-x-2">
              <Badge variant="outline" className={cn("text-xs", sideColor)}>
                {position.side.toUpperCase()}
              </Badge>
              <span className="text-xs text-muted-foreground">{position.leverage}x</span>
            </div>
          </div>
        </div>

        {/* Size & Entry */}
        <div className="space-y-1">
          <div className="text-sm font-medium">
            {new Intl.NumberFormat('en-US', { 
              minimumFractionDigits: 8,
              maximumFractionDigits: 8 
            }).format(position.size)}
          </div>
          <div className="text-xs text-muted-foreground">
            Entry: {position.entryPrice.toFixed(2)}
          </div>
        </div>

        {/* Mark Price */}
        <div>
          <PriceDisplay 
            price={position.markPrice}
            previousPrice={position.entryPrice}
            size="sm"
            showChange={false}
          />
        </div>

        {/* PnL */}
        <div className="space-y-1">
          <div className={cn("font-medium", pnlColor)}>
            {position.unrealizedPnl >= 0 ? '+' : ''}{position.unrealizedPnl.toFixed(2)} USDT
          </div>
          <div className={cn("text-sm", pnlColor)}>
            ({position.percentage >= 0 ? '+' : ''}{position.percentage.toFixed(2)}%)
          </div>
        </div>

        {/* Margin */}
        <div className="space-y-1">
          <div className="text-sm">
            {position.margin.toFixed(2)} USDT
          </div>
          {position.liquidationPrice && (
            <div className="text-xs text-muted-foreground">
              Liq: {position.liquidationPrice.toFixed(2)}
            </div>
          )}
        </div>

        {/* Exchange & Time */}
        <div className="space-y-1">
          <Badge variant="secondary" className="text-xs">
            {position.exchange.toUpperCase()}
          </Badge>
          <div className="text-xs text-muted-foreground">
            {formatDate(position.openedAt)}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end space-x-1">
          <Dialog>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => {
                  setSelectedPosition(position)
                  setStopLoss('')
                  setTakeProfit('')
                }}
              >
                <Edit3 className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Modify Position - {position.symbol}</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
                  <div>
                    <span className="text-sm text-muted-foreground">Size:</span>
                    <div className="font-medium">{position.size}</div>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Side:</span>
                    <div className={cn("font-medium", sideColor)}>{position.side.toUpperCase()}</div>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Entry Price:</span>
                    <div className="font-medium">{position.entryPrice.toFixed(2)}</div>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Mark Price:</span>
                    <div className="font-medium">{position.markPrice.toFixed(2)}</div>
                  </div>
                </div>

                <FormField
                  label="Stop Loss"
                  type="number"
                  placeholder="Stop loss price"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(e.target.value)}
                  hint="Optional stop loss price"
                />

                <FormField
                  label="Take Profit"
                  type="number"
                  placeholder="Take profit price"
                  value={takeProfit}
                  onChange={(e) => setTakeProfit(e.target.value)}
                  hint="Optional take profit price"
                />

                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setSelectedPosition(null)}>
                    Cancel
                  </Button>
                  <Button onClick={handleModifyPosition}>
                    Update Position
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={() => onClosePosition(position.id)}
          >
            <X className="h-4 w-4" />
          </Button>

          <Button variant="ghost" size="icon" className="h-8 w-8">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </div>
      </div>
    )
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Open Positions ({activePositions.length})</span>
          <div className="flex items-center space-x-4">
            <div className="text-sm">
              Total PnL: <span className={cn("font-semibold", totalUnrealizedPnl >= 0 ? 'text-success' : 'text-destructive')}>
                {totalUnrealizedPnl >= 0 ? '+' : ''}{totalUnrealizedPnl.toFixed(2)} USDT
              </span>
            </div>
          </div>
        </CardTitle>
      </CardHeader>

      <CardContent className="p-0">
        {/* Desktop Header */}
        <div className="hidden md:grid md:grid-cols-7 gap-4 p-4 border-b bg-muted/30 text-sm font-medium text-muted-foreground">
          <div>Symbol</div>
          <div>Size/Entry</div>
          <div>Mark Price</div>
          <div>PnL</div>
          <div>Margin</div>
          <div>Exchange</div>
          <div className="text-right">Actions</div>
        </div>

        {/* Positions List */}
        {activePositions.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <DollarSign className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h3 className="font-medium mb-2">No Open Positions</h3>
            <p className="text-sm">Your open positions will appear here</p>
          </div>
        ) : (
          <div className="divide-y">
            {activePositions.map((position) => (
              <PositionRow key={position.id} position={position} />
            ))}
          </div>
        )}

        {/* Summary Footer */}
        {activePositions.length > 0 && (
          <div className="p-4 border-t bg-muted/30">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Total Margin:</span>
                <div className="font-medium">
                  {activePositions.reduce((sum, p) => sum + p.margin, 0).toFixed(2)} USDT
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">Total Fees:</span>
                <div className="font-medium">
                  {activePositions.reduce((sum, p) => sum + p.fees, 0).toFixed(2)} USDT
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">Avg Leverage:</span>
                <div className="font-medium">
                  {(activePositions.reduce((sum, p) => sum + p.leverage, 0) / activePositions.length).toFixed(1)}x
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">Unrealized PnL:</span>
                <div className={cn("font-medium", totalUnrealizedPnl >= 0 ? 'text-success' : 'text-destructive')}>
                  {totalUnrealizedPnl >= 0 ? '+' : ''}{totalUnrealizedPnl.toFixed(2)} USDT
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export { PositionsTable }
export type { PositionsTableProps, Position }