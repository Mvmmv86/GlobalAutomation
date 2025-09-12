import { PrismaClient } from '@prisma/client';
import Redis from 'ioredis';
import { Worker, Queue } from 'bullmq';
import {
  BinanceAdapter,
  BybitAdapter,
  BaseExchangeAdapter,
  decryptCredentials,
  logger,
  Position,
  TradeExecution,
} from '@tradingview-gateway/shared';

export class ReconciliationService {
  private reconQueue: Queue;

  constructor(
    private prisma: PrismaClient,
    private redis: Redis
  ) {
    this.reconQueue = new Queue('recon', {
      connection: redis,
      defaultJobOptions: {
        removeOnComplete: 50,
        removeOnFail: 20,
        attempts: 2,
        backoff: {
          type: 'exponential',
          delay: 5000,
        },
      },
    });
  }

  async reconcileAccount(accountId: string): Promise<void> {
    logger.info(`Starting reconciliation for account: ${accountId}`);

    // Get account details
    const account = await this.prisma.exchangeAccount.findUnique({
      where: { id: accountId },
      include: { user: true },
    });

    if (!account) {
      throw new Error(`Account not found: ${accountId}`);
    }

    if (!account.isActive) {
      logger.info(`Skipping inactive account: ${accountId}`);
      return;
    }

    // Decrypt credentials and create adapter
    const credentials = decryptCredentials(
      account.encryptedApiKey,
      account.encryptedSecretKey,
      account.encryptedPassphrase || undefined
    );

    const adapter = this.createExchangeAdapter(account.exchange as any, {
      ...credentials,
      testnet: account.testnet,
    });

    try {
      // Reconcile positions
      await this.reconcilePositions(adapter, accountId);
      
      // Reconcile trades
      await this.reconcileTrades(adapter, accountId);
      
      // Calculate and store PnL
      await this.calculatePnL(accountId, account.userId);
      
      // Broadcast updates (could be via WebSocket/SSE)
      await this.broadcastUpdates(accountId, account.userId);

    } catch (error) {
      logger.error(`Reconciliation error for account ${accountId}:`, error);
      throw error;
    }
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

  private async reconcilePositions(adapter: BaseExchangeAdapter, accountId: string): Promise<void> {
    try {
      // Get positions from exchange
      const exchangePositions = await adapter.getPositions();
      
      // Get existing positions from database
      const dbPositions = await this.prisma.position.findMany({
        where: { accountId },
      });

      // Create a map of existing positions
      const dbPositionsMap = new Map(
        dbPositions.map(pos => [`${pos.symbol}`, pos])
      );

      // Update or create positions
      for (const exchangePos of exchangePositions) {
        const existingPos = dbPositionsMap.get(exchangePos.symbol);
        
        if (existingPos) {
          // Update existing position
          await this.prisma.position.update({
            where: { id: existingPos.id },
            data: {
              side: exchangePos.side,
              size: exchangePos.size,
              entryPrice: exchangePos.entryPrice,
              markPrice: exchangePos.markPrice,
              unrealizedPnl: exchangePos.unrealizedPnl,
              realizedPnl: exchangePos.realizedPnl,
              leverage: exchangePos.leverage,
              timestamp: exchangePos.timestamp,
              updatedAt: new Date(),
            },
          });
        } else {
          // Create new position
          await this.prisma.position.create({
            data: {
              symbol: exchangePos.symbol,
              exchange: exchangePos.exchange,
              side: exchangePos.side,
              size: exchangePos.size,
              entryPrice: exchangePos.entryPrice,
              markPrice: exchangePos.markPrice,
              unrealizedPnl: exchangePos.unrealizedPnl,
              realizedPnl: exchangePos.realizedPnl,
              leverage: exchangePos.leverage,
              accountId,
              timestamp: exchangePos.timestamp,
            },
          });
        }
        
        // Remove from map to track what's been processed
        dbPositionsMap.delete(exchangePos.symbol);
      }

      // Remove positions that no longer exist on exchange (closed positions)
      for (const [symbol, dbPos] of dbPositionsMap) {
        await this.prisma.position.delete({
          where: { id: dbPos.id },
        });
        logger.info(`Removed closed position: ${symbol}`);
      }

      logger.info(`Reconciled ${exchangePositions.length} positions for account ${accountId}`);

    } catch (error) {
      logger.error(`Position reconciliation failed for account ${accountId}:`, error);
      throw error;
    }
  }

  private async reconcileTrades(adapter: BaseExchangeAdapter, accountId: string): Promise<void> {
    try {
      // Get the most recent trade timestamp to avoid fetching all trades
      const lastTrade = await this.prisma.trade.findFirst({
        where: {
          order: {
            accountId,
          },
        },
        orderBy: {
          timestamp: 'desc',
        },
      });

      const since = lastTrade ? lastTrade.timestamp.getTime() : undefined;
      
      // Get trades from exchange
      const exchangeTrades = await adapter.getTrades(undefined, since);
      
      // Process each trade
      for (const trade of exchangeTrades) {
        // Check if trade already exists
        const existingTrade = await this.prisma.trade.findUnique({
          where: {
            tradeId_orderId: {
              tradeId: trade.tradeId,
              orderId: trade.orderId,
            },
          },
        });

        if (!existingTrade) {
          // Find corresponding order
          const order = await this.prisma.order.findFirst({
            where: {
              OR: [
                { id: trade.orderId },
                { clientOrderId: trade.orderId }, // Sometimes orderId is clientOrderId
              ],
              accountId,
            },
          });

          if (order) {
            // Create new trade record
            await this.prisma.trade.create({
              data: {
                tradeId: trade.tradeId,
                orderId: order.id,
                symbol: trade.symbol,
                side: trade.side,
                amount: trade.amount,
                price: trade.price,
                fee: trade.fee,
                feeCurrency: trade.feeCurrency,
                timestamp: trade.timestamp,
              },
            });

            // Update order fill status
            const newFilled = order.filled + trade.amount;
            const newRemaining = Math.max(0, order.amount - newFilled);
            const newStatus = newRemaining === 0 ? 'closed' : order.status;

            await this.prisma.order.update({
              where: { id: order.id },
              data: {
                filled: newFilled,
                remaining: newRemaining,
                status: newStatus,
              },
            });
          }
        }
      }

      logger.info(`Reconciled ${exchangeTrades.length} trades for account ${accountId}`);

    } catch (error) {
      logger.error(`Trade reconciliation failed for account ${accountId}:`, error);
      throw error;
    }
  }

  private async calculatePnL(accountId: string, userId: string): Promise<void> {
    try {
      // Get all positions for the account
      const positions = await this.prisma.position.findMany({
        where: { accountId },
      });

      // Calculate totals
      let totalUnrealizedPnl = 0;
      let totalRealizedPnl = 0;

      for (const position of positions) {
        totalUnrealizedPnl += position.unrealizedPnl;
        totalRealizedPnl += position.realizedPnl;
      }

      // Get realized PnL from closed trades
      const closedTrades = await this.prisma.trade.findMany({
        where: {
          order: {
            accountId,
          },
        },
        include: {
          order: true,
        },
      });

      // Calculate realized PnL from trades (simplified calculation)
      for (const trade of closedTrades) {
        // This is a simplified calculation - in reality, you'd need more complex logic
        // to calculate actual realized PnL considering entry/exit prices
      }

      // Calculate equity (this would typically include account balance + unrealized PnL)
      const equity = totalRealizedPnl + totalUnrealizedPnl;

      // Store PnL record
      await this.prisma.pnLRecord.create({
        data: {
          accountId,
          userId,
          realizedPnl: totalRealizedPnl,
          unrealizedPnl: totalUnrealizedPnl,
          equity,
          timestamp: new Date(),
        },
      });

      logger.info(`PnL calculated for account ${accountId}: Realized=${totalRealizedPnl}, Unrealized=${totalUnrealizedPnl}, Equity=${equity}`);

    } catch (error) {
      logger.error(`PnL calculation failed for account ${accountId}:`, error);
      throw error;
    }
  }

  private async broadcastUpdates(accountId: string, userId: string): Promise<void> {
    try {
      // Publish updates to Redis for real-time notifications
      const updateData = {
        type: 'account_update',
        accountId,
        userId,
        timestamp: new Date().toISOString(),
      };

      await this.redis.publish('account_updates', JSON.stringify(updateData));
      
      logger.debug(`Broadcast update for account ${accountId}`);

    } catch (error) {
      logger.error(`Failed to broadcast updates for account ${accountId}:`, error);
      // Don't throw here as this is not critical
    }
  }

  async scheduleRecurringRecon(worker: Worker): Promise<void> {
    // Schedule reconciliation for all active accounts every 30 seconds
    setInterval(async () => {
      try {
        const activeAccounts = await this.prisma.exchangeAccount.findMany({
          where: { isActive: true },
          select: { id: true },
        });

        for (const account of activeAccounts) {
          await this.reconQueue.add(
            'reconcile-positions',
            { accountId: account.id },
            {
              delay: Math.random() * 10000, // Stagger requests
              jobId: `recon_${account.id}_${Date.now()}`,
            }
          );
        }

        logger.debug(`Scheduled reconciliation for ${activeAccounts.length} accounts`);

      } catch (error) {
        logger.error('Failed to schedule recurring reconciliation:', error);
      }
    }, 30000); // 30 seconds
  }

  async cleanup(): Promise<void> {
    await this.reconQueue.close();
  }
}