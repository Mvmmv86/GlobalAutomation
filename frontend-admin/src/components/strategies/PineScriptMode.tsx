/**
 * PineScriptMode Component
 * Interface for PineScript/TradingView webhook integration
 */
import { useState } from 'react'
import { Copy, Check, ExternalLink, AlertCircle, Zap, Shield, Clock } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { Label } from '@/components/atoms/Label'
import { Badge } from '@/components/atoms/Badge'

interface PineScriptModeProps {
  strategyId?: string
  strategyName: string
  onSave: (config: PineScriptConfig) => void
  onCancel: () => void
  isSaving?: boolean
}

export interface PineScriptConfig {
  name: string
  description: string
  webhook_secret: string
  symbols: string[]
  default_leverage: number
  default_margin_pct: number
}

// Example PineScript alert message
const ALERT_MESSAGE_TEMPLATE = `{
  "secret": "{{webhook_secret}}",
  "action": "{{strategy.order.action}}",
  "ticker": "{{ticker}}",
  "price": {{close}},
  "quantity": {{strategy.order.contracts}},
  "position_size": {{strategy.position_size}},
  "comment": "{{strategy.order.comment}}"
}`

export function PineScriptMode({ strategyId, strategyName, onSave, onCancel, isSaving }: PineScriptModeProps) {
  const [config, setConfig] = useState<PineScriptConfig>({
    name: strategyName || 'PineScript Strategy',
    description: 'Estrategia baseada em alertas do TradingView',
    webhook_secret: generateSecret(),
    symbols: [],
    default_leverage: 10,
    default_margin_pct: 5,
  })

  const [copied, setCopied] = useState<string | null>(null)
  const [symbolInput, setSymbolInput] = useState('')

  // Generate webhook URL
  const baseUrl = import.meta.env.VITE_API_URL || 'https://api.ominiiachain.com'
  const webhookUrl = `${baseUrl}/api/v1/strategies/pinescript-webhook`

  function generateSecret(): string {
    return 'ps_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
  }

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(null), 2000)
  }

  const addSymbol = () => {
    const symbol = symbolInput.toUpperCase().trim()
    if (symbol && !config.symbols.includes(symbol)) {
      setConfig(prev => ({ ...prev, symbols: [...prev.symbols, symbol] }))
    }
    setSymbolInput('')
  }

  const removeSymbol = (symbol: string) => {
    setConfig(prev => ({ ...prev, symbols: prev.symbols.filter(s => s !== symbol) }))
  }

  const regenerateSecret = () => {
    setConfig(prev => ({ ...prev, webhook_secret: generateSecret() }))
  }

  const alertMessage = ALERT_MESSAGE_TEMPLATE.replace('{{webhook_secret}}', config.webhook_secret)

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <Card className="p-4 bg-gradient-to-r from-orange-900/20 to-yellow-900/20 border-orange-700/50">
        <div className="flex items-start gap-3">
          <Zap className="w-6 h-6 text-orange-400 mt-0.5" />
          <div>
            <h3 className="text-white font-medium">Integracao PineScript / TradingView</h3>
            <p className="text-gray-300 text-sm mt-1">
              Configure alertas no TradingView para enviar sinais diretamente para o sistema.
              Os sinais serao processados e executados automaticamente via bots.
            </p>
          </div>
        </div>
      </Card>

      {/* Basic Config */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label className="text-gray-300">Nome da Estrategia</Label>
          <Input
            value={config.name}
            onChange={(e) => setConfig(prev => ({ ...prev, name: e.target.value }))}
            placeholder="Nome da estrategia"
            className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white"
          />
        </div>
        <div>
          <Label className="text-gray-300">Descricao</Label>
          <Input
            value={config.description}
            onChange={(e) => setConfig(prev => ({ ...prev, description: e.target.value }))}
            placeholder="Descricao opcional"
            className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white"
          />
        </div>
      </div>

      {/* Webhook URL */}
      <div>
        <Label className="text-gray-300 flex items-center gap-2">
          Webhook URL
          <Badge variant="default" className="bg-green-500/20 text-green-300 text-xs">Copie para o TradingView</Badge>
        </Label>
        <div className="mt-1 flex gap-2">
          <Input
            value={webhookUrl}
            readOnly
            className="flex-1 bg-[#1e222d] border-[#2a2e39] text-cyan-300 font-mono text-sm"
          />
          <Button
            variant="outline"
            onClick={() => copyToClipboard(webhookUrl, 'url')}
            className="border-[#2a2e39]"
          >
            {copied === 'url' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Webhook Secret */}
      <div>
        <Label className="text-gray-300 flex items-center gap-2">
          <Shield className="w-4 h-4 text-yellow-400" />
          Webhook Secret (Chave de Autenticacao)
        </Label>
        <div className="mt-1 flex gap-2">
          <Input
            value={config.webhook_secret}
            readOnly
            className="flex-1 bg-[#1e222d] border-[#2a2e39] text-yellow-300 font-mono text-sm"
          />
          <Button
            variant="outline"
            onClick={() => copyToClipboard(config.webhook_secret, 'secret')}
            className="border-[#2a2e39]"
          >
            {copied === 'secret' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </Button>
          <Button
            variant="outline"
            onClick={regenerateSecret}
            className="border-[#2a2e39] text-gray-400"
          >
            Regenerar
          </Button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Esta chave deve ser incluida no JSON do alerta para autenticar as requisicoes.
        </p>
      </div>

      {/* Alert Message Template */}
      <div>
        <Label className="text-gray-300 flex items-center gap-2">
          Mensagem do Alerta (JSON)
          <Badge variant="default" className="bg-purple-500/20 text-purple-300 text-xs">Cole no campo "Message" do alerta</Badge>
        </Label>
        <div className="mt-1 relative">
          <pre className="p-4 bg-[#0d1117] border border-[#2a2e39] rounded-lg text-sm font-mono text-gray-300 overflow-x-auto">
            {alertMessage}
          </pre>
          <Button
            variant="outline"
            size="sm"
            onClick={() => copyToClipboard(alertMessage, 'message')}
            className="absolute top-2 right-2 border-[#2a2e39]"
          >
            {copied === 'message' ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Trading Config */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <Label className="text-gray-300">Alavancagem Padrao</Label>
          <Input
            type="number"
            value={config.default_leverage}
            onChange={(e) => setConfig(prev => ({ ...prev, default_leverage: parseInt(e.target.value) || 1 }))}
            min={1}
            max={125}
            className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white"
          />
        </div>
        <div>
          <Label className="text-gray-300">Margem Padrao (%)</Label>
          <Input
            type="number"
            value={config.default_margin_pct}
            onChange={(e) => setConfig(prev => ({ ...prev, default_margin_pct: parseFloat(e.target.value) || 1 }))}
            min={0.1}
            max={100}
            step={0.1}
            className="mt-1 bg-[#1e222d] border-[#2a2e39] text-white"
          />
        </div>
      </div>

      {/* Allowed Symbols */}
      <div>
        <Label className="text-gray-300">Simbolos Permitidos (opcional)</Label>
        <p className="text-xs text-gray-500 mb-2">
          Se vazio, aceita qualquer simbolo. Se preenchido, apenas esses simbolos serao aceitos.
        </p>
        <div className="flex flex-wrap gap-2 mb-2">
          {config.symbols.map(symbol => (
            <Badge
              key={symbol}
              variant="default"
              className="bg-blue-500/20 text-blue-300 border-blue-500/50 cursor-pointer hover:bg-red-500/20"
              onClick={() => removeSymbol(symbol)}
            >
              {symbol} x
            </Badge>
          ))}
        </div>
        <div className="flex gap-2">
          <Input
            value={symbolInput}
            onChange={(e) => setSymbolInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addSymbol()}
            placeholder="BTCUSDT"
            className="flex-1 bg-[#1e222d] border-[#2a2e39] text-white"
          />
          <Button variant="outline" onClick={addSymbol}>Adicionar</Button>
        </div>
      </div>

      {/* Instructions */}
      <Card className="p-4 bg-[#131722] border-[#2a2e39]">
        <h4 className="text-white font-medium mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-400" />
          Como configurar no TradingView
        </h4>
        <ol className="text-sm text-gray-300 space-y-2 list-decimal list-inside">
          <li>Abra seu script PineScript no TradingView</li>
          <li>Clique em "Add Alert" (Adicionar Alerta)</li>
          <li>Configure a condicao do alerta</li>
          <li>Em "Webhook URL", cole a URL acima</li>
          <li>Em "Message", cole o JSON de mensagem acima</li>
          <li>Ative "Webhook URL" nas configuracoes do alerta</li>
          <li>Salve o alerta</li>
        </ol>
        <a
          href="https://www.tradingview.com/support/solutions/43000529348-about-webhooks/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-blue-400 text-sm mt-3 hover:underline"
        >
          Documentacao do TradingView sobre Webhooks
          <ExternalLink className="w-3 h-3" />
        </a>
      </Card>

      {/* Warning */}
      <div className="flex items-start gap-2 p-3 bg-yellow-900/20 border border-yellow-700/50 rounded-lg">
        <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5" />
        <p className="text-yellow-300 text-sm">
          <strong>Importante:</strong> Guarde a chave secreta em local seguro.
          Qualquer pessoa com essa chave pode enviar sinais para sua conta.
        </p>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-[#2a2e39]">
        <Button
          variant="outline"
          onClick={onCancel}
          className="border-[#2a2e39] text-gray-300"
        >
          Cancelar
        </Button>
        <Button
          onClick={() => onSave(config)}
          disabled={!config.name.trim() || isSaving}
          className="bg-orange-600 hover:bg-orange-700"
        >
          {isSaving ? 'Salvando...' : 'Salvar Configuracao'}
        </Button>
      </div>
    </div>
  )
}
