import { PrismaClient } from '@prisma/client';
import type { TradingViewWebhook } from '@tradingview-gateway/shared';
import { logger } from '@tradingview-gateway/shared';

export interface AccountSelectionCriteria {
  webhook: TradingViewWebhook;
  userId?: string; // For user-specific webhooks
}

export interface SelectedAccount {
  id: string;
  name: string;
  exchange: string;
  userId: string;
  testnet: boolean;
  isActive: boolean;
  selectionReason: string;
}

export interface AccountSelectionResult {
  account: SelectedAccount | null;
  reason: string;
  success: boolean;
}

export class AccountSelectionService {
  constructor(private prisma: PrismaClient) {}

  /**
   * Smart account selection with multiple fallback strategies
   */
  async selectAccount(criteria: AccountSelectionCriteria): Promise<AccountSelectionResult> {
    const { webhook, userId } = criteria;
    
    logger.info('Starting account selection', {
      exchange: webhook.exchange,
      strategy: webhook.strategy,
      accountId: webhook.account_id,
      userId
    });

    // Strategy 1: Direct account_id from webhook
    if (webhook.account_id) {
      const result = await this.selectByAccountId(webhook.account_id, webhook.exchange, userId);
      if (result.success) return result;
      
      logger.warn('Failed to select by account_id, trying fallbacks', {
        accountId: webhook.account_id,
        reason: result.reason
      });
    }

    // Strategy 2: Select by strategy mapping
    const strategyResult = await this.selectByStrategy(webhook.strategy, webhook.exchange, userId);
    if (strategyResult.success) return strategyResult;

    // Strategy 3: Select user's default account for exchange
    if (userId) {
      const defaultResult = await this.selectUserDefault(userId, webhook.exchange);
      if (defaultResult.success) return defaultResult;
    }

    // Strategy 4: First active account for exchange (original behavior)
    const firstActiveResult = await this.selectFirstActive(webhook.exchange);
    if (firstActiveResult.success) return firstActiveResult;

    // All strategies failed
    return {
      account: null,
      reason: `No suitable account found for exchange ${webhook.exchange}`,
      success: false
    };
  }

  /**
   * Strategy 1: Select by explicit account_id
   */
  private async selectByAccountId(
    accountId: string, 
    exchange: string, 
    userId?: string
  ): Promise<AccountSelectionResult> {
    try {
      const whereClause: any = {
        id: accountId,
        exchange,
        isActive: true
      };

      // If userId provided, ensure account belongs to user
      if (userId) {
        whereClause.userId = userId;
      }

      const account = await this.prisma.exchangeAccount.findFirst({
        where: whereClause,
        include: { user: true }
      });

      if (!account) {
        return {
          account: null,
          reason: userId 
            ? `Account ${accountId} not found or doesn't belong to user ${userId}`
            : `Account ${accountId} not found or inactive`,
          success: false
        };
      }

      return {
        account: {
          id: account.id,
          name: account.name,
          exchange: account.exchange,
          userId: account.userId,
          testnet: account.testnet,
          isActive: account.isActive,
          selectionReason: 'Direct account_id match'
        },
        reason: `Selected account by ID: ${account.name}`,
        success: true
      };
    } catch (error) {
      return {
        account: null,
        reason: `Error selecting by account_id: ${error}`,
        success: false
      };
    }
  }

  /**
   * Strategy 2: Select by strategy name mapping
   */
  private async selectByStrategy(
    strategy: string, 
    exchange: string, 
    userId?: string
  ): Promise<AccountSelectionResult> {
    try {
      // First try explicit strategy mappings (new system)
      const explicitMapping = await this.selectByExplicitMapping(strategy, exchange, userId);
      if (explicitMapping.success) return explicitMapping;

      // Fallback to name-based matching (legacy)
      const nameMatching = await this.selectByNameMatching(strategy, exchange, userId);
      if (nameMatching.success) return nameMatching;

      return {
        account: null,
        reason: `No account found matching strategy "${strategy}"`,
        success: false
      };
    } catch (error) {
      return {
        account: null,
        reason: `Error selecting by strategy: ${error}`,
        success: false
      };
    }
  }

  /**
   * Strategy 2a: Select by explicit strategy mapping table
   */
  private async selectByExplicitMapping(
    strategy: string, 
    exchange: string, 
    userId?: string
  ): Promise<AccountSelectionResult> {
    try {
      const whereClause: any = {
        strategyName: strategy,
        isActive: true,
        account: {
          exchange,
          isActive: true
        }
      };

      if (userId) {
        whereClause.userId = userId;
      }

      const mapping = await this.prisma.strategyMapping.findFirst({
        where: whereClause,
        include: {
          account: {
            include: { user: true }
          }
        },
        orderBy: [
          { priority: 'desc' }, // Higher priority first
          { createdAt: 'desc' }  // Then newest
        ]
      });

      if (!mapping || !mapping.account) {
        return {
          account: null,
          reason: `No explicit mapping found for strategy "${strategy}"`,
          success: false
        };
      }

      return {
        account: {
          id: mapping.account.id,
          name: mapping.account.name,
          exchange: mapping.account.exchange,
          userId: mapping.account.userId,
          testnet: mapping.account.testnet,
          isActive: mapping.account.isActive,
          selectionReason: `Explicit strategy mapping (priority: ${mapping.priority})`
        },
        reason: `Selected account by explicit strategy mapping: ${mapping.account.name}`,
        success: true
      };
    } catch (error) {
      return {
        account: null,
        reason: `Error selecting by explicit mapping: ${error}`,
        success: false
      };
    }
  }

