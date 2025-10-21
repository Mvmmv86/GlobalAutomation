/**
 * CreateBotModal Component
 * Modal for creating new bots with all configuration parameters
 */
import { useState, useMemo } from 'react'
import { X, Copy, Check } from 'lucide-react'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Input } from '@/components/atoms/Input'
import { Label } from '@/components/atoms/Label'
import { adminService, BotCreateData } from '@/services/adminService'
import { toast } from 'sonner'
import { useNgrokUrl } from '@/hooks/useNgrokUrl'

interface CreateBotModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function CreateBotModal({ isOpen, onClose, onSuccess }: CreateBotModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [copied, setCopied] = useState(false)
  const { data: ngrokUrl } = useNgrokUrl()

  const [formData, setFormData] = useState<BotCreateData>({
    name: '',
    description: '',
    market_type: 'futures',
    allowed_directions: 'both',
    status: 'active',
    master_webhook_path: '',
    master_secret: '',
    default_leverage: 10,
    default_margin_usd: 100,
    default_stop_loss_pct: 3,
    default_take_profit_pct: 5,
  })

  // Generate webhook URL in real-time as user types
  const webhookUrl = useMemo(() => {
    if (!formData.master_webhook_path) return ''
    const baseUrl = ngrokUrl || import.meta.env.VITE_API_URL || 'http://localhost:8000'
    return `${baseUrl}/api/v1/bots/webhook/master/${formData.master_webhook_path}`
  }, [formData.master_webhook_path, ngrokUrl])

  const handleCopyUrl = () => {
    if (webhookUrl) {
      navigator.clipboard.writeText(webhookUrl)
      setCopied(true)
      toast.success('URL copiada para a área de transferência!')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Generate webhook path automatically from bot name
  const generateWebhookPath = (name: string) => {
    if (!name.trim()) return ''

    // Convert to lowercase, remove special chars, replace spaces with hyphens
    const slug = name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove accents
      .replace(/[^a-z0-9\s-]/g, '') // Remove special chars
      .replace(/\s+/g, '-') // Replace spaces with hyphens
      .replace(/-+/g, '-') // Replace multiple hyphens with single
      .substring(0, 20) // Limit to 20 chars to leave room for suffix

    // Generate guaranteed 12-char random suffix (ensures 16+ total with hyphen)
    const randomSuffix = Array.from({ length: 12 }, () =>
      Math.random().toString(36).charAt(2)
    ).join('')

    const fullPath = `${slug}-${randomSuffix}`

    // Ensure minimum 16 characters
    if (fullPath.length < 16) {
      // Pad with more random chars if needed
      const padding = Array.from({ length: 16 - fullPath.length }, () =>
        Math.random().toString(36).charAt(2)
      ).join('')
      return fullPath + padding
    }

    return fullPath
  }

  // Auto-generate webhook path when name changes (only if path is empty or was auto-generated)
  const handleNameChange = (name: string) => {
    setFormData(prev => ({
      ...prev,
      name,
      // Auto-generate path if it's empty or looks auto-generated
      master_webhook_path: prev.master_webhook_path === '' || prev.master_webhook_path.match(/-[a-z0-9]{8}$/)
        ? generateWebhookPath(name)
        : prev.master_webhook_path
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    console.log('🚀 STEP 1: Form submitted!')
    console.log('🚀 Name:', formData.name)
    console.log('🚀 Description:', formData.description)
    console.log('🚀 Webhook Path:', formData.master_webhook_path)
    console.log('🚀 Webhook Path Length:', formData.master_webhook_path?.length)

    // Validation
    console.log('🔍 STEP 2: Starting validation...')
    if (!formData.name.trim()) {
      console.log('❌ Name validation failed')
      toast.error('Nome do bot é obrigatório')
      return
    }
    console.log('✅ Name OK')

    if (!formData.description.trim()) {
      console.log('❌ Description validation failed (empty)')
      toast.error('Descrição é obrigatória')
      return
    }
    if (formData.description.trim().length < 10) {
      console.log('❌ Description validation failed (too short):', formData.description.trim().length)
      toast.error('Descrição deve ter pelo menos 10 caracteres')
      return
    }
    console.log('✅ Description OK')

    if (!formData.master_webhook_path.trim()) {
      console.log('❌ Webhook path validation failed (empty)')
      toast.error('Webhook Path é obrigatório (mín. 16 caracteres)')
      return
    }
    console.log('✅ Webhook path not empty')

    if (formData.master_webhook_path.trim().length < 16) {
      console.log('❌ Webhook path validation failed (length < 16):', formData.master_webhook_path.trim().length)
      toast.error('Webhook Path deve ter pelo menos 16 caracteres para segurança')
      return
    }
    console.log('✅ Webhook path length OK:', formData.master_webhook_path.trim().length)

    console.log('✅✅✅ STEP 3: ALL VALIDATION PASSED!')
    setIsSubmitting(true)
    try {
      console.log('📡 STEP 4: Calling adminService.createBot...')
      const result = await adminService.createBot(formData)
      console.log('✅ STEP 5: Bot created successfully!', result)

      // Show success with webhook URL
      toast.success(
        <div>
          <p className="font-bold mb-2">✅ Bot criado com sucesso!</p>
          <p className="text-sm mb-2">ID: {result.bot_id}</p>
          <div className="bg-gray-800 p-2 rounded mt-2">
            <p className="text-xs text-gray-400 mb-1">URL do Webhook (copie para o TradingView):</p>
            <p className="text-xs font-mono break-all select-all">{result.webhook_url}</p>
          </div>
        </div>,
        { duration: 10000 } // Mostra por 10 segundos
      )

      onSuccess()
      resetForm()
    } catch (error) {
      toast.error(`Erro ao criar bot: ${(error as Error).message}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      market_type: 'futures',
      allowed_directions: 'both',
      status: 'active',
      master_webhook_path: '',
      master_secret: '',
      default_leverage: 10,
      default_margin_usd: 100,
      default_stop_loss_pct: 3,
      default_take_profit_pct: 5,
    })
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto bg-gray-900 border-gray-800">
        <div className="p-6 border-b border-gray-800 flex justify-between items-center sticky top-0 bg-gray-900 z-10">
          <h2 className="text-2xl font-bold text-white">Criar Novo Bot</h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            disabled={isSubmitting}
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Informações Básicas</h3>

            <div>
              <Label htmlFor="name" className="text-gray-300">Nome do Bot *</Label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="Ex: Bot Scalper BTCUSDT"
                required
                className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                💡 O webhook path será gerado automaticamente baseado neste nome
              </p>
            </div>

            <div>
              <Label htmlFor="description" className="text-gray-300">Descrição *</Label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descreva a estratégia e características do bot..."
                required
                minLength={10}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 text-white placeholder-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
              />
              <p className="text-xs text-gray-400 mt-1">
                Mínimo 10 caracteres
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="market_type" className="text-gray-300">Tipo de Mercado *</Label>
                <select
                  id="market_type"
                  value={formData.market_type}
                  onChange={(e) => setFormData({ ...formData, market_type: e.target.value as 'spot' | 'futures' })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="futures">FUTURES</option>
                  <option value="spot">SPOT</option>
                </select>
              </div>

              <div>
                <Label htmlFor="status" className="text-gray-300">Status Inicial</Label>
                <select
                  id="status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value as 'active' | 'paused' })}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="active">Ativo</option>
                  <option value="paused">Pausado</option>
                </select>
              </div>
            </div>

            {/* Allowed Directions */}
            <div>
              <Label htmlFor="allowed_directions" className="text-gray-300">
                Direções Permitidas *
              </Label>
              <select
                id="allowed_directions"
                value={formData.allowed_directions}
                onChange={(e) => setFormData({ ...formData, allowed_directions: e.target.value as 'buy_only' | 'sell_only' | 'both' })}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 text-white rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="both">Ambos (Long e Short)</option>
                <option value="buy_only">Apenas Long (Buy)</option>
                <option value="sell_only">Apenas Short (Sell)</option>
              </select>
              <p className="text-sm text-gray-400 mt-1">
                Define quais sinais o bot aceita. 'Ambos' = opera Long e Short
              </p>
            </div>
          </div>

          {/* Webhook Configuration */}
          <div className="space-y-4 pt-6 border-t border-gray-800">
            <h3 className="text-lg font-semibold text-white">Configuração do Webhook</h3>

            <div>
              <Label htmlFor="master_webhook_path" className="text-gray-300">Webhook Path (Token Secreto) *</Label>
              <Input
                id="master_webhook_path"
                type="text"
                value={formData.master_webhook_path}
                onChange={(e) => setFormData({ ...formData, master_webhook_path: e.target.value })}
                placeholder="exemplo: a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                required
                minLength={16}
                className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
              />
              <p className="text-sm text-yellow-400 mt-1">
                ⚠️ Este path é o TOKEN DE SEGURANÇA. Mín. 16 caracteres. Guarde-o em segredo!
              </p>

              {/* Real-time Webhook URL Preview */}
              {webhookUrl && (
                <div className="mt-3 p-3 bg-green-900/20 border border-green-700/50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-semibold text-green-400">
                      ✅ URL do Webhook (copie para o TradingView):
                    </p>
                    <button
                      type="button"
                      onClick={handleCopyUrl}
                      className="flex items-center gap-1 px-2 py-1 text-xs bg-green-700 hover:bg-green-600 text-white rounded transition-colors"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3" />
                          Copiado!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          Copiar
                        </>
                      )}
                    </button>
                  </div>
                  <p className="text-xs font-mono text-green-300 break-all select-all bg-gray-900/50 p-2 rounded">
                    {webhookUrl}
                  </p>
                  <p className="text-xs text-green-400/70 mt-2">
                    💡 Esta URL será usada no TradingView para enviar sinais de trading
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Trading Parameters */}
          <div className="space-y-4 pt-6 border-t border-gray-800">
            <h3 className="text-lg font-semibold text-white">Parâmetros de Trading (Padrões)</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="default_leverage" className="text-gray-300">Alavancagem Padrão *</Label>
                <Input
                  id="default_leverage"
                  type="number"
                  min="1"
                  max="125"
                  value={formData.default_leverage}
                  onChange={(e) => setFormData({ ...formData, default_leverage: Number(e.target.value) })}
                  required
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-sm text-gray-400 mt-1">1x - 125x</p>
              </div>

              <div>
                <Label htmlFor="default_margin_usd" className="text-gray-300">Margem Padrão (USD) *</Label>
                <Input
                  id="default_margin_usd"
                  type="number"
                  min="10"
                  step="0.01"
                  value={formData.default_margin_usd}
                  onChange={(e) => setFormData({ ...formData, default_margin_usd: Number(e.target.value) })}
                  required
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-sm text-gray-400 mt-1">Mínimo: $10</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="default_stop_loss_pct" className="text-gray-300">Stop Loss Padrão (%) *</Label>
                <Input
                  id="default_stop_loss_pct"
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={formData.default_stop_loss_pct}
                  onChange={(e) => setFormData({ ...formData, default_stop_loss_pct: Number(e.target.value) })}
                  required
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-sm text-gray-400 mt-1">Ex: 3 = 3% de perda</p>
              </div>

              <div>
                <Label htmlFor="default_take_profit_pct" className="text-gray-300">Take Profit Padrão (%) *</Label>
                <Input
                  id="default_take_profit_pct"
                  type="number"
                  min="0.1"
                  max="1000"
                  step="0.1"
                  value={formData.default_take_profit_pct}
                  onChange={(e) => setFormData({ ...formData, default_take_profit_pct: Number(e.target.value) })}
                  required
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-sm text-gray-400 mt-1">Ex: 5 = 5% de lucro</p>
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="p-4 bg-blue-900 rounded-lg border border-blue-700">
            <h4 className="font-semibold text-blue-100 mb-2">Resumo da Configuração</h4>
            <div className="grid grid-cols-2 gap-2 text-sm text-blue-200">
              <div>
                <span className="font-medium">Tipo:</span> {formData.market_type.toUpperCase()}
              </div>
              <div>
                <span className="font-medium">Alavancagem:</span> {formData.default_leverage}x
              </div>
              <div>
                <span className="font-medium">Margem:</span> ${formData.default_margin_usd}
              </div>
              <div>
                <span className="font-medium">SL/TP:</span> {formData.default_stop_loss_pct}% / {formData.default_take_profit_pct}%
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-6 border-t border-gray-800">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              className="flex-1"
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Criando...' : 'Criar Bot'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
