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
    const response = await apiClient.post<{ success: boolean; data: ExchangeAccount; message: string }>('/exchange-accounts', data)
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