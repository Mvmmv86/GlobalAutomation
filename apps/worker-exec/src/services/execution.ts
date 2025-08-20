import { PrismaClient } from '@prisma/client';
import {
  JobPayload,
  TradingViewWebhook,
  BinanceAdapter,
  BybitAdapter,
  BaseExchangeAdapter,
  decryptCredentials,
  calculatePositionSize,
  validateSizingParams,
  logger,
  circuitBreakerManager,
  CircuitBreakerConfigs,
  RetryUtils,
  TradingErrorHandler,
  ErrorCategory,
} from '@tradingview-gateway/shared';

export class TradeExecutionService {
  constructor(private prisma: PrismaClient) {}

  async executeTradeWebhook(payload: JobPayload): Promise<void> {
    const { webhook, accountId, alertId } = payload;
    
    logger.info(`Executing trade for alert ${alertId}`, {
      symbol: webhook.ticker,
      action: webhook.action,
      exchange: webhook.exchange,
    });

    // Get account details with credentials
    const account = await this.prisma.exchangeAccount.findUnique({
      where: { id: accountId },
    });

    if (!account) {
      throw new Error(`Account not found: ${accountId}`);
    }

    if (!account.isActive) {
      throw new Error(`Account is inactive: ${accountId}`);
    }

    // Decrypt credentials
    const credentials = decryptCredentials(
      account.encryptedApiKey,
      account.encryptedSecretKey,
      account.encryptedPassphrase || undefined
    );

    // Create exchange adapter
    const adapter = this.createExchangeAdapter(account.exchange as any, {
      ...credentials,
      testnet: account.testnet,
    });

    // Execute trade based on action
    switch (webhook.action) {
      case 'buy':
      case 'sell':
        await this.executeBuySellOrder(adapter, webhook, alertId);
        break;
      case 'close':
        await this.executeClosePosition(adapter, webhook, alertId);
        break;
      case 'close_all':
        await this.executeCloseAllPositions(adapter, alertId);
        break;
      default:
        throw new Error(`Unsupported action: ${webhook.action}`);
    }

    logger.info(`Trade executed successfully for alert ${alertId}`);
  }

  private createExchangeAdapter(exchange: string, credentials: any): BaseExchangeAdapter {
    switch (exchange) {
      case 'binance':
        return new BinanceAdapter(credentials);
      case 'bybit':
        return new BybitAdapter(credentials);
      default:
        throw new Error(`Unsupported exchange: ${exchange}`);
    }
  }

  private async executeBuySellOrder(
    adapter: BaseExchangeAdapter,
    webhook: TradingViewWebhook,
    alertId: string
  ): Promise<void> {
    const symbol = adapter.normalizeSymbol(webhook.ticker);
    
    // Set leverage if specified
    if (webhook.leverage && webhook.leverage > 1) {
      await adapter.setLeverage(symbol, webhook.leverage);
    }

    // Get market price first for calculations
    const marketPrice = await this.getMarketPrice(adapter, symbol);
    
    let orderSize: number;
    
    if (webhook.size_value && webhook.size_value > 0) {
      // Get balance for sizing calculation with retry policy
      const balance = await RetryUtils.withRetry(
        () => adapter.getBalance(),
        { operation: 'getBalance', symbol }
      );
      
      const sizingParams = {
        mode: webhook.size_mode,
        value: webhook.size_value,
        balance: balance.USDT || balance.BUSD || 0,
        price: marketPrice,
        leverage: webhook.leverage || 1,
      };
      
      validateSizingParams(sizingParams);
      orderSize = calculatePositionSize(sizingParams);
    } else {
      // Fallback to quantity or contracts
      orderSize = webhook.quantity || webhook.contracts || 0;
    }

    if (orderSize <= 0) {
      throw new Error('Invalid order size calculated');
    }

    // CRITICAL: Validate balance before placing order with retry
    const balanceValidation = await RetryUtils.withRetry(
      () => adapter.validateBalance(
        symbol,
        webhook.action as 'buy' | 'sell',
        orderSize,
        marketPrice,
        webhook.leverage || 1
      ),
      { operation: 'validateBalance', symbol, side: webhook.action }
    );

    if (!balanceValidation.isValid) {
      throw new Error(`Insufficient balance: ${balanceValidation.reason}`);
    }

    logger.info(`Balance validation passed for ${symbol}`, {
      orderSize,
      marketPrice,
      leverage: webhook.leverage || 1,
      side: webhook.action
    });

    // Generate client order ID for idempotency
    const clientOrderId = `tv_${alertId}_${Date.now()}`;

    // Place main order with circuit breaker protection
    const order = await circuitBreakerManager.execute(
      `exchange-place-order-${adapter.constructor.name}`,
      () => adapter.placeOrder({
        symbol,
        side: webhook.action,
        amount: orderSize,
        type: 'market',
        clientOrderId,
        reduceOnly: webhook.reduce_only,
        stopLoss: webhook.stop_loss,
        takeProfit: webhook.take_profit,
      }),
      CircuitBreakerConfigs.EXCHANGE_API
    );

    // Store order in database
    await this.prisma.order.create({
      data: {
        id: order.id,
        clientOrderId: order.clientOrderId,
        exchange: order.exchange,
        symbol: order.symbol,
        side: order.side,
        type: order.type,
        amount: order.amount,
        price: order.price || 0,
        filled: order.filled,
        remaining: order.remaining,
        status: order.status,
        reduceOnly: webhook.reduce_only,
        accountId: webhook.account_id || '',
      },
    });

    logger.info(`Order placed successfully`, {
      orderId: order.id,
      clientOrderId,
      symbol,
      side: webhook.action,
      amount: orderSize,
    });
  }

