# 🤖 ANÁLISE DAS TABELAS DE BOTS

## 📋 Resumo Executivo

Foram encontradas **4 tabelas** relacionadas ao sistema de bots:

1. **`bots`** - Configuração Master dos bots criados no Admin
2. **`bot_subscriptions`** - Assinaturas dos usuários aos bots (ativação)
3. **`bot_signals`** - Sinais recebidos do TradingView
4. **`bot_signal_executions`** - Execuções individuais por usuário

---

## 🔗 MAPA DE RELACIONAMENTOS

```
┌─────────────────────────────────────────────────────────────────┐
│                         BOTS (Master)                           │
│  • Criado no Admin                                              │
│  • Configuração default (leverage, margin, SL/TP)              │
│  • master_webhook_path (URL única)                             │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴──────────┐
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌──────────────────────┐
│  BOT_SIGNALS    │    │ BOT_SUBSCRIPTIONS    │
│  • TradingView  │    │  • User ativa bot    │
│  • Broadcast    │    │  • Escolhe exchange  │
└────────┬────────┘    │  • Config custom     │
         │             └──────────┬───────────┘
         │                        │
         │                        │ exchange_account_id
         │                        │        ↓
         │                 ┌──────────────────────┐
         │                 │  EXCHANGE_ACCOUNTS   │
         │                 │  • Credenciais API   │
         │                 └──────────────────────┘
         │
         └──────────┬─────────────┘
                    ▼
         ┌──────────────────────┐
         │ BOT_SIGNAL_EXECUTIONS│
         │  • 1 por user        │
         │  • Status individual │
         └──────────────────────┘
```

---

## 📊 ANÁLISE DETALHADA DE CADA TABELA

### 1️⃣ TABELA: `bots` (Master Configuration)

**Propósito:** Configuração master dos bots criados no Admin

**Colunas (17 total):**

| Coluna | Tipo | Necessária? | Análise |
|--------|------|-------------|---------|
| `id` | UUID | ✅ SIM | PK - OK |
| `name` | VARCHAR(255) | ✅ SIM | Nome do bot - OK |
| `description` | TEXT | ⚠️ OPCIONAL | Descrição longa - pode ficar |
| `market_type` | VARCHAR(50) | ✅ SIM | 'futures'/'spot' - IMPORTANTE |
| `status` | VARCHAR(50) | ✅ SIM | 'active'/'archived' - OK |
| `master_webhook_path` | VARCHAR(255) | ✅ SIM | URL única do bot - CRÍTICO |
| `default_leverage` | INTEGER | ✅ SIM | Config padrão - OK |
| `default_margin_usd` | NUMERIC | ✅ SIM | Config padrão - OK |
| `default_stop_loss_pct` | NUMERIC | ✅ SIM | Config padrão - OK |
| `default_take_profit_pct` | NUMERIC | ✅ SIM | Config padrão - OK |
| `total_subscribers` | INTEGER | ⚠️ DESNORM | Contador - redundante (pode calcular) |
| `total_signals_sent` | INTEGER | ⚠️ DESNORM | Contador - redundante (pode calcular) |
| `avg_win_rate` | NUMERIC | ⚠️ DESNORM | Métrica - redundante (pode calcular) |
| `avg_pnl_pct` | NUMERIC | ⚠️ DESNORM | Métrica - redundante (pode calcular) |
| `created_at` | TIMESTAMP | ✅ SIM | Auditoria - OK |
| `updated_at` | TIMESTAMP | ✅ SIM | Auditoria - OK |
| `allowed_directions` | VARCHAR(20) | ✅ SIM | 'both'/'long'/'short' - IMPORTANTE |

**❌ PROBLEMAS IDENTIFICADOS:**

1. **FALTA COLUNA CRÍTICA:** `ticker` ou `symbol`
   - **Problema:** Sua regra diz "um bot por ativo" mas não tem coluna para armazenar qual ativo!
   - **Impacto:** Como saber se o bot é de BTC, ETH, BNB?
   - **Solução:** Adicionar `ticker VARCHAR(50) NOT NULL`

2. **FALTA COLUNA CRÍTICA:** `exchange`
   - **Problema:** Sua regra diz "um bot por exchange" mas não tem coluna para armazenar qual exchange!
   - **Impacto:** Como saber se o bot é para Binance, BingX, Bybit?
   - **Solução:** Adicionar `exchange VARCHAR(50) NOT NULL` (ou ENUM)

