-- Migration: Adicionar campo position_mode na tabela exchange_accounts
-- Data: 2025-12-02
-- Descrição: Suporte para Hedge Mode e One-Way Mode da BingX

-- Adicionar coluna position_mode (default 'hedge' porque é o padrão da BingX)
ALTER TABLE exchange_accounts
ADD COLUMN IF NOT EXISTS position_mode VARCHAR(20) DEFAULT 'hedge';

-- Comentário explicativo
COMMENT ON COLUMN exchange_accounts.position_mode IS
'Modo de posição da conta: hedge (LONG/SHORT) ou one_way (BOTH). Usado principalmente para BingX.';

-- Índice para consultas rápidas por modo
CREATE INDEX IF NOT EXISTS ix_exchange_accounts_position_mode ON exchange_accounts(position_mode);
