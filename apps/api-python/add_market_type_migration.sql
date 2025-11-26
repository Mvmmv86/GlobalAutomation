-- Migration: Add market_type column to webhooks table
-- Purpose: Allow users to choose between SPOT and FUTURES markets per webhook
-- Date: 2025-10-13

-- Add market_type column (spot or futures, default: spot)
ALTER TABLE webhooks
ADD COLUMN IF NOT EXISTS market_type VARCHAR(10) DEFAULT 'spot';

-- Add comment
COMMENT ON COLUMN webhooks.market_type IS 'Market type: spot or futures';

-- Add check constraint to ensure only valid values
ALTER TABLE webhooks
ADD CONSTRAINT check_market_type CHECK (market_type IN ('spot', 'futures'));

-- Update existing webhooks to use 'futures' for user's preference
-- (Usuário tem saldo em FUTURES, então definir FUTURES como padrão para webhooks existentes)
UPDATE webhooks
SET market_type = 'futures'
WHERE market_type IS NULL OR market_type = 'spot';

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_webhooks_market_type ON webhooks(market_type);