3. **Colunas desnormalizadas:**
   - `total_subscribers`, `total_signals_sent`, `avg_win_rate`, `avg_pnl_pct`
   - Podem ser calculadas via queries agregadas
   - Se mantidas, criar triggers para atualizar automaticamente

**✅ PONTOS POSITIVOS:**

- Configurações default bem definidas
- `master_webhook_path` único (critical for TradingView)
- `allowed_directions` permite controlar tipo de operações

---

### 2️⃣ TABELA: `bot_subscriptions` (User Activation)

**Propósito:** Registro de ativação do bot pelo usuário

**Colunas (22 total):**

| Coluna | Tipo | Necessária? | Análise |
|--------|------|-------------|---------|
| `id` | UUID | ✅ SIM | PK - OK |
| `user_id` | UUID | ✅ SIM | FK users - OK |
| `bot_id` | UUID | ✅ SIM | FK bots - OK |
| `exchange_account_id` | UUID | ✅ SIM | FK exchange_accounts - CRÍTICO |
| `status` | VARCHAR(50) | ✅ SIM | 'active'/'paused'/'cancelled' - OK |
| `custom_leverage` | INTEGER | ✅ SIM | Override config - OK |
| `custom_margin_usd` | NUMERIC | ✅ SIM | Override config - OK |
| `custom_stop_loss_pct` | NUMERIC | ✅ SIM | Override config - OK |
| `custom_take_profit_pct` | NUMERIC | ✅ SIM | Override config - OK |
| `max_daily_loss_usd` | NUMERIC | ✅ SIM | Risk management - IMPORTANTE |
| `max_concurrent_positions` | INTEGER | ✅ SIM | Risk management - IMPORTANTE |
| `current_daily_loss_usd` | NUMERIC | ⚠️ CACHE | Contador - melhor calcular real-time |
| `current_positions` | INTEGER | ⚠️ CACHE | Contador - melhor calcular real-time |
| `total_signals_received` | INTEGER | ⚠️ DESNORM | Contador - redundante |
| `total_orders_executed` | INTEGER | ⚠️ DESNORM | Contador - redundante |
| `total_orders_failed` | INTEGER | ⚠️ DESNORM | Contador - redundante |
| `total_pnl_usd` | NUMERIC | ⚠️ DESNORM | Métrica - redundante |
| `win_count` | INTEGER | ⚠️ DESNORM | Métrica - redundante |
| `loss_count` | INTEGER | ⚠️ DESNORM | Métrica - redundante |
| `created_at` | TIMESTAMP | ✅ SIM | Auditoria - OK |
| `updated_at` | TIMESTAMP | ✅ SIM | Auditoria - OK |
| `last_signal_at` | TIMESTAMP | ⚠️ OPCIONAL | Info útil mas redundante |

**❌ PROBLEMAS IDENTIFICADOS:**

1. **CONSTRAINT FALTANDO:** Unicidade `(user_id, bot_id, exchange_account_id)`
   - **Problema:** Tem constraint `unique_user_bot (user_id, bot_id)` mas deveria incluir `exchange_account_id`
   - **Impacto:** User não pode ativar mesmo bot em exchanges diferentes!
   - **Solução:**
     - Remover constraint `unique_user_bot`
     - Criar `UNIQUE (user_id, bot_id, exchange_account_id)`

2. **Muitas colunas de cache/desnormalização:**
   - `current_daily_loss_usd`, `current_positions`, `total_signals_received`, etc.
   - Difícil manter sincronizado
   - Melhor calcular via queries quando necessário

**✅ PONTOS POSITIVOS:**

- Link correto com `exchange_accounts` ✅
- Permite override de configurações do bot
- Risk management bem pensado (max_daily_loss, max_concurrent_positions)

---

### 3️⃣ TABELA: `bot_signals` (TradingView Alerts)

**Propósito:** Armazenar sinais recebidos do TradingView

**Colunas (14 total):**

