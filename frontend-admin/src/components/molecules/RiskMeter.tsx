import React from 'react'
import { AlertTriangle, Shield, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface RiskMeterProps {
  riskLevel: number // 0-100
  label?: string
  size?: 'sm' | 'md' | 'lg'
  showIcon?: boolean
  showPercentage?: boolean
  variant?: 'circular' | 'linear'
  className?: string
}

const RiskMeter: React.FC<RiskMeterProps> = ({
  riskLevel,
  label = "Risk Level",
  size = 'md',
  showIcon = true,
  showPercentage = true,
  variant = 'linear',
  className
}) => {
  // Clamp risk level between 0-100
  const clampedRisk = Math.max(0, Math.min(100, riskLevel))
  
  // Determine risk category and colors
  const getRiskCategory = (risk: number) => {
    if (risk <= 25) return 'low'
    if (risk <= 50) return 'medium'
    if (risk <= 75) return 'high'
    return 'critical'
  }

  const category = getRiskCategory(clampedRisk)

  const riskConfig = {
    low: {
      color: 'text-success',
      bgColor: 'bg-success',
      lightBg: 'bg-success/10',
      borderColor: 'border-success/20',
      icon: Shield,
      label: 'Low Risk'
    },
    medium: {
      color: 'text-warning',
      bgColor: 'bg-warning', 
      lightBg: 'bg-warning/10',
      borderColor: 'border-warning/20',
      icon: AlertCircle,
      label: 'Medium Risk'
    },
    high: {
      color: 'text-orange-500',
      bgColor: 'bg-orange-500',
      lightBg: 'bg-orange-500/10',
      borderColor: 'border-orange-500/20',
      icon: AlertTriangle,
      label: 'High Risk'
    },
    critical: {
      color: 'text-destructive',
      bgColor: 'bg-destructive',
      lightBg: 'bg-destructive/10',
      borderColor: 'border-destructive/20',
      icon: AlertTriangle,
      label: 'Critical Risk'
    }
  }

  const config = riskConfig[category]
  const Icon = config.icon

  const sizeConfig = {
    sm: {
      height: 'h-2',
      width: 'w-16',
      circleSize: 'h-8 w-8',
      iconSize: 'h-3 w-3',
      textSize: 'text-xs'
    },
    md: {
      height: 'h-3',
      width: 'w-24',
      circleSize: 'h-12 w-12',
      iconSize: 'h-4 w-4',
      textSize: 'text-sm'
    },
    lg: {
      height: 'h-4',
      width: 'w-32',
      circleSize: 'h-16 w-16',
      iconSize: 'h-5 w-5',
      textSize: 'text-base'
    }
  }

  const sizes = sizeConfig[size]

  if (variant === 'circular') {
    const circumference = 2 * Math.PI * 18 // radius = 18
    const strokeDasharray = circumference
    const strokeDashoffset = circumference - (clampedRisk / 100) * circumference

    return (
      <div className={cn("flex flex-col items-center space-y-2", className)}>
        <div className="relative">
          <svg className={cn(sizes.circleSize, "transform -rotate-90")} viewBox="0 0 40 40">
            {/* Background circle */}
            <circle
              cx="20"
              cy="20"
              r="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="text-muted-foreground/20"
            />
            {/* Progress circle */}
            <circle
              cx="20"
              cy="20"
              r="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray={strokeDasharray}
              strokeDashoffset={strokeDashoffset}
              className={cn(config.color, "transition-all duration-300")}
            />
          </svg>
          
          {/* Center content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            {showIcon && <Icon className={cn(sizes.iconSize, config.color)} />}
            {showPercentage && (
              <span className={cn(sizes.textSize, "font-semibold", config.color)}>
                {Math.round(clampedRisk)}%
              </span>
            )}
          </div>
        </div>

        <div className="text-center">
          <div className={cn(sizes.textSize, "font-medium")}>{label}</div>
          <div className={cn(sizes.textSize, "text-xs text-muted-foreground mt-1")}>
            {config.label}
          </div>
        </div>
      </div>
    )
  }

  // Linear variant
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {showIcon && <Icon className={cn(sizes.iconSize, config.color)} />}
          <span className={cn(sizes.textSize, "font-medium")}>{label}</span>
        </div>
        {showPercentage && (
          <span className={cn(sizes.textSize, "font-semibold", config.color)}>
            {Math.round(clampedRisk)}%
          </span>
        )}
      </div>

      <div className="space-y-1">
        {/* Progress bar */}
        <div className={cn(
          "relative rounded-full bg-muted overflow-hidden",
          sizes.height,
          sizes.width
        )}>
          <div
            className={cn(
              "h-full rounded-full transition-all duration-300",
              config.bgColor
            )}
            style={{ width: `${clampedRisk}%` }}
          />
        </div>

        {/* Risk category label */}
        <div className={cn(sizes.textSize, "text-xs text-muted-foreground")}>
          {config.label}
        </div>
      </div>
    </div>
  )
}

export { RiskMeter }
export type { RiskMeterProps }