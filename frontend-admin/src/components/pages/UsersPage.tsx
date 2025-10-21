/**
 * UsersPage Component
 * Admin page to view and manage all users
 */
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Eye, Building2, Bot, Webhook, AlertCircle } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Badge } from '@/components/atoms/Badge'
import { Input } from '@/components/atoms/Input'
import { adminService, User, UserDetails } from '@/services/adminService'
import { useAuth } from '@/contexts/AuthContext'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface UserDetailsModalProps {
  user: UserDetails | null
  onClose: () => void
}

function UserDetailsModal({ user, onClose }: UserDetailsModalProps) {
  if (!user) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{user.name}</h2>
              <p className="text-gray-600 mt-1">{user.email}</p>
            </div>
            <Button variant="ghost" onClick={onClose}>✕</Button>
          </div>
          <div className="flex items-center gap-4 mt-4">
            <Badge variant={user.is_admin ? 'success' : 'default'}>
              {user.is_admin ? 'Admin' : 'Cliente'}
            </Badge>
            <span className="text-sm text-gray-500">
              Criado em {format(new Date(user.created_at), "dd/MM/yyyy 'às' HH:mm", { locale: ptBR })}
            </span>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Exchanges */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
              <Building2 className="w-5 h-5 mr-2 text-blue-600" />
              Exchanges Integradas ({user.exchanges.length})
            </h3>
            {user.exchanges.length === 0 ? (
              <p className="text-gray-500 text-sm">Nenhuma exchange integrada</p>
            ) : (
              <div className="space-y-2">
                {user.exchanges.map((exchange) => (
                  <Card key={exchange.id} className="p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium text-gray-900">{exchange.name}</p>
                        <p className="text-sm text-gray-500">{exchange.exchange}</p>
                      </div>
                      <div className="text-right">
                        <Badge variant={exchange.status === 'active' ? 'success' : 'warning'}>
                          {exchange.status}
                        </Badge>
                        <p className="text-xs text-gray-500 mt-1">
                          {format(new Date(exchange.created_at), 'dd/MM/yyyy', { locale: ptBR })}
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Subscriptions */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
              <Bot className="w-5 h-5 mr-2 text-purple-600" />
              Assinaturas de Bots ({user.subscriptions.length})
            </h3>
            {user.subscriptions.length === 0 ? (
              <p className="text-gray-500 text-sm">Nenhuma assinatura ativa</p>
            ) : (
              <div className="space-y-2">
                {user.subscriptions.map((sub) => (
                  <Card key={sub.id} className="p-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{sub.bot_name}</p>
                        <div className="flex items-center gap-3 mt-2 text-sm text-gray-600">
                          <span>Sinais: {sub.total_signals_received}</span>
                          <span className={sub.total_pnl_usd >= 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                            P&L: ${sub.total_pnl_usd.toFixed(2)}
                          </span>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant={sub.status === 'active' ? 'success' : 'warning'}>
                          {sub.status}
                        </Badge>
                        <p className="text-xs text-gray-500 mt-1">
                          {format(new Date(sub.created_at), 'dd/MM/yyyy', { locale: ptBR })}
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Webhooks */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
              <Webhook className="w-5 h-5 mr-2 text-orange-600" />
              Webhooks ({user.webhooks.length})
            </h3>
            {user.webhooks.length === 0 ? (
              <p className="text-gray-500 text-sm">Nenhum webhook configurado</p>
            ) : (
              <div className="space-y-2">
                {user.webhooks.map((webhook) => (
                  <Card key={webhook.id} className="p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium text-gray-900">{webhook.name}</p>
                        <p className="text-sm text-gray-500">
                          Deliveries: {webhook.total_deliveries}
                        </p>
                      </div>
                      <div className="text-right">
                        <Badge variant={webhook.status === 'active' ? 'success' : 'warning'}>
                          {webhook.status}
                        </Badge>
                        <p className="text-xs text-gray-500 mt-1">
                          {format(new Date(webhook.created_at), 'dd/MM/yyyy', { locale: ptBR })}
                        </p>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function UsersPage() {
  const { user: authUser } = useAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedUser, setSelectedUser] = useState<UserDetails | null>(null)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)

  // Set admin user ID
  useEffect(() => {
    if (authUser?.id) {
      adminService.setAdminUserId(authUser.id)
    }
  }, [authUser?.id])

  const { data, isLoading, error } = useQuery({
    queryKey: ['adminUsers', searchQuery],
    queryFn: () => adminService.getUsers({ search: searchQuery || undefined }),
    refetchInterval: 30000,
    enabled: !!authUser?.id,
  })

  const handleViewDetails = async (userId: string) => {
    setIsLoadingDetails(true)
    try {
      const details = await adminService.getUserDetails(userId)
      setSelectedUser(details)
    } catch (err) {
      console.error('Error loading user details:', err)
    } finally {
      setIsLoadingDetails(false)
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Clientes</h1>
        <Card className="p-6">
          <div className="animate-pulse space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded" />
            ))}
          </div>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 lg:p-8">
        <Card className="p-6 bg-red-50 border-red-200">
          <div className="flex items-center text-red-800">
            <AlertCircle className="w-5 h-5 mr-2" />
            <p>Erro ao carregar usuários: {(error as Error).message}</p>
          </div>
        </Card>
      </div>
    )
  }

  const users = data?.users || []
  const total = data?.total || 0

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Clientes</h1>
        <p className="text-gray-600">Gerenciar todos os usuários do sistema</p>
      </div>

      {/* Search */}
      <Card className="p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <Input
              type="text"
              placeholder="Buscar por nome ou email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="text-sm text-gray-600">
            Total: <span className="font-semibold">{total}</span> usuários
          </div>
        </div>
      </Card>

      {/* Users List */}
      <Card className="overflow-hidden">
        {users.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500">Nenhum usuário encontrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left py-3 px-6 text-sm font-semibold text-gray-700">Usuário</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Exchanges</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Assinaturas</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Webhooks</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Último Login</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="py-4 px-6">
                      <div>
                        <p className="font-medium text-gray-900">{user.name}</p>
                        <p className="text-sm text-gray-500">{user.email}</p>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <Badge variant="default">{user.total_exchanges}</Badge>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <Badge variant="default">{user.total_subscriptions}</Badge>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <Badge variant="default">{user.total_webhooks}</Badge>
                    </td>
                    <td className="py-4 px-4 text-center text-sm text-gray-600">
                      {user.last_login
                        ? format(new Date(user.last_login), 'dd/MM/yyyy', { locale: ptBR })
                        : 'Nunca'}
                    </td>
                    <td className="py-4 px-4 text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewDetails(user.id)}
                        disabled={isLoadingDetails}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        Ver Detalhes
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* User Details Modal */}
      {selectedUser && (
        <UserDetailsModal
          user={selectedUser}
          onClose={() => setSelectedUser(null)}
        />
      )}
    </div>
  )
}
