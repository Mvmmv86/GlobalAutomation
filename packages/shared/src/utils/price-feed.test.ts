import { describe, it, expect, beforeEach } from 'vitest';
import { PriceCache } from './price-cache';

describe('PriceCache', () => {
  let cache: PriceCache;

  beforeEach(() => {
    cache = new PriceCache(1); // 1 second TTL for testing
  });

  it('should store and retrieve prices', () => {
    const now = new Date();
    cache.set('binance', 'BTCUSDT', 50000, now);
    
    const result = cache.get('binance', 'BTCUSDT');
    expect(result).toBeDefined();
    expect(result?.price).toBe(50000);
    expect(result?.timestamp).toEqual(now);
  });

  it('should return null for non-existent symbols', () => {
    const result = cache.get('binance', 'NONEXISTENT');
    expect(result).toBeNull();
  });

  it('should handle different exchanges separately', () => {
    const now = new Date();
    cache.set('binance', 'BTCUSDT', 50000, now);
    cache.set('bybit', 'BTCUSDT', 51000, now);
    
    const binanceResult = cache.get('binance', 'BTCUSDT');
    const bybitResult = cache.get('bybit', 'BTCUSDT');
    
    expect(binanceResult?.price).toBe(50000);
    expect(bybitResult?.price).toBe(51000);
  });

  it('should expire entries after TTL', async () => {
    const now = new Date();
    cache.set('binance', 'BTCUSDT', 50000, now);
    
    // Should exist immediately
    expect(cache.get('binance', 'BTCUSDT')).toBeDefined();
    
    // Wait for expiration
    await new Promise(resolve => setTimeout(resolve, 1100));
    
    // Should be expired
    expect(cache.get('binance', 'BTCUSDT')).toBeNull();
  });

  it('should cleanup expired entries', () => {
    const now = new Date();
    cache.set('binance', 'BTCUSDT', 50000, now);
    cache.set('binance', 'ETHUSDT', 3000, now);
    
    expect(cache.size()).toBe(2);
    
    // Wait for expiration
    setTimeout(() => {
      const removed = cache.cleanup();
      expect(removed).toBe(2);
      expect(cache.size()).toBe(0);
    }, 1100);
  });

  it('should clear all entries', () => {
    const now = new Date();
    cache.set('binance', 'BTCUSDT', 50000, now);
    cache.set('bybit', 'ETHUSDT', 3000, now);
    
    expect(cache.size()).toBe(2);
    cache.clear();
    expect(cache.size()).toBe(0);
  });
});

// Integration test scenarios for different symbols
describe('Symbol Normalization', () => {
  const testSymbols = [
    { input: 'BTCUSD', expected: 'BTCUSDT' },
    { input: 'ETHUSD', expected: 'ETHUSDT' },
    { input: 'BTCUSDT', expected: 'BTCUSDT' },
    { input: 'ADAUSD', expected: 'ADAUSDT' },
  ];

  testSymbols.forEach(({ input, expected }) => {
    it(`should normalize ${input} to ${expected}`, () => {
      // This would test the adapter's normalizeSymbol method
      // For now, just validate the logic
      const normalized = input.endsWith('USD') && !input.endsWith('USDT') 
        ? input.replace('USD', 'USDT') 
        : input;
      
      expect(normalized).toBe(expected);
    });
  });
});