| Coluna | Tipo | Necessária? | Análise |
|--------|------|-------------|---------|
| `id` | UUID | ✅ SIM | PK - OK |
| `bot_id` | UUID | ✅ SIM | FK bots - OK |
| `ticker` | VARCHAR(50) | ✅ SIM | BTCUSDT, ETHUSDT - OK |
| `action` | VARCHAR(50) | ✅ SIM | 'buy'/'sell'/'close' - OK |
| `price` | NUMERIC | ⚠️ OPCIONAL | Preço do alerta - pode ser útil |
| `total_subscribers` | INTEGER | ⚠️ DESNORM | Contador - redundante |
| `successful_executions` | INTEGER | ⚠️ DESNORM | Contador - redundante |
| `failed_executions` | INTEGER | ⚠️ DESNORM | Contador - redundante |
| `broadcast_duration_ms` | INTEGER | ⚠️ OPCIONAL | Métrica de performance - útil |
| `source` | VARCHAR(50) | ✅ SIM | 'tradingview'/'manual' - OK |
| `source_ip` | VARCHAR(50) | ⚠️ OPCIONAL | Segurança - pode ser útil |
| `payload` | JSONB | ✅ SIM | JSON completo do alerta - IMPORTANTE |
| `created_at` | TIMESTAMP | ✅ SIM | Quando recebeu - CRÍTICO |
| `completed_at` | TIMESTAMP | ⚠️ OPCIONAL | Quando terminou broadcast - útil |

**❌ PROBLEMAS IDENTIFICADOS:**

1. **Validação de ticker:**
   - Sem constraint para validar se `ticker` bate com o ativo do bot
   - Se bot é de BTC, não deveria aceitar sinal de ETH

2. **Colunas desnormalizadas:**
   - `total_subscribers`, `successful_executions`, `failed_executions`
   - Podem ser calculadas via JOIN com `bot_signal_executions`

**✅ PONTOS POSITIVOS:**

- `payload` JSONB guarda tudo - excelente para debug
- Índice em `ticker` - bom para buscar sinais por ativo
- `broadcast_duration_ms` - métrica útil para monitorar performance

---

### 4️⃣ TABELA: `bot_signal_executions` (Individual Executions)

**Propósito:** Execução individual do sinal para cada usuário inscrito

**Colunas (17 total):**

| Coluna | Tipo | Necessária? | Análise |
|--------|------|-------------|---------|
| `id` | UUID | ✅ SIM | PK - OK |
| `signal_id` | UUID | ✅ SIM | FK bot_signals - OK |
| `subscription_id` | UUID | ✅ SIM | FK bot_subscriptions - OK |
| `user_id` | UUID | ✅ SIM | Para joins rápidos - OK |
| `status` | VARCHAR(50) | ✅ SIM | 'success'/'failed'/'pending' - OK |
| `exchange_order_id` | VARCHAR(255) | ✅ SIM | Order ID da exchange - CRÍTICO |
| `executed_price` | NUMERIC | ✅ SIM | Preço real executado - OK |
| `executed_quantity` | NUMERIC | ✅ SIM | Quantidade executada - OK |
| `error_message` | TEXT | ✅ SIM | Debug de falhas - IMPORTANTE |
| `error_code` | VARCHAR(50) | ⚠️ OPCIONAL | Código de erro - útil |
| `execution_time_ms` | INTEGER | ⚠️ OPCIONAL | Performance - útil |
| `created_at` | TIMESTAMP | ✅ SIM | Quando iniciou - OK |
| `completed_at` | TIMESTAMP | ✅ SIM | Quando terminou - OK |
| `stop_loss_order_id` | VARCHAR(255) | ✅ SIM | Order ID do SL - IMPORTANTE |
| `take_profit_order_id` | VARCHAR(255) | ✅ SIM | Order ID do TP - IMPORTANTE |
| `stop_loss_price` | NUMERIC | ⚠️ OPCIONAL | Preço do SL - útil para histórico |
| `take_profit_price` | NUMERIC | ⚠️ OPCIONAL | Preço do TP - útil para histórico |

**❌ PROBLEMAS IDENTIFICADOS:**

1. **FALTA COLUNA:** `exchange_account_id`
   - **Problema:** Não armazena qual conta foi usada!
   - **Impacto:** Precisa fazer JOIN com `bot_subscriptions` para saber
   - **Solução:** Adicionar `exchange_account_id UUID NOT NULL` + FK
   - **Benefício:** Queries mais rápidas, dados mais claros

**✅ PONTOS POSITIVOS:**

- Índices excelentes (signal, subscription, user, status)
- Armazena SL/TP order IDs - essencial para gerenciar posições
- `error_message` - crítico para debug
- Índices parciais em SL/TP (WHERE NOT NULL) - otimização inteligente

---

## 🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS

### 1. **Tabela `bots` - FALTAM COLUNAS ESSENCIAIS**

❌ **Problema:** Bot não armazena `ticker` nem `exchange`

**Sua regra:** "um bot por ativo e um bot por exchange"

**Realidade:** Tabela `bots` não tem essas colunas!