  private async executeClosePosition(
    adapter: BaseExchangeAdapter,
    webhook: TradingViewWebhook,
    alertId: string
  ): Promise<void> {
    const symbol = adapter.normalizeSymbol(webhook.ticker);
    
    // Get current position
    const positions = await adapter.getPositions(symbol);
    const position = positions.find(p => p.symbol === symbol);
    
    if (!position || position.size === 0) {
      logger.warn(`No position found to close for symbol: ${symbol}`);
      return;
    }

    // Get market price for validation
    const marketPrice = await this.getMarketPrice(adapter, symbol);

    // Determine close side (opposite of position)
    const closeSide = position.side === 'long' ? 'sell' : 'buy';
    const closeSize = Math.abs(position.size);

    // Validate balance for closing (should always be valid for reduce-only orders)
    const balanceValidation = await adapter.validateBalance(
      symbol,
      closeSide,
      closeSize,
      marketPrice,
      position.leverage
    );

    if (!balanceValidation.isValid) {
      logger.warn(`Balance validation failed for close position: ${balanceValidation.reason}`);
      // Continue anyway since this is a reduce-only order
    }

    const clientOrderId = `tv_close_${alertId}_${Date.now()}`;

    // Place close order
    const order = await adapter.placeOrder({
      symbol,
      side: closeSide,
      amount: closeSize,
      type: 'market',
      clientOrderId,
      reduceOnly: true,
    });

    // Store order in database
    await this.prisma.order.create({
      data: {
        id: order.id,
        clientOrderId: order.clientOrderId,
        exchange: order.exchange,
        symbol: order.symbol,
        side: order.side,
        type: order.type,
        amount: order.amount,
        price: order.price || 0,
        filled: order.filled,
        remaining: order.remaining,
        status: order.status,
        reduceOnly: true,
        accountId: webhook.account_id || '',
      },
    });

    logger.info(`Position closed successfully`, {
      orderId: order.id,
      symbol,
      side: closeSide,
      amount: closeSize,
    });
  }

