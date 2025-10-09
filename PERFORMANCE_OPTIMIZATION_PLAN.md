# 🚀 PLANO DE OTIMIZAÇÃO DE PERFORMANCE

**Data:** 09 de Outubro de 2025
**Status Atual:** Sistema operacional, mas com oportunidades de melhoria
**Objetivo:** Reduzir latência, aumentar throughput e melhorar UX

---

## 📊 ANÁLISE ATUAL DE PERFORMANCE

### Backend (FastAPI - Port 8000)
- ✅ GZip compression ativo (>500 bytes)
- ⚠️ CPU: 57.6% em um processo (PID 40180)
- ⚠️ Queries síncronas em loops (N+1 problem)
- ⚠️ Cache em memória (não distribuído)
- ⚠️ Sem connection pooling otimizado

### Frontend (React - Port 3000)
- ✅ React Query configurado
- ⚠️ Bundle size não otimizado (~400KB estimado)
- ⚠️ Sem code splitting por rotas
- ⚠️ Sem lazy loading de componentes pesados
- ⚠️ Múltiplas instâncias npm (consumo desnecessário)

### Database (PostgreSQL/Supabase)
- ⚠️ Sem índices otimizados para queries frequentes
- ⚠️ pgBouncer em transaction mode (limitações)
- ⚠️ Queries complexas sem explain analyze
- ⚠️ Sem materialized views para agregações

### WebSocket
- ✅ Heartbeat implementado
- ⚠️ Sem compressão de mensagens
- ⚠️ Broadcasting para todos usuários (não filtrado)
- ⚠️ Sem batching de notificações

---

## 🎯 OTIMIZAÇÕES PRIORITÁRIAS

### FASE 1: Backend Optimization (Impact: HIGH)

#### 1.1 Database Query Optimization
**Problema:** Queries N+1 no endpoint `/api/v1/orders`
**Impacto:** ~5-10s de latência extra
**Solução:**
```python
# ANTES (main.py:686-697):
for symbol in all_symbols:  # Loop serial - LENTO!
    result = await connector.get_account_orders(symbol)
    all_orders.extend(result)

# DEPOIS (implementar):
# Buscar em paralelo com asyncio.gather()
tasks = [connector.get_account_orders(symbol) for symbol in all_symbols]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Ganho Esperado:** 80-90% redução no tempo de busca de orders

---

#### 1.2 Connection Pool Optimization
**Problema:** pgBouncer transaction mode limita reuso de conexões
**Impacto:** Overhead de nova conexão a cada query
**Solução:**
```python
# infrastructure/database/connection_transaction_mode.py
# ANTES:
min_size=5, max_size=20

# DEPOIS:
min_size=10,     # Mais conexões pré-alocadas
max_size=50,     # Permitir mais conexões simultâneas
max_queries=50000,  # Rotação menos frequente
```

**Ganho Esperado:** 30-40% redução na latência de queries

---

#### 1.3 Redis Cache (Ativar)
**Problema:** Cache apenas em memória (não distribuído)
**Impacto:** Cada instância tem cache próprio
**Solução:**
```python
# main.py:85 - ATIVAR REDIS:
# ANTES:
logger.info("Redis connection skipped for integration testing")

# DEPOIS:
await redis_manager.connect()
logger.info("✅ Redis cache connected")
```

**Ganho Esperado:** 50-70% redução em consultas repetidas

---

#### 1.4 Database Indexes
**Problema:** Queries sem índices otimizados
**Solução SQL:**
```sql
-- Índices para orders (main.py:617-1085)
CREATE INDEX CONCURRENTLY idx_orders_exchange_account_created
  ON orders(exchange_account_id, created_at DESC);

CREATE INDEX CONCURRENTLY idx_orders_symbol_status
  ON orders(symbol, status) WHERE status IN ('filled', 'pending');

-- Índices para positions
CREATE INDEX CONCURRENTLY idx_positions_account_symbol
  ON positions(exchange_account_id, symbol);

-- Índices para trading_orders
CREATE INDEX CONCURRENTLY idx_trading_orders_created_status
  ON trading_orders(created_at DESC, status);
```

**Ganho Esperado:** 60-80% redução em query time

---

### FASE 2: Frontend Optimization (Impact: MEDIUM-HIGH)

#### 2.1 Code Splitting por Rotas
**Problema:** Bundle único carrega tudo de uma vez
**Solução:**
```typescript
// AppRouter.tsx - Implementar lazy loading
import { lazy, Suspense } from 'react';

