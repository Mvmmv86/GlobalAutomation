import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '../atoms/Button'
import { Input } from '../atoms/Input'
import { Label } from '../atoms/Label'
import { LoadingSpinner } from '../atoms/LoadingSpinner'

const loginSchema = z.object({
  email: z.string().email('Email inválido'),
  password: z.string().min(6, 'Senha deve ter pelo menos 6 caracteres'),
  totpCode: z.string().optional(),
})

type LoginFormData = z.infer<typeof loginSchema>

export const LoginPage: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false)
  const [showTotpInput, setShowTotpInput] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { login } = useAuth()
  const navigate = useNavigate()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormData) => {
    console.log('📝 Form submitted:', data.email)
    setIsLoading(true)
    setError(null)

    try {
      console.log('🚀 Calling login function...')
      await login(data)
      console.log('✅ Login successful, navigating to dashboard...')
      // Redirect to dashboard after successful login
      navigate('/dashboard')
      console.log('🎯 Navigation to dashboard completed')
    } catch (err: any) {
      console.error('❌ Login form error:', err)
      if (err.response?.data?.message?.includes('2FA') || err.response?.data?.message?.includes('TOTP')) {
        setShowTotpInput(true)
        setError('Código de autenticação em duas etapas necessário')
      } else {
        setError(err.response?.data?.message || err.message || 'Erro ao fazer login')
      }
    } finally {
      setIsLoading(false)
      console.log('🏁 Form submission completed')
    }
  }

  return (
    <div>
      <div className="mb-6 text-center">
        <h2 className="text-3xl font-bold text-emerald-500">
          Trading Platform
        </h2>
        <h3 className="mt-2 text-xl font-semibold text-white">
          Portal Admin
        </h3>
        <p className="mt-2 text-sm text-gray-400">
          Acesse o painel administrativo
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {error && (
          <div className="p-3 text-sm text-red-400 bg-red-900/20 border border-red-800 rounded-md">
            {error}
          </div>
        )}

        <div>
          <Label htmlFor="email" className="text-gray-300">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="seu@email.com"
            className="mt-1 bg-[#2a2e39] border-[#3a3f4b] text-white placeholder:text-gray-500"
            autoComplete="email"
            {...register('email')}
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-400">
              {errors.email.message}
            </p>
          )}
        </div>

        <div>
          <Label htmlFor="password" className="text-gray-300">Senha</Label>
          <div className="relative mt-1">
            <Input
              id="password"
              type={showPassword ? 'text' : 'password'}
              placeholder="Sua senha"
              className="pr-10 bg-[#2a2e39] border-[#3a3f4b] text-white placeholder:text-gray-500"
              autoComplete="current-password"
              {...register('password')}
            />
            <button
              type="button"
              className="absolute inset-y-0 right-0 flex items-center pr-3"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4 text-gray-400" />
              ) : (
                <Eye className="h-4 w-4 text-gray-400" />
              )}
            </button>
          </div>
          {errors.password && (
            <p className="mt-1 text-sm text-red-400">
              {errors.password.message}
            </p>
          )}
        </div>

        {showTotpInput && (
          <div>
            <Label htmlFor="totpCode" className="text-gray-300">Código de Autenticação (2FA)</Label>
            <Input
              id="totpCode"
              type="text"
              placeholder="123456"
              className="mt-1 bg-[#2a2e39] border-[#3a3f4b] text-white placeholder:text-gray-500"
              maxLength={6}
              autoComplete="one-time-code"
              {...register('totpCode')}
            />
            {errors.totpCode && (
              <p className="mt-1 text-sm text-red-400">
                {errors.totpCode.message}
              </p>
            )}
          </div>
        )}

        <Button
          type="submit"
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
          disabled={isLoading}
        >
          {isLoading ? (
            <LoadingSpinner size="sm" text="Entrando..." />
          ) : (
            'Entrar no Admin'
          )}
        </Button>

        <div className="text-center mt-4">
          <p className="text-xs text-gray-500">
            Acesso restrito a administradores autorizados
          </p>
        </div>
      </form>
    </div>
  )
}