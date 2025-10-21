import React, { useState } from 'react'
import { Settings, Activity, Shield, Zap, BarChart3, AlertCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { FormField } from './FormField'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../atoms/Select'
import { Switch } from '../atoms/Switch'
import { Badge } from '../atoms/Badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'

interface ConfigureWebhookModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: WebhookConfiguration) => void
  webhookId: string
  webhookName: string
  webhookStatus: string
  isLoading?: boolean
}

export interface WebhookConfiguration {
  // Status & Basic Settings
  status: 'active' | 'paused' | 'disabled'
  name: string
  description: string
  
  // Security Settings
  enableAuth: boolean
  rotateSecretKey: boolean
  enableIPWhitelist: boolean
  allowedIPs: string[]
  enableRateLimit: boolean
  rateLimit: number
  
  // Signal Processing
  enableSignalValidation: boolean
  requiredFields: string[]
  enableDuplicateFilter: boolean
  duplicateWindowMs: number
  enableTimestampValidation: boolean
  maxTimestampAge: number
  
  // Risk Management
  enableRiskLimits: boolean
  maxOrdersPerMinute: number
  maxDailyOrders: number
  maxDailyVolume: number
  enablePositionLimits: boolean
  maxOpenPositions: number
  maxExposurePerSymbol: number
  
  // Order Execution
  executionMode: 'immediate' | 'delayed' | 'conditional'
  executionDelay: number
  enableSlippageControl: boolean
  maxSlippage: number
  enableRetry: boolean
  maxRetries: number
  retryDelayMs: number
  
  // Filters & Conditions
  enableSymbolFilter: boolean
  allowedSymbols: string[]
  enableTimeFilter: boolean
  tradingStartTime: string
  tradingEndTime: string
  enableWeekendTrading: boolean
  
  // Notifications & Monitoring
  enableLogging: boolean
  logLevel: 'debug' | 'info' | 'warning' | 'error'
  enableNotifications: boolean
  notificationMethods: string[]
  notificationEmail: string
  notificationWebhook: string
  
  // Performance Monitoring
  enablePerformanceMonitoring: boolean
  alertOnHighLatency: boolean
  latencyThresholdMs: number
  alertOnFailureRate: boolean
  failureRateThreshold: number
  
  // Advanced Settings
  customHeaders: Record<string, string>
  enableCustomScripts: boolean
  preExecutionScript: string
  postExecutionScript: string
  enableBacktest: boolean
  backtestDays: number
}

const SYMBOL_OPTIONS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT']
const REQUIRED_FIELDS_OPTIONS = ['symbol', 'side', 'quantity', 'price', 'type', 'timestamp', 'strategy', 'leverage']
const NOTIFICATION_METHODS = ['email', 'webhook', 'telegram', 'discord', 'slack']

