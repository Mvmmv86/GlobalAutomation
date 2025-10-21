-- Migration: Add trading parameters to webhooks table
-- Date: 2025-10-14
-- Purpose: Add margin, leverage, stop loss, and take profit configuration for webhooks

-- Add new columns for trading parameters
ALTER TABLE webhooks
ADD COLUMN IF NOT EXISTS default_margin_usd DECIMAL(20, 2) DEFAULT 100.00
    CHECK (default_margin_usd >= 10.00),
ADD COLUMN IF NOT EXISTS default_leverage INTEGER DEFAULT 10
    CHECK (default_leverage >= 1 AND default_leverage <= 125),
ADD COLUMN IF NOT EXISTS default_stop_loss_pct DECIMAL(5, 2) DEFAULT 3.00
    CHECK (default_stop_loss_pct >= 0.1 AND default_stop_loss_pct <= 100.00),
ADD COLUMN IF NOT EXISTS default_take_profit_pct DECIMAL(5, 2) DEFAULT 5.00
    CHECK (default_take_profit_pct >= 0.1 AND default_take_profit_pct <= 1000.00);

-- Add comments for documentation
COMMENT ON COLUMN webhooks.default_margin_usd IS 'Default margin in USD to use per order (min: $10)';
COMMENT ON COLUMN webhooks.default_leverage IS 'Default leverage multiplier (1x - 125x)';
COMMENT ON COLUMN webhooks.default_stop_loss_pct IS 'Default stop loss percentage (0.1% - 100%)';
COMMENT ON COLUMN webhooks.default_take_profit_pct IS 'Default take profit percentage (0.1% - 1000%)';

-- Update existing webhooks with default values (already handled by DEFAULT clause)
-- But explicitly update NULL values if any exist
UPDATE webhooks
SET
    default_margin_usd = 100.00
WHERE default_margin_usd IS NULL;

UPDATE webhooks
SET
    default_leverage = 10
WHERE default_leverage IS NULL;

UPDATE webhooks
SET
    default_stop_loss_pct = 3.00
WHERE default_stop_loss_pct IS NULL;

UPDATE webhooks
SET
    default_take_profit_pct = 5.00
WHERE default_take_profit_pct IS NULL;

-- Verify the migration
SELECT
    'Migration completed successfully' as status,
    COUNT(*) as total_webhooks,
    COUNT(CASE WHEN default_margin_usd IS NOT NULL THEN 1 END) as webhooks_with_margin,
    COUNT(CASE WHEN default_leverage IS NOT NULL THEN 1 END) as webhooks_with_leverage,
    AVG(default_margin_usd) as avg_margin_usd,
    AVG(default_leverage) as avg_leverage
FROM webhooks;
