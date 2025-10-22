import React, { useState, useEffect } from 'react'
import { X, Eye, EyeOff, AlertCircle, AlertTriangle, Copy, Check } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { FormField } from './FormField'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../atoms/Select'
import { Switch } from '../atoms/Switch'
import { useExchangeAccounts } from '@/hooks/useApiData'
import { ConfirmationModal } from './ConfirmationModal'

interface CreateExchangeAccountModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: ExchangeAccountData) => void
  isLoading?: boolean
  currentMainAccount?: { name: string; exchange: string } | null
}

export interface ExchangeAccountData {
  name: string
  exchange: string
  apiKey: string
  secretKey: string
  passphrase?: string
  testnet: boolean
  isDefault: boolean
}

const EXCHANGES = [
  { value: 'binance', label: 'Binance', requiresPassphrase: false },
  { value: 'bybit', label: 'Bybit', requiresPassphrase: false },
  { value: 'okx', label: 'OKX', requiresPassphrase: true },
  { value: 'coinbase', label: 'Coinbase Pro', requiresPassphrase: true },
  { value: 'bitget', label: 'Bitget', requiresPassphrase: false },
] as const

export const CreateExchangeAccountModal: React.FC<CreateExchangeAccountModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false
}) => {
  const { data: existingAccounts } = useExchangeAccounts()
  const [formData, setFormData] = useState<ExchangeAccountData>({
    name: '',
    exchange: '',
    apiKey: '',
    secretKey: '',
    passphrase: '',
    testnet: true,
    isDefault: false
  })

  const [showApiKey, setShowApiKey] = useState(false)
  const [showSecretKey, setShowSecretKey] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [showMainAccountWarning, setShowMainAccountWarning] = useState(false)
  const [currentMainAccount, setCurrentMainAccount] = useState<{ name: string; exchange: string } | null>(null)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [pendingSubmitData, setPendingSubmitData] = useState<ExchangeAccountData | null>(null)
  const [publicIPs, setPublicIPs] = useState<string[]>([])
  const [loadingIPs, setLoadingIPs] = useState(false)
  const [copiedIP, setCopiedIP] = useState<string | null>(null)

  const selectedExchange = EXCHANGES.find(ex => ex.value === formData.exchange)
  const requiresPassphrase = selectedExchange?.requiresPassphrase || false

  // Fetch public IPs when modal opens
  useEffect(() => {
    if (isOpen && publicIPs.length === 0) {
      fetchPublicIPs()
    }
  }, [isOpen])

  const fetchPublicIPs = async () => {
    setLoadingIPs(true)
    try {
      const baseUrl = import.meta.env.VITE_API_URL || ''
      const url = baseUrl ? `${baseUrl}/api/v1/health/public-ips` : '/api/v1/health/public-ips'

      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setPublicIPs(data.ips || [])
      }
    } catch (error) {
      console.error('Failed to fetch public IPs:', error)
      setPublicIPs(['Unable to detect - Please contact support'])
    } finally {
      setLoadingIPs(false)
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedIP(text)
      setTimeout(() => setCopiedIP(null), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const copyAllIPs = async () => {
    const ipsText = publicIPs.join('\n')
    await copyToClipboard(ipsText)
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Nome é obrigatório'
    }

    if (!formData.exchange) {
      newErrors.exchange = 'Selecione uma exchange'
    }

    if (!formData.apiKey.trim()) {
      newErrors.apiKey = 'API Key é obrigatória'
    }

    if (!formData.secretKey.trim()) {
      newErrors.secretKey = 'Secret Key é obrigatória'
    }

    if (requiresPassphrase && !formData.passphrase?.trim()) {
      newErrors.passphrase = 'Passphrase é obrigatória para esta exchange'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    // If there's a warning and user hasn't confirmed, show confirmation modal
    if (showMainAccountWarning && formData.isDefault && currentMainAccount) {
      setPendingSubmitData(formData)
      setShowConfirmModal(true)
      return
    }

    onSubmit(formData)
  }

  const handleConfirmSubmit = () => {
    if (pendingSubmitData) {
      onSubmit(pendingSubmitData)
      setPendingSubmitData(null)
    }
  }

  const handleInputChange = (field: keyof ExchangeAccountData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))

    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }

    // Check for existing main account when toggling isDefault
    if (field === 'isDefault' && value === true && formData.exchange) {
      const mainAccount = existingAccounts?.find(
        (acc: any) => acc.exchange === formData.exchange && acc.isMain === true
      )
      if (mainAccount) {
        setCurrentMainAccount({ name: mainAccount.name, exchange: mainAccount.exchange })
        setShowMainAccountWarning(true)
      } else {
        setShowMainAccountWarning(false)
      }
    }

    // Also check when exchange changes and isDefault is already true
    if (field === 'exchange' && formData.isDefault) {
      const mainAccount = existingAccounts?.find(
        (acc: any) => acc.exchange === value && acc.isMain === true
      )
      if (mainAccount) {
        setCurrentMainAccount({ name: mainAccount.name, exchange: mainAccount.exchange })
        setShowMainAccountWarning(true)
      } else {
        setShowMainAccountWarning(false)
      }
    }

    if (field === 'isDefault' && value === false) {
      setShowMainAccountWarning(false)
    }
  }

  const handleClose = () => {
    if (!isLoading) {
      setFormData({
        name: '',
        exchange: '',
        apiKey: '',
        secretKey: '',
        passphrase: '',
        testnet: true,
        isDefault: false
      })
      setErrors({})
      setShowApiKey(false)
      setShowSecretKey(false)
      onClose()
    }
  }

  return (
    <>
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Nova Conta de Exchange</DialogTitle>
          <DialogDescription>
            Configure uma nova conta de exchange para começar a fazer trading
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Nome da conta */}
          <FormField
            label="Nome da Conta"
            placeholder="Ex: Binance Principal"
            value={formData.name}
            onChange={(e) => handleInputChange('name', e.target.value)}
            error={errors.name}
            required
          />

          {/* Exchange */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Exchange *</label>
            <Select value={formData.exchange} onValueChange={(value) => handleInputChange('exchange', value)}>
              <SelectTrigger className={errors.exchange ? 'border-destructive' : ''}>
                <SelectValue placeholder="Selecione uma exchange" />
              </SelectTrigger>
              <SelectContent>
                {EXCHANGES.map((exchange) => (
                  <SelectItem key={exchange.value} value={exchange.value}>
                    {exchange.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.exchange && <p className="text-sm text-destructive">{errors.exchange}</p>}
          </div>

          {/* API Key */}
          <div className="space-y-2">
            <label className="text-sm font-medium">API Key *</label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                className={`w-full px-3 py-2 border rounded-md pr-10 ${
                  errors.apiKey ? 'border-destructive' : 'border-input'
                }`}
                placeholder="Sua API Key"
                value={formData.apiKey}
                onChange={(e) => handleInputChange('apiKey', e.target.value)}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.apiKey && <p className="text-sm text-destructive">{errors.apiKey}</p>}
          </div>

          {/* Secret Key */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Secret Key *</label>
            <div className="relative">
              <input
                type={showSecretKey ? 'text' : 'password'}
                className={`w-full px-3 py-2 border rounded-md pr-10 ${
                  errors.secretKey ? 'border-destructive' : 'border-input'
                }`}
                placeholder="Sua Secret Key"
                value={formData.secretKey}
                onChange={(e) => handleInputChange('secretKey', e.target.value)}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                onClick={() => setShowSecretKey(!showSecretKey)}
              >
                {showSecretKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.secretKey && <p className="text-sm text-destructive">{errors.secretKey}</p>}
          </div>

          {/* Passphrase (condicional) */}
          {requiresPassphrase && (
            <FormField
              label="Passphrase"
              placeholder="Passphrase da API"
              value={formData.passphrase || ''}
              onChange={(e) => handleInputChange('passphrase', e.target.value)}
              error={errors.passphrase}
              required
              hint="Obrigatório para esta exchange"
            />
          )}

          {/* Switches */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Testnet</label>
                <p className="text-xs text-gray-500">Usar ambiente de teste</p>
              </div>
              <Switch
                checked={formData.testnet}
                onCheckedChange={(checked) => handleInputChange('testnet', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Conta Principal</label>
                <p className="text-xs text-gray-500">Usar como conta principal para o dashboard</p>
              </div>
              <Switch
                checked={formData.isDefault}
                onCheckedChange={(checked) => handleInputChange('isDefault', checked)}
              />
            </div>

            {/* Warning about existing main account */}
            {showMainAccountWarning && currentMainAccount && (
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                <div className="flex">
                  <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mr-2 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-amber-800 dark:text-amber-200">
                      <strong>Atenção:</strong> A conta "{currentMainAccount.name}" já está definida como principal para {currentMainAccount.exchange}.
                      Ao criar esta conta como principal, ela substituirá a conta existente.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Security Warning & IP Information */}
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 space-y-3">
            <div className="flex">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mr-2 mt-0.5 flex-shrink-0" />
              <div className="flex-1 space-y-3">
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  <strong>Importante:</strong> Suas chaves de API são criptografadas e armazenadas com segurança.
                  Recomendamos usar API Keys apenas com permissão de trading (sem withdraw).
                </p>

                {/* IP Whitelist for production (non-testnet) */}
                {formData.exchange && !formData.testnet && (
                  <div className="space-y-2 pt-2 border-t border-yellow-200 dark:border-yellow-700">
                    <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                      📍 Configure estes IPs na {selectedExchange?.label}:
                    </p>
                    {loadingIPs ? (
                      <div className="text-xs text-yellow-700 dark:text-yellow-300">
                        Carregando IPs...
                      </div>
                    ) : (
                      <>
                        <div className="space-y-1">
                          {publicIPs.map((ip, index) => (
                            <div
                              key={index}
                              className="flex items-center justify-between bg-white dark:bg-gray-800 rounded px-2 py-1.5 text-xs"
                            >
                              <code className="font-mono text-gray-900 dark:text-gray-100">
                                {ip}
                              </code>
                              <button
                                type="button"
                                onClick={() => copyToClipboard(ip)}
                                className="text-yellow-600 dark:text-yellow-400 hover:text-yellow-800 dark:hover:text-yellow-200 p-1"
                                title="Copiar IP"
                              >
                                {copiedIP === ip ? (
                                  <Check className="w-3 h-3" />
                                ) : (
                                  <Copy className="w-3 h-3" />
                                )}
                              </button>
                            </div>
                          ))}
                        </div>
                        <p className="text-xs text-yellow-700 dark:text-yellow-300">
                          💡 Na {selectedExchange?.label}: API Management → Edit Restrictions → Restrict access to trusted IPs
                        </p>
                      </>
                    )}
                  </div>
                )}
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
              {isLoading ? 'Criando...' : 'Criar Conta'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>

    {/* Modal de confirmação para substituir conta principal */}
    <ConfirmationModal
      isOpen={showConfirmModal}
      onClose={() => setShowConfirmModal(false)}
      onConfirm={handleConfirmSubmit}
      title="Substituir Conta Principal?"
      message={`A conta "${currentMainAccount?.name}" atualmente está definida como principal para ${currentMainAccount?.exchange}. Ao criar esta nova conta como principal, ela substituirá a conta existente. Deseja continuar?`}
      confirmText="Sim, Substituir"
      cancelText="Cancelar"
      variant="warning"
    />
    </>
  )
}