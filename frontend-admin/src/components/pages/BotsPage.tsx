/**
 * BotsPage Component - ADMIN VERSION
 * Admin page to view and manage all bots with "Criar Bot" button
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, TrendingUp, Users, Activity, AlertCircle, Copy, Pause, Play, Check, Calculator, RefreshCw } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { adminService, Bot } from '@/services/adminService'
import { useAuth } from '@/contexts/AuthContext'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { CreateBotModal } from '@/components/molecules/CreateBotModal'
import { EditBotModal } from '@/components/molecules/EditBotModal'
import { BotSymbolConfigsModal } from '@/components/molecules/BotSymbolConfigsModal'
import { Settings } from 'lucide-react'
import { useNgrokUrl } from '@/hooks/useNgrokUrl'
import { toast } from 'sonner'

export function BotsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [isSymbolConfigsModalOpen, setIsSymbolConfigsModalOpen] = useState(false)
  const [botToEdit, setBotToEdit] = useState<Bot | null>(null)
  const [botForSymbolConfigs, setBotForSymbolConfigs] = useState<Bot | null>(null)
  const [botToDelete, setBotToDelete] = useState<Bot | null>(null)
  const [deleteMode, setDeleteMode] = useState<'archive' | 'permanent'>('archive')
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)
  const { data: ngrokUrl } = useNgrokUrl()

  // Set admin user ID
  useEffect(() => {
    if (user?.id) {
      adminService.setAdminUserId(user.id)
    }
  }, [user?.id])

  const { data: bots, isLoading, error } = useQuery({
    queryKey: ['adminBots', selectedStatus],
    queryFn: () => adminService.getAllBots(selectedStatus === 'all' ? undefined : selectedStatus),
    // refetchInterval desabilitado para performance
    enabled: !!user?.id,
  })

  const deleteMutation = useMutation({
    mutationFn: (botId: string) => adminService.deleteBot(botId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBots'] })
      toast.success('Bot arquivado com sucesso')
      setBotToDelete(null)
    },
    onError: (error: Error) => {
      toast.error(`Erro ao arquivar bot: ${error.message}`)
    },
  })

  const permanentDeleteMutation = useMutation({
    mutationFn: (botId: string) => adminService.permanentlyDeleteBot(botId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBots'] })
      toast.success('Bot excluído permanentemente')
      setBotToDelete(null)
    },
    onError: (error: Error) => {
      toast.error(`Erro ao excluir bot: ${error.message}`)
    },
  })

  const toggleStatusMutation = useMutation({
    mutationFn: ({ botId, newStatus }: { botId: string; newStatus: string }) =>
      adminService.updateBot(botId, { status: newStatus }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminBots'] })
      toast.success('Status do bot atualizado!')
    },
    onError: (error: Error) => {
      toast.error(`Erro ao atualizar status: ${error.message}`)
    },
  })

  const calculateMetricsMutation = useMutation({
    mutationFn: () => adminService.calculateBotMetrics(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['adminBots'] })
      toast.success(data.message || 'Métricas calculadas com sucesso!')
    },
    onError: (error: Error) => {
      toast.error(`Erro ao calcular métricas: ${error.message}`)
    },
  })

  const handleArchiveBot = (bot: Bot) => {
    setDeleteMode('archive')
    setBotToDelete(bot)
  }

  const handlePermanentDeleteBot = (bot: Bot) => {
    setDeleteMode('permanent')
    setBotToDelete(bot)
  }

  const handleEditBot = (bot: Bot) => {
    setBotToEdit(bot)
    setIsEditModalOpen(true)
  }

  const handleSymbolConfigs = (bot: Bot) => {
    setBotForSymbolConfigs(bot)
    setIsSymbolConfigsModalOpen(true)
  }

  const handleToggleStatus = (bot: Bot) => {
    const newStatus = bot.status === 'active' ? 'paused' : 'active'
    toggleStatusMutation.mutate({ botId: bot.id, newStatus })
  }

  const handleCopyWebhookUrl = (bot: Bot) => {
    const baseUrl = ngrokUrl || import.meta.env.VITE_API_URL || 'https://api.ominiiachain.com'
    const url = `${baseUrl}/api/v1/bots/webhook/master/${bot.master_webhook_path}`
    navigator.clipboard.writeText(url)
    setCopiedUrl(bot.id)
    toast.success('URL copiada!')
    setTimeout(() => setCopiedUrl(null), 2000)
  }

  const confirmDelete = () => {
    if (botToDelete) {
      if (deleteMode === 'permanent') {
        permanentDeleteMutation.mutate(botToDelete.id)
      } else {
        deleteMutation.mutate(botToDelete.id)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-3xl font-bold text-white mb-8">Bots</h1>
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
            <p>Erro ao carregar bots: {(error as Error).message}</p>
          </div>
        </Card>
      </div>
    )
  }

  const allBots = bots || []
  const activeBots = allBots.filter((b) => b.status === 'active').length
  const pausedBots = allBots.filter((b) => b.status === 'paused').length

  return (
    <div className="p-6 lg:p-8">
      {/* Header with "Criar Bot" button */}
      <div className="mb-8 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Bots</h1>
          <p className="text-gray-300">Gerenciar todos os bots de copy trading</p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => calculateMetricsMutation.mutate()}
            disabled={calculateMetricsMutation.isPending}
            className="flex items-center gap-2"
          >
            {calculateMetricsMutation.isPending ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <Calculator className="w-5 h-5" />
            )}
            {calculateMetricsMutation.isPending ? 'Calculando...' : 'Calcular Métricas'}
          </Button>
          <Button onClick={() => setIsCreateModalOpen(true)} className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Criar Bot
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300 mb-1">Total de Bots</p>
              <p className="text-3xl font-bold text-white">{allBots.length}</p>
            </div>
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Activity className="w-6 h-6 text-blue-400" />
            </div>
          </div>
        </Card>
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300 mb-1">Bots Ativos</p>
              <p className="text-3xl font-bold text-green-400">{activeBots}</p>
            </div>
            <div className="p-3 bg-green-500/20 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-400" />
            </div>
          </div>
        </Card>
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-300 mb-1">Bots Pausados</p>
              <p className="text-3xl font-bold text-orange-400">{pausedBots}</p>
            </div>
            <div className="p-3 bg-orange-500/20 rounded-lg">
              <Activity className="w-6 h-6 text-orange-400" />
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
          Todos ({allBots.length})
        </Button>
        <Button
          variant={selectedStatus === 'active' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedStatus('active')}
        >
          Ativos ({activeBots})
        </Button>
        <Button
          variant={selectedStatus === 'paused' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedStatus('paused')}
        >
          Pausados ({pausedBots})
        </Button>
      </div>

      {/* Bots Grid */}
      {allBots.length === 0 ? (
        <Card className="p-12 text-center bg-[#1e222d] border-[#2a2e39]">
          <Activity className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400 mb-4">Nenhum bot encontrado</p>
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Criar Primeiro Bot
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {allBots.map((bot) => {
            console.log('🔍 Rendering bot:', bot)
            console.log('🔍 Bot name:', bot.name)
            console.log('🔍 Bot description:', bot.description)
            return (
            <Card key={bot.id} className="p-6 hover:shadow-lg transition-shadow bg-[#1e222d] border-[#2a2e39]">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-cyan-400 mb-1">{bot.name}</h3>
                  <p className="text-sm text-gray-200 line-clamp-2">{bot.description}</p>
                </div>
                <Badge
                  variant={
                    bot.status === 'active'
                      ? 'success'
                      : bot.status === 'paused'
                      ? 'warning'
                      : 'default'
                  }
                >
                  {bot.status}
                </Badge>
              </div>

              {/* Win Rate e P&L Destacados */}
              <div className="grid grid-cols-2 gap-3 mb-4 p-3 bg-[#131722] rounded-lg">
                <div className="text-center">
                  <p className="text-xs text-gray-400 mb-1">Win Rate</p>
                  {bot.avg_win_rate !== null ? (
                    <p className={`text-xl font-bold ${bot.avg_win_rate >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                      {bot.avg_win_rate.toFixed(1)}%
                    </p>
                  ) : (
                    <p className="text-xl font-bold text-gray-500">-</p>
                  )}
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-400 mb-1">P&L Médio</p>
                  {bot.avg_pnl_pct !== null ? (
                    <p className={`text-xl font-bold ${bot.avg_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {bot.avg_pnl_pct >= 0 ? '+' : ''}{bot.avg_pnl_pct.toFixed(2)}%
                    </p>
                  ) : (
                    <p className="text-xl font-bold text-gray-500">-</p>
                  )}
                </div>
              </div>

              <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white">Tipo de Mercado</span>
                  <Badge variant="default" className="bg-green-500/30 text-green-300 border-green-500/50 font-semibold">{bot.market_type.toUpperCase()}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white flex items-center">
                    <Users className="w-4 h-4 mr-1 text-blue-400" />
                    Assinantes
                  </span>
                  <span className="font-semibold text-white">{bot.total_subscribers}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white">Sinais Enviados</span>
                  <span className="font-semibold text-yellow-300">{bot.total_signals_sent}</span>
                </div>
              </div>

              <div className="pt-4 border-t border-[#2a2e39] space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-white">Criado em</span>
                  <span className="text-white">{format(new Date(bot.created_at), 'dd/MM/yyyy', { locale: ptBR })}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-white">Webhook Path</span>
                  <code className="text-xs bg-[#2a2e39] text-cyan-300 px-2 py-1 rounded">
                    {bot.master_webhook_path}
                  </code>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-white">URL do Webhook</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={`${ngrokUrl || import.meta.env.VITE_API_URL || 'https://api.ominiiachain.com'}/api/v1/bots/webhook/master/${bot.master_webhook_path}`}
                      className="text-xs bg-[#131722] text-white border border-[#2a2e39] px-3 py-2 rounded flex-1 font-mono"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCopyWebhookUrl(bot)}
                      className="flex-shrink-0 px-2"
                    >
                      {copiedUrl === bot.id ? (
                        <Check className="w-4 h-4 text-green-600" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-2 mt-4">
                {/* Symbol Configs Button */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleSymbolConfigs(bot)}
                  className="w-full border-purple-600 text-purple-400 hover:bg-purple-900/30"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Config por Simbolo
                </Button>

                {/* Other Actions Row */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggleStatus(bot)}
                    className="flex-shrink-0 px-3 border-[#3a3f4b] text-white hover:bg-[#2a2e39]"
                    disabled={toggleStatusMutation.isPending}
                  >
                    {bot.status === 'active' ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEditBot(bot)}
                    className="flex-1 border-[#3a3f4b] text-white hover:bg-[#2a2e39]"
                  >
                    <Edit className="w-4 h-4 mr-1" />
                    Editar
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleArchiveBot(bot)}
                    className="text-orange-300 border-orange-400 hover:text-orange-200 hover:border-orange-300 hover:bg-orange-500/20"
                    title="Arquivar bot (pode ser reativado)"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePermanentDeleteBot(bot)}
                    className="text-red-300 border-red-400 hover:text-red-200 hover:border-red-300 hover:bg-red-500/20"
                    title="Excluir permanentemente"
                  >
                    <Trash2 className="w-4 h-4" />
                    Excluir
                  </Button>
                </div>
              </div>
            </Card>
            )
          })}
        </div>
      )}

      {/* Create Bot Modal */}
      <CreateBotModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['adminBots'] })
          setIsCreateModalOpen(false)
        }}
      />

      {/* Edit Bot Modal */}
      <EditBotModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false)
          setBotToEdit(null)
        }}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['adminBots'] })
          setIsEditModalOpen(false)
          setBotToEdit(null)
        }}
        bot={botToEdit}
      />

      {/* Symbol Configs Modal */}
      <BotSymbolConfigsModal
        isOpen={isSymbolConfigsModalOpen}
        onClose={() => {
          setIsSymbolConfigsModalOpen(false)
          setBotForSymbolConfigs(null)
        }}
        bot={botForSymbolConfigs}
      />

      {/* Delete Confirmation Modal */}
      {botToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full p-6 bg-[#1e222d] border-[#2a2e39]">
            <h3 className={`text-lg font-semibold mb-2 ${deleteMode === 'permanent' ? 'text-red-400' : 'text-orange-400'}`}>
              {deleteMode === 'permanent' ? '⚠️ Excluir Permanentemente' : 'Arquivar Bot'}
            </h3>
            <p className="text-gray-300 mb-4">
              {deleteMode === 'permanent' ? (
                <>
                  Tem certeza que deseja <strong className="text-red-400">EXCLUIR PERMANENTEMENTE</strong> o bot{' '}
                  <strong className="text-white">{botToDelete.name}</strong>?
                </>
              ) : (
                <>
                  Tem certeza que deseja arquivar o bot <strong className="text-white">{botToDelete.name}</strong>?
                </>
              )}
            </p>
            {deleteMode === 'permanent' && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4">
                <p className="text-red-300 text-sm">
                  <strong>ATENÇÃO:</strong> Esta ação irá remover:
                </p>
                <ul className="text-red-300 text-sm mt-2 list-disc list-inside">
                  <li>Todos os sinais enviados por este bot</li>
                  <li>Todas as execuções de sinais</li>
                  <li>Todas as assinaturas de usuários</li>
                  <li>O bot em si</li>
                </ul>
                <p className="text-red-400 text-sm mt-2 font-semibold">
                  Esta ação NÃO pode ser desfeita!
                </p>
              </div>
            )}
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setBotToDelete(null)}
                className="flex-1 border-[#2a2e39] text-gray-300 hover:bg-[#2a2e39]"
                disabled={deleteMutation.isPending || permanentDeleteMutation.isPending}
              >
                Cancelar
              </Button>
              <Button
                onClick={confirmDelete}
                className={`flex-1 ${deleteMode === 'permanent' ? 'bg-red-600 hover:bg-red-700' : 'bg-orange-500 hover:bg-orange-600'}`}
                disabled={deleteMutation.isPending || permanentDeleteMutation.isPending}
              >
                {deleteMutation.isPending || permanentDeleteMutation.isPending
                  ? (deleteMode === 'permanent' ? 'Excluindo...' : 'Arquivando...')
                  : (deleteMode === 'permanent' ? 'Excluir Permanentemente' : 'Arquivar')
                }
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
