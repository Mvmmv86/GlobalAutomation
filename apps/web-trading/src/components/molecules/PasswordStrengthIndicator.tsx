import React from 'react'
import { Check, X, AlertCircle } from 'lucide-react'

interface PasswordRule {
  id: string
  label: string
  regex?: RegExp
  validator?: (password: string) => boolean
  passed: boolean
}

interface PasswordStrengthIndicatorProps {
  password: string
  className?: string
}

export const PasswordStrengthIndicator: React.FC<PasswordStrengthIndicatorProps> = ({
  password,
  className = '',
}) => {
  const rules: PasswordRule[] = [
    {
      id: 'length',
      label: 'Pelo menos 8 caracteres',
      validator: (pwd) => pwd.length >= 8,
      passed: password.length >= 8,
    },
    {
      id: 'lowercase',
      label: 'Pelo menos 1 letra minúscula (a-z)',
      regex: /[a-z]/,
      passed: /[a-z]/.test(password),
    },
    {
      id: 'uppercase',
      label: 'Pelo menos 1 letra maiúscula (A-Z)',
      regex: /[A-Z]/,
      passed: /[A-Z]/.test(password),
    },
    {
      id: 'number',
      label: 'Pelo menos 1 número (0-9)',
      regex: /[0-9]/,
      passed: /[0-9]/.test(password),
    },
    {
      id: 'special',
      label: 'Pelo menos 1 símbolo (!@#$%^&*)',
      regex: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/,
      passed: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
    },
    {
      id: 'no-common',
      label: 'Não deve ser uma senha comum',
      validator: (pwd) => {
        const commonPasswords = [
          '123456', 'password', 'qwerty', 'abc123', 
          '12345678', '123456789', 'qwerty123', 'password123'
        ]
        return !commonPasswords.includes(pwd.toLowerCase())
      },
      passed: (() => {
        const commonPasswords = [
          '123456', 'password', 'qwerty', 'abc123', 
          '12345678', '123456789', 'qwerty123', 'password123'
        ]
        return !commonPasswords.includes(password.toLowerCase())
      })(),
    },
    {
      id: 'no-sequence',
      label: 'Evitar sequências (123, abc)',
      validator: (pwd) => {
        // Check for numeric sequences
        for (let i = 0; i < pwd.length - 2; i++) {
          const char1 = pwd.charCodeAt(i)
          const char2 = pwd.charCodeAt(i + 1)
          const char3 = pwd.charCodeAt(i + 2)
          
          if (char2 === char1 + 1 && char3 === char2 + 1) {
            return false
          }
        }
        return true
      },
      passed: (() => {
        for (let i = 0; i < password.length - 2; i++) {
          const char1 = password.charCodeAt(i)
          const char2 = password.charCodeAt(i + 1)
          const char3 = password.charCodeAt(i + 2)
          
          if (char2 === char1 + 1 && char3 === char2 + 1) {
            return false
          }
        }
        return true
      })(),
    },
  ]

  const passedRules = rules.filter(rule => rule.passed).length
  const totalRules = rules.length
  const strengthPercentage = (passedRules / totalRules) * 100

  const getStrengthColor = () => {
    if (strengthPercentage < 40) return 'text-red-600 bg-red-100'
    if (strengthPercentage < 70) return 'text-yellow-600 bg-yellow-100'
    return 'text-green-600 bg-green-100'
  }

  const getStrengthLabel = () => {
    if (strengthPercentage < 40) return 'Fraca'
    if (strengthPercentage < 70) return 'Média'
    return 'Forte'
  }

  if (!password) return null

  return (
    <div className={`p-4 border rounded-lg bg-gray-50 dark:bg-gray-800 dark:border-gray-700 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white">
          Força da senha
        </h4>
        <span className={`px-2 py-1 text-xs font-medium rounded ${getStrengthColor()}`}>
          {getStrengthLabel()} ({passedRules}/{totalRules})
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-4 dark:bg-gray-700">
        <div
          className={`h-2 rounded-full transition-all duration-300 ${
            strengthPercentage < 40
              ? 'bg-red-500'
              : strengthPercentage < 70
              ? 'bg-yellow-500'
              : 'bg-green-500'
          }`}
          style={{ width: `${strengthPercentage}%` }}
        />
      </div>

      {/* Rules checklist */}
      <div className="space-y-2">
        {rules.map((rule) => (
          <div key={rule.id} className="flex items-center space-x-2">
            {rule.passed ? (
              <Check className="h-4 w-4 text-green-500" />
            ) : (
              <X className="h-4 w-4 text-red-500" />
            )}
            <span
              className={`text-xs ${
                rule.passed
                  ? 'text-green-700 dark:text-green-400'
                  : 'text-red-700 dark:text-red-400'
              }`}
            >
              {rule.label}
            </span>
          </div>
        ))}
      </div>

      {/* Dicas adicionais */}
      {strengthPercentage < 70 && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md dark:bg-blue-900/10 dark:border-blue-800">
          <div className="flex items-start space-x-2">
            <AlertCircle className="h-4 w-4 text-blue-500 mt-0.5" />
            <div>
              <h5 className="text-xs font-medium text-blue-800 dark:text-blue-400">
                Dicas para uma senha forte:
              </h5>
              <ul className="mt-1 text-xs text-blue-700 dark:text-blue-300 space-y-1">
                <li>• Use uma frase como base: "MeuGato#Preto123!"</li>
                <li>• Combine palavras não relacionadas: "Piano$Verde2024"</li>
                <li>• Evite informações pessoais (nome, aniversário)</li>
                <li>• Use caracteres especiais: !@#$%^&*</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}