import ccxt, { type Exchange as CCXTExchange } from 'ccxt';
import { BaseExchangeAdapter, ExchangeCredentials, PlaceOrderParams } from './base';
import type { Order, Position, TradeExecution } from '../types';
import { priceCache } from '../utils/price-cache';
import { 
  calculateRequiredMargin, 
  validateBalance as validateBalanceUtil,
  findExistingPosition,
  calculateMarginImpact
} from '../utils/balance';

export class BybitAdapter extends BaseExchangeAdapter {
  constructor(credentials: ExchangeCredentials) {
    super(credentials, 'bybit');
  }

  protected createExchange(credentials: ExchangeCredentials): CCXTExchange {
    return new ccxt.bybit({
      apiKey: credentials.apiKey,
      secret: credentials.secret,
      sandbox: credentials.testnet || false,
      options: {
        defaultType: 'linear', // Use USDT perpetual contracts
      },
      enableRateLimit: true,
    });
  }

  normalizeSymbol(symbol: string): string {
    // Convert from TradingView format (BTCUSD) to Bybit format (BTCUSDT)
    if (symbol.endsWith('USD') && !symbol.endsWith('USDT')) {
      return symbol.replace('USD', 'USDT');
    }
    return symbol;
  }

  async setLeverage(symbol: string, leverage: number): Promise<void> {
    try {
      await this.exchange.setLeverage(leverage, symbol);
    } catch (error) {
      throw new Error(`Failed to set leverage: ${error}`);
    }
  }

  async placeOrder(params: PlaceOrderParams): Promise<Order> {
    const { symbol, side, amount, price, type = 'market', clientOrderId, reduceOnly } = params;
    
    try {
      const orderParams: any = {
        symbol: this.normalizeSymbol(symbol),
        type,
        side,
        amount,
        price,
        params: {
          orderLinkId: clientOrderId || this.generateClientOrderId('bybit'),
        },
      };

      if (reduceOnly) {
        orderParams.params.reduceOnly = true;
      }

      const result = await this.exchange.createOrder(
        orderParams.symbol,
        orderParams.type,
        orderParams.side,
        orderParams.amount,
        orderParams.price,
        orderParams.params
      );

      // Handle SL/TP orders if specified
      if (params.stopLoss) {
        await this.placeStopLoss(symbol, side === 'buy' ? 'sell' : 'buy', amount, params.stopLoss);
      }
      
      if (params.takeProfit) {
        await this.placeTakeProfit(symbol, side === 'buy' ? 'sell' : 'buy', amount, params.takeProfit);
      }

      return this.normalizeOrder(result);
    } catch (error) {
      throw new Error(`Failed to place order: ${error}`);
    }
  }

  private async placeStopLoss(symbol: string, side: string, amount: number, stopPrice: number): Promise<void> {
    await this.exchange.createOrder(
      this.normalizeSymbol(symbol),
      'market',
      side,
      amount,
      undefined,
      {
        stopLoss: stopPrice,
        reduceOnly: true,
        orderLinkId: this.generateClientOrderId('sl'),
      }
    );
  }

  private async placeTakeProfit(symbol: string, side: string, amount: number, price: number): Promise<void> {
    await this.exchange.createOrder(
      this.normalizeSymbol(symbol),
      'market',
      side,
      amount,
      undefined,
      {
        takeProfit: price,
        reduceOnly: true,
        orderLinkId: this.generateClientOrderId('tp'),
      }
    );
  }

  async getPositions(symbol?: string): Promise<Position[]> {
    try {
      const positions = await this.exchange.fetchPositions(symbol ? [this.normalizeSymbol(symbol)] : undefined);
      return positions
        .filter((pos: any) => pos.contracts !== 0)
        .map((pos: any) => this.normalizePosition(pos));
    } catch (error) {
      throw new Error(`Failed to fetch positions: ${error}`);
    }
  }

  async getOpenOrders(symbol?: string): Promise<Order[]> {
    try {
      const orders = await this.exchange.fetchOpenOrders(symbol ? this.normalizeSymbol(symbol) : undefined);
      return orders.map((order: any) => this.normalizeOrder(order));
    } catch (error) {
      throw new Error(`Failed to fetch open orders: ${error}`);
    }
  }

