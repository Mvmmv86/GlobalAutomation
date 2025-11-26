import React, { useState } from 'react'
import { Zap, Eye, EyeOff, Copy, AlertCircle, TrendingUp } from 'lucide-react'
import { Slider } from '../atoms/Slider'
import { Badge } from '../atoms/Badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { FormField } from './FormField'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../atoms/Select'
import { useExchangeAccounts } from '@/hooks/useExchangeAccounts'

interface CreateWebhookModalSimpleProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: WebhookSimpleData) => Promise<void>
  isLoading?: boolean
}

export interface WebhookSimpleData {
  name: string
  url_path: string
  exchange_account_id?: string  // Opcional - backend não usa atualmente
  status: 'active' | 'paused'
  market_type: 'spot' | 'futures'
  secret?: string
  // Trading parameters
  default_margin_usd?: number
  default_leverage?: number
  default_stop_loss_pct?: number
  default_take_profit_pct?: number
}

/**
 * Modal simplificado para criar webhook - MVP FASE 1
 * Apenas 4 campos essenciais: name, url_path, exchange_account_id, status
 */
export const CreateWebhookModalSimple: React.FC<CreateWebhookModalSimpleProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false
}) => {
  const { data: exchangeAccounts, isLoading: loadingAccounts } = useExchangeAccounts()

  const [formData, setFormData] = useState<WebhookSimpleData>({
    name: '',
    url_path: '',
    exchange_account_id: '',
    status: 'active',
    market_type: 'futures',  // Default: futures (usuário tem saldo em FUTURES)
    secret: '',
    // Trading parameters - valores padrão
    default_margin_usd: 100,
    default_leverage: 10,
    default_stop_loss_pct: 3,
    default_take_profit_pct: 5
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [showSecret, setShowSecret] = useState(false)
  const [generatedUrl, setGeneratedUrl] = useState<string>('')

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Nome é obrigatório'
    }

    if (!formData.url_path.trim()) {
      newErrors.url_path = 'URL path é obrigatório'
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.url_path)) {
      newErrors.url_path = 'URL path deve conter apenas letras, números, - ou _'
    }

    // Exchange account é opcional - backend cria webhook sem precisar de exchange account
    // if (!formData.exchange_account_id) {
    //   newErrors.exchange_account_id = 'Selecione uma conta de exchange'
    // }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const generateSecretKey = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    let result = ''
    for (let i = 0; i < 32; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    setFormData(prev => ({ ...prev, secret: result }))
  }

  const generateWebhookUrl = () => {
    if (!formData.url_path) return ''
    // Usa URL pública do ngrok para webhooks, senão usa API_URL
    const baseUrl = import.meta.env.VITE_WEBHOOK_PUBLIC_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const url = `${baseUrl}/api/v1/webhooks/tradingview/${formData.url_path}`
    setGeneratedUrl(url)
    return url
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    // Auto-gerar secret se não tiver
    if (!formData.secret) {
      generateSecretKey()
    }

    // Gerar URL preview
    generateWebhookUrl()

    try {
      await onSubmit(formData)
      handleClose()
    } catch (error) {
      console.error('Error creating webhook:', error)
    }
  }

  const handleInputChange = (field: keyof WebhookSimpleData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))

    // Limpar erro quando user começar a digitar
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }

    // Auto-gerar URL quando mudar url_path
    if (field === 'url_path') {
      // Usa URL pública do ngrok para webhooks, senão usa API_URL
      const baseUrl = import.meta.env.VITE_WEBHOOK_PUBLIC_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const url = `${baseUrl}/api/v1/webhooks/tradingview/${value}`
      setGeneratedUrl(url)
    }
  }

  const handleClose = () => {
    if (!isLoading) {
      // Reset form
      setFormData({
        name: '',
        url_path: '',
        exchange_account_id: '',
        status: 'active',
        market_type: 'futures',
        secret: '',
        default_margin_usd: 100,
        default_leverage: 10,
        default_stop_loss_pct: 3,
        default_take_profit_pct: 5
      })
      setErrors({})
      setGeneratedUrl('')
      onClose()
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    alert('Copiado para clipboard!')
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center space-x-2">
            <Zap className="w-5 h-5" />
            <span>Novo Webhook - MVP</span>
          </DialogTitle>
          <DialogDescription>
            Configure um webhook simples para receber sinais do TradingView
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 overflow-y-auto flex-1 pr-2 py-2">
          {/* Nome do Webhook */}
          <FormField
            label="Nome do Webhook"
            placeholder="Ex: Strategy MACD Bitcoin"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            error={errors.name}
            required
          />

          {/* URL Path */}
          <FormField
            label="URL Path (identificador único)"
            placeholder="Ex: btc-scalping-v1"
            value={formData.url_path}
            onChange={(e) => handleInputChange('url_path', e.target.value.toLowerCase())}
            error={errors.url_path}
            hint="Apenas letras, números, - ou _"
            required
          />

          {/* Exchange Account - OPCIONAL */}
          <div>
            <label className="text-sm font-medium">Conta de Exchange (opcional)</label>
            <Select
              value={formData.exchange_account_id}
              onValueChange={(value) => handleInputChange('exchange_account_id', value)}
            >
              <SelectTrigger className={errors.exchange_account_id ? 'border-destructive' : ''}>
                <SelectValue placeholder={loadingAccounts ? "Carregando contas..." : "Usar conta padrão"} />
              </SelectTrigger>
              <SelectContent>
                {exchangeAccounts && exchangeAccounts.length > 0 ? (
                  exchangeAccounts.map((account: any) => (
                    <SelectItem key={account.id} value={account.id}>
                      {account.name} ({account.exchange})
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="none" disabled>Nenhuma conta encontrada</SelectItem>
                )}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              Deixe vazio para usar a conta padrão do sistema
            </p>
            {errors.exchange_account_id && (
              <p className="text-sm text-destructive mt-1">{errors.exchange_account_id}</p>
            )}
          </div>

          {/* Market Type - NOVO CAMPO */}
          <div>
            <label className="text-sm font-medium">Tipo de Mercado</label>
            <Select
              value={formData.market_type}
              onValueChange={(value) => handleInputChange('market_type', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="spot">SPOT (Mercado à Vista)</SelectItem>
                <SelectItem value="futures">FUTURES (Contratos Futuros)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              {formData.market_type === 'futures'
                ? '⚡ FUTURES: Alavancagem disponível, margem isolada/cruzada'
                : '💰 SPOT: Compra/venda direta, sem alavancagem'}
            </p>
          </div>

          {/* Status */}
          <div>
            <label className="text-sm font-medium">Status Inicial</label>
            <Select
              value={formData.status}
              onValueChange={(value) => handleInputChange('status', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Ativo</SelectItem>
                <SelectItem value="paused">Pausado</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Secret Key (opcional - auto-gerada) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Secret Key (HMAC)</label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={generateSecretKey}
              >
                Gerar Nova
              </Button>
            </div>
            <div className="relative">
              <input
                type={showSecret ? 'text' : 'password'}
                className="w-full px-3 py-2 border rounded-md pr-10 border-input"
                placeholder="Auto-gerada ao criar"
                value={formData.secret}
                onChange={(e) => handleInputChange('secret', e.target.value)}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                onClick={() => setShowSecret(!showSecret)}
              >
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              Deixe vazio para gerar automaticamente
            </p>
          </div>

          {/* URL Preview */}
          {generatedUrl && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <h4 className="font-medium text-green-800 dark:text-green-200 mb-2 flex items-center">
                🎉 URL do Webhook (Preview)
              </h4>
              <div className="flex items-center space-x-2">
                <code className="flex-1 text-xs bg-background px-3 py-2 rounded border break-all">
                  {generatedUrl}
                </code>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(generatedUrl)}
                >
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Security Warning */}
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
            <div className="flex">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mr-2 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  <strong>Importante:</strong> Guarde sua secret key. Ela será usada para validar
                  os sinais do TradingView.
                </p>
              </div>
            </div>
          </div>

          {/* Trading Parameters Section */}
          <div className="border-t pt-4 space-y-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              <h3 className="text-lg font-semibold">Parâmetros de Trading</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Configure quanto investir por sinal e os níveis de risco
            </p>

            {/* Margin USD */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Margem por Ordem (USD)</label>
                <div className="flex items-center space-x-2">
                  <Badge variant="outline">${formData.default_margin_usd}</Badge>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <Slider
                  value={[formData.default_margin_usd || 100]}
                  onValueChange={(value) => handleInputChange('default_margin_usd', value[0])}
                  min={10}
                  max={1000}
                  step={10}
                  className="flex-1"
                />
                <input
                  type="number"
                  min="10"
                  max="10000"
                  step="10"
                  value={formData.default_margin_usd}
                  onChange={(e) => handleInputChange('default_margin_usd', Number(e.target.value))}
                  className="w-24 px-2 py-1 text-sm border rounded bg-white text-black"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Quanto você quer investir por cada sinal (mínimo: $10)
              </p>
            </div>

            {/* Leverage */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Alavancagem</label>
                <Badge variant="outline">{formData.default_leverage}x</Badge>
              </div>
              <div className="flex items-center space-x-3">
                <Slider
                  value={[formData.default_leverage || 10]}
                  onValueChange={(value) => handleInputChange('default_leverage', value[0])}
                  min={1}
                  max={125}
                  step={1}
                  className="flex-1"
                />
                <input
                  type="number"
                  min="1"
                  max="125"
                  step="1"
                  value={formData.default_leverage}
                  onChange={(e) => handleInputChange('default_leverage', Number(e.target.value))}
                  className="w-24 px-2 py-1 text-sm border rounded bg-white text-black"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Multiplicador da sua posição (1x - 125x). Tamanho real: ${((formData.default_margin_usd || 100) * (formData.default_leverage || 10)).toFixed(2)}
              </p>
            </div>

            {/* Stop Loss */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Stop Loss (%)</label>
                <Badge variant="destructive">{formData.default_stop_loss_pct}%</Badge>
              </div>
              <div className="flex items-center space-x-3">
                <Slider
                  value={[formData.default_stop_loss_pct || 3]}
                  onValueChange={(value) => handleInputChange('default_stop_loss_pct', value[0])}
                  min={0.1}
                  max={20}
                  step={0.1}
                  className="flex-1"
                />
                <input
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={formData.default_stop_loss_pct}
                  onChange={(e) => handleInputChange('default_stop_loss_pct', Number(e.target.value))}
                  className="w-24 px-2 py-1 text-sm border rounded bg-white text-black"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Limite máximo de perda por operação (0.1% - 100%)
              </p>
            </div>

            {/* Take Profit */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Take Profit (%)</label>
                <Badge variant="default" className="bg-green-600">{formData.default_take_profit_pct}%</Badge>
              </div>
              <div className="flex items-center space-x-3">
                <Slider
                  value={[formData.default_take_profit_pct || 5]}
                  onValueChange={(value) => handleInputChange('default_take_profit_pct', value[0])}
                  min={0.1}
                  max={50}
                  step={0.1}
                  className="flex-1"
                />
                <input
                  type="number"
                  min="0.1"
                  max="1000"
                  step="0.1"
                  value={formData.default_take_profit_pct}
                  onChange={(e) => handleInputChange('default_take_profit_pct', Number(e.target.value))}
                  className="w-24 px-2 py-1 text-sm border rounded bg-white text-black"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Alvo de lucro automático (0.1% - 1000%)
              </p>
            </div>

            {/* Summary Box */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h4 className="font-medium text-blue-800 dark:text-blue-200 mb-2">
                📊 Resumo da Configuração
              </h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Investimento:</span>
                  <span className="font-semibold ml-2">${formData.default_margin_usd}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Alavancagem:</span>
                  <span className="font-semibold ml-2">{formData.default_leverage}x</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Tamanho Posição:</span>
                  <span className="font-semibold ml-2 text-blue-600">
                    ${((formData.default_margin_usd || 100) * (formData.default_leverage || 10)).toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">SL / TP:</span>
                  <span className="font-semibold ml-2 text-red-600">-{formData.default_stop_loss_pct}%</span>
                  <span className="font-semibold ml-1 text-green-600">+{formData.default_take_profit_pct}%</span>
                </div>
              </div>
            </div>
          </div>
        </form>

        {/* Buttons - Fixed at bottom */}
        <div className="flex justify-end space-x-3 pt-4 border-t flex-shrink-0">
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
            disabled={isLoading}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            disabled={isLoading}
            onClick={async (e) => {
              e.preventDefault()
              await handleSubmit(e as any)
            }}
          >
            {isLoading ? 'Criando...' : 'Criar Webhook'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
