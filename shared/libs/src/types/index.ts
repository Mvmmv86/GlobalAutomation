export type Exchange = 'binance' | 'bybit';
export type MarketType = 'spot' | 'futures' | 'perp';
export type OrderSide = 'buy' | 'sell';
export type OrderType = 'market' | 'limit' | 'stop' | 'stop_limit';
export type TimeInForce = 'GTC' | 'IOC' | 'FOK';
export type SizeMode = 'base' | 'quote' | 'pct_balance' | 'contracts';

export interface Position {
  id: string;
  symbol: string;
  exchange: Exchange;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  markPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
  leverage: number;
  timestamp: Date;
}

export interface Order {
  id: string;
  clientOrderId: string;
  symbol: string;
  exchange: Exchange;
  side: OrderSide;
  type: OrderType;
  amount: number;
  price?: number;
  filled: number;
  remaining: number;
  status: 'open' | 'closed' | 'canceled' | 'expired' | 'rejected';
  timestamp: Date;
  reduceOnly?: boolean;
}

export interface TradeExecution {
  orderId: string;
  tradeId: string;
  symbol: string;
  side: OrderSide;
  amount: number;
  price: number;
  fee: number;
  feeCurrency: string;
  timestamp: Date;
}

export interface ExchangeAccount {
  id: string;
  name: string;
  exchange: Exchange;
  apiKey: string;
  secretKey: string;
  passphrase?: string;
  testnet: boolean;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface JobPayload {
  alertId: string;
  accountId: string;
  webhook: any;
  retryCount: number;
}

export interface HealthStatus {
  redis: boolean;
  database: boolean;
  queue: boolean;
  exchanges: Record<string, boolean>;
}

export interface PnLRecord {
  id: string;
  accountId: string;
  symbol?: string;
  realizedPnl: number;
  unrealizedPnl: number;
  equity: number;
  timestamp: Date;
}