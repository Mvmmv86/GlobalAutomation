/**
 * CreateStrategyModal Component
 * Modal for creating new strategies with 3 modes: Visual, YAML, PineScript
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Settings, Code, Zap } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { VisualEditor, VisualStrategyConfig } from './VisualEditor'
import { YamlEditor } from './YamlEditor'
import { PineScriptMode, PineScriptConfig } from './PineScriptMode'
import { strategyService } from '@/services/strategyService'
import { toast } from 'sonner'

type EditorMode = 'select' | 'visual' | 'yaml' | 'pinescript'

interface CreateStrategyModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function CreateStrategyModal({ isOpen, onClose, onSuccess }: CreateStrategyModalProps) {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<EditorMode>('select')

  // Visual editor mutation
  const createVisualMutation = useMutation({
    mutationFn: async (config: VisualStrategyConfig) => {
      // Create strategy
      const strategy = await strategyService.createStrategy({
        name: config.name,
        description: config.description,
        config_type: 'visual',
        symbols: config.symbols,
        timeframe: config.timeframe,
        bot_id: config.bot_id || undefined,
      })

      // Add indicators
      for (const indicator of config.indicators) {
        await strategyService.addIndicator(strategy.id, {
          indicator_type: indicator.type,
          parameters: indicator.parameters,
          order_index: indicator.order_index,
        })
      }

      // Add conditions
      for (const condition of config.conditions) {
        await strategyService.addCondition(strategy.id, {
          condition_type: condition.condition_type,
          conditions: condition.conditions,
          logic_operator: condition.logic_operator,
          order_index: condition.order_index,
        })
      }

      return strategy
    },
    onSuccess: () => {
      toast.success('Estrategia criada com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      handleClose()
      onSuccess?.()
    },
    onError: (error: Error) => {
      toast.error(`Erro ao criar estrategia: ${error.message}`)
    },
  })

  // YAML editor mutation
  const createYamlMutation = useMutation({
    mutationFn: async (yaml: string) => {
      // First create a basic strategy
      const strategy = await strategyService.createStrategy({
        name: 'Nova Estrategia YAML',
        config_type: 'yaml',
        config_yaml: yaml,
      })

      // Then apply the YAML config
      return strategyService.applyYamlConfig(strategy.id, yaml)
    },
    onSuccess: () => {
      toast.success('Estrategia YAML criada com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      handleClose()
      onSuccess?.()
    },
    onError: (error: Error) => {
      toast.error(`Erro ao criar estrategia: ${error.message}`)
    },
  })

  // PineScript mutation
  const createPineScriptMutation = useMutation({
    mutationFn: async (config: PineScriptConfig) => {
      return strategyService.createStrategy({
        name: config.name,
        description: config.description,
        config_type: 'pinescript',
        symbols: config.symbols.length > 0 ? config.symbols : undefined,
        pinescript_source: JSON.stringify({
          webhook_secret: config.webhook_secret,
          default_leverage: config.default_leverage,
          default_margin_pct: config.default_margin_pct,
        }),
      })
    },
    onSuccess: () => {
      toast.success('Estrategia PineScript criada com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      handleClose()
      onSuccess?.()
    },
    onError: (error: Error) => {
      toast.error(`Erro ao criar estrategia: ${error.message}`)
    },
  })

  const handleClose = () => {
    setMode('select')
    onClose()
  }

  if (!isOpen) return null

  const isSaving = createVisualMutation.isPending || createYamlMutation.isPending || createPineScriptMutation.isPending

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
      <Card className="w-full max-w-4xl bg-[#1e222d] border-[#2a2e39] my-8">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#2a2e39]">
          <h2 className="text-xl font-semibold text-white">
            {mode === 'select' && 'Criar Nova Estrategia'}
            {mode === 'visual' && 'Editor Visual'}
            {mode === 'yaml' && 'Editor YAML'}
            {mode === 'pinescript' && 'Integracao PineScript'}
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClose}
            className="text-gray-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Mode Selection */}
          {mode === 'select' && (
            <div className="space-y-6">
              <p className="text-gray-300 text-center">
                Escolha como deseja configurar sua estrategia de trading automatizada
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Visual Editor */}
                <button
                  onClick={() => setMode('visual')}
                  className="p-6 bg-[#131722] rounded-lg border-2 border-[#2a2e39] hover:border-emerald-500/50 transition-colors text-left group"
                >
                  <div className="w-12 h-12 bg-emerald-500/20 rounded-lg flex items-center justify-center mb-4 group-hover:bg-emerald-500/30 transition-colors">
                    <Settings className="w-6 h-6 text-emerald-400" />
                  </div>
                  <h3 className="text-white font-semibold mb-2">Editor Visual</h3>
                  <p className="text-gray-400 text-sm">
                    Interface grafica para selecionar indicadores e definir condicoes de forma intuitiva.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-1">
                    <span className="text-xs px-2 py-1 bg-emerald-500/10 text-emerald-300 rounded">Iniciante</span>
                    <span className="text-xs px-2 py-1 bg-blue-500/10 text-blue-300 rounded">Recomendado</span>
                  </div>
                </button>

                {/* YAML Editor */}
                <button
                  onClick={() => setMode('yaml')}
                  className="p-6 bg-[#131722] rounded-lg border-2 border-[#2a2e39] hover:border-purple-500/50 transition-colors text-left group"
                >
                  <div className="w-12 h-12 bg-purple-500/20 rounded-lg flex items-center justify-center mb-4 group-hover:bg-purple-500/30 transition-colors">
                    <Code className="w-6 h-6 text-purple-400" />
                  </div>
                  <h3 className="text-white font-semibold mb-2">Editor YAML</h3>
                  <p className="text-gray-400 text-sm">
                    Configure estrategias complexas usando codigo YAML com suporte a templates.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-1">
                    <span className="text-xs px-2 py-1 bg-purple-500/10 text-purple-300 rounded">Avancado</span>
                    <span className="text-xs px-2 py-1 bg-yellow-500/10 text-yellow-300 rounded">Flexivel</span>
                  </div>
                </button>

                {/* PineScript */}
                <button
                  onClick={() => setMode('pinescript')}
                  className="p-6 bg-[#131722] rounded-lg border-2 border-[#2a2e39] hover:border-orange-500/50 transition-colors text-left group"
                >
                  <div className="w-12 h-12 bg-orange-500/20 rounded-lg flex items-center justify-center mb-4 group-hover:bg-orange-500/30 transition-colors">
                    <Zap className="w-6 h-6 text-orange-400" />
                  </div>
                  <h3 className="text-white font-semibold mb-2">PineScript / TradingView</h3>
                  <p className="text-gray-400 text-sm">
                    Receba alertas do TradingView via webhook e execute automaticamente.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-1">
                    <span className="text-xs px-2 py-1 bg-orange-500/10 text-orange-300 rounded">Externo</span>
                    <span className="text-xs px-2 py-1 bg-cyan-500/10 text-cyan-300 rounded">TradingView</span>
                  </div>
                </button>
              </div>

              <div className="text-center pt-4">
                <Button variant="outline" onClick={handleClose} className="border-[#2a2e39] text-gray-400">
                  Cancelar
                </Button>
              </div>
            </div>
          )}

          {/* Visual Editor */}
          {mode === 'visual' && (
            <VisualEditor
              onSave={(config) => createVisualMutation.mutate(config)}
              onCancel={() => setMode('select')}
              isSaving={createVisualMutation.isPending}
            />
          )}

          {/* YAML Editor */}
          {mode === 'yaml' && (
            <YamlEditor
              onSave={(yaml) => createYamlMutation.mutate(yaml)}
              onCancel={() => setMode('select')}
              isSaving={createYamlMutation.isPending}
            />
          )}

          {/* PineScript Mode */}
          {mode === 'pinescript' && (
            <PineScriptMode
              strategyName=""
              onSave={(config) => createPineScriptMutation.mutate(config)}
              onCancel={() => setMode('select')}
              isSaving={createPineScriptMutation.isPending}
            />
          )}
        </div>
      </Card>
    </div>
  )
}
