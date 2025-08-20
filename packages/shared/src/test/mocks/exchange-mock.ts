import type { Exchange as CCXTExchange } from 'ccxt';
import { BaseExchangeAdapter, ExchangeCredentials, PlaceOrderParams } from '../../exchanges/base';
import type { Exchange, Order, Position, TradeExecution } from '../../types';

export interface MockExchangeConfig {
  simulateLatency?: number;
  simulateErrors?: boolean;
  errorRate?: number;
  balances?: Record<string, number>;
  positions?: Position[];
  orders?: Order[];
}

export interface Balance extends Record<string, number> {}

export interface Ticker {
  symbol: string;
  price: number;
  bid: number;
  ask: number;
  timestamp: number;
}

/**
 * Mock exchange adapter for testing
 * Simulates real exchange behavior without making actual API calls
 */
export class MockExchangeAdapter extends BaseExchangeAdapter {
  private config: MockExchangeConfig;
  private mockBalances: Record<string, number>;
  private mockPositions: Position[];
  private mockOrders: Order[];
  private orderIdCounter = 1;

  constructor(credentials: ExchangeCredentials, config: MockExchangeConfig = {}) {
    super(credentials, 'binance' as Exchange);
    this.config = {
      simulateLatency: 100,
      simulateErrors: false,
      errorRate: 0.1,
      balances: { USDT: 10000, BTC: 0, ETH: 0 },
      positions: [],
      orders: [],
      ...config
    };

    this.mockBalances = { ...this.config.balances! };
    this.mockPositions = [...this.config.positions!];
    this.mockOrders = [...this.config.orders!];
  }

  protected createExchange(credentials: ExchangeCredentials): CCXTExchange {
    // Return a mock CCXT exchange object (not used in mock)
    return {} as CCXTExchange;
  }

  async ping(): Promise<boolean> {
    await this.simulateDelay();
    this.maybeThrowError('ping');
    return true;
  }

  async getBalance(): Promise<Record<string, number>> {
    await this.simulateDelay();
    this.maybeThrowError('getBalance');
    
    return { ...this.mockBalances };
  }

  async getTicker(symbol: string): Promise<{ price: number; timestamp: Date }> {
    await this.simulateDelay();
    this.maybeThrowError('getTicker');

    // Generate realistic mock prices
    const basePrices: Record<string, number> = {
      'BTCUSDT': 50000,
      'ETHUSDT': 3000,
      'ADAUSDT': 0.5,
      'SOLUSDT': 100,
      'DOTUSDT': 10
    };

    const basePrice = basePrices[symbol] || 100;
    const variation = (Math.random() - 0.5) * 0.02; // ±1% variation
    const price = basePrice * (1 + variation);

    return {
      price,
      timestamp: new Date()
    };
  }

  /**
   * Get full ticker data with bid/ask spread
   */
  async getFullTicker(symbol: string): Promise<Ticker> {
    const basicTicker = await this.getTicker(symbol);
    return {
      symbol,
      price: basicTicker.price,
      bid: basicTicker.price * 0.999,
      ask: basicTicker.price * 1.001,
      timestamp: basicTicker.timestamp.getTime()
    };
  }

  async getPositions(symbol?: string): Promise<Position[]> {
    await this.simulateDelay();
    this.maybeThrowError('getPositions');

    let positions = [...this.mockPositions];
    
    if (symbol) {
      positions = positions.filter(p => p.symbol === symbol);
    }

    return positions;
  }

  async getOpenOrders(symbol?: string): Promise<Order[]> {
    await this.simulateDelay();
    this.maybeThrowError('getOpenOrders');

    let orders = this.mockOrders.filter(o => o.status === 'open');
    
    if (symbol) {
      orders = orders.filter(o => o.symbol === symbol);
    }

    return orders;
  }

  async getTrades(symbol?: string, since?: number): Promise<TradeExecution[]> {
    await this.simulateDelay();
    this.maybeThrowError('getTrades');
    
    // Return empty array for mock implementation
    return [];
  }

  async placeOrder(params: PlaceOrderParams): Promise<Order> {
    await this.simulateDelay();
    this.maybeThrowError('placeOrder');

    const orderId = `mock_order_${this.orderIdCounter++}`;
    const ticker = await this.getTicker(params.symbol);
    const executionPrice = params.type === 'market' ? ticker.price : (params.price || ticker.price);

    // Simulate order execution
    const order: Order = {
      id: orderId,
      clientOrderId: params.clientOrderId || orderId,
      exchange: 'binance' as Exchange,
      symbol: params.symbol,
      side: params.side,
      type: params.type || 'market',
      amount: params.amount,
      price: params.price,
      filled: params.type === 'market' ? params.amount : 0,
      remaining: params.type === 'market' ? 0 : params.amount,
      status: params.type === 'market' ? 'closed' : 'open',
      timestamp: new Date()
    };

    // Update mock balances for market orders
    if (params.type === 'market') {
      await this.updateMockBalances(order, executionPrice);
    }

    // Update mock positions for market orders
    if (params.type === 'market' && !params.reduceOnly) {
      await this.updateMockPositions(order, executionPrice);
    }

    this.mockOrders.push(order);
    return order;
  }

  async cancelOrder(orderId: string): Promise<void> {
    await this.simulateDelay();
    this.maybeThrowError('cancelOrder');

    const orderIndex = this.mockOrders.findIndex(o => o.id === orderId);
    if (orderIndex === -1) {
      throw new Error(`Order ${orderId} not found`);
    }

    this.mockOrders[orderIndex].status = 'canceled';
  }

