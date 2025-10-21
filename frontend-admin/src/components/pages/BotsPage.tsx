/**
 * BotsPage Component - ADMIN VERSION
 * Admin page to view and manage all bots with "Criar Bot" button
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, TrendingUp, Users, Activity, AlertCircle, Copy, Pause, Play, Check } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { adminService, Bot } from '@/services/adminService'
import { useAuth } from '@/contexts/AuthContext'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { CreateBotModal } from '@/components/molecules/CreateBotModal'
import { EditBotModal } from '@/components/molecules/EditBotModal'
import { useNgrokUrl } from '@/hooks/useNgrokUrl'
import { toast } from 'sonner'

export function BotsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [botToEdit, setBotToEdit] = useState<Bot | null>(null)
  const [botToDelete, setBotToDelete] = useState<Bot | null>(null)
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
    refetchInterval: 30000,
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

  const handleDeleteBot = (bot: Bot) => {
    setBotToDelete(bot)
  }

  const handleEditBot = (bot: Bot) => {
    setBotToEdit(bot)
    setIsEditModalOpen(true)
  }

  const handleToggleStatus = (bot: Bot) => {
    const newStatus = bot.status === 'active' ? 'paused' : 'active'
    toggleStatusMutation.mutate({ botId: bot.id, newStatus })
  }

  const handleCopyWebhookUrl = (bot: Bot) => {
    const baseUrl = ngrokUrl || import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const url = `${baseUrl}/api/v1/bots/webhook/master/${bot.master_webhook_path}`
    navigator.clipboard.writeText(url)
    setCopiedUrl(bot.id)
    toast.success('URL copiada!')
    setTimeout(() => setCopiedUrl(null), 2000)
  }

  const confirmDelete = () => {
    if (botToDelete) {
      deleteMutation.mutate(botToDelete.id)
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Bots</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="p-6 animate-pulse">
              <div className="h-6 bg-gray-200 rounded mb-4" />
              <div className="h-4 bg-gray-200 rounded mb-2" />
              <div className="h-4 bg-gray-200 rounded w-2/3" />
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 lg:p-8">
        <Card className="p-6 bg-red-50 border-red-200">
          <div className="flex items-center text-red-800">
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Bots</h1>
          <p className="text-gray-600">Gerenciar todos os bots de copy trading</p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)} className="flex items-center gap-2">
          <Plus className="w-5 h-5" />
          Criar Bot
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Total de Bots</p>
              <p className="text-3xl font-bold text-gray-900">{allBots.length}</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg">
              <Activity className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Bots Ativos</p>
              <p className="text-3xl font-bold text-green-600">{activeBots}</p>
            </div>
            <div className="p-3 bg-green-50 rounded-lg">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </Card>
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Bots Pausados</p>
              <p className="text-3xl font-bold text-orange-600">{pausedBots}</p>
            </div>
            <div className="p-3 bg-orange-50 rounded-lg">
              <Activity className="w-6 h-6 text-orange-600" />
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
        <Card className="p-12 text-center">
          <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500 mb-4">Nenhum bot encontrado</p>
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
            <Card key={bot.id} className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 mb-1">{bot.name}</h3>
                  <p className="text-sm text-gray-600 line-clamp-2">{bot.description}</p>
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

              <div className="space-y-3 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Tipo de Mercado</span>
                  <Badge variant="default">{bot.market_type.toUpperCase()}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 flex items-center">
                    <Users className="w-4 h-4 mr-1" />
                    Assinantes
                  </span>
                  <span className="font-semibold text-gray-900">{bot.total_subscribers}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Sinais Enviados</span>
                  <span className="font-semibold text-gray-900">{bot.total_signals_sent}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Win Rate</span>
                  {bot.avg_win_rate !== null ? (
                    <Badge variant={bot.avg_win_rate >= 50 ? 'success' : 'warning'}>
                      {bot.avg_win_rate.toFixed(1)}%
                    </Badge>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">P&L Médio</span>
                  {bot.avg_pnl_pct !== null ? (
                    <span
                      className={`font-semibold ${
                        bot.avg_pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {bot.avg_pnl_pct >= 0 ? '+' : ''}
                      {bot.avg_pnl_pct.toFixed(2)}%
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-gray-200 space-y-2">
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Criado em</span>
                  <span>{format(new Date(bot.created_at), 'dd/MM/yyyy', { locale: ptBR })}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Webhook Path</span>
                  <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                    {bot.master_webhook_path}
                  </code>
                </div>
                <div className="space-y-1">
                  <span className="text-xs text-gray-500">URL do Webhook</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={`${ngrokUrl || import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/bots/webhook/master/${bot.master_webhook_path}`}
                      className="text-xs bg-white text-black border border-gray-300 px-3 py-2 rounded flex-1 font-mono"
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

              <div className="flex gap-2 mt-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleToggleStatus(bot)}
                  className="flex-shrink-0 px-3"
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
                  className="flex-1"
                >
                  <Edit className="w-4 h-4 mr-1" />
                  Editar
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDeleteBot(bot)}
                  className="flex-1 text-red-600 hover:text-red-700 hover:border-red-300"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Arquivar
                </Button>
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

      {/* Delete Confirmation Modal */}
      {botToDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Arquivar Bot</h3>
            <p className="text-gray-600 mb-6">
              Tem certeza que deseja arquivar o bot <strong>{botToDelete.name}</strong>? Esta ação
              não pode ser desfeita.
            </p>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => setBotToDelete(null)}
                className="flex-1"
                disabled={deleteMutation.isPending}
              >
                Cancelar
              </Button>
              <Button
                onClick={confirmDelete}
                className="flex-1 bg-red-600 hover:bg-red-700"
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Arquivando...' : 'Arquivar'}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
