import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../atoms/Card'
import { Button } from '../atoms/Button'

const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Configurações
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Gerencie suas preferências e configurações da conta
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Perfil</CardTitle>
            <CardDescription>
              Informações básicas da sua conta
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Nome
              </label>
              <input
                type="text"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
                defaultValue="Demo User"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Email
              </label>
              <input
                type="email"
                className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
                defaultValue="demo@tradingplatform.com"
              />
            </div>
            <Button>Salvar Alterações</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Segurança</CardTitle>
            <CardDescription>
              Configurações de segurança da conta
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Autenticação em Duas Etapas (2FA)
              </h4>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Adicione uma camada extra de segurança à sua conta
              </p>
              <Button variant="outline" className="mt-2">
                Configurar 2FA
              </Button>
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Alterar Senha
              </h4>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Atualize sua senha regularmente
              </p>
              <Button variant="outline" className="mt-2">
                Alterar Senha
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notificações</CardTitle>
            <CardDescription>
              Configure como você quer ser notificado
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Email sobre ordens
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Receba emails quando ordens forem executadas
                </p>
              </div>
              <input type="checkbox" className="rounded" defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Alertas de webhook
                </h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Seja notificado sobre falhas de webhook
                </p>
              </div>
              <input type="checkbox" className="rounded" defaultChecked />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>API Keys</CardTitle>
            <CardDescription>
              Gerencie suas chaves de API
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Demo API Key
                  </h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    tp_demo1...
                  </p>
                </div>
                <Button variant="outline" size="sm">
                  Revogar
                </Button>
              </div>
              <Button>Nova API Key</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default SettingsPage