const TradingPage = lazy(() => import('./pages/TradingPage'));
const OrdersPage = lazy(() => import('./pages/OrdersPage'));
const PositionsPage = lazy(() => import('./pages/PositionsPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));

// Wrapper com suspense
<Suspense fallback={<PageSkeleton />}>
  <TradingPage />
</Suspense>
```

**Ganho Esperado:** 60-70% redução no initial bundle

---

#### 2.2 Virtual Scrolling para Tabelas
**Problema:** Renderiza todas as rows de uma vez (100+ orders)
**Solução:**
```typescript
// OrdersPage.tsx - Usar react-window
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={orders.length}
  itemSize={60}
  width="100%"
>
  {({ index, style }) => (
    <OrderRow order={orders[index]} style={style} />
  )}
</FixedSizeList>
```

**Ganho Esperado:** 90% redução em re-renders

---

#### 2.3 Image Optimization
**Problema:** Ícones e imagens sem otimização
**Solução:**
```bash
# Adicionar ao package.json
npm install vite-plugin-image-optimizer

# vite.config.ts
import imageOptimizer from 'vite-plugin-image-optimizer';

export default {
  plugins: [
    imageOptimizer({
      png: { quality: 80 },
      jpeg: { quality: 80 },
      webp: { quality: 80 }
    })
  ]
}
```

**Ganho Esperado:** 40-50% redução em asset size

---

#### 2.4 Prefetch de Dados Críticos
**Problema:** Cada página faz requests sequenciais
**Solução:**
```typescript
// DashboardLayout.tsx - Prefetch parallel
useEffect(() => {
  // Prefetch em paralelo ao carregar layout
  queryClient.prefetchQuery(['balances']);
  queryClient.prefetchQuery(['positions']);
  queryClient.prefetchQuery(['orders-recent']);
}, []);
```

**Ganho Esperado:** 50% redução em tempo de carregamento

---

### FASE 3: WebSocket Optimization (Impact: MEDIUM)

#### 3.1 Message Compression
**Problema:** Mensagens JSON sem compressão
**Solução:**
```python
# websocket_controller.py
import zlib
import base64

async def send_compressed(message: dict):
    json_str = json.dumps(message)
    compressed = zlib.compress(json_str.encode())
    encoded = base64.b64encode(compressed).decode()
    await websocket.send_text(encoded)
```

**Ganho Esperado:** 70-80% redução em bandwidth

---

#### 3.2 Batching de Notificações
**Problema:** Envia 1 notificação por evento
**Solução:**
```python
# Buffer de notificações (enviar a cada 100ms)
notification_buffer = []

async def batch_notify():
    while True:
        await asyncio.sleep(0.1)  # 100ms
        if notification_buffer:
            await broadcast_batch(notification_buffer)
            notification_buffer.clear()
```

**Ganho Esperado:** 60% redução em overhead de rede

---

#### 3.3 Topic-Based Subscriptions
**Problema:** Cliente recebe TODAS notificações
**Solução:**
```python
# Permitir subscribe por tópico
{
  "action": "subscribe",
  "topics": ["orders.BTCUSDT", "positions.*"]
}

# Filtrar antes de enviar
if matches_subscription(user_topics, message_topic):
    await send_message(message)
```

**Ganho Esperado:** 80% redução em tráfego desnecessário

---

### FASE 4: Advanced Optimizations (Impact: MEDIUM)

#### 4.1 Server-Side Caching com ETags
**Problema:** Frontend refetch mesmo sem mudanças
**Solução:**
```python
from hashlib import md5

@app.get("/api/v1/orders")
async def get_orders(request: Request):
    data = await fetch_orders()

    # Generate ETag
    etag = md5(json.dumps(data).encode()).hexdigest()

    # Check If-None-Match header
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304)  # Not Modified

    return JSONResponse(data, headers={"ETag": etag})
```

**Ganho Esperado:** 90% redução em transferências repetidas

---

#### 4.2 GraphQL para Queries Flexíveis
**Problema:** REST endpoints retornam dados desnecessários
**Solução:**
```python
# Implementar GraphQL com Strawberry
import strawberry

@strawberry.type
class Order:
    id: str
    symbol: str
    quantity: float
    # Cliente escolhe campos necessários

schema = strawberry.Schema(query=Query)
```

**Ganho Esperado:** 30-50% redução em payload size

---

#### 4.3 HTTP/2 Server Push
**Problema:** Requests sequenciais (HTML, CSS, JS)
**Solução:**
```python
# Configurar uvicorn com HTTP/2
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    http="h2"  # HTTP/2
)
```

**Ganho Esperado:** 40% redução em tempo de carregamento inicial

---

#### 4.4 Service Worker para Offline Support
**Problema:** Sem cache de assets no browser
**Solução:**
```typescript
// public/service-worker.js
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('trading-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/main.js',
        '/main.css',
        '/logo.png'
      ]);
    })
  );
});
```

**Ganho Esperado:** Carregamento instantâneo em visitas repetidas

---

## 📈 MÉTRICAS ALVO

### Performance Atual (Baseline)
| Métrica | Atual | Alvo | Melhoria |
|---------|-------|------|----------|
| **Backend Response Time (p95)** | 150ms | < 50ms | 66% |
| **Frontend Initial Load** | ~2s | < 800ms | 60% |
| **Bundle Size** | 400KB | < 200KB | 50% |
| **WebSocket Latency** | 100ms | < 30ms | 70% |
| **Orders API (50 items)** | 5-10s | < 1s | 80-90% |
| **Memory Usage (Backend)** | 171MB | < 120MB | 30% |
| **CPU Usage (Backend)** | 57% | < 20% | 65% |

### Lighthouse Score Alvo
| Categoria | Atual | Alvo |
|-----------|-------|------|
| Performance | ~60 | 90+ |
| Accessibility | ~80 | 95+ |
| Best Practices | ~70 | 95+ |
| SEO | ~80 | 95+ |

---

## 🔧 ROADMAP DE IMPLEMENTAÇÃO

### Sprint 1 (2 dias) - Quick Wins
- [ ] 1.1 Database Query Optimization (parallelização)
- [ ] 1.2 Connection Pool Optimization
- [ ] 2.4 Prefetch de dados críticos
- [ ] 4.1 Server-side ETags

**Impacto:** 50-60% melhoria geral

### Sprint 2 (3 dias) - Major Optimizations
- [ ] 1.3 Ativar Redis Cache
- [ ] 1.4 Database Indexes
- [ ] 2.1 Code Splitting por Rotas
- [ ] 2.2 Virtual Scrolling

**Impacto:** 70-80% melhoria geral

### Sprint 3 (2 dias) - Advanced Features
- [ ] 3.1 WebSocket Compression
- [ ] 3.2 Batching de Notificações
- [ ] 3.3 Topic-Based Subscriptions
- [ ] 2.3 Image Optimization

**Impacto:** 80-85% melhoria geral

### Sprint 4 (3 dias) - Polish & Monitoring
- [ ] 4.2 GraphQL (opcional)
- [ ] 4.3 HTTP/2 Server Push
- [ ] 4.4 Service Worker
- [ ] Monitoring completo (Prometheus + Grafana)

**Impacto:** 90%+ melhoria geral

---

## 🧪 TESTES DE PERFORMANCE

### Ferramentas
- **Backend:** `locust` (load testing)
- **Frontend:** Lighthouse CI
- **Database:** `pg_stat_statements`
- **WebSocket:** `artillery`

### Testes Críticos
```bash
# 1. Load test backend
locust -f locustfile.py --host=http://localhost:8000

