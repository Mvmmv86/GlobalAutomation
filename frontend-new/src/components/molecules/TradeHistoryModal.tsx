import React from 'react'
import { X, TrendingUp, TrendingDown, Clock, CheckCircle, XCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../atoms/Dialog'
import { Badge } from '../atoms/Badge'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { useQuery } from '@tanstack/react-query'
import { webhookService, TradeItem } from '@/services/webhookService'

interface TradeHistoryModalProps {
  isOpen: boolean
  onClose: () => void
  webhookId: string | null
  webhookName: string
}

export const TradeHistoryModal: React.FC<TradeHistoryModalProps> = ({
  isOpen,
  onClose,
  webhookId,
  webhookName
}) => {
  // Buscar trades do webhook
  const { data, isLoading, error } = useQuery({
    queryKey: ['webhook-trades', webhookId],
    queryFn: () => webhookService.getWebhookTrades(webhookId!),
    enabled: !!webhookId && isOpen,
  })

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 8
    }).format(price)
  }

  const getSideBadge = (side: string) => {
    return side.toLowerCase() === 'buy' ? (
      <Badge variant="success" className="flex items-center gap-1">
        <TrendingUp className="w-3 h-3" />
        COMPRA
      </Badge>
    ) : (
      <Badge variant="danger" className="flex items-center gap-1">
        <TrendingDown className="w-3 h-3" />
        VENDA
      </Badge>
    )
  }

  const getStatusBadge = (status: string) => {
    return status === 'open' ? (
      <Badge variant="warning" className="flex items-center gap-1">
        <Clock className="w-3 h-3" />
        Aberta
      </Badge>
    ) : (
      <Badge variant="secondary" className="flex items-center gap-1">
        <CheckCircle className="w-3 h-3" />
        Fechada
      </Badge>
    )
  }

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-600 dark:text-green-400'
    if (pnl < 0) return 'text-red-600 dark:text-red-400'
    return 'text-gray-600 dark:text-gray-400'
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[900px] max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>📊 Histórico de Trades - {webhookName}</span>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            >
              <X className="w-5 h-5" />
            </button>
          </DialogTitle>
        </DialogHeader>

        <div className="mt-4">
          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                <p className="text-red-800 dark:text-red-200 text-sm">
                  Erro ao carregar trades. Tente novamente.
                </p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !error && data?.trades.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-600 dark:text-gray-400">
                Nenhum trade executado ainda por este webhook.
              </p>
            </div>
          )}

          {/* Trades Table */}
          {!isLoading && !error && data && data.trades.length > 0 && (
            <div className="overflow-auto max-h-[60vh]">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Data/Hora</th>
                    <th className="px-4 py-3 text-left font-medium">Ativo</th>
                    <th className="px-4 py-3 text-left font-medium">Lado</th>
                    <th className="px-4 py-3 text-right font-medium">Preço</th>
                    <th className="px-4 py-3 text-right font-medium">Quantidade</th>
                    <th className="px-4 py-3 text-right font-medium">Margem USD</th>
                    <th className="px-4 py-3 text-center font-medium">Alavancagem</th>
                    <th className="px-4 py-3 text-center font-medium">Status</th>
                    <th className="px-4 py-3 text-right font-medium">P&L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {data.trades.map((trade: TradeItem) => (
                    <tr key={trade.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-3 whitespace-nowrap text-xs">
                        {formatDate(trade.date)}
                      </td>
                      <td className="px-4 py-3 font-medium">
                        {trade.symbol}
                      </td>
                      <td className="px-4 py-3">
                        {getSideBadge(trade.side)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        {formatPrice(trade.price)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {trade.filled_quantity > 0 ? trade.filled_quantity : trade.quantity}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-green-600 dark:text-green-400">
                        ${trade.margin_usd.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="font-medium">{trade.leverage}x</span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {getStatusBadge(trade.status)}
                      </td>
                      <td className={`px-4 py-3 text-right font-medium ${getPnLColor(trade.pnl)}`}>
                        {trade.pnl !== 0 ? (
                          <>
                            {trade.pnl > 0 ? '+' : ''}
                            {formatPrice(trade.pnl)}
                          </>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Summary */}
              <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">
                    Total de operações: {data.total}
                  </span>
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    Mostrando até 50 trades mais recentes
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