  async getTrades(symbol?: string, since?: number): Promise<TradeExecution[]> {
    try {
      const trades = await this.exchange.fetchMyTrades(
        symbol ? this.normalizeSymbol(symbol) : undefined,
        since
      );
      
      return trades.map((trade: any) => ({
        orderId: trade.order,
        tradeId: trade.id,
        symbol: trade.symbol,
        side: trade.side,
        amount: trade.amount,
        price: trade.price,
        fee: trade.fee?.cost || 0,
        feeCurrency: trade.fee?.currency || 'USDT',
        timestamp: new Date(trade.timestamp),
      }));
    } catch (error) {
      throw new Error(`Failed to fetch trades: ${error}`);
    }
  }

  async getBalance(): Promise<Record<string, number>> {
    try {
      const balance = await this.exchange.fetchBalance();
      const result: Record<string, number> = {};
      
      for (const [currency, info] of Object.entries(balance)) {
        if (typeof info === 'object' && info && 'free' in info) {
          result[currency] = (info as any).free;
        }
      }
      
      return result;
    } catch (error) {
      throw new Error(`Failed to fetch balance: ${error}`);
    }
  }

  async getTicker(symbol: string): Promise<{ price: number; timestamp: Date }> {
    const normalizedSymbol = this.normalizeSymbol(symbol);
    
    // Check cache first
    const cached = priceCache.get('bybit', normalizedSymbol);
    if (cached) {
      return cached;
    }

    try {
      const ticker = await this.exchange.fetchTicker(normalizedSymbol);
      const price = ticker.last || ticker.close || 0;
      const timestamp = new Date(ticker.timestamp || Date.now());
      
      // Cache the result
      if (price > 0) {
        priceCache.set('bybit', normalizedSymbol, price, timestamp);
      }
      
      return { price, timestamp };
    } catch (error) {
      throw new Error(`Failed to fetch ticker for ${symbol}: ${error}`);
    }
  }

  async ping(): Promise<boolean> {
    try {
      await this.exchange.fetchTime();
      return true;
    } catch {
      return false;
    }
  }

  async getAvailableMargin(): Promise<number> {
    try {
      const balance = await this.exchange.fetchBalance();
      
      // For Bybit, check available balance in account info
      if (balance.info && balance.info.result && balance.info.result.list) {
        const usdtBalance = balance.info.result.list.find(
          (account: any) => account.coin === 'USDT'
        );
        if (usdtBalance && usdtBalance.availableBalance) {
          return parseFloat(usdtBalance.availableBalance);
        }
      }
      
      // Fallback: use free USDT balance
      const freeUSDT = balance.USDT?.free || 0;
      return freeUSDT;
    } catch (error) {
      throw new Error(`Failed to get available margin: ${error}`);
    }
  }

  async validateBalance(
    symbol: string, 
    side: 'buy' | 'sell', 
    amount: number, 
    price: number, 
    leverage: number = 1
  ): Promise<{ isValid: boolean; reason?: string }> {
    try {
      // Get current balance and positions
      const [availableMargin, positions] = await Promise.all([
        this.getAvailableMargin(),
        this.getPositions()
      ]);

      // Calculate required margin
      const requiredMargin = calculateRequiredMargin({
        amount,
        price,
        leverage,
        side,
        exchange: 'bybit'
      });

      // Find existing position for this symbol
      const normalizedSymbol = this.normalizeSymbol(symbol);
      const existingPosition = findExistingPosition(positions, normalizedSymbol) || undefined;

      // Calculate margin impact
      const { marginDelta } = calculateMarginImpact(
        { amount, price, leverage, side, exchange: 'bybit' },
        existingPosition
      );

      // Validate balance
      const validation = validateBalanceUtil({
        availableBalance: availableMargin,
        requiredMargin: marginDelta,
        existingPositions: positions,
        symbol: normalizedSymbol,
        side
      });

      return {
        isValid: validation.isValid,
        reason: validation.message
      };
    } catch (error) {
      return {
        isValid: false,
        reason: `Balance validation failed: ${error instanceof Error ? error.message : String(error)}`
      };
    }
  }
}