  /**
   * Strategy 2b: Select by account name matching (legacy)
   */
  private async selectByNameMatching(
    strategy: string, 
    exchange: string, 
    userId?: string
  ): Promise<AccountSelectionResult> {
    try {
      const whereClause: any = {
        exchange,
        isActive: true,
        OR: [
          { name: { contains: strategy, mode: 'insensitive' } },
          { name: { equals: strategy, mode: 'insensitive' } }
        ]
      };

      if (userId) {
        whereClause.userId = userId;
      }

      const account = await this.prisma.exchangeAccount.findFirst({
        where: whereClause,
        include: { user: true },
        orderBy: [
          { name: 'asc' }, // Prefer exact matches first
          { createdAt: 'desc' } // Then newest
        ]
      });

      if (!account) {
        return {
          account: null,
          reason: `No account found with name matching strategy "${strategy}"`,
          success: false
        };
      }

      return {
        account: {
          id: account.id,
          name: account.name,
          exchange: account.exchange,
          userId: account.userId,
          testnet: account.testnet,
          isActive: account.isActive,
          selectionReason: 'Strategy name matching (legacy)'
        },
        reason: `Selected account by name matching: ${account.name}`,
        success: true
      };
    } catch (error) {
      return {
        account: null,
        reason: `Error selecting by name matching: ${error}`,
        success: false
      };
    }
  }

  /**
   * Strategy 3: Select user's default account (first created, or marked as default)
   */
  private async selectUserDefault(
    userId: string, 
    exchange: string
  ): Promise<AccountSelectionResult> {
    try {
      // First try to find account with "default" in name
      const defaultAccount = await this.prisma.exchangeAccount.findFirst({
        where: {
          userId,
          exchange,
          isActive: true,
          name: { contains: 'default', mode: 'insensitive' }
        },
        include: { user: true }
      });

      if (defaultAccount) {
        return {
          account: {
            id: defaultAccount.id,
            name: defaultAccount.name,
            exchange: defaultAccount.exchange,
            userId: defaultAccount.userId,
            testnet: defaultAccount.testnet,
            isActive: defaultAccount.isActive,
            selectionReason: 'User default account (by name)'
          },
          reason: `Selected user's default account: ${defaultAccount.name}`,
          success: true
        };
      }

      // Fallback: oldest account for user (first created)
      const oldestAccount = await this.prisma.exchangeAccount.findFirst({
        where: {
          userId,
          exchange,
          isActive: true
        },
        include: { user: true },
        orderBy: { createdAt: 'asc' }
      });

      if (!oldestAccount) {
        return {
          account: null,
          reason: `No active accounts found for user ${userId} on ${exchange}`,
          success: false
        };
      }

      return {
        account: {
          id: oldestAccount.id,
          name: oldestAccount.name,
          exchange: oldestAccount.exchange,
          userId: oldestAccount.userId,
          testnet: oldestAccount.testnet,
          isActive: oldestAccount.isActive,
          selectionReason: 'User first account (fallback)'
        },
        reason: `Selected user's first account: ${oldestAccount.name}`,
        success: true
      };
    } catch (error) {
      return {
        account: null,
        reason: `Error selecting user default: ${error}`,
        success: false
      };
    }
  }

  /**
   * Strategy 4: First active account (original behavior)
   */
  private async selectFirstActive(exchange: string): Promise<AccountSelectionResult> {
    try {
      const account = await this.prisma.exchangeAccount.findFirst({
        where: {
          exchange,
          isActive: true
        },
        include: { user: true },
        orderBy: { createdAt: 'desc' } // Prefer newer accounts
      });

      if (!account) {
        return {
          account: null,
          reason: `No active accounts found for exchange ${exchange}`,
          success: false
        };
      }

      return {
        account: {
          id: account.id,
          name: account.name,
          exchange: account.exchange,
          userId: account.userId,
          testnet: account.testnet,
          isActive: account.isActive,
          selectionReason: 'First active account (system fallback)'
        },
        reason: `Selected first active account: ${account.name}`,
        success: true
      };
    } catch (error) {
      return {
        account: null,
        reason: `Error selecting first active account: ${error}`,
        success: false
      };
    }
  }

  /**
   * Validate if user has permission to use a specific account
   */
  async validateAccountPermission(
    accountId: string, 
    userId: string
  ): Promise<{ valid: boolean; reason: string }> {
    try {
      const account = await this.prisma.exchangeAccount.findFirst({
        where: {
          id: accountId,
          userId,
          isActive: true
        }
      });

      if (!account) {
        return {
          valid: false,
          reason: 'Account not found or does not belong to user'
        };
      }

      return {
        valid: true,
        reason: 'User has permission to use this account'
      };
    } catch (error) {
      return {
        valid: false,
        reason: `Error validating permission: ${error}`
      };
    }
  }

  /**
   * Get account selection statistics for monitoring
   */
  async getSelectionStats(timeRange: { from: Date; to: Date }) {
    try {
      const jobs = await this.prisma.job.findMany({
        where: {
          createdAt: {
            gte: timeRange.from,
            lte: timeRange.to
          }
        },
        include: {
          account: true
        }
      });

      const stats = {
        totalJobs: jobs.length,
        accountUsage: {} as Record<string, number>,
        exchangeUsage: {} as Record<string, number>
      };

      jobs.forEach(job => {
        if (job.account) {
          stats.accountUsage[job.account.name] = (stats.accountUsage[job.account.name] || 0) + 1;
          stats.exchangeUsage[job.account.exchange] = (stats.exchangeUsage[job.account.exchange] || 0) + 1;
        }
      });

      return stats;
    } catch (error) {
      logger.error('Error getting selection stats:', error);
      return null;
    }
  }
}