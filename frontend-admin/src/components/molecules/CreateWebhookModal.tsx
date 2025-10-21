import React, { useState } from 'react'
import { Copy, AlertCircle, Zap, Eye, EyeOff } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { FormField } from './FormField'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../atoms/Select'
import { Switch } from '../atoms/Switch'
import { Badge } from '../atoms/Badge'

interface CreateWebhookModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: WebhookData) => void
  isLoading?: boolean
}

export interface WebhookData {
  name: string
  description: string
  exchangeAccountId: string
  strategy: string
  symbols: string[]
  status: 'active' | 'paused' | 'disabled'
  
  // Security
  enableAuth: boolean
  secretKey: string
  enableIPWhitelist: boolean
  allowedIPs: string[]
  
  // Signal Processing
  enableSignalValidation: boolean
  requiredFields: string[]
  enableDuplicateFilter: boolean
  duplicateWindowMs: number
  
  // Risk Management
  enableRiskLimits: boolean
  maxOrdersPerMinute: number
  maxDailyOrders: number
  minOrderSize: number
  maxOrderSize: number
  
  // Execution Settings
  executionDelay: number
  enableRetry: boolean
  maxRetries: number
  retryDelayMs: number
  
  // Logging & Notifications
  enableLogging: boolean
  enableNotifications: boolean
  notificationEmail: string
  
  // Advanced
  customHeaders: Record<string, string>
  timeoutMs: number
  enableRateLimit: boolean
  rateLimit: number
}

const STRATEGY_OPTIONS = [
  { value: 'scalping', label: 'Scalping', description: 'Operações rápidas em timeframes baixos' },
  { value: 'swing', label: 'Swing Trading', description: 'Operações de médio prazo' },
  { value: 'position', label: 'Position Trading', description: 'Operações de longo prazo' },
  { value: 'arbitrage', label: 'Arbitragem', description: 'Explorar diferenças de preço' },
  { value: 'grid', label: 'Grid Trading', description: 'Estratégia de grade' },
  { value: 'dca', label: 'DCA (Dollar Cost Average)', description: 'Média de custo' },
  { value: 'martingale', label: 'Martingale', description: 'Aumentar posição após perda' },
  { value: 'custom', label: 'Personalizada', description: 'Estratégia customizada' },
]

const POPULAR_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'LINKUSDT', 'ATOMUSDT']

const REQUIRED_FIELDS_OPTIONS = [
  'symbol', 'side', 'quantity', 'price', 'type', 'timestamp', 'strategy', 'leverage', 'stop_loss', 'take_profit'
]

