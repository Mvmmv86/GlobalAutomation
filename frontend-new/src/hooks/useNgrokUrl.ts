import { useQuery } from '@tanstack/react-query'

interface NgrokUrlResponse {
  success: boolean
  ngrok_url: string | null
  updated_at: string
  error?: string
}

export const useNgrokUrl = () => {
  return useQuery({
    queryKey: ['ngrok-url'],
    queryFn: async (): Promise<string | null> => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/ngrok/url`)
        const data: NgrokUrlResponse = await response.json()

        if (data.success && data.ngrok_url) {
          return data.ngrok_url
        }

        // Fallback para .env se ngrok não estiver disponível
        return import.meta.env.VITE_WEBHOOK_PUBLIC_URL || import.meta.env.VITE_API_URL
      } catch (error) {
        console.error('Error fetching ngrok URL:', error)
        // Fallback para .env em caso de erro
        return import.meta.env.VITE_WEBHOOK_PUBLIC_URL || import.meta.env.VITE_API_URL
      }
    },
    staleTime: 30000, // Considera "fresco" por 30 segundos
    refetchInterval: 60000, // Revalida a cada 60 segundos
    refetchOnWindowFocus: true, // Revalida quando usuário volta para a aba
  })
}
