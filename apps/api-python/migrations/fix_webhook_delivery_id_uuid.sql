-- Migration: Change webhook_delivery_id from INTEGER to UUID
-- Data: 2025-10-16
-- Descrição: Ajustar tipo de coluna para permitir vinculação com webhook_deliveries

-- Step 1: Alterar tipo da coluna de INTEGER para UUID
ALTER TABLE trading_orders
ALTER COLUMN webhook_delivery_id TYPE UUID USING webhook_delivery_id::text::uuid;

-- Confirmação
SELECT 'Migration completed: webhook_delivery_id now UUID' AS status;
