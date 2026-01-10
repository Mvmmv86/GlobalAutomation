/**
 * RiskStatusCard Component
 * Displays risk management status for a subscription
 *
 * Shows:
 * - Current daily loss vs max daily loss
 * - Current positions vs max positions
 * - Risk level indicator (low/medium/high/critical)
 * - Alerts when approaching limits
 */

import React from 'react'
import { Shield, AlertTriangle, TrendingDown, Layers } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'
import { RiskMeter } from './RiskMeter'
import { cn } from '@/lib/utils'

interface RiskStatusCardProps {
  // Subscription level
  currentDailyLoss: number
  maxDailyLoss: number
  currentPositions: number
  maxPositions: number
  // Optional: symbol level breakdown
  symbolRisks?: {
    symbol: string
    currentLoss: number
    maxLoss: number
    currentPositions: number
    maxPositions: number
  }[]
  // Display options
  compact?: boolean
  showSymbols?: boolean
  className?: string
}

export const RiskStatusCard: React.FC<RiskStatusCardProps> = ({
  currentDailyLoss,
  maxDailyLoss,
  currentPositions,
  maxPositions,
  symbolRisks = [],
  compact = false,
  showSymbols = false,
  className
}) => {
  // Calculate risk percentages
  const lossRiskPct = maxDailyLoss > 0 ? (currentDailyLoss / maxDailyLoss) * 100 : 0
  const positionRiskPct = maxPositions > 0 ? (currentPositions / maxPositions) * 100 : 0
  const overallRisk = Math.max(lossRiskPct, positionRiskPct)

  // Determine risk level
  const getRiskLevel = (pct: number) => {
    if (pct >= 90) return 'critical'
    if (pct >= 75) return 'high'
    if (pct >= 50) return 'medium'
    return 'low'
  }

  const riskLevel = getRiskLevel(overallRisk)
  const isAtRisk = overallRisk >= 75

  // Risk level colors
  const riskColors = {
    low: 'text-green-500 bg-green-500/10 border-green-500/20',
    medium: 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20',
    high: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
    critical: 'text-red-500 bg-red-500/10 border-red-500/20'
  }

  const riskLabels = {
    low: 'Baixo Risco',
    medium: 'Risco Moderado',
    high: 'Alto Risco',
    critical: 'Risco Critico'
  }

  if (compact) {
    return (
      <div className={cn("flex items-center gap-3 p-2 rounded-lg", riskColors[riskLevel], className)}>
        <Shield className={cn("w-4 h-4", riskLevel === 'low' ? 'text-green-500' : riskLevel === 'medium' ? 'text-yellow-500' : 'text-red-500')} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium truncate">
              Perda: ${currentDailyLoss.toFixed(2)} / ${maxDailyLoss.toFixed(2)}
            </span>
            <span className="text-xs">
              {lossRiskPct.toFixed(0)}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full mt-1">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                lossRiskPct >= 90 ? 'bg-red-500' :
                lossRiskPct >= 75 ? 'bg-orange-500' :
                lossRiskPct >= 50 ? 'bg-yellow-500' : 'bg-green-500'
              )}
              style={{ width: `${Math.min(lossRiskPct, 100)}%` }}
            />
          </div>
        </div>
      </div>
    )
  }

  return (
    <Card className={cn("border", isAtRisk ? 'border-red-500/30' : 'border-border', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Status de Risco
          </CardTitle>
          <Badge className={cn("text-xs", riskColors[riskLevel])}>
            {riskLevel === 'critical' && <AlertTriangle className="w-3 h-3 mr-1" />}
            {riskLabels[riskLevel]}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Overall Risk Meter */}
        <div className="flex justify-center">
          <RiskMeter
            riskLevel={overallRisk}
            label="Risco Geral"
            variant="circular"
            size="md"
          />
        </div>

        {/* Loss Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1 text-muted-foreground">
              <TrendingDown className="w-3 h-3" />
              Perda Diaria
            </span>
            <span className={cn(
              "font-medium",
              lossRiskPct >= 75 ? 'text-red-500' : 'text-foreground'
            )}>
              ${currentDailyLoss.toFixed(2)} / ${maxDailyLoss.toFixed(2)}
            </span>
          </div>
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                lossRiskPct >= 90 ? 'bg-red-500' :
                lossRiskPct >= 75 ? 'bg-orange-500' :
                lossRiskPct >= 50 ? 'bg-yellow-500' : 'bg-green-500'
              )}
              style={{ width: `${Math.min(lossRiskPct, 100)}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground text-right">
            {(100 - lossRiskPct).toFixed(1)}% disponivel
          </p>
        </div>

        {/* Positions Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1 text-muted-foreground">
              <Layers className="w-3 h-3" />
              Posicoes
            </span>
            <span className={cn(
              "font-medium",
              positionRiskPct >= 75 ? 'text-red-500' : 'text-foreground'
            )}>
              {currentPositions} / {maxPositions}
            </span>
          </div>
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                positionRiskPct >= 90 ? 'bg-red-500' :
                positionRiskPct >= 75 ? 'bg-orange-500' :
                positionRiskPct >= 50 ? 'bg-yellow-500' : 'bg-blue-500'
              )}
              style={{ width: `${Math.min(positionRiskPct, 100)}%` }}
            />
          </div>
        </div>

        {/* Symbol-level risks (optional) */}
        {showSymbols && symbolRisks.length > 0 && (
          <div className="pt-2 border-t border-border">
            <p className="text-xs font-medium text-muted-foreground mb-2">Por Ativo:</p>
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {symbolRisks.map((sr) => {
                const symbolLossPct = sr.maxLoss > 0 ? (sr.currentLoss / sr.maxLoss) * 100 : 0
                return (
                  <div key={sr.symbol} className="flex items-center gap-2 text-xs">
                    <span className="font-mono w-20 truncate">{sr.symbol}</span>
                    <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          symbolLossPct >= 90 ? 'bg-red-500' :
                          symbolLossPct >= 75 ? 'bg-orange-500' : 'bg-green-500'
                        )}
                        style={{ width: `${Math.min(symbolLossPct, 100)}%` }}
                      />
                    </div>
                    <span className="text-muted-foreground w-12 text-right">
                      {symbolLossPct.toFixed(0)}%
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Warning message */}
        {isAtRisk && (
          <div className={cn(
            "flex items-start gap-2 p-2 rounded-lg text-xs",
            riskLevel === 'critical' ? 'bg-red-500/10 text-red-500' : 'bg-orange-500/10 text-orange-500'
          )}>
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <span>
              {riskLevel === 'critical'
                ? 'Limite de risco atingido! Novas operacoes bloqueadas e posicoes podem ser fechadas automaticamente.'
                : 'Atencao: Aproximando-se do limite de risco. Considere reduzir exposicao.'}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default RiskStatusCard
