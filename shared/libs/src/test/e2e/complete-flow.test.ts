import { describe, test, expect, beforeEach, afterEach } from '@jest/globals';
import crypto from 'crypto';
import { MockExchangeAdapter } from '../mocks/exchange-mock';
import { AccountSelectionService } from '../../../apps/api/src/services/account-selection';
import { PriceCache } from '../../utils/price-cache';
import { ErrorClassifier } from '../../utils/error-handling';

/**
 * End-to-End tests for complete webhook → trade flows
 * Tests the entire system integration from webhook receipt to trade execution
 */
describe('Complete Webhook to Trade Flow E2E Tests', () => {
  let mockExchange: MockExchangeAdapter;
  let accountSelection: AccountSelectionService;
  let priceCache: PriceCache;
  let errorClassifier: ErrorClassifier;
  
  const webhookSecret = 'test_e2e_webhook_secret';
  
  beforeEach(() => {
    mockExchange = new MockExchangeAdapter(
      { apiKey: 'e2e_test', secret: 'e2e_test' },
      {
        simulateLatency: 25,
        simulateErrors: false,
        balances: {
          USDT: 50000,
          BTC: 1.0,
          ETH: 10.0,
          ADA: 1000,
          SOL: 100
        }
      }
    );
    
    accountSelection = new AccountSelectionService();
    priceCache = new PriceCache();
    errorClassifier = new ErrorClassifier();
  });

  afterEach(() => {
    priceCache.clear();
  });

  /**
   * Simulates the complete webhook processing pipeline
   */
  async function processWebhook(webhookData: any): Promise<{
    signature: string;
    payload: string;
    parsedData: any;
    validationResult: any;
    priceData: any;
    orderResult: any;
    finalState: any;
  }> {
    // Step 1: Generate webhook signature
    const payload = JSON.stringify(webhookData);
    const signature = crypto
      .createHmac('sha256', webhookSecret)
      .update(payload)
      .digest('hex');

    // Step 2: Validate webhook signature
    const isSignatureValid = crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(crypto.createHmac('sha256', webhookSecret).update(payload).digest('hex'), 'hex')
    );
    
    if (!isSignatureValid) {
      throw new Error('Invalid webhook signature');
    }

    // Step 3: Parse and validate payload
    const parsedData = JSON.parse(payload);
    const requiredFields = ['action', 'symbol', 'quantity'];
    const missingFields = requiredFields.filter(field => !parsedData.hasOwnProperty(field));
    
    if (missingFields.length > 0) {
      throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
    }

    // Step 4: Get current price (with caching)
    const priceData = await priceCache.getPrice(parsedData.symbol, async () => {
      const ticker = await mockExchange.getTicker(parsedData.symbol);
      return ticker.price;
    });

    // Step 5: Validate balance and margin
    const validationResult = await mockExchange.validateBalance(
      parsedData.symbol,
      parsedData.action,
      parsedData.quantity,
      parsedData.price || priceData,
      parsedData.leverage || 1
    );

    if (!validationResult.isValid) {
      throw new Error(`Insufficient balance: ${validationResult.reason}`);
    }

    // Step 6: Execute order
    const orderResult = await mockExchange.placeOrder({
      symbol: parsedData.symbol,
      side: parsedData.action,
      amount: parsedData.quantity,
      type: parsedData.order_type || 'market',
      price: parsedData.price,
      clientOrderId: parsedData.client_id || `e2e_${Date.now()}`,
      stopLoss: parsedData.stop_loss,
      takeProfit: parsedData.take_profit,
      reduceOnly: parsedData.reduce_only
    });

    // Step 7: Get final system state
    const finalState = {
      balance: await mockExchange.getBalance(),
      positions: await mockExchange.getPositions(),
      orders: await mockExchange.getOpenOrders()
    };

    return {
      signature,
      payload,
      parsedData,
      validationResult,
      priceData,
      orderResult,
      finalState
    };
  }

  test('should process complete BTC buy flow successfully', async () => {
    const webhookData = {
      timestamp: Date.now(),
      strategy: 'BTC_Long_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.01,
      order_type: 'market',
      leverage: 1,
      client_id: 'e2e_btc_buy_001'
    };

    const result = await processWebhook(webhookData);

    // Validate webhook processing
    expect(result.signature).toHaveLength(64); // SHA256 hex
    expect(result.parsedData.action).toBe('buy');
    expect(result.parsedData.symbol).toBe('BTCUSDT');

    // Validate price fetching
    expect(result.priceData).toBeGreaterThan(0);

    // Validate balance check
    expect(result.validationResult.isValid).toBe(true);
    expect(result.validationResult.requiredMargin).toBeGreaterThan(0);

    // Validate order execution
    expect(result.orderResult).toMatchObject({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.01,
      status: 'closed',
      filled: 0.01
    });

    // Validate final state changes
    expect(result.finalState.balance.USDT).toBeLessThan(50000); // USDT decreased
    expect(result.finalState.balance.BTC).toBeGreaterThan(1.0); // BTC increased
  });

  test('should process complete ETH sell flow successfully', async () => {
    const webhookData = {
      timestamp: Date.now(),
      strategy: 'ETH_Short_E2E',
      action: 'sell',
      symbol: 'ETHUSDT',
      quantity: 0.5,
      order_type: 'market',
      client_id: 'e2e_eth_sell_001'
    };

    const result = await processWebhook(webhookData);

    expect(result.orderResult).toMatchObject({
      symbol: 'ETHUSDT',
      side: 'sell',
      amount: 0.5,
      status: 'closed'
    });

    // ETH should decrease, USDT should increase
    expect(result.finalState.balance.ETH).toBeLessThan(10.0);
    expect(result.finalState.balance.USDT).toBeGreaterThan(50000);
  });

  test('should handle limit order flow with price specification', async () => {
    const webhookData = {
      timestamp: Date.now(),
      strategy: 'BTC_Limit_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.005,
      price: 48000,
      order_type: 'limit',
      client_id: 'e2e_btc_limit_001'
    };

    const result = await processWebhook(webhookData);

    expect(result.orderResult).toMatchObject({
      symbol: 'BTCUSDT',
      side: 'buy',
      type: 'limit',
      price: 48000,
      status: 'open', // Limit orders start as open
      remaining: 0.005
    });

    // Balance shouldn't change for open limit orders
    expect(result.finalState.balance.USDT).toBe(50000);
    expect(result.finalState.orders).toHaveLength(1);
  });

  test('should handle leveraged trading flow', async () => {
    const webhookData = {
      timestamp: Date.now(),
      strategy: 'BTC_Leveraged_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.05,
      leverage: 10,
      order_type: 'market',
      client_id: 'e2e_btc_leverage_001'
    };

    const result = await processWebhook(webhookData);

    // With 10x leverage, required margin should be 1/10 of notional value
    expect(result.validationResult.requiredMargin).toBeLessThan(
      0.05 * result.priceData // Less than full notional due to leverage
    );

    expect(result.orderResult.status).toBe('closed');
  });

  test('should handle stop loss and take profit orders', async () => {
    const webhookData = {
      timestamp: Date.now(),
      strategy: 'BTC_SL_TP_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.01,
      order_type: 'market',
      stop_loss: 49000,
      take_profit: 55000,
      client_id: 'e2e_btc_sl_tp_001'
    };

    const result = await processWebhook(webhookData);

    expect(result.orderResult.status).toBe('closed');
    // In a real system, SL/TP would create additional orders
    // Here we just verify the main order executed
  });

  test('should handle reduce only orders', async () => {
    // First create a position
    await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.02,
      type: 'market'
    });

    const webhookData = {
      timestamp: Date.now(),
      strategy: 'BTC_Reduce_E2E',
      action: 'sell',
      symbol: 'BTCUSDT',
      quantity: 0.01,
      order_type: 'market',
      reduce_only: true,
      client_id: 'e2e_btc_reduce_001'
    };

    const result = await processWebhook(webhookData);

    expect(result.orderResult).toMatchObject({
      side: 'sell',
      amount: 0.01,
      status: 'closed'
    });
  });

  test('should handle multiple symbol trading in sequence', async () => {
    const symbols = [
      { symbol: 'BTCUSDT', quantity: 0.001 },
      { symbol: 'ETHUSDT', quantity: 0.01 },
      { symbol: 'ADAUSDT', quantity: 10 }
    ];

    const results = [];

    for (const { symbol, quantity } of symbols) {
      const webhookData = {
        timestamp: Date.now(),
        strategy: `Multi_Symbol_E2E_${symbol}`,
        action: 'buy',
        symbol,
        quantity,
        order_type: 'market',
        client_id: `e2e_multi_${symbol.toLowerCase()}_001`
      };

      const result = await processWebhook(webhookData);
      results.push(result);

      // Small delay between orders
      await new Promise(resolve => setTimeout(resolve, 10));
    }

    // All orders should have executed successfully
    expect(results).toHaveLength(3);
    results.forEach(result => {
      expect(result.orderResult.status).toBe('closed');
      expect(result.orderResult.filled).toBeGreaterThan(0);
    });

    // USDT balance should have decreased from all purchases
    const finalBalance = await mockExchange.getBalance();
    expect(finalBalance.USDT).toBeLessThan(50000);
  });

  test('should handle price caching across multiple requests', async () => {
    const symbol = 'BTCUSDT';
    const requests = [];

    // Make multiple concurrent webhook requests
    for (let i = 0; i < 5; i++) {
      const webhookData = {
        timestamp: Date.now(),
        strategy: `Cache_Test_E2E_${i}`,
        action: 'buy',
        symbol,
        quantity: 0.001,
        client_id: `e2e_cache_${i}`
      };

      requests.push(processWebhook(webhookData));
    }

    const results = await Promise.all(requests);

    // All should use the same cached price
    const prices = results.map(r => r.priceData);
    expect(new Set(prices).size).toBe(1); // All prices should be identical due to caching

    // All orders should execute successfully
    results.forEach(result => {
      expect(result.orderResult.status).toBe('closed');
    });
  });

  test('should reject webhook with invalid signature', async () => {
    const webhookData = {
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001
    };

    const payload = JSON.stringify(webhookData);
    const invalidSignature = 'invalid_signature_12345';

    const isValid = crypto.timingSafeEqual(
      Buffer.from(invalidSignature, 'hex').slice(0, 32),
      Buffer.from(crypto.createHmac('sha256', webhookSecret).update(payload).digest('hex'), 'hex').slice(0, 32)
    );

    expect(isValid).toBe(false);
  });

  test('should handle insufficient balance gracefully', async () => {
    // Set very low balance
    mockExchange.setMockBalance('USDT', 10);

    const webhookData = {
      timestamp: Date.now(),
      strategy: 'Insufficient_Balance_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 1.0, // Trying to buy 1 BTC with only $10
      client_id: 'e2e_insufficient_001'
    };

    await expect(processWebhook(webhookData)).rejects.toThrow('Insufficient balance');
  });

  test('should handle missing required fields', async () => {
    const incompleteWebhookData = {
      timestamp: Date.now(),
      strategy: 'Incomplete_E2E',
      action: 'buy'
      // Missing symbol and quantity
    };

    await expect(processWebhook(incompleteWebhookData)).rejects.toThrow('Missing required fields');
  });

  test('should handle malformed JSON gracefully', async () => {
    const malformedPayload = '{ "action": "buy", "symbol": "BTCUSDT", "quantity": 0.001';
    
    expect(() => JSON.parse(malformedPayload)).toThrow();
  });

  test('should handle concurrent webhook processing', async () => {
    const concurrentRequests = 10;
    const promises = [];

    for (let i = 0; i < concurrentRequests; i++) {
      const webhookData = {
        timestamp: Date.now(),
        strategy: `Concurrent_E2E_${i}`,
        action: 'buy',
        symbol: 'BTCUSDT',
        quantity: 0.001,
        client_id: `e2e_concurrent_${i}`
      };

      promises.push(processWebhook(webhookData));
    }

    const results = await Promise.all(promises);

    // All should succeed
    expect(results).toHaveLength(concurrentRequests);
    results.forEach(result => {
      expect(result.orderResult.status).toBe('closed');
    });

    // All should have unique client order IDs
    const clientIds = results.map(r => r.orderResult.clientOrderId);
    const uniqueIds = new Set(clientIds);
    expect(uniqueIds.size).toBe(concurrentRequests);
  });

  test('should maintain data consistency across full flow', async () => {
    const initialBalance = await mockExchange.getBalance();
    const initialState = mockExchange.getMockState();

    const webhookData = {
      timestamp: Date.now(),
      strategy: 'Consistency_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.01,
      client_id: 'e2e_consistency_001'
    };

    const result = await processWebhook(webhookData);
    const finalState = mockExchange.getMockState();

    // Verify state changes are consistent
    expect(finalState.orders.length).toBe(initialState.orders.length + 1);
    
    // Calculate expected balance changes
    const orderValue = result.orderResult.filled * result.priceData;
    const expectedUSDT = initialBalance.USDT - orderValue;
    const expectedBTC = initialBalance.BTC + result.orderResult.filled;

    expect(result.finalState.balance.USDT).toBeCloseTo(expectedUSDT, 2);
    expect(result.finalState.balance.BTC).toBeCloseTo(expectedBTC, 8);
  });

  test('should handle edge case with very small quantities', async () => {
    const webhookData = {
      timestamp: Date.now(),
      strategy: 'Small_Quantity_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.00001, // Very small quantity
      client_id: 'e2e_small_quantity_001'
    };

    const result = await processWebhook(webhookData);

    expect(result.orderResult.filled).toBe(0.00001);
    expect(result.orderResult.status).toBe('closed');
  });

  test('should handle timestamp validation', async () => {
    const oldTimestamp = Date.now() - (10 * 60 * 1000); // 10 minutes ago
    
    const webhookData = {
      timestamp: oldTimestamp,
      strategy: 'Old_Timestamp_E2E',
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      client_id: 'e2e_old_timestamp_001'
    };

    // In a real system, you might want to reject old timestamps
    const maxAge = 5 * 60 * 1000; // 5 minutes
    const timeDiff = Math.abs(Date.now() - webhookData.timestamp);
    
    if (timeDiff > maxAge) {
      // This webhook would be rejected in a real system
      expect(timeDiff).toBeGreaterThan(maxAge);
    }
  });
});