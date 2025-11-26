-- ==========================================
-- ROW LEVEL SECURITY (RLS)
-- Garante que cada cliente só acessa seus próprios dados
-- Data: 2025-10-24
-- ==========================================

-- ==========================================
-- PARTE 1: HABILITAR RLS NAS TABELAS
-- ==========================================

-- Tabela principal de contas de exchange
ALTER TABLE exchange_accounts ENABLE ROW LEVEL SECURITY;

-- Tabela de balances (SPOT e FUTURES)
ALTER TABLE exchange_account_balances ENABLE ROW LEVEL SECURITY;

-- Tabela de posições abertas
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;

-- Tabela de ordens
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

-- Tabela de usuários
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- PARTE 2: POLÍTICAS PARA exchange_accounts
-- ==========================================

-- Usuário só vê/edita/deleta suas próprias contas de exchange
DROP POLICY IF EXISTS "users_own_exchange_accounts" ON exchange_accounts;
CREATE POLICY "users_own_exchange_accounts"
ON exchange_accounts
FOR ALL
USING (user_id = auth.uid());

-- ==========================================
-- PARTE 3: POLÍTICAS PARA exchange_account_balances
-- ==========================================

-- Usuário só vê balances de suas contas
DROP POLICY IF EXISTS "users_own_balances" ON exchange_account_balances;
CREATE POLICY "users_own_balances"
ON exchange_account_balances
FOR ALL
USING (
    exchange_account_id IN (
        SELECT id FROM exchange_accounts WHERE user_id = auth.uid()
    )
);

-- ==========================================
-- PARTE 4: POLÍTICAS PARA positions
-- ==========================================

-- Usuário só vê posições de suas contas
DROP POLICY IF EXISTS "users_own_positions" ON positions;
CREATE POLICY "users_own_positions"
ON positions
FOR ALL
USING (
    exchange_account_id IN (
        SELECT id FROM exchange_accounts WHERE user_id = auth.uid()
    )
);

-- ==========================================
-- PARTE 5: POLÍTICAS PARA orders
-- ==========================================

-- Usuário só vê ordens de suas contas
DROP POLICY IF EXISTS "users_own_orders" ON orders;
CREATE POLICY "users_own_orders"
ON orders
FOR ALL
USING (
    exchange_account_id IN (
        SELECT id FROM exchange_accounts WHERE user_id = auth.uid()
    )
);

-- ==========================================
-- PARTE 6: POLÍTICAS PARA users
-- ==========================================

-- Usuário só vê seus próprios dados
DROP POLICY IF EXISTS "users_own_data" ON users;
CREATE POLICY "users_own_data"
ON users
FOR ALL
USING (id = auth.uid());

-- ==========================================
-- PARTE 7: VERIFICAÇÃO
-- ==========================================

-- Executar para confirmar que RLS está ativo:
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- AND tablename IN ('exchange_accounts', 'exchange_account_balances', 'positions', 'orders', 'users');

-- Deve retornar rowsecurity = TRUE para todas as tabelas

-- ==========================================
-- NOTAS DE SEGURANÇA
-- ==========================================

-- 1. RLS garante isolamento NO NÍVEL DO BANCO DE DADOS
-- 2. Mesmo se houver bug no backend, RLS protege os dados
-- 3. Cliente A NUNCA consegue ver dados do Cliente B
-- 4. Supabase auth.uid() retorna o UUID do usuário autenticado
-- 5. Se não houver autenticação (auth.uid() = NULL), nenhum dado é retornado

-- ==========================================
-- ROLLBACK (SE NECESSÁRIO)
-- ==========================================

-- Para desabilitar RLS (NÃO RECOMENDADO):
-- ALTER TABLE exchange_accounts DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE exchange_account_balances DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE positions DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE orders DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- Para remover políticas:
-- DROP POLICY IF EXISTS "users_own_exchange_accounts" ON exchange_accounts;
-- DROP POLICY IF EXISTS "users_own_balances" ON exchange_account_balances;
-- DROP POLICY IF EXISTS "users_own_positions" ON positions;
-- DROP POLICY IF EXISTS "users_own_orders" ON orders;
-- DROP POLICY IF EXISTS "users_own_data" ON users;

-- ==========================================
-- FIM DO SCRIPT
-- ==========================================
