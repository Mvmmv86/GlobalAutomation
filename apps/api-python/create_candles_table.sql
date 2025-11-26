-- Script SQL para criar tabela de candles
-- Execute este script no banco de dados para criar a tabela

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

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_candles_symbol_interval ON candles(symbol, interval);
CREATE INDEX IF NOT EXISTS idx_candles_time ON candles(time);
CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON candles(symbol, time);

-- Constraint única para evitar duplicatas
ALTER TABLE candles ADD CONSTRAINT uq_candle UNIQUE (symbol, interval, time) ON CONFLICT DO NOTHING;

-- Comentários para documentação
COMMENT ON TABLE candles IS 'Armazena dados históricos de candles (OHLCV) para cache';
COMMENT ON COLUMN candles.symbol IS 'Símbolo do par de trading (ex: BTCUSDT)';
COMMENT ON COLUMN candles.interval IS 'Intervalo do candle (1m, 5m, 15m, 1h, etc)';
COMMENT ON COLUMN candles.time IS 'Timestamp em millisegundos';
COMMENT ON COLUMN candles.open IS 'Preço de abertura';
COMMENT ON COLUMN candles.high IS 'Preço máximo';
COMMENT ON COLUMN candles.low IS 'Preço mínimo';
COMMENT ON COLUMN candles.close IS 'Preço de fechamento';
COMMENT ON COLUMN candles.volume IS 'Volume negociado';
COMMENT ON COLUMN candles.created_at IS 'Timestamp de criação do registro em ms';
COMMENT ON COLUMN candles.updated_at IS 'Timestamp da última atualização em ms';