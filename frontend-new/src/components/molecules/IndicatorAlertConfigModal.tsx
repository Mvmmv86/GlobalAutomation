/**
 * IndicatorAlertConfigModal - Modal for configuring indicator signal alerts
 * Allows users to set up alerts for BUY/SELL signals from indicators
 */

import React, { useState, useEffect } from 'react'
import { X, Bell, BellOff, Mail, Volume2, Clock, Check, Trash2, History, Play } from 'lucide-react'
import {
  useIndicatorAlerts,
  useCreateAlert,
  useUpdateAlert,
  useDeleteAlert,
  useToggleAlert,
  SIGNAL_LABELS,
  SOUND_LABELS,
  TIMEFRAME_LABELS
} from '@/hooks/useIndicatorAlerts'
import {
  IndicatorType,
  SignalType,
  AlertTimeframe,
  AlertSoundType,
  IndicatorAlert
} from '@/services/indicatorAlertsService'
import { playAlertSound, AlertSoundType as SoundServiceType } from '@/services/alertSoundService'

interface IndicatorAlertConfigModalProps {
  isOpen: boolean
  onClose: () => void
  indicatorType: string  // e.g., 'NWENVELOPE', 'RSI', 'MACD'
  indicatorName: string  // Display name
  symbol: string         // e.g., 'BTCUSDT'
  currentTimeframe: string  // Current chart timeframe
}

// Map frontend indicator types to backend types
const INDICATOR_TYPE_MAP: Record<string, IndicatorType> = {
  'NWENVELOPE': 'nadaraya_watson',
  'TPO': 'tpo',
  'RSI': 'rsi',
  'MACD': 'macd',
  'BB': 'bollinger',
  'EMA': 'ema_cross',
  'VP': 'volume_profile'
}

const TIMEFRAMES: AlertTimeframe[] = [
  '1m', '3m', '5m', '15m', '30m',
  '1h', '2h', '4h', '6h', '8h', '12h',
  '1d', '3d', '1w', '1M'
]

const SOUNDS: AlertSoundType[] = [
  'default', 'bell', 'chime', 'alert', 'notification', 'none'
]

// Map backend sound types to frontend service sound types
const mapSoundType = (type: AlertSoundType): SoundServiceType => {
  const mapping: Record<string, SoundServiceType> = {
    'default': 'default',
    'bell': 'bell',
    'chime': 'chime',
    'alert': 'alarm',  // Map 'alert' to 'alarm' sound file
    'notification': 'notification',
    'none': 'none'
  }
  return mapping[type] || 'default'
}

