-- Migration: Fix positions duplicates
-- Date: 2025-12-10
-- Description: Add UNIQUE constraint to prevent duplicate positions per account/symbol/side
-- This is safe because we already cleaned up existing duplicates

-- Step 1: First, let's check if there are any remaining duplicates before adding constraint
-- (Run this SELECT first to verify)
/*
SELECT exchange_account_id, symbol, side, COUNT(*) as count
FROM positions
WHERE status = 'open'
GROUP BY exchange_account_id, symbol, side
HAVING COUNT(*) > 1;
*/

-- Step 2: If there are duplicates, keep only the most recent one per group
-- This CTE finds IDs to DELETE (all except the most recent per group)
WITH duplicates_to_delete AS (
    SELECT p.id
    FROM positions p
    INNER JOIN (
        SELECT exchange_account_id, symbol, side, MAX(created_at) as max_created
        FROM positions
        WHERE status = 'open'
        GROUP BY exchange_account_id, symbol, side
        HAVING COUNT(*) > 1
    ) dup ON p.exchange_account_id = dup.exchange_account_id
         AND p.symbol = dup.symbol
         AND p.side = dup.side
         AND p.created_at < dup.max_created
    WHERE p.status = 'open'
)
UPDATE positions
SET status = 'closed',
    closed_at = NOW(),
    updated_at = NOW()
WHERE id IN (SELECT id FROM duplicates_to_delete);

-- Step 3: Create unique index for open positions only (partial index)
-- This allows multiple closed positions but only ONE open position per account/symbol/side
DROP INDEX IF EXISTS idx_positions_unique_open;
CREATE UNIQUE INDEX idx_positions_unique_open
ON positions (exchange_account_id, symbol, side)
WHERE status = 'open';

-- Step 4: Add index for faster lookups during sync
DROP INDEX IF EXISTS idx_positions_account_symbol_status;
CREATE INDEX idx_positions_account_symbol_status
ON positions (exchange_account_id, symbol, status);

-- Step 5: Normalize existing data (uppercase symbols, lowercase side)
UPDATE positions
SET symbol = UPPER(REPLACE(symbol, '-', '')),
    side = LOWER(side)
WHERE symbol != UPPER(REPLACE(symbol, '-', ''))
   OR side != LOWER(side);

-- Verification query (run after migration)
/*
SELECT
    'Total positions' as metric,
    COUNT(*) as value
FROM positions
UNION ALL
SELECT
    'Open positions' as metric,
    COUNT(*) as value
FROM positions WHERE status = 'open'
UNION ALL
SELECT
    'Unique constraint working' as metric,
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END as value
FROM (
    SELECT exchange_account_id, symbol, side, COUNT(*)
    FROM positions WHERE status = 'open'
    GROUP BY exchange_account_id, symbol, side
    HAVING COUNT(*) > 1
) dup;
*/