**Exemplo do problema:**
```
Bot: "TPO_BTC"
- Qual ativo? ❌ Não está na tabela
- Qual exchange? ❌ Não está na tabela
- Como validar sinais? ❌ Impossível
```

**Solução:**
```sql
ALTER TABLE bots
ADD COLUMN ticker VARCHAR(50) NOT NULL,
ADD COLUMN exchange VARCHAR(50) NOT NULL,
ADD CONSTRAINT unique_bot_ticker_exchange UNIQUE (ticker, exchange);
```

---

### 2. **Tabela `bot_subscriptions` - CONSTRAINT ERRADO**

❌ **Problema:** Constraint `unique_user_bot (user_id, bot_id)` não permite múltiplas exchanges

**Sua regra:** User pode ativar mesmo bot em exchanges diferentes

**Realidade:** Constraint atual impede isso!

**Exemplo do problema:**
```
User Marcus quer ativar "Bot BTC" em:
- Binance ✅ (primeira ativação)
- BingX ❌ ERRO: "duplicate key unique_user_bot"
```

**Solução:**
```sql
-- Remover constraint errado
DROP INDEX unique_user_bot;

-- Criar constraint correto
CREATE UNIQUE INDEX unique_user_bot_exchange
ON bot_subscriptions (user_id, bot_id, exchange_account_id);
```

---

### 3. **Tabela `bot_signal_executions` - FALTA exchange_account_id**

❌ **Problema:** Não armazena qual conta exchange foi usada

**Impacto:**
- Queries lentas (precisa JOIN com bot_subscriptions)
- Dados incompletos para auditoria
- Difícil rastrear problemas por conta

**Solução:**
```sql
ALTER TABLE bot_signal_executions
ADD COLUMN exchange_account_id UUID NOT NULL
  REFERENCES exchange_accounts(id);

CREATE INDEX idx_bot_signal_executions_exchange
ON bot_signal_executions(exchange_account_id);
```

---

## 📊 ANÁLISE DE DESNORMALIZAÇÃO

**Colunas desnormalizadas encontradas:**

### Tabela `bots`:
- `total_subscribers` ← COUNT em bot_subscriptions
- `total_signals_sent` ← COUNT em bot_signals
- `avg_win_rate` ← Calculável via executions
- `avg_pnl_pct` ← Calculável via executions

### Tabela `bot_subscriptions`:
- `current_daily_loss_usd` ← Soma de executions hoje
- `current_positions` ← COUNT de posições abertas
- `total_signals_received` ← COUNT de executions
- `total_orders_executed` ← COUNT de executions success
- `total_orders_failed` ← COUNT de executions failed
- `total_pnl_usd` ← Soma de P&L
- `win_count` ← COUNT de wins
- `loss_count` ← COUNT de losses

### Tabela `bot_signals`:
- `total_subscribers` ← COUNT de executions
- `successful_executions` ← COUNT WHERE status = success
- `failed_executions` ← COUNT WHERE status = failed

**⚠️ Recomendação:**
- **Desenvolvimento:** Remover desnormalização, calcular via queries
- **Produção (se necessário):** Manter com triggers automáticos

---

## ✅ ESTRUTURA CORRETA PROPOSTA

### REGRA DE NEGÓCIO (do usuário):

1. ✅ Admin cria bot com configuração master
2. ✅ Bot gera URL única (webhook)
3. ✅ TradingView envia alertas para URL
4. ✅ User ativa bot na plataforma
5. ✅ User escolhe exchange ao ativar
6. ✅ User pode usar config default ou customizar
7. ✅ **Um bot por ativo e por exchange**
8. ✅ Bot executa sinal em todos os users inscritos

### SCHEMA CORRETO:

