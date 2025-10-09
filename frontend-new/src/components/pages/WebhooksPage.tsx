import React, { useState } from 'react'
import { Plus, Copy, Settings, Trash2, Wifi, Edit, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { webhookService, WebhookData } from '@/services/webhookService'
import { CreateWebhookModalSimple, WebhookSimpleData } from '../molecules/CreateWebhookModalSimple'
import { EditWebhookModalSimple, WebhookEditData } from '../molecules/EditWebhookModalSimple'

const WebhooksPage: React.FC = () => {
  const queryClient = useQueryClient()

  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [selectedWebhook, setSelectedWebhook] = useState<WebhookEditData | null>(null)

  // React Query hooks para API real
  const { data: webhooks = [], isLoading: loadingWebhooks, error: webhooksError } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => webhookService.getWebhooks()
  })

  const createMutation = useMutation({
    mutationFn: (data: WebhookSimpleData) => webhookService.createWebhook(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      alert('✅ Webhook criado com sucesso!')
    },
    onError: (error: any) => {
      alert(`❌ Erro ao criar webhook: ${error.message || 'Erro desconhecido'}`)
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ webhookId, data }: { webhookId: string, data: any }) =>
      webhookService.updateWebhook(webhookId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      alert('✅ Webhook atualizado com sucesso!')
    },
    onError: (error: any) => {
      alert(`❌ Erro ao atualizar webhook: ${error.message || 'Erro desconhecido'}`)
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (webhookId: string) => webhookService.deleteWebhook(webhookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      alert('✅ Webhook deletado com sucesso!')
    },
    onError: (error: any) => {
      alert(`❌ Erro ao deletar webhook: ${error.message || 'Erro desconhecido'}`)
    }
  })

  const testApiConnection = async () => {
    setApiStatus('testing')
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/`)
      if (response.ok) {
        setApiStatus('success')
      } else {
        setApiStatus('error')
      }
    } catch (error) {
      setApiStatus('error')
    }
  }

  const handleCreateWebhook = () => {
    setIsCreateModalOpen(true)
  }

  const handleSubmitCreate = async (data: WebhookSimpleData) => {
    await createMutation.mutateAsync(data)
  }

  const handleCopyUrl = (urlPath: string) => {
    const fullUrl = `${import.meta.env.VITE_API_URL}/api/v1/webhooks/tradingview/${urlPath}`
    navigator.clipboard.writeText(fullUrl)
    alert('URL copiada para clipboard!')
  }

  const handleEditWebhook = (webhook: WebhookData) => {
    setSelectedWebhook({
      id: webhook.id || '',
      name: webhook.name,
      url_path: webhook.url_path,
      status: webhook.status,
      secret: webhook.secret
    })
    setIsEditModalOpen(true)
  }

  const handleSubmitEdit = async (webhookId: string, data: WebhookEditData) => {
    await updateMutation.mutateAsync({ webhookId, data })
  }

  const handleDeleteWebhook = (webhookId: string, webhookName: string) => {
    if (confirm(`Tem certeza que deseja deletar o webhook "${webhookName}"?`)) {
      deleteMutation.mutate(webhookId)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return <Badge variant="success">Ativo</Badge>
      case 'paused':
        return <Badge variant="warning">Pausado</Badge>
      case 'disabled':
        return <Badge variant="secondary">Desabilitado</Badge>
      case 'error':
        return <Badge variant="danger">Erro</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Webhooks
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Configure webhooks para receber sinais de trading
          </p>
        </div>
        <div className="flex space-x-2">
          <Button 
            onClick={testApiConnection}
            variant={apiStatus === 'success' ? 'success' : apiStatus === 'error' ? 'danger' : 'outline'}
            disabled={apiStatus === 'testing'}
          >
            <Wifi className="w-4 h-4 mr-2" />
            {apiStatus === 'testing' ? 'Testando...' : 'Testar API'}
          </Button>
          <Button onClick={handleCreateWebhook}>
            <Plus className="w-4 h-4 mr-2" />
            Novo Webhook
          </Button>
        </div>
      </div>

      {/* API Error Banner */}
      {webhooksError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <p className="text-red-800 dark:text-red-200 text-sm">
              ❌ Erro ao carregar webhooks da API - verifique se o backend está rodando
            </p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loadingWebhooks && webhooks.length === 0 && (
        <div className="bg-gray-50 dark:bg-gray-900/20 border border-gray-200 dark:border-gray-800 rounded-lg p-8 text-center">
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Nenhum webhook cadastrado ainda
          </p>
          <Button onClick={handleCreateWebhook}>
            <Plus className="w-4 h-4 mr-2" />
            Criar Primeiro Webhook
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loadingWebhooks ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {webhooks.map((webhook) => (
          <Card key={webhook.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-lg">{webhook.name}</CardTitle>
                  <CardDescription className="flex items-center space-x-2 mt-1">
                    <code className="text-sm bg-muted px-2 py-1 rounded">
                      {webhook.url_path}
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopyUrl(webhook.url_path)}
                    >
                      <Copy className="w-4 h-4" />
                    </Button>
                  </CardDescription>
                </div>
                <div className="flex space-x-2">
                  {getStatusBadge(webhook.status)}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEditWebhook(webhook)}
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteWebhook(webhook.id || '', webhook.name)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Total Deliveries</p>
                  <p className="font-medium">{webhook.total_deliveries || 0}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Sucessos</p>
                  <p className="font-medium text-success">{webhook.successful_deliveries || 0}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Falhas</p>
                  <p className="font-medium text-danger">{webhook.failed_deliveries || 0}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Taxa de Sucesso</p>
                  <p className="font-medium">{webhook.success_rate?.toFixed(1) || '0'}%</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        </div>
      )}

      {/* Create Webhook Modal */}
      <CreateWebhookModalSimple
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleSubmitCreate}
        isLoading={createMutation.isPending}
      />

      {/* Edit Webhook Modal */}
      <EditWebhookModalSimple
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        onSubmit={handleSubmitEdit}
        isLoading={updateMutation.isPending}
        webhook={selectedWebhook}
      />
    </div>
  )
}

export default WebhooksPage