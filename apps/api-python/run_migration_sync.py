"""Run strategies system migration on Supabase using psycopg2"""

import psycopg2
from urllib.parse import quote_plus

# Using Supabase pooler connection from DIGITAL_OCEAN_BULK_PASTE.txt
DATABASE_URL = "postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

MIGRATION_SQL = """
-- Migration: Create Strategies System (Automated Trading Strategies)

-- ============================================================================
-- TABLE: strategies
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    config_type VARCHAR(20) NOT NULL DEFAULT 'visual',
    config_yaml TEXT,
    pinescript_source TEXT,
    symbols JSONB NOT NULL DEFAULT '[]',
    timeframe VARCHAR(10) NOT NULL DEFAULT '5m',
    is_active BOOLEAN DEFAULT false,
    is_backtesting BOOLEAN DEFAULT false,
    bot_id UUID REFERENCES bots(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT check_config_type CHECK (config_type IN ('visual', 'yaml', 'pinescript')),
    CONSTRAINT check_timeframe CHECK (timeframe IN ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w'))
);

CREATE INDEX IF NOT EXISTS idx_strategies_is_active ON strategies(is_active);
CREATE INDEX IF NOT EXISTS idx_strategies_bot_id ON strategies(bot_id);
CREATE INDEX IF NOT EXISTS idx_strategies_created_by ON strategies(created_by);

-- ============================================================================
-- TABLE: strategy_indicators
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    indicator_type VARCHAR(50) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_indicator_type CHECK (indicator_type IN (
        'nadaraya_watson', 'tpo', 'rsi', 'macd', 'ema', 'bollinger', 'atr', 'volume_profile'
    ))
);

CREATE INDEX IF NOT EXISTS idx_strategy_indicators_strategy ON strategy_indicators(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_indicators_type ON strategy_indicators(indicator_type);

-- ============================================================================
-- TABLE: strategy_conditions
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_conditions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    condition_type VARCHAR(30) NOT NULL,
    conditions JSONB NOT NULL,
    logic_operator VARCHAR(10) DEFAULT 'AND',
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_condition_type CHECK (condition_type IN ('entry_long', 'entry_short', 'exit_long', 'exit_short')),
    CONSTRAINT check_logic_operator CHECK (logic_operator IN ('AND', 'OR'))
);

CREATE INDEX IF NOT EXISTS idx_strategy_conditions_strategy ON strategy_conditions(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_conditions_type ON strategy_conditions(condition_type);

-- ============================================================================
-- TABLE: strategy_signals
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20, 8),
    indicator_values JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    bot_signal_id UUID REFERENCES bot_signals(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_signal_type CHECK (signal_type IN ('long', 'short')),
    CONSTRAINT check_signal_status CHECK (status IN ('pending', 'executed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_strategy_signals_strategy ON strategy_signals(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_symbol ON strategy_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_status ON strategy_signals(status);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_created ON strategy_signals(created_at DESC);

-- ============================================================================
-- TABLE: strategy_backtest_results
-- ============================================================================
CREATE TABLE IF NOT EXISTS strategy_backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    initial_capital DECIMAL(20, 8) DEFAULT 10000,
    leverage INTEGER DEFAULT 10,
    margin_percent DECIMAL(5, 2) DEFAULT 5.00,
    stop_loss_percent DECIMAL(5, 2) DEFAULT 2.00,
    take_profit_percent DECIMAL(5, 2) DEFAULT 4.00,
    include_fees BOOLEAN DEFAULT true,
    include_slippage BOOLEAN DEFAULT true,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5, 2),
    profit_factor DECIMAL(10, 4),
    total_pnl DECIMAL(20, 8),
    total_pnl_percent DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    trades JSONB,
    equity_curve JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_backtest_dates CHECK (end_date > start_date)
);

CREATE INDEX IF NOT EXISTS idx_strategy_backtest_results_strategy ON strategy_backtest_results(strategy_id);
CREATE INDEX IF NOT EXISTS idx_strategy_backtest_results_symbol ON strategy_backtest_results(symbol);
CREATE INDEX IF NOT EXISTS idx_strategy_backtest_results_created ON strategy_backtest_results(created_at DESC);

-- ============================================================================
-- Trigger for updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_strategies_updated_at ON strategies;
CREATE TRIGGER update_strategies_updated_at BEFORE UPDATE ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE strategies IS 'Configuracao de estrategias automatizadas de trading';
COMMENT ON TABLE strategy_indicators IS 'Indicadores tecnicos configurados por estrategia';
COMMENT ON TABLE strategy_conditions IS 'Condicoes de entrada e saida para estrategias';
COMMENT ON TABLE strategy_signals IS 'Sinais de trading gerados pelas estrategias';
COMMENT ON TABLE strategy_backtest_results IS 'Resultados de backtests de estrategias';
"""


def run_migration():
    print("Connecting to Supabase...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        print("Connected!")

        print("Running migration...")
        cursor.execute(MIGRATION_SQL)

        print("Migration completed successfully!")

        # Verify tables were created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'strateg%'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print("\nCreated tables:")
        for t in tables:
            print(f"  - {t[0]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    run_migration()
