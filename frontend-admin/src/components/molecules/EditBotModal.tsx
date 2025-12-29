/**
 * EditBotModal Component
 * Modal for editing existing bot configuration
 */
import { useState, useEffect } from 'react'
import { Bot, adminService, BotUpdateData } from '@/services/adminService'
import { Card } from '@/components/atoms/Card'
import { Button } from '@/components/atoms/Button'
import { Label } from '@/components/atoms/Label'
import { Input } from '@/components/atoms/Input'
import { X } from 'lucide-react'
import { toast } from 'sonner'

interface EditBotModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  bot: Bot | null
}

export function EditBotModal({ isOpen, onClose, onSuccess, bot }: EditBotModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState<BotUpdateData>({
    name: '',
    description: '',
    default_leverage: 10,
    default_margin_usd: 100,
    default_stop_loss_pct: 3,
    default_take_profit_pct: 5,
    default_max_positions: 3,
  })

  // Load bot data when modal opens
  useEffect(() => {
    if (bot) {
      setFormData({
        name: bot.name,
        description: bot.description,
        default_leverage: bot.default_leverage,
        default_margin_usd: bot.default_margin_usd,
        default_stop_loss_pct: bot.default_stop_loss_pct,
        default_take_profit_pct: bot.default_take_profit_pct,
        default_max_positions: bot.default_max_positions || 3,
      })
    }
  }, [bot])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!bot) return

    // Validation
    if (formData.name && formData.name.trim().length < 3) {
      toast.error('Nome deve ter pelo menos 3 caracteres')
      return
    }
    if (formData.description && formData.description.trim().length < 10) {
      toast.error('Descrição deve ter pelo menos 10 caracteres')
      return
    }

    setIsSubmitting(true)
    try {
      await adminService.updateBot(bot.id, formData)

      toast.success('Bot atualizado com sucesso!')
      onSuccess()
      onClose()
    } catch (error) {
      toast.error(`Erro ao atualizar bot: ${(error as Error).message}`)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!isOpen || !bot) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
      <Card className="max-w-2xl w-full max-h-[90vh] overflow-y-auto bg-gray-900 border-gray-800">
        <div className="p-6 border-b border-gray-800 flex justify-between items-center sticky top-0 bg-gray-900 z-10">
          <h2 className="text-2xl font-bold text-white">Editar Bot</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            disabled={isSubmitting}
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 gap-6">
            {/* Nome */}
            <div>
              <Label htmlFor="name" className="text-gray-300">Nome do Bot</Label>
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Bot Scalper BTCUSDT"
                minLength={3}
                className="bg-gray-800 border-gray-700 text-white placeholder-gray-500"
              />
            </div>

            {/* Descrição */}
            <div>
              <Label htmlFor="description" className="text-gray-300">Descrição</Label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Descreva a estratégia e características do bot..."
                minLength={10}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 text-white placeholder-gray-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
              />
              <p className="text-xs text-gray-400 mt-1">
                Mínimo 10 caracteres
              </p>
            </div>

            {/* Alavancagem e Margem */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="leverage" className="text-gray-300">Alavancagem Padrão</Label>
                <Input
                  id="leverage"
                  type="number"
                  value={formData.default_leverage}
                  onChange={(e) =>
                    setFormData({ ...formData, default_leverage: Number(e.target.value) })
                  }
                  min={1}
                  max={125}
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-xs text-gray-400 mt-1">1x até 125x</p>
              </div>

              <div>
                <Label htmlFor="margin" className="text-gray-300">Margem Padrão (USDT)</Label>
                <Input
                  id="margin"
                  type="number"
                  value={formData.default_margin_usd}
                  onChange={(e) =>
                    setFormData({ ...formData, default_margin_usd: Number(e.target.value) })
                  }
                  min={5}
                  step={0.01}
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-xs text-gray-400 mt-1">Mínimo $5</p>
              </div>
            </div>

            {/* Stop Loss e Take Profit */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="stop_loss" className="text-gray-300">Stop Loss Padrão (%)</Label>
                <Input
                  id="stop_loss"
                  type="number"
                  value={formData.default_stop_loss_pct}
                  onChange={(e) =>
                    setFormData({ ...formData, default_stop_loss_pct: Number(e.target.value) })
                  }
                  min={0.1}
                  max={50}
                  step={0.1}
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-xs text-gray-400 mt-1">0.1% até 50%</p>
              </div>

              <div>
                <Label htmlFor="take_profit" className="text-gray-300">Take Profit Padrão (%)</Label>
                <Input
                  id="take_profit"
                  type="number"
                  value={formData.default_take_profit_pct}
                  onChange={(e) =>
                    setFormData({ ...formData, default_take_profit_pct: Number(e.target.value) })
                  }
                  min={0.1}
                  max={100}
                  step={0.1}
                  className="bg-gray-800 border-gray-700 text-white"
                />
                <p className="text-xs text-gray-400 mt-1">0.1% até 100%</p>
              </div>
            </div>

            {/* Max Positions */}
            <div>
              <Label htmlFor="max_positions" className="text-gray-300">Max Posicoes Simultaneas</Label>
              <Input
                id="max_positions"
                type="number"
                value={formData.default_max_positions}
                onChange={(e) =>
                  setFormData({ ...formData, default_max_positions: Number(e.target.value) })
                }
                min={1}
                max={20}
                className="bg-gray-800 border-gray-700 text-white"
              />
              <p className="text-xs text-gray-400 mt-1">Sugestao de 1 a 20 operacoes. Cliente pode personalizar.</p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-gray-800">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1 border-gray-700 text-gray-300 hover:bg-gray-800"
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" className="flex-1" disabled={isSubmitting}>
              {isSubmitting ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
