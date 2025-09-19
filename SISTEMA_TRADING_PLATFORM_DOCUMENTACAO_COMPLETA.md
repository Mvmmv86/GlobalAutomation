# 📊 TRADING PLATFORM - DOCUMENTAÇÃO TÉCNICA COMPLETA

**Versão:** 1.0.0  
**Data:** 20 de Janeiro de 2025  
**Status:** Em Desenvolvimento  

---

## 🎯 **VISÃO GERAL DO SISTEMA**

### **Objetivo Principal**
Plataforma de trading automatizada que funciona como ponte entre TradingView e exchanges de criptomoedas, permitindo execução automática de sinais de trading com gestão de risco avançada.

### **Arquitetura Geral**
```
TradingView → Webhook → Nossa Plataforma → Exchange APIs → Dashboard
```

### **Fluxo de Dados**
1. **TradingView** envia sinais via webhook
2. **Backend** recebe, valida e processa sinais
3. **Exchange APIs** executam ordens automaticamente
4. **Frontend** exibe resultados e métricas
5. **Usuário** monitora e configura via dashboard

---

## 🏗️ **ARQUITETURA TÉCNICA**

### **Frontend (React + TypeScript)**
- **Framework:** React 18 com Vite
- **Linguagem:** TypeScript
- **Estilo:** Tailwind CSS + Tema escuro
- **Padrão:** Atomic Design (atoms, molecules, organisms)
- **Estado:** Context API para autenticação
- **Roteamento:** React Router DOM

### **Backend (FastAPI + Python)**
- **Framework:** FastAPI 
- **Linguagem:** Python 3.11
- **Banco:** PostgreSQL (com migrações Alembic)
- **Autenticação:** JWT tokens
- **Arquitetura:** Clean Architecture
- **APIs:** Binance, Bybit, OKX

### **Infraestrutura**
- **Containers:** Docker Compose
- **Desenvolvimento:** Dev Containers
- **CI/CD:** GitHub Actions (configurado)
- **Monitoramento:** Logs estruturados

---

## 🎨 **INTERFACE DO USUÁRIO - DOCUMENTAÇÃO COMPLETA**

### **1. 🔐 SISTEMA DE AUTENTICAÇÃO**

#### **LoginPage**
**Localização:** `/workspace/apps/web-trading/src/components/pages/LoginPage.tsx`

**Funcionalidades:**
- ✅ Login com email e senha
- ✅ Validação de campos (Zod schema)
- ✅ Suporte a 2FA (TOTP)
- ✅ Toggle de visualização de senha
- ✅ Integração com AuthContext
- ✅ Redirecionamento automático pós-login

**Campos:**
- `email`: string (validação de email)
- `password`: string (mínimo 6 caracteres)
- `totpCode`: string opcional (2FA)

**Estados:**
- `isLoading`: boolean (carregamento do login)
- `error`: string (mensagem de erro)

---

### **🔧 PROBLEMAS COMUNS DE CONFIGURAÇÃO E SOLUÇÕES**

#### **1. Problemas de Permissões de Arquivos**

**Problema:** Frontend falha ao iniciar com erro `EACCES: permission denied`
```bash
Error: EACCES: permission denied, open '/home/user/global/frontend/trading-dashboard/vite.config.ts.timestamp-xxx.mjs'
```

**Causa:** Arquivos criados com permissões de root no sistema

**Solução:**
```bash
# Criar cópia com permissões corretas
cp -r frontend/trading-dashboard frontend-new
cd frontend-new && npm run dev
```

#### **2. Erro de Porta Incorreta no Frontend**

**Problema:** Erro de conexão `ECONNREFUSED 127.0.0.1:8002`
```javascript
❌ AuthService: Error response: {"error":"API Proxy error","message":"connect ECONNREFUSED 127.0.0.1:8002"}
```

**Causa:** Frontend configurado para porta 8002, mas backend roda na porta 8000

