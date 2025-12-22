# Sistema de Estrategias Automatizadas

**Ultima atualizacao:** 22/12/2024
**Status:** Fase 1 (Backend) CONCLUIDA | Fase 2 (Frontend) CONCLUIDA

---

## Objetivo

Sistema interno de geracao de sinais de trading que usa indicadores ja existentes (NDY, RSI, MACD, Bollinger, EMA) para detectar oportunidades e executar trades automaticamente via bot_broadcast_service.

---

## Arquitetura Implementada

```
BINANCE WEBSOCKET (< 1s latencia)
         │
         ▼
┌─────────────────────────────────────┐
│     BinanceWebSocketManager         │
│  (binance_websocket.py)             │
│  - Conexao WebSocket Futures        │
│  - Reconnect automatico             │
│  - Parse KlineData                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    StrategyWebSocketMonitor         │  ◄── NOVO (implementado 21/12)
│  (strategy_websocket_monitor.py)    │
│                                     │
│  1. Carrega estrategias ativas      │
│  2. Subscreve WebSocket por simbolo │
│  3. A cada candle fechado:          │
│     - Calcula indicadores           │
│     - Avalia condicoes              │
│     - Gera sinal se satisfeito      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      bot_broadcast_service          │  ◄── JA EXISTIA
│  - Executa ordem nas exchanges      │
│  - Aplica SL/TP/Leverage            │
│  - Registra trade                   │
└─────────────────────────────────────┘
```

---

## Fase 1 - Backend (CONCLUIDA)

### Tabelas no Supabase (5 tabelas criadas)
- `strategies` - Configuracao geral (nome, simbolos, timeframe, bot_id)
- `strategy_indicators` - Indicadores configurados por estrategia
- `strategy_conditions` - Condicoes de entrada/saida
- `strategy_signals` - Sinais gerados
- `strategy_backtest_results` - Resultados de backtests

### Arquivos Backend

| Arquivo | Status | Descricao |
|---------|--------|-----------|
| `infrastructure/exchanges/binance_websocket.py` | ✅ OK | WebSocket Binance |
| `infrastructure/services/strategy_websocket_monitor.py` | ✅ NOVO | Monitor real-time via WebSocket |
| `infrastructure/services/strategy_engine_service.py` | ✅ OK | Engine com polling (backup) |
| `infrastructure/services/indicator_alert_monitor.py` | ✅ OK | Calculos de indicadores (REUSADO) |
| `infrastructure/services/strategy_service_sql.py` | ✅ NOVO | Service com transaction_db |
| `infrastructure/database/repositories/strategy_sql.py` | ✅ NOVO | Repository SQL direto |
| `presentation/controllers/strategy_controller.py` | ✅ NOVO | API REST completa |
| `main.py` | ✅ MODIFICADO | Inicializa WebSocket monitor |

### Nota sobre Arquitetura
O plano original previa SQLAlchemy ORM, mas foi migrado para `transaction_db` (SQL direto via asyncpg) por compatibilidade com pgBouncer. Esta mudanca foi aprovada e nao afeta a funcionalidade.

### Principio de Nao Duplicacao
Todos os calculos de indicadores sao feitos via `IndicatorAlertMonitor`:
- `_calc_nadaraya_watson_signal()`
- `_calc_rsi_signal()`
- `_calc_macd_signal()`
- `_calc_bollinger_signal()`
- `_calc_ema_cross_signal()`

**NAO FOI CRIADO CODIGO DUPLICADO!**

---

## Fase 2 - Frontend Admin (CONCLUIDA)

### 3 Modos de Configuracao Implementados

```
┌──────────────────────────────────────────────────────────────┐
│                     ADMIN DASHBOARD                          │
│                  /dashboard-admin/strategies                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│   │  VISUAL    │  │   YAML     │  │ PINESCRIPT │            │
│   │  EDITOR    │  │  EDITOR    │  │   MODE     │            │
│   │    ✅      │  │    ✅      │  │    ✅      │            │
│   └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │
│         │               │               │                    │
│         └───────────────┼───────────────┘                    │
│                         ▼                                    │
│         ┌───────────────────────────────────┐               │
│         │     ESTRUTURA INTERNA UNIFICADA   │               │
│         │  strategy_indicators + conditions │               │
│         └───────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────┘
```

### Tarefas Completadas

