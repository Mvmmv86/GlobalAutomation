-- Migration: Create Bots System (Copy-Trading Architecture)
-- Description: Sistema de bots gerenciados para copy-trading multi-exchange
-- Date: 2025-10-13

-- ============================================================================
-- TABLE: bots (Catálogo de bots gerenciados pelos administradores)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  description TEXT,
  market_type VARCHAR(50) DEFAULT 'futures',
  status VARCHAR(50) DEFAULT 'active',

  -- Master webhook configuration
  master_webhook_path VARCHAR(255) UNIQUE NOT NULL,
  master_secret VARCHAR(255) NOT NULL,

  -- Default bot settings (clients can override)
  default_leverage INTEGER DEFAULT 10,
  default_margin_usd DECIMAL(18, 2) DEFAULT 50.00,
  default_stop_loss_pct DECIMAL(5, 2) DEFAULT 2.5,
  default_take_profit_pct DECIMAL(5, 2) DEFAULT 5.0,

  -- Bot statistics
  total_subscribers INTEGER DEFAULT 0,
  total_signals_sent INTEGER DEFAULT 0,
  avg_win_rate DECIMAL(5, 2),
  avg_pnl_pct DECIMAL(5, 2),

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Constraints
  CONSTRAINT check_market_type CHECK (market_type IN ('spot', 'futures')),
  CONSTRAINT check_status CHECK (status IN ('active', 'paused', 'archived')),
  CONSTRAINT check_leverage CHECK (default_leverage >= 1 AND default_leverage <= 125),
  CONSTRAINT check_margin CHECK (default_margin_usd >= 5.00)
);

-- Indexes for bots table
CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status);
CREATE INDEX IF NOT EXISTS idx_bots_market_type ON bots(market_type);
CREATE INDEX IF NOT EXISTS idx_bots_webhook_path ON bots(master_webhook_path);

-- ============================================================================
-- TABLE: bot_subscriptions (Client subscriptions to bots)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bot_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
  exchange_account_id UUID NOT NULL REFERENCES exchange_accounts(id) ON DELETE CASCADE,

  status VARCHAR(50) DEFAULT 'active',

  -- Custom client settings (NULL = use bot defaults)
  custom_leverage INTEGER,
  custom_margin_usd DECIMAL(18, 2),
  custom_stop_loss_pct DECIMAL(5, 2),
  custom_take_profit_pct DECIMAL(5, 2),

  -- Risk management
  max_daily_loss_usd DECIMAL(18, 2) DEFAULT 200.00,
  max_concurrent_positions INTEGER DEFAULT 3,
  current_daily_loss_usd DECIMAL(18, 2) DEFAULT 0.00,
  current_positions INTEGER DEFAULT 0,

  -- Subscription statistics
  total_signals_received INTEGER DEFAULT 0,
  total_orders_executed INTEGER DEFAULT 0,
  total_orders_failed INTEGER DEFAULT 0,
  total_pnl_usd DECIMAL(18, 2) DEFAULT 0.00,
  win_count INTEGER DEFAULT 0,
  loss_count INTEGER DEFAULT 0,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_signal_at TIMESTAMP,

  -- Constraints
  CONSTRAINT unique_user_bot UNIQUE(user_id, bot_id),
  CONSTRAINT check_subscription_status CHECK (status IN ('active', 'paused', 'cancelled')),
  CONSTRAINT check_custom_leverage CHECK (custom_leverage IS NULL OR (custom_leverage >= 1 AND custom_leverage <= 125)),
  CONSTRAINT check_custom_margin CHECK (custom_margin_usd IS NULL OR custom_margin_usd >= 5.00)
);

-- Indexes for bot_subscriptions table
CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_user ON bot_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_bot ON bot_subscriptions(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_status ON bot_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_bot_subscriptions_active ON bot_subscriptions(bot_id, status) WHERE status = 'active';

-- ============================================================================
-- TABLE: bot_signals (Master signals sent by admins)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bot_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,

  -- Signal data
  ticker VARCHAR(50) NOT NULL,
  action VARCHAR(50) NOT NULL,
  price DECIMAL(18, 8),

  -- Broadcast statistics
  total_subscribers INTEGER DEFAULT 0,
  successful_executions INTEGER DEFAULT 0,
  failed_executions INTEGER DEFAULT 0,
  broadcast_duration_ms INTEGER,

  -- Signal metadata
  source VARCHAR(50) DEFAULT 'tradingview',
  source_ip VARCHAR(50),
  payload JSONB,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,

  -- Constraints
  CONSTRAINT check_action CHECK (action IN ('buy', 'sell', 'close', 'close_all'))
);

