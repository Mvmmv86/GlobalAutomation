-- =====================================================
-- TRADING PLATFORM - COMPLETE SCHEMA CREATION
-- Execute this in Supabase SQL Editor
-- =====================================================

-- Drop existing objects if they exist (for clean setup)
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS webhook_deliveries CASCADE;
DROP TABLE IF EXISTS webhooks CASCADE;
DROP TABLE IF EXISTS exchange_accounts CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop types if they exist
DROP TYPE IF EXISTS positionstatus CASCADE;
DROP TYPE IF EXISTS positionside CASCADE;
DROP TYPE IF EXISTS timeinforce CASCADE;
DROP TYPE IF EXISTS orderstatus CASCADE;
DROP TYPE IF EXISTS ordertype CASCADE;
DROP TYPE IF EXISTS orderside CASCADE;
DROP TYPE IF EXISTS webhookdeliverystatus CASCADE;
DROP TYPE IF EXISTS webhookstatus CASCADE;
DROP TYPE IF EXISTS exchangetype CASCADE;

-- Create ENUM types
CREATE TYPE exchangetype AS ENUM ('binance', 'bybit');
CREATE TYPE webhookstatus AS ENUM ('active', 'paused', 'disabled', 'error');
CREATE TYPE webhookdeliverystatus AS ENUM ('pending', 'processing', 'success', 'failed', 'retrying');
CREATE TYPE ordertype AS ENUM ('market', 'limit', 'stop_loss', 'take_profit', 'stop_limit');
CREATE TYPE orderside AS ENUM ('buy', 'sell');
CREATE TYPE orderstatus AS ENUM ('pending', 'submitted', 'open', 'partially_filled', 'filled', 'canceled', 'rejected', 'expired', 'failed');
CREATE TYPE timeinforce AS ENUM ('gtc', 'ioc', 'fok', 'gtd');
CREATE TYPE positionside AS ENUM ('long', 'short');
CREATE TYPE positionstatus AS ENUM ('open', 'closed', 'closing', 'liquidated');

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    totp_secret VARCHAR(32),
    totp_enabled BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for users
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_is_active ON users(is_active);

-- =====================================================
-- API KEYS TABLE
-- =====================================================
CREATE TABLE api_keys (
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

-- Create indexes for api_keys
CREATE INDEX ix_api_keys_is_active ON api_keys(is_active);
CREATE INDEX ix_api_keys_key_hash ON api_keys(key_hash);
CREATE UNIQUE INDEX ix_api_keys_prefix ON api_keys(prefix);

-- =====================================================
-- EXCHANGE ACCOUNTS TABLE
-- =====================================================
CREATE TABLE exchange_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    exchange exchangetype NOT NULL,
    api_key VARCHAR(512) NOT NULL,
    secret_key VARCHAR(512) NOT NULL,
    passphrase VARCHAR(512),
    testnet BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for exchange_accounts
CREATE INDEX ix_exchange_accounts_exchange ON exchange_accounts(exchange);
CREATE INDEX ix_exchange_accounts_is_active ON exchange_accounts(is_active);
CREATE INDEX ix_exchange_accounts_testnet ON exchange_accounts(testnet);

-- =====================================================
-- WEBHOOKS TABLE
-- =====================================================
CREATE TABLE webhooks (
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
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for webhooks
CREATE UNIQUE INDEX ix_webhooks_url_path ON webhooks(url_path);

-- =====================================================
-- WEBHOOK DELIVERIES TABLE
-- =====================================================
CREATE TABLE webhook_deliveries (
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

-- =====================================================
-- ORDERS TABLE
-- =====================================================
CREATE TABLE orders (
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

-- Create indexes for orders
CREATE UNIQUE INDEX ix_orders_client_order_id ON orders(client_order_id);
CREATE INDEX ix_orders_external_id ON orders(external_id);
CREATE INDEX ix_orders_status ON orders(status);
CREATE INDEX ix_orders_symbol ON orders(symbol);

-- =====================================================
-- POSITIONS TABLE
-- =====================================================
CREATE TABLE positions (
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

-- Create indexes for positions
CREATE INDEX ix_positions_external_id ON positions(external_id);
CREATE INDEX ix_positions_status ON positions(status);
CREATE INDEX ix_positions_symbol ON positions(symbol);

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
SELECT 'Trading Platform Schema Created Successfully! 🎉' as message,
       'All 7 tables with indexes and relationships ready!' as details;