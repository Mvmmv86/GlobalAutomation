import type { Position } from '../types';

export interface MarginCalculationParams {
  amount: number;
  price: number;
  leverage: number;
  side: 'buy' | 'sell';
  exchange: 'binance' | 'bybit';
}

export interface BalanceValidationParams {
  availableBalance: number;
  requiredMargin: number;
  existingPositions: Position[];
  symbol: string;
  side: 'buy' | 'sell';
}

export interface BalanceValidationResult {
  isValid: boolean;
  availableBalance: number;
  requiredMargin: number;
  usedMargin: number;
  freeMargin: number;
  message?: string;
}

/**
 * Calculate required margin for a position
 * Formula: (amount * price) / leverage
 */
export function calculateRequiredMargin(params: MarginCalculationParams): number {
  const { amount, price, leverage } = params;
  
  if (amount <= 0) throw new Error('Amount must be positive');
  if (price <= 0) throw new Error('Price must be positive');
  if (leverage <= 0) throw new Error('Leverage must be positive');
  
  const notionalValue = amount * price;
  const requiredMargin = notionalValue / leverage;
  
  return requiredMargin;
}

/**
 * Calculate used margin from existing positions
 */
export function calculateUsedMargin(positions: Position[]): number {
  return positions.reduce((total, position) => {
    if (position.size === 0) return total;
    
    // Margin = (size * entryPrice) / leverage
    const positionMargin = (position.size * position.entryPrice) / position.leverage;
    return total + positionMargin;
  }, 0);
}

/**
 * Check if there's an existing position that would be increased/decreased
 */
export function findExistingPosition(
  positions: Position[], 
  symbol: string
): Position | undefined {
  return positions.find(pos => 
    pos.symbol === symbol && pos.size > 0
  );
}

/**
 * Calculate margin impact considering existing positions
 */
export function calculateMarginImpact(
  params: MarginCalculationParams,
  existingPosition?: Position
): { newMargin: number; marginDelta: number } {
  const newOrderMargin = calculateRequiredMargin(params);
  
  if (!existingPosition || existingPosition.size === 0) {
    // New position
    return {
      newMargin: newOrderMargin,
      marginDelta: newOrderMargin
    };
  }
  
  const { amount, side } = params;
  const existingMargin = (existingPosition.size * existingPosition.entryPrice) / existingPosition.leverage;
  
  // Check if order increases or decreases position
  const isSameSide = (existingPosition.side === 'long' && side === 'buy') || 
                     (existingPosition.side === 'short' && side === 'sell');
  
  if (isSameSide) {
    // Increasing position
    const newTotalMargin = existingMargin + newOrderMargin;
    return {
      newMargin: newTotalMargin,
      marginDelta: newOrderMargin
    };
  } else {
    // Reducing or closing position
    if (amount >= existingPosition.size) {
      // Closing or reversing position
      const remainingSize = amount - existingPosition.size;
      const newMargin = remainingSize > 0 ? 
        calculateRequiredMargin({ ...params, amount: remainingSize }) : 0;
      
      return {
        newMargin,
        marginDelta: newMargin - existingMargin
      };
    } else {
      // Partial close
      const newSize = existingPosition.size - amount;
      const newMargin = (newSize * existingPosition.entryPrice) / existingPosition.leverage;
      
      return {
        newMargin,
        marginDelta: newMargin - existingMargin
      };
    }
  }
}

/**
 * Validate if there's sufficient balance for the trade
 */
export function validateBalance(params: BalanceValidationParams): BalanceValidationResult {
  const { availableBalance, requiredMargin, existingPositions, symbol, side } = params;
  
  // Calculate current used margin
  const usedMargin = calculateUsedMargin(existingPositions);
  const freeMargin = Math.max(0, availableBalance - usedMargin);
  
  // Find existing position for this symbol
  const existingPosition = findExistingPosition(existingPositions, symbol);
  
  // Determine actual margin impact
  let marginDelta = requiredMargin;
  
  if (existingPosition) {
    const isSameSide = (existingPosition.side === 'long' && side === 'buy') || 
                     (existingPosition.side === 'short' && side === 'sell');
    
    if (!isSameSide && existingPosition) {
      // Reducing position - might free up margin
      const existingMargin = (existingPosition.size * existingPosition.entryPrice) / existingPosition.leverage;
      marginDelta = Math.max(0, requiredMargin - existingMargin);
    }
  }
  
  const isValid = freeMargin >= marginDelta;
  
  return {
    isValid,
    availableBalance,
    requiredMargin: marginDelta,
    usedMargin,
    freeMargin,
    message: isValid 
      ? 'Sufficient balance for trade'
      : `Insufficient margin. Required: ${marginDelta.toFixed(2)}, Available: ${freeMargin.toFixed(2)}`
  };
}

/**
 * Get margin requirements for different leverage levels
 */
export function getMarginRequirements(
  amount: number, 
  price: number
): Record<number, number> {
  const leverages = [1, 5, 10, 20, 50, 100];
  const requirements: Record<number, number> = {};
  
  leverages.forEach(leverage => {
    requirements[leverage] = calculateRequiredMargin({
      amount,
      price,
      leverage,
      side: 'buy',
      exchange: 'binance'
    });
  });
  
  return requirements;
}

/**
 * Calculate maximum position size for given balance and parameters
 */
export function calculateMaxPositionSize(
  availableMargin: number,
  price: number,
  leverage: number
): number {
  if (availableMargin <= 0 || price <= 0 || leverage <= 0) {
    return 0;
  }
  
  // maxMargin * leverage = maxNotional
  // maxNotional / price = maxSize
  const maxNotional = availableMargin * leverage;
  const maxSize = maxNotional / price;
  
  return maxSize;
}