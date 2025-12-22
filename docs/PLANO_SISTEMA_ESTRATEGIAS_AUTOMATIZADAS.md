# Sistema de Estrategias Automatizadas

**Ultima atualizacao:** 21/12/2024
**Status:** Fase 1 (Backend) CONCLUIDA | Fase 2 (Frontend) PENDENTE

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

## O Que Foi Implementado (Fase 1 - Backend)

### Tabelas no Supabase (5 tabelas criadas)
- `strategies` - Configuracao geral (nome, simbolos, timeframe, bot_id)
- `strategy_indicators` - Indicadores configurados por estrategia
- `strategy_conditions` - Condicoes de entrada/saida
- `strategy_signals` - Sinais gerados
- `strategy_backtest_results` - Resultados de backtests

### Arquivos Backend Criados/Modificados

| Arquivo | Status | Descricao |
|---------|--------|-----------|
| `infrastructure/exchanges/binance_websocket.py` | OK | WebSocket Binance (ja existia, corrigido) |
| `infrastructure/services/strategy_websocket_monitor.py` | NOVO | Monitor real-time via WebSocket |
| `infrastructure/services/strategy_engine_service.py` | OK | Engine com polling (backup) |
| `infrastructure/services/indicator_alert_monitor.py` | OK | Calculos de indicadores (REUSADO) |
| `infrastructure/database/models/strategy.py` | OK | Models SQLAlchemy |
| `infrastructure/database/repositories/strategy.py` | OK | Repositories |
| `main.py` | MODIFICADO | Inicializa WebSocket monitor |

### Principio de Nao Duplicacao
Todos os calculos de indicadores sao feitos via `IndicatorAlertMonitor`:
- `_calc_nadaraya_watson_signal()`
- `_calc_rsi_signal()`
- `_calc_macd_signal()`
- `_calc_bollinger_signal()`
- `_calc_ema_cross_signal()`

**NAO FOI CRIADO CODIGO DUPLICADO!**

---

## O Que Falta Implementar (Fase 2 - Frontend Admin)

### 3 Modos de Configuracao

```
┌──────────────────────────────────────────────────────────────┐
│                     ADMIN DASHBOARD                          │
│                  /dashboard-admin/strategies                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│   │  VISUAL    │  │   YAML     │  │ PINESCRIPT │            │
│   │  EDITOR    │  │  EDITOR    │  │   MODE     │            │
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

### Tarefas Pendentes

| Tarefa | Prioridade | Descricao |
|--------|------------|-----------|
| Visual Editor | ALTA | Interface drag-and-drop para indicadores |
| YAML Editor | ALTA | Monaco Editor com syntax highlighting |
| YAML Parser | ALTA | Converte YAML para tabelas do banco |
| Strategy CRUD API | ALTA | Endpoints REST para gerenciar estrategias |
| PineScript Webhook | MEDIA | Endpoint para receber alertas TradingView |
| Backtest UI | BAIXA | Interface para rodar e ver backtests |

### Arquivos Frontend a Criar

```
frontend-admin/src/
├── pages/
│   └── StrategiesPage.tsx          # Pagina principal
├── components/strategies/
│   ├── StrategyList.tsx            # Lista de estrategias
│   ├── StrategyEditor.tsx          # Editor principal
│   ├── VisualEditor.tsx            # Modo visual
│   ├── YamlEditor.tsx              # Modo YAML
│   ├── IndicatorSelector.tsx       # Seletor de indicadores
│   └── ConditionBuilder.tsx        # Builder de condicoes
└── services/
    └── strategyApi.ts              # API calls
```

---

## Fluxo de Cada Modo

### 1. Visual Editor
```
Admin seleciona indicadores → Define parametros → Define condicoes
    → Salva → API grava em strategy_indicators + strategy_conditions
    → StrategyWebSocketMonitor detecta e comeca monitorar
```

### 2. YAML Editor
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
→ YAML Parser converte para tabelas do banco

### 3. PineScript Mode
```
Admin cola script PineScript → Define webhook URL
    → TradingView envia alertas → Webhook receiver processa
    → Chama bot_broadcast_service
```

---

## Como Testar o Backend

1. Criar estrategia diretamente no banco:
```sql
INSERT INTO strategies (name, symbols, timeframe, is_active, bot_id)
VALUES ('Test NDY', '["BTCUSDT"]', '5m', true, 'uuid-do-bot');

INSERT INTO strategy_indicators (strategy_id, indicator_type, parameters)
VALUES ('uuid-estrategia', 'nadaraya_watson', '{"bandwidth": 8, "mult": 3.0}');

INSERT INTO strategy_conditions (strategy_id, condition_type, conditions, logic_operator)
VALUES ('uuid-estrategia', 'entry_long',
  '[{"left": "close", "operator": "<", "right": "nadaraya_watson.lower"}]', 'AND');
```

2. Verificar logs do servidor para ver WebSocket conectando
3. Esperar candle fechar e verificar se sinal foi gerado

---

## Historico de Alteracoes

| Data | Alteracao |
|------|-----------|
| 21/12/2024 | Implementado StrategyWebSocketMonitor (< 1s latencia) |
| 21/12/2024 | Removido codigo duplicado de indicadores |
| 20/12/2024 | Criadas 5 tabelas no Supabase |
| 20/12/2024 | Refatorado strategy_engine_service para usar IndicatorAlertMonitor |

---

## Proximos Passos

1. **Criar endpoints REST** para CRUD de estrategias (`/api/v1/strategies`)
2. **Criar pagina no admin** para listar/criar estrategias
3. **Implementar Visual Editor** com seletor de indicadores
4. **Implementar YAML Parser** para converter YAML em tabelas
5. **Testar fluxo completo** criando estrategia e verificando execucao