**Solução:** Corrigir arquivo `vite.config.ts`
```javascript
// Em vite.config.ts linha ~13
// Alterar de:
return 'http://localhost:8002'
// Para:
return 'http://localhost:8000'
```

#### **3. Erro de Mapeamento de Tokens no Login**

**Problema:** Login retorna 200 mas falha com "No access token in response"
```javascript
❌ Login failed: Error: No access token in response
```

**Causa:** API retorna `access_token` (snake_case), frontend espera `accessToken` (camelCase)

**Solução:** Atualizar `AuthContext.tsx`
```javascript
// Suporte para ambos os formatos
const accessToken = response.access_token || response.accessToken
const refreshToken = response.refresh_token || response.refreshToken
```

#### **4. Configurações de Porta Padrão**
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **Documentação API:** http://localhost:8000/docs

#### **5. Credenciais Demo Padrão**
- **Email:** `demo@tradingview.com`
- **Senha:** `demo123456`

---

### **2. 🏠 DASHBOARD PRINCIPAL**

#### **DashboardPage**
**Localização:** `/workspace/apps/web-trading/src/components/pages/DashboardPage.tsx`

**Funcionalidades:**
- ✅ Visão geral de métricas de trading
- ✅ Teste de conectividade API
- ✅ Ordens recentes
- ✅ Posições ativas
- ✅ Integração com hooks de API
- ✅ Fallback para dados mock

**Métricas Exibidas:**
- **Total P&L:** Lucro/prejuízo acumulado
- **Ordens Hoje:** Número de ordens do dia
- **Posições Ativas:** Posições em aberto
- **Total de Ordens:** Histórico completo
- **Webhooks Ativos:** Webhooks funcionando
- **Exchange Accounts:** Contas conectadas

**Componentes:**
- Cards de métricas com ícones
- Tabela de ordens recentes
- Lista de posições ativas
- Botão de teste de API
- Indicadores de status

---

### **3. 🏦 GERENCIAMENTO DE CONTAS**

#### **ExchangeAccountsPage**
**Localização:** `/workspace/apps/web-trading/src/components/pages/ExchangeAccountsPage.tsx`

**Funcionalidades:**
- ✅ Listagem de contas de exchange
- ✅ Criação de novas contas
- ✅ Configuração avançada de contas
- ✅ Teste de conectividade
- ✅ Exclusão de contas

**Estados da Conta:**
- `isActive`: boolean (conta ativa/inativa)
- `testnet`: boolean (ambiente de teste)
- `exchange`: string (binance, bybit, okx, etc.)
- `name`: string (nome personalizado)

#### **CreateExchangeAccountModal**
**Localização:** `/workspace/apps/web-trading/src/components/molecules/CreateExchangeAccountModal.tsx`

**Campos de Entrada:**
- `name`: Nome da conta (obrigatório)
- `exchange`: Seleção de exchange (obrigatório)
- `apiKey`: Chave de API (obrigatório, oculta)
- `secretKey`: Chave secreta (obrigatório, oculta)
- `passphrase`: Passphrase (condicional para OKX/Coinbase)
- `testnet`: Toggle para ambiente de teste
- `isDefault`: Toggle para conta padrão

**Exchanges Suportadas:**
- **Binance:** Sem passphrase
- **Bybit:** Sem passphrase
- **OKX:** Com passphrase obrigatória
- **Coinbase Pro:** Com passphrase obrigatória
- **Bitget:** Sem passphrase

**Validações:**
- Campos obrigatórios
- Passphrase obrigatória conforme exchange
- Formato de chaves API
- Aviso de segurança

#### **ConfigureAccountModal**
**Localização:** `/workspace/apps/web-trading/src/components/molecules/ConfigureAccountModal.tsx`

**5 Abas de Configuração:**

