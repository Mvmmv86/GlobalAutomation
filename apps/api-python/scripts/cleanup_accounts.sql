-- Script para limpar contas mock e manter apenas a conta real mainnet
-- Conta real a manter: 78e6b4fa-9a71-4360-b808-f1cd7c98dcbe (Teste1 Binance)

BEGIN;

-- 1. Remover posições das contas mock
DELETE FROM positions 
WHERE exchange_account_id IN (
    '7edce3b4-8ba2-4275-b136-7a8b6b6e93ba',  -- tests (testnet)
    '1cfb9b63-bdd1-470d-9763-92f32635d2d8',  -- Teste Frontend Fix (testnet)
    '0f505abb-0260-4b73-8580-a6332f2ec37b',  -- Test API Keys (testnet)
    'f42d8315-1a1e-4eb4-aef1-cbeda245f928',  -- testeMarcus (testnet)
    'a91cf0e8-f9d1-409a-bd1b-e83a1ac55a68',  -- Test Real Keys (testnet)
    '94b8a494-acd2-40dd-8773-63d7773ab8d1',  -- Test Binance Testnet
    '770e8400-e29b-41d4-a716-446655440001',  -- Demo Binance Testnet
    '770e8400-e29b-41d4-a716-446655440004',  -- Admin Binance Live (outra conta)
    '770e8400-e29b-41d4-a716-446655440003',  -- Trader Binance Testnet
    '770e8400-e29b-41d4-a716-446655440002'   -- Demo Bybit Testnet
);

-- 2. Remover ordens das contas mock
DELETE FROM orders 
WHERE exchange_account_id IN (
    '7edce3b4-8ba2-4275-b136-7a8b6b6e93ba',
    '1cfb9b63-bdd1-470d-9763-92f32635d2d8',
    '0f505abb-0260-4b73-8580-a6332f2ec37b',
    'f42d8315-1a1e-4eb4-aef1-cbeda245f928',
    'a91cf0e8-f9d1-409a-bd1b-e83a1ac55a68',
    '94b8a494-acd2-40dd-8773-63d7773ab8d1',
    '770e8400-e29b-41d4-a716-446655440001',
    '770e8400-e29b-41d4-a716-446655440004',
    '770e8400-e29b-41d4-a716-446655440003',
    '770e8400-e29b-41d4-a716-446655440002'
);

-- 3. Remover as contas mock (mantém apenas a conta real)
DELETE FROM exchange_accounts 
WHERE id IN (
    '7edce3b4-8ba2-4275-b136-7a8b6b6e93ba',
    '1cfb9b63-bdd1-470d-9763-92f32635d2d8',
    '0f505abb-0260-4b73-8580-a6332f2ec37b',
    'f42d8315-1a1e-4eb4-aef1-cbeda245f928',
    'a91cf0e8-f9d1-409a-bd1b-e83a1ac55a68',
    '94b8a494-acd2-40dd-8773-63d7773ab8d1',
    '770e8400-e29b-41d4-a716-446655440001',
    '770e8400-e29b-41d4-a716-446655440004',
    '770e8400-e29b-41d4-a716-446655440003',
    '770e8400-e29b-41d4-a716-446655440002'
);

-- 4. Verificar resultado
SELECT 
    id, name, exchange, environment,
    CASE 
        WHEN id = '78e6b4fa-9a71-4360-b808-f1cd7c98dcbe' THEN '✅ CONTA REAL MANTIDA'
        ELSE '❌ ESTA DEVERIA TER SIDO REMOVIDA'
    END as status
FROM exchange_accounts 
ORDER BY created_at;

COMMIT;