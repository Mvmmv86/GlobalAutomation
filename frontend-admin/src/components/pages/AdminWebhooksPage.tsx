/**
 * AdminWebhooksPage Component
 * Admin page to view all webhooks with metrics
 */
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Webhook, CheckCircle, XCircle, Pause, Users, Activity, AlertCircle, Send, CheckCheck, XOctagon } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Badge } from '@/components/atoms/Badge'
import { adminService, WebhooksAdminData } from '@/services/adminService'
import { useAuth } from '@/contexts/AuthContext'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export function AdminWebhooksPage() {
  const { user } = useAuth()

  // Set admin user ID
  useEffect(() => {
    if (user?.id) {
      adminService.setAdminUserId(user.id)
    }
  }, [user?.id])

  const { data, isLoading, error } = useQuery<WebhooksAdminData>({
    queryKey: ['adminWebhooks'],
    queryFn: () => adminService.getAllWebhooks(),
    // refetchInterval desabilitado para performance
    enabled: !!user?.id,
  })

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-3xl font-bold text-white mb-8">Webhooks</h1>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="p-6 animate-pulse bg-[#1e222d]">
              <div className="h-6 bg-gray-700 rounded mb-4" />
              <div className="h-8 bg-gray-700 rounded" />
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
            <p>Erro ao carregar webhooks: {(error as Error).message}</p>
          </div>
        </Card>
      </div>
    )
  }

  const stats = data?.stats || {}
  const breakdown = data?.breakdown || []
  const webhooks = data?.webhooks || []

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Ativo</Badge>
      case 'paused':
        return <Badge variant="warning">Pausado</Badge>
      case 'disabled':
      case 'error':
        return <Badge variant="destructive">Inativo</Badge>
      default:
        return <Badge variant="default">{status}</Badge>
    }
  }

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Webhooks</h1>
        <p className="text-gray-400">Gerenciar todos os webhooks configurados pelos usuários</p>
      </div>

      {/* Stats Cards - Row 1 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Total de Webhooks</p>
              <p className="text-3xl font-bold text-white">{stats.total || 0}</p>
            </div>
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Webhook className="w-6 h-6 text-blue-400" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Webhooks Ativos</p>
              <p className="text-3xl font-bold text-emerald-400">{stats.active || 0}</p>
            </div>
            <div className="p-3 bg-emerald-500/20 rounded-lg">
              <CheckCircle className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Webhooks Pausados</p>
              <p className="text-3xl font-bold text-orange-400">{stats.paused || 0}</p>
            </div>
            <div className="p-3 bg-orange-500/20 rounded-lg">
              <Pause className="w-6 h-6 text-orange-400" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Usuários com Webhooks</p>
              <p className="text-3xl font-bold text-purple-400">{stats.users_with_webhooks || 0}</p>
            </div>
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Users className="w-6 h-6 text-purple-400" />
            </div>
          </div>
        </Card>
      </div>

      {/* Stats Cards - Row 2 (Deliveries) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Total de Entregas</p>
              <p className="text-3xl font-bold text-white">{stats.total_deliveries?.toLocaleString() || 0}</p>
            </div>
            <div className="p-3 bg-cyan-500/20 rounded-lg">
              <Send className="w-6 h-6 text-cyan-400" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Entregas com Sucesso</p>
              <p className="text-3xl font-bold text-emerald-400">{stats.successful_deliveries?.toLocaleString() || 0}</p>
            </div>
            <div className="p-3 bg-emerald-500/20 rounded-lg">
              <CheckCheck className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Entregas Falharam</p>
              <p className="text-3xl font-bold text-red-400">{stats.failed_deliveries?.toLocaleString() || 0}</p>
            </div>
            <div className="p-3 bg-red-500/20 rounded-lg">
              <XOctagon className="w-6 h-6 text-red-400" />
            </div>
          </div>
        </Card>
      </div>

      {/* Market Type Breakdown */}
      {breakdown.length > 0 && (
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39] mb-8">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-emerald-400" />
            Distribuição por Tipo de Mercado
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {breakdown.map((item) => (
              <div
                key={item.market_type}
                className="bg-[#2a2e39] rounded-lg p-4 text-center"
              >
                <p className="text-lg font-bold text-white uppercase">{item.market_type}</p>
                <p className="text-2xl font-bold text-emerald-400">{item.count}</p>
                <p className="text-xs text-gray-400">
                  {item.active_count} ativos
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Webhooks Table */}
      <Card className="bg-[#1e222d] border-[#2a2e39] overflow-hidden">
        <div className="p-6 border-b border-[#2a2e39]">
          <h3 className="text-lg font-semibold text-white">Lista de Webhooks</h3>
        </div>

        {webhooks.length === 0 ? (
          <div className="p-12 text-center">
            <Webhook className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">Nenhum webhook configurado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#2a2e39]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Usuário
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Nome do Webhook
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Entregas
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Sucesso
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Criado em
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a2e39]">
                {webhooks.map((webhook) => (
                  <tr key={webhook.id} className="hover:bg-[#2a2e39]/50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-white font-medium">{webhook.user_name}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-gray-400">{webhook.user_email}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-gray-300">{webhook.name}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant="default" className="uppercase bg-purple-500/20 text-purple-400 border-purple-500/30">
                        {webhook.market_type || 'N/A'}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(webhook.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-white font-medium">{webhook.total_deliveries}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="text-emerald-400">{webhook.successful_deliveries}</span>
                        <span className="text-gray-600">/</span>
                        <span className="text-red-400">{webhook.failed_deliveries}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400 text-sm">
                      {format(new Date(webhook.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