```sql
-- 1. BOTS (Master Configuration)
CREATE TABLE bots (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    ticker VARCHAR(50) NOT NULL,  -- ⭐ ADICIONAR
    exchange VARCHAR(50) NOT NULL, -- ⭐ ADICIONAR
    description TEXT,
    market_type VARCHAR(50) DEFAULT 'futures',
    status VARCHAR(50) DEFAULT 'active',
    master_webhook_path VARCHAR(255) UNIQUE NOT NULL,
    default_leverage INTEGER DEFAULT 10,
    default_margin_usd NUMERIC DEFAULT 50.00,
    default_stop_loss_pct NUMERIC DEFAULT 2.5,
    default_take_profit_pct NUMERIC DEFAULT 5.0,
    allowed_directions VARCHAR(20) DEFAULT 'both',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_bot_ticker_exchange UNIQUE (ticker, exchange)
);

-- 2. BOT_SUBSCRIPTIONS (User Activation)
CREATE TABLE bot_subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    bot_id UUID NOT NULL REFERENCES bots(id),
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id),
    status VARCHAR(50) DEFAULT 'active',

    -- Custom configs (override bot defaults)
    custom_leverage INTEGER,
    custom_margin_usd NUMERIC,
    custom_stop_loss_pct NUMERIC,
    custom_take_profit_pct NUMERIC,

    -- Risk management
    max_daily_loss_usd NUMERIC DEFAULT 200.00,
    max_concurrent_positions INTEGER DEFAULT 3,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- ⭐ CORRIGIR: Permitir múltiplas exchanges
    CONSTRAINT unique_user_bot_exchange UNIQUE (user_id, bot_id, exchange_account_id)
);

-- 3. BOT_SIGNALS (TradingView Alerts)
CREATE TABLE bot_signals (
    id UUID PRIMARY KEY,
    bot_id UUID NOT NULL REFERENCES bots(id),
    ticker VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    price NUMERIC,
    source VARCHAR(50) DEFAULT 'tradingview',
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. BOT_SIGNAL_EXECUTIONS (Individual Executions)
CREATE TABLE bot_signal_executions (
    id UUID PRIMARY KEY,
    signal_id UUID NOT NULL REFERENCES bot_signals(id),
    subscription_id UUID NOT NULL REFERENCES bot_subscriptions(id),
    user_id UUID NOT NULL,
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id), -- ⭐ ADICIONAR

    status VARCHAR(50) NOT NULL,
    exchange_order_id VARCHAR(255),
    executed_price NUMERIC,
    executed_quantity NUMERIC,

    -- Stop Loss / Take Profit
    stop_loss_order_id VARCHAR(255),
    take_profit_order_id VARCHAR(255),
    stop_loss_price NUMERIC,
    take_profit_price NUMERIC,

    -- Error tracking
    error_message TEXT,
    error_code VARCHAR(50),
    execution_time_ms INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## 🎯 PRÓXIMOS PASSOS RECOMENDADOS

### URGENTE (Bloqueia a regra de negócio):

1. ✅ **Adicionar `ticker` e `exchange` na tabela `bots`**
2. ✅ **Corrigir constraint em `bot_subscriptions`** (permitir múltiplas exchanges)
3. ✅ **Adicionar `exchange_account_id` em `bot_signal_executions`**

### IMPORTANTE (Melhorias de design):

4. ⚠️ **Remover colunas desnormalizadas** (ou criar triggers)
5. ⚠️ **Adicionar validações:**
   - Ticker do sinal deve bater com ticker do bot
   - Exchange da subscription deve bater com exchange do bot

### OPCIONAL (Otimizações):

6. ℹ️ Revisar índices após mudanças
7. ℹ️ Adicionar constraints CHECK para validações de negócio
8. ℹ️ Criar views para queries complexas comuns

---

## 📝 RESUMO FINAL

### ✅ O QUE ESTÁ BOM:

- Estrutura geral bem pensada
- Separação clara de responsabilidades
- Link correto `bot_subscriptions → exchange_accounts`
- Índices bem planejados
- Sistema de SL/TP bem desenhado

### ❌ O QUE PRECISA CORRIGIR:

1. **`bots`:** FALTA `ticker` e `exchange` (CRÍTICO)
2. **`bot_subscriptions`:** Constraint errado impede múltiplas exchanges (CRÍTICO)
3. **`bot_signal_executions`:** FALTA `exchange_account_id` (IMPORTANTE)
4. **Todas:** Muitas colunas desnormalizadas (REFATORAR)

### 🎯 ADERÊNCIA À REGRA DE NEGÓCIO:

| Regra | Status | Observação |
|-------|--------|------------|
| Admin cria bot com config | ✅ OK | Tabela `bots` bem estruturada |
| Bot gera URL única | ✅ OK | `master_webhook_path` unique |
| TradingView envia alertas | ✅ OK | Tabela `bot_signals` adequada |
| User ativa bot | ✅ OK | Tabela `bot_subscriptions` |
| User escolhe exchange | ✅ OK | Campo `exchange_account_id` |
| Config default ou custom | ✅ OK | Campos `custom_*` |
| **Um bot por ativo/exchange** | ❌ ERRO | FALTA constraint e colunas |
| Broadcast para todos users | ✅ OK | Sistema de executions |

**Aderência geral:** 87.5% (7 de 8 regras OK)
