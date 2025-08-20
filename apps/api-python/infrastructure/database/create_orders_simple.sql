-- Criar apenas as tabelas necessárias para ordens
-- Sem foreign keys complexas para evitar conflitos

-- Tabela de ordens (principal)
CREATE TABLE IF NOT EXISTS trading_orders (
    id SERIAL PRIMARY KEY,
    webhook_delivery_id INTEGER,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'buy', 'sell'
    order_type VARCHAR(20) NOT NULL, -- 'market', 'limit'
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8),
    status VARCHAR(50) DEFAULT 'pending',
    exchange VARCHAR(50) DEFAULT 'binance',
    exchange_order_id VARCHAR(100),
    filled_quantity DECIMAL(18, 8) DEFAULT 0,
    average_price DECIMAL(18, 8),
    error_message TEXT,
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de contas de exchange
CREATE TABLE IF NOT EXISTS trading_accounts (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(50) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT,
    testnet BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_trading_orders_status ON trading_orders(status);
CREATE INDEX IF NOT EXISTS idx_trading_orders_symbol ON trading_orders(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_orders_created_at ON trading_orders(created_at DESC);