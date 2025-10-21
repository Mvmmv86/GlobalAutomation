-- Migration: Add Stop Loss and Take Profit columns to bot_signal_executions
-- Date: 2025-10-21
-- Description: Add columns to track SL/TP order IDs and prices

-- Add SL/TP columns to bot_signal_executions table
ALTER TABLE bot_signal_executions
ADD COLUMN IF NOT EXISTS stop_loss_order_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS take_profit_order_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS stop_loss_price DECIMAL(18, 8),
ADD COLUMN IF NOT EXISTS take_profit_price DECIMAL(18, 8);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_sl_order
ON bot_signal_executions(stop_loss_order_id)
WHERE stop_loss_order_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_bot_signal_executions_tp_order
ON bot_signal_executions(take_profit_order_id)
WHERE take_profit_order_id IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN bot_signal_executions.stop_loss_order_id
IS 'ID da ordem de Stop Loss criada na exchange';

COMMENT ON COLUMN bot_signal_executions.take_profit_order_id
IS 'ID da ordem de Take Profit criada na exchange';

COMMENT ON COLUMN bot_signal_executions.stop_loss_price
IS 'Preço configurado para o Stop Loss';

COMMENT ON COLUMN bot_signal_executions.take_profit_price
IS 'Preço configurado para o Take Profit';
