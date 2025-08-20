/**
 * Global test setup for integration tests
 * Configures mocks, timeouts, and test environment
 */

// Extend Jest timeout for integration tests
jest.setTimeout(30000);

// Mock environment variables
process.env.NODE_ENV = 'test';
process.env.DATABASE_URL = 'postgresql://test:test@localhost:5432/test_tradingview_gateway';
process.env.REDIS_URL = 'redis://localhost:6379';
process.env.WEBHOOK_SECRET = 'test_webhook_secret_key';

// Global test helpers
(global as any).testHelpers = {
  /**
   * Wait for a specified amount of time
   */
  delay: (ms: number) => new Promise(resolve => setTimeout(resolve, ms)),
  
  /**
   * Generate random test data
   */
  randomString: (length: number = 10) => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  },
  
  /**
   * Generate random number between min and max
   */
  randomNumber: (min: number, max: number) => {
    return Math.random() * (max - min) + min;
  },
  
  /**
   * Generate random price within realistic range
   */
  randomPrice: (symbol: string) => {
    const basePrices: Record<string, [number, number]> = {
      'BTCUSDT': [40000, 60000],
      'ETHUSDT': [2000, 4000],
      'ADAUSDT': [0.3, 0.8],
      'SOLUSDT': [80, 150],
      'DOTUSDT': [8, 15]
    };
    
    const [min, max] = basePrices[symbol] || [50, 150];
    return (global as any).testHelpers.randomNumber(min, max);
  },
  
  /**
   * Create realistic test order data
   */
  createTestOrder: (overrides: any = {}) => {
    return {
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.001,
      type: 'market',
      timestamp: Date.now(),
      ...overrides
    };
  },
  
  /**
   * Create test webhook payload
   */
  createTestWebhook: (overrides: any = {}) => {
    return {
      timestamp: Date.now(),
      exchange: 'binance',
      strategy: 'test_strategy',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      order_type: 'market',
      leverage: 1,
      client_id: `test_${Date.now()}`,
      ...overrides
    };
  }
};

// Console log filtering for cleaner test output
const originalConsoleLog = console.log;
const originalConsoleWarn = console.warn;
const originalConsoleError = console.error;

console.log = (...args: any[]) => {
  // Filter out noisy logs during tests
  const message = args.join(' ');
  if (
    message.includes('API not available, using mock data') ||
    message.includes('Mock error in') ||
    message.includes('Simulating network delay')
  ) {
    return;
  }
  originalConsoleLog.apply(console, args);
};

console.warn = (...args: any[]) => {
  // Filter out expected warnings during tests
  const message = args.join(' ');
  if (message.includes('Using mock data for testing')) {
    return;
  }
  originalConsoleWarn.apply(console, args);
};

console.error = (...args: any[]) => {
  // Don't filter error logs as they're usually important
  originalConsoleError.apply(console, args);
};

// Global error handler for unhandled promises
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // Don't exit in tests, just log
});

// Mock fetch for tests that need HTTP calls
(global as any).fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    status: 200,
    statusText: 'OK'
  } as Response)
);

// Declare global types for TypeScript
declare global {
  var testHelpers: {
    delay: (ms: number) => Promise<void>;
    randomString: (length?: number) => string;
    randomNumber: (min: number, max: number) => number;
    randomPrice: (symbol: string) => number;
    createTestOrder: (overrides?: any) => any;
    createTestWebhook: (overrides?: any) => any;
  };
  
  var fetch: jest.MockedFunction<typeof fetch>;
}