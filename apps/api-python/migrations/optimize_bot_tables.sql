-- ================================================================================
-- MIGRATION: Otimização das Tabelas de Bots
-- Data: 2025-01-07
-- Objetivo: Adicionar exchange_account_id em bot_signal_executions para histórico completo
-- ================================================================================

-- ============================================================================
-- ANÁLISE DO PROBLEMA
-- ============================================================================
--
-- PROBLEMA: Tabela bot_signal_executions não armazena qual exchange_account foi usada
--
-- IMPACTO:
--   1. Histórico incompleto - se user trocar de exchange, perde rastreabilidade
--   2. Queries lentas - precisa JOIN com bot_subscriptions para saber qual conta
--   3. Auditoria difícil - não consegue rastrear problemas por conta específica
--
-- SOLUÇÃO: Adicionar coluna exchange_account_id com FK para exchange_accounts
--
-- ============================================================================

-- ============================================================================
-- PARTE 1: ADICIONAR COLUNA exchange_account_id
-- ============================================================================

-- IMPORTANTE: Precisamos primeiro popular a coluna com dados históricos
-- antes de torná-la NOT NULL

-- 1.1: Adicionar coluna como NULLABLE primeiro
ALTER TABLE bot_signal_executions
ADD COLUMN IF NOT EXISTS exchange_account_id UUID;

-- 1.2: Popular coluna com dados históricos
-- Busca o exchange_account_id da subscription correspondente
UPDATE bot_signal_executions
SET exchange_account_id = bs.exchange_account_id
FROM bot_subscriptions bs
WHERE bot_signal_executions.subscription_id = bs.id
AND bot_signal_executions.exchange_account_id IS NULL;

-- 1.3: Verificar se todos foram populados
DO $$
DECLARE
    null_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO null_count
    FROM bot_signal_executions
    WHERE exchange_account_id IS NULL;

    IF null_count > 0 THEN
        RAISE WARNING 'ATENÇÃO: % registros em bot_signal_executions sem exchange_account_id!', null_count;
        RAISE WARNING 'Execute manualmente: SELECT id, subscription_id FROM bot_signal_executions WHERE exchange_account_id IS NULL;';
    ELSE
        RAISE NOTICE 'Sucesso: Todos os registros foram populados com exchange_account_id';
    END IF;
END $$;

-- 1.4: Tornar coluna NOT NULL (após popular)
ALTER TABLE bot_signal_executions
ALTER COLUMN exchange_account_id SET NOT NULL;

-- 1.5: Adicionar Foreign Key
ALTER TABLE bot_signal_executions
ADD CONSTRAINT bot_signal_executions_exchange_account_id_fkey
FOREIGN KEY (exchange_account_id)
REFERENCES exchange_accounts(id)
ON DELETE CASCADE;

-- ============================================================================
-- PARTE 2: CRIAR ÍNDICE PARA PERFORMANCE
-- ============================================================================

-- 2.1: Índice em exchange_account_id
-- Justificativa: Queries comuns filtram por conta (ex: "histórico da conta X")
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bot_signal_executions_exchange
ON bot_signal_executions(exchange_account_id);

COMMENT ON INDEX idx_bot_signal_executions_exchange IS
'Índice para queries de histórico por exchange account';

-- ============================================================================
-- PARTE 3: VERIFICAÇÕES PÓS-MIGRATION
-- ============================================================================

-- 3.1: Verificar estrutura da coluna
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'bot_signal_executions'
AND column_name = 'exchange_account_id';

-- 3.2: Verificar Foreign Key
SELECT
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_name = 'bot_signal_executions'
AND tc.constraint_type = 'FOREIGN KEY'
AND kcu.column_name = 'exchange_account_id';

-- 3.3: Verificar índice
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'bot_signal_executions'
AND indexname = 'idx_bot_signal_executions_exchange';

-- 3.4: Verificar integridade dos dados
SELECT
    COUNT(*) as total_executions,
    COUNT(exchange_account_id) as with_exchange_account,
    COUNT(*) - COUNT(exchange_account_id) as missing_exchange_account
FROM bot_signal_executions;

-- 3.5: Teste de JOIN (deve ser mais rápido agora)
EXPLAIN ANALYZE
SELECT
    bse.id,
    bse.status,
    bse.exchange_order_id,
    ea.name as exchange_account_name,
    ea.exchange
FROM bot_signal_executions bse
JOIN exchange_accounts ea ON bse.exchange_account_id = ea.id
LIMIT 10;

-- ============================================================================
-- NOTAS DE IMPLEMENTAÇÃO
-- ============================================================================
--
-- IMPORTANTE:
-- 1. Migration popula dados históricos antes de tornar NOT NULL
-- 2. Se houver executions órfãs (sem subscription), migration falhará
-- 3. Índice criado com CONCURRENTLY (não bloqueia tabela)
-- 4. ON DELETE CASCADE: se exchange_account for deletada, deleta executions
--
-- ROLLBACK (se necessário):
--   DROP INDEX CONCURRENTLY IF EXISTS idx_bot_signal_executions_exchange;
--   ALTER TABLE bot_signal_executions DROP CONSTRAINT bot_signal_executions_exchange_account_id_fkey;
--   ALTER TABLE bot_signal_executions DROP COLUMN exchange_account_id;
--
-- TEMPO ESTIMADO:
--   - Adicionar coluna: ~1 segundo
--   - Popular dados: ~5 segundos (45 registros)
--   - Criar índice: ~5 segundos
--   - Total: ~15 segundos
--
-- ================================================================================