-- Indexes for bot_signals table
CREATE INDEX IF NOT EXISTS idx_bot_signals_bot ON bot_signals(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_signals_created ON bot_signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_signals_ticker ON bot_signals(ticker);

-- ============================================================================
-- TABLE: bot_signal_executions (Individual executions per client)
-- ============================================================================
CREATE TABLE IF NOT EXISTS bot_signal_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id UUID NOT NULL REFERENCES bot_signals(id) ON DELETE CASCADE,
  subscription_id UUID NOT NULL REFERENCES bot_subscriptions(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  -- Execution result
  status VARCHAR(50) NOT NULL,
  exchange_order_id VARCHAR(255),
  executed_price DECIMAL(18, 8),
  executed_quantity DECIMAL(18, 8),

  -- Error tracking
  error_message TEXT,
  error_code VARCHAR(50),

  -- Performance
  execution_time_ms INTEGER,

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,

  -- Constraints
  CONSTRAINT check_execution_status CHECK (status IN ('pending', 'success', 'failed', 'skipped'))
);

-- Indexes for bot_signal_executions table
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_signal ON bot_signal_executions(signal_id);
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_subscription ON bot_signal_executions(subscription_id);
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_user ON bot_signal_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_status ON bot_signal_executions(status);

-- ============================================================================
-- UPDATED TABLE: trading_orders (adicionar referências ao sistema de bots)
-- ============================================================================
DO $$
BEGIN
    -- Adicionar coluna bot_signal_id se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trading_orders' AND column_name = 'bot_signal_id'
    ) THEN
        ALTER TABLE trading_orders ADD COLUMN bot_signal_id UUID REFERENCES bot_signals(id);
        CREATE INDEX idx_trading_orders_bot_signal ON trading_orders(bot_signal_id);
    END IF;

    -- Adicionar coluna bot_subscription_id se não existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trading_orders' AND column_name = 'bot_subscription_id'
    ) THEN
        ALTER TABLE trading_orders ADD COLUMN bot_subscription_id UUID REFERENCES bot_subscriptions(id);
        CREATE INDEX idx_trading_orders_bot_subscription ON trading_orders(bot_subscription_id);
    END IF;
END $$;

-- ============================================================================
-- FUNCTIONS: Auto-update timestamps
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

-- ============================================================================
-- SEED DATA: Demo bot for testing
-- ============================================================================
INSERT INTO bots (
    id,
    name,
    description,
    market_type,
    status,
    master_webhook_path,
    master_secret,
    default_leverage,
    default_margin_usd,
    default_stop_loss_pct,
    default_take_profit_pct
) VALUES (
    gen_random_uuid(),
    'EMA Cross 15m Demo',
    'Estratégia de cruzamento de médias móveis exponenciais em timeframe de 15 minutos. Ideal para day trading em mercados de alta volatilidade.',
    'futures',
    'active',
    'bot-ema-cross-15m',
    'demo-secret-change-in-production',
    10,
    50.00,
    2.5,
    5.0
) ON CONFLICT (master_webhook_path) DO NOTHING;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE bots IS 'Catálogo de bots gerenciados pelos administradores';
COMMENT ON TABLE bot_subscriptions IS 'Assinaturas de clientes aos bots';
COMMENT ON TABLE bot_signals IS 'Sinais master enviados pelos administradores';
COMMENT ON TABLE bot_signal_executions IS 'Execuções individuais de sinais por cliente';

COMMENT ON COLUMN bot_subscriptions.custom_leverage IS 'NULL = usar default do bot';
COMMENT ON COLUMN bot_subscriptions.custom_margin_usd IS 'NULL = usar default do bot';
COMMENT ON COLUMN bot_subscriptions.custom_stop_loss_pct IS 'NULL = seguir stop do bot';
COMMENT ON COLUMN bot_subscriptions.custom_take_profit_pct IS 'NULL = seguir take profit do bot';
