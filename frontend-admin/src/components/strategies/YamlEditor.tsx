/**
 * YamlEditor Component
 * YAML editor for advanced strategy configuration
 */
import { useState, useEffect } from 'react'
import { Save, Copy, Check, FileCode, Download, Upload, AlertCircle } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { Label } from '@/components/atoms/Label'
import { strategyService } from '@/services/strategyService'

// YAML template example
const DEFAULT_YAML_TEMPLATE = `# Estrategia de Trading Automatizada
# Documentacao: https://docs.globalautomation.com/strategies

strategy:
  name: "Minha Estrategia"
  description: "Descricao da estrategia"
  symbols:
    - BTCUSDT
    - ETHUSDT
  timeframe: "5m"

# Indicadores disponiveis:
# - nadaraya_watson: Envelope NDY (bandwidth, mult)
# - rsi: Relative Strength Index (period, overbought, oversold)
# - macd: MACD (fast, slow, signal)
# - ema: Exponential Moving Average (period)
# - sma: Simple Moving Average (period)
# - bollinger: Bollinger Bands (period, std_dev)
# - atr: Average True Range (period)
# - stochastic: Stochastic (k_period, d_period, overbought, oversold)

indicators:
  - type: nadaraya_watson
    params:
      bandwidth: 8
      mult: 3.0

  - type: rsi
    params:
      period: 14
      overbought: 70
      oversold: 30

# Condicoes de entrada/saida
# Operadores: >, <, >=, <=, ==, crosses_above, crosses_below
# Valores: close, open, high, low, volume, [indicador].[output]

conditions:
  entry_long:
    operator: AND
    rules:
      - left: close
        op: "<"
        right: nadaraya_watson.lower
      - left: rsi.value
        op: "<"
        right: 30

  entry_short:
    operator: AND
    rules:
      - left: close
        op: ">"
        right: nadaraya_watson.upper
      - left: rsi.value
        op: ">"
        right: 70

  exit_long:
    operator: OR
    rules:
      - left: close
        op: ">"
        right: nadaraya_watson.upper
      - left: rsi.value
        op: ">"
        right: 70

  exit_short:
    operator: OR
    rules:
      - left: close
        op: "<"
        right: nadaraya_watson.lower
      - left: rsi.value
        op: "<"
        right: 30
`

interface YamlEditorProps {
  strategyId?: string
  initialYaml?: string
  onSave: (yaml: string) => void
  onCancel: () => void
  isSaving?: boolean
}

export function YamlEditor({ strategyId, initialYaml, onSave, onCancel, isSaving }: YamlEditorProps) {
  const [yaml, setYaml] = useState(initialYaml || DEFAULT_YAML_TEMPLATE)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isValidating, setIsValidating] = useState(false)

  // Line numbers
  const lineCount = yaml.split('\n').length

  const handleCopy = () => {
    navigator.clipboard.writeText(yaml)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([yaml], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'strategy.yaml'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (event) => {
        const content = event.target?.result as string
        setYaml(content)
        setError(null)
      }
      reader.readAsText(file)
    }
  }

  const validateYaml = () => {
    setIsValidating(true)
    setError(null)

    try {
      // Basic YAML structure validation
      const lines = yaml.split('\n')
      let hasStrategy = false
      let hasIndicators = false

      for (const line of lines) {
        if (line.trim().startsWith('strategy:')) hasStrategy = true
        if (line.trim().startsWith('indicators:')) hasIndicators = true
      }

      if (!hasStrategy) {
        setError('YAML deve conter a secao "strategy:"')
        setIsValidating(false)
        return false
      }

      if (!hasIndicators) {
        setError('YAML deve conter a secao "indicators:"')
        setIsValidating(false)
        return false
      }

      setIsValidating(false)
      return true
    } catch (err: any) {
      setError(`Erro de validacao: ${err.message}`)
      setIsValidating(false)
      return false
    }
  }

  const handleSave = () => {
    if (validateYaml()) {
      onSave(yaml)
    }
  }

  const loadTemplate = () => {
    setYaml(DEFAULT_YAML_TEMPLATE)
    setError(null)
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="w-5 h-5 text-purple-400" />
          <span className="text-white font-medium">Editor YAML</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadTemplate}
            className="border-[#2a2e39] text-gray-400"
          >
            Template
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="border-[#2a2e39] text-gray-400"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            className="border-[#2a2e39] text-gray-400"
          >
            <Download className="w-4 h-4" />
          </Button>
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".yaml,.yml"
              onChange={handleUpload}
              className="hidden"
            />
            <Button
              variant="outline"
              size="sm"
              className="border-[#2a2e39] text-gray-400"
              asChild
            >
              <span><Upload className="w-4 h-4" /></span>
            </Button>
          </label>
        </div>
      </div>

      {/* Editor */}
      <div className="relative">
        <div className="flex bg-[#0d1117] rounded-lg border border-[#2a2e39] overflow-hidden">
          {/* Line numbers */}
          <div className="bg-[#161b22] px-3 py-4 text-right select-none border-r border-[#2a2e39]">
            {Array.from({ length: lineCount }, (_, i) => (
              <div key={i} className="text-gray-600 text-xs font-mono leading-6">
                {i + 1}
              </div>
            ))}
          </div>

          {/* Code area */}
          <textarea
            value={yaml}
            onChange={(e) => {
              setYaml(e.target.value)
              setError(null)
            }}
            className="flex-1 bg-transparent text-gray-300 font-mono text-sm p-4 resize-none focus:outline-none leading-6 min-h-[500px]"
            spellCheck={false}
            placeholder="Cole seu YAML aqui..."
          />
        </div>

        {/* Syntax highlighting overlay (basic) */}
        <style>{`
          .yaml-editor textarea {
            caret-color: white;
          }
        `}</style>
      </div>

      {/* Error message */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-700/50 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <span className="text-red-300 text-sm">{error}</span>
        </div>
      )}

      {/* Help text */}
      <Card className="p-4 bg-[#131722] border-[#2a2e39]">
        <p className="text-xs text-gray-400 mb-2">Dicas:</p>
        <ul className="text-xs text-gray-500 space-y-1">
          <li>• Use 2 espacos para indentacao (nao TAB)</li>
          <li>• Simbolos devem estar no formato BASEUSDT (ex: BTCUSDT)</li>
          <li>• Timeframes validos: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d</li>
          <li>• Outputs de indicadores: nadaraya_watson.upper, rsi.value, macd.histogram, etc.</li>
        </ul>
      </Card>

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
          onClick={handleSave}
          disabled={isValidating || isSaving}
          className="bg-purple-600 hover:bg-purple-700"
        >
          <Save className="w-4 h-4 mr-2" />
          {isSaving ? 'Salvando...' : 'Aplicar YAML'}
        </Button>
      </div>
    </div>
  )
}
