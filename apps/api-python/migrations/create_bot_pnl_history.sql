-- Migration: Create bot_pnl_history table for tracking P&L over time
-- This enables charts showing performance history per bot subscription

-- Table to store daily P&L snapshots per subscription
CREATE TABLE IF NOT EXISTS bot_pnl_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES bot_subscriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,

    -- Date of the snapshot (one per day per subscription)
    snapshot_date DATE NOT NULL,

    -- Daily metrics
    daily_pnl_usd DECIMAL(20, 8) NOT NULL DEFAULT 0,
    daily_trades INTEGER NOT NULL DEFAULT 0,
    daily_wins INTEGER NOT NULL DEFAULT 0,
    daily_losses INTEGER NOT NULL DEFAULT 0,

    -- Cumulative metrics (running totals up to this date)
    cumulative_pnl_usd DECIMAL(20, 8) NOT NULL DEFAULT 0,
    cumulative_trades INTEGER NOT NULL DEFAULT 0,
    cumulative_wins INTEGER NOT NULL DEFAULT 0,
    cumulative_losses INTEGER NOT NULL DEFAULT 0,

    -- Win rate at this point in time
    win_rate_pct DECIMAL(5, 2) NOT NULL DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Ensure one snapshot per day per subscription
    UNIQUE(subscription_id, snapshot_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_subscription_id ON bot_pnl_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_user_id ON bot_pnl_history(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_bot_id ON bot_pnl_history(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_snapshot_date ON bot_pnl_history(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_sub_date ON bot_pnl_history(subscription_id, snapshot_date DESC);

-- Table to track individual trades for detailed analytics
CREATE TABLE IF NOT EXISTS bot_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES bot_subscriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    signal_execution_id UUID REFERENCES bot_signal_executions(id) ON DELETE SET NULL,

    -- Trade details
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
    direction VARCHAR(10) NOT NULL, -- 'long' or 'short'

    -- Entry details
    entry_price DECIMAL(20, 8) NOT NULL,
    entry_quantity DECIMAL(20, 8) NOT NULL,
    entry_order_id VARCHAR(100),
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Exit details (NULL while trade is open)
    exit_price DECIMAL(20, 8),
    exit_quantity DECIMAL(20, 8),
    exit_order_id VARCHAR(100),
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_reason VARCHAR(20), -- 'take_profit', 'stop_loss', 'manual', 'signal'

    -- P&L (calculated when trade closes)
    pnl_usd DECIMAL(20, 8),
    pnl_pct DECIMAL(10, 4),
    is_winner BOOLEAN,

    -- Trade status
    status VARCHAR(20) NOT NULL DEFAULT 'open', -- 'open', 'closed', 'cancelled'

    -- Fees
    entry_fee_usd DECIMAL(20, 8) DEFAULT 0,
    exit_fee_usd DECIMAL(20, 8) DEFAULT 0,
    total_fee_usd DECIMAL(20, 8) DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for bot_trades
CREATE INDEX IF NOT EXISTS idx_bot_trades_subscription_id ON bot_trades(subscription_id);
CREATE INDEX IF NOT EXISTS idx_bot_trades_user_id ON bot_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_trades_status ON bot_trades(status);
CREATE INDEX IF NOT EXISTS idx_bot_trades_symbol ON bot_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_bot_trades_entry_time ON bot_trades(entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_bot_trades_exit_time ON bot_trades(exit_time DESC);
CREATE INDEX IF NOT EXISTS idx_bot_trades_is_winner ON bot_trades(is_winner);

-- Trigger to update updated_at on bot_pnl_history
CREATE OR REPLACE FUNCTION update_bot_pnl_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_bot_pnl_history_updated_at ON bot_pnl_history;
CREATE TRIGGER trigger_bot_pnl_history_updated_at
    BEFORE UPDATE ON bot_pnl_history
    FOR EACH ROW
    EXECUTE FUNCTION update_bot_pnl_history_updated_at();

-- Trigger to update updated_at on bot_trades
DROP TRIGGER IF EXISTS trigger_bot_trades_updated_at ON bot_trades;
CREATE TRIGGER trigger_bot_trades_updated_at
    BEFORE UPDATE ON bot_trades
    FOR EACH ROW
    EXECUTE FUNCTION update_bot_pnl_history_updated_at();

-- Comments
COMMENT ON TABLE bot_pnl_history IS 'Daily P&L snapshots per bot subscription for performance charts';
COMMENT ON TABLE bot_trades IS 'Individual trades executed by bots for detailed analytics';
COMMENT ON COLUMN bot_pnl_history.win_rate_pct IS 'Win rate percentage at the time of snapshot';
COMMENT ON COLUMN bot_trades.exit_reason IS 'Reason trade was closed: take_profit, stop_loss, manual, or signal';