##### **1. 🔄 Trading**
- `defaultLeverage`: 1x-125x (padrão: 10x)
- `marginMode`: Cross/Isolated (padrão: Cross)
- `positionMode`: One-way/Hedge (padrão: One-way)
- `defaultOrderSize`: Tamanho da ordem (padrão: 1)
- `orderSizeType`: Percentage/Fixed (padrão: Percentage)
- `favoriteSymbols`: Array de símbolos selecionados

##### **2. 🛡️ Risk Management**
- `maxLossPerTrade`: Máx perda por trade % (padrão: 2%)
- `maxDailyExposure`: Máx exposição diária % (padrão: 10%)
- `maxSimultaneousPositions`: Máx posições simultâneas (padrão: 5)
- `maxLeverageLimit`: Limite máx de alavancagem (padrão: 20x)
- `enableStopLoss`: Stop loss automático (padrão: true)
- `enableTakeProfit`: Take profit automático (padrão: true)

##### **3. 📡 API**
- `apiTimeout`: Timeout da API ms (padrão: 5000)
- `enableApiRetry`: Retry automático (padrão: true)
- `maxRetryAttempts`: Máx tentativas (padrão: 3)
- `apiRateLimit`: Rate limit req/min (padrão: 1200)
- Teste de conectividade em tempo real

##### **4. ⚡ Webhooks**
- `webhookDelay`: Delay de execução ms (padrão: 100)
- `enableWebhookRetry`: Retry de webhook (padrão: true)
- `webhookTimeout`: Timeout do webhook ms (padrão: 3000)
- `enableSignalValidation`: Validação de sinais (padrão: true)
- `minVolumeFilter`: Filtro volume mín USDT (padrão: 1000)

##### **5. ⚙️ Avançado**
- `orderExecutionMode`: Market/Limit/Auto (padrão: Auto)
- `customFees`: Taxas maker/taker personalizadas
- `enableSlippage`: Controle de slippage (padrão: true)
- `maxSlippage`: Máx slippage % (padrão: 0.5%)
- `enablePartialFills`: Preenchimento parcial (padrão: true)
- `preferredTimeframes`: Timeframes preferidos

---

### **4. 🔗 SISTEMA DE WEBHOOKS**

#### **WebhooksPage**
**Localização:** `/workspace/apps/web-trading/src/components/pages/WebhooksPage.tsx`

**Funcionalidades:**
- ✅ Listagem de webhooks ativos
- ✅ Criação de novos webhooks
- ✅ Configuração avançada
- ✅ Cópia de URLs
- ✅ Estatísticas de entrega
- ✅ Exclusão de webhooks

**Estatísticas por Webhook:**
- `totalDeliveries`: Total de entregas
- `successfulDeliveries`: Entregas bem-sucedidas
- `failedDeliveries`: Entregas com falha
- `status`: active/paused/disabled/error

#### **CreateWebhookModal**
**Localização:** `/workspace/apps/web-trading/src/components/molecules/CreateWebhookModal.tsx`

**Seções de Configuração:**

##### **📝 Informações Básicas**
- `name`: Nome do webhook (obrigatório)
- `description`: Descrição da estratégia
- `exchangeAccountId`: Conta de exchange (obrigatório)
- `strategy`: Tipo de estratégia (scalping, swing, etc.)
- `symbols`: Símbolos suportados (seleção múltipla)
- `status`: Status inicial (active/paused/disabled)

**Estratégias Disponíveis:**
- **Scalping:** Operações rápidas timeframes baixos
- **Swing Trading:** Operações médio prazo
- **Position Trading:** Operações longo prazo
- **Arbitragem:** Explorar diferenças de preço
- **Grid Trading:** Estratégia de grade
- **DCA:** Dollar Cost Average
- **Martingale:** Aumentar posição após perda
- **Personalizada:** Estratégia customizada

##### **🔒 Segurança**
- `enableAuth`: Autenticação HMAC (padrão: true)
- `secretKey`: Chave secreta (gerada automaticamente)
- `enableIPWhitelist`: Whitelist de IPs (padrão: false)
- `allowedIPs`: Array de IPs permitidos

