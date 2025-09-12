import React, { useState } from 'react'
import { Plus, Copy, Settings, Trash2, Wifi } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { useWebhooks, useCreateWebhook } from '@/hooks/useApiData'
import { CreateWebhookModal, WebhookData } from '../molecules/CreateWebhookModal'
import { ConfigureWebhookModal, WebhookConfiguration } from '../molecules/ConfigureWebhookModal'

const WebhooksPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isConfigureModalOpen, setIsConfigureModalOpen] = useState(false)
  const [selectedWebhookId, setSelectedWebhookId] = useState<string>('')
  const [selectedWebhookName, setSelectedWebhookName] = useState<string>('')
  const [selectedWebhookStatus, setSelectedWebhookStatus] = useState<string>('')

  // API Data hooks
  const { data: webhooksApi, isLoading: loadingWebhooks, error: webhooksError } = useWebhooks()
  const createWebhookMutation = useCreateWebhook()

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

  const handleSubmitWebhook = async (data: WebhookData) => {
    try {
      // Here you would normally save to backend
      console.log('💾 Creating webhook:', data)
      setIsCreateModalOpen(false)
      alert(`✅ Webhook "${data.name}" criado com sucesso!`)
      // In a real app, you would refetch webhooks here
    } catch (error: any) {
      alert(`❌ Erro ao criar webhook: ${error.message || "Não foi possível criar"}`)
    }
  }

  const handleCopyUrl = (urlPath: string) => {
    const fullUrl = `${import.meta.env.VITE_API_URL}/webhook/${urlPath}`
    navigator.clipboard.writeText(fullUrl)
    alert('URL copiada para clipboard!')
  }

  const handleConfigureWebhook = (webhookId: string) => {
    const webhook = webhooks.find(w => w.id === webhookId)
    if (webhook) {
      setSelectedWebhookId(webhookId)
      setSelectedWebhookName(webhook.name)
      setSelectedWebhookStatus(webhook.status)
      setIsConfigureModalOpen(true)
    }
  }

  const handleSubmitConfiguration = async (config: WebhookConfiguration) => {
    try {
      // Here you would normally save to backend
      console.log('💾 Saving webhook configuration for:', selectedWebhookId, config)
      setIsConfigureModalOpen(false)
      alert(`✅ Configurações salvas com sucesso para "${selectedWebhookName}"!`)
    } catch (error: any) {
      alert(`❌ Erro ao salvar configurações: ${error.message || "Não foi possível salvar"}`)
    }
  }

  const handleDeleteWebhook = (webhookId: string) => {
    if (confirm('Tem certeza que deseja deletar este webhook?')) {
      alert(`Webhook ${webhookId} deletado - implementação em breve!`)
    }
  }

  // Mock data for fallback
  const mockWebhooks = [
    {
      id: '1',
      name: 'TradingView Strategy 1',
      urlPath: 'webhook_abc123',
      status: 'active',
      totalDeliveries: 156,
      successfulDeliveries: 154,
      failedDeliveries: 2,
    },
    {
      id: '2',
      name: 'Scalping Bot',
      urlPath: 'webhook_def456',
      status: 'paused',
      totalDeliveries: 89,
      successfulDeliveries: 87,
      failedDeliveries: 2,
    },
  ]

  // Use real data when available, fallback to mock data
  const webhooks = webhooksApi || mockWebhooks

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
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <p className="text-yellow-800 dark:text-yellow-200 text-sm">
            ⚠️ API indisponível - usando dados demo
          </p>
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
                      {webhook.urlPath}
                    </code>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => handleCopyUrl(webhook.urlPath)}
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
                    onClick={() => handleConfigureWebhook(webhook.id)}
                  >
                    <Settings className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleDeleteWebhook(webhook.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Total</p>
                  <p className="font-medium">{webhook.totalDeliveries}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Sucessos</p>
                  <p className="font-medium text-success">{webhook.successfulDeliveries}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Falhas</p>
                  <p className="font-medium text-danger">{webhook.failedDeliveries}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        </div>
      )}

      {/* Create Webhook Modal */}
      <CreateWebhookModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleSubmitWebhook}
        isLoading={false}
      />

      {/* Configure Webhook Modal */}
      <ConfigureWebhookModal
        isOpen={isConfigureModalOpen}
        onClose={() => setIsConfigureModalOpen(false)}
        onSubmit={handleSubmitConfiguration}
        webhookId={selectedWebhookId}
        webhookName={selectedWebhookName}
        webhookStatus={selectedWebhookStatus}
        isLoading={false}
      />
    </div>
  )
}

export default WebhooksPage