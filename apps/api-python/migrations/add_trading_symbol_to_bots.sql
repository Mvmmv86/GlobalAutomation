-- Migration: Add trading_symbol column to bots table
-- Description: Adds a trading_symbol column to store the trading pair (e.g., BNBUSDT)
--              This replaces the regex-based extraction from bot name
-- Date: 2025-12-16

-- ============================================================================
-- ADD trading_symbol COLUMN TO bots TABLE
-- ============================================================================

-- Add column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bots' AND column_name = 'trading_symbol'
    ) THEN
        ALTER TABLE bots ADD COLUMN trading_symbol VARCHAR(20);

        -- Add comment explaining the column
        COMMENT ON COLUMN bots.trading_symbol IS 'Trading pair for P&L filtering (e.g., BNBUSDT, ETHUSDT). When set, only trades for this symbol are shown in bot performance.';

        RAISE NOTICE 'Column trading_symbol added to bots table';
    ELSE
        RAISE NOTICE 'Column trading_symbol already exists in bots table';
    END IF;
END $$;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_bots_trading_symbol ON bots(trading_symbol);

-- ============================================================================
-- UPDATE EXISTING BOTS - Try to extract symbol from name
-- ============================================================================

-- For bots with TPO_XXX pattern, auto-populate trading_symbol
UPDATE bots
SET trading_symbol = UPPER(REGEXP_REPLACE(
    REGEXP_REPLACE(name, '^TPO[_\s]+([A-Z]{2,10}).*$', '\1', 'i'),
    '.*', '\0'
)) || 'USDT'
WHERE trading_symbol IS NULL
  AND name ~* '^TPO[_\s]+[A-Z]{2,10}';

-- Show what was updated
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO updated_count FROM bots WHERE trading_symbol IS NOT NULL;
    RAISE NOTICE 'Bots with trading_symbol set: %', updated_count;
END $$;