##### **🔍 Processamento de Sinais**
- `enableSignalValidation`: Validação de campos (padrão: true)
- `requiredFields`: Campos obrigatórios (symbol, side, quantity)
- `enableDuplicateFilter`: Filtro duplicatas (padrão: true)
- `duplicateWindowMs`: Janela de duplicata ms (padrão: 5000)

**Campos Obrigatórios Configuráveis:**
- symbol, side, quantity, price, type, timestamp, strategy, leverage, stop_loss, take_profit

##### **⚠️ Gestão de Risco**
- `enableRiskLimits`: Aplicar limites (padrão: true)
- `maxOrdersPerMinute`: Máx ordens/minuto (padrão: 10)
- `maxDailyOrders`: Máx ordens/dia (padrão: 500)
- `minOrderSize`: Tamanho mín USDT (padrão: 10)
- `maxOrderSize`: Tamanho máx USDT (padrão: 1000)

##### **⚡ Execução**
- `executionDelay`: Delay de execução ms (padrão: 100)
- `enableRetry`: Retry automático (padrão: true)
- `maxRetries`: Máx tentativas (padrão: 3)
- `retryDelayMs`: Delay entre tentativas (padrão: 1000)
- `timeoutMs`: Timeout ms (padrão: 5000)

##### **🚀 Funcionalidades Especiais**
- **Geração automática de URL**: Cria URL única do webhook
- **Botão copiar URL**: Copia URL para clipboard
- **Gerador de secret key**: Gera chave segura automaticamente
- **Validação completa**: Valida todos os campos obrigatórios
- **Preview de configuração**: Mostra resumo antes de salvar

#### **ConfigureWebhookModal**
**Localização:** `/workspace/apps/web-trading/src/components/molecules/ConfigureWebhookModal.tsx`

**5 Abas Avançadas:**

##### **1. 🏠 Geral**
- Configurações básicas e status
- Validação de sinais
- Filtros por símbolo e horário
- Trading em fins de semana

##### **2. 🛡️ Segurança**
- Autenticação HMAC
- Rotação de secret key
- Whitelist de IPs
- Rate limiting
- Validação de timestamp

##### **3. ⚠️ Risco**
- Limites de ordens e volume
- Controle de posições
- Exposição máxima por símbolo
- Proteções automáticas

##### **4. ⚡ Execução**
- Modos de execução (Imediato/Delayed/Condicional)
- Controle de slippage
- Sistema de retry inteligente
- Configurações de latência

##### **5. 📊 Monitoramento**
- Níveis de logging (Debug, Info, Warning, Error)
- Notificações multi-canal
- Alertas de performance
- Monitoramento de latência

---

## 🔧 **COMPONENTES REUTILIZÁVEIS**

### **Atoms (Componentes Básicos)**
- `Button`: Botões com variantes (primary, outline, danger, etc.)
- `Input`: Campos de entrada com validação
- `Badge`: Etiquetas coloridas para status
- `LoadingSpinner`: Indicador de carregamento
- `Card`: Cards com header, content e description
- `Dialog`: Modais responsivos
- `Select`: Dropdown com search
- `Switch`: Toggle switches
- `Label`: Labels semânticas

### **Molecules (Componentes Compostos)**
- `FormField`: Campo de formulário completo
- `PriceDisplay`: Exibição formatada de preços
- `OrderCard`: Card de ordem com status
- `NotificationCenter`: Central de notificações
- `DemoBanner`: Banner de modo demo

### **Organisms (Componentes Complexos)**
- `PositionsTable`: Tabela completa de posições
- `DashboardLayout`: Layout com sidebar e header
- `AuthLayout`: Layout de páginas de autenticação

---

## 🎯 **REGRAS DE NEGÓCIO**

### **Autenticação**
- Login obrigatório para acesso
- Suporte a 2FA opcional
- Tokens JWT com expiração
- Redirecionamento automático