| Tarefa | Prioridade | Status | Arquivo |
|--------|------------|--------|---------|
| Visual Editor | ALTA | ✅ COMPLETO | `VisualEditor.tsx` |
| YAML Editor | ALTA | ✅ COMPLETO | `YamlEditor.tsx` |
| YAML Parser | ALTA | ✅ COMPLETO | Backend endpoint `/strategies/{id}/yaml` |
| Strategy CRUD API | ALTA | ✅ COMPLETO | `strategy_controller.py` |
| PineScript Webhook | MEDIA | ✅ COMPLETO | Endpoint `/pinescript-webhook` |
| Backtest UI | BAIXA | ✅ COMPLETO | `BacktestPanel.tsx` |

### Arquivos Frontend Criados

```
frontend-admin/src/
├── components/
│   ├── pages/
│   │   └── StrategiesPage.tsx        ✅ Pagina principal com grid de estrategias
│   └── strategies/
│       ├── IndicatorSelector.tsx     ✅ Seletor de indicadores com parametros
│       ├── ConditionBuilder.tsx      ✅ Builder de condicoes entry/exit
│       ├── VisualEditor.tsx          ✅ Editor visual com 3 abas
│       ├── YamlEditor.tsx            ✅ Editor YAML com template e validacao
│       ├── PineScriptMode.tsx        ✅ Interface webhook TradingView
│       ├── CreateStrategyModal.tsx   ✅ Modal unificado com 3 modos
│       └── BacktestPanel.tsx         ✅ Interface de backtest
└── services/
    └── strategyService.ts            ✅ API calls + tipos TypeScript
```

---

## Fluxo de Cada Modo

### 1. Visual Editor ✅
```
Admin abre modal → Seleciona "Editor Visual"
    → Aba 1: Nome, descricao, simbolos, timeframe
    → Aba 2: Adiciona indicadores via IndicatorSelector
    → Aba 3: Define condicoes via ConditionBuilder
    → Salva → API grava em strategy + strategy_indicators + strategy_conditions
    → StrategyWebSocketMonitor detecta e comeca monitorar
```

### 2. YAML Editor ✅
```yaml
strategy:
  name: "NDY + RSI Strategy"
  symbols: ["BTCUSDT"]
  timeframe: "5m"

indicators:
  - type: nadaraya_watson
    params: { bandwidth: 8, mult: 3.0 }
  - type: rsi
    params: { period: 14 }

conditions:
  entry_long:
    operator: AND
    rules:
      - { left: close, op: "<", right: nadaraya_watson.lower }
      - { left: rsi.value, op: "<", right: 30 }
```
→ Admin cola/edita YAML → Clica "Aplicar YAML"
→ Backend endpoint `/strategies/{id}/yaml` faz parse
→ Converte para tabelas do banco automaticamente

### 3. PineScript Mode ✅
```
Admin abre modal → Seleciona "PineScript / TradingView"
    → Sistema gera webhook URL e secret automatico
    → Admin copia URL e JSON template
    → Configura alerta no TradingView com webhook
    → TradingView envia POST para /pinescript-webhook
    → Backend valida secret, cria signal
    → Se strategy tem bot_id, executa via bot_broadcast_service
```

**Webhook URL:** `https://globalautomation-tqu2m.ondigitalocean.app/api/v1/strategies/pinescript-webhook`

**JSON Template para TradingView:**
```json
{
  "secret": "{{webhook_secret}}",
  "action": "{{strategy.order.action}}",
  "ticker": "{{ticker}}",
  "price": {{close}},
  "quantity": {{strategy.order.contracts}},
  "position_size": {{strategy.position_size}},
  "comment": "{{strategy.order.comment}}"
}
```

---

## Endpoints API Implementados

### Estrategias (CRUD)
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/v1/strategies` | Listar estrategias com stats |
| GET | `/api/v1/strategies/{id}` | Detalhes com indicadores e condicoes |
| POST | `/api/v1/strategies` | Criar estrategia |
| PUT | `/api/v1/strategies/{id}` | Atualizar estrategia |
| DELETE | `/api/v1/strategies/{id}` | Excluir estrategia |
| POST | `/api/v1/strategies/{id}/activate` | Ativar estrategia |
| POST | `/api/v1/strategies/{id}/deactivate` | Desativar estrategia |

### Indicadores
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/v1/strategies/{id}/indicators` | Adicionar indicador |
| DELETE | `/api/v1/strategies/{id}/indicators/{ind_id}` | Remover indicador |

