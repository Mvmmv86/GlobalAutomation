-- Tabelas para sistema de ordens
-- Compatível com pgBouncer transaction mode

-- Tabela de contas de exchange
CREATE TABLE IF NOT EXISTS exchange_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    exchange VARCHAR(50) NOT NULL, -- 'binance', 'bybit', 'okx'
    account_name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    testnet BOOLEAN DEFAULT true, -- Usar testnet por segurança
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de webhooks recebidos
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id SERIAL PRIMARY KEY,
    webhook_path VARCHAR(255),
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'received', -- received, processing, processed, failed
    hmac_verified BOOLEAN DEFAULT false,
    processed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de ordens
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    webhook_delivery_id INTEGER REFERENCES webhook_deliveries(id),
    exchange_account_id INTEGER REFERENCES exchange_accounts(id),
    exchange VARCHAR(50) NOT NULL,
    exchange_order_id VARCHAR(100), -- ID da ordem na exchange
    symbol VARCHAR(20) NOT NULL, -- BTCUSDT
    side VARCHAR(10) NOT NULL, -- buy, sell
    order_type VARCHAR(20) NOT NULL, -- market, limit
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8),
    status VARCHAR(50) DEFAULT 'pending', -- pending, submitted, filled, partially_filled, cancelled, failed
    filled_quantity DECIMAL(18, 8) DEFAULT 0,
    average_price DECIMAL(18, 8),
    commission DECIMAL(18, 8),
    commission_asset VARCHAR(10),
    stop_loss_price DECIMAL(18, 8),
    take_profit_price DECIMAL(18, 8),
    error_message TEXT,
    raw_response JSONB, -- Resposta completa da exchange
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP
);

-- Tabela de execuções (trades)
CREATE TABLE IF NOT EXISTS trade_executions (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    exchange_trade_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    quantity DECIMAL(18, 8) NOT NULL,
    commission DECIMAL(18, 8),
    commission_asset VARCHAR(10),
    executed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de posições abertas
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    exchange_account_id INTEGER REFERENCES exchange_accounts(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- long, short
    quantity DECIMAL(18, 8) NOT NULL,
    entry_price DECIMAL(18, 8) NOT NULL,
    current_price DECIMAL(18, 8),
    unrealized_pnl DECIMAL(18, 8),
    realized_pnl DECIMAL(18, 8),
    stop_loss_price DECIMAL(18, 8),
    take_profit_price DECIMAL(18, 8),
    leverage INTEGER DEFAULT 1,
    margin_type VARCHAR(20) DEFAULT 'cross', -- cross, isolated
    status VARCHAR(20) DEFAULT 'open', -- open, closed
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_exchange_accounts_updated_at BEFORE UPDATE
    ON exchange_accounts FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE
    ON orders FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_positions_updated_at BEFORE UPDATE
    ON positions FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();