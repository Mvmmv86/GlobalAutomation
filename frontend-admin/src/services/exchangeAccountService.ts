import { apiClient } from '@/lib/api'
import { ExchangeAccount } from '@/types/trading'

class ExchangeAccountService {
  async getExchangeAccounts(): Promise<ExchangeAccount[]> {
    try {
      console.log('🏦 ExchangeAccountService: Fetching exchange accounts...')
      const response = await apiClient.get<any[]>('/exchange-accounts')
      console.log('✅ ExchangeAccountService: Response received:', response)

      // Mapear os campos do backend para o formato do frontend
      const accounts = (response || []).map(account => ({
        id: account.id,
        name: account.name,
        exchange: account.exchange,
        testnet: account.environment === 'testnet',
        isActive: account.is_active,
        isMain: account.is_main, // Mapear is_main para isMain
        createdAt: account.created_at,
        updatedAt: account.updated_at
      }))

      return accounts
    } catch (error) {
      console.error('❌ ExchangeAccountService: Error fetching accounts:', error)
      return []
    }
  }

  async createExchangeAccount(data: {
    name: string
    exchange: string
    apiKey: string
    secretKey: string
    passphrase?: string
    testnet: boolean
    isDefault?: boolean
  }): Promise<ExchangeAccount> {
    // Convert camelCase to snake_case for backend compatibility
    const backendData = {
      name: data.name,
      exchange: data.exchange,
      api_key: data.apiKey,
      secret_key: data.secretKey,
      passphrase: data.passphrase,
      testnet: data.testnet,
      is_main: data.isDefault  // Mapeia isDefault para is_main no backend
    }
    const response = await apiClient.post<{ success: boolean; data: ExchangeAccount; message: string }>('/exchange-accounts', backendData)
    return response.data
  }

  async updateExchangeAccount(id: string, data: Partial<ExchangeAccount>): Promise<ExchangeAccount> {
    return apiClient.put<ExchangeAccount>(`/exchange-accounts/${id}`, data)
  }

  async setAsMainAccount(id: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put<{ success: boolean; message: string }>(`/exchange-accounts/${id}`, { is_main: true })
    return response
  }

  async deleteExchangeAccount(id: string): Promise<void> {
    return apiClient.delete(`/exchange-accounts/${id}`)
  }

  async testConnection(id: string): Promise<{ success: boolean; message: string }> {
    return apiClient.post(`/exchange-accounts/${id}/test`)
  }
}

export const exchangeAccountService = new ExchangeAccountService()