import { MockExchangeAdapter } from '../mocks/exchange-mock';

describe('Basic Mock Exchange Tests', () => {
  let mockExchange: MockExchangeAdapter;
  
  beforeEach(() => {
    mockExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test' },
      {
        simulateLatency: 10,
        simulateErrors: false,
        balances: { USDT: 10000, BTC: 1 }
      }
    );
  });

  test('should create mock exchange successfully', () => {
    expect(mockExchange).toBeDefined();
  });

  test('should ping successfully', async () => {
    const result = await mockExchange.ping();
    expect(result).toBe(true);
  });

  test('should get balance', async () => {
    const balance = await mockExchange.getBalance();
    expect(balance.USDT).toBe(10000);
    expect(balance.BTC).toBe(1);
  });

  test('should get ticker', async () => {
    const ticker = await mockExchange.getTicker('BTCUSDT');
    expect(ticker).toHaveProperty('price');
    expect(ticker).toHaveProperty('timestamp');
    expect(ticker.price).toBeGreaterThan(0);
  });

  test('should place market order', async () => {
    const order = await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.001,
      type: 'market'
    });

    expect(order).toMatchObject({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.001,
      type: 'market',
      status: 'closed'
    });
  });
});