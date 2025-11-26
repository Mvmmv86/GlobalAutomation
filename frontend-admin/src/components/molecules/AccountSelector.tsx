import React from 'react'
import { Building2, Wifi, WifiOff } from 'lucide-react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../atoms/Select'
import { Badge } from '../atoms/Badge'
import { cn } from '@/lib/utils'

interface ExchangeAccount {
  id: string
  name: string
  exchange: 'binance' | 'bybit' | 'okx'
  testnet: boolean
  isActive: boolean
  balance?: number
  currency?: string
}

interface AccountSelectorProps {
  accounts: ExchangeAccount[]
  selectedAccountId?: string
  onAccountChange: (accountId: string) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

const AccountSelector: React.FC<AccountSelectorProps> = ({
  accounts,
  selectedAccountId,
  onAccountChange,
  placeholder = "Select an account",
  className,
  disabled = false
}) => {
  const selectedAccount = accounts.find(acc => acc.id === selectedAccountId)

  const exchangeColors = {
    binance: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
    bybit: 'bg-orange-500/10 text-orange-600 border-orange-500/20',
    okx: 'bg-blue-500/10 text-blue-600 border-blue-500/20'
  }

  const formatBalance = (balance?: number, currency: string = 'USDT') => {
    if (balance === undefined) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(balance).replace('$', '') + ` ${currency}`
  }

  return (
    <Select value={selectedAccountId} onValueChange={onAccountChange} disabled={disabled}>
      <SelectTrigger className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder}>
          {selectedAccount && (
            <div className="flex items-center space-x-2">
              <Building2 className="h-4 w-4" />
              <span className="truncate">{selectedAccount.name}</span>
              <Badge 
                variant="outline" 
                className={cn("text-xs", exchangeColors[selectedAccount.exchange])}
              >
                {selectedAccount.exchange.toUpperCase()}
              </Badge>
              {selectedAccount.testnet && (
                <Badge variant="secondary" className="text-xs">
                  TESTNET
                </Badge>
              )}
              {selectedAccount.isActive ? (
                <Wifi className="h-3 w-3 text-success" />
              ) : (
                <WifiOff className="h-3 w-3 text-destructive" />
              )}
            </div>
          )}
        </SelectValue>
      </SelectTrigger>
      
      <SelectContent>
        {accounts.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground text-center">
            No accounts available
          </div>
        ) : (
          accounts.map((account) => (
            <SelectItem key={account.id} value={account.id}>
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <Building2 className="h-4 w-4 flex-shrink-0" />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="truncate font-medium">{account.name}</span>
                      <Badge 
                        variant="outline" 
                        className={cn("text-xs flex-shrink-0", exchangeColors[account.exchange])}
                      >
                        {account.exchange.toUpperCase()}
                      </Badge>
                    </div>
                    
                    <div className="flex items-center space-x-2 mt-1">
                      {account.testnet && (
                        <Badge variant="secondary" className="text-xs">
                          TESTNET
                        </Badge>
                      )}
                      
                      <span className="text-xs text-muted-foreground">
                        Balance: {formatBalance(account.balance, account.currency)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-1 flex-shrink-0 ml-2">
                  {account.isActive ? (
                    <div className="flex items-center space-x-1">
                      <Wifi className="h-3 w-3 text-success" />
                      <span className="text-xs text-success">Online</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-1">
                      <WifiOff className="h-3 w-3 text-destructive" />
                      <span className="text-xs text-destructive">Offline</span>
                    </div>
                  )}
                </div>
              </div>
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  )
}

export { AccountSelector }
export type { AccountSelectorProps, ExchangeAccount }