  async setLeverage(symbol: string, leverage: number): Promise<void> {
    await this.simulateDelay();
    this.maybeThrowError('setLeverage');

    // Update positions with new leverage
    this.mockPositions.forEach(position => {
      if (position.symbol === symbol) {
        position.leverage = leverage;
      }
    });
  }

  async getAvailableMargin(): Promise<number> {
    await this.simulateDelay();
    return this.mockBalances.USDT || 0;
  }

  normalizeSymbol(symbol: string): string {
    // Basic normalization
    return symbol.replace('/', '').toUpperCase();
  }

  /**
   * Validate balance for potential trade
   */
  async validateBalance(
    symbol: string,
    side: 'buy' | 'sell',
    amount: number,
    price: number,
    leverage: number = 1
  ): Promise<{ isValid: boolean; reason?: string; requiredMargin?: number; availableMargin?: number }> {
    const quoteAsset = symbol.replace(/[^A-Z]/g, '').slice(-4); // Extract quote asset (e.g., USDT)
    const availableBalance = this.mockBalances[quoteAsset] || 0;
    const requiredMargin = (amount * price) / leverage;

    if (side === 'buy' && requiredMargin > availableBalance) {
      return {
        isValid: false,
        reason: `Insufficient ${quoteAsset} balance. Required: ${requiredMargin.toFixed(2)}, Available: ${availableBalance.toFixed(2)}`,
        requiredMargin,
        availableMargin: availableBalance
      };
    }

    return {
      isValid: true,
      requiredMargin,
      availableMargin: availableBalance
    };
  }

  /**
   * Add mock position for testing
   */
  addMockPosition(position: Partial<Position>): void {
    const mockPosition: Position = {
      id: `mock_pos_${Date.now()}`,
      symbol: 'BTCUSDT',
      exchange: 'binance' as Exchange,
      side: 'long',
      size: 0,
      entryPrice: 50000,
      markPrice: 50000,
      unrealizedPnl: 0,
      realizedPnl: 0,
      leverage: 1,
      timestamp: new Date(),
      ...position
    };
    
    this.mockPositions.push(mockPosition);
  }

  /**
   * Set mock balance for testing
   */
  setMockBalance(asset: string, amount: number): void {
    this.mockBalances[asset] = amount;
  }

  /**
   * Get current mock state for assertions
   */
  getMockState(): {
    balances: Record<string, number>;
    positions: Position[];
    orders: Order[];
  } {
    return {
      balances: { ...this.mockBalances },
      positions: [...this.mockPositions],
      orders: [...this.mockOrders]
    };
  }

  /**
   * Reset mock state
   */
  resetMockState(): void {
    this.mockBalances = { ...this.config.balances! };
    this.mockPositions = [...this.config.positions!];
    this.mockOrders = [...this.config.orders!];
    this.orderIdCounter = 1;
  }

  /**
   * Simulate network delay
   */
  private async simulateDelay(): Promise<void> {
    if (this.config.simulateLatency! > 0) {
      await new Promise(resolve => setTimeout(resolve, this.config.simulateLatency));
    }
  }

  /**
   * Maybe throw error based on configuration
   */
  private maybeThrowError(operation: string): void {
    if (this.config.simulateErrors && Math.random() < this.config.errorRate!) {
      throw new Error(`Mock error in ${operation}`);
    }
  }

  /**
   * Update mock balances after order execution
   */
  private async updateMockBalances(order: Order, executionPrice: number): Promise<void> {
    const baseAsset = order.symbol.replace('USDT', '').replace('BUSD', '');
    const quoteAsset = order.symbol.includes('USDT') ? 'USDT' : 'BUSD';

    if (order.side === 'buy') {
      // Buying base asset with quote asset
      const cost = order.filled * executionPrice;
      this.mockBalances[quoteAsset] = (this.mockBalances[quoteAsset] || 0) - cost;
      this.mockBalances[baseAsset] = (this.mockBalances[baseAsset] || 0) + order.filled;
    } else {
      // Selling base asset for quote asset
      const revenue = order.filled * executionPrice;
      this.mockBalances[baseAsset] = (this.mockBalances[baseAsset] || 0) - order.filled;
      this.mockBalances[quoteAsset] = (this.mockBalances[quoteAsset] || 0) + revenue;
    }
  }

  /**
   * Update mock positions after order execution
   */
  private async updateMockPositions(order: Order, executionPrice: number): Promise<void> {
    let position = this.mockPositions.find(p => p.symbol === order.symbol);

    if (!position) {
      // Create new position
      position = {
        id: `mock_pos_${Date.now()}`,
        symbol: order.symbol,
        exchange: 'binance' as Exchange,
        side: order.side === 'buy' ? 'long' : 'short',
        size: order.filled,
        entryPrice: executionPrice,
        markPrice: executionPrice,
        unrealizedPnl: 0,
        realizedPnl: 0,
        leverage: 1,
        timestamp: new Date()
      };
      this.mockPositions.push(position);
    } else {
      // Update existing position
      const newSize = order.side === 'buy' ? 
        position.size + order.filled : 
        position.size - order.filled;
      
      if (newSize === 0) {
        // Close position
        const positionIndex = this.mockPositions.indexOf(position);
        this.mockPositions.splice(positionIndex, 1);
      } else {
        // Update position
        const oldNotional = position.size * position.entryPrice;
        const newNotional = order.filled * executionPrice;
        const totalNotional = oldNotional + newNotional;
        
        position.size = newSize;
        position.entryPrice = totalNotional / newSize;
        position.markPrice = executionPrice;
      }
    }
  }
}