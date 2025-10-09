-- 🚀 PERFORMANCE OPTIMIZATION - Database Indexes
-- Data: 09 de Outubro de 2025
-- Objetivo: Acelerar queries frequentes do sistema de trading

-- ===========================================================================
-- IMPORTANTE: Executar com CONCURRENTLY para não bloquear tabela
-- ===========================================================================

BEGIN;

-- ===========================================================================
-- 1. ÍNDICES PARA ORDERS/TRADING_ORDERS (Endpoints mais usados)
-- ===========================================================================

-- 1.1 Índice para busca por conta + data (main.py:631-644)
-- Usado em: GET /api/v1/orders
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_account_created
  ON orders(exchange_account_id, created_at DESC)
  WHERE is_active = true;

-- 1.2 Índice para busca por símbolo + status (main.py:808-837)
-- Usado em: filtros de orders por símbolo
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_symbol_status
  ON orders(symbol, status)
  WHERE status IN ('filled', 'pending', 'new');

-- 1.3 Índice composto para queries de histórico
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_status_account
  ON orders(created_at DESC, status, exchange_account_id);

-- 1.4 Índice para trading_orders (tabela legacy)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_orders_created_status
  ON trading_orders(created_at DESC, status)
  WHERE created_at >= NOW() - INTERVAL '6 months';

-- 1.5 Índice para trading_orders stats (main.py:1088-1129)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_orders_stats
  ON trading_orders(status, created_at, filled_quantity, average_price)
  WHERE created_at >= NOW() - INTERVAL '7 days';

-- ===========================================================================
-- 2. ÍNDICES PARA POSITIONS (Dashboard e Positions Page)
-- ===========================================================================

-- 2.1 Índice para busca de posições por conta (positions_controller.py)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_account_symbol
  ON positions(exchange_account_id, symbol)
  WHERE status IN ('open', 'active');

-- 2.2 Índice para posições abertas
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_open
  ON positions(status, created_at DESC)
  WHERE status IN ('open', 'active');

-- 2.3 Índice composto para P&L queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_pnl
  ON positions(exchange_account_id, status, unrealized_pnl, realized_pnl)
  WHERE status IN ('open', 'active', 'closed');

-- ===========================================================================
-- 3. ÍNDICES PARA EXCHANGE_ACCOUNTS (Lookup frequente)
-- ===========================================================================

-- 3.1 Índice para busca de contas ativas (main.py:632-642)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_active
  ON exchange_accounts(testnet, is_active, created_at ASC)
  WHERE is_active = true;

-- 3.2 Índice para busca por exchange + testnet
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_exchange_accounts_exchange
  ON exchange_accounts(exchange, testnet, is_active);

-- ===========================================================================
-- 4. ÍNDICES PARA USERS (Autenticação)
-- ===========================================================================

-- 4.1 Índice para login (main.py:1304-1310)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_active
  ON users(email, is_active)
  WHERE is_active = true;

-- 4.2 Índice para busca por ID + active
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_id_active
  ON users(id, is_active)
  WHERE is_active = true;

-- ===========================================================================
-- 5. ÍNDICES PARA WEBHOOK_DELIVERIES (Se usado)
-- ===========================================================================

-- 5.1 Índice para busca por status + created
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_webhook_deliveries_status
  ON webhook_deliveries(status, created_at DESC)
  WHERE created_at >= NOW() - INTERVAL '30 days';

-- ===========================================================================
-- 6. PARTIAL INDEXES para queries específicas
-- ===========================================================================

-- 6.1 Ordens FILLED dos últimos 30 dias (queries de estatísticas)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_filled_recent
  ON orders(created_at DESC, exchange_account_id, symbol)
  WHERE status = 'filled' AND created_at >= NOW() - INTERVAL '30 days';

-- 6.2 Ordens PENDING (para monitoramento)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_pending
  ON orders(created_at DESC, exchange_account_id, symbol)
  WHERE status = 'pending';

-- ===========================================================================
-- 7. ÍNDICES para símbolos históricos (main.py:471-478)
-- ===========================================================================

-- 7.1 Índice para busca de símbolos únicos
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trading_orders_symbol_created
  ON trading_orders(symbol, created_at DESC)
  WHERE symbol IS NOT NULL AND symbol != '' AND created_at >= NOW() - INTERVAL '6 months';

-- ===========================================================================
-- 8. ANÁLISE DE PERFORMANCE (Opcional - Run After)
-- ===========================================================================

-- 8.1 Atualizar estatísticas das tabelas
ANALYZE orders;
ANALYZE positions;
ANALYZE trading_orders;
ANALYZE exchange_accounts;
ANALYZE users;
ANALYZE webhook_deliveries;

-- ===========================================================================
-- 9. VERIFICAÇÃO DOS ÍNDICES CRIADOS
-- ===========================================================================

-- Query para verificar índices criados:
/*
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
*/

-- Query para verificar tamanho dos índices:
/*
SELECT
    indexrelname AS index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS number_of_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
*/

-- Query para verificar queries lentas (habilitar pg_stat_statements):
/*
SELECT
    query,
    calls,
    total_exec_time / 1000 AS total_time_sec,
    mean_exec_time / 1000 AS avg_time_sec,
    max_exec_time / 1000 AS max_time_sec
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_%'
ORDER BY mean_exec_time DESC
LIMIT 20;
*/

COMMIT;

-- ===========================================================================
-- 10. ÍNDICES ADICIONAIS (Se necessário após análise)
-- ===========================================================================

-- 10.1 GIN index para full-text search em símbolos (se implementar)
-- CREATE INDEX CONCURRENTLY idx_orders_symbol_gin
--   ON orders USING gin(to_tsvector('english', symbol));

-- 10.2 BRIN index para tabelas muito grandes (time-series)
-- CREATE INDEX CONCURRENTLY idx_orders_created_brin
--   ON orders USING brin(created_at) WITH (pages_per_range = 128);

-- ===========================================================================
-- NOTES
-- ===========================================================================

-- Performance Gains Expected:
-- - Orders endpoint: 60-80% faster (main bottleneck)
-- - Dashboard queries: 50-70% faster
-- - Login/Auth: 40-60% faster
-- - Position queries: 50-60% faster

-- Monitoring:
-- - Use pg_stat_user_indexes to track index usage
-- - Use pg_stat_statements to identify slow queries
-- - Monitor index bloat with pg_indexes

-- Maintenance:
-- - REINDEX CONCURRENTLY monthly for heavily updated tables
-- - VACUUM ANALYZE weekly
-- - Monitor index hit ratio (should be > 99%)

-- ===========================================================================
-- FIM DO SCRIPT
-- ===========================================================================

-- Para executar este script:
-- psql -U postgres -d trading_platform -f database_performance_indexes.sql

-- Para verificar se os índices foram criados:
-- \di+ idx_*
