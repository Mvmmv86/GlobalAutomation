/**
 * AdminExchangesPage Component
 * Admin page to view all exchange accounts with metrics
 */
import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Building2, CheckCircle, XCircle, Users, Activity, AlertCircle } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Badge } from '@/components/atoms/Badge'
import { adminService, ExchangesAdminData } from '@/services/adminService'
import { useAuth } from '@/contexts/AuthContext'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export function AdminExchangesPage() {
  const { user } = useAuth()

  // Set admin user ID
  useEffect(() => {
    if (user?.id) {
      adminService.setAdminUserId(user.id)
    }
  }, [user?.id])

  const { data, isLoading, error } = useQuery<ExchangesAdminData>({
    queryKey: ['adminExchanges'],
    queryFn: () => adminService.getAllExchanges(),
    // refetchInterval desabilitado para performance
    enabled: !!user?.id,
  })

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-3xl font-bold text-white mb-8">Exchanges</h1>
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
            <p>Erro ao carregar exchanges: {(error as Error).message}</p>
          </div>
        </Card>
      </div>
    )
  }

  const stats = data?.stats || {}
  const breakdown = data?.breakdown || []
  const exchanges = data?.exchanges || []

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Exchanges</h1>
        <p className="text-gray-400">Gerenciar todas as exchanges conectadas pelos usuários</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Total de Contas</p>
              <p className="text-3xl font-bold text-white">{stats.total || 0}</p>
            </div>
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Building2 className="w-6 h-6 text-blue-400" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Contas Ativas</p>
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
              <p className="text-sm text-gray-400 mb-1">Contas Inativas</p>
              <p className="text-3xl font-bold text-red-400">{stats.inactive || 0}</p>
            </div>
            <div className="p-3 bg-red-500/20 rounded-lg">
              <XCircle className="w-6 h-6 text-red-400" />
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-[#1e222d] border-[#2a2e39]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400 mb-1">Usuários com Exchanges</p>
              <p className="text-3xl font-bold text-purple-400">{stats.users_with_exchanges || 0}</p>
            </div>
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Users className="w-6 h-6 text-purple-400" />
            </div>
          </div>
        </Card>
      </div>

      {/* Exchange Breakdown */}
      {breakdown.length > 0 && (
        <Card className="p-6 bg-[#1e222d] border-[#2a2e39] mb-8">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
            <Activity className="w-5 h-5 mr-2 text-emerald-400" />
            Distribuição por Exchange
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {breakdown.map((item) => (
              <div
                key={item.exchange}
                className="bg-[#2a2e39] rounded-lg p-4 text-center"
              >
                <p className="text-lg font-bold text-white capitalize">{item.exchange}</p>
                <p className="text-2xl font-bold text-emerald-400">{item.count}</p>
                <p className="text-xs text-gray-400">
                  {item.active_count} ativas
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Exchanges Table */}
      <Card className="bg-[#1e222d] border-[#2a2e39] overflow-hidden">
        <div className="p-6 border-b border-[#2a2e39]">
          <h3 className="text-lg font-semibold text-white">Lista de Exchanges Conectadas</h3>
        </div>

        {exchanges.length === 0 ? (
          <div className="p-12 text-center">
            <Building2 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400">Nenhuma exchange conectada</p>
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
                    Exchange
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Nome da Conta
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Modo
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                    Criado em
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#2a2e39]">
                {exchanges.map((exchange) => (
                  <tr key={exchange.id} className="hover:bg-[#2a2e39]/50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-white font-medium">{exchange.user_name}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-gray-400">{exchange.user_email}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant="default" className="capitalize bg-blue-500/20 text-blue-400 border-blue-500/30">
                        {exchange.exchange}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-gray-300">{exchange.account_name}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={exchange.is_active ? 'success' : 'destructive'}>
                        {exchange.is_active ? 'Ativa' : 'Inativa'}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={exchange.testnet ? 'warning' : 'success'}>
                        {exchange.testnet ? 'Testnet' : 'Produção'}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-400 text-sm">
                      {format(new Date(exchange.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
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
