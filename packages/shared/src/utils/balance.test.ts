import { describe, it, expect } from 'vitest';
import {
  calculateRequiredMargin,
  calculateUsedMargin,
  findExistingPosition,
  calculateMarginImpact,
  validateBalance,
  getMarginRequirements,
  calculateMaxPositionSize
} from './balance';
import type { Position } from '../types';

describe('Balance Calculations', () => {
  describe('calculateRequiredMargin', () => {
    it('should calculate margin correctly', () => {
      const result = calculateRequiredMargin({
        amount: 1,
        price: 50000,
        leverage: 10,
        side: 'buy',
        exchange: 'binance'
      });
      
      // (1 * 50000) / 10 = 5000
      expect(result).toBe(5000);
    });

    it('should handle different leverage levels', () => {
      const params = {
        amount: 0.1,
        price: 50000,
        side: 'buy' as const,
        exchange: 'binance' as const
      };

      expect(calculateRequiredMargin({ ...params, leverage: 1 })).toBe(5000);
      expect(calculateRequiredMargin({ ...params, leverage: 10 })).toBe(500);
      expect(calculateRequiredMargin({ ...params, leverage: 100 })).toBe(50);
    });

    it('should throw for invalid inputs', () => {
      expect(() => calculateRequiredMargin({
        amount: 0,
        price: 50000,
        leverage: 10,
        side: 'buy',
        exchange: 'binance'
      })).toThrow('Amount must be positive');

      expect(() => calculateRequiredMargin({
        amount: 1,
        price: 0,
        leverage: 10,
        side: 'buy',
        exchange: 'binance'
      })).toThrow('Price must be positive');

      expect(() => calculateRequiredMargin({
        amount: 1,
        price: 50000,
        leverage: 0,
        side: 'buy',
        exchange: 'binance'
      })).toThrow('Leverage must be positive');
    });
  });

  describe('calculateUsedMargin', () => {
    it('should calculate used margin from positions', () => {
      const positions: Position[] = [
        {
          id: '1',
          symbol: 'BTCUSDT',
          exchange: 'binance',
          side: 'long',
          size: 1,
          entryPrice: 50000,
          markPrice: 51000,
          unrealizedPnl: 1000,
          realizedPnl: 0,
          leverage: 10,
          timestamp: new Date()
        },
        {
          id: '2',
          symbol: 'ETHUSDT',
          exchange: 'binance',
          side: 'long',
          size: 5,
          entryPrice: 3000,
          markPrice: 3100,
          unrealizedPnl: 500,
          realizedPnl: 0,
          leverage: 5,
          timestamp: new Date()
        }
      ];

      // BTC: (1 * 50000) / 10 = 5000
      // ETH: (5 * 3000) / 5 = 3000
      // Total: 8000
      const result = calculateUsedMargin(positions);
      expect(result).toBe(8000);
    });

    it('should ignore positions with zero size', () => {
      const positions: Position[] = [
        {
          id: '1',
          symbol: 'BTCUSDT',
          exchange: 'binance',
          side: 'long',
          size: 0,
          entryPrice: 50000,
          markPrice: 51000,
          unrealizedPnl: 0,
          realizedPnl: 0,
          leverage: 10,
          timestamp: new Date()
        }
      ];

      const result = calculateUsedMargin(positions);
      expect(result).toBe(0);
    });
  });

  describe('findExistingPosition', () => {
    it('should find existing position by symbol', () => {
      const positions: Position[] = [
        {
          id: '1',
          symbol: 'BTCUSDT',
          exchange: 'binance',
          side: 'long',
          size: 1,
          entryPrice: 50000,
          markPrice: 51000,
          unrealizedPnl: 1000,
          realizedPnl: 0,
          leverage: 10,
          timestamp: new Date()
        }
      ];

      const result = findExistingPosition(positions, 'BTCUSDT');
      expect(result).toBeDefined();
      expect(result?.symbol).toBe('BTCUSDT');
    });

    it('should return undefined for non-existent symbol', () => {
      const positions: Position[] = [];
      const result = findExistingPosition(positions, 'ETHUSDT');
      expect(result).toBeUndefined();
    });
  });

  describe('calculateMarginImpact', () => {
    it('should handle new position', () => {
      const params = {
        amount: 1,
        price: 50000,
        leverage: 10,
        side: 'buy' as const,
        exchange: 'binance' as const
      };

      const result = calculateMarginImpact(params);
      expect(result.newMargin).toBe(5000);
      expect(result.marginDelta).toBe(5000);
    });

    it('should handle increasing existing position', () => {
      const params = {
        amount: 0.5,
        price: 50000,
        leverage: 10,
        side: 'buy' as const,
        exchange: 'binance' as const
      };

      const existingPosition: Position = {
        id: '1',
        symbol: 'BTCUSDT',
        exchange: 'binance',
        side: 'long',
        size: 1,
        entryPrice: 48000,
        markPrice: 50000,
        unrealizedPnl: 2000,
        realizedPnl: 0,
        leverage: 10,
        timestamp: new Date()
      };

      const result = calculateMarginImpact(params, existingPosition);
      
      // Existing margin: (1 * 48000) / 10 = 4800
      // New order margin: (0.5 * 50000) / 10 = 2500
      // Total new margin: 4800 + 2500 = 7300
      expect(result.newMargin).toBe(7300);
      expect(result.marginDelta).toBe(2500);
    });

    it('should handle closing position', () => {
      const params = {
        amount: 1,
        price: 50000,
        leverage: 10,
        side: 'sell' as const,
        exchange: 'binance' as const
      };

      const existingPosition: Position = {
        id: '1',
        symbol: 'BTCUSDT',
        exchange: 'binance',
        side: 'long',
        size: 1,
        entryPrice: 48000,
        markPrice: 50000,
        unrealizedPnl: 2000,
        realizedPnl: 0,
        leverage: 10,
        timestamp: new Date()
      };

      const result = calculateMarginImpact(params, existingPosition);
      
      // Closing full position should result in 0 margin
      expect(result.newMargin).toBe(0);
      expect(result.marginDelta).toBeLessThan(0); // Negative because margin is freed
    });
  });

  describe('validateBalance', () => {
    it('should validate sufficient balance', () => {
      const result = validateBalance({
        availableBalance: 10000,
        requiredMargin: 5000,
        existingPositions: [],
        symbol: 'BTCUSDT',
        side: 'buy'
      });

      expect(result.isValid).toBe(true);
      expect(result.freeMargin).toBe(10000);
      expect(result.message).toBe('Sufficient balance for trade');
    });

    it('should detect insufficient balance', () => {
      const result = validateBalance({
        availableBalance: 1000,
        requiredMargin: 5000,
        existingPositions: [],
        symbol: 'BTCUSDT',
        side: 'buy'
      });

      expect(result.isValid).toBe(false);
      expect(result.message).toContain('Insufficient margin');
    });

    it('should consider existing positions', () => {
      const existingPositions: Position[] = [
        {
          id: '1',
          symbol: 'ETHUSDT',
          exchange: 'binance',
          side: 'long',
          size: 2,
          entryPrice: 3000,
          markPrice: 3100,
          unrealizedPnl: 200,
          realizedPnl: 0,
          leverage: 5,
          timestamp: new Date()
        }
      ];

      const result = validateBalance({
        availableBalance: 10000,
        requiredMargin: 5000,
        existingPositions,
        symbol: 'BTCUSDT',
        side: 'buy'
      });

      // Available: 10000
      // Used by ETH: (2 * 3000) / 5 = 1200
      // Free: 10000 - 1200 = 8800
      // Required: 5000
      // Should be valid
      expect(result.isValid).toBe(true);
      expect(result.usedMargin).toBe(1200);
      expect(result.freeMargin).toBe(8800);
    });
  });

  describe('getMarginRequirements', () => {
    it('should return requirements for different leverage levels', () => {
      const requirements = getMarginRequirements(1, 50000);
      
      expect(requirements[1]).toBe(50000);
      expect(requirements[10]).toBe(5000);
      expect(requirements[100]).toBe(500);
    });
  });

  describe('calculateMaxPositionSize', () => {
    it('should calculate maximum position size', () => {
      const maxSize = calculateMaxPositionSize(5000, 50000, 10);
      
      // 5000 * 10 / 50000 = 1
      expect(maxSize).toBe(1);
    });

    it('should return 0 for invalid inputs', () => {
      expect(calculateMaxPositionSize(0, 50000, 10)).toBe(0);
      expect(calculateMaxPositionSize(5000, 0, 10)).toBe(0);
      expect(calculateMaxPositionSize(5000, 50000, 0)).toBe(0);
    });
  });
});

