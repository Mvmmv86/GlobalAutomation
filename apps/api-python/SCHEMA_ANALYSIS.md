# 📊 Análise de Schema - O que já existe vs O que precisa

## 🟢 **O que NÃO precisa alterar no Supabase**

### 1. **Schemas Pydantic** (Apenas validação Python)
- ✅ `CompleteTradingViewWebhook` - Modelo de validação de dados
- ✅ `AccountConfiguration` - Modelo de configuração de conta  
- ✅ `WebhookConfiguration` - Modelo de configuração de webhook
- ✅ Todos os schemas em `/presentation/schemas/`

**Estes são apenas para validação de dados no Python - não vão para o banco!**

---

## 🟡 **O que JÁ EXISTE no Supabase** (não precisa alterar)

### Tabelas já criadas:
1. ✅ **`users`** - Usuários do sistema
2. ✅ **`webhooks`** - Configurações de webhook básicas
3. ✅ **`webhook_deliveries`** - Histórico de entregas
4. ✅ **`exchange_accounts`** - Contas de exchange
5. ✅ **`orders`** - Ordens executadas
6. ✅ **`positions`** - Posições abertas

---

## 🔴 **O que PRECISA ADICIONAR no Supabase**

### 1. **Campos para armazenar configurações JSON**

#### Na tabela `webhooks`:
```sql
-- Adicionar colunas JSON para configurações
ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS webhook_config JSONB DEFAULT '{}';
ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS account_config JSONB DEFAULT '{}';
ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS risk_config JSONB DEFAULT '{}';
```

#### Na tabela `exchange_accounts`:
```sql  
-- Adicionar configurações de trading
ALTER TABLE exchange_accounts ADD COLUMN IF NOT EXISTS trading_config JSONB DEFAULT '{}';
ALTER TABLE exchange_accounts ADD COLUMN IF NOT EXISTS risk_config JSONB DEFAULT '{}';
ALTER TABLE exchange_accounts ADD COLUMN IF NOT EXISTS api_config JSONB DEFAULT '{}';
```

### 2. **Campos específicos que podem estar faltando**

#### Na tabela `webhooks`:
```sql
-- Verificar se existem estes campos
ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS strategy VARCHAR(50) DEFAULT 'scalping';
ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS symbols TEXT[]; -- Array de símbolos
ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS enable_stop_loss BOOLEAN DEFAULT true;
ALTER TABLE webhooks ADD COLUMN IF NOT EXISTS enable_take_profit BOOLEAN DEFAULT true;
```

#### Na tabela `exchange_accounts`:
```sql
-- Configurações básicas de trading
ALTER TABLE exchange_accounts ADD COLUMN IF NOT EXISTS default_leverage INTEGER DEFAULT 10;
ALTER TABLE exchange_accounts ADD COLUMN IF NOT EXISTS margin_mode VARCHAR(20) DEFAULT 'cross';
ALTER TABLE exchange_accounts ADD COLUMN IF NOT EXISTS position_mode VARCHAR(20) DEFAULT 'one-way';
```

---

## 🎯 **Solução Recomendada**

### Opção 1: **Usar campos JSONB** (Recomendado)
```sql
-- Webhooks com configurações flexíveis
UPDATE webhooks SET 
  webhook_config = '{
    "strategy": "scalping",
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "enable_stop_loss": true,
    "enable_take_profit": true,
    "risk_limits": {
      "max_orders_per_minute": 10,
      "max_daily_orders": 100
    }
  }'::jsonb;

-- Exchange accounts com configurações de trading
UPDATE exchange_accounts SET 
  trading_config = '{
    "default_leverage": 10,
    "margin_mode": "cross", 
    "position_mode": "one-way",
    "default_order_size": 1.0
  }'::jsonb;
```

### Opção 2: **Adicionar colunas específicas**
```sql
-- Mais campos específicos (menos flexível)
ALTER TABLE webhooks ADD COLUMN strategy VARCHAR(50);
ALTER TABLE webhooks ADD COLUMN symbols TEXT[];
ALTER TABLE exchange_accounts ADD COLUMN default_leverage INTEGER;
-- etc...
```

---

## 🚀 **Próximos Passos**

### 1. **Você escolhe a abordagem:**
- 🟢 **JSONB** - Mais flexível, menos colunas, configurações dinâmicas
- 🟡 **Colunas específicas** - Mais estruturado, queries mais fáceis

### 2. **Eu posso:**
- ✅ Gerar o SQL para você executar no Supabase
- ✅ Criar migration do Alembic (se preferir)
- ✅ Testar as queries necessárias

### 3. **O que NÃO precisa fazer:**
- ❌ Recriar tabelas existentes
- ❌ Perder dados existentes  
- ❌ Grandes mudanças estruturais

---

## ❓ **Qual abordagem prefere?**

1. **JSONB** - Flexível, guarda configurações como JSON
2. **Colunas específicas** - Estruturado, colunas para cada config
3. **Misto** - Campos principais como colunas + detalhes em JSONB

Posso gerar o SQL exato para você executar no Supabase!