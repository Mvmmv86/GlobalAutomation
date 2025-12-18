/**
 * Indicator Alerts Hook
 * React Query hooks for managing indicator alerts
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  indicatorAlertsService,
  IndicatorAlert,
  CreateAlertData,
  UpdateAlertData,
  IndicatorType,
  AvailableIndicators,
  AlertHistoryEntry
} from '@/services/indicatorAlertsService'
import { toast } from 'sonner'

// Query keys
const QUERY_KEYS = {
  alerts: ['indicator-alerts'] as const,
  alert: (id: string) => ['indicator-alerts', id] as const,
  history: (id: string) => ['indicator-alerts', id, 'history'] as const,
  availableIndicators: ['indicator-alerts', 'available-indicators'] as const
}

/**
 * Hook to fetch all indicator alerts
 */
export function useIndicatorAlerts(filters?: {
  indicator_type?: IndicatorType
  symbol?: string
  active_only?: boolean
}) {
  return useQuery<IndicatorAlert[]>({
    queryKey: [...QUERY_KEYS.alerts, filters],
    queryFn: () => indicatorAlertsService.getAlerts(filters),
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Hook to fetch a specific alert
 */
export function useIndicatorAlert(alertId: string | undefined) {
  return useQuery<IndicatorAlert | null>({
    queryKey: QUERY_KEYS.alert(alertId || ''),
    queryFn: () => alertId ? indicatorAlertsService.getAlertById(alertId) : null,
    enabled: !!alertId,
  })
}

/**
 * Hook to fetch alert trigger history
 */
export function useAlertHistory(alertId: string | undefined, limit: number = 50) {
  return useQuery<AlertHistoryEntry[]>({
    queryKey: QUERY_KEYS.history(alertId || ''),
    queryFn: () => alertId ? indicatorAlertsService.getAlertHistory(alertId, limit) : [],
    enabled: !!alertId,
  })
}

/**
 * Hook to fetch available indicators metadata
 */
export function useAvailableIndicators() {
  return useQuery<AvailableIndicators>({
    queryKey: QUERY_KEYS.availableIndicators,
    queryFn: () => indicatorAlertsService.getAvailableIndicators(),
    staleTime: 5 * 60 * 1000, // 5 minutes (metadata rarely changes)
  })
}

/**
 * Hook to create a new alert
 */
export function useCreateAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateAlertData) => indicatorAlertsService.createAlert(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts })
      toast.success('Alerta criado com sucesso')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Falha ao criar alerta')
    }
  })
}

/**
 * Hook to update an alert
 */
export function useUpdateAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ alertId, data }: { alertId: string; data: UpdateAlertData }) =>
      indicatorAlertsService.updateAlert(alertId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alert(variables.alertId) })
      toast.success('Alerta atualizado com sucesso')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Falha ao atualizar alerta')
    }
  })
}

/**
 * Hook to delete an alert
 */
export function useDeleteAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (alertId: string) => indicatorAlertsService.deleteAlert(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts })
      toast.success('Alerta excluído com sucesso')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Falha ao excluir alerta')
    }
  })
}

/**
 * Hook to toggle alert active state
 */
export function useToggleAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (alertId: string) => indicatorAlertsService.toggleAlert(alertId),
    onSuccess: (result, alertId) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alerts })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.alert(alertId) })
      toast.success(result.is_active ? 'Alerta ativado' : 'Alerta desativado')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Falha ao alternar alerta')
    }
  })
}

// Utility functions for UI

export const INDICATOR_LABELS: Record<IndicatorType, string> = {
  nadaraya_watson: 'Nadaraya-Watson Envelope',
  tpo: 'TPO (Market Profile)',
  rsi: 'RSI',
  macd: 'MACD',
  bollinger: 'Bollinger Bands',
  ema_cross: 'EMA Crossover',
  volume_profile: 'Volume Profile',
  custom: 'Custom'
}

export const SIGNAL_LABELS = {
  buy: 'Somente COMPRA',
  sell: 'Somente VENDA',
  both: 'COMPRA & VENDA'
}

export const SOUND_LABELS: Record<string, string> = {
  default: 'Padrão (Acorde)',
  bell: 'Sino',
  chime: 'Carrilhão',
  alert: 'Alarme (Urgente)',
  cash: 'Dinheiro',
  success: 'Sucesso',
  notification: 'Notificação',
  none: 'Sem Som'
}

export const TIMEFRAME_LABELS: Record<string, string> = {
  '1m': '1 Minuto',
  '3m': '3 Minutos',
  '5m': '5 Minutos',
  '15m': '15 Minutos',
  '30m': '30 Minutos',
  '1h': '1 Hora',
  '2h': '2 Horas',
  '4h': '4 Horas',
  '6h': '6 Horas',
  '8h': '8 Horas',
  '12h': '12 Horas',
  '1d': '1 Dia',
  '3d': '3 Dias',
  '1w': '1 Semana',
  '1M': '1 Mês'
}