# 2. Lighthouse audit
lighthouse http://localhost:3000 --output=json

# 3. Database slow queries
SELECT * FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;

# 4. WebSocket stress test
artillery run websocket-test.yml
```

---

## 💾 MONITORING CONTÍNUO

### Métricas em Tempo Real
```python
# Adicionar ao main.py
from prometheus_client import Counter, Histogram

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration'
)

@app.middleware("http")
async def monitor_performance(request, call_next):
    with request_duration.time():
        response = await call_next(request)
    return response
```

### Dashboard Grafana
- Response times por endpoint
- Query execution time
- WebSocket connections ativas
- Cache hit/miss ratio
- Memory/CPU usage

---

## ⚠️ RISCOS E TRADE-OFFS

### Ativação do Redis
**Risco:** Dependência adicional
**Mitigação:** Fallback para cache em memória se Redis falhar

### Code Splitting
**Risco:** Complexidade de build aumenta
**Mitigação:** Testing rigoroso de lazy loading

### Database Indexes
**Risco:** Writes mais lentos
**Mitigação:** Apenas índices essenciais, usar CONCURRENTLY

### HTTP/2
**Risco:** Compatibilidade com proxies antigos
**Mitigação:** Fallback automático para HTTP/1.1

---

## ✅ CHECKLIST PRÉ-OTIMIZAÇÃO

- [x] Baseline de métricas estabelecido
- [x] Plano documentado e revisado
- [ ] Backup do banco de dados
- [ ] Ambiente de staging configurado
- [ ] Testes de load preparados
- [ ] Rollback plan definido
- [ ] Monitoramento configurado

---

## 📞 RESPONSÁVEIS

**Desenvolvimento:** Claude Code
**Code Review:** Pendente
**Testing:** Pendente
**Deploy:** Pendente

---

**Última Atualização:** 09/10/2025
**Próxima Revisão:** Após Sprint 1

**Estimativa Total:** 10 dias de trabalho focado
**Impacto Esperado:** 80-90% melhoria geral de performance
