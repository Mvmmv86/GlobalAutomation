import { MockExchangeAdapter } from '../mocks/exchange-mock';

/**
 * Integration tests for complete webhook-to-trade flow
 * Tests the entire flow from webhook receipt to trade execution
 */
describe('Webhook to Trade Flow Integration Tests', () => {
  let mockExchange: MockExchangeAdapter;
  
  beforeEach(() => {
    // Reset mock exchange with test data
    mockExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test', testnet: true },
      {
        simulateLatency: 10,
        simulateErrors: false,
        balances: {
          USDT: 10000,
          BTC: 0.5,
          ETH: 2.0
        },
        positions: [],
        orders: []
      }
    );
  });

  test('should handle complete buy order flow', async () => {
    // Simulate TradingView webhook payload
    const webhookPayload = {
      strategy: 'BTC_Long_Strategy',
      action: 'buy' as 'buy' | 'sell',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      price: 50000,
      timestamp: Date.now()
    };

    // 1. Validate balance before trade
    const balanceValidation = await mockExchange.validateBalance(
      webhookPayload.symbol,
      webhookPayload.action,
      webhookPayload.quantity,
      webhookPayload.price,
      1
    );

    expect(balanceValidation.isValid).toBe(true);
    expect(balanceValidation.requiredMargin).toBeGreaterThan(0);

    // 2. Get current price
    const ticker = await mockExchange.getTicker(webhookPayload.symbol);
    expect(ticker).toHaveProperty('price');
    expect(ticker.price).toBeGreaterThan(0);

    // 3. Place market order
    const order = await mockExchange.placeOrder({
      symbol: webhookPayload.symbol,
      side: webhookPayload.action,
      amount: webhookPayload.quantity,
      type: 'market'
    });

    expect(order).toMatchObject({
      symbol: 'BTCUSDT',
      side: 'buy',
      type: 'market',
      amount: 0.001,
      status: 'closed',
      filled: 0.001
    });

    // 4. Verify balance was updated
    const updatedBalance = await mockExchange.getBalance();
    expect(updatedBalance.USDT).toBeLessThan(10000); // USDT decreased
    expect(updatedBalance.BTC).toBeGreaterThan(0.5); // BTC increased
  });

  test('should handle complete sell order flow', async () => {
    // First, ensure we have BTC position
    await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.002,
      type: 'market'
    });

    const webhookPayload = {
      strategy: 'BTC_Short_Strategy',
      action: 'sell' as 'buy' | 'sell',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      timestamp: Date.now()
    };

    // 1. Get initial balance
    const initialBalance = await mockExchange.getBalance();
    const initialBTC = initialBalance.BTC;
    const initialUSDT = initialBalance.USDT;

    // 2. Place sell order
    const order = await mockExchange.placeOrder({
      symbol: webhookPayload.symbol,
      side: webhookPayload.action,
      amount: webhookPayload.quantity,
      type: 'market'
    });

    expect(order.status).toBe('closed');
    expect(order.side).toBe('sell');

    // 3. Verify balance changes
    const finalBalance = await mockExchange.getBalance();
    expect(finalBalance.BTC).toBeLessThan(initialBTC);
    expect(finalBalance.USDT).toBeGreaterThan(initialUSDT);
  });

  test('should reject orders with insufficient balance', async () => {
    const webhookPayload = {
      strategy: 'Large_BTC_Buy',
      action: 'buy' as 'buy' | 'sell',
      symbol: 'BTCUSDT',
      quantity: 1.0, // Too large for 10k USDT balance
      price: 50000,
      timestamp: Date.now()
    };

    // Validate balance should fail
    const validation = await mockExchange.validateBalance(
      webhookPayload.symbol,
      webhookPayload.action,
      webhookPayload.quantity,
      webhookPayload.price,
      1
    );

    expect(validation.isValid).toBe(false);
    expect(validation.reason).toContain('Insufficient');
    expect(validation.requiredMargin).toBe(50000);
    expect(validation.availableMargin).toBe(10000);
  });

  test('should handle limit orders correctly', async () => {
    const webhookPayload = {
      strategy: 'BTC_Limit_Strategy',
      action: 'buy' as 'buy' | 'sell',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      price: 49000, // Limit price below current market
      timestamp: Date.now()
    };

    const order = await mockExchange.placeOrder({
      symbol: webhookPayload.symbol,
      side: webhookPayload.action,
      amount: webhookPayload.quantity,
      type: 'limit',
      price: webhookPayload.price
    });

    expect(order).toMatchObject({
      symbol: 'BTCUSDT',
      side: 'buy',
      type: 'limit',
      amount: 0.001,
      price: 49000,
      status: 'open',
      filled: 0,
      remaining: 0.001
    });

    // Verify it appears in open orders
    const openOrders = await mockExchange.getOpenOrders('BTCUSDT');
    expect(openOrders).toHaveLength(1);
    expect(openOrders[0].id).toBe(order.id);
  });

  test('should handle order cancellation', async () => {
    // Place limit order
    const order = await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.001,
      type: 'limit',
      price: 48000
    });

    // Verify order is open
    let openOrders = await mockExchange.getOpenOrders();
    expect(openOrders).toHaveLength(1);

    // Cancel order
    await mockExchange.cancelOrder(order.id);

    // Verify order is no longer open
    openOrders = await mockExchange.getOpenOrders();
    expect(openOrders).toHaveLength(0);
  });

  test('should handle position tracking for futures', async () => {
    // Place buy order to open long position
    const buyOrder = await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.01,
      type: 'market'
    });

    const positions = await mockExchange.getPositions('BTCUSDT');
    expect(positions).toHaveLength(1);
    expect(positions[0]).toMatchObject({
      symbol: 'BTCUSDT',
      side: 'long',
      size: 0.01
    });

    // Place sell order to reduce position
    await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'sell',
      amount: 0.005,
      type: 'market'
    });

    const updatedPositions = await mockExchange.getPositions('BTCUSDT');
    expect(updatedPositions[0].size).toBe(0.005);
  });

  test('should handle leverage settings', async () => {
    const symbol = 'BTCUSDT';
    const leverage = 10;

    await mockExchange.setLeverage(symbol, leverage);

    // Add position to test leverage
    mockExchange.addMockPosition({
      symbol,
      side: 'long',
      size: 0.1,
      leverage
    });

    const positions = await mockExchange.getPositions(symbol);
    expect(positions[0].leverage).toBe(leverage);
  });

  test('should handle multiple symbol trading', async () => {
    const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'];
    const orders = [];

    // Place orders for multiple symbols
    for (const symbol of symbols) {
      const order = await mockExchange.placeOrder({
        symbol,
        side: 'buy',
        amount: symbol === 'BTCUSDT' ? 0.001 : 0.01,
        type: 'market'
      });
      orders.push(order);
    }

    expect(orders).toHaveLength(3);
    orders.forEach(order => {
      expect(order.status).toBe('closed');
      expect(order.filled).toBeGreaterThan(0);
    });

    // Check that prices are realistic for each symbol
    for (const symbol of symbols) {
      const ticker = await mockExchange.getTicker(symbol);
      expect(ticker.price).toBeGreaterThan(0);
    }
  });
});