# Database Migrations

Este diretório contém as migrações do banco de dados para a plataforma de trading.

## Estrutura

```
migrations/
├── README.md              # Este arquivo
├── env.py                 # Configuração do ambiente Alembic
├── script.py.mako         # Template para novos scripts de migração
└── versions/
    └── 001_initial_schema.py  # Migração inicial do schema
```

## Configuração

As migrações são gerenciadas pelo Alembic com suporte assíncrono para PostgreSQL.

### Ambientes Suportados

- **dev**: `postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_dev`
- **test**: `postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test`
- **prod**: Configurado via variável de ambiente `DATABASE_URL`

## Comandos Úteis

### Aplicar todas as migrações
```bash
alembic upgrade head
```

### Aplicar migração específica
```bash
alembic upgrade 001
```

### Reverter última migração
```bash
alembic downgrade -1
```

### Reverter para migração específica
```bash
alembic downgrade 001
```

### Ver histórico de migrações
```bash
alembic history --verbose
```

### Ver migração atual
```bash
alembic current
```

### Gerar nova migração (auto-detectar mudanças)
```bash
alembic revision --autogenerate -m "Descrição da mudança"
```

### Gerar migração vazia
```bash
alembic revision -m "Descrição da mudança"
```

## Seed Data

Para popular o banco com dados de desenvolvimento:

```bash
python scripts/seed_data.py
```

### Usuários Demo Criados

| Email | Senha | Perfil |
|-------|-------|--------|
| demo@tradingplatform.com | demo123 | Usuário básico |
| trader@tradingplatform.com | trader123 | Trader profissional |
| admin@tradingplatform.com | admin123 | Administrador |

## Schema Atual (v001)

### Tabelas Principais

1. **users** - Usuários da plataforma
2. **api_keys** - Chaves de API para autenticação
3. **exchange_accounts** - Contas de exchanges (Binance, Bybit)
4. **webhooks** - Configurações de webhooks do TradingView
5. **webhook_deliveries** - Histórico de deliveries de webhooks
6. **orders** - Ordens de trading
7. **positions** - Posições abertas

### Relacionamentos

```
users (1) → (N) api_keys
users (1) → (N) exchange_accounts
users (1) → (N) webhooks
webhooks (1) → (N) webhook_deliveries
exchange_accounts (1) → (N) orders
exchange_accounts (1) → (N) positions
webhook_deliveries (1) → (N) orders [opcional]
```

### Tipos ENUM

- **ExchangeType**: binance, bybit
- **WebhookStatus**: active, paused, disabled, error
- **WebhookDeliveryStatus**: pending, processing, success, failed, retrying
- **OrderType**: market, limit, stop_loss, take_profit, stop_limit
- **OrderSide**: buy, sell
- **OrderStatus**: pending, submitted, open, partially_filled, filled, canceled, rejected, expired, failed
- **TimeInForce**: gtc, ioc, fok, gtd
- **PositionSide**: long, short
- **PositionStatus**: open, closed, closing, liquidated

## Troubleshooting

### Erro de Conexão
Verifique se o PostgreSQL está rodando e as credenciais estão corretas.

### Migração Falhando
1. Verifique os logs para detalhes do erro
2. Confira se há conflitos no schema
3. Use `alembic downgrade` para reverter se necessário

### Reset Completo (CUIDADO!)
```bash
# Remove todas as tabelas e recria
alembic downgrade base
alembic upgrade head
```

## Boas Práticas

1. **Sempre** teste migrações em ambiente de desenvolvimento primeiro
2. **Faça backup** antes de aplicar migrações em produção
3. **Documente** mudanças complexas nos comentários da migração
4. **Nunca** edite migrações já aplicadas em produção
5. **Use** transações para operações que podem falhar