# Progresso - 26 de Novembro de 2025

## Sistema de P&L e Performance para Bots

### Resumo do Dia

Implementação completa do sistema de tracking de P&L (Profit & Loss) para bot subscriptions, incluindo:
- Tabelas de banco de dados para histórico de P&L
- Service de tracking de trades
- Endpoints de API
- Componentes de visualização no frontend (gráficos)

---

## 1. Backend - Banco de Dados

### Migration: `create_bot_pnl_history.sql`

Criadas duas novas tabelas:

#### `bot_pnl_history`
- Armazena snapshots diários de P&L por subscription
- Campos: `daily_pnl_usd`, `cumulative_pnl_usd`, `daily_wins`, `daily_losses`, `win_rate_pct`
- Índices otimizados para consultas por subscription e data

#### `bot_trades`
- Registra trades individuais executados pelos bots
- Campos: `symbol`, `side`, `direction`, `entry_price`, `exit_price`, `pnl_usd`, `pnl_pct`, `is_winner`
- Suporta status: `open`, `closed`, `cancelled`

---

## 2. Backend - Services

### `BotTradeTrackerService` (NOVO)
**Arquivo:** `apps/api-python/infrastructure/services/bot_trade_tracker_service.py`

Métodos implementados:

| Método | Descrição |
|--------|-----------|
| `record_trade_close()` | Registra trade fechado e atualiza métricas da subscription |
| `_update_daily_pnl()` | Cria/atualiza entrada diária no `bot_pnl_history` |
| `process_position_close()` | Processa fechamento de posição (via SL/TP ou manual) |
| `generate_daily_snapshots()` | Gera snapshots diários para todas subscriptions ativas |
| `reset_daily_loss_counters()` | Reseta contadores de perda diária (para cron job) |

### Integração com `BotBroadcastService`
**Arquivo:** `apps/api-python/infrastructure/services/bot_broadcast_service.py`

- Adicionado `BotTradeTrackerService` como dependência
- Quando uma posição é fechada (action = "close"), o P&L é automaticamente registrado

---

## 3. Backend - Endpoints

### Novos endpoints em `bot_subscriptions_controller.py`

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/{subscription_id}/performance` | GET | Retorna métricas e histórico de P&L para gráficos |
| `/{subscription_id}/record-trade-close` | POST | Registra fechamento de trade manualmente |
| `/daily-snapshots` | POST | Gera snapshots diários (para cron job) |
| `/reset-daily-loss` | POST | Reseta contadores diários (para cron job) |

---

## 4. Frontend - Serviços

### `botsService.ts` - Novas interfaces e métodos

```typescript
// Interfaces adicionadas
interface PnLHistoryPoint {
  date: string
  daily_pnl: number
  cumulative_pnl: number
  daily_wins: number
  daily_losses: number
  cumulative_wins: number
  cumulative_losses: number
  win_rate: number
}

interface SubscriptionPerformance {
  subscription_id: string
  bot_name: string
  summary: { ... }
  pnl_history: PnLHistoryPoint[]
}

// Método adicionado
getSubscriptionPerformance(subscriptionId, userId, days)
```

---

## 5. Frontend - Componentes

### `BotPnLChart.tsx` (NOVO)
- Gráfico de área mostrando P&L cumulativo ao longo do tempo
- Usa Recharts (AreaChart)
- Cores: verde para positivo, vermelho para negativo
- Tooltip com formatação em USD

### `BotWinRateChart.tsx` (NOVO)
- Gráfico de pizza mostrando proporção wins/losses
- Porcentagem de win rate no centro
- Cores: verde para wins, vermelho para losses

### `BotDetailsModal.tsx` (MODIFICADO)

**Layout atualizado:**
- **5 cards de estatísticas** no topo: Win Rate, P&L Total, Sinais, Posições, Taxa Vitória
- **Gráfico P&L em largura total** (100%) - removido o gráfico de pizza lado a lado
- Seletor de período: 7, 30 ou 90 dias
- Loading state com spinner

**Fix aplicado:**
- Corrigido import de `useAuth` de `@/hooks/useAuth` para `@/contexts/AuthContext`

---

## 6. Arquivos Criados/Modificados

### Novos Arquivos
- `apps/api-python/migrations/create_bot_pnl_history.sql`
- `apps/api-python/infrastructure/services/bot_trade_tracker_service.py`
- `frontend-new/src/components/molecules/BotPnLChart.tsx`
- `frontend-new/src/components/molecules/BotWinRateChart.tsx`

### Arquivos Modificados
- `apps/api-python/infrastructure/services/bot_broadcast_service.py`
- `apps/api-python/presentation/controllers/bot_subscriptions_controller.py`
- `frontend-new/src/components/molecules/BotDetailsModal.tsx`
- `frontend-new/src/services/botsService.ts`

### Arquivos Limpos (Removidos)
- `apps/api-python/check_accounts.py`
- `apps/api-python/check_all_accounts.py`
- `apps/api-python/check_db_state.py`
- `apps/api-python/check_trader.py`
- `create_test_user.py`
- `frontend-new/src/components/atoms/CustomChart.tsx.backup`

---

## 7. Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUXO DE TRACKING P&L                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Bot envia sinal "close" ──► BotBroadcastService         │
│                                        │                    │
│  2. Posição fechada na exchange        │                    │
│                                        ▼                    │
│  3. BotTradeTrackerService.process_position_close()         │
│           │                                                 │
│           ├──► Insere em bot_trades                         │
│           ├──► Atualiza bot_subscriptions (P&L, wins/losses)│
│           └──► Atualiza/cria bot_pnl_history (diário)       │
│                                                             │
│  4. Frontend busca via GET /performance                     │
│           │                                                 │
│           └──► BotDetailsModal exibe gráfico P&L            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Cron Jobs Necessários

Para manter o sistema funcionando corretamente, configurar os seguintes cron jobs:

```bash
# Gerar snapshots diários às 23:59 UTC
59 23 * * * curl -X POST http://localhost:8001/api/v1/bot-subscriptions/daily-snapshots

# Resetar contadores de perda diária à meia-noite UTC
0 0 * * * curl -X POST http://localhost:8001/api/v1/bot-subscriptions/reset-daily-loss
```

---

## 9. Próximos Passos Sugeridos

1. **Webhooks da Exchange**: Implementar listeners para receber notificações de SL/TP triggers automaticamente
2. **Backtesting**: Adicionar dados históricos para simular performance passada
3. **Alertas**: Notificar usuários quando atingirem limites de perda diária
4. **Exportação**: Permitir exportar histórico de trades em CSV/Excel

---

## Status Final

| Item | Status |
|------|--------|
| Migration executada | ✅ |
| Service de tracking | ✅ |
| Endpoints API | ✅ |
| Frontend charts | ✅ |
| Layout modal | ✅ |
| Limpeza de arquivos | ✅ |

**Sistema de P&L para Bots: COMPLETO**
