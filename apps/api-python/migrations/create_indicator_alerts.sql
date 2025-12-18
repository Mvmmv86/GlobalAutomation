-- =====================================================
-- INDICATOR ALERTS TABLE - Sistema de Alertas de Indicadores
-- Execute this in Supabase SQL Editor
-- =====================================================

-- Drop types if exists for clean setup
DROP TYPE IF EXISTS indicator_type CASCADE;
DROP TYPE IF EXISTS signal_type CASCADE;
DROP TYPE IF EXISTS alert_timeframe CASCADE;
DROP TYPE IF EXISTS alert_sound_type CASCADE;

-- Create ENUM types for indicator alerts
CREATE TYPE indicator_type AS ENUM (
    'nadaraya_watson',  -- NW Envelope (Gaussian Kernel Regression)
    'tpo',              -- Time Price Opportunity (Market Profile)
    'rsi',              -- Relative Strength Index
    'macd',             -- Moving Average Convergence Divergence
    'bollinger',        -- Bollinger Bands
    'ema_cross',        -- EMA Crossover
    'volume_profile',   -- Volume Profile
    'custom'            -- Custom indicator
);

CREATE TYPE signal_type AS ENUM ('buy', 'sell', 'both');

CREATE TYPE alert_timeframe AS ENUM (
    '1m', '3m', '5m', '15m', '30m',
    '1h', '2h', '4h', '6h', '8h', '12h',
    '1d', '3d', '1w', '1M'
);

CREATE TYPE alert_sound_type AS ENUM (
    'default',      -- Som padrão (acorde agradável)
    'bell',         -- Sino
    'chime',        -- Carrilhão
    'alarm',        -- Alerta urgente
    'notification', -- Som de notificação
    'none'          -- Sem som
);

-- =====================================================
-- INDICATOR ALERTS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS indicator_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- User relationship (required)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Indicator configuration
    indicator_type indicator_type NOT NULL,
    symbol VARCHAR(20) NOT NULL,                    -- e.g., 'BTCUSDT', 'ETHUSDT'
    timeframe alert_timeframe NOT NULL,             -- Timeframe to monitor

    -- Signal settings
    signal_type signal_type NOT NULL DEFAULT 'both', -- BUY, SELL, or BOTH

    -- Indicator-specific parameters (JSON for flexibility)
    -- For NW: { bandwidth: 8, mult: 3.0 }
    -- For RSI: { period: 14, overbought: 70, oversold: 30 }
    indicator_params JSONB DEFAULT '{}',

    -- Notification settings
    message_template VARCHAR(500) DEFAULT 'Signal {signal_type} detected for {symbol} on {timeframe}',

    -- Notification channels
    push_enabled BOOLEAN NOT NULL DEFAULT true,     -- In-app notification
    email_enabled BOOLEAN NOT NULL DEFAULT false,   -- Email notification
    sound_type alert_sound_type NOT NULL DEFAULT 'default',

    -- Status and tracking
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER NOT NULL DEFAULT 0,

    -- Cooldown period (avoid spam) - in seconds
    cooldown_seconds INTEGER NOT NULL DEFAULT 300,  -- 5 minutes default

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================
-- INDICATOR ALERT HISTORY TABLE (for tracking triggers)
-- =====================================================
CREATE TABLE IF NOT EXISTS indicator_alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Reference to the alert configuration
    alert_id UUID NOT NULL REFERENCES indicator_alerts(id) ON DELETE CASCADE,

    -- Signal details
    signal_type VARCHAR(10) NOT NULL,               -- 'buy' or 'sell'
    signal_price DECIMAL(20, 8),                    -- Price when signal triggered

    -- Notification status
    push_sent BOOLEAN NOT NULL DEFAULT false,
    email_sent BOOLEAN NOT NULL DEFAULT false,

    -- Metadata
    metadata JSONB,                                 -- Additional signal data

    -- Timestamps
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Index for user_id (get alerts for a user)
CREATE INDEX IF NOT EXISTS ix_indicator_alerts_user_id ON indicator_alerts(user_id);

-- Index for active alerts (for monitoring service)
CREATE INDEX IF NOT EXISTS ix_indicator_alerts_active ON indicator_alerts(is_active) WHERE is_active = true;

-- Index for symbol (query by symbol)
CREATE INDEX IF NOT EXISTS ix_indicator_alerts_symbol ON indicator_alerts(symbol);

-- Composite index for monitoring service (active alerts by user)
CREATE INDEX IF NOT EXISTS ix_indicator_alerts_user_active ON indicator_alerts(user_id, is_active) WHERE is_active = true;

-- Index for alert history
CREATE INDEX IF NOT EXISTS ix_alert_history_alert_id ON indicator_alert_history(alert_id);
CREATE INDEX IF NOT EXISTS ix_alert_history_triggered_at ON indicator_alert_history(triggered_at DESC);

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS
ALTER TABLE indicator_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE indicator_alert_history ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own alerts
CREATE POLICY indicator_alerts_select_policy ON indicator_alerts
    FOR SELECT
    USING (user_id = auth.uid());

-- Policy: Users can insert their own alerts
CREATE POLICY indicator_alerts_insert_policy ON indicator_alerts
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Policy: Users can update their own alerts
CREATE POLICY indicator_alerts_update_policy ON indicator_alerts
    FOR UPDATE
    USING (user_id = auth.uid());

-- Policy: Users can delete their own alerts
CREATE POLICY indicator_alerts_delete_policy ON indicator_alerts
    FOR DELETE
    USING (user_id = auth.uid());

-- Alert History policies (through alert ownership)
CREATE POLICY alert_history_select_policy ON indicator_alert_history
    FOR SELECT
    USING (
        alert_id IN (
            SELECT id FROM indicator_alerts WHERE user_id = auth.uid()
        )
    );

CREATE POLICY alert_history_insert_policy ON indicator_alert_history
    FOR INSERT
    WITH CHECK (true);  -- System can insert

-- =====================================================
-- TRIGGER: Auto-update updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_indicator_alerts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_indicator_alerts_updated_at ON indicator_alerts;
CREATE TRIGGER trigger_indicator_alerts_updated_at
    BEFORE UPDATE ON indicator_alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_indicator_alerts_updated_at();

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
SELECT 'Indicator Alerts Tables Created Successfully!' as message,
       'Tables indicator_alerts and indicator_alert_history with indexes and RLS ready!' as details;
