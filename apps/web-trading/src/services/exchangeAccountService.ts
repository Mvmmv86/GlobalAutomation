import { apiClient } from '@/lib/api'
import { ExchangeAccount } from '@/types/trading'

class ExchangeAccountService {
  async getExchangeAccounts(): Promise<ExchangeAccount[]> {
    const response = await apiClient.get<{ success: boolean; data: ExchangeAccount[] }>('/exchange-accounts')
    return response.data || []
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
      is_default: data.isDefault
    }
    const response = await apiClient.post<{ success: boolean; data: ExchangeAccount; message: string }>('/exchange-accounts', backendData)
    return response.data
  }

  async updateExchangeAccount(id: string, data: Partial<ExchangeAccount>): Promise<ExchangeAccount> {
    return apiClient.put<ExchangeAccount>(`/exchange-accounts/${id}`, data)
  }

  async deleteExchangeAccount(id: string): Promise<void> {
    return apiClient.delete(`/exchange-accounts/${id}`)
  }

  async testConnection(id: string): Promise<{ success: boolean; message: string }> {
    return apiClient.post(`/exchange-accounts/${id}/test`)
  }
}

export const exchangeAccountService = new ExchangeAccountService()