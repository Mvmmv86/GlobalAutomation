-- =====================================================
-- GLOBALTRADE_PROD - COMPLETE SCHEMA MIGRATION
-- Execute this in Supabase SQL Editor for production database
-- Generated: 2025-11-27
-- =====================================================

-- ============================================================================
-- STEP 1: Create ENUM types
-- ============================================================================

-- Exchange type
DO $$ BEGIN CREATE TYPE exchangetype AS ENUM ('binance', 'bybit', 'bingx'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Add 'bingx' to existing enum if it exists but doesn't have bingx
DO $$ BEGIN ALTER TYPE exchangetype ADD VALUE IF NOT EXISTS 'bingx'; EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- Webhook status
DO $$ BEGIN CREATE TYPE webhookstatus AS ENUM ('active', 'paused', 'disabled', 'error'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Webhook delivery status
DO $$ BEGIN CREATE TYPE webhookdeliverystatus AS ENUM ('pending', 'processing', 'success', 'failed', 'retrying'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Order types
DO $$ BEGIN CREATE TYPE ordertype AS ENUM ('market', 'limit', 'stop_loss', 'take_profit', 'stop_limit'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE orderside AS ENUM ('buy', 'sell'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE orderstatus AS ENUM ('pending', 'submitted', 'open', 'partially_filled', 'filled', 'canceled', 'rejected', 'expired', 'failed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE timeinforce AS ENUM ('gtc', 'ioc', 'fok', 'gtd'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Position types
DO $$ BEGIN CREATE TYPE positionside AS ENUM ('long', 'short'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE positionstatus AS ENUM ('open', 'closed', 'closing', 'liquidated'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Notification types
DO $$ BEGIN CREATE TYPE notificationtype AS ENUM ('success', 'warning', 'error', 'info'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE notificationcategory AS ENUM ('order', 'position', 'system', 'market', 'bot', 'price_alert'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================================
-- STEP 2: Create base tables
-- ============================================================================

-- USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    is_admin BOOLEAN DEFAULT false,
    totp_secret VARCHAR(32),
    totp_enabled BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS ix_users_is_admin ON users(is_admin);

-- API KEYS TABLE
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    prefix VARCHAR(8) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    permissions JSONB,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 100,
    rate_limit_per_hour INTEGER NOT NULL DEFAULT 5000,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_api_keys_is_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS ix_api_keys_key_hash ON api_keys(key_hash);

-- EXCHANGE ACCOUNTS TABLE
CREATE TABLE IF NOT EXISTS exchange_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    exchange exchangetype NOT NULL,
    api_key VARCHAR(512) NOT NULL,
    secret_key VARCHAR(512) NOT NULL,
    passphrase VARCHAR(512),
    testnet BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_main BOOLEAN DEFAULT false,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_exchange_accounts_exchange ON exchange_accounts(exchange);
CREATE INDEX IF NOT EXISTS ix_exchange_accounts_is_active ON exchange_accounts(is_active);
CREATE INDEX IF NOT EXISTS ix_exchange_accounts_testnet ON exchange_accounts(testnet);
CREATE INDEX IF NOT EXISTS idx_exchange_accounts_is_main ON exchange_accounts(is_main);

-- WEBHOOKS TABLE
CREATE TABLE IF NOT EXISTS webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    url_path VARCHAR(255) NOT NULL UNIQUE,
    secret VARCHAR(255) NOT NULL,
    status webhookstatus NOT NULL DEFAULT 'active',
    is_public BOOLEAN NOT NULL DEFAULT false,
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
    rate_limit_per_hour INTEGER NOT NULL DEFAULT 1000,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_delay_seconds INTEGER NOT NULL DEFAULT 60,
    allowed_ips TEXT,
    required_headers TEXT,
    payload_validation_schema TEXT,
    total_deliveries INTEGER NOT NULL DEFAULT 0,
    successful_deliveries INTEGER NOT NULL DEFAULT 0,
    failed_deliveries INTEGER NOT NULL DEFAULT 0,
    last_delivery_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    auto_pause_on_errors BOOLEAN NOT NULL DEFAULT true,
    error_threshold INTEGER NOT NULL DEFAULT 10,
    consecutive_errors INTEGER NOT NULL DEFAULT 0,
    -- Trading parameters
    default_margin_usd DECIMAL(20, 2) DEFAULT 100.00,
    default_leverage INTEGER DEFAULT 10,
    default_stop_loss_pct DECIMAL(5, 2) DEFAULT 3.00,
    default_take_profit_pct DECIMAL(5, 2) DEFAULT 5.00,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_webhooks_url_path ON webhooks(url_path);

-- WEBHOOK DELIVERIES TABLE
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status webhookdeliverystatus NOT NULL DEFAULT 'pending',
    payload JSONB NOT NULL,
    headers JSONB NOT NULL,
    source_ip VARCHAR(45),
    user_agent TEXT,
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_duration_ms INTEGER,
    hmac_valid BOOLEAN,
    ip_allowed BOOLEAN,
    headers_valid BOOLEAN,
    payload_valid BOOLEAN,
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    orders_created INTEGER NOT NULL DEFAULT 0,
    orders_executed INTEGER NOT NULL DEFAULT 0,
    orders_failed INTEGER NOT NULL DEFAULT 0,
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ORDERS TABLE
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255),
    client_order_id VARCHAR(255) NOT NULL UNIQUE,
    symbol VARCHAR(50) NOT NULL,
    side orderside NOT NULL,
    type ordertype NOT NULL,
    status orderstatus NOT NULL DEFAULT 'pending',
    quantity NUMERIC(20,8) NOT NULL,
    price NUMERIC(20,8),
    stop_price NUMERIC(20,8),
    filled_quantity NUMERIC(20,8) NOT NULL DEFAULT 0,
    average_fill_price NUMERIC(20,8),
    fees_paid NUMERIC(20,8) NOT NULL DEFAULT 0,
    fee_currency VARCHAR(10),
    time_in_force timeinforce NOT NULL DEFAULT 'gtc',
    good_till_date TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    first_fill_at TIMESTAMPTZ,
    last_fill_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    source VARCHAR(50) NOT NULL DEFAULT 'webhook',
    webhook_delivery_id UUID REFERENCES webhook_deliveries(id) ON DELETE SET NULL,
    original_payload JSONB,
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER NOT NULL DEFAULT 0,
    exchange_response JSONB,
    reduce_only BOOLEAN NOT NULL DEFAULT false,
    post_only BOOLEAN NOT NULL DEFAULT false,
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_client_order_id ON orders(client_order_id);
CREATE INDEX IF NOT EXISTS ix_orders_external_id ON orders(external_id);
CREATE INDEX IF NOT EXISTS ix_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS ix_orders_symbol ON orders(symbol);

-- POSITIONS TABLE
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255),
    symbol VARCHAR(50) NOT NULL,
    side positionside NOT NULL,
    status positionstatus NOT NULL DEFAULT 'open',
    size NUMERIC(20,8) NOT NULL,
    entry_price NUMERIC(20,8) NOT NULL,
    mark_price NUMERIC(20,8),
    unrealized_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    realized_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    initial_margin NUMERIC(20,8) NOT NULL,
    maintenance_margin NUMERIC(20,8) NOT NULL,
    leverage NUMERIC(5,2) NOT NULL,
    liquidation_price NUMERIC(20,8),
    bankruptcy_price NUMERIC(20,8),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ,
    last_update_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_fees NUMERIC(20,8) NOT NULL DEFAULT 0,
    funding_fees NUMERIC(20,8) NOT NULL DEFAULT 0,
    exchange_data JSONB,
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_positions_external_id ON positions(external_id);
CREATE INDEX IF NOT EXISTS ix_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS ix_positions_symbol ON positions(symbol);

-- ============================================================================
-- STEP 3: Create BOTS system tables
-- ============================================================================

-- BOTS TABLE
CREATE TABLE IF NOT EXISTS bots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    market_type VARCHAR(50) DEFAULT 'futures',
    status VARCHAR(50) DEFAULT 'active',
    master_webhook_path VARCHAR(255) UNIQUE NOT NULL,
    master_secret VARCHAR(255) NOT NULL,
    default_leverage INTEGER DEFAULT 10,
    default_margin_usd DECIMAL(18, 2) DEFAULT 50.00,
    default_stop_loss_pct DECIMAL(5, 2) DEFAULT 2.5,
    default_take_profit_pct DECIMAL(5, 2) DEFAULT 5.0,
    allowed_directions VARCHAR(20) DEFAULT 'both',
    total_subscribers INTEGER DEFAULT 0,
    total_signals_sent INTEGER DEFAULT 0,
    avg_win_rate DECIMAL(5, 2),
    avg_pnl_pct DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_market_type CHECK (market_type IN ('spot', 'futures')),
    CONSTRAINT check_status CHECK (status IN ('active', 'paused', 'archived')),
    CONSTRAINT check_leverage CHECK (default_leverage >= 1 AND default_leverage <= 125),
    CONSTRAINT check_margin CHECK (default_margin_usd >= 5.00),
    CONSTRAINT check_allowed_directions CHECK (allowed_directions IN ('buy_only', 'sell_only', 'both'))
);

CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status);
CREATE INDEX IF NOT EXISTS idx_bots_market_type ON bots(market_type);
CREATE INDEX IF NOT EXISTS idx_bots_webhook_path ON bots(master_webhook_path);
CREATE INDEX IF NOT EXISTS idx_bots_allowed_directions ON bots(allowed_directions);

-- BOT SUBSCRIPTIONS TABLE
CREATE TABLE IF NOT EXISTS bot_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'active',
    custom_leverage INTEGER,
    custom_margin_usd DECIMAL(18, 2),
    custom_stop_loss_pct DECIMAL(5, 2),
    custom_take_profit_pct DECIMAL(5, 2),
    max_daily_loss_usd DECIMAL(18, 2) DEFAULT 200.00,
    max_concurrent_positions INTEGER DEFAULT 3,
    current_daily_loss_usd DECIMAL(18, 2) DEFAULT 0.00,
    current_positions INTEGER DEFAULT 0,
    total_signals_received INTEGER DEFAULT 0,
    total_orders_executed INTEGER DEFAULT 0,
    total_orders_failed INTEGER DEFAULT 0,
    total_pnl_usd DECIMAL(18, 2) DEFAULT 0.00,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_signal_at TIMESTAMP,
    CONSTRAINT unique_user_bot UNIQUE(user_id, bot_id),
    CONSTRAINT check_subscription_status CHECK (status IN ('active', 'paused', 'cancelled')),
    CONSTRAINT check_custom_leverage CHECK (custom_leverage IS NULL OR (custom_leverage >= 1 AND custom_leverage <= 125)),
    CONSTRAINT check_custom_margin CHECK (custom_margin_usd IS NULL OR custom_margin_usd >= 5.00)
);

CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_user ON bot_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_bot ON bot_subscriptions(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_status ON bot_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_active ON bot_subscriptions(bot_id, status) WHERE status = 'active';

-- BOT SIGNALS TABLE
CREATE TABLE IF NOT EXISTS bot_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    ticker VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    price DECIMAL(18, 8),
    total_subscribers INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    broadcast_duration_ms INTEGER,
    source VARCHAR(50) DEFAULT 'tradingview',
    source_ip VARCHAR(50),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    CONSTRAINT check_action CHECK (action IN ('buy', 'sell', 'close', 'close_all'))
);

CREATE INDEX IF NOT EXISTS idx_bot_signals_bot ON bot_signals(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_signals_created ON bot_signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_signals_ticker ON bot_signals(ticker);

-- BOT SIGNAL EXECUTIONS TABLE
CREATE TABLE IF NOT EXISTS bot_signal_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES bot_signals(id) ON DELETE CASCADE,
    subscription_id UUID NOT NULL REFERENCES bot_subscriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    exchange_order_id VARCHAR(255),
    executed_price DECIMAL(18, 8),
    executed_quantity DECIMAL(18, 8),
    error_message TEXT,
    error_code VARCHAR(50),
    execution_time_ms INTEGER,
    -- SL/TP tracking
    stop_loss_order_id VARCHAR(255),
    take_profit_order_id VARCHAR(255),
    stop_loss_price DECIMAL(18, 8),
    take_profit_price DECIMAL(18, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_execution_status CHECK (status IN ('pending', 'success', 'failed', 'skipped'))
);

CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_signal ON bot_signal_executions(signal_id);
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_subscription ON bot_signal_executions(subscription_id);
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_user ON bot_signal_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_status ON bot_signal_executions(status);
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_sl_order ON bot_signal_executions(stop_loss_order_id) WHERE stop_loss_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_tp_order ON bot_signal_executions(take_profit_order_id) WHERE take_profit_order_id IS NOT NULL;

-- ============================================================================
-- STEP 4: Create ADMIN system tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'admin',
    permissions JSONB DEFAULT '{"bots": true, "users": true, "webhooks": true, "reports": true}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES admins(id),
    CONSTRAINT unique_admin_user UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_admins_user_id ON admins(user_id);
CREATE INDEX IF NOT EXISTS idx_admins_is_active ON admins(is_active);

CREATE TABLE IF NOT EXISTS admin_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_admin_activity_admin_id ON admin_activity_log(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_activity_entity ON admin_activity_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_admin_activity_created_at ON admin_activity_log(created_at DESC);

-- ============================================================================
-- STEP 5: Create P&L History tables
-- ============================================================================

CREATE TABLE IF NOT EXISTS bot_pnl_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES bot_subscriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    daily_pnl_usd DECIMAL(20, 8) NOT NULL DEFAULT 0,
    daily_trades INTEGER NOT NULL DEFAULT 0,
    daily_wins INTEGER NOT NULL DEFAULT 0,
    daily_losses INTEGER NOT NULL DEFAULT 0,
    cumulative_pnl_usd DECIMAL(20, 8) NOT NULL DEFAULT 0,
    cumulative_trades INTEGER NOT NULL DEFAULT 0,
    cumulative_wins INTEGER NOT NULL DEFAULT 0,
    cumulative_losses INTEGER NOT NULL DEFAULT 0,
    win_rate_pct DECIMAL(5, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(subscription_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_subscription_id ON bot_pnl_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_user_id ON bot_pnl_history(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_bot_id ON bot_pnl_history(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_snapshot_date ON bot_pnl_history(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_bot_pnl_history_sub_date ON bot_pnl_history(subscription_id, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS bot_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID NOT NULL REFERENCES bot_subscriptions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    signal_execution_id UUID REFERENCES bot_signal_executions(id) ON DELETE SET NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    entry_quantity DECIMAL(20, 8) NOT NULL,
    entry_order_id VARCHAR(100),
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_price DECIMAL(20, 8),
    exit_quantity DECIMAL(20, 8),
    exit_order_id VARCHAR(100),
    exit_time TIMESTAMP WITH TIME ZONE,
    exit_reason VARCHAR(20),
    pnl_usd DECIMAL(20, 8),
    pnl_pct DECIMAL(10, 4),
    is_winner BOOLEAN,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    entry_fee_usd DECIMAL(20, 8) DEFAULT 0,
    exit_fee_usd DECIMAL(20, 8) DEFAULT 0,
    total_fee_usd DECIMAL(20, 8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bot_trades_subscription_id ON bot_trades(subscription_id);
CREATE INDEX IF NOT EXISTS idx_bot_trades_user_id ON bot_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_trades_status ON bot_trades(status);
CREATE INDEX IF NOT EXISTS idx_bot_trades_symbol ON bot_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_bot_trades_entry_time ON bot_trades(entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_bot_trades_exit_time ON bot_trades(exit_time DESC);
CREATE INDEX IF NOT EXISTS idx_bot_trades_is_winner ON bot_trades(is_winner);

-- ============================================================================
-- STEP 6: Create NOTIFICATIONS table
-- ============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type notificationtype NOT NULL DEFAULT 'info',
    category notificationcategory NOT NULL DEFAULT 'system',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    read BOOLEAN NOT NULL DEFAULT false,
    action_url VARCHAR(512),
    metadata JSONB,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_notifications_read ON notifications(read);
CREATE INDEX IF NOT EXISTS ix_notifications_category ON notifications(category);
CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_notifications_user_unread ON notifications(user_id, read) WHERE read = false;

-- ============================================================================
-- STEP 7: Create CANDLES table (for caching)
-- ============================================================================

CREATE TABLE IF NOT EXISTS candles (
    symbol VARCHAR(20) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    time BIGINT NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL,
    PRIMARY KEY (symbol, interval, time)
);

CREATE INDEX IF NOT EXISTS idx_candles_symbol_interval ON candles(symbol, interval);
CREATE INDEX IF NOT EXISTS idx_candles_time ON candles(time);
CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON candles(symbol, time);

-- ============================================================================
-- STEP 8: Create alembic_version table
-- ============================================================================

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('prod_001') ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 9: Create functions and triggers
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_bots_updated_at ON bots;
CREATE TRIGGER update_bots_updated_at BEFORE UPDATE ON bots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_bot_subscriptions_updated_at ON bot_subscriptions;
CREATE TRIGGER update_bot_subscriptions_updated_at BEFORE UPDATE ON bot_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_admins_updated_at ON admins;
CREATE TRIGGER update_admins_updated_at BEFORE UPDATE ON admins
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_bot_pnl_history_updated_at ON bot_pnl_history;
CREATE TRIGGER trigger_bot_pnl_history_updated_at BEFORE UPDATE ON bot_pnl_history
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_bot_trades_updated_at ON bot_trades;
CREATE TRIGGER trigger_bot_trades_updated_at BEFORE UPDATE ON bot_trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_notifications_updated_at ON notifications;
CREATE TRIGGER trigger_notifications_updated_at BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 10: Success message
-- ============================================================================

SELECT 'GlobalTrade PROD Schema Created Successfully!' as status,
       '22 tables created with all indexes and triggers' as details,
       NOW() as completed_at;
