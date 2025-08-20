import { describe, it, expect, beforeEach, vi } from 'vitest';
import { AccountSelectionService } from './account-selection';
import type { TradingViewWebhook } from '@tradingview-gateway/shared';

// Mock PrismaClient
const mockPrisma = {
  exchangeAccount: {
    findFirst: vi.fn(),
  },
  strategyMapping: {
    findFirst: vi.fn(),
  },
  job: {
    findMany: vi.fn(),
  },
} as any;

describe('AccountSelectionService', () => {
  let service: AccountSelectionService;
  
  beforeEach(() => {
    service = new AccountSelectionService(mockPrisma);
    vi.clearAllMocks();
  });

  const createMockWebhook = (overrides: Partial<TradingViewWebhook> = {}): TradingViewWebhook => ({
    strategy: 'test-strategy',
    ticker: 'BTCUSDT',
    action: 'buy',
    exchange: 'binance',
    alert_id: 'test-alert-123',
    size_mode: 'quote',
    ...overrides
  });

  describe('Strategy 1: Direct account_id selection', () => {
    it('should select account by direct account_id', async () => {
      const webhook = createMockWebhook({ account_id: 'account-123' });
      
      mockPrisma.exchangeAccount.findFirst.mockResolvedValueOnce({
        id: 'account-123',
        name: 'Main Trading Account',
        exchange: 'binance',
        userId: 'user-123',
        testnet: false,
        isActive: true,
      });

      const result = await service.selectAccount({ webhook });

      expect(result.success).toBe(true);
      expect(result.account?.id).toBe('account-123');
      expect(result.account?.selectionReason).toBe('Direct account_id match');
      expect(mockPrisma.exchangeAccount.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'account-123',
          exchange: 'binance',
          isActive: true,
        },
        include: { user: true }
      });
    });

    it('should validate account ownership when userId provided', async () => {
      const webhook = createMockWebhook({ account_id: 'account-123' });
      
      mockPrisma.exchangeAccount.findFirst.mockResolvedValueOnce(null);

      const result = await service.selectAccount({ 
        webhook, 
        userId: 'user-123' 
      });

      expect(result.success).toBe(false);
      expect(result.reason).toContain('doesn\'t belong to user');
      expect(mockPrisma.exchangeAccount.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'account-123',
          exchange: 'binance',
          isActive: true,
          userId: 'user-123',
        },
        include: { user: true }
      });
    });
  });

  describe('Strategy 2: Strategy mapping selection', () => {
    it('should select account by explicit strategy mapping', async () => {
      const webhook = createMockWebhook({ strategy: 'scalping-strategy' });
      
      // Mock no direct account_id
      mockPrisma.exchangeAccount.findFirst.mockResolvedValueOnce(null);
      
      // Mock strategy mapping found
      mockPrisma.strategyMapping.findFirst.mockResolvedValueOnce({
        id: 'mapping-123',
        strategyName: 'scalping-strategy',
        priority: 10,
        account: {
          id: 'account-456',
          name: 'Scalping Account',
          exchange: 'binance',
          userId: 'user-123',
          testnet: false,
          isActive: true,
        }
      });

      const result = await service.selectAccount({ 
        webhook, 
        userId: 'user-123' 
      });

      expect(result.success).toBe(true);
      expect(result.account?.id).toBe('account-456');
      expect(result.account?.selectionReason).toContain('Explicit strategy mapping');
    });

    it('should fallback to name matching when no explicit mapping', async () => {
      const webhook = createMockWebhook({ strategy: 'test-strategy' });
      
      // Mock no direct account_id
      mockPrisma.exchangeAccount.findFirst
        .mockResolvedValueOnce(null) // No direct account
        .mockResolvedValueOnce({     // Name matching found
          id: 'account-789',
          name: 'test-strategy-account',
          exchange: 'binance',
          userId: 'user-123',
          testnet: false,
          isActive: true,
        });
      
      // Mock no explicit strategy mapping
      mockPrisma.strategyMapping.findFirst.mockResolvedValueOnce(null);

      const result = await service.selectAccount({ 
        webhook, 
        userId: 'user-123' 
      });

      expect(result.success).toBe(true);
      expect(result.account?.id).toBe('account-789');
      expect(result.account?.selectionReason).toBe('Strategy name matching (legacy)');
    });
  });

  describe('Strategy 3: User default account', () => {
    it('should select user default account by name', async () => {
      const webhook = createMockWebhook();
      
      // Mock no direct account_id or strategy mapping
      mockPrisma.exchangeAccount.findFirst
        .mockResolvedValueOnce(null) // No direct account
        .mockResolvedValueOnce(null) // No strategy mapping
        .mockResolvedValueOnce({     // Default account found
          id: 'account-default',
          name: 'Default Trading Account',
          exchange: 'binance',
          userId: 'user-123',
          testnet: false,
          isActive: true,
        });

      mockPrisma.strategyMapping.findFirst.mockResolvedValueOnce(null);

      const result = await service.selectAccount({ 
        webhook, 
        userId: 'user-123' 
      });

      expect(result.success).toBe(true);
      expect(result.account?.id).toBe('account-default');
      expect(result.account?.selectionReason).toContain('User default account');
    });

    it('should fallback to oldest account when no default found', async () => {
      const webhook = createMockWebhook();
      
      // Mock no direct account_id, strategy mapping, or default
      mockPrisma.exchangeAccount.findFirst
        .mockResolvedValueOnce(null) // No direct account
        .mockResolvedValueOnce(null) // No strategy mapping  
        .mockResolvedValueOnce(null) // No default account
        .mockResolvedValueOnce({     // Oldest account found
          id: 'account-oldest',
          name: 'First Account',
          exchange: 'binance',
          userId: 'user-123',
          testnet: false,
          isActive: true,
        });

      mockPrisma.strategyMapping.findFirst.mockResolvedValueOnce(null);

      const result = await service.selectAccount({ 
        webhook, 
        userId: 'user-123' 
      });

      expect(result.success).toBe(true);
      expect(result.account?.id).toBe('account-oldest');
      expect(result.account?.selectionReason).toBe('User first account (fallback)');
    });
  });

  describe('Strategy 4: First active account (system fallback)', () => {
    it('should select first active account when no user context', async () => {
      const webhook = createMockWebhook();
      
      // Mock no direct account_id or strategy matching
      mockPrisma.exchangeAccount.findFirst
        .mockResolvedValueOnce(null) // No direct account
        .mockResolvedValueOnce(null) // No strategy mapping
        .mockResolvedValueOnce({     // First active account
          id: 'account-system',
          name: 'System Fallback Account',
          exchange: 'binance',
          userId: 'any-user',
          testnet: false,
          isActive: true,
        });

      mockPrisma.strategyMapping.findFirst.mockResolvedValueOnce(null);

      const result = await service.selectAccount({ webhook });

      expect(result.success).toBe(true);
      expect(result.account?.id).toBe('account-system');
      expect(result.account?.selectionReason).toBe('First active account (system fallback)');
    });

    it('should fail when no accounts found at all', async () => {
      const webhook = createMockWebhook();
      
      // Mock all strategies returning null
      mockPrisma.exchangeAccount.findFirst.mockResolvedValue(null);
      mockPrisma.strategyMapping.findFirst.mockResolvedValue(null);

      const result = await service.selectAccount({ webhook });

      expect(result.success).toBe(false);
      expect(result.reason).toContain('No suitable account found');
    });
  });

  describe('Account permission validation', () => {
    it('should validate user has permission to use account', async () => {
      mockPrisma.exchangeAccount.findFirst.mockResolvedValueOnce({
        id: 'account-123',
        userId: 'user-123',
        isActive: true,
      });

      const result = await service.validateAccountPermission('account-123', 'user-123');

      expect(result.valid).toBe(true);
      expect(result.reason).toBe('User has permission to use this account');
    });

    it('should reject when account does not belong to user', async () => {
      mockPrisma.exchangeAccount.findFirst.mockResolvedValueOnce(null);

      const result = await service.validateAccountPermission('account-123', 'user-456');

      expect(result.valid).toBe(false);
      expect(result.reason).toBe('Account not found or does not belong to user');
    });
  });

  describe('Selection priority order', () => {
    it('should respect priority order: account_id > strategy mapping > user default > system fallback', async () => {
      const webhook = createMockWebhook({ 
        account_id: 'priority-account',
        strategy: 'test-strategy' 
      });
      
      // Mock direct account_id found (should be selected first)
      mockPrisma.exchangeAccount.findFirst.mockResolvedValueOnce({
        id: 'priority-account',
        name: 'Priority Account',
        exchange: 'binance',
        userId: 'user-123',
        testnet: false,
        isActive: true,
      });

      const result = await service.selectAccount({ 
        webhook, 
        userId: 'user-123' 
      });

      expect(result.success).toBe(true);
      expect(result.account?.id).toBe('priority-account');
      expect(result.account?.selectionReason).toBe('Direct account_id match');
      
      // Should not call strategy mapping since direct account_id was found
      expect(mockPrisma.strategyMapping.findFirst).not.toHaveBeenCalled();
    });
  });

  describe('Error handling', () => {
    it('should handle database errors gracefully', async () => {
      const webhook = createMockWebhook({ account_id: 'error-account' });
      
      mockPrisma.exchangeAccount.findFirst.mockRejectedValueOnce(
        new Error('Database connection failed')
      );

      const result = await service.selectAccount({ webhook });

      expect(result.success).toBe(false);
      expect(result.reason).toContain('Error selecting by account_id');
    });
  });
});