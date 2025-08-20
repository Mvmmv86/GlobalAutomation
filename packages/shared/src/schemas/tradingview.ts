import { z } from 'zod';

export const TradingViewWebhookSchema = z.object({
  // Core fields
  strategy: z.string(),
  ticker: z.string(),
  action: z.enum(['buy', 'sell', 'close', 'close_all']),
  
  // Order details
  quantity: z.number().positive().optional(),
  price: z.number().positive().optional(),
  contracts: z.number().positive().optional(),
  
  // Risk management
  stop_loss: z.number().positive().optional(),
  take_profit: z.number().positive().optional(),
  
  // Position sizing
  size_mode: z.enum(['base', 'quote', 'pct_balance', 'contracts']).default('quote'),
  size_value: z.number().positive().optional(),
  
  // Exchange specific
  exchange: z.enum(['binance', 'bybit']),
  market_type: z.enum(['spot', 'futures', 'perp']).default('futures'),
  
  // Metadata
  alert_id: z.string(),
  timestamp: z.string().datetime().optional(),
  
  // Optional fields
  leverage: z.number().min(1).max(100).optional(),
  reduce_only: z.boolean().default(false),
  time_in_force: z.enum(['GTC', 'IOC', 'FOK']).default('GTC'),
  
  // Custom fields
  account_id: z.string().optional(),
  notes: z.string().optional(),
});

export type TradingViewWebhook = z.infer<typeof TradingViewWebhookSchema>;

// Binance specific schema
export const BinanceFuturesAlertSchema = z.object({
  strategy: z.string(),
  ticker: z.string(), // BTCUSDT format
  action: z.enum(['buy', 'sell', 'close']),
  size_mode: z.enum(['quote', 'pct_balance']).default('quote'),
  size_value: z.number().positive(),
  stop_loss: z.number().positive().optional(),
  take_profit: z.number().positive().optional(),
  leverage: z.number().min(1).max(125).optional(),
  alert_id: z.string(),
});

// Bybit specific schema  
export const BybitPerpAlertSchema = z.object({
  strategy: z.string(),
  ticker: z.string(), // BTCUSDT format
  action: z.enum(['buy', 'sell', 'close']),
  size_mode: z.enum(['contracts', 'pct_balance']).default('contracts'),
  size_value: z.number().positive(),
  stop_loss: z.number().positive().optional(),
  take_profit: z.number().positive().optional(),
  leverage: z.number().min(1).max(100).optional(),
  alert_id: z.string(),
});

export type BinanceFuturesAlert = z.infer<typeof BinanceFuturesAlertSchema>;
export type BybitPerpAlert = z.infer<typeof BybitPerpAlertSchema>;