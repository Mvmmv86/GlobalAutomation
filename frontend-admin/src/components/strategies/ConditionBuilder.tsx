/**
 * ConditionBuilder Component
 * Build entry/exit conditions for strategies
 */
import { useState } from 'react'
import { Plus, Trash2, ChevronDown } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { Label } from '@/components/atoms/Label'
import { Badge } from '@/components/atoms/Badge'
import { AVAILABLE_INDICATORS } from './IndicatorSelector'

export interface ConditionRule {
  left: string
  operator: string
  right: string
}

export interface ConditionConfig {
  id: string
  condition_type: 'entry_long' | 'entry_short' | 'exit_long' | 'exit_short'
  conditions: ConditionRule[]
  logic_operator: 'AND' | 'OR'
  order_index: number
}

const CONDITION_TYPES = [
  { value: 'entry_long', label: 'Entrada LONG', color: 'bg-green-500/20 text-green-300 border-green-500/50' },
  { value: 'entry_short', label: 'Entrada SHORT', color: 'bg-red-500/20 text-red-300 border-red-500/50' },
  { value: 'exit_long', label: 'Saida LONG', color: 'bg-blue-500/20 text-blue-300 border-blue-500/50' },
  { value: 'exit_short', label: 'Saida SHORT', color: 'bg-purple-500/20 text-purple-300 border-purple-500/50' },
]

const OPERATORS = [
  { value: '>', label: 'Maior que (>)' },
  { value: '<', label: 'Menor que (<)' },
  { value: '>=', label: 'Maior ou igual (>=)' },
  { value: '<=', label: 'Menor ou igual (<=)' },
  { value: '==', label: 'Igual a (==)' },
  { value: 'crosses_above', label: 'Cruza acima' },
  { value: 'crosses_below', label: 'Cruza abaixo' },
]

const PRICE_VALUES = [
  { value: 'close', label: 'Preco de Fechamento' },
  { value: 'open', label: 'Preco de Abertura' },
  { value: 'high', label: 'Maxima' },
  { value: 'low', label: 'Minima' },
  { value: 'volume', label: 'Volume' },
]

interface ConditionBuilderProps {
  conditions: ConditionConfig[]
  onChange: (conditions: ConditionConfig[]) => void
  availableIndicators: string[] // List of indicator types currently in the strategy
}

