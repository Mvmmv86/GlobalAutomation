import React, { useState } from 'react'
import { X, AlertCircle, Activity, Shield, Settings, Zap, Wifi } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Button } from '../atoms/Button'
import { FormField } from './FormField'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../atoms/Select'
import { Switch } from '../atoms/Switch'
import { Badge } from '../atoms/Badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'

interface ConfigureAccountModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: AccountConfiguration) => void
  accountId: string
  accountName: string
  exchange: string
  isLoading?: boolean
}

export interface AccountConfiguration {
  // Trading Settings
  defaultLeverage: number
  marginMode: 'cross' | 'isolated'
  positionMode: 'hedge' | 'one-way'
  defaultOrderSize: number
  orderSizeType: 'percentage' | 'fixed'
  
  // Risk Management
  maxLossPerTrade: number
  maxDailyExposure: number
  maxSimultaneousPositions: number
  maxLeverageLimit: number
  enableStopLoss: boolean
  enableTakeProfit: boolean
  
  // API Settings
  apiTimeout: number
  enableApiRetry: boolean
  maxRetryAttempts: number
  apiRateLimit: number
  
  // Webhook Settings
  webhookDelay: number
  enableWebhookRetry: boolean
  webhookTimeout: number
  enableSignalValidation: boolean
  minVolumeFilter: number
  
  // Exchange Specific
  favoriteSymbols: string[]
  preferredTimeframes: string[]
  customFees: {
    maker: number
    taker: number
  }
  
  // Advanced Settings
  enableSlippage: boolean
  maxSlippage: number
  enablePartialFills: boolean
  orderExecutionMode: 'market' | 'limit' | 'auto'
}

const LEVERAGE_OPTIONS = [1, 2, 3, 5, 10, 20, 25, 50, 75, 100, 125]
const TIMEFRAME_OPTIONS = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
const POPULAR_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'AVAXUSDT', 'MATICUSDT']