  private async executeCloseAllPositions(
    adapter: BaseExchangeAdapter,
    alertId: string
  ): Promise<void> {
    // Get all open positions
    const positions = await adapter.getPositions();
    
    if (positions.length === 0) {
      logger.info('No positions to close');
      return;
    }

    // Close each position
    for (const position of positions) {
      if (position.size === 0) continue;

      const closeSide = position.side === 'long' ? 'sell' : 'buy';
      const closeSize = Math.abs(position.size);
      const clientOrderId = `tv_close_all_${alertId}_${position.symbol}_${Date.now()}`;

      try {
        const order = await adapter.placeOrder({
          symbol: position.symbol,
          side: closeSide,
          amount: closeSize,
          type: 'market',
          clientOrderId,
          reduceOnly: true,
        });

        // Store order in database
        await this.prisma.order.create({
          data: {
            id: order.id,
            clientOrderId: order.clientOrderId,
            exchange: order.exchange,
            symbol: order.symbol,
            side: order.side,
            type: order.type,
            amount: order.amount,
            price: order.price || 0,
            filled: order.filled,
            remaining: order.remaining,
            status: order.status,
            reduceOnly: true,
            accountId: '', // We don't have account_id in close_all
          },
        });

        logger.info(`Position closed`, {
          symbol: position.symbol,
          side: closeSide,
          amount: closeSize,
        });

      } catch (error) {
        logger.error(`Failed to close position ${position.symbol}:`, error);
        // Continue with other positions
      }
    }
  }

  private async getMarketPrice(adapter: BaseExchangeAdapter, symbol: string): Promise<number> {
    const errors: string[] = [];

    // Use circuit breaker for exchange API calls
    try {
      // Primary: get real-time price from ticker with circuit breaker protection
      const ticker = await circuitBreakerManager.execute(
        `exchange-ticker-${adapter.constructor.name}`,
        () => adapter.getTicker(symbol),
        CircuitBreakerConfigs.EXCHANGE_API
      );
      
      if (ticker.price > 0) {
        logger.info(`Market price for ${symbol}: ${ticker.price} (from ticker)`);
        return ticker.price;
      }
      errors.push('Ticker returned zero price');
    } catch (error) {
      const tradingError = TradingErrorHandler.classifyError(error as Error, { symbol, operation: 'getTicker' });
      TradingErrorHandler.logError(tradingError, logger);
      errors.push(`Ticker failed: ${tradingError.message}`);
    }

    // Fallback 1: use existing positions mark price with retry
    try {
      const positions = await RetryUtils.withRetry(
        () => adapter.getPositions(symbol),
        { operation: 'getPositions', symbol }
      );
      
      if (positions.length > 0 && positions[0].markPrice > 0) {
        logger.warn(`Using position mark price for ${symbol}: ${positions[0].markPrice}`);
        return positions[0].markPrice;
      }
      errors.push('No positions with valid mark price');
    } catch (error) {
      const tradingError = TradingErrorHandler.classifyError(error as Error, { symbol, operation: 'getPositions' });
      TradingErrorHandler.logError(tradingError, logger);
      errors.push(`Positions failed: ${tradingError.message}`);
    }

    // Fallback 2: check recent orders for price reference with circuit breaker
    try {
      const orders = await circuitBreakerManager.execute(
        `exchange-orders-${adapter.constructor.name}`,
        () => adapter.getOpenOrders(symbol),
        CircuitBreakerConfigs.EXCHANGE_API
      );
      
      const recentOrder = orders.find(order => order.price && order.price > 0);
      if (recentOrder && recentOrder.price) {
        logger.warn(`Using recent order price for ${symbol}: ${recentOrder.price}`);
        return recentOrder.price;
      }
      errors.push('No recent orders with valid price');
    } catch (error) {
      const tradingError = TradingErrorHandler.classifyError(error as Error, { symbol, operation: 'getOpenOrders' });
      TradingErrorHandler.logError(tradingError, logger);
      errors.push(`Orders failed: ${tradingError.message}`);
    }

    // All fallbacks failed - throw comprehensive error
    const errorMessage = `Unable to determine market price for ${symbol}. All methods failed:\n${errors.join('\n')}`;
    logger.error(errorMessage);
    
    // Create a proper trading error for price feed failure
    const priceError = new Error(`Trading halted for safety - no valid price source for ${symbol}`);
    const tradingError = TradingErrorHandler.classifyError(priceError, { 
      symbol, 
      operation: 'getMarketPrice',
      category: ErrorCategory.PRICE_FEED_ERROR 
    });
    
    throw tradingError;
  }
}