export function ConditionBuilder({ conditions, onChange, availableIndicators }: ConditionBuilderProps) {
  const [expandedCondition, setExpandedCondition] = useState<string | null>(null)
  const [showAddPanel, setShowAddPanel] = useState(false)

  // Build available values for left/right selectors
  const getAvailableValues = () => {
    const values = [...PRICE_VALUES]

    // Add indicator outputs
    availableIndicators.forEach(indType => {
      const indicator = AVAILABLE_INDICATORS.find(i => i.type === indType)
      if (indicator) {
        indicator.outputs.forEach(output => {
          values.push({
            value: `${indType}.${output}`,
            label: `${indicator.label} - ${output}`
          })
        })
      }
    })

    return values
  }

  const availableValues = getAvailableValues()

  const getConditionTypeInfo = (type: string) => {
    return CONDITION_TYPES.find(c => c.value === type)
  }

  const addCondition = (type: string) => {
    const newCondition: ConditionConfig = {
      id: `${type}_${Date.now()}`,
      condition_type: type as any,
      conditions: [{ left: 'close', operator: '<', right: '' }],
      logic_operator: 'AND',
      order_index: conditions.length,
    }
    onChange([...conditions, newCondition])
    setShowAddPanel(false)
    setExpandedCondition(newCondition.id)
  }

  const removeCondition = (id: string) => {
    const filtered = conditions.filter(c => c.id !== id)
    const reindexed = filtered.map((cond, idx) => ({ ...cond, order_index: idx }))
    onChange(reindexed)
  }

  const updateCondition = (id: string, updates: Partial<ConditionConfig>) => {
    onChange(conditions.map(cond => {
      if (cond.id === id) {
        return { ...cond, ...updates }
      }
      return cond
    }))
  }

  const addRule = (conditionId: string) => {
    onChange(conditions.map(cond => {
      if (cond.id === conditionId) {
        return {
          ...cond,
          conditions: [...cond.conditions, { left: 'close', operator: '<', right: '' }]
        }
      }
      return cond
    }))
  }

  const updateRule = (conditionId: string, ruleIndex: number, updates: Partial<ConditionRule>) => {
    onChange(conditions.map(cond => {
      if (cond.id === conditionId) {
        const newRules = [...cond.conditions]
        newRules[ruleIndex] = { ...newRules[ruleIndex], ...updates }
        return { ...cond, conditions: newRules }
      }
      return cond
    }))
  }

  const removeRule = (conditionId: string, ruleIndex: number) => {
    onChange(conditions.map(cond => {
      if (cond.id === conditionId) {
        const newRules = cond.conditions.filter((_, idx) => idx !== ruleIndex)
        return { ...cond, conditions: newRules }
      }
      return cond
    }))
  }

  return (
    <div className="space-y-4">
      {/* Current Conditions */}
      <div className="space-y-3">
        {conditions.length === 0 ? (
          <Card className="p-6 bg-[#131722] border-[#2a2e39] text-center">
            <ChevronDown className="w-8 h-8 text-gray-600 mx-auto mb-2" />
            <p className="text-gray-400 text-sm">Nenhuma condicao definida</p>
            <p className="text-gray-500 text-xs mt-1">Adicione condicoes de entrada e saida</p>
          </Card>
        ) : (
          conditions.map((condition) => {
            const typeInfo = getConditionTypeInfo(condition.condition_type)
            const isExpanded = expandedCondition === condition.id

            return (
              <Card key={condition.id} className="p-4 bg-[#131722] border-[#2a2e39]">
                <div
                  className="flex items-center justify-between cursor-pointer"
                  onClick={() => setExpandedCondition(isExpanded ? null : condition.id)}
                >
                  <div className="flex items-center gap-3">
                    <Badge variant="default" className={typeInfo?.color}>
                      {typeInfo?.label}
                    </Badge>
                    <span className="text-gray-400 text-sm">
                      {condition.conditions.length} regra(s) - {condition.logic_operator}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        removeCondition(condition.id)
                      }}
                      className="p-1 h-7 w-7 text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Expanded Rules */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-[#2a2e39] space-y-4">
                    {/* Logic Operator */}
                    <div className="flex items-center gap-2">
                      <Label className="text-xs text-gray-400">Operador Logico:</Label>
                      <div className="flex gap-2">
                        <Button
                          variant={condition.logic_operator === 'AND' ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => updateCondition(condition.id, { logic_operator: 'AND' })}
                          className="h-7 text-xs"
                        >
                          AND (Todas)
                        </Button>
                        <Button
                          variant={condition.logic_operator === 'OR' ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => updateCondition(condition.id, { logic_operator: 'OR' })}
                          className="h-7 text-xs"
                        >
                          OR (Qualquer)
                        </Button>
                      </div>
                    </div>

                    {/* Rules */}
                    <div className="space-y-2">
                      {condition.conditions.map((rule, ruleIdx) => (
                        <div key={ruleIdx} className="flex items-center gap-2 p-2 bg-[#1e222d] rounded-lg">
                          {ruleIdx > 0 && (
                            <span className="text-xs text-gray-500 w-8">{condition.logic_operator}</span>
                          )}
                          {ruleIdx === 0 && <span className="text-xs text-gray-500 w-8">SE</span>}

                          {/* Left Value */}
                          <select
                            value={rule.left}
                            onChange={(e) => updateRule(condition.id, ruleIdx, { left: e.target.value })}
                            className="flex-1 bg-[#131722] border border-[#2a2e39] text-white text-sm rounded px-2 py-1"
                          >
                            {availableValues.map(v => (
                              <option key={v.value} value={v.value}>{v.label}</option>
                            ))}
                          </select>

                          {/* Operator */}
                          <select
                            value={rule.operator}
                            onChange={(e) => updateRule(condition.id, ruleIdx, { operator: e.target.value })}
                            className="bg-[#131722] border border-[#2a2e39] text-white text-sm rounded px-2 py-1"
                          >
                            {OPERATORS.map(op => (
                              <option key={op.value} value={op.value}>{op.label}</option>
                            ))}
                          </select>

                          {/* Right Value */}
                          <select
                            value={rule.right}
                            onChange={(e) => updateRule(condition.id, ruleIdx, { right: e.target.value })}
                            className="flex-1 bg-[#131722] border border-[#2a2e39] text-white text-sm rounded px-2 py-1"
                          >
                            <option value="">Selecionar...</option>
                            {availableValues.map(v => (
                              <option key={v.value} value={v.value}>{v.label}</option>
                            ))}
                            <option value="__custom__">Valor customizado</option>
                          </select>

                          {/* Custom value input */}
                          {rule.right === '__custom__' && (
                            <Input
                              type="number"
                              placeholder="Valor"
                              onChange={(e) => updateRule(condition.id, ruleIdx, { right: e.target.value })}
                              className="w-20 bg-[#131722] border-[#2a2e39] text-white h-7 text-sm"
                            />
                          )}

                          {/* Remove rule */}
                          {condition.conditions.length > 1 && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeRule(condition.id, ruleIdx)}
                              className="p-1 h-7 w-7 text-red-400 hover:text-red-300"
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>

                    {/* Add Rule Button */}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => addRule(condition.id)}
                      className="w-full border-dashed border-[#3a3f4b] text-gray-400"
                    >
                      <Plus className="w-3 h-3 mr-1" />
                      Adicionar Regra
                    </Button>
                  </div>
                )}
              </Card>
            )
          })
        )}
      </div>

      {/* Add Condition Button */}
      {!showAddPanel ? (
        <Button
          variant="outline"
          onClick={() => setShowAddPanel(true)}
          className="w-full border-dashed border-[#3a3f4b] text-gray-300 hover:bg-[#2a2e39]"
        >
          <Plus className="w-4 h-4 mr-2" />
          Adicionar Condicao
        </Button>
      ) : (
        <Card className="p-4 bg-[#131722] border-[#2a2e39]">
          <div className="flex justify-between items-center mb-3">
            <p className="text-white font-medium">Tipo de Condicao</p>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAddPanel(false)}
              className="text-gray-400"
            >
              Cancelar
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {CONDITION_TYPES.map(type => {
              const alreadyExists = conditions.some(c => c.condition_type === type.value)
              return (
                <button
                  key={type.value}
                  onClick={() => !alreadyExists && addCondition(type.value)}
                  disabled={alreadyExists}
                  className={`
                    p-3 rounded-lg text-center transition-colors
                    ${alreadyExists
                      ? 'bg-[#1e222d] opacity-50 cursor-not-allowed'
                      : 'bg-[#1e222d] hover:bg-[#2a2e39] cursor-pointer'
                    }
                  `}
                >
                  <Badge variant="default" className={type.color}>
                    {type.label}
                  </Badge>
                  {alreadyExists && (
                    <span className="text-xs text-yellow-500 block mt-1">Ja existe</span>
                  )}
                </button>
              )
            })}
          </div>
        </Card>
      )}

      {/* Warning if no indicators */}
      {availableIndicators.length === 0 && (
        <div className="p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
          <p className="text-yellow-300 text-sm">
            Adicione indicadores primeiro para poder criar condicoes baseadas neles.
          </p>
        </div>
      )}
    </div>
  )
}
