/**
 * StrategiesPage Component - ADMIN VERSION
 * Admin page to view and manage automated trading strategies
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  Trash2,
  Activity,
  AlertCircle,
  Play,
  Pause,
  Settings,
  Zap,
  Clock,
  BarChart3,
  Code,
  Eye,
  TestTube,
  Pencil
} from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { strategyService, StrategyWithStats, INDICATOR_TYPES, TIMEFRAMES } from '@/services/strategyService'
import { CreateStrategyModal } from '@/components/strategies/CreateStrategyModal'
import { EditStrategyModal } from '@/components/strategies/EditStrategyModal'
import { BacktestPanel } from '@/components/strategies/BacktestPanel'
import { StrategyDetailsModal } from '@/components/strategies/StrategyDetailsModal'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { toast } from 'sonner'

export function StrategiesPage() {
  const queryClient = useQueryClient()
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [strategyToDelete, setStrategyToDelete] = useState<StrategyWithStats | null>(null)
  const [strategyToView, setStrategyToView] = useState<string | null>(null)
  const [strategyToBacktest, setStrategyToBacktest] = useState<StrategyWithStats | null>(null)
  const [strategyToEdit, setStrategyToEdit] = useState<string | null>(null)

  // Fetch strategies
  const { data, isLoading, error } = useQuery({
    queryKey: ['strategies', selectedStatus],
    queryFn: () => strategyService.getStrategies({
      active_only: selectedStatus === 'active'
    }),
    // refetchInterval desabilitado para performance
  })

  // Toggle status mutation
  const toggleStatusMutation = useMutation({
    mutationFn: async ({ strategyId, isActive }: { strategyId: string; isActive: boolean }) => {
      if (isActive) {
        return strategyService.deactivateStrategy(strategyId)
      } else {
        return strategyService.activateStrategy(strategyId)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      toast.success('Status da estrategia atualizado!')
    },
    onError: (error: Error) => {
      toast.error(`Erro ao atualizar status: ${error.message}`)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (strategyId: string) => strategyService.deleteStrategy(strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      toast.success('Estrategia excluida com sucesso')
      setStrategyToDelete(null)
    },
    onError: (error: Error) => {
      toast.error(`Erro ao excluir estrategia: ${error.message}`)
    },
  })

  const handleToggleStatus = (strategy: StrategyWithStats) => {
    toggleStatusMutation.mutate({
      strategyId: strategy.strategy.id,
      isActive: strategy.strategy.is_active
    })
  }

  const handleDeleteStrategy = (strategy: StrategyWithStats) => {
    setStrategyToDelete(strategy)
  }

  const confirmDelete = () => {
    if (strategyToDelete) {
      deleteMutation.mutate(strategyToDelete.strategy.id)
    }
  }

  const getIndicatorLabel = (type: string): string => {
    const indicator = INDICATOR_TYPES.find(i => i.value === type)
    return indicator?.label || type
  }

  const getTimeframeLabel = (value: string): string => {
    const tf = TIMEFRAMES.find(t => t.value === value)
    return tf?.label || value
  }

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-3xl font-bold text-white mb-8">Estrategias</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="p-6 animate-pulse bg-[#1e222d] border-[#2a2e39]">
              <div className="h-6 bg-gray-700 rounded mb-4" />
              <div className="h-4 bg-gray-700 rounded mb-2" />
              <div className="h-4 bg-gray-700 rounded w-2/3" />
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 lg:p-8">
        <Card className="p-6 bg-red-900/30 border-red-700">
          <div className="flex items-center text-red-300">
            <AlertCircle className="w-5 h-5 mr-2" />
            <p>Erro ao carregar estrategias: {(error as Error).message}</p>
          </div>
        </Card>
      </div>
    )
  }

  const strategies = data?.strategies || []
  const filteredStrategies = selectedStatus === 'all'
    ? strategies
    : strategies.filter(s => selectedStatus === 'active' ? s.strategy.is_active : !s.strategy.is_active)

  const activeStrategies = strategies.filter(s => s.strategy.is_active).length
  const inactiveStrategies = strategies.filter(s => !s.strategy.is_active).length
  const totalSignalsToday = strategies.reduce((sum, s) => sum + s.signals_today, 0)

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Estrategias Automatizadas</h1>
          <p className="text-gray-300">Gerenciar estrategias de trading com indicadores tecnicos</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)} className="flex items-center gap-2">
          <Plus className="w-5 h-5" />
          Criar Estrategia
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300 mb-1">Total de Estrategias</p>
              <p className="text-3xl font-bold text-white">{strategies.length}</p>
            </div>
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Settings className="w-6 h-6 text-blue-400" />
            </div>
          </div>
        </Card>
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300 mb-1">Ativas</p>
              <p className="text-3xl font-bold text-green-400">{activeStrategies}</p>
            </div>
            <div className="p-3 bg-green-500/20 rounded-lg">
              <Activity className="w-6 h-6 text-green-400" />
            </div>
          </div>
        </Card>
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300 mb-1">Inativas</p>
              <p className="text-3xl font-bold text-orange-400">{inactiveStrategies}</p>
            </div>
            <div className="p-3 bg-orange-500/20 rounded-lg">
              <Pause className="w-6 h-6 text-orange-400" />
            </div>
          </div>
        </Card>
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300 mb-1">Sinais Hoje</p>
              <p className="text-3xl font-bold text-cyan-400">{totalSignalsToday}</p>
            </div>
            <div className="p-3 bg-cyan-500/20 rounded-lg">
              <Zap className="w-6 h-6 text-cyan-400" />
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-2">
        <Button
          variant={selectedStatus === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedStatus('all')}
        >
          Todas ({strategies.length})
        </Button>
        <Button
          variant={selectedStatus === 'active' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedStatus('active')}
        >
          Ativas ({activeStrategies})
        </Button>
        <Button
          variant={selectedStatus === 'inactive' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedStatus('inactive')}
        >
          Inativas ({inactiveStrategies})
        </Button>
      </div>

      {/* Strategies Grid */}
      {filteredStrategies.length === 0 ? (
        <Card className="p-12 text-center bg-[#1e222d] border-[#2a2e39]">
          <BarChart3 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 mb-4">Nenhuma estrategia encontrada</p>
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Criar Primeira Estrategia
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredStrategies.map((item) => {
            const strategy = item.strategy
            const symbols = Array.isArray(strategy.symbols) ? strategy.symbols : []

            return (
              <Card key={strategy.id} className="p-6 hover:shadow-lg transition-shadow bg-[#1e222d] border-[#2a2e39]">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-cyan-400 mb-1">{strategy.name}</h3>
                    <p className="text-sm text-gray-200 line-clamp-2">
                      {strategy.description || 'Sem descricao'}
                    </p>
                  </div>
                  <Badge
                    variant={strategy.is_active ? 'success' : 'default'}
                  >
                    {strategy.is_active ? 'Ativa' : 'Inativa'}
                  </Badge>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 mb-4 p-3 bg-[#131722] rounded-lg">
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Sinais Hoje</p>
                    <p className="text-xl font-bold text-yellow-400">{item.signals_today}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-gray-400 mb-1">Executados</p>
                    <p className="text-xl font-bold text-green-400">{item.total_executed}</p>
                  </div>
                </div>

                {/* Info */}
                <div className="space-y-3 mb-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-white flex items-center">
                      <Clock className="w-4 h-4 mr-1 text-blue-400" />
                      Timeframe
                    </span>
                    <Badge variant="default" className="bg-blue-500/30 text-blue-300 border-blue-500/50">
                      {getTimeframeLabel(strategy.timeframe)}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-white flex items-center">
                      <Code className="w-4 h-4 mr-1 text-purple-400" />
                      Tipo
                    </span>
                    <Badge variant="default" className="bg-purple-500/30 text-purple-300 border-purple-500/50">
                      {strategy.config_type}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-white">Simbolos</span>
                    <span className="text-gray-300 text-xs">
                      {symbols.length > 0 ? symbols.slice(0, 2).join(', ') : '-'}
                      {symbols.length > 2 && ` +${symbols.length - 2}`}
                    </span>
                  </div>
                </div>

                {/* Indicators */}
                {item.indicators.length > 0 && (
                  <div className="mb-4">
                    <p className="text-xs text-gray-400 mb-2">Indicadores</p>
                    <div className="flex flex-wrap gap-1">
                      {item.indicators.map((ind, idx) => (
                        <Badge
                          key={idx}
                          variant="default"
                          className="text-xs bg-emerald-500/20 text-emerald-300 border-emerald-500/50"
                        >
                          {getIndicatorLabel(ind)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Footer */}
                <div className="pt-4 border-t border-[#2a2e39]">
                  <div className="flex items-center justify-between text-xs mb-3">
                    <span className="text-gray-400">Criada em</span>
                    <span className="text-gray-300">
                      {format(new Date(strategy.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggleStatus(item)}
                    className="flex-shrink-0 px-3 border-[#3a3f4b] text-white hover:bg-[#2a2e39]"
                    disabled={toggleStatusMutation.isPending}
                  >
                    {strategy.is_active ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setStrategyToBacktest(item)}
                    className="flex-shrink-0 px-3 border-[#3a3f4b] text-cyan-300 hover:bg-cyan-500/20"
                    title="Backtest"
                  >
                    <TestTube className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setStrategyToEdit(strategy.id)}
                    className="flex-shrink-0 px-3 border-[#3a3f4b] text-yellow-300 hover:bg-yellow-500/20"
                    title="Editar"
                  >
                    <Pencil className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setStrategyToView(strategy.id)}
                    className="flex-1 border-[#3a3f4b] text-white hover:bg-[#2a2e39]"
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    Detalhes
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteStrategy(item)}
                    className="text-red-300 border-red-400 hover:text-red-200 hover:border-red-300 hover:bg-red-500/20"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {strategyToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full p-6 bg-[#1e222d] border-[#2a2e39]">
            <h3 className="text-lg font-semibold text-red-400 mb-2">Excluir Estrategia</h3>
            <p className="text-gray-300 mb-4">
              Tem certeza que deseja excluir a estrategia{' '}
              <strong className="text-white">{strategyToDelete.strategy.name}</strong>?
            </p>
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4">
              <p className="text-red-300 text-sm">
                <strong>ATENCAO:</strong> Esta acao ira remover:
              </p>
              <ul className="text-red-300 text-sm mt-2 list-disc list-inside">
                <li>Todos os indicadores configurados</li>
                <li>Todas as condicoes de entrada/saida</li>
                <li>Todos os sinais gerados</li>
              </ul>
              <p className="text-red-400 text-sm mt-2 font-semibold">
                Esta acao NAO pode ser desfeita!
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setStrategyToDelete(null)}
                className="flex-1 border-[#2a2e39] text-gray-300 hover:bg-[#2a2e39]"
                disabled={deleteMutation.isPending}
              >
                Cancelar
              </Button>
              <Button
                onClick={confirmDelete}
                className="flex-1 bg-red-600 hover:bg-red-700"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Excluindo...' : 'Excluir'}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Create Strategy Modal */}
      <CreateStrategyModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      {/* View Details Modal - Enhanced with Tabs */}
      {strategyToView && (
        <StrategyDetailsModal
          strategyId={strategyToView}
          onClose={() => setStrategyToView(null)}
        />
      )}

      {/* Backtest Panel Modal */}
      {strategyToBacktest && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
          <Card className="w-full max-w-4xl bg-[#1e222d] border-[#2a2e39] my-8">
            <div className="flex items-center justify-between p-4 border-b border-[#2a2e39]">
              <h2 className="text-xl font-semibold text-white">
                Backtest - {strategyToBacktest.strategy.name}
              </h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStrategyToBacktest(null)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </Button>
            </div>
            <div className="p-6">
              <BacktestPanel
                strategyId={strategyToBacktest.strategy.id}
                strategyName={strategyToBacktest.strategy.name}
                symbols={Array.isArray(strategyToBacktest.strategy.symbols) ? strategyToBacktest.strategy.symbols : []}
              />
            </div>
          </Card>
        </div>
      )}

      {/* Edit Strategy Modal */}
      {strategyToEdit && (
        <EditStrategyModal
          strategyId={strategyToEdit}
          isOpen={!!strategyToEdit}
          onClose={() => setStrategyToEdit(null)}
        />
      )}
    </div>
  )
}

