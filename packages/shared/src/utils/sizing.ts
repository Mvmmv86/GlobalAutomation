import type { SizeMode } from '../types';

export interface SizingParams {
  mode: SizeMode;
  value: number;
  balance?: number;
  price?: number;
  leverage?: number;
  contractSize?: number;
}

export function calculatePositionSize(params: SizingParams): number {
  const { mode, value, balance, price, leverage = 1, contractSize = 1 } = params;

  switch (mode) {
    case 'base':
      // Direct base currency amount (e.g., 0.1 BTC)
      return value;

    case 'quote':
      // Quote currency amount (e.g., 1000 USDT)
      if (!price) {
        throw new Error('Price is required for quote sizing mode');
      }
      return value / price;

    case 'pct_balance':
      // Percentage of available balance
      if (!balance) {
        throw new Error('Balance is required for pct_balance sizing mode');
      }
      if (!price) {
        throw new Error('Price is required for pct_balance sizing mode');
      }
      const quoteAmount = (balance * value / 100) * leverage;
      return quoteAmount / price;

    case 'contracts':
      // Number of contracts (for futures/perp)
      return value * contractSize;

    default:
      throw new Error(`Unsupported sizing mode: ${mode}`);
  }
}

export function validateSizingParams(params: SizingParams): void {
  if (params.value <= 0) {
    throw new Error('Size value must be positive');
  }

  if (params.mode === 'pct_balance') {
    if (params.value > 100) {
      throw new Error('Percentage cannot exceed 100%');
    }
  }

  if (params.leverage && (params.leverage < 1 || params.leverage > 125)) {
    throw new Error('Leverage must be between 1 and 125');
  }
}