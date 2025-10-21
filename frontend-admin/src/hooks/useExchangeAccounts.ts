import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

export interface ExchangeAccount {
  id: string
  name: string
  exchange: string
  api_key_preview?: string
  testnet: boolean
  is_active: boolean
  status: string
  created_at: string
  updated_at: string
}

/**
 * Hook para buscar contas de exchange do backend
 *
 * Endpoint: GET /api/v1/exchange-accounts
 *
 * Retorna lista de contas ativas para usar nos webhooks
 */
export const useExchangeAccounts = () => {
  return useQuery<ExchangeAccount[]>({
    queryKey: ['exchange-accounts'],
    queryFn: async () => {
      const response = await apiClient.instance.get('/api/v1/exchange-accounts')

      // Backend pode retornar array direto ou objeto com data
      if (Array.isArray(response.data)) {
        return response.data
      }

      // Se for objeto com data
      if (response.data?.data) {
        return response.data.data
      }

      // Se for objeto success
      if (response.data?.success && response.data?.accounts) {
        return response.data.accounts
      }

      return []
    },
    staleTime: 5 * 60 * 1000, // 5 minutos
    gcTime: 10 * 60 * 1000, // 10 minutos
    retry: 2,
    refetchOnWindowFocus: false
  })
}

/**
 * Hook para buscar uma conta específica
 */
export const useExchangeAccount = (accountId: string | undefined) => {
  return useQuery<ExchangeAccount>({
    queryKey: ['exchange-account', accountId],
    queryFn: async () => {
      if (!accountId) {
        throw new Error('Account ID is required')
      }

      const response = await apiClient.instance.get(`/api/v1/exchange-accounts/${accountId}`)
      return response.data?.data || response.data
    },
    enabled: !!accountId,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000
  })
}
