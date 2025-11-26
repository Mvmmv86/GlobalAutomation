-- ==========================================
-- SCRIPT DE VERIFICAÇÃO DO RLS
-- Verifica se Row Level Security está ativo
-- Data: 2025-10-24
-- ==========================================

-- ==========================================
-- VERIFICAR SE RLS ESTÁ HABILITADO
-- ==========================================

SELECT
    tablename,
    rowsecurity as rls_enabled,
    CASE
        WHEN rowsecurity THEN '✅ ATIVO'
        ELSE '❌ DESATIVADO'
    END as status
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
    'exchange_accounts',
    'exchange_account_balances',
    'positions',
    'orders',
    'users'
)
ORDER BY tablename;

-- RESULTADO ESPERADO:
-- tablename                    | rls_enabled | status
-- ----------------------------|-------------|-------------
-- exchange_account_balances    | t           | ✅ ATIVO
-- exchange_accounts            | t           | ✅ ATIVO
-- orders                       | t           | ✅ ATIVO
-- positions                    | t           | ✅ ATIVO
-- users                        | t           | ✅ ATIVO

-- ==========================================
-- VERIFICAR POLÍTICAS CRIADAS
-- ==========================================

SELECT
    schemaname,
    tablename,
    policyname,
    cmd as command_type,
    CASE
        WHEN roles = '{public}' THEN 'PUBLIC'
        ELSE array_to_string(roles, ', ')
    END as applies_to
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN (
    'exchange_accounts',
    'exchange_account_balances',
    'positions',
    'orders',
    'users'
)
ORDER BY tablename, policyname;

-- RESULTADO ESPERADO:
-- 5 políticas criadas (uma para cada tabela)

-- ==========================================
-- CONTAGEM DE POLÍTICAS POR TABELA
-- ==========================================

SELECT
    tablename,
    COUNT(*) as total_policies
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN (
    'exchange_accounts',
    'exchange_account_balances',
    'positions',
    'orders',
    'users'
)
GROUP BY tablename
ORDER BY tablename;

-- RESULTADO ESPERADO:
-- Cada tabela deve ter 1 política (FOR ALL)

-- ==========================================
-- TESTAR ISOLAMENTO (SIMULAÇÃO)
-- ==========================================

-- IMPORTANTE: Este teste só funciona se você tiver auth.uid() configurado
-- No ambiente de desenvolvimento sem autenticação, pode não funcionar

-- Exemplo de teste:
-- SET LOCAL "request.jwt.claim.sub" = 'user-uuid-1';
-- SELECT COUNT(*) FROM exchange_accounts;  -- Deve retornar apenas contas do user-uuid-1

-- SET LOCAL "request.jwt.claim.sub" = 'user-uuid-2';
-- SELECT COUNT(*) FROM exchange_accounts;  -- Deve retornar apenas contas do user-uuid-2

-- ==========================================
-- FIM DA VERIFICAÇÃO
-- ==========================================
