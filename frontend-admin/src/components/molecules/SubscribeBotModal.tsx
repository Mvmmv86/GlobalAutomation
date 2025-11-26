import React, { useState } from 'react'
import { X, TrendingUp, Shield, DollarSign, Settings } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { Bot, CreateSubscriptionData } from '@/services/botsService'

interface SubscribeBotModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateSubscriptionData) => Promise<void>
  bot: Bot | null
  exchangeAccounts: Array<{ id: string; name: string; exchange: string }>
  isLoading?: boolean
}

export const SubscribeBotModal: React.FC<SubscribeBotModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  bot,
  exchangeAccounts,
  isLoading = false
}) => {
  const [formData, setFormData] = useState<CreateSubscriptionData>({
    bot_id: bot?.id || '',
    exchange_account_id: '',
    custom_leverage: undefined,
    custom_margin_usd: undefined,
    custom_stop_loss_pct: undefined,
    custom_take_profit_pct: undefined,
    max_daily_loss_usd: 200.00,
    max_concurrent_positions: 3
  })

  const [useCustomSettings, setUseCustomSettings] = useState({
    leverage: false,
    margin: false,
    stopLoss: false,
    takeProfit: false
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.exchange_account_id) {
      alert('Por favor, selecione uma conta de exchange')
      return
    }

    // Remove custom fields if not using custom settings
    const dataToSubmit = {
      ...formData,
      bot_id: bot?.id || '',
      custom_leverage: useCustomSettings.leverage ? formData.custom_leverage : undefined,
      custom_margin_usd: useCustomSettings.margin ? formData.custom_margin_usd : undefined,
      custom_stop_loss_pct: useCustomSettings.stopLoss ? formData.custom_stop_loss_pct : undefined,
      custom_take_profit_pct: useCustomSettings.takeProfit ? formData.custom_take_profit_pct : undefined,
    }

    try {
      await onSubmit(dataToSubmit)
      onClose()
      // Reset form
      setFormData({
        bot_id: '',
        exchange_account_id: '',
        custom_leverage: undefined,
        custom_margin_usd: undefined,
        custom_stop_loss_pct: undefined,
        custom_take_profit_pct: undefined,
        max_daily_loss_usd: 200.00,
        max_concurrent_positions: 3
      })
      setUseCustomSettings({
        leverage: false,
        margin: false,
        stopLoss: false,
        takeProfit: false
      })
    } catch (error: any) {
      alert(error.message || 'Erro ao assinar bot')
    }
  }

  if (!bot) return null

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Configurar Bot: {bot.name}
            </DialogTitle>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              type="button"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            {bot.description}
          </p>
          <div className="flex items-center gap-2 mt-2">
            <Badge variant={bot.market_type === 'futures' ? 'default' : 'secondary'}>
              {bot.market_type === 'futures' ? '⚡ FUTURES' : '💰 SPOT'}
            </Badge>
            <Badge variant="outline">
              {bot.total_subscribers} assinantes
            </Badge>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6 mt-4">
          {/* Exchange Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Conta de Exchange *
            </label>
            <select
              value={formData.exchange_account_id}
              onChange={(e) => setFormData({ ...formData, exchange_account_id: e.target.value })}
              className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
              required
            >
              <option value="">Selecione uma conta...</option>
              {exchangeAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.exchange} - {account.name}
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              Escolha qual conta de exchange será usada para executar as ordens
            </p>
          </div>

          {/* Trading Settings */}
          <div className="border rounded-lg p-4 space-y-4">
            <h3 className="font-medium flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              Configurações de Trading
            </h3>

            {/* Leverage */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Alavancagem</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useCustomSettings.leverage}
                    onChange={(e) => setUseCustomSettings({ ...useCustomSettings, leverage: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {useCustomSettings.leverage ? (
                <input
                  type="number"
                  value={formData.custom_leverage || ''}
                  onChange={(e) => setFormData({ ...formData, custom_leverage: Number(e.target.value) })}
                  placeholder={`Padrão: ${bot.default_leverage}x`}
                  min="1"
                  max="125"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrão do bot: <span className="font-semibold">{bot.default_leverage}x</span>
                </div>
              )}
            </div>

            {/* Margin */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Margem por Operação (USD)</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useCustomSettings.margin}
                    onChange={(e) => setUseCustomSettings({ ...useCustomSettings, margin: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {useCustomSettings.margin ? (
                <input
                  type="number"
                  value={formData.custom_margin_usd || ''}
                  onChange={(e) => setFormData({ ...formData, custom_margin_usd: Number(e.target.value) })}
                  placeholder={`Padrão: $${bot.default_margin_usd}`}
                  min="5"
                  step="0.01"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrão do bot: <span className="font-semibold">${bot.default_margin_usd}</span>
                </div>
              )}
            </div>

            {/* Stop Loss */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Stop Loss (%)</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useCustomSettings.stopLoss}
                    onChange={(e) => setUseCustomSettings({ ...useCustomSettings, stopLoss: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {useCustomSettings.stopLoss ? (
                <input
                  type="number"
                  value={formData.custom_stop_loss_pct || ''}
                  onChange={(e) => setFormData({ ...formData, custom_stop_loss_pct: Number(e.target.value) })}
                  placeholder={`Padrão: ${bot.default_stop_loss_pct}%`}
                  min="0.1"
                  max="50"
                  step="0.1"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrão do bot: <span className="font-semibold">{bot.default_stop_loss_pct}%</span>
                </div>
              )}
            </div>

            {/* Take Profit */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Take Profit (%)</label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useCustomSettings.takeProfit}
                    onChange={(e) => setUseCustomSettings({ ...useCustomSettings, takeProfit: e.target.checked })}
                    className="rounded"
                  />
                  <span className="text-xs text-muted-foreground">Personalizar</span>
                </label>
              </div>
              {useCustomSettings.takeProfit ? (
                <input
                  type="number"
                  value={formData.custom_take_profit_pct || ''}
                  onChange={(e) => setFormData({ ...formData, custom_take_profit_pct: Number(e.target.value) })}
                  placeholder={`Padrão: ${bot.default_take_profit_pct}%`}
                  min="0.1"
                  max="100"
                  step="0.1"
                  className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                />
              ) : (
                <div className="px-3 py-2 bg-muted rounded-md text-sm">
                  Usando padrão do bot: <span className="font-semibold">{bot.default_take_profit_pct}%</span>
                </div>
              )}
            </div>
          </div>

          {/* Risk Management */}
          <div className="border rounded-lg p-4 space-y-4">
            <h3 className="font-medium flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Gestão de Risco
            </h3>

            <div className="space-y-2">
              <label className="text-sm font-medium">Perda Máxima Diária (USD) *</label>
              <input
                type="number"
                value={formData.max_daily_loss_usd}
                onChange={(e) => setFormData({ ...formData, max_daily_loss_usd: Number(e.target.value) })}
                min="10"
                step="0.01"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
              <p className="text-xs text-muted-foreground">
                Bot será pausado automaticamente se atingir esta perda no dia
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Máximo de Posições Simultâneas *</label>
              <input
                type="number"
                value={formData.max_concurrent_positions}
                onChange={(e) => setFormData({ ...formData, max_concurrent_positions: Number(e.target.value) })}
                min="1"
                max="10"
                className="w-full px-3 py-2 border border-input bg-background rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
                required
              />
              <p className="text-xs text-muted-foreground">
                Número máximo de operações abertas ao mesmo tempo
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Ativando...' : 'Ativar Bot'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
