import ccxt, { type Exchange as CCXTExchange } from 'ccxt';
import type { Exchange, Order, Position, TradeExecution } from '../types';

export interface ExchangeCredentials {
  apiKey: string;
  secret: string;
  passphrase?: string;
  testnet?: boolean;
}

export interface PlaceOrderParams {
  symbol: string;
  side: 'buy' | 'sell';
  amount: number;
  price?: number;
  type?: 'market' | 'limit';
  clientOrderId?: string;
  reduceOnly?: boolean;
  stopLoss?: number;
  takeProfit?: number;
}

export abstract class BaseExchangeAdapter {
  protected exchange: CCXTExchange;
  protected exchangeName: Exchange;

  constructor(credentials: ExchangeCredentials, exchangeName: Exchange) {
    this.exchangeName = exchangeName;
    this.exchange = this.createExchange(credentials);
  }

  protected abstract createExchange(credentials: ExchangeCredentials): CCXTExchange;
  
  abstract normalizeSymbol(symbol: string): string;
  abstract setLeverage(symbol: string, leverage: number): Promise<void>;
  abstract placeOrder(params: PlaceOrderParams): Promise<Order>;
  abstract getPositions(symbol?: string): Promise<Position[]>;
  abstract getOpenOrders(symbol?: string): Promise<Order[]>;
  abstract getTrades(symbol?: string, since?: number): Promise<TradeExecution[]>;
  abstract getBalance(): Promise<Record<string, number>>;
  abstract getTicker(symbol: string): Promise<{ price: number; timestamp: Date }>;
  abstract ping(): Promise<boolean>;

  // Balance validation methods
  abstract getAvailableMargin(): Promise<number>;
  abstract validateBalance(symbol: string, side: 'buy' | 'sell', amount: number, price: number, leverage?: number): Promise<{ isValid: boolean; reason?: string }>;

  protected generateClientOrderId(prefix: string = 'tv'): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8);
    return `${prefix}_${timestamp}_${random}`;
  }

  protected normalizeOrder(order: any): Order {
    return {
      id: order.id,
      clientOrderId: order.clientOrderId || '',
      symbol: order.symbol,
      exchange: this.exchangeName,
      side: order.side,
      type: order.type,
      amount: order.amount,
      price: order.price,
      filled: order.filled,
      remaining: order.remaining,
      status: order.status,
      timestamp: new Date(order.timestamp),
      reduceOnly: order.reduceOnly,
    };
  }

  protected normalizePosition(position: any): Position {
    const side = position.side || (position.contracts > 0 ? 'long' : 'short');
    
    return {
      id: `${this.exchangeName}_${position.symbol}`,
      symbol: position.symbol,
      exchange: this.exchangeName,
      side,
      size: Math.abs(position.contracts || position.size || 0),
      entryPrice: position.entryPrice || 0,
      markPrice: position.markPrice || 0,
      unrealizedPnl: position.unrealizedPnl || 0,
      realizedPnl: position.realizedPnl || 0,
      leverage: position.leverage || 1,
      timestamp: new Date(position.timestamp || Date.now()),
    };
  }
}