### **Contas de Exchange**
- API Keys criptografadas
- Validação de permissões
- Suporte a testnet/mainnet
- Uma conta padrão por exchange

### **Webhooks**
- URLs únicas e seguras
- Autenticação HMAC obrigatória
- Limites de rate por webhook
- Logs completos de atividade

### **Trading**
- Validação de saldo antes execução
- Limites de risco por conta
- Stop loss/take profit automáticos
- Retry em caso de falha

### **Segurança**
- Todas as senhas são hash
- API Keys são criptografadas
- Rate limiting por IP
- Logs de segurança

---

## 📊 **ESTRUTURA DE DADOS**

### **User**
```typescript
interface User {
  id: string
  email: string
  name: string
  isActive: boolean
  isVerified: boolean
  totpEnabled: boolean
  createdAt: string
  lastLoginAt: string | null
}
```

### **ExchangeAccount**
```typescript
interface ExchangeAccount {
  id: string
  name: string
  exchange: 'binance' | 'bybit' | 'okx' | 'coinbase' | 'bitget'
  apiKey: string (encrypted)
  secretKey: string (encrypted)
  passphrase?: string (encrypted)
  testnet: boolean
  isActive: boolean
  isDefault: boolean
  userId: string
  createdAt: string
  updatedAt: string
}
```

### **Webhook**
```typescript
interface Webhook {
  id: string
  name: string
  description: string
  urlPath: string
  secretKey: string
  exchangeAccountId: string
  strategy: string
  symbols: string[]
  status: 'active' | 'paused' | 'disabled'
  totalDeliveries: number
  successfulDeliveries: number
  failedDeliveries: number
  userId: string
  createdAt: string
  updatedAt: string
}
```

### **Order**
```typescript
interface Order {
  id: string
  clientOrderId: string
  symbol: string
  side: 'buy' | 'sell'
  type: 'market' | 'limit' | 'stop' | 'take_profit'
  status: 'pending' | 'open' | 'filled' | 'cancelled' | 'rejected'
  quantity: number
  price: number
  filledQuantity: number
  averageFillPrice: number | null
  feesPaid: number
  feeCurrency: string | null
  source: 'manual' | 'webhook' | 'bot'
  exchangeAccountId: string
  userId: string
  createdAt: string
  updatedAt: string
}
```

### **Position**
```typescript
interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  status: 'open' | 'closed'
  size: number
  entryPrice: number
  markPrice: number
  unrealizedPnl: number
  realizedPnl: number
  initialMargin: number
  maintenanceMargin: number
  leverage: number
  liquidationPrice: number
  exchangeAccountId: string
  userId: string
  openedAt: string
  closedAt: string | null
  createdAt: string
  updatedAt: string
}
```

---

## 🔌 **INTEGRAÇÕES DE API**

### **Exchanges Suportadas**
- **Binance Spot & Futures** ✅ **IMPLEMENTADO E FUNCIONANDO**
- **Bybit USDT Perpetual**
- **OKX Futures**
- **Coinbase Pro**
- **Bitget Futures**

### **🎯 INTEGRAÇÃO BINANCE - IMPLEMENTAÇÃO COMPLETA**

#### **📊 Dashboard Cards com Dados Reais**
Sistema completo de sincronização e exibição de dados reais da Binance implementado em 20/01/2025:

**Arquivos Principais:**
- `apps/api-python/presentation/controllers/dashboard_cards_controller.py` - Endpoint de cards
- `apps/api-python/infrastructure/exchanges/binance_connector.py` - Conector Binance
- `apps/api-python/create_trades_table_and_sync.py` - Sincronização de trades
- `frontend-new/src/hooks/useApiData.ts` - Hook para dados reais
- `frontend-new/src/components/pages/DashboardPage.tsx` - Exibição no frontend