export const CreateWebhookModal: React.FC<CreateWebhookModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false
}) => {
  const [formData, setFormData] = useState<WebhookData>({
    name: '',
    description: '',
    exchangeAccountId: '',
    strategy: 'scalping',
    symbols: ['BTCUSDT'],
    status: 'active',
    
    // Security
    enableAuth: true,
    secretKey: '',
    enableIPWhitelist: false,
    allowedIPs: [],
    
    // Signal Processing
    enableSignalValidation: true,
    requiredFields: ['symbol', 'side', 'quantity'],
    enableDuplicateFilter: true,
    duplicateWindowMs: 5000,
    
    // Risk Management
    enableRiskLimits: true,
    maxOrdersPerMinute: 10,
    maxDailyOrders: 500,
    minOrderSize: 10,
    maxOrderSize: 1000,
    
    // Execution Settings
    executionDelay: 100,
    enableRetry: true,
    maxRetries: 3,
    retryDelayMs: 1000,
    
    // Logging & Notifications
    enableLogging: true,
    enableNotifications: false,
    notificationEmail: '',
    
    // Advanced
    customHeaders: {},
    timeoutMs: 5000,
    enableRateLimit: true,
    rateLimit: 60
  })

  const [errors, setErrors] = useState<Record<string, string>>({})
  const [showSecretKey, setShowSecretKey] = useState(false)
  const [generatedUrl, setGeneratedUrl] = useState<string>('')

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = 'Nome é obrigatório'
    }

    if (!formData.exchangeAccountId) {
      newErrors.exchangeAccountId = 'Selecione uma conta de exchange'
    }

    if (formData.symbols.length === 0) {
      newErrors.symbols = 'Selecione pelo menos um símbolo'
    }

    if (formData.enableAuth && !formData.secretKey.trim()) {
      newErrors.secretKey = 'Secret Key é obrigatória quando autenticação está habilitada'
    }

    if (formData.enableNotifications && !formData.notificationEmail.trim()) {
      newErrors.notificationEmail = 'Email é obrigatório quando notificações estão habilitadas'
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
    setFormData(prev => ({ ...prev, secretKey: result }))
  }

  const generateWebhookUrl = () => {
    const webhookId = 'webhook_' + Math.random().toString(36).substring(2, 15)
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    const url = `${baseUrl}/webhooks/tradingview/${webhookId}`
    setGeneratedUrl(url)
    return webhookId
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    // Generate webhook ID and URL
    const webhookId = generateWebhookUrl()
    
    const webhookData = {
      ...formData,
      id: webhookId,
      urlPath: webhookId,
      totalDeliveries: 0,
      successfulDeliveries: 0,
      failedDeliveries: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }

    onSubmit(webhookData)
  }

  const handleInputChange = (field: keyof WebhookData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }))
    }
  }

  const toggleSymbol = (symbol: string) => {
    setFormData(prev => ({
      ...prev,
      symbols: prev.symbols.includes(symbol)
        ? prev.symbols.filter(s => s !== symbol)
        : [...prev.symbols, symbol]
    }))
  }

  const toggleRequiredField = (field: string) => {
    setFormData(prev => ({
      ...prev,
      requiredFields: prev.requiredFields.includes(field)
        ? prev.requiredFields.filter(f => f !== field)
        : [...prev.requiredFields, field]
    }))
  }

  const handleClose = () => {
    if (!isLoading) {
      setFormData({
        name: '',
        description: '',
        exchangeAccountId: '',
        strategy: 'scalping',
        symbols: ['BTCUSDT'],
        status: 'active',
        enableAuth: true,
        secretKey: '',
        enableIPWhitelist: false,
        allowedIPs: [],
        enableSignalValidation: true,
        requiredFields: ['symbol', 'side', 'quantity'],
        enableDuplicateFilter: true,
        duplicateWindowMs: 5000,
        enableRiskLimits: true,
        maxOrdersPerMinute: 10,
        maxDailyOrders: 500,
        minOrderSize: 10,
        maxOrderSize: 1000,
        executionDelay: 100,
        enableRetry: true,
        maxRetries: 3,
        retryDelayMs: 1000,
        enableLogging: true,
        enableNotifications: false,
        notificationEmail: '',
        customHeaders: {},
        timeoutMs: 5000,
        enableRateLimit: true,
        rateLimit: 60
      })
      setErrors({})
      setGeneratedUrl('')
      onClose()
    }
  }

  const copyUrlToClipboard = () => {
    if (generatedUrl) {
      navigator.clipboard.writeText(generatedUrl)
      alert('URL copiada para clipboard!')
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Zap className="w-5 h-5" />
            <span>Novo Webhook</span>
          </DialogTitle>
          <DialogDescription>
            Configure um novo webhook para receber sinais do TradingView
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Informações Básicas</h3>
            
            <FormField
              label="Nome do Webhook"
              placeholder="Ex: Strategy MACD Bitcoin"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              error={errors.name}
              required
            />

            <FormField
              label="Descrição"
              placeholder="Descrição da estratégia e objetivos"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              multiline
              rows={2}
            />

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Conta de Exchange *</label>
                <Select value={formData.exchangeAccountId} onValueChange={(value) => handleInputChange('exchangeAccountId', value)}>
                  <SelectTrigger className={errors.exchangeAccountId ? 'border-destructive' : ''}>
                    <SelectValue placeholder="Selecione uma conta" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="binance-main">Binance Main</SelectItem>
                    <SelectItem value="binance-testnet">Binance Testnet</SelectItem>
                    <SelectItem value="bybit-main">Bybit Main</SelectItem>
                  </SelectContent>
                </Select>
                {errors.exchangeAccountId && <p className="text-sm text-destructive">{errors.exchangeAccountId}</p>}
              </div>

              <div>
                <label className="text-sm font-medium">Estratégia</label>
                <Select value={formData.strategy} onValueChange={(value) => handleInputChange('strategy', value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STRATEGY_OPTIONS.map((strategy) => (
                      <SelectItem key={strategy.value} value={strategy.value}>
                        <div>
                          <div className="font-medium">{strategy.label}</div>
                          <div className="text-xs text-muted-foreground">{strategy.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Símbolos Suportados *</label>
              <div className="flex flex-wrap gap-2">
                {POPULAR_SYMBOLS.map((symbol) => (
                  <Badge
                    key={symbol}
                    variant={formData.symbols.includes(symbol) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleSymbol(symbol)}
                  >
                    {symbol}
                  </Badge>
                ))}
              </div>
              {errors.symbols && <p className="text-sm text-destructive mt-1">{errors.symbols}</p>}
            </div>
          </div>

          {/* Security Settings */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Segurança</h3>
            
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Autenticação por Secret Key</label>
                <p className="text-xs text-muted-foreground">Verificar assinatura HMAC dos sinais</p>
              </div>
              <Switch
                checked={formData.enableAuth}
                onCheckedChange={(checked) => handleInputChange('enableAuth', checked)}
              />
            </div>

            {formData.enableAuth && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Secret Key</label>
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
                    type={showSecretKey ? 'text' : 'password'}
                    className={`w-full px-3 py-2 border rounded-md pr-10 ${
                      errors.secretKey ? 'border-destructive' : 'border-input'
                    }`}
                    placeholder="Sua secret key para HMAC"
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
            )}
          </div>

          {/* Signal Processing */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Processamento de Sinais</h3>
            
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Validação de Sinais</label>
                <p className="text-xs text-muted-foreground">Verificar campos obrigatórios</p>
              </div>
              <Switch
                checked={formData.enableSignalValidation}
                onCheckedChange={(checked) => handleInputChange('enableSignalValidation', checked)}
              />
            </div>

            {formData.enableSignalValidation && (
              <div>
                <label className="text-sm font-medium mb-2 block">Campos Obrigatórios</label>
                <div className="flex flex-wrap gap-2">
                  {REQUIRED_FIELDS_OPTIONS.map((field) => (
                    <Badge
                      key={field}
                      variant={formData.requiredFields.includes(field) ? 'default' : 'outline'}
                      className="cursor-pointer"
                      onClick={() => toggleRequiredField(field)}
                    >
                      {field}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-sm font-medium">Filtro de Duplicatas</label>
                  <p className="text-xs text-muted-foreground">Ignorar sinais duplicados</p>
                </div>
                <Switch
                  checked={formData.enableDuplicateFilter}
                  onCheckedChange={(checked) => handleInputChange('enableDuplicateFilter', checked)}
                />
              </div>

              {formData.enableDuplicateFilter && (
                <FormField
                  label="Janela de Duplicata (ms)"
                  type="number"
                  value={formData.duplicateWindowMs.toString()}
                  onChange={(e) => handleInputChange('duplicateWindowMs', parseInt(e.target.value))}
                  placeholder="5000"
                  step="1000"
                  min="1000"
                />
              )}
            </div>
          </div>

          {/* Risk Management */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Gestão de Risco</h3>
            
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Limites de Risco</label>
                <p className="text-xs text-muted-foreground">Aplicar limites de segurança</p>
              </div>
              <Switch
                checked={formData.enableRiskLimits}
                onCheckedChange={(checked) => handleInputChange('enableRiskLimits', checked)}
              />
            </div>

            {formData.enableRiskLimits && (
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  label="Max Ordens/Minuto"
                  type="number"
                  value={formData.maxOrdersPerMinute.toString()}
                  onChange={(e) => handleInputChange('maxOrdersPerMinute', parseInt(e.target.value))}
                  placeholder="10"
                  min="1"
                  max="100"
                />

                <FormField
                  label="Max Ordens/Dia"
                  type="number"
                  value={formData.maxDailyOrders.toString()}
                  onChange={(e) => handleInputChange('maxDailyOrders', parseInt(e.target.value))}
                  placeholder="500"
                  min="10"
                  max="10000"
                />

                <FormField
                  label="Tamanho Mín (USDT)"
                  type="number"
                  value={formData.minOrderSize.toString()}
                  onChange={(e) => handleInputChange('minOrderSize', parseFloat(e.target.value))}
                  placeholder="10"
                  step="1"
                  min="1"
                />

                <FormField
                  label="Tamanho Máx (USDT)"
                  type="number"
                  value={formData.maxOrderSize.toString()}
                  onChange={(e) => handleInputChange('maxOrderSize', parseFloat(e.target.value))}
                  placeholder="1000"
                  step="10"
                  min="10"
                />
              </div>
            )}
          </div>

          {/* Execution Settings */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Configurações de Execução</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <FormField
                label="Delay de Execução (ms)"
                type="number"
                value={formData.executionDelay.toString()}
                onChange={(e) => handleInputChange('executionDelay', parseInt(e.target.value))}
                placeholder="100"
                step="50"
                min="0"
                max="5000"
                hint="Aguardar antes de executar"
              />

              <FormField
                label="Timeout (ms)"
                type="number"
                value={formData.timeoutMs.toString()}
                onChange={(e) => handleInputChange('timeoutMs', parseInt(e.target.value))}
                placeholder="5000"
                step="500"
                min="1000"
                max="30000"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium">Retry Automático</label>
                <p className="text-xs text-muted-foreground">Tentar novamente em caso de falha</p>
              </div>
              <Switch
                checked={formData.enableRetry}
                onCheckedChange={(checked) => handleInputChange('enableRetry', checked)}
              />
            </div>

            {formData.enableRetry && (
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  label="Máximo de Tentativas"
                  type="number"
                  value={formData.maxRetries.toString()}
                  onChange={(e) => handleInputChange('maxRetries', parseInt(e.target.value))}
                  placeholder="3"
                  min="1"
                  max="10"
                />

                <FormField
                  label="Delay entre Tentativas (ms)"
                  type="number"
                  value={formData.retryDelayMs.toString()}
                  onChange={(e) => handleInputChange('retryDelayMs', parseInt(e.target.value))}
                  placeholder="1000"
                  step="500"
                  min="500"
                  max="10000"
                />
              </div>
            )}
          </div>

          {/* URL Preview */}
          {generatedUrl && (
            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
              <h4 className="font-medium text-green-800 dark:text-green-200 mb-2">🎉 Webhook URL Gerada</h4>
              <div className="flex items-center space-x-2">
                <code className="flex-1 text-sm bg-background px-3 py-2 rounded border break-all">
                  {generatedUrl}
                </code>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={copyUrlToClipboard}
                >
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Security Warning */}
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 mr-2 mt-0.5" />
              <div>
                <p className="text-sm text-yellow-800 dark:text-yellow-200">
                  <strong>Importante:</strong> Mantenha sua secret key segura. Ela será usada para validar 
                  a autenticidade dos sinais recebidos do TradingView.
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