export const IndicatorAlertConfigModal: React.FC<IndicatorAlertConfigModalProps> = ({
  isOpen,
  onClose,
  indicatorType,
  indicatorName,
  symbol,
  currentTimeframe
}) => {
  // Map to backend indicator type
  const backendIndicatorType = INDICATOR_TYPE_MAP[indicatorType] || 'custom'

  // Fetch existing alerts for this indicator/symbol
  const { data: existingAlerts, isLoading } = useIndicatorAlerts({
    indicator_type: backendIndicatorType as IndicatorType,
    symbol: symbol
  })

  // Mutations
  const createAlert = useCreateAlert()
  const updateAlert = useUpdateAlert()
  const deleteAlert = useDeleteAlert()
  const toggleAlert = useToggleAlert()

  // Form state
  const [signalType, setSignalType] = useState<SignalType>('both')
  const [timeframe, setTimeframe] = useState<AlertTimeframe>(currentTimeframe as AlertTimeframe || '1h')
  const [messageTemplate, setMessageTemplate] = useState('')
  const [pushEnabled, setPushEnabled] = useState(true)
  const [emailEnabled, setEmailEnabled] = useState(false)
  const [soundType, setSoundType] = useState<AlertSoundType>('default')
  const [cooldownMinutes, setCooldownMinutes] = useState(5)

  // Find existing alert for current timeframe
  const existingAlert = existingAlerts?.find(a => a.timeframe === timeframe)

  // Load existing alert settings if present
  useEffect(() => {
    if (existingAlert) {
      setSignalType(existingAlert.signal_type as SignalType)
      setMessageTemplate(existingAlert.message_template || '')
      setPushEnabled(existingAlert.push_enabled)
      setEmailEnabled(existingAlert.email_enabled)
      setSoundType(existingAlert.sound_type as AlertSoundType)
      setCooldownMinutes(Math.round(existingAlert.cooldown_seconds / 60))
    } else {
      // Reset to defaults
      setSignalType('both')
      setMessageTemplate('')
      setPushEnabled(true)
      setEmailEnabled(false)
      setSoundType('default')
      setCooldownMinutes(5)
    }
  }, [existingAlert, timeframe])

  const handleSave = async () => {
    if (existingAlert) {
      // Update existing alert
      await updateAlert.mutateAsync({
        alertId: existingAlert.id,
        data: {
          signal_type: signalType,
          message_template: messageTemplate || undefined,
          push_enabled: pushEnabled,
          email_enabled: emailEnabled,
          sound_type: soundType,
          cooldown_seconds: cooldownMinutes * 60
        }
      })
    } else {
      // Create new alert
      await createAlert.mutateAsync({
        indicator_type: backendIndicatorType as IndicatorType,
        symbol: symbol,
        timeframe: timeframe,
        signal_type: signalType,
        message_template: messageTemplate || undefined,
        push_enabled: pushEnabled,
        email_enabled: emailEnabled,
        sound_type: soundType,
        cooldown_seconds: cooldownMinutes * 60
      })
    }
  }

  const handleDelete = async () => {
    if (existingAlert && confirm('Tem certeza que deseja excluir este alerta?')) {
      await deleteAlert.mutateAsync(existingAlert.id)
    }
  }

  const handleToggle = async () => {
    if (existingAlert) {
      await toggleAlert.mutateAsync(existingAlert.id)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800/50">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-yellow-500" />
            <div>
              <h2 className="text-lg font-semibold text-white">
                Configurar Alerta
              </h2>
              <p className="text-xs text-gray-400">
                {indicatorName} - {symbol}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh] space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            </div>
          ) : (
            <>
              {/* Existing Alerts Summary */}
              {existingAlerts && existingAlerts.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-medium text-gray-400">Alertas Ativos</h3>
                  <div className="flex flex-wrap gap-2">
                    {existingAlerts.map(alert => (
                      <button
                        key={alert.id}
                        onClick={() => setTimeframe(alert.timeframe as AlertTimeframe)}
                        className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 transition-colors ${
                          timeframe === alert.timeframe
                            ? 'bg-blue-600 text-white'
                            : alert.is_active
                              ? 'bg-green-600/20 text-green-400 border border-green-600/30'
                              : 'bg-gray-700/50 text-gray-400'
                        }`}
                      >
                        {alert.is_active ? <Bell className="w-3 h-3" /> : <BellOff className="w-3 h-3" />}
                        {alert.timeframe}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Timeframe Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">
                  Timeframe para Monitorar
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value as AlertTimeframe)}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                >
                  {TIMEFRAMES.map(tf => (
                    <option key={tf} value={tf}>
                      {TIMEFRAME_LABELS[tf] || tf}
                    </option>
                  ))}
                </select>
              </div>

              {/* Signal Type */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">
                  Tipo de Sinal
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(['buy', 'sell', 'both'] as SignalType[]).map(type => (
                    <button
                      key={type}
                      onClick={() => setSignalType(type)}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        signalType === type
                          ? type === 'buy'
                            ? 'bg-green-600 text-white'
                            : type === 'sell'
                              ? 'bg-red-600 text-white'
                              : 'bg-blue-600 text-white'
                          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                      }`}
                    >
                      {SIGNAL_LABELS[type]}
                    </button>
                  ))}
                </div>
              </div>

              {/* Message Template */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">
                  Mensagem da Notificação (Opcional)
                </label>
                <input
                  type="text"
                  value={messageTemplate}
                  onChange={(e) => setMessageTemplate(e.target.value)}
                  placeholder="Sinal {signal_type} para {symbol} em {timeframe}"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:border-blue-500 focus:outline-none"
                />
                <p className="text-xs text-gray-500">
                  Variáveis disponíveis: {'{signal_type}'}, {'{symbol}'}, {'{timeframe}'}, {'{price}'}
                </p>
              </div>

              {/* Notification Channels */}
              <div className="space-y-3">
                <label className="text-sm font-medium text-gray-300">
                  Canais de Notificação
                </label>

                {/* Push Notifications */}
                <label className="flex items-center justify-between p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700/70 transition-colors">
                  <div className="flex items-center gap-3">
                    <Bell className="w-5 h-5 text-blue-400" />
                    <div>
                      <span className="text-sm text-white">Notificações Push</span>
                      <p className="text-xs text-gray-500">Notificações no app</p>
                    </div>
                  </div>
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={pushEnabled}
                      onChange={(e) => setPushEnabled(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-5 bg-gray-600 rounded-full peer peer-checked:bg-blue-600 transition-colors" />
                    <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                  </div>
                </label>

                {/* Email Notifications */}
                <label className="flex items-center justify-between p-3 bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-700/70 transition-colors">
                  <div className="flex items-center gap-3">
                    <Mail className="w-5 h-5 text-purple-400" />
                    <div>
                      <span className="text-sm text-white">Notificações por Email</span>
                      <p className="text-xs text-gray-500">Em breve</p>
                    </div>
                  </div>
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={emailEnabled}
                      onChange={(e) => setEmailEnabled(e.target.checked)}
                      className="sr-only peer"
                      disabled
                    />
                    <div className="w-10 h-5 bg-gray-600 rounded-full peer peer-checked:bg-purple-600 transition-colors opacity-50" />
                    <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5 opacity-50" />
                  </div>
                </label>
              </div>

              {/* Sound Selection */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-medium text-gray-300">
                  <Volume2 className="w-4 h-4" />
                  Som do Alerta
                </label>
                <div className="flex gap-2">
                  <select
                    value={soundType}
                    onChange={(e) => setSoundType(e.target.value as AlertSoundType)}
                    className="flex-1 px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
                  >
                    {SOUNDS.map(sound => (
                      <option key={sound} value={sound}>
                        {SOUND_LABELS[sound] || sound}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => playAlertSound(mapSoundType(soundType), 0.5)}
                    disabled={soundType === 'none'}
                    className="px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                    title="Ouvir som"
                  >
                    <Play className="w-4 h-4 text-white" />
                  </button>
                </div>
              </div>

              {/* Cooldown */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-medium text-gray-300">
                  <Clock className="w-4 h-4" />
                  Intervalo: {cooldownMinutes} minutos
                </label>
                <input
                  type="range"
                  min="1"
                  max="60"
                  value={cooldownMinutes}
                  onChange={(e) => setCooldownMinutes(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>1 min</span>
                  <span>Evita alertas repetidos para o mesmo sinal</span>
                  <span>60 min</span>
                </div>
              </div>

              {/* Alert Stats */}
              {existingAlert && (
                <div className="p-3 bg-gray-800/50 rounded-lg space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Vezes Disparado:</span>
                    <span className="text-white font-medium">{existingAlert.trigger_count}</span>
                  </div>
                  {existingAlert.last_triggered_at && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">Último Disparo:</span>
                      <span className="text-white font-medium">
                        {new Date(existingAlert.last_triggered_at).toLocaleString('pt-BR')}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-700 bg-gray-800/30">
          <div className="flex items-center gap-2">
            {existingAlert && (
              <>
                <button
                  onClick={handleToggle}
                  disabled={toggleAlert.isPending}
                  className={`flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors ${
                    existingAlert.is_active
                      ? 'text-yellow-400 hover:bg-yellow-400/10'
                      : 'text-green-400 hover:bg-green-400/10'
                  }`}
                >
                  {existingAlert.is_active ? (
                    <>
                      <BellOff className="w-4 h-4" />
                      Desativar
                    </>
                  ) : (
                    <>
                      <Bell className="w-4 h-4" />
                      Ativar
                    </>
                  )}
                </button>
                <button
                  onClick={handleDelete}
                  disabled={deleteAlert.isPending}
                  className="flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  Excluir
                </button>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              disabled={createAlert.isPending || updateAlert.isPending}
              className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors disabled:opacity-50"
            >
              <Check className="w-4 h-4" />
              {existingAlert ? 'Atualizar Alerta' : 'Criar Alerta'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default IndicatorAlertConfigModal