**Dados Sincronizados:**
- ✅ **Saldo Futures**: Total em USDT + P&L diário realizado
- ✅ **Saldo Spot**: Total em USDT + contagem de ativos
- ✅ **P&L Total**: Soma do P&L diário de Futures + Spot
- ✅ **Posições Ativas**: Posições abertas em tempo real
- ✅ **Ordens**: Total de ordens e ordens do dia

**Endpoint Principal:**
```
GET /api/v1/dashboard/cards
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "futures": {
      "value": 710.36638042,
      "daily_pnl_realized": -46.78766007
    },
    "spot": {
      "value": 1730.56718875,
      "total_assets": 28
    },
    "pnl_total": {
      "value": -46.78766007
    },
    "positions_active": {
      "value": 3
    },
    "orders_total": {
      "value": 0
    },
    "orders_today": {
      "value": 61
    }
  }
}
```

**Features Implementadas:**
- 🔄 **Auto-refresh**: Dados atualizados a cada 10 segundos
- 📊 **Dados reais**: Sem mock data, apenas dados do banco
- 💹 **P&L diário**: Calculado a partir dos trades realizados
- 🏦 **Multi-conta**: Suporte para múltiplas contas Binance
- 🔐 **Segurança**: API keys criptografadas com AES-256

**Sincronização de Trades:**
- Tabela `daily_trades` criada para tracking de P&L
- Sync automático de trades Futures da Binance
- Cálculo de P&L realizado por dia
- 61 trades sincronizados com sucesso

**Frontend Integration:**
- Hook `useDashboardCards()` implementado
- React Query para cache e auto-refresh
- Cards responsivos com dados em tempo real
- Debug logs para troubleshooting

#### **🔧 Fixes e Ajustes Implementados**

**1. Correção da Estrutura de Resposta da API:**
```typescript
// apiClient.get() modificado para extrair dados corretamente
const apiResponse = response.data as any
if (apiResponse.success && apiResponse.data) {
  return apiResponse.data as T
}
```

**2. Resolução de Conflito de Cards Duplicados:**
- Removidos cards obsoletos que usavam `balancesSummary`
- Mantidos apenas cards que usam `dashboardCards`
- Eliminada duplicação de componentes Futures/Spot

**3. Import Missing no Hook:**
```typescript
// Adicionado import essencial
import { apiClient } from '@/lib/api'
```

**4. Configuração do Hook com Debug:**
```typescript
export const useDashboardCards = () => {
  return useQuery({
    queryKey: ['dashboard-cards'],
    queryFn: async () => {
      console.log('🔍 Dashboard Cards: Fazendo chamada para API...')
      const response = await apiClient.get('/dashboard/cards')
      console.log('✅ Dashboard Cards: Resposta recebida:', response)
      return response
    },
    refetchInterval: 10000, // Auto-refresh a cada 10s
    staleTime: 5000,
  })
}
```

**5. Mapeamento Correto dos Dados:**
```typescript
const stats = {
  futuresBalance: dashboardCards?.futures?.value || 0,
  futuresPnL: dashboardCards?.futures?.daily_pnl_realized || 0,
  spotBalance: dashboardCards?.spot?.value || 0,
  spotAssets: dashboardCards?.spot?.total_assets || 0,
  totalPnL: dashboardCards?.pnl_total?.value || 0,
  activePositions: dashboardCards?.positions_active?.value || 0,
  totalOrders: dashboardCards?.orders_total?.value || 0,
  todayOrders: dashboardCards?.orders_today?.value || 0,
}
```

**Status Atual: ✅ FUNCIONANDO PERFEITAMENTE**
- Dados reais da Binance exibidos no dashboard
- Auto-refresh funcionando
- P&L calculado corretamente
- Sem mock data

#### **🔄 FLUXO COMPLETO: BACKEND → FRONTEND**

**Passo-a-passo de como os dados chegam no frontend:**

