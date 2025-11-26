import React, { useState } from 'react'
import { Plus, Settings, Trash2, Wifi, Star, StarOff } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { LoadingSpinner } from '../atoms/LoadingSpinner'
import { useExchangeAccounts, useCreateExchangeAccount, useDeleteExchangeAccount } from '@/hooks/useApiData'
import { CreateExchangeAccountModal, ExchangeAccountData } from '../molecules/CreateExchangeAccountModal'
import { ConfigureAccountModal, AccountConfiguration } from '../molecules/ConfigureAccountModal'
import { ConfirmationModal } from '../molecules/ConfirmationModal'

const ExchangeAccountsPage: React.FC = () => {
  const [apiStatus, setApiStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [isConfigureModalOpen, setIsConfigureModalOpen] = useState(false)
  const [selectedAccountId, setSelectedAccountId] = useState<string>('')
  const [selectedAccountName, setSelectedAccountName] = useState<string>('')
  const [selectedExchange, setSelectedExchange] = useState<string>('')
  const [showMainAccountConfirm, setShowMainAccountConfirm] = useState(false)
  const [pendingMainAccountId, setPendingMainAccountId] = useState<string>('')
  const [confirmModalData, setConfirmModalData] = useState<{ newAccount: string; currentAccount: string }>({ newAccount: '', currentAccount: '' })

  // API Data hooks
  const { data: accountsApi, isLoading: loadingAccounts, error: accountsError, refetch } = useExchangeAccounts()
  const createAccountMutation = useCreateExchangeAccount()
  const deleteAccountMutation = useDeleteExchangeAccount()

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

  const handleCreateAccount = () => {
    setIsCreateModalOpen(true)
  }

  const handleSubmitAccount = async (data: ExchangeAccountData) => {
    try {
      await createAccountMutation.mutateAsync(data)
      setIsCreateModalOpen(false)
      alert(`✅ Conta criada com sucesso! ${data.name} foi configurada na ${data.exchange}`)
      refetch()
    } catch (error: any) {
      alert(`❌ Erro ao criar conta: ${error.message || "Não foi possível criar a conta"}`)
    }
  }

  const handleConfigureAccount = (accountId: string) => {
    const account = accounts.find(acc => acc.id === accountId)
    if (account) {
      setSelectedAccountId(accountId)
      setSelectedAccountName(account.name)
      setSelectedExchange(account.exchange)
      setIsConfigureModalOpen(true)
    }
  }

  const handleSubmitConfiguration = async (config: AccountConfiguration) => {
    try {
      // Here you would normally save to backend
      console.log('💾 Saving configuration for account:', selectedAccountId, config)
      setIsConfigureModalOpen(false)
      alert(`✅ Configurações salvas com sucesso para ${selectedAccountName}!`)
    } catch (error: any) {
      alert(`❌ Erro ao salvar configurações: ${error.message || "Não foi possível salvar"}`)
    }
  }

  const handleSetAsMain = async (accountId: string) => {
    const account = accounts.find(acc => acc.id === accountId)
    // Buscar QUALQUER conta principal (não apenas da mesma exchange)
    const currentMain = accounts.find(acc => acc.isMain)

    if (currentMain && currentMain.id !== accountId) {
      // Mostrar modal de confirmação
      setPendingMainAccountId(accountId)
      setConfirmModalData({
        newAccount: account?.name || '',
        currentAccount: currentMain.name
      })
      setShowMainAccountConfirm(true)
      return
    }

    // Se não tem conta principal ainda, apenas define
    await executeSetAsMain(accountId)
  }

  const executeSetAsMain = async (accountId: string) => {
    const account = accounts.find(acc => acc.id === accountId)

    try {
      // Import the service
      const { exchangeAccountService } = await import('@/services/exchangeAccountService')

      await exchangeAccountService.setAsMainAccount(accountId)

      // Refetch accounts to update the UI
      refetch()

      alert(`✅ ${account?.name} definida como conta principal!`)
    } catch (error: any) {
      alert(`❌ Erro ao definir conta principal: ${error.message || "Não foi possível alterar"}`)
    }
  }

  const handleConfirmMainAccount = async () => {
    if (pendingMainAccountId) {
      await executeSetAsMain(pendingMainAccountId)
      setPendingMainAccountId('')
    }
  }

  const handleDeleteAccount = async (accountId: string) => {
    const account = accounts.find(acc => acc.id === accountId)
    if (confirm(`Tem certeza que deseja deletar a conta "${account?.name}"? Esta ação não pode ser desfeita.`)) {
      try {
        await deleteAccountMutation.mutateAsync(accountId)
        alert(`✅ Conta "${account?.name}" deletada com sucesso!`)
        refetch()
      } catch (error: any) {
        alert(`❌ Erro ao deletar conta: ${error.message || "Não foi possível deletar"}`)
      }
    }
  }

  // Use only real data from API
  const accounts = accountsApi || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Exchange Accounts
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Gerencie suas contas de exchanges
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
          <Button onClick={handleCreateAccount}>
            <Plus className="w-4 h-4 mr-2" />
            Nova Conta
          </Button>
        </div>
      </div>

      {/* API Error Banner */}
      {accountsError && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <p className="text-yellow-800 dark:text-yellow-200 text-sm">
            ⚠️ API indisponível - usando dados demo
          </p>
        </div>
      )}

      {/* Loading State */}
      {loadingAccounts ? (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {accounts.map((account) => (
          <Card key={account.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{account.name}</CardTitle>
                <div className="flex space-x-2">
                  <Button
                    variant={account.isMain ? "default" : "outline"}
                    size="sm"
                    onClick={() => !account.isMain && handleSetAsMain(account.id)}
                    title={account.isMain ? "Conta principal" : "Definir como conta principal"}
                    disabled={account.isMain}
                    className={account.isMain ? "bg-yellow-500 hover:bg-yellow-600 text-white" : ""}
                  >
                    <Star className={`w-4 h-4 ${account.isMain ? 'fill-current' : ''}`} />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleConfigureAccount(account.id)}
                  >
                    <Settings className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDeleteAccount(account.id)}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <CardDescription>
                Exchange: {account.exchange.charAt(0).toUpperCase() + account.exchange.slice(1)}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex space-x-2 flex-wrap">
                <Badge variant={account.isActive ? 'success' : 'secondary'}>
                  {account.isActive ? 'Ativa' : 'Inativa'}
                </Badge>
                <Badge variant={account.testnet ? 'warning' : 'default'}>
                  {account.testnet ? 'Testnet' : 'Mainnet'}
                </Badge>
                <Badge
                  variant={account.isMain ? 'default' : 'outline'}
                  className={account.isMain ? 'bg-yellow-500 text-white border-yellow-500' : ''}
                >
                  {account.isMain ? '⭐ Principal' : 'Secundária'}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
        </div>
      )}

      {/* Create Account Modal */}
      <CreateExchangeAccountModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleSubmitAccount}
        isLoading={createAccountMutation.isPending}
      />

      {/* Configure Account Modal */}
      <ConfigureAccountModal
        isOpen={isConfigureModalOpen}
        onClose={() => setIsConfigureModalOpen(false)}
        onSubmit={handleSubmitConfiguration}
        accountId={selectedAccountId}
        accountName={selectedAccountName}
        exchange={selectedExchange}
        isLoading={false}
      />

      {/* Modal de confirmação para alterar conta principal */}
      <ConfirmationModal
        isOpen={showMainAccountConfirm}
        onClose={() => {
          setShowMainAccountConfirm(false)
          setPendingMainAccountId('')
        }}
        onConfirm={handleConfirmMainAccount}
        title="Alterar Conta Principal?"
        message={`A conta "${confirmModalData.currentAccount}" está definida como principal atualmente. Deseja alterar para "${confirmModalData.newAccount}"?`}
        confirmText="Sim, Alterar"
        cancelText="Cancelar"
        variant="warning"
      />
    </div>
  )
}

export default ExchangeAccountsPage