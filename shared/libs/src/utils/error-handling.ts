export enum ErrorCategory {
  // Recoverable errors - can retry
  NETWORK_ERROR = 'NETWORK_ERROR',
  RATE_LIMIT = 'RATE_LIMIT',
  TEMPORARY_UNAVAILABLE = 'TEMPORARY_UNAVAILABLE',
  TIMEOUT = 'TIMEOUT',
  
  // Business logic errors - might be recoverable
  INSUFFICIENT_BALANCE = 'INSUFFICIENT_BALANCE',
  PRICE_FEED_ERROR = 'PRICE_FEED_ERROR',
  POSITION_SIZE_ERROR = 'POSITION_SIZE_ERROR',
  
  // Fatal errors - don't retry
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  ACCOUNT_NOT_FOUND = 'ACCOUNT_NOT_FOUND',
  INVALID_CONFIGURATION = 'INVALID_CONFIGURATION',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  EXCHANGE_REJECTED = 'EXCHANGE_REJECTED',
  
  // System errors - critical
  DATABASE_ERROR = 'DATABASE_ERROR',
  SYSTEM_ERROR = 'SYSTEM_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

export interface ErrorClassification {
  category: ErrorCategory;
  isRecoverable: boolean;
  maxRetries: number;
  retryDelayMs: number;
  shouldCircuitBreak: boolean;
  requiresImmediateAlert: boolean;
}

export interface TradingError extends Error {
  category: ErrorCategory;
  code?: string;
  context?: Record<string, any>;
  originalError?: Error;
  timestamp: Date;
  alertId?: string;
  accountId?: string;
}

export class TradingErrorHandler {
  private static classifications: Map<ErrorCategory, ErrorClassification> = new Map([
    // Recoverable network errors
    [ErrorCategory.NETWORK_ERROR, {
      category: ErrorCategory.NETWORK_ERROR,
      isRecoverable: true,
      maxRetries: 3,
      retryDelayMs: 2000,
      shouldCircuitBreak: true,
      requiresImmediateAlert: false
    }],
    
    [ErrorCategory.RATE_LIMIT, {
      category: ErrorCategory.RATE_LIMIT,
      isRecoverable: true,
      maxRetries: 5,
      retryDelayMs: 60000, // 1 minute for rate limits
      shouldCircuitBreak: false,
      requiresImmediateAlert: false
    }],
    
    [ErrorCategory.TEMPORARY_UNAVAILABLE, {
      category: ErrorCategory.TEMPORARY_UNAVAILABLE,
      isRecoverable: true,
      maxRetries: 3,
      retryDelayMs: 5000,
      shouldCircuitBreak: true,
      requiresImmediateAlert: false
    }],
    
    [ErrorCategory.TIMEOUT, {
      category: ErrorCategory.TIMEOUT,
      isRecoverable: true,
      maxRetries: 2,
      retryDelayMs: 3000,
      shouldCircuitBreak: true,
      requiresImmediateAlert: false
    }],
    
    // Business logic errors
    [ErrorCategory.INSUFFICIENT_BALANCE, {
      category: ErrorCategory.INSUFFICIENT_BALANCE,
      isRecoverable: false, // Don't retry - user needs to add funds
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: false,
      requiresImmediateAlert: true
    }],
    
    [ErrorCategory.PRICE_FEED_ERROR, {
      category: ErrorCategory.PRICE_FEED_ERROR,
      isRecoverable: true,
      maxRetries: 2,
      retryDelayMs: 1000,
      shouldCircuitBreak: true,
      requiresImmediateAlert: false
    }],
    
    [ErrorCategory.POSITION_SIZE_ERROR, {
      category: ErrorCategory.POSITION_SIZE_ERROR,
      isRecoverable: false,
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: false,
      requiresImmediateAlert: true
    }],
    
    // Fatal errors
    [ErrorCategory.AUTHENTICATION_ERROR, {
      category: ErrorCategory.AUTHENTICATION_ERROR,
      isRecoverable: false,
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: false,
      requiresImmediateAlert: true
    }],
    
    [ErrorCategory.ACCOUNT_NOT_FOUND, {
      category: ErrorCategory.ACCOUNT_NOT_FOUND,
      isRecoverable: false,
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: false,
      requiresImmediateAlert: true
    }],
    
    [ErrorCategory.INVALID_CONFIGURATION, {
      category: ErrorCategory.INVALID_CONFIGURATION,
      isRecoverable: false,
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: false,
      requiresImmediateAlert: true
    }],
    
    [ErrorCategory.VALIDATION_ERROR, {
      category: ErrorCategory.VALIDATION_ERROR,
      isRecoverable: false,
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: false,
      requiresImmediateAlert: false
    }],
    
    [ErrorCategory.EXCHANGE_REJECTED, {
      category: ErrorCategory.EXCHANGE_REJECTED,
      isRecoverable: false,
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: false,
      requiresImmediateAlert: true
    }],
    
    // System errors
    [ErrorCategory.DATABASE_ERROR, {
      category: ErrorCategory.DATABASE_ERROR,
      isRecoverable: true,
      maxRetries: 2,
      retryDelayMs: 1000,
      shouldCircuitBreak: true,
      requiresImmediateAlert: true
    }],
    
    [ErrorCategory.SYSTEM_ERROR, {
      category: ErrorCategory.SYSTEM_ERROR,
      isRecoverable: false,
      maxRetries: 0,
      retryDelayMs: 0,
      shouldCircuitBreak: true,
      requiresImmediateAlert: true
    }],
    
    [ErrorCategory.UNKNOWN_ERROR, {
      category: ErrorCategory.UNKNOWN_ERROR,
      isRecoverable: true,
      maxRetries: 1,
      retryDelayMs: 2000,
      shouldCircuitBreak: false,
      requiresImmediateAlert: true
    }]
  ]);

  /**
   * Classify an error based on its message and context
   */
  static classifyError(error: Error, context?: Record<string, any>): TradingError {
    const category = this.determineCategory(error);
    
    return {
      name: error.name,
      message: error.message,
      stack: error.stack,
      category,
      context: context || {},
      originalError: error,
      timestamp: new Date(),
      alertId: context?.alertId,
      accountId: context?.accountId
    } as TradingError;
  }

  /**
   * Get error classification details
   */
  static getClassification(category: ErrorCategory): ErrorClassification {
    return this.classifications.get(category) || this.classifications.get(ErrorCategory.UNKNOWN_ERROR)!;
  }

  /**
   * Determine if error should be retried
   */
  static shouldRetry(error: TradingError, currentRetryCount: number): boolean {
    const classification = this.getClassification(error.category);
    return classification.isRecoverable && currentRetryCount < classification.maxRetries;
  }

  /**
   * Calculate retry delay with exponential backoff
   */
  static calculateRetryDelay(error: TradingError, retryCount: number): number {
    const classification = this.getClassification(error.category);
    const baseDelay = classification.retryDelayMs;
    
    // Exponential backoff: baseDelay * (2 ^ retryCount) with jitter
    const exponentialDelay = baseDelay * Math.pow(2, retryCount);
    const jitter = Math.random() * 0.3; // 30% jitter
    
    return Math.floor(exponentialDelay * (1 + jitter));
  }

  /**
   * Determine error category from error message and type
   */
  private static determineCategory(error: Error): ErrorCategory {
    const message = error.message.toLowerCase();
    const name = error.name.toLowerCase();

    // Network and connection errors
    if (message.includes('network') || message.includes('connection') || 
        message.includes('econnreset') || message.includes('enotfound') ||
        name.includes('networkerror')) {
      return ErrorCategory.NETWORK_ERROR;
    }

    // Rate limiting
    if (message.includes('rate limit') || message.includes('too many requests') ||
        message.includes('429') || message.includes('rate exceeded')) {
      return ErrorCategory.RATE_LIMIT;
    }

    // Timeouts
    if (message.includes('timeout') || message.includes('timed out') ||
        name.includes('timeouterror')) {
      return ErrorCategory.TIMEOUT;
    }

    // Service unavailable
    if (message.includes('unavailable') || message.includes('service down') ||
        message.includes('503') || message.includes('502')) {
      return ErrorCategory.TEMPORARY_UNAVAILABLE;
    }

    // Authentication errors
    if (message.includes('unauthorized') || message.includes('authentication') ||
        message.includes('invalid token') || message.includes('401') ||
        message.includes('forbidden') || message.includes('403')) {
      return ErrorCategory.AUTHENTICATION_ERROR;
    }

    // Balance errors
    if (message.includes('insufficient balance') || message.includes('insufficient margin') ||
        message.includes('not enough') || message.includes('balance too low')) {
      return ErrorCategory.INSUFFICIENT_BALANCE;
    }

    // Account errors
    if (message.includes('account not found') || message.includes('account inactive') ||
        message.includes('no active account')) {
      return ErrorCategory.ACCOUNT_NOT_FOUND;
    }

    // Validation errors
    if (message.includes('validation') || message.includes('invalid') ||
        message.includes('schema') || name.includes('validationerror')) {
      return ErrorCategory.VALIDATION_ERROR;
    }

    // Price feed errors
    if (message.includes('price') || message.includes('ticker') ||
        message.includes('market data') || message.includes('no valid price')) {
      return ErrorCategory.PRICE_FEED_ERROR;
    }

    // Position size errors
    if (message.includes('order size') || message.includes('position size') ||
        message.includes('size calculated') || message.includes('sizing')) {
      return ErrorCategory.POSITION_SIZE_ERROR;
    }

    // Database errors
    if (message.includes('database') || message.includes('prisma') ||
        message.includes('connection') || message.includes('query failed')) {
      return ErrorCategory.DATABASE_ERROR;
    }

    // Exchange rejection
    if (message.includes('rejected') || message.includes('order failed') ||
        message.includes('exchange error') || message.includes('trading halted')) {
      return ErrorCategory.EXCHANGE_REJECTED;
    }

    // Configuration errors
    if (message.includes('configuration') || message.includes('config') ||
        message.includes('environment variable') || message.includes('missing')) {
      return ErrorCategory.INVALID_CONFIGURATION;
    }

    // Default to unknown
    return ErrorCategory.UNKNOWN_ERROR;
  }

  /**
   * Create a standardized error response
   */
  static formatErrorResponse(error: TradingError): {
    error: string;
    category: string;
    isRecoverable: boolean;
    retryAfter?: number;
    context?: Record<string, any>;
  } {
    const classification = this.getClassification(error.category);
    
    return {
      error: error.message,
      category: error.category,
      isRecoverable: classification.isRecoverable,
      retryAfter: classification.isRecoverable ? classification.retryDelayMs : undefined,
      context: error.context
    };
  }

  /**
   * Log error with appropriate level
   */
  static logError(error: TradingError, logger: any): void {
    const classification = this.getClassification(error.category);
    const logData = {
      category: error.category,
      isRecoverable: classification.isRecoverable,
      alertId: error.alertId,
      accountId: error.accountId,
      context: error.context,
      stack: error.stack
    };

    if (classification.requiresImmediateAlert) {
      logger.error(`CRITICAL ERROR: ${error.message}`, logData);
    } else if (!classification.isRecoverable) {
      logger.warn(`BUSINESS ERROR: ${error.message}`, logData);
    } else {
      logger.info(`RECOVERABLE ERROR: ${error.message}`, logData);
    }
  }
}

/**
 * Utility function to create typed trading errors
 */
export function createTradingError(
  message: string,
  category?: ErrorCategory,
  context?: Record<string, any>,
  originalError?: Error
): TradingError {
  const error = new Error(message) as TradingError;
  error.category = category || ErrorCategory.UNKNOWN_ERROR;
  error.context = context || {};
  error.originalError = originalError;
  error.timestamp = new Date();
  
  if (context?.alertId) error.alertId = context.alertId;
  if (context?.accountId) error.accountId = context.accountId;
  
  return error;
}

/**
 * Utility function to wrap existing errors
 */
export function wrapError(
  originalError: Error,
  context?: Record<string, any>
): TradingError {
  return TradingErrorHandler.classifyError(originalError, context);
}