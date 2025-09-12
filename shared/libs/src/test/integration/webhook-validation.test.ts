import { describe, test, expect, beforeEach } from '@jest/globals';
import crypto from 'crypto';
import { MockExchangeAdapter } from '../mocks/exchange-mock';

/**
 * Integration tests for TradingView webhook validation and processing
 * Tests webhook signature validation, payload parsing, and execution flow
 */
describe('TradingView Webhook Integration Tests', () => {
  let mockExchange: MockExchangeAdapter;
  const webhookSecret = 'test_webhook_secret_key';
  
  beforeEach(() => {
    mockExchange = new MockExchangeAdapter(
      { apiKey: 'test', secret: 'test' },
      {
        simulateLatency: 50,
        balances: { USDT: 10000, BTC: 0.5, ETH: 2.0 }
      }
    );
  });

  const generateHMACSignature = (payload: string, secret: string): string => {
    return crypto
      .createHmac('sha256', secret)
      .update(payload)
      .digest('hex');
  };

  const createWebhookPayload = (data: any) => {
    return {
      timestamp: Date.now(),
      exchange: 'binance',
      strategy: data.strategy || 'test_strategy',
      action: data.action,
      symbol: data.symbol,
      quantity: data.quantity,
      price: data.price,
      order_type: data.order_type || 'market',
      leverage: data.leverage || 1,
      reduce_only: data.reduce_only || false,
      stop_loss: data.stop_loss,
      take_profit: data.take_profit,
      client_id: data.client_id || `tv_${Date.now()}`,
      ...data
    };
  };

  const validateWebhookSignature = (payload: string, signature: string, secret: string): boolean => {
    const expectedSignature = generateHMACSignature(payload, secret);
    return crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(expectedSignature, 'hex')
    );
  };

  test('should validate correct webhook signature', () => {
    const payload = JSON.stringify({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001
    });
    
    const signature = generateHMACSignature(payload, webhookSecret);
    const isValid = validateWebhookSignature(payload, signature, webhookSecret);
    
    expect(isValid).toBe(true);
  });

  test('should reject invalid webhook signature', () => {
    const payload = JSON.stringify({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001
    });
    
    // Create a completely different signature with correct length
    const invalidSignature = generateHMACSignature(payload + '_invalid', webhookSecret);
    
    const isValid = validateWebhookSignature(payload, invalidSignature, webhookSecret);
    
    expect(isValid).toBe(false);
  });

  test('should process valid buy webhook', async () => {
    const webhookData = createWebhookPayload({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      strategy: 'BTC_Long_Strategy'
    });

    const payload = JSON.stringify(webhookData);
    const signature = generateHMACSignature(payload, webhookSecret);
    
    // Validate signature
    const isSignatureValid = validateWebhookSignature(payload, signature, webhookSecret);
    expect(isSignatureValid).toBe(true);

    // Process webhook
    const parsedData = JSON.parse(payload);
    
    // Validate required fields
    expect(parsedData).toHaveProperty('action');
    expect(parsedData).toHaveProperty('symbol');
    expect(parsedData).toHaveProperty('quantity');
    expect(parsedData.action).toBe('buy');

    // Validate balance before trade
    const balanceValidation = await mockExchange.validateBalance(
      parsedData.symbol,
      parsedData.action,
      parsedData.quantity,
      parsedData.price || 50000,
      parsedData.leverage
    );
    
    expect(balanceValidation.isValid).toBe(true);

    // Execute trade
    const order = await mockExchange.placeOrder({
      symbol: parsedData.symbol,
      side: parsedData.action,
      amount: parsedData.quantity,
      type: parsedData.order_type,
      clientOrderId: parsedData.client_id
    });

    expect(order).toMatchObject({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.001,
      status: 'closed'
    });
  });

  test('should process valid sell webhook', async () => {
    // First ensure we have BTC position
    await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.002,
      type: 'market'
    });

    const webhookData = createWebhookPayload({
      action: 'sell',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      strategy: 'BTC_Short_Strategy'
    });

    const payload = JSON.stringify(webhookData);
    const signature = generateHMACSignature(payload, webhookSecret);
    
    // Validate and process
    const isValid = validateWebhookSignature(payload, signature, webhookSecret);
    expect(isValid).toBe(true);

    const parsedData = JSON.parse(payload);
    const order = await mockExchange.placeOrder({
      symbol: parsedData.symbol,
      side: parsedData.action,
      amount: parsedData.quantity,
      type: parsedData.order_type,
      clientOrderId: parsedData.client_id
    });

    expect(order.side).toBe('sell');
    expect(order.status).toBe('closed');
  });

  test('should handle limit order webhooks', async () => {
    const webhookData = createWebhookPayload({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      price: 48000,
      order_type: 'limit',
      strategy: 'BTC_Limit_Buy'
    });

    const payload = JSON.stringify(webhookData);
    const signature = generateHMACSignature(payload, webhookSecret);
    
    const isValid = validateWebhookSignature(payload, signature, webhookSecret);
    expect(isValid).toBe(true);

    const parsedData = JSON.parse(payload);
    const order = await mockExchange.placeOrder({
      symbol: parsedData.symbol,
      side: parsedData.action,
      amount: parsedData.quantity,
      type: parsedData.order_type,
      price: parsedData.price,
      clientOrderId: parsedData.client_id
    });

    expect(order).toMatchObject({
      type: 'limit',
      price: 48000,
      status: 'open',
      remaining: 0.001
    });
  });

  test('should handle webhooks with stop loss and take profit', async () => {
    const webhookData = createWebhookPayload({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      order_type: 'market',
      stop_loss: 49000,
      take_profit: 52000,
      strategy: 'BTC_SL_TP_Strategy'
    });

    const payload = JSON.stringify(webhookData);
    const signature = generateHMACSignature(payload, webhookSecret);
    
    const isValid = validateWebhookSignature(payload, signature, webhookSecret);
    expect(isValid).toBe(true);

    const parsedData = JSON.parse(payload);
    const order = await mockExchange.placeOrder({
      symbol: parsedData.symbol,
      side: parsedData.action,
      amount: parsedData.quantity,
      type: parsedData.order_type,
      stopLoss: parsedData.stop_loss,
      takeProfit: parsedData.take_profit,
      clientOrderId: parsedData.client_id
    });

    expect(order.status).toBe('closed');
    // In a real implementation, SL/TP would create additional orders
  });

  test('should handle leverage webhooks', async () => {
    const webhookData = createWebhookPayload({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.01,
      leverage: 10,
      strategy: 'BTC_Leveraged_Long'
    });

    const payload = JSON.stringify(webhookData);
    const signature = generateHMACSignature(payload, webhookSecret);
    
    const isValid = validateWebhookSignature(payload, signature, webhookSecret);
    expect(isValid).toBe(true);

    const parsedData = JSON.parse(payload);
    
    // Set leverage
    await mockExchange.setLeverage(parsedData.symbol, parsedData.leverage);
    
    // Validate balance with leverage
    const balanceValidation = await mockExchange.validateBalance(
      parsedData.symbol,
      parsedData.action,
      parsedData.quantity,
      50000,
      parsedData.leverage
    );
    
    expect(balanceValidation.isValid).toBe(true);
    expect(balanceValidation.requiredMargin).toBe(50); // 0.01 * 50000 / 10 leverage
  });

  test('should validate required webhook fields', () => {
    const incompleteWebhook = {
      action: 'buy',
      // Missing symbol and quantity
      strategy: 'test'
    };

    const payload = JSON.stringify(incompleteWebhook);
    const parsedData = JSON.parse(payload);
    
    const requiredFields = ['action', 'symbol', 'quantity'];
    const missingFields = requiredFields.filter(field => !parsedData.hasOwnProperty(field));
    
    expect(missingFields).toContain('symbol');
    expect(missingFields).toContain('quantity');
    expect(missingFields).not.toContain('action');
  });

  test('should handle malformed JSON webhook', () => {
    const malformedPayload = '{ "action": "buy", "symbol": "BTCUSDT", "quantity": 0.001';
    
    expect(() => {
      JSON.parse(malformedPayload);
    }).toThrow();
  });

  test('should validate webhook timestamp', () => {
    const currentTime = Date.now();
    const oldTimestamp = currentTime - (10 * 60 * 1000); // 10 minutes ago
    
    const webhookData = createWebhookPayload({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      timestamp: oldTimestamp
    });

    const timeDiff = Math.abs(currentTime - webhookData.timestamp);
    const maxAge = 5 * 60 * 1000; // 5 minutes
    
    expect(timeDiff).toBeGreaterThan(maxAge);
  });

  test('should handle reduce only orders', async () => {
    // First create a position
    await mockExchange.placeOrder({
      symbol: 'BTCUSDT',
      side: 'buy',
      amount: 0.002,
      type: 'market'
    });

    const webhookData = createWebhookPayload({
      action: 'sell',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      reduce_only: true,
      strategy: 'BTC_Reduce_Position'
    });

    const payload = JSON.stringify(webhookData);
    const signature = generateHMACSignature(payload, webhookSecret);
    
    const isValid = validateWebhookSignature(payload, signature, webhookSecret);
    expect(isValid).toBe(true);

    const parsedData = JSON.parse(payload);
    const order = await mockExchange.placeOrder({
      symbol: parsedData.symbol,
      side: parsedData.action,
      amount: parsedData.quantity,
      type: 'market',
      reduceOnly: parsedData.reduce_only,
      clientOrderId: parsedData.client_id
    });

    expect(order.status).toBe('closed');
  });

  test('should handle multiple symbol webhooks in sequence', async () => {
    const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT'];
    const orders = [];

    for (const symbol of symbols) {
      const webhookData = createWebhookPayload({
        action: 'buy',
        symbol,
        quantity: symbol === 'BTCUSDT' ? 0.001 : 0.01,
        strategy: `Multi_Symbol_${symbol}`
      });

      const payload = JSON.stringify(webhookData);
      const signature = generateHMACSignature(payload, webhookSecret);
      
      const isValid = validateWebhookSignature(payload, signature, webhookSecret);
      expect(isValid).toBe(true);

      const parsedData = JSON.parse(payload);
      const order = await mockExchange.placeOrder({
        symbol: parsedData.symbol,
        side: parsedData.action,
        amount: parsedData.quantity,
        type: 'market',
        clientOrderId: parsedData.client_id
      });

      orders.push(order);
    }

    expect(orders).toHaveLength(3);
    orders.forEach(order => {
      expect(order.status).toBe('closed');
      expect(order.filled).toBeGreaterThan(0);
    });
  });

  test('should handle concurrent webhook processing', async () => {
    const webhookCount = 10;
    const webhookPromises = [];

    for (let i = 0; i < webhookCount; i++) {
      const webhookData = createWebhookPayload({
        action: 'buy',
        symbol: 'BTCUSDT',
        quantity: 0.001,
        strategy: `Concurrent_Test_${i}`,
        client_id: `concurrent_${i}_${Date.now()}`
      });

      const payload = JSON.stringify(webhookData);
      const signature = generateHMACSignature(payload, webhookSecret);
      
      // Validate signature
      const isValid = validateWebhookSignature(payload, signature, webhookSecret);
      expect(isValid).toBe(true);

      // Process webhook
      const parsedData = JSON.parse(payload);
      const orderPromise = mockExchange.placeOrder({
        symbol: parsedData.symbol,
        side: parsedData.action,
        amount: parsedData.quantity,
        type: 'market',
        clientOrderId: parsedData.client_id
      });

      webhookPromises.push(orderPromise);
    }

    const orders = await Promise.all(webhookPromises);
    
    expect(orders).toHaveLength(webhookCount);
    
    // Verify all orders have unique client IDs
    const clientIds = orders.map(o => o.clientOrderId);
    const uniqueClientIds = new Set(clientIds);
    expect(uniqueClientIds.size).toBe(webhookCount);
  });

  test('should handle webhook with custom parameters', async () => {
    const webhookData = createWebhookPayload({
      action: 'buy',
      symbol: 'BTCUSDT',
      quantity: 0.001,
      strategy: 'Custom_Strategy',
      custom_field_1: 'custom_value_1',
      custom_field_2: 42,
      metadata: {
        source: 'tradingview',
        version: '1.2.3'
      }
    });

    const payload = JSON.stringify(webhookData);
    const signature = generateHMACSignature(payload, webhookSecret);
    
    const isValid = validateWebhookSignature(payload, signature, webhookSecret);
    expect(isValid).toBe(true);

    const parsedData = JSON.parse(payload);
    
    // Verify custom fields are preserved
    expect(parsedData.custom_field_1).toBe('custom_value_1');
    expect(parsedData.custom_field_2).toBe(42);
    expect(parsedData.metadata.source).toBe('tradingview');
    
    // Should still process the trade normally
    const order = await mockExchange.placeOrder({
      symbol: parsedData.symbol,
      side: parsedData.action,
      amount: parsedData.quantity,
      type: 'market'
    });

    expect(order.status).toBe('closed');
  });
});