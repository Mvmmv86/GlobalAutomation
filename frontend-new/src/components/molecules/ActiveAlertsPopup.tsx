import React, { useState } from 'react'
import { AlertTriangle, BellOff, X, Settings, Trash2, Volume2, VolumeX, Bell } from 'lucide-react'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { useIndicatorAlerts, useToggleAlert, useDeleteAlert, INDICATOR_LABELS, SIGNAL_LABELS, TIMEFRAME_LABELS } from '@/hooks/useIndicatorAlerts'
import { IndicatorAlertConfigModal } from './IndicatorAlertConfigModal'
import { cn } from '@/lib/utils'

interface ActiveAlertsPopupProps {
  isOpen: boolean
  onClose: () => void
  symbol?: string
  indicatorType?: string
}

export const ActiveAlertsPopup: React.FC<ActiveAlertsPopupProps> = ({
  isOpen,
  onClose,
  symbol,
  indicatorType
}) => {
  const { data: alertsData, isLoading } = useIndicatorAlerts({
    symbol,
    indicator_type: indicatorType as any
  })
  const toggleAlertMutation = useToggleAlert()
  const deleteAlertMutation = useDeleteAlert()

  const [showConfigModal, setShowConfigModal] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  if (!isOpen) return null

  // Safe access to alerts array
  const alerts = alertsData ?? []
  const activeAlerts = alerts.filter(a => a.is_active)
  const inactiveAlerts = alerts.filter(a => !a.is_active)

  const handleDelete = async (alertId: string) => {
    setDeletingId(alertId)
    try {
      await deleteAlertMutation.mutateAsync(alertId)
    } finally {
      setDeletingId(null)
    }
  }

  const handleToggle = async (alertId: string) => {
    await toggleAlertMutation.mutateAsync(alertId)
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Popup */}
      <div className="absolute right-0 top-full mt-2 w-80 bg-background border rounded-lg shadow-xl z-50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b bg-muted/30">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <span className="font-semibold text-sm">Alertas de Indicadores</span>
            {activeAlerts.length > 0 && (
              <Badge variant="default" className="h-5 px-1.5 text-xs">
                {activeAlerts.length}
              </Badge>
            )}
          </div>
          <div className="flex items-center space-x-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setShowConfigModal(true)}
              title="Criar novo alerta"
            >
              <Settings className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={onClose}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="p-6 text-center">
              <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-sm text-muted-foreground mt-2">Carregando...</p>
            </div>
          ) : alerts.length === 0 ? (
            <div className="p-6 text-center">
              <BellOff className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Nenhum alerta configurado</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => setShowConfigModal(true)}
              >
                Criar Primeiro Alerta
              </Button>
            </div>
          ) : (
            <div className="divide-y">
              {/* Alertas Ativos */}
              {activeAlerts.length > 0 && (
                <div>
                  <div className="px-3 py-2 bg-success/10 border-b border-success/20">
                    <span className="text-xs font-medium text-success">Ativos ({activeAlerts.length})</span>
                  </div>
                  {activeAlerts.map(alert => (
                    <AlertItem
                      key={alert.id}
                      alert={alert}
                      onToggle={handleToggle}
                      onDelete={handleDelete}
                      isDeleting={deletingId === alert.id}
                    />
                  ))}
                </div>
              )}

              {/* Alertas Inativos */}
              {inactiveAlerts.length > 0 && (
                <div>
                  <div className="px-3 py-2 bg-muted/50 border-b">
                    <span className="text-xs font-medium text-muted-foreground">Inativos ({inactiveAlerts.length})</span>
                  </div>
                  {inactiveAlerts.map(alert => (
                    <AlertItem
                      key={alert.id}
                      alert={alert}
                      onToggle={handleToggle}
                      onDelete={handleDelete}
                      isDeleting={deletingId === alert.id}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {alerts.length > 0 && (
          <div className="p-2 border-t bg-muted/30">
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => setShowConfigModal(true)}
            >
              <AlertTriangle className="h-3.5 w-3.5 mr-2" />
              Criar Novo Alerta
            </Button>
          </div>
        )}
      </div>

      {/* Modal de Configuração */}
      <IndicatorAlertConfigModal
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        symbol={symbol}
        indicatorType={indicatorType as any}
      />
    </>
  )
}

// Componente de item de alerta
interface AlertItemProps {
  alert: any
  onToggle: (id: string) => void
  onDelete: (id: string) => void
  isDeleting: boolean
}

const AlertItem: React.FC<AlertItemProps> = ({ alert, onToggle, onDelete, isDeleting }) => {
  return (
    <div
      className={cn(
        "p-3 hover:bg-muted/50 transition-colors",
        !alert.is_active && "opacity-60"
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          {/* Symbol e Timeframe */}
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-sm">{alert.symbol}</span>
            <Badge variant="outline" className="text-[10px] h-4 px-1">
              {TIMEFRAME_LABELS[alert.timeframe] || alert.timeframe}
            </Badge>
          </div>

          {/* Indicador e Tipo de Sinal */}
          <div className="flex items-center space-x-2 mt-1">
            <span className="text-xs text-muted-foreground">
              {INDICATOR_LABELS[alert.indicator_type] || alert.indicator_type}
            </span>
            <span className="text-xs text-muted-foreground">•</span>
            <span className={cn(
              "text-xs",
              alert.signal_type === 'buy' && "text-success",
              alert.signal_type === 'sell' && "text-destructive",
              alert.signal_type === 'both' && "text-primary"
            )}>
              {SIGNAL_LABELS[alert.signal_type] || alert.signal_type}
            </span>
          </div>

          {/* Info adicional */}
          <div className="flex items-center space-x-2 mt-1 text-[10px] text-muted-foreground">
            {alert.push_enabled && <Volume2 className="h-3 w-3" />}
            {!alert.push_enabled && <VolumeX className="h-3 w-3" />}
            <span>Disparou {alert.trigger_count}x</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-1 ml-2">
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              "h-7 w-7",
              alert.is_active ? "text-success hover:text-success" : "text-muted-foreground"
            )}
            onClick={() => onToggle(alert.id)}
            title={alert.is_active ? "Desativar" : "Ativar"}
          >
            {alert.is_active ? (
              <Bell className="h-3.5 w-3.5" />
            ) : (
              <BellOff className="h-3.5 w-3.5" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive"
            onClick={() => onDelete(alert.id)}
            disabled={isDeleting}
            title="Excluir"
          >
            {isDeleting ? (
              <div className="h-3 w-3 border border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ActiveAlertsPopup