**1. 📊 Backend - Coleta de Dados:**
```python
# apps/api-python/presentation/controllers/dashboard_cards_controller.py
@router.get("/cards")
async def get_dashboard_cards():
    # 1. Busca dados da Binance via connector
    futures_balance = await binance_connector.get_futures_balance()
    spot_balance = await binance_connector.get_spot_balance()

    # 2. Calcula P&L do banco de dados
    daily_pnl = await calculate_daily_pnl_from_trades()

    # 3. Retorna estrutura padronizada
    return {
        "success": True,
        "data": {
            "futures": {"value": 710.37, "daily_pnl_realized": -46.79},
            "spot": {"value": 1730.57, "total_assets": 28},
            "pnl_total": {"value": -46.79}
        }
    }
```

**2. 🌐 API Client - Interceptação e Parsing:**
```typescript
// frontend-new/src/lib/api.ts
async get<T>(url: string): Promise<T> {
    const response = await this.instance.get<ApiResponse<T>>(url)

    // EXTRAI dados da estrutura { success: true, data: {...} }
    const apiResponse = response.data as any
    if (apiResponse.success && apiResponse.data) {
        return apiResponse.data as T  // ← Retorna APENAS os dados úteis
    }
    return response.data as T
}
```

**3. 🎣 React Hook - Chamada da API:**
```typescript
// frontend-new/src/hooks/useApiData.ts
export const useDashboardCards = () => {
  return useQuery({
    queryKey: ['dashboard-cards'],
    queryFn: async () => {
      console.log('🔍 Fazendo chamada para /dashboard/cards...')

      // Chama API através do apiClient
      const response = await apiClient.get('/dashboard/cards')

      console.log('✅ Dados recebidos:', response)
      return response  // ← Dados já extraídos pelo apiClient
    },
    refetchInterval: 10000, // ← Auto-refresh a cada 10s
    staleTime: 5000,
  })
}
```

**4. ⚛️ Componente React - Consumo dos Dados:**
```typescript
// frontend-new/src/components/pages/DashboardPage.tsx
const DashboardPage = () => {
  // Hook puxa dados automaticamente
  const { data: dashboardCards, isLoading, error } = useDashboardCards()

  // Mapeia dados para stats
  const stats = {
    futuresBalance: dashboardCards?.futures?.value || 0,        // 710.37
    futuresPnL: dashboardCards?.futures?.daily_pnl_realized || 0, // -46.79
    spotBalance: dashboardCards?.spot?.value || 0,              // 1730.57
    totalPnL: dashboardCards?.pnl_total?.value || 0,           // -46.79
  }

  return (
    <Card>
      <CardContent>
        <div className="text-2xl font-bold">
          ${stats.futuresBalance.toFixed(2)}  {/* ← Exibe: $710.37 */}
        </div>
      </CardContent>
    </Card>
  )
}
```

**5. 🔄 Configuração do Proxy (Vite):**
```typescript
// frontend-new/vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // ← Redireciona para backend
      changeOrigin: true,
    }
  }
}
```

**SEQUÊNCIA COMPLETA:**
1. **React Query** dispara chamada a cada 10s
2. **Hook** chama `apiClient.get('/dashboard/cards')`
3. **Vite Proxy** redireciona para `http://localhost:8000/api/v1/dashboard/cards`
4. **Backend** consulta Binance + banco e retorna dados
5. **API Client** extrai dados da estrutura `{success: true, data: {...}}`
6. **React Query** atualiza cache e re-renderiza componente
7. **Dashboard** exibe dados atualizados em tempo real

**RESULTADO FINAL:**
- 🎯 Dados reais da Binance no frontend
- 🔄 Atualização automática a cada 10 segundos
- ⚡ Cache inteligente com React Query
- 🛡️ Tratamento de erros e loading states