export const ConfigureWebhookModal: React.FC<ConfigureWebhookModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  webhookId,
  webhookName,
  webhookStatus,
  isLoading = false
}) => {
  const [activeTab, setActiveTab] = useState<'general' | 'security' | 'risk' | 'execution' | 'monitoring'>('general')
  
  const [config, setConfig] = useState<WebhookConfiguration>({
    // Status & Basic Settings
    status: webhookStatus as 'active' | 'paused' | 'disabled',
    name: webhookName,
    description: '',
    
    // Security Settings
    enableAuth: true,
    rotateSecretKey: false,
    enableIPWhitelist: false,
    allowedIPs: [],
    enableRateLimit: true,
    rateLimit: 60,
    
    // Signal Processing
    enableSignalValidation: true,
    requiredFields: ['symbol', 'side', 'quantity'],
    enableDuplicateFilter: true,
    duplicateWindowMs: 5000,
    enableTimestampValidation: true,
    maxTimestampAge: 30000,
    
    // Risk Management
    enableRiskLimits: true,
    maxOrdersPerMinute: 10,
    maxDailyOrders: 500,
    maxDailyVolume: 50000,
    enablePositionLimits: true,
    maxOpenPositions: 5,
    maxExposurePerSymbol: 10000,
    
    // Order Execution
    executionMode: 'immediate',
    executionDelay: 100,
    enableSlippageControl: true,
    maxSlippage: 0.5,
    enableRetry: true,
    maxRetries: 3,
    retryDelayMs: 1000,
    
    // Filters & Conditions
    enableSymbolFilter: false,
    allowedSymbols: [],
    enableTimeFilter: false,
    tradingStartTime: '09:00',
    tradingEndTime: '17:00',
    enableWeekendTrading: true,
    
    // Notifications & Monitoring
    enableLogging: true,
    logLevel: 'info',
    enableNotifications: false,
    notificationMethods: [],
    notificationEmail: '',
    notificationWebhook: '',
    
    // Performance Monitoring
    enablePerformanceMonitoring: true,
    alertOnHighLatency: true,
    latencyThresholdMs: 1000,
    alertOnFailureRate: true,
    failureRateThreshold: 5,
    
    // Advanced Settings
    customHeaders: {},
    enableCustomScripts: false,
    preExecutionScript: '',
    postExecutionScript: '',
    enableBacktest: false,
    backtestDays: 30
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(config)
  }

  const handleConfigChange = (field: keyof WebhookConfiguration, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }))
  }

  const toggleSymbol = (symbol: string) => {
    setConfig(prev => ({
      ...prev,
      allowedSymbols: prev.allowedSymbols.includes(symbol)
        ? prev.allowedSymbols.filter(s => s !== symbol)
        : [...prev.allowedSymbols, symbol]
    }))
  }

  const toggleRequiredField = (field: string) => {
    setConfig(prev => ({
      ...prev,
      requiredFields: prev.requiredFields.includes(field)
        ? prev.requiredFields.filter(f => f !== field)
        : [...prev.requiredFields, field]
    }))
  }

  const toggleNotificationMethod = (method: string) => {
    setConfig(prev => ({
      ...prev,
      notificationMethods: prev.notificationMethods.includes(method)
        ? prev.notificationMethods.filter(m => m !== method)
        : [...prev.notificationMethods, method]
    }))
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Ativo</Badge>
      case 'paused':
        return <Badge variant="warning">Pausado</Badge>
      case 'disabled':
        return <Badge variant="secondary">Desabilitado</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const tabs = [
    { id: 'general', label: 'Geral', icon: Settings },
    { id: 'security', label: 'Segurança', icon: Shield },
    { id: 'risk', label: 'Risco', icon: AlertCircle },
    { id: 'execution', label: 'Execução', icon: Zap },
    { id: 'monitoring', label: 'Monitoramento', icon: BarChart3 },
  ] as const

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Settings className="w-5 h-5" />
              <span>Configurar {webhookName}</span>
            </div>
            {getStatusBadge(config.status)}
          </DialogTitle>
          <DialogDescription>
            Configure as opções avançadas do webhook • ID: {webhookId}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col h-[650px]">
          {/* Tabs */}
          <div className="flex space-x-1 bg-muted p-1 rounded-lg mb-4">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-background text-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              )
            })}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {activeTab === 'general' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Configurações Gerais</CardTitle>
                    <CardDescription>Status e informações básicas do webhook</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        label="Nome do Webhook"
                        value={config.name}
                        onChange={(e) => handleConfigChange('name', e.target.value)}
                        placeholder="Nome do webhook"
                      />

                      <div>
                        <label className="text-sm font-medium">Status</label>
                        <Select value={config.status} onValueChange={(value: 'active' | 'paused' | 'disabled') => handleConfigChange('status', value)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="active">Ativo</SelectItem>
                            <SelectItem value="paused">Pausado</SelectItem>
                            <SelectItem value="disabled">Desabilitado</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <FormField
                      label="Descrição"
                      value={config.description}
                      onChange={(e) => handleConfigChange('description', e.target.value)}
                      placeholder="Descrição opcional"
                      multiline
                      rows={2}
                    />

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Validação de Sinais</label>
                          <p className="text-xs text-muted-foreground">Verificar campos obrigatórios</p>
                        </div>
                        <Switch
                          checked={config.enableSignalValidation}
                          onCheckedChange={(checked) => handleConfigChange('enableSignalValidation', checked)}
                        />
                      </div>

                      {config.enableSignalValidation && (
                        <div>
                          <label className="text-sm font-medium mb-2 block">Campos Obrigatórios</label>
                          <div className="flex flex-wrap gap-2">
                            {REQUIRED_FIELDS_OPTIONS.map((field) => (
                              <Badge
                                key={field}
                                variant={config.requiredFields.includes(field) ? 'default' : 'outline'}
                                className="cursor-pointer"
                                onClick={() => toggleRequiredField(field)}
                              >
                                {field}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Filtro de Duplicatas</label>
                          <p className="text-xs text-muted-foreground">Ignorar sinais duplicados</p>
                        </div>
                        <Switch
                          checked={config.enableDuplicateFilter}
                          onCheckedChange={(checked) => handleConfigChange('enableDuplicateFilter', checked)}
                        />
                      </div>

                      {config.enableDuplicateFilter && (
                        <FormField
                          label="Janela de Duplicata (ms)"
                          type="number"
                          value={config.duplicateWindowMs.toString()}
                          onChange={(e) => handleConfigChange('duplicateWindowMs', parseInt(e.target.value))}
                          placeholder="5000"
                          step="1000"
                          min="1000"
                        />
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Filtros de Trading</CardTitle>
                    <CardDescription>Controle quando e como os sinais são processados</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium">Filtro por Símbolo</label>
                        <p className="text-xs text-muted-foreground">Limitar símbolos aceitos</p>
                      </div>
                      <Switch
                        checked={config.enableSymbolFilter}
                        onCheckedChange={(checked) => handleConfigChange('enableSymbolFilter', checked)}
                      />
                    </div>

                    {config.enableSymbolFilter && (
                      <div>
                        <label className="text-sm font-medium mb-2 block">Símbolos Permitidos</label>
                        <div className="flex flex-wrap gap-2">
                          {SYMBOL_OPTIONS.map((symbol) => (
                            <Badge
                              key={symbol}
                              variant={config.allowedSymbols.includes(symbol) ? 'default' : 'outline'}
                              className="cursor-pointer"
                              onClick={() => toggleSymbol(symbol)}
                            >
                              {symbol}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium">Filtro de Horário</label>
                        <p className="text-xs text-muted-foreground">Definir horário de trading</p>
                      </div>
                      <Switch
                        checked={config.enableTimeFilter}
                        onCheckedChange={(checked) => handleConfigChange('enableTimeFilter', checked)}
                      />
                    </div>

                    {config.enableTimeFilter && (
                      <div className="grid grid-cols-3 gap-4">
                        <FormField
                          label="Início"
                          type="time"
                          value={config.tradingStartTime}
                          onChange={(e) => handleConfigChange('tradingStartTime', e.target.value)}
                        />

                        <FormField
                          label="Fim"
                          type="time"
                          value={config.tradingEndTime}
                          onChange={(e) => handleConfigChange('tradingEndTime', e.target.value)}
                        />

                        <div className="flex items-center">
                          <div>
                            <label className="text-sm font-medium">Fins de Semana</label>
                            <Switch
                              checked={config.enableWeekendTrading}
                              onCheckedChange={(checked) => handleConfigChange('enableWeekendTrading', checked)}
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center space-x-2">
                      <Shield className="w-5 h-5" />
                      <span>Configurações de Segurança</span>
                    </CardTitle>
                    <CardDescription>Proteja seu webhook contra acessos não autorizados</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Autenticação HMAC</label>
                          <p className="text-xs text-muted-foreground">Verificar assinatura dos sinais</p>
                        </div>
                        <Switch
                          checked={config.enableAuth}
                          onCheckedChange={(checked) => handleConfigChange('enableAuth', checked)}
                        />
                      </div>

                      {config.enableAuth && (
                        <div className="flex items-center justify-between">
                          <div>
                            <label className="text-sm font-medium">Rotacionar Secret Key</label>
                            <p className="text-xs text-muted-foreground">Gerar nova chave de segurança</p>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleConfigChange('rotateSecretKey', true)}
                          >
                            Rotacionar
                          </Button>
                        </div>
                      )}

                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Whitelist de IPs</label>
                          <p className="text-xs text-muted-foreground">Limitar acesso por IP</p>
                        </div>
                        <Switch
                          checked={config.enableIPWhitelist}
                          onCheckedChange={(checked) => handleConfigChange('enableIPWhitelist', checked)}
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Rate Limiting</label>
                          <p className="text-xs text-muted-foreground">Limitar requisições por minuto</p>
                        </div>
                        <Switch
                          checked={config.enableRateLimit}
                          onCheckedChange={(checked) => handleConfigChange('enableRateLimit', checked)}
                        />
                      </div>

                      {config.enableRateLimit && (
                        <FormField
                          label="Limite de Requisições/Minuto"
                          type="number"
                          value={config.rateLimit.toString()}
                          onChange={(e) => handleConfigChange('rateLimit', parseInt(e.target.value))}
                          placeholder="60"
                          min="1"
                          max="1000"
                        />
                      )}
                    </div>

                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                      <div className="flex">
                        <Activity className="h-4 w-4 text-blue-600 dark:text-blue-400 mr-2 mt-0.5" />
                        <div>
                          <p className="text-sm text-blue-800 dark:text-blue-200">
                            <strong>Validação de Timestamp:</strong> Sinais mais antigos que {config.maxTimestampAge}ms serão rejeitados para evitar ataques de replay.
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'risk' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center space-x-2">
                      <AlertCircle className="w-5 h-5" />
                      <span>Gestão de Risco</span>
                    </CardTitle>
                    <CardDescription>Configure limites para proteger seu capital</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium">Limites de Risco</label>
                        <p className="text-xs text-muted-foreground">Aplicar controles de segurança</p>
                      </div>
                      <Switch
                        checked={config.enableRiskLimits}
                        onCheckedChange={(checked) => handleConfigChange('enableRiskLimits', checked)}
                      />
                    </div>

                    {config.enableRiskLimits && (
                      <div className="grid grid-cols-2 gap-4">
                        <FormField
                          label="Max Ordens/Minuto"
                          type="number"
                          value={config.maxOrdersPerMinute.toString()}
                          onChange={(e) => handleConfigChange('maxOrdersPerMinute', parseInt(e.target.value))}
                          placeholder="10"
                          min="1"
                          max="100"
                        />

                        <FormField
                          label="Max Ordens/Dia"
                          type="number"
                          value={config.maxDailyOrders.toString()}
                          onChange={(e) => handleConfigChange('maxDailyOrders', parseInt(e.target.value))}
                          placeholder="500"
                          min="10"
                          max="10000"
                        />

                        <FormField
                          label="Max Volume Diário (USDT)"
                          type="number"
                          value={config.maxDailyVolume.toString()}
                          onChange={(e) => handleConfigChange('maxDailyVolume', parseFloat(e.target.value))}
                          placeholder="50000"
                          step="1000"
                          min="1000"
                        />

                        <div className="flex items-center">
                          <div>
                            <label className="text-sm font-medium">Limites de Posição</label>
                            <Switch
                              checked={config.enablePositionLimits}
                              onCheckedChange={(checked) => handleConfigChange('enablePositionLimits', checked)}
                            />
                          </div>
                        </div>
                      </div>
                    )}

                    {config.enablePositionLimits && (
                      <div className="grid grid-cols-2 gap-4">
                        <FormField
                          label="Max Posições Abertas"
                          type="number"
                          value={config.maxOpenPositions.toString()}
                          onChange={(e) => handleConfigChange('maxOpenPositions', parseInt(e.target.value))}
                          placeholder="5"
                          min="1"
                          max="50"
                        />

                        <FormField
                          label="Max Exposição/Símbolo (USDT)"
                          type="number"
                          value={config.maxExposurePerSymbol.toString()}
                          onChange={(e) => handleConfigChange('maxExposurePerSymbol', parseFloat(e.target.value))}
                          placeholder="10000"
                          step="1000"
                          min="100"
                        />
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'execution' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center space-x-2">
                      <Zap className="w-5 h-5" />
                      <span>Configurações de Execução</span>
                    </CardTitle>
                    <CardDescription>Configure como as ordens são executadas</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Modo de Execução</label>
                      <Select value={config.executionMode} onValueChange={(value: 'immediate' | 'delayed' | 'conditional') => handleConfigChange('executionMode', value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="immediate">Imediato</SelectItem>
                          <SelectItem value="delayed">Com Delay</SelectItem>
                          <SelectItem value="conditional">Condicional</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        label="Delay de Execução (ms)"
                        type="number"
                        value={config.executionDelay.toString()}
                        onChange={(e) => handleConfigChange('executionDelay', parseInt(e.target.value))}
                        placeholder="100"
                        step="50"
                        min="0"
                        max="10000"
                      />

                      <div>
                        <label className="text-sm font-medium">Controle de Slippage</label>
                        <Switch
                          checked={config.enableSlippageControl}
                          onCheckedChange={(checked) => handleConfigChange('enableSlippageControl', checked)}
                        />
                      </div>
                    </div>

                    {config.enableSlippageControl && (
                      <FormField
                        label="Max Slippage (%)"
                        type="number"
                        value={config.maxSlippage.toString()}
                        onChange={(e) => handleConfigChange('maxSlippage', parseFloat(e.target.value))}
                        placeholder="0.5"
                        step="0.1"
                        min="0.1"
                        max="5"
                      />
                    )}

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium">Retry Automático</label>
                        <p className="text-xs text-muted-foreground">Tentar novamente em caso de falha</p>
                      </div>
                      <Switch
                        checked={config.enableRetry}
                        onCheckedChange={(checked) => handleConfigChange('enableRetry', checked)}
                      />
                    </div>

                    {config.enableRetry && (
                      <div className="grid grid-cols-2 gap-4">
                        <FormField
                          label="Máximo de Tentativas"
                          type="number"
                          value={config.maxRetries.toString()}
                          onChange={(e) => handleConfigChange('maxRetries', parseInt(e.target.value))}
                          placeholder="3"
                          min="1"
                          max="10"
                        />

                        <FormField
                          label="Delay entre Tentativas (ms)"
                          type="number"
                          value={config.retryDelayMs.toString()}
                          onChange={(e) => handleConfigChange('retryDelayMs', parseInt(e.target.value))}
                          placeholder="1000"
                          step="500"
                          min="500"
                          max="10000"
                        />
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'monitoring' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center space-x-2">
                      <BarChart3 className="w-5 h-5" />
                      <span>Monitoramento e Logs</span>
                    </CardTitle>
                    <CardDescription>Configure alertas e notificações</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Logging</label>
                          <p className="text-xs text-muted-foreground">Registrar atividades</p>
                        </div>
                        <Switch
                          checked={config.enableLogging}
                          onCheckedChange={(checked) => handleConfigChange('enableLogging', checked)}
                        />
                      </div>

                      {config.enableLogging && (
                        <div>
                          <label className="text-sm font-medium">Nível de Log</label>
                          <Select value={config.logLevel} onValueChange={(value: 'debug' | 'info' | 'warning' | 'error') => handleConfigChange('logLevel', value)}>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="debug">Debug</SelectItem>
                              <SelectItem value="info">Info</SelectItem>
                              <SelectItem value="warning">Warning</SelectItem>
                              <SelectItem value="error">Error</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between">
                      <div>
                        <label className="text-sm font-medium">Notificações</label>
                        <p className="text-xs text-muted-foreground">Receber alertas</p>
                      </div>
                      <Switch
                        checked={config.enableNotifications}
                        onCheckedChange={(checked) => handleConfigChange('enableNotifications', checked)}
                      />
                    </div>

                    {config.enableNotifications && (
                      <div className="space-y-4">
                        <div>
                          <label className="text-sm font-medium mb-2 block">Métodos de Notificação</label>
                          <div className="flex flex-wrap gap-2">
                            {NOTIFICATION_METHODS.map((method) => (
                              <Badge
                                key={method}
                                variant={config.notificationMethods.includes(method) ? 'default' : 'outline'}
                                className="cursor-pointer"
                                onClick={() => toggleNotificationMethod(method)}
                              >
                                {method}
                              </Badge>
                            ))}
                          </div>
                        </div>

                        {config.notificationMethods.includes('email') && (
                          <FormField
                            label="Email para Notificações"
                            type="email"
                            value={config.notificationEmail}
                            onChange={(e) => handleConfigChange('notificationEmail', e.target.value)}
                            placeholder="seu@email.com"
                          />
                        )}
                      </div>
                    )}

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Monitor de Performance</label>
                          <p className="text-xs text-muted-foreground">Alertar sobre latência alta</p>
                        </div>
                        <Switch
                          checked={config.enablePerformanceMonitoring}
                          onCheckedChange={(checked) => handleConfigChange('enablePerformanceMonitoring', checked)}
                        />
                      </div>

                      {config.enablePerformanceMonitoring && (
                        <div className="grid grid-cols-2 gap-4">
                          <div className="flex items-center justify-between">
                            <label className="text-sm font-medium">Alerta de Latência</label>
                            <Switch
                              checked={config.alertOnHighLatency}
                              onCheckedChange={(checked) => handleConfigChange('alertOnHighLatency', checked)}
                            />
                          </div>

                          {config.alertOnHighLatency && (
                            <FormField
                              label="Limite de Latência (ms)"
                              type="number"
                              value={config.latencyThresholdMs.toString()}
                              onChange={(e) => handleConfigChange('latencyThresholdMs', parseInt(e.target.value))}
                              placeholder="1000"
                              step="100"
                              min="100"
                            />
                          )}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancelar
            </Button>
            <Button onClick={handleSubmit} disabled={isLoading}>
              {isLoading ? 'Salvando...' : 'Salvar Configurações'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}