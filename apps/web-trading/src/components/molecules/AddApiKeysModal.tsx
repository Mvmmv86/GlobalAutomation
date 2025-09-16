import React, { useState, useEffect } from 'react'
import { Eye, EyeOff, Key, Shield, Copy, Check, Globe } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { FormField } from './FormField'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Badge } from '../atoms/Badge'

interface AddApiKeysModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: ApiKeysData) => void
  accountId: string
  accountName: string
  exchange: string
  isLoading?: boolean
}

export interface ApiKeysData {
  api_key: string
  secret_key: string
  passphrase?: string // For exchanges like Bitget
}

interface ServerIPs {
  local_ips: string[]
  public_ip: string
  hostname: string
}

export const AddApiKeysModal: React.FC<AddApiKeysModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  accountId,
  accountName,
  exchange,
  isLoading = false
}) => {
  const [showApiKey, setShowApiKey] = useState(false)
  const [showSecretKey, setShowSecretKey] = useState(false)
  const [copied, setCopied] = useState('')
  const [serverIPs, setServerIPs] = useState<ServerIPs | null>(null)
  const [loadingIPs, setLoadingIPs] = useState(false)
  
  const [formData, setFormData] = useState<ApiKeysData>({
    api_key: '',
    secret_key: '',
    passphrase: ''
  })

  // Load server IPs when modal opens
  useEffect(() => {
    if (isOpen && !serverIPs) {
      loadServerIPs()
    }
  }, [isOpen])

  const loadServerIPs = async () => {
    setLoadingIPs(true)
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/system/server-ips`)
      const result = await response.json()
      if (result.success) {
        setServerIPs(result.data)
      }
    } catch (error) {
      console.error('Failed to load server IPs:', error)
    } finally {
      setLoadingIPs(false)
    }
  }

  const handleInputChange = (field: keyof ApiKeysData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.api_key.trim() || !formData.secret_key.trim()) {
      alert('Por favor, preencha API Key e Secret Key')
      return
    }
    
    onSubmit(formData)
  }

  const copyToClipboard = async (text: string, type: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(type)
      setTimeout(() => setCopied(''), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const exchangeNeedsPassphrase = exchange === 'bitget'

  const getExchangeInstructions = () => {
    switch (exchange) {
      case 'binance':
        return {
          url: 'https://www.binance.com/en/my/settings/api-management',
          permissions: ['Enable Reading', 'Enable Spot & Margin Trading (opcional)', 'Enable Futures (se usar futuros)'],
          notes: 'Certifique-se de que a API key tem as permissões necessárias'
        }
      case 'bybit':
        return {
          url: 'https://www.bybit.com/app/user/api-management',
          permissions: ['Read-Write', 'Contract', 'Spot', 'Wallet'],
          notes: 'Configure as permissões de acordo com suas necessidades de trading'
        }
      case 'bitget':
        return {
          url: 'https://www.bitget.com/api-doc',
          permissions: ['Read', 'Trade', 'Futures'],
          notes: 'Bitget requer uma passphrase adicional'
        }
      case 'bingx':
        return {
          url: 'https://bingx.com/en-us/account/api',
          permissions: ['Read Info', 'Spot Trading', 'Standard Futures'],
          notes: 'Configure as permissões necessárias'
        }
      default:
        return {
          url: '#',
          permissions: ['Read', 'Trade'],
          notes: 'Verifique as permissões necessárias'
        }
    }
  }

  const instructions = getExchangeInstructions()

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Key className="w-5 h-5" />
            <span>Adicionar API Keys - {accountName}</span>
          </DialogTitle>
          <DialogDescription>
            Configure as credenciais para {exchange.toUpperCase()}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Server IPs Card */}
          <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
            <CardHeader>
              <CardTitle className="text-lg flex items-center space-x-2">
                <Globe className="w-5 h-5" />
                <span>IPs do Servidor</span>
              </CardTitle>
              <CardDescription>
                Configure estes IPs na sua exchange para permitir acesso
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {loadingIPs ? (
                <p className="text-sm text-muted-foreground">Carregando IPs...</p>
              ) : serverIPs ? (
                <>
                  <div className="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border">
                    <div>
                      <p className="font-medium text-sm">IP Público (Recomendado)</p>
                      <p className="font-mono text-lg">{serverIPs.public_ip}</p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(serverIPs.public_ip, 'public_ip')}
                    >
                      {copied === 'public_ip' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </Button>
                  </div>
                  
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
                    <p className="text-green-800 dark:text-green-200 text-sm">
                      ✅ <strong>Como configurar:</strong>
                    </p>
                    <ol className="text-green-700 dark:text-green-300 text-sm mt-2 ml-4 list-decimal space-y-1">
                      <li>Vá para <a href={instructions.url} target="_blank" rel="noopener noreferrer" className="underline">API Management da {exchange}</a></li>
                      <li>Adicione o IP <strong>{serverIPs.public_ip}</strong> na lista de IPs permitidos</li>
                      <li>Ou desative temporariamente a restrição de IP</li>
                    </ol>
                  </div>
                </>
              ) : (
                <p className="text-sm text-red-600">Erro ao carregar IPs do servidor</p>
              )}
            </CardContent>
          </Card>

          {/* API Credentials Form */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center space-x-2">
                <Shield className="w-5 h-5" />
                <span>Credenciais da API</span>
              </CardTitle>
              <CardDescription>
                Suas credenciais são criptografadas antes de serem salvas
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* API Key */}
              <div>
                <label className="text-sm font-medium">API Key *</label>
                <div className="relative">
                  <input
                    type={showApiKey ? "text" : "password"}
                    value={formData.api_key}
                    onChange={(e) => handleInputChange('api_key', e.target.value)}
                    placeholder="Cole sua API Key aqui"
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Secret Key */}
              <div>
                <label className="text-sm font-medium">Secret Key *</label>
                <div className="relative">
                  <input
                    type={showSecretKey ? "text" : "password"}
                    value={formData.secret_key}
                    onChange={(e) => handleInputChange('secret_key', e.target.value)}
                    placeholder="Cole sua Secret Key aqui"
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecretKey(!showSecretKey)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  >
                    {showSecretKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* Passphrase (if needed) */}
              {exchangeNeedsPassphrase && (
                <div>
                  <label className="text-sm font-medium">Passphrase *</label>
                  <input
                    type="text"
                    value={formData.passphrase || ''}
                    onChange={(e) => handleInputChange('passphrase', e.target.value)}
                    placeholder="Passphrase da API"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800"
                  />
                </div>
              )}

              {/* Permissions Info */}
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                <p className="font-medium text-sm text-yellow-800 dark:text-yellow-200 mb-2">
                  🔐 Permissões Necessárias:
                </p>
                <div className="flex flex-wrap gap-1">
                  {instructions.permissions.map((permission, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {permission}
                    </Badge>
                  ))}
                </div>
                <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-2">
                  {instructions.notes}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Footer */}
          <div className="flex justify-end space-x-3">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Salvando...' : 'Salvar e Testar'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}