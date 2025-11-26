/**
 * AdminDashboard Page
 * Main dashboard with KPIs and statistics for admin portal
 */
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Users,
  Building2,
  Bot,
  Webhook,
  UserPlus,
  Activity,
  TrendingUp,
  DollarSign,
  AlertCircle
} from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Badge } from '@/components/atoms/Badge'
import { adminService, DashboardStats } from '@/services/adminService'
import { useAuth } from '@/contexts/AuthContext'

interface KPICardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  trend?: {
    value: number
    label: string
  }
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'red'
}

function KPICard({ title, value, icon, trend, color = 'blue' }: KPICardProps) {
  const colorClasses = {
    blue: 'bg-blue-600 text-white',
    green: 'bg-green-600 text-white',
    purple: 'bg-purple-600 text-white',
    orange: 'bg-orange-600 text-white',
    red: 'bg-red-600 text-white',
  }

  return (
    <Card className="p-6 bg-gray-900 border-gray-800">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        {trend && (
          <div className="flex items-center text-sm">
            <TrendingUp className="w-4 h-4 text-green-400 mr-1" />
            <span className="text-green-400 font-medium">+{trend.value}</span>
            <span className="text-gray-400 ml-1">{trend.label}</span>
          </div>
        )}
      </div>
      <h3 className="text-2xl font-bold text-white mb-1">{value}</h3>
      <p className="text-sm text-gray-400">{title}</p>
    </Card>
  )
}

export function AdminDashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<DashboardStats | null>(null)

  // Set admin user ID when component mounts
  useEffect(() => {
    if (user?.id) {
      adminService.setAdminUserId(user.id)
    }
  }, [user?.id])

  const { data, isLoading, error } = useQuery({
    queryKey: ['adminDashboardStats'],
    queryFn: () => adminService.getDashboardStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: !!user?.id,
  })

  useEffect(() => {
    if (data) {
      setStats(data)
    }
  }, [data])

  if (isLoading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Dashboard</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(8)].map((_, i) => (
            <Card key={i} className="p-6 animate-pulse">
              <div className="h-12 bg-gray-200 rounded mb-4" />
              <div className="h-8 bg-gray-200 rounded mb-2" />
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
            <p>Erro ao carregar dashboard: {(error as Error).message}</p>
          </div>
        </Card>
      </div>
    )
  }

  if (!stats) {
    return null
  }

  const { overview, recent_activity, top_bots } = stats

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400">Visão geral do sistema de copy trading</p>
      </div>

      {/* Main KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Total de Clientes"
          value={overview.total_users.toLocaleString()}
          icon={<Users className="w-6 h-6" />}
          color="blue"
          trend={{
            value: recent_activity.new_users_7d,
            label: 'últimos 7 dias',
          }}
        />
        <KPICard
          title="Total de Exchanges"
          value={overview.total_exchanges.toLocaleString()}
          icon={<Building2 className="w-6 h-6" />}
          color="green"
        />
        <KPICard
          title="Total de Bots"
          value={overview.total_bots.toLocaleString()}
          icon={<Bot className="w-6 h-6" />}
          color="purple"
        />
        <KPICard
          title="Total de Webhooks"
          value={overview.total_webhooks.toLocaleString()}
          icon={<Webhook className="w-6 h-6" />}
          color="orange"
        />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Bots Ativos"
          value={overview.active_bots.toLocaleString()}
          icon={<Activity className="w-6 h-6" />}
          color="green"
        />
        <KPICard
          title="Webhooks Ativos"
          value={overview.active_webhooks.toLocaleString()}
          icon={<Webhook className="w-6 h-6" />}
          color="blue"
        />
        <KPICard
          title="Assinaturas Ativas"
          value={overview.active_subscriptions.toLocaleString()}
          icon={<UserPlus className="w-6 h-6" />}
          color="purple"
          trend={{
            value: recent_activity.new_subscriptions_7d,
            label: 'últimos 7 dias',
          }}
        />
        <KPICard
          title="P&L Total (USD)"
          value={`$${overview.total_pnl_usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          icon={<DollarSign className="w-6 h-6" />}
          color={overview.total_pnl_usd >= 0 ? 'green' : 'red'}
        />
      </div>

      {/* Recent Activity & Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Signals Sent */}
        <Card className="p-6 bg-gray-900 border-gray-800">
          <h3 className="text-lg font-semibold text-white mb-4">Sinais Enviados</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Total de Sinais</span>
              <span className="text-2xl font-bold text-white">
                {overview.total_signals_sent.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Últimos 7 dias</span>
              <Badge variant="success">
                +{recent_activity.signals_sent_7d.toLocaleString()}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Ordens Executadas</span>
              <span className="text-xl font-semibold text-white">
                {overview.total_orders_executed.toLocaleString()}
              </span>
            </div>
          </div>
        </Card>

        {/* Subscriptions */}
        <Card className="p-6 bg-gray-900 border-gray-800">
          <h3 className="text-lg font-semibold text-white mb-4">Assinaturas</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Total de Assinaturas</span>
              <span className="text-2xl font-bold text-white">
                {overview.total_subscriptions.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Assinaturas Ativas</span>
              <Badge variant="success">
                {overview.active_subscriptions.toLocaleString()}
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Novas (7 dias)</span>
              <span className="text-xl font-semibold text-green-400">
                +{recent_activity.new_subscriptions_7d.toLocaleString()}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Top Performing Bots */}
      <Card className="p-6 bg-gray-900 border-gray-800">
        <h3 className="text-lg font-semibold text-white mb-4">Top Bots com Melhor Performance</h3>
        {top_bots.length === 0 ? (
          <p className="text-gray-400 text-center py-8">Nenhum bot encontrado</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-300">Nome</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-300">Assinantes</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-300">Sinais Enviados</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-300">Win Rate</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-300">P&L Médio</th>
                </tr>
              </thead>
              <tbody>
                {top_bots.map((bot) => (
                  <tr key={bot.id} className="border-b border-gray-800 hover:bg-gray-800">
                    <td className="py-3 px-4">
                      <p className="font-medium text-white">{bot.name}</p>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Badge variant="default">{bot.total_subscribers}</Badge>
                    </td>
                    <td className="py-3 px-4 text-center text-gray-300">
                      {bot.total_signals_sent.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {bot.avg_win_rate !== null ? (
                        <Badge variant={bot.avg_win_rate >= 50 ? 'success' : 'warning'}>
                          {bot.avg_win_rate.toFixed(1)}%
                        </Badge>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {bot.avg_pnl_pct !== null ? (
                        <span className={`font-semibold ${bot.avg_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {bot.avg_pnl_pct >= 0 ? '+' : ''}{bot.avg_pnl_pct.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
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
