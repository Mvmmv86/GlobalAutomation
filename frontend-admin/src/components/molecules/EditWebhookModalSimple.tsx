import React, { useState, useEffect } from 'react'
import { Edit, Eye, EyeOff, Copy, AlertCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { FormField } from './FormField'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../atoms/Select'
import { useExchangeAccounts } from '@/hooks/useExchangeAccounts'

interface EditWebhookModalSimpleProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (webhookId: string, data: WebhookEditData) => Promise<void>
  isLoading?: boolean
  webhook: WebhookEditData | null
}

export interface WebhookEditData {
  id: string
  name: string
  url_path: string
  exchange_account_id?: string
  status: 'active' | 'paused' | 'disabled' | 'error'
  market_type?: 'spot' | 'futures'
  secret?: string
}

/**
 * Modal simplificado para editar webhook - MVP FASE 1
 * Permite editar: name, status
 * Campos readonly: url_path, secret (por segurança)
 */
export const EditWebhookModalSimple: React.FC<EditWebhookModalSimpleProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
  webhook
}) => {
  const { data: exchangeAccounts, isLoading: loadingAccounts } = useExchangeAccounts()

  const [formData, setFormData] = useState<WebhookEditData>({
    id: '',
    name: '',
    url_path: '',
    exchange_account_id: '',
    status: 'active',
    market_type: 'spot',
    secret: ''
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [showSecret, setShowSecret] = useState(false)

  // Carregar dados do webhook quando modal abre
  useEffect(() => {
    if (webhook && isOpen) {
      setFormData({
        id: webhook.id,
        name: webhook.name,
        url_path: webhook.url_path,
        exchange_account_id: webhook.exchange_account_id || '',
        status: webhook.status,
        market_type: webhook.market_type || 'spot',
        secret: webhook.secret || ''
      })
    }
  }, [webhook, isOpen])

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Nome é obrigatório'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    try {
      await onSubmit(formData.id, {
        id: formData.id,
        name: formData.name,
        url_path: formData.url_path,
        status: formData.status,
        market_type: formData.market_type
      })
      handleClose()
    } catch (error) {
      console.error('Error updating webhook:', error)
    }
  }

  const handleInputChange = (field: keyof WebhookEditData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))

    // Limpar erro quando user começar a digitar
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }
  }

  const handleClose = () => {
    if (!isLoading) {
      setErrors({})
      onClose()
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    alert('Copiado para clipboard!')
  }

  const getWebhookUrl = () => {
    if (!formData.url_path) return ''
    // Usa URL pública do ngrok para webhooks, senão usa API_URL
    const baseUrl = import.meta.env.VITE_WEBHOOK_PUBLIC_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000'
    return `${baseUrl}/api/v1/webhooks/tradingview/${formData.url_path}`
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[550px]">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Edit className="w-5 h-5" />
            <span>Editar Webhook</span>
          </DialogTitle>
          <DialogDescription>
            Atualizar configurações do webhook
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

          {/* URL Path (readonly) */}
          <div>
            <label className="text-sm font-medium text-muted-foreground">URL Path (readonly)</label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                className="flex-1 px-3 py-2 border rounded-md bg-muted border-input cursor-not-allowed"
                value={formData.url_path}
                readOnly
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(getWebhookUrl())}
                title="Copiar URL completa"
              >
                <Copy className="w-4 h-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              URL path não pode ser alterado após criação
            </p>
          </div>

          {/* Exchange Account (readonly se já configurado) */}
          {formData.exchange_account_id && (
            <div>
              <label className="text-sm font-medium text-muted-foreground">Conta de Exchange (readonly)</label>
              <Select value={formData.exchange_account_id} disabled>
                <SelectTrigger className="bg-muted cursor-not-allowed">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {exchangeAccounts?.map((account: any) => (
                    <SelectItem key={account.id} value={account.id}>
                      {account.name} ({account.exchange})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground mt-1">
                Conta de exchange não pode ser alterada
              </p>
            </div>
          )}

          {/* Market Type */}
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
            <label className="text-sm font-medium">Status</label>
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
                <SelectItem value="disabled">Desabilitado</SelectItem>
                <SelectItem value="error">Erro</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              {formData.status === 'active' && '✅ Webhook está recebendo sinais'}
              {formData.status === 'paused' && '⏸️ Webhook está temporariamente pausado'}
              {formData.status === 'disabled' && '🚫 Webhook está desabilitado'}
              {formData.status === 'error' && '❌ Webhook em estado de erro'}
            </p>
          </div>

          {/* Secret Key (readonly) */}
          {formData.secret && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-muted-foreground">Secret Key (readonly)</label>
              <div className="relative">
                <input
                  type={showSecret ? 'text' : 'password'}
                  className="w-full px-3 py-2 border rounded-md pr-20 bg-muted border-input cursor-not-allowed"
                  value={formData.secret}
                  readOnly
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex space-x-1">
                  <button
                    type="button"
                    className="text-gray-500 hover:text-gray-700"
                    onClick={() => copyToClipboard(formData.secret || '')}
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    className="text-gray-500 hover:text-gray-700"
                    onClick={() => setShowSecret(!showSecret)}
                  >
                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Secret key não pode ser alterada por segurança
              </p>
            </div>
          )}

          {/* Info Warning */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <div className="flex">
              <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400 mr-2 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>Nota:</strong> Por segurança, URL path, conta de exchange e secret key não podem
                  ser alterados. Para mudar esses valores, crie um novo webhook.
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
              {isLoading ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