### Condicoes
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/v1/strategies/{id}/conditions` | Adicionar condicao |
| DELETE | `/api/v1/strategies/{id}/conditions/{cond_id}` | Remover condicao |

### YAML
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/v1/strategies/{id}/yaml` | Aplicar config YAML |
| GET | `/api/v1/strategies/yaml-template` | Gerar template YAML |

### Sinais
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/v1/strategies/{id}/signals` | Listar sinais |

### Backtest
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/v1/strategies/{id}/backtest-results` | Listar resultados |
| POST | `/api/v1/strategies/{id}/backtest` | Executar backtest |

### PineScript Webhook
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| POST | `/api/v1/strategies/pinescript-webhook` | Receber alertas TradingView |

### Engine
| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| GET | `/api/v1/strategies/engine/status` | Status do engine |
| POST | `/api/v1/strategies/engine/reload` | Recarregar estrategias |

---

## Indicadores Suportados

| Indicador | Tipo | Parametros Padrao |
|-----------|------|-------------------|
| Nadaraya-Watson Envelope | `nadaraya_watson` | bandwidth: 8, mult: 3.0 |
| RSI | `rsi` | period: 14, overbought: 70, oversold: 30 |
| MACD | `macd` | fast: 12, slow: 26, signal: 9 |
| EMA | `ema` | period: 20 |
| Bollinger Bands | `bollinger` | period: 20, std_dev: 2 |
| ATR | `atr` | period: 14 |
| Volume Profile | `volume_profile` | lookback: 24 |

---

## Como Testar

### 1. Via Interface Admin
1. Acesse `https://globalautomation-frontend-g9gmr.ondigitalocean.app`
2. Faca login como admin
3. Va para menu "Estrategias"
4. Clique "Criar Estrategia"
5. Escolha um dos 3 modos e configure

### 2. Via API Direta
```bash
# Criar estrategia
curl -X POST https://globalautomation-tqu2m.ondigitalocean.app/api/v1/strategies \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "name": "Test Strategy",
    "symbols": ["BTCUSDT"],
    "timeframe": "5m",
    "config_type": "visual"
  }'

# Adicionar indicador
curl -X POST https://globalautomation-tqu2m.ondigitalocean.app/api/v1/strategies/{id}/indicators \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {token}" \
  -d '{
    "indicator_type": "nadaraya_watson",
    "parameters": {"bandwidth": 8, "mult": 3.0}
  }'
```

### 3. Testar Webhook PineScript
```bash
curl -X POST https://globalautomation-tqu2m.ondigitalocean.app/api/v1/strategies/pinescript-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "ps_xxxxxxxxxxxxx",
    "action": "buy",
    "ticker": "BTCUSDT",
    "price": 42000.50
  }'
```

---

## Historico de Alteracoes

| Data | Alteracao |
|------|-----------|
| 22/12/2024 | **FASE 2 CONCLUIDA** - Frontend Admin completo |
| 22/12/2024 | Implementado PineScript webhook endpoint |
| 22/12/2024 | Criados 7 componentes React para estrategias |
| 22/12/2024 | Migrado backend para transaction_db (SQL direto) |
| 21/12/2024 | Implementado StrategyWebSocketMonitor (< 1s latencia) |
| 21/12/2024 | Removido codigo duplicado de indicadores |
| 20/12/2024 | Criadas 5 tabelas no Supabase |
| 20/12/2024 | Refatorado strategy_engine_service para usar IndicatorAlertMonitor |

---

## Notas Importantes

1. **Bots existentes NAO foram afetados** - O sistema de estrategias e adicional
2. **Compatibilidade pgBouncer** - Usa transaction_db (asyncpg) em vez de SQLAlchemy ORM
3. **Backtest** - Interface pronta, mas usa simulacao (backend real precisaria dados historicos)
4. **PineScript** - Webhook funcional, executa via bot_broadcast_service se strategy tem bot_id

---

## Proximos Passos Sugeridos (Futuro)

1. [ ] Implementar backtest real com dados historicos da Binance
2. [ ] Adicionar mais indicadores (Stochastic, Ichimoku, etc)
3. [ ] Dashboard de performance das estrategias
4. [ ] Alertas por email/telegram quando sinal e gerado
5. [ ] Paper trading mode para testar sem risco
