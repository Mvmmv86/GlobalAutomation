# 🔧 CORREÇÃO DO DASHBOARD FRONTEND

## PROBLEMA IDENTIFICADO
O dashboard está usando dados das APIs antigas (`metrics`, `orderStats`, etc.) mas precisa usar o novo endpoint `/api/v1/dashboard/cards`.

## SOLUÇÃO COMPLETA

### 1️⃣ **Adicione em `src/hooks/useApiData.ts`:**

```typescript
// Dashboard Cards Hook (adicione no final do arquivo)
export const useDashboardCards = () => {
  return useQuery({
    queryKey: ['dashboard-cards'],
    queryFn: async () => {
      const response = await apiClient.get('/dashboard/cards')
      return response
    },
    refetchInterval: 10000, // Refresh every 10 seconds
    staleTime: 5000,
  })
}
```

### 2️⃣ **Modifique `src/components/pages/DashboardPage.tsx`:**

#### ADICIONE O IMPORT:
```typescript
import {
  useExchangeAccounts,
  useWebhooks,
  useRecentOrders,
  useActivePositions,
  usePositionMetrics,
  useOrderStats,
  useCreateTestOrder,
  useDashboardCards  // <-- ADICIONE ESTA LINHA
} from '@/hooks/useApiData'
```

#### ADICIONE O HOOK NO COMPONENTE:
```typescript
const DashboardPage: React.FC = () => {
  // ... outros hooks existentes ...

  // Adicione esta linha após os outros hooks:
  const { data: dashboardCards, isLoading: loadingCards } = useDashboardCards()

  // ... resto do código ...
```

#### SUBSTITUA O OBJETO `stats`:
Encontre este código:
```typescript
const stats = {
  totalOrders: orderStats?.total_orders || recentOrdersApi?.length || 156,
  activePositions: activePositions?.length || 8,
  totalPnL: metrics?.totalPnl || 2547.83,
  // ... etc
}
```

SUBSTITUA POR:
```typescript
const stats = {
  totalOrders: dashboardCards?.orders_total?.value || 0,
  activePositions: dashboardCards?.positions_active?.value || 0,
  totalPnL: dashboardCards?.pnl_total?.value || 0,
  activeWebhooks: webhooks?.filter(w => w.status === 'active').length || 0,
  exchangeAccounts: exchangeAccounts?.length || 0,
  todayOrders: dashboardCards?.orders_today?.value || 0,
  successRate: orderStats?.success_rate || 0,
  filledOrders: orderStats?.filled_orders || 0,
  pendingOrders: orderStats?.pending_orders || 0,
  // Novos campos dos cards
  futuresBalance: dashboardCards?.futures?.value || 0,
  futuresPnL: dashboardCards?.futures?.unrealized_pnl || 0,
  spotBalance: dashboardCards?.spot?.value || 0,
  spotAssets: dashboardCards?.spot?.total_assets || 0,
}
```

### 3️⃣ **ADICIONE OS NOVOS CARDS DE FUTURES E SPOT:**

Encontre onde estão os cards (antes de "Total P&L") e adicione:

```tsx
{/* Card Futures */}
<Card>
  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    <CardTitle className="text-sm font-medium">Futures Balance</CardTitle>
    <TrendingUp className="h-4 w-4 text-muted-foreground" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold">
      ${stats.futuresBalance.toFixed(2)}
    </div>
    <p className="text-xs text-muted-foreground">
      P&L: ${stats.futuresPnL.toFixed(2)}
    </p>
  </CardContent>
</Card>

{/* Card Spot */}
<Card>
  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    <CardTitle className="text-sm font-medium">Spot Balance</CardTitle>
    <DollarSign className="h-4 w-4 text-muted-foreground" />
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-bold">
      ${stats.spotBalance.toFixed(2)}
    </div>
    <p className="text-xs text-muted-foreground">
      {stats.spotAssets} ativos
    </p>
  </CardContent>
</Card>
```

### 4️⃣ **ATUALIZE O CARD DE P&L TOTAL:**

Encontre o card "Total P&L" e modifique para:

```tsx
<Card>
  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
    <CardTitle className="text-sm font-medium">P&L Total do Dia</CardTitle>
    <DollarSign className="h-4 w-4 text-muted-foreground" />
  </CardHeader>
  <CardContent>
    <div className={`text-2xl font-bold ${stats.totalPnL >= 0 ? 'text-success' : 'text-danger'}`}>
      {stats.totalPnL >= 0 ? '+' : ''}${Math.abs(stats.totalPnL).toFixed(2)}
    </div>
    <p className="text-xs text-muted-foreground">
      P&L não realizado
    </p>
  </CardContent>
</Card>
```

## 📊 VALORES ATUAIS DA API:

```json
{
  "futures": {
    "value": 710.37,         // Saldo total em Futures
    "unrealized_pnl": 10.38  // P&L não realizado
  },
  "spot": {
    "value": 1730.57,        // Saldo total em Spot
    "total_assets": 28       // Número de ativos
  },
  "pnl_total": {
    "value": 10.38           // P&L total do dia
  },
  "positions_active": {
    "value": 3               // Posições abertas
  },
  "orders_total": {
    "value": 2               // Total de ordens
  },
  "orders_today": {
    "value": 0               // Ordens hoje
  }
}
```

## ✅ RESULTADO ESPERADO:
Após essas mudanças, o dashboard mostrará:
- **Futures Balance**: $710.37 (P&L: +$10.38)
- **Spot Balance**: $1,730.57 (28 ativos)
- **P&L Total do Dia**: +$10.38
- **Posições Ativas**: 3
- **Total de Ordens**: 2
- **Ordens Hoje**: 0

## 🔄 ATUALIZAÇÃO AUTOMÁTICA:
Os dados serão atualizados automaticamente a cada 10 segundos!