describe('Real-world Scenarios', () => {
  it('should handle complex multi-position scenario', () => {
    const existingPositions: Position[] = [
      {
        id: '1',
        symbol: 'BTCUSDT',
        exchange: 'binance',
        side: 'long',
        size: 0.5,
        entryPrice: 45000,
        markPrice: 50000,
        unrealizedPnl: 2500,
        realizedPnl: 0,
        leverage: 20,
        timestamp: new Date()
      },
      {
        id: '2',
        symbol: 'ETHUSDT',
        exchange: 'binance',
        side: 'short',
        size: 3,
        entryPrice: 3200,
        markPrice: 3000,
        unrealizedPnl: 600,
        realizedPnl: 0,
        leverage: 10,
        timestamp: new Date()
      }
    ];

    // Used margin calculation:
    // BTC: (0.5 * 45000) / 20 = 1125
    // ETH: (3 * 3200) / 10 = 960
    // Total used: 2085
    
    const validation = validateBalance({
      availableBalance: 5000,
      requiredMargin: 2000, // New position requiring 2000 margin
      existingPositions,
      symbol: 'ADAUSDT',
      side: 'buy'
    });

    expect(validation.usedMargin).toBe(2085);
    expect(validation.freeMargin).toBe(2915); // 5000 - 2085
    expect(validation.isValid).toBe(true); // 2915 >= 2000
  });

  it('should handle position reduction scenario', () => {
    const existingPositions: Position[] = [
      {
        id: '1',
        symbol: 'BTCUSDT',
        exchange: 'binance',
        side: 'long',
        size: 1,
        entryPrice: 50000,
        markPrice: 52000,
        unrealizedPnl: 2000,
        realizedPnl: 0,
        leverage: 10,
        timestamp: new Date()
      }
    ];

    // Trying to sell 0.5 BTC (reducing position)
    const validation = validateBalance({
      availableBalance: 5000,
      requiredMargin: 2500, // This would be for opening 0.5 BTC
      existingPositions,
      symbol: 'BTCUSDT',
      side: 'sell' // Opposite side = reducing position
    });

    // When reducing position, margin should be freed up, not required
    expect(validation.isValid).toBe(true);
  });
});