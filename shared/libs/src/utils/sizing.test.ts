import { describe, it, expect } from 'vitest';
import { calculatePositionSize, validateSizingParams } from './sizing';

describe('Position Sizing', () => {
  describe('calculatePositionSize', () => {
    it('should calculate base currency amount correctly', () => {
      const size = calculatePositionSize({
        mode: 'base',
        value: 0.5,
      });
      
      expect(size).toBe(0.5);
    });

    it('should calculate quote currency amount correctly', () => {
      const size = calculatePositionSize({
        mode: 'quote',
        value: 1000,
        price: 50000,
      });
      
      expect(size).toBe(0.02); // 1000 / 50000
    });

    it('should calculate percentage of balance correctly', () => {
      const size = calculatePositionSize({
        mode: 'pct_balance',
        value: 10, // 10%
        balance: 5000,
        price: 50000,
        leverage: 2,
      });
      
      expect(size).toBe(0.02); // (5000 * 0.1 * 2) / 50000
    });

    it('should calculate contracts correctly', () => {
      const size = calculatePositionSize({
        mode: 'contracts',
        value: 5,
        contractSize: 0.01,
      });
      
      expect(size).toBe(0.05); // 5 * 0.01
    });

    it('should throw error for quote mode without price', () => {
      expect(() => {
        calculatePositionSize({
          mode: 'quote',
          value: 1000,
        });
      }).toThrow('Price is required for quote sizing mode');
    });

    it('should throw error for pct_balance mode without balance', () => {
      expect(() => {
        calculatePositionSize({
          mode: 'pct_balance',
          value: 10,
          price: 50000,
        });
      }).toThrow('Balance is required for pct_balance sizing mode');
    });
  });

  describe('validateSizingParams', () => {
    it('should validate positive size value', () => {
      expect(() => {
        validateSizingParams({
          mode: 'base',
          value: -1,
        });
      }).toThrow('Size value must be positive');
    });

    it('should validate percentage not exceeding 100%', () => {
      expect(() => {
        validateSizingParams({
          mode: 'pct_balance',
          value: 150,
        });
      }).toThrow('Percentage cannot exceed 100%');
    });

    it('should validate leverage range', () => {
      expect(() => {
        validateSizingParams({
          mode: 'base',
          value: 1,
          leverage: 200,
        });
      }).toThrow('Leverage must be between 1 and 125');
    });

    it('should pass valid parameters', () => {
      expect(() => {
        validateSizingParams({
          mode: 'quote',
          value: 100,
          leverage: 10,
        });
      }).not.toThrow();
    });
  });
});