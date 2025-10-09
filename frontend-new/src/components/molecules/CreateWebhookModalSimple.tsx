import React, { useState } from 'react'
import { Zap, Eye, EyeOff, Copy, AlertCircle } from 'lucide-react'
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
  exchange_account_id: string
  status: 'active' | 'paused'
  secret?: string
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
    secret: ''
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

    if (!formData.exchange_account_id) {
      newErrors.exchange_account_id = 'Selecione uma conta de exchange'
    }

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
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
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
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
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
        secret: ''
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
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Zap className="w-5 h-5" />
            <span>Novo Webhook - MVP</span>
          </DialogTitle>
          <DialogDescription>
            Configure um webhook simples para receber sinais do TradingView
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
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

          {/* Exchange Account */}
          <div>
            <label className="text-sm font-medium">Conta de Exchange *</label>
            <Select
              value={formData.exchange_account_id}
              onValueChange={(value) => handleInputChange('exchange_account_id', value)}
            >
              <SelectTrigger className={errors.exchange_account_id ? 'border-destructive' : ''}>
                <SelectValue placeholder={loadingAccounts ? "Carregando contas..." : "Selecione uma conta"} />
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
            {errors.exchange_account_id && (
              <p className="text-sm text-destructive mt-1">{errors.exchange_account_id}</p>
            )}
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

          {/* Buttons */}
          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Criando...' : 'Criar Webhook'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
