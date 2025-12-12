-- =====================================================
-- Migration: Add SL/TP Monitoring Columns
-- Date: 2025-12-08
-- Description: Adds columns for tracking SL/TP order status
-- =====================================================

-- 1. Add columns to bot_signal_executions for SL/TP status tracking
ALTER TABLE bot_signal_executions
ADD COLUMN IF NOT EXISTS sl_order_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS tp_order_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS sl_filled_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS tp_filled_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS realized_pnl DECIMAL(18,8),
ADD COLUMN IF NOT EXISTS close_reason VARCHAR(20);

-- 2. Add index for faster queries on pending SL/TP orders
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_sltp_status
ON bot_signal_executions(sl_order_status, tp_order_status)
WHERE sl_order_status = 'pending' OR tp_order_status = 'pending';

-- 3. Ensure bot_trades table has all necessary columns
-- Check if status column exists, if not add it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bot_trades' AND column_name = 'status'
    ) THEN
        ALTER TABLE bot_trades ADD COLUMN status VARCHAR(20) DEFAULT 'closed';
    END IF;
END $$;

-- Add exit_reason if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bot_trades' AND column_name = 'exit_reason'
    ) THEN
        ALTER TABLE bot_trades ADD COLUMN exit_reason VARCHAR(20);
    END IF;
END $$;

-- Add sl_order_id and tp_order_id if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bot_trades' AND column_name = 'sl_order_id'
    ) THEN
        ALTER TABLE bot_trades ADD COLUMN sl_order_id VARCHAR(100);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bot_trades' AND column_name = 'tp_order_id'
    ) THEN
        ALTER TABLE bot_trades ADD COLUMN tp_order_id VARCHAR(100);
    END IF;
END $$;

-- 4. Add pnl_pct column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bot_trades' AND column_name = 'pnl_pct'
    ) THEN
        ALTER TABLE bot_trades ADD COLUMN pnl_pct DECIMAL(10,4);
    END IF;
END $$;

-- 5. Create index on bot_trades for status lookups
CREATE INDEX IF NOT EXISTS idx_bot_trades_status
ON bot_trades(status);

CREATE INDEX IF NOT EXISTS idx_bot_trades_subscription_status
ON bot_trades(subscription_id, status);

-- 6. Add comment for documentation
COMMENT ON COLUMN bot_signal_executions.sl_order_status IS 'Status of Stop Loss order: pending, filled, canceled';
COMMENT ON COLUMN bot_signal_executions.tp_order_status IS 'Status of Take Profit order: pending, filled, canceled';
COMMENT ON COLUMN bot_signal_executions.realized_pnl IS 'Actual P&L from exchange when trade closed';
COMMENT ON COLUMN bot_signal_executions.close_reason IS 'How the trade was closed: stop_loss, take_profit, manual';

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
SELECT 'SL/TP Monitoring Columns Migration Completed!' as message;
