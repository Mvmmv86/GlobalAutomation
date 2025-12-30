/**
 * EditStrategyModal Component
 * Modal for editing existing strategies
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Loader2 } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { VisualEditor, VisualStrategyConfig } from './VisualEditor'
import { strategyService, StrategyWithRelations } from '@/services/strategyService'
import { toast } from 'sonner'
import { IndicatorConfig } from './IndicatorSelector'
import { ConditionConfig } from './ConditionBuilder'

interface EditStrategyModalProps {
  strategyId: string
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function EditStrategyModal({ strategyId, isOpen, onClose, onSuccess }: EditStrategyModalProps) {
  const queryClient = useQueryClient()

  // Fetch strategy details
  const { data: strategy, isLoading, error } = useQuery({
    queryKey: ['strategy', strategyId],
    queryFn: () => strategyService.getStrategy(strategyId),
    enabled: isOpen && !!strategyId,
  })

  // Update strategy mutation - using atomic sync endpoint
  const updateMutation = useMutation({
    mutationFn: async (config: VisualStrategyConfig) => {
      // Single atomic call that:
      // 1. Updates basic info
      // 2. Deletes ALL old indicators
      // 3. Deletes ALL old conditions
      // 4. Creates new indicators
      // 5. Creates new conditions
      return await strategyService.syncStrategy(strategyId, {
        name: config.name,
        description: config.description,
        symbols: config.symbols,
        timeframe: config.timeframe,
        bot_id: config.bot_id || null,
        indicators: config.indicators.map((ind, idx) => ({
          indicator_type: ind.type,
          parameters: ind.parameters,
          order_index: ind.order_index ?? idx,
        })),
        conditions: config.conditions.map((cond, idx) => ({
          condition_type: cond.condition_type,
          conditions: cond.conditions,
          logic_operator: cond.logic_operator,
          order_index: cond.order_index ?? idx,
        })),
      })
    },
    onSuccess: () => {
      toast.success('Estrategia atualizada com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      queryClient.invalidateQueries({ queryKey: ['strategy', strategyId] })
      onClose()
      onSuccess?.()
    },
    onError: (error: Error) => {
      toast.error(`Erro ao atualizar estrategia: ${error.message}`)
    },
  })

  // Convert strategy data to VisualStrategyConfig format
  const convertToVisualConfig = (strategy: StrategyWithRelations): Partial<VisualStrategyConfig> => {
    // Convert indicators
    const indicators: IndicatorConfig[] = (strategy.indicators || []).map((ind, index) => ({
      type: ind.indicator_type,
      parameters: ind.parameters || {},
      order_index: ind.order_index ?? index,
    }))

    // Convert conditions
    const conditions: ConditionConfig[] = (strategy.conditions || []).map((cond, index) => ({
      condition_type: cond.condition_type as ConditionConfig['condition_type'],
      conditions: cond.conditions || [],
      logic_operator: cond.logic_operator || 'AND',
      order_index: cond.order_index ?? index,
    }))

    return {
      name: strategy.name,
      description: strategy.description || '',
      symbols: Array.isArray(strategy.symbols) ? strategy.symbols : [],
      timeframe: strategy.timeframe || '5m',
      bot_id: strategy.bot_id || null,
      indicators,
      conditions,
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
      <Card className="w-full max-w-4xl bg-[#1e222d] border-[#2a2e39] my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#2a2e39]">
          <h2 className="text-xl font-semibold text-white">
            Editar Estrategia
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
              <span className="ml-3 text-gray-400">Carregando estrategia...</span>
            </div>
          )}

          {error && (
            <div className="text-center py-12">
              <p className="text-red-400">Erro ao carregar estrategia</p>
              <Button
                variant="outline"
                onClick={onClose}
                className="mt-4 border-[#2a2e39] text-gray-400"
              >
                Fechar
              </Button>
            </div>
          )}

          {strategy && !isLoading && (
            <VisualEditor
              initialConfig={convertToVisualConfig(strategy)}
              onSave={(config) => updateMutation.mutate(config)}
              onCancel={onClose}
              isSaving={updateMutation.isPending}
            />
          )}
        </div>
      </Card>
    </div>
  )
}
