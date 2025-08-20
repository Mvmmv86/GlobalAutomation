import { describe, it, expect } from 'vitest';
import { TradingViewWebhookSchema, BinanceFuturesAlertSchema, BybitPerpAlertSchema } from './tradingview';

describe('TradingView Schemas', () => {
  describe('TradingViewWebhookSchema', () => {
    it('should validate valid webhook payload', () => {
      const validPayload = {
        strategy: 'Test Strategy',
        ticker: 'BTCUSDT',
        action: 'buy',
        exchange: 'binance',
        alert_id: 'test_alert_123',
        size_mode: 'quote',
        size_value: 100,
        leverage: 10,
      };

      const result = TradingViewWebhookSchema.safeParse(validPayload);
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.data.strategy).toBe('Test Strategy');
        expect(result.data.action).toBe('buy');
        expect(result.data.market_type).toBe('futures'); // default value
        expect(result.data.size_mode).toBe('quote');
      }
    });

    it('should apply default values', () => {
      const minimalPayload = {
        strategy: 'Test Strategy',
        ticker: 'BTCUSDT',
        action: 'buy',
        exchange: 'binance',
        alert_id: 'test_alert_123',
      };

      const result = TradingViewWebhookSchema.safeParse(minimalPayload);
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.data.size_mode).toBe('quote');
        expect(result.data.market_type).toBe('futures');
        expect(result.data.time_in_force).toBe('GTC');
        expect(result.data.reduce_only).toBe(false);
      }
    });

    it('should reject invalid action', () => {
      const invalidPayload = {
        strategy: 'Test Strategy',
        ticker: 'BTCUSDT',
        action: 'invalid_action',
        exchange: 'binance',
        alert_id: 'test_alert_123',
      };

      const result = TradingViewWebhookSchema.safeParse(invalidPayload);
      expect(result.success).toBe(false);
    });

    it('should reject invalid exchange', () => {
      const invalidPayload = {
        strategy: 'Test Strategy',
        ticker: 'BTCUSDT',
        action: 'buy',
        exchange: 'invalid_exchange',
        alert_id: 'test_alert_123',
      };

      const result = TradingViewWebhookSchema.safeParse(invalidPayload);
      expect(result.success).toBe(false);
    });

    it('should validate leverage range', () => {
      const invalidLeveragePayload = {
        strategy: 'Test Strategy',
        ticker: 'BTCUSDT',
        action: 'buy',
        exchange: 'binance',
        alert_id: 'test_alert_123',
        leverage: 200, // Too high
      };

      const result = TradingViewWebhookSchema.safeParse(invalidLeveragePayload);
      expect(result.success).toBe(false);
    });
  });

  describe('BinanceFuturesAlertSchema', () => {
    it('should validate valid Binance futures alert', () => {
      const validAlert = {
        strategy: 'Binance Strategy',
        ticker: 'BTCUSDT',
        action: 'buy',
        size_value: 1000,
        alert_id: 'binance_alert_123',
        leverage: 50,
      };

      const result = BinanceFuturesAlertSchema.safeParse(validAlert);
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.data.size_mode).toBe('quote'); // default
      }
    });

    it('should reject leverage above 125 for Binance', () => {
      const invalidAlert = {
        strategy: 'Binance Strategy',
        ticker: 'BTCUSDT',
        action: 'buy',
        size_value: 1000,
        alert_id: 'binance_alert_123',
        leverage: 150, // Too high for Binance
      };

      const result = BinanceFuturesAlertSchema.safeParse(invalidAlert);
      expect(result.success).toBe(false);
    });
  });

  describe('BybitPerpAlertSchema', () => {
    it('should validate valid Bybit perp alert', () => {
      const validAlert = {
        strategy: 'Bybit Strategy',
        ticker: 'BTCUSDT',
        action: 'sell',
        size_value: 0.1,
        alert_id: 'bybit_alert_123',
        leverage: 20,
      };

      const result = BybitPerpAlertSchema.safeParse(validAlert);
      expect(result.success).toBe(true);
      
      if (result.success) {
        expect(result.data.size_mode).toBe('contracts'); // default for Bybit
      }
    });

    it('should reject leverage above 100 for Bybit', () => {
      const invalidAlert = {
        strategy: 'Bybit Strategy',
        ticker: 'BTCUSDT',
        action: 'sell',
        size_value: 0.1,
        alert_id: 'bybit_alert_123',
        leverage: 150, // Too high for Bybit
      };

      const result = BybitPerpAlertSchema.safeParse(invalidAlert);
      expect(result.success).toBe(false);
    });
  });
});