### **Endpoints Principais**
```
GET    /api/v1/health                     - Health check
POST   /api/v1/auth/login                 - Login
GET    /api/v1/auth/me                    - User profile
GET    /api/v1/accounts                   - Exchange accounts
POST   /api/v1/accounts                   - Create account
PUT    /api/v1/accounts/{id}/config       - Configure account
GET    /api/v1/webhooks                   - List webhooks
POST   /api/v1/webhooks                   - Create webhook
PUT    /api/v1/webhooks/{id}/config       - Configure webhook
POST   /api/v1/webhooks/tradingview/{id}  - Receive signals
GET    /api/v1/orders                     - List orders
GET    /api/v1/positions                  - List positions
GET    /api/v1/dashboard/cards            - ✅ Dashboard cards (Binance data)
```

---

## 🛡️ **SEGURANÇA**

### **Criptografia**
- Senhas: bcrypt hash
- API Keys: AES-256 encryption
- JWTs: RS256 signature
- HMAC: SHA-256

### **Validação**
- Input sanitization
- Schema validation (Pydantic)
- Rate limiting
- CORS protection

### **Auditoria**
- Logs estruturados
- Activity tracking
- Error monitoring
- Performance metrics

---

## 🧪 **TESTES**

### **Frontend**
- Unit tests com Jest
- Component tests com Testing Library
- E2E tests com Cypress
- Snapshot tests

### **Backend**
- Unit tests com pytest
- Integration tests
- API tests
- Load tests

### **Cobertura Mínima**
- 80% code coverage
- Critical paths 100%
- Edge cases covered

---

## 📦 **DEPLOYMENT**

### **Ambientes**
- **Development:** Local com Docker
- **Staging:** Docker Compose
- **Production:** Kubernetes

### **CI/CD Pipeline**
1. Lint & Format
2. Unit Tests
3. Integration Tests
4. Security Scan
5. Build Docker Images
6. Deploy to Environment
7. Health Checks

### **Monitoramento**
- Prometheus metrics
- Grafana dashboards
- ELK stack logs
- Alertmanager notifications

---

## 📈 **MÉTRICAS E KPIs**

### **Performance**
- Response time < 200ms
- Uptime > 99.9%
- Error rate < 0.1%
- Throughput > 1000 req/s

### **Business**
- Total trades executed
- Success rate
- P&L metrics
- User engagement

### **Technical**
- API latency
- Database performance
- Memory usage
- CPU utilization

---

## 🚀 **ROADMAP FUTURO**

### **Fase 2 - Core Features**
- [ ] Implementação completa do backend
- [ ] Integração real com exchanges
- [ ] Sistema de persistência
- [ ] Testes automatizados

### **Fase 3 - Advanced Features**
- [ ] Backtesting engine
- [ ] Copy trading
- [ ] Portfolio management
- [ ] Advanced analytics

### **Fase 4 - Scale & Optimization**
- [ ] Microservices architecture
- [ ] Redis caching
- [ ] WebSocket real-time
- [ ] Mobile app

---

## 📞 **SUPORTE TÉCNICO**

### **Arquivos de Configuração**
- `package.json`: Dependências frontend
- `requirements.txt`: Dependências backend
- `docker-compose.yml`: Orquestração containers
- `CLAUDE.md`: Instruções para desenvolvimento
- `.env.example`: Variáveis de ambiente

### **Comandos Principais**
```bash
# Frontend
npm install
npm run dev

# Backend
pip install -r requirements.txt
python simple_server.py

# Docker
docker compose up
docker compose down
```

### **Troubleshooting**
- Logs no console do navegador
- Logs do backend no terminal
- Verificar variáveis de ambiente
- Testar conectividade API

---

## 📄 **CONCLUSÃO**

Este documento representa o estado atual completo da plataforma de trading automatizada. O sistema está estruturado com padrões modernos de desenvolvimento, arquitetura limpa e foco em segurança e performance.

**Status Atual:** Interface completa funcional com backend mockado  
**Próximo Passo:** Implementação do backend real com integrações de exchange  
**Objetivo:** Sistema de produção para automação de trading via TradingView  

---

*Documento gerado em 20/01/2025 - Versão 1.0.0*