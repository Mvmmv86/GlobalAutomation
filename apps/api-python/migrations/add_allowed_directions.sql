-- Migration: Add allowed_directions column to bots table
-- Date: 2025-10-21
-- Description: Allow admin to configure if bot operates on buy_only, sell_only, or both directions

-- Add allowed_directions column
ALTER TABLE bots
ADD COLUMN IF NOT EXISTS allowed_directions VARCHAR(20) DEFAULT 'both';

-- Add constraint to ensure valid values
ALTER TABLE bots
ADD CONSTRAINT check_allowed_directions
CHECK (allowed_directions IN ('buy_only', 'sell_only', 'both'));

-- Create index for filtering
CREATE INDEX IF NOT EXISTS idx_bots_allowed_directions
ON bots(allowed_directions);

-- Add comment for documentation
COMMENT ON COLUMN bots.allowed_directions IS
'Defines which signal directions are allowed: buy_only (Long only), sell_only (Short only), both (Long and Short)';