export const ConfigureAccountModal: React.FC<ConfigureAccountModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  accountId,
  accountName,
  exchange,
  isLoading = false
}) => {
  const [activeTab, setActiveTab] = useState<'trading' | 'risk' | 'api' | 'webhook' | 'advanced'>('trading')
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  
  const [config, setConfig] = useState<AccountConfiguration>({
    // Trading Settings
    defaultLeverage: 10,
    marginMode: 'cross',
    positionMode: 'one-way',
    defaultOrderSize: 1,
    orderSizeType: 'percentage',
    
    // Risk Management
    maxLossPerTrade: 2,
    maxDailyExposure: 10,
    maxSimultaneousPositions: 5,
    maxLeverageLimit: 20,
    enableStopLoss: true,
    enableTakeProfit: true,
    
    // API Settings
    apiTimeout: 5000,
    enableApiRetry: true,
    maxRetryAttempts: 3,
    apiRateLimit: 1200,
    
    // Webhook Settings
    webhookDelay: 100,
    enableWebhookRetry: true,
    webhookTimeout: 3000,
    enableSignalValidation: true,
    minVolumeFilter: 1000,
    
    // Exchange Specific
    favoriteSymbols: ['BTCUSDT', 'ETHUSDT'],
    preferredTimeframes: ['5m', '15m', '1h'],
    customFees: {
      maker: 0.1,
      taker: 0.1
    },
    
    // Advanced Settings
    enableSlippage: true,
    maxSlippage: 0.5,
    enablePartialFills: true,
    orderExecutionMode: 'auto'
  })

  const testApiConnection = async () => {
    setApiStatus('testing')
    try {
      // Simulate API test
      await new Promise(resolve => setTimeout(resolve, 1500))
      setApiStatus('success')
      setTimeout(() => setApiStatus('idle'), 3000)
    } catch (error) {
      setApiStatus('error')
      setTimeout(() => setApiStatus('idle'), 3000)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(config)
  }

  const handleConfigChange = (field: keyof AccountConfiguration, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }))
  }

  const toggleSymbol = (symbol: string) => {
    setConfig(prev => ({
      ...prev,
      favoriteSymbols: prev.favoriteSymbols.includes(symbol)
        ? prev.favoriteSymbols.filter(s => s !== symbol)
        : [...prev.favoriteSymbols, symbol]
    }))
  }

  const toggleTimeframe = (timeframe: string) => {
    setConfig(prev => ({
      ...prev,
      preferredTimeframes: prev.preferredTimeframes.includes(timeframe)
        ? prev.preferredTimeframes.filter(t => t !== timeframe)
        : [...prev.preferredTimeframes, timeframe]
    }))
  }

  const tabs = [
    { id: 'trading', label: 'Trading', icon: Activity },
    { id: 'risk', label: 'Risk Management', icon: Shield },
    { id: 'api', label: 'API', icon: Wifi },
    { id: 'webhook', label: 'Webhooks', icon: Zap },
    { id: 'advanced', label: 'Avançado', icon: Settings },
  ] as const

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[800px] max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <Settings className="w-5 h-5" />
            <span>Configurar {accountName}</span>
          </DialogTitle>
          <DialogDescription>
            Configure as opções de trading para {exchange.toUpperCase()} • ID: {accountId}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col h-[600px]">
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
            {activeTab === 'trading' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Configurações de Trading</CardTitle>
                    <CardDescription>Definições padrão para suas operações</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium">Alavancagem Padrão</label>
                        <Select value={config.defaultLeverage.toString()} onValueChange={(value) => handleConfigChange('defaultLeverage', parseInt(value))}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {LEVERAGE_OPTIONS.map((lev) => (
                              <SelectItem key={lev} value={lev.toString()}>{lev}x</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <label className="text-sm font-medium">Modo de Margem</label>
                        <Select value={config.marginMode} onValueChange={(value: 'cross' | 'isolated') => handleConfigChange('marginMode', value)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="cross">Cross Margin</SelectItem>
                            <SelectItem value="isolated">Isolated Margin</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium">Modo de Posição</label>
                        <Select value={config.positionMode} onValueChange={(value: 'hedge' | 'one-way') => handleConfigChange('positionMode', value)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="one-way">One-way</SelectItem>
                            <SelectItem value="hedge">Hedge Mode</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <label className="text-sm font-medium">Tipo de Ordem</label>
                        <Select value={config.orderSizeType} onValueChange={(value: 'percentage' | 'fixed') => handleConfigChange('orderSizeType', value)}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="percentage">% do Saldo</SelectItem>
                            <SelectItem value="fixed">Valor Fixo</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <FormField
                      label={`Tamanho Padrão da Ordem (${config.orderSizeType === 'percentage' ? '%' : 'USDT'})`}
                      type="number"
                      value={config.defaultOrderSize.toString()}
                      onChange={(e) => handleConfigChange('defaultOrderSize', parseFloat(e.target.value))}
                      placeholder={config.orderSizeType === 'percentage' ? '1' : '100'}
                      step={config.orderSizeType === 'percentage' ? '0.1' : '10'}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Símbolos Favoritos</CardTitle>
                    <CardDescription>Selecione os pares que você mais utiliza</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {POPULAR_SYMBOLS.map((symbol) => (
                        <Badge
                          key={symbol}
                          variant={config.favoriteSymbols.includes(symbol) ? 'default' : 'outline'}
                          className="cursor-pointer"
                          onClick={() => toggleSymbol(symbol)}
                        >
                          {symbol}
                        </Badge>
                      ))}
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
                      <Shield className="w-5 h-5" />
                      <span>Gestão de Risco</span>
                    </CardTitle>
                    <CardDescription>Defina limites para proteger seu capital</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        label="Max Perda por Trade (%)"
                        type="number"
                        value={config.maxLossPerTrade.toString()}
                        onChange={(e) => handleConfigChange('maxLossPerTrade', parseFloat(e.target.value))}
                        placeholder="2"
                        step="0.1"
                        min="0.1"
                        max="10"
                      />

                      <FormField
                        label="Max Exposição Diária (%)"
                        type="number"
                        value={config.maxDailyExposure.toString()}
                        onChange={(e) => handleConfigChange('maxDailyExposure', parseFloat(e.target.value))}
                        placeholder="10"
                        step="1"
                        min="1"
                        max="50"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        label="Max Posições Simultâneas"
                        type="number"
                        value={config.maxSimultaneousPositions.toString()}
                        onChange={(e) => handleConfigChange('maxSimultaneousPositions', parseInt(e.target.value))}
                        placeholder="5"
                        min="1"
                        max="20"
                      />

                      <FormField
                        label="Limite Máximo de Alavancagem"
                        type="number"
                        value={config.maxLeverageLimit.toString()}
                        onChange={(e) => handleConfigChange('maxLeverageLimit', parseInt(e.target.value))}
                        placeholder="20"
                        min="1"
                        max="125"
                      />
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Stop Loss Automático</label>
                          <p className="text-xs text-muted-foreground">Aplicar stop loss em todas as ordens</p>
                        </div>
                        <Switch
                          checked={config.enableStopLoss}
                          onCheckedChange={(checked) => handleConfigChange('enableStopLoss', checked)}
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Take Profit Automático</label>
                          <p className="text-xs text-muted-foreground">Aplicar take profit em todas as ordens</p>
                        </div>
                        <Switch
                          checked={config.enableTakeProfit}
                          onCheckedChange={(checked) => handleConfigChange('enableTakeProfit', checked)}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'api' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Wifi className="w-5 h-5" />
                        <span>Configurações de API</span>
                      </div>
                      <Button
                        onClick={testApiConnection}
                        variant={apiStatus === 'success' ? 'success' : apiStatus === 'error' ? 'danger' : 'outline'}
                        size="sm"
                        disabled={apiStatus === 'testing'}
                      >
                        {apiStatus === 'testing' ? 'Testando...' : 'Testar Conexão'}
                      </Button>
                    </CardTitle>
                    <CardDescription>Ajuste as configurações de conectividade</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {apiStatus === 'success' && (
                      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
                        <p className="text-green-800 dark:text-green-200 text-sm">✅ Conexão com API funcionando perfeitamente</p>
                      </div>
                    )}
                    
                    {apiStatus === 'error' && (
                      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                        <p className="text-red-800 dark:text-red-200 text-sm">❌ Erro na conexão com API</p>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        label="Timeout da API (ms)"
                        type="number"
                        value={config.apiTimeout.toString()}
                        onChange={(e) => handleConfigChange('apiTimeout', parseInt(e.target.value))}
                        placeholder="5000"
                        step="500"
                        min="1000"
                        max="30000"
                      />

                      <FormField
                        label="Rate Limit (req/min)"
                        type="number"
                        value={config.apiRateLimit.toString()}
                        onChange={(e) => handleConfigChange('apiRateLimit', parseInt(e.target.value))}
                        placeholder="1200"
                        step="100"
                        min="100"
                        max="2400"
                      />
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Retry Automático</label>
                          <p className="text-xs text-muted-foreground">Tentar novamente em caso de falha</p>
                        </div>
                        <Switch
                          checked={config.enableApiRetry}
                          onCheckedChange={(checked) => handleConfigChange('enableApiRetry', checked)}
                        />
                      </div>

                      {config.enableApiRetry && (
                        <FormField
                          label="Máximo de Tentativas"
                          type="number"
                          value={config.maxRetryAttempts.toString()}
                          onChange={(e) => handleConfigChange('maxRetryAttempts', parseInt(e.target.value))}
                          placeholder="3"
                          min="1"
                          max="10"
                        />
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'webhook' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center space-x-2">
                      <Zap className="w-5 h-5" />
                      <span>Configurações de Webhook</span>
                    </CardTitle>
                    <CardDescription>Ajuste como os sinais do TradingView são processados</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        label="Delay de Execução (ms)"
                        type="number"
                        value={config.webhookDelay.toString()}
                        onChange={(e) => handleConfigChange('webhookDelay', parseInt(e.target.value))}
                        placeholder="100"
                        step="50"
                        min="0"
                        max="5000"
                        hint="Atraso antes de executar ordem"
                      />

                      <FormField
                        label="Timeout do Webhook (ms)"
                        type="number"
                        value={config.webhookTimeout.toString()}
                        onChange={(e) => handleConfigChange('webhookTimeout', parseInt(e.target.value))}
                        placeholder="3000"
                        step="500"
                        min="1000"
                        max="10000"
                      />
                    </div>

                    <FormField
                      label="Filtro de Volume Mínimo (USDT)"
                      type="number"
                      value={config.minVolumeFilter.toString()}
                      onChange={(e) => handleConfigChange('minVolumeFilter', parseFloat(e.target.value))}
                      placeholder="1000"
                      step="100"
                      min="0"
                      hint="Ignorar sinais com volume menor que este valor"
                    />

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Retry de Webhook</label>
                          <p className="text-xs text-muted-foreground">Tentar novamente se falhar</p>
                        </div>
                        <Switch
                          checked={config.enableWebhookRetry}
                          onCheckedChange={(checked) => handleConfigChange('enableWebhookRetry', checked)}
                        />
                      </div>

                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Validação de Sinais</label>
                          <p className="text-xs text-muted-foreground">Verificar validade dos sinais recebidos</p>
                        </div>
                        <Switch
                          checked={config.enableSignalValidation}
                          onCheckedChange={(checked) => handleConfigChange('enableSignalValidation', checked)}
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeTab === 'advanced' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Configurações Avançadas</CardTitle>
                    <CardDescription>Opções para usuários experientes</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Modo de Execução</label>
                      <Select value={config.orderExecutionMode} onValueChange={(value: 'market' | 'limit' | 'auto') => handleConfigChange('orderExecutionMode', value)}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">Automático</SelectItem>
                          <SelectItem value="market">Market Orders</SelectItem>
                          <SelectItem value="limit">Limit Orders</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <FormField
                        label="Taxa Maker (%)"
                        type="number"
                        value={config.customFees.maker.toString()}
                        onChange={(e) => handleConfigChange('customFees', { ...config.customFees, maker: parseFloat(e.target.value) })}
                        placeholder="0.1"
                        step="0.01"
                        min="0"
                        max="1"
                      />

                      <FormField
                        label="Taxa Taker (%)"
                        type="number"
                        value={config.customFees.taker.toString()}
                        onChange={(e) => handleConfigChange('customFees', { ...config.customFees, taker: parseFloat(e.target.value) })}
                        placeholder="0.1"
                        step="0.01"
                        min="0"
                        max="1"
                      />
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium">Controle de Slippage</label>
                          <p className="text-xs text-muted-foreground">Monitorar diferença de preço</p>
                        </div>
                        <Switch
                          checked={config.enableSlippage}
                          onCheckedChange={(checked) => handleConfigChange('enableSlippage', checked)}
                        />
                      </div>

                      {config.enableSlippage && (
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
                          <label className="text-sm font-medium">Preenchimento Parcial</label>
                          <p className="text-xs text-muted-foreground">Aceitar ordens parcialmente preenchidas</p>
                        </div>
                        <Switch
                          checked={config.enablePartialFills}
                          onCheckedChange={(checked) => handleConfigChange('enablePartialFills', checked)}
                        />
                      </div>
                    </div>

                    <Card className="bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800">
                      <CardContent className="pt-6">
                        <div className="flex">
                          <AlertCircle className="h-4 w-4 text-orange-600 dark:text-orange-400 mr-2 mt-0.5" />
                          <div>
                            <p className="text-sm text-orange-800 dark:text-orange-200">
                              <strong>Atenção:</strong> Configurações avançadas podem impactar significativamente 
                              sua estratégia de trading. Teste em ambiente simulado primeiro.
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <div>
                      <label className="text-sm font-medium mb-2 block">Timeframes Preferidos</label>
                      <div className="flex flex-wrap gap-2">
                        {TIMEFRAME_OPTIONS.map((timeframe) => (
                          <Badge
                            key={timeframe}
                            variant={config.preferredTimeframes.includes(timeframe) ? 'default' : 'outline'}
                            className="cursor-pointer"
                            onClick={() => toggleTimeframe(timeframe)}
                          >
                            {timeframe}
                          </Badge>
                        ))}
                      </div>
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