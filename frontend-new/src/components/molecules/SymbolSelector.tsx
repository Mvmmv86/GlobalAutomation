import React, { useState, useEffect, useRef } from 'react'
import { Search, TrendingUp, TrendingDown, Star, ChevronDown } from 'lucide-react'
import { Button } from '../atoms/Button'
import { Badge } from '../atoms/Badge'
import { cn } from '@/lib/utils'
import { useSymbolDiscovery, useSymbolSearch } from '@/hooks/useApiData'
import type { DiscoveredSymbol } from '@/services/symbolDiscoveryService'

interface SymbolSelectorProps {
  selectedSymbol: string
  onSymbolChange: (symbol: string) => void
  className?: string
}

const SymbolSelector: React.FC<SymbolSelectorProps> = ({
  selectedSymbol,
  onSymbolChange,
  className
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Hooks para descoberta e pesquisa de símbolos
  const { data: discoveredSymbols = [], isLoading: isLoadingDiscovery } = useSymbolDiscovery()
  const { data: searchResults = [], isLoading: isSearching } = useSymbolSearch(searchQuery)

  // Determinar quais símbolos mostrar
  const symbolsToShow = searchQuery.length >= 2 ? searchResults : discoveredSymbols.slice(0, 20)

  // Fechar dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleSymbolSelect = (symbol: string) => {
    onSymbolChange(symbol)
    setIsOpen(false)
    setSearchQuery('')
  }

  const getCategoryIcon = (symbol: DiscoveredSymbol) => {
    if (symbol.hasPosition) {
      return symbol.positionSide === 'long' ?
        <TrendingUp className="h-3 w-3 text-success" /> :
        <TrendingDown className="h-3 w-3 text-destructive" />
    }
    if (symbol.category === 'favorite') {
      return <Star className="h-3 w-3 text-warning" />
    }
    return null
  }

  const getCategoryBadge = (symbol: DiscoveredSymbol) => {
    if (symbol.hasPosition) {
      return (
        <Badge variant="secondary" className="text-xs">
          {symbol.positionSide?.toUpperCase()}
        </Badge>
      )
    }
    if (symbol.isPopular) {
      return <Badge variant="outline" className="text-xs">Popular</Badge>
    }
    return null
  }

  return (
    <div className={cn("relative", className)} ref={dropdownRef}>
      {/* Botão Seletor */}
      <Button
        variant="outline"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full justify-between min-w-[140px]"
      >
        <div className="flex items-center space-x-2">
          <span className="font-mono font-semibold">{selectedSymbol}</span>
          {/* Mostrar ícone se o símbolo atual tem posição */}
          {discoveredSymbols.find(s => s.symbol === selectedSymbol)?.hasPosition && (
            <div className="flex items-center space-x-1">
              {getCategoryIcon(discoveredSymbols.find(s => s.symbol === selectedSymbol)!)}
            </div>
          )}
        </div>
        <ChevronDown className={cn(
          "h-4 w-4 transition-transform duration-200",
          isOpen && "transform rotate-180"
        )} />
      </Button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 z-50 mt-2 bg-background border rounded-lg shadow-lg max-h-[400px] overflow-hidden min-w-[320px] w-max max-w-[400px]">
          {/* Barra de Pesquisa */}
          <div className="p-3 border-b">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Buscar símbolo (ex: BTC, ETH)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                autoFocus
              />
            </div>
          </div>

          {/* Lista de Símbolos */}
          <div className="max-h-[300px] overflow-y-auto">
            {(isLoadingDiscovery || isSearching) ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                <div className="inline-flex items-center space-x-2">
                  <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  <span>Carregando símbolos...</span>
                </div>
              </div>
            ) : symbolsToShow.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                {searchQuery ? 'Nenhum símbolo encontrado' : 'Nenhum símbolo disponível'}
              </div>
            ) : (
              <>
                {/* Grupos de símbolos */}
                {!searchQuery && discoveredSymbols.some(s => s.hasPosition) && (
                  <>
                    <div className="px-3 py-2 text-xs font-semibold text-muted-foreground bg-muted/30">
                      POSIÇÕES ATIVAS
                    </div>
                    {discoveredSymbols
                      .filter(symbol => symbol.hasPosition)
                      .map((symbol) => (
                        <button
                          key={`${symbol.symbol}-${symbol.exchange}`}
                          onClick={() => handleSymbolSelect(symbol.symbol)}
                          className="w-full px-4 py-3 text-left hover:bg-muted/50 focus:bg-muted/50 focus:outline-none transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3 min-w-0 flex-1">
                              {getCategoryIcon(symbol)}
                              <div className="min-w-0">
                                <div className="font-mono font-semibold text-sm flex items-center gap-2">
                                  {symbol.symbol}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {symbol.exchange.toUpperCase()} • Size: {symbol.positionSize?.toFixed(4)}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center space-x-3 flex-shrink-0">
                              {getCategoryBadge(symbol)}
                              {symbol.unrealizedPnl !== undefined && (
                                <div className={cn(
                                  "text-xs font-mono font-medium px-2 py-1 rounded",
                                  symbol.unrealizedPnl >= 0 ? "text-success bg-success/10" : "text-destructive bg-destructive/10"
                                )}>
                                  {symbol.unrealizedPnl >= 0 ? '+' : ''}
                                  ${symbol.unrealizedPnl.toFixed(2)}
                                </div>
                              )}
                            </div>
                          </div>
                        </button>
                      ))}
                  </>
                )}

                {/* Símbolos populares/outros */}
                {!searchQuery && discoveredSymbols.some(s => !s.hasPosition) && (
                  <>
                    <div className="px-3 py-2 text-xs font-semibold text-muted-foreground bg-muted/30">
                      SÍMBOLOS POPULARES
                    </div>
                    {discoveredSymbols
                      .filter(symbol => !symbol.hasPosition)
                      .slice(0, 15)
                      .map((symbol) => (
                        <button
                          key={`${symbol.symbol}-${symbol.exchange}`}
                          onClick={() => handleSymbolSelect(symbol.symbol)}
                          className="w-full px-3 py-2 text-left hover:bg-muted/50 focus:bg-muted/50 focus:outline-none transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              {getCategoryIcon(symbol)}
                              <div>
                                <div className="font-mono font-semibold text-sm">
                                  {symbol.symbol}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {symbol.exchange.toUpperCase()}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              {getCategoryBadge(symbol)}
                            </div>
                          </div>
                        </button>
                      ))}
                  </>
                )}

                {/* Resultados da pesquisa */}
                {searchQuery && symbolsToShow.map((symbol) => (
                  <button
                    key={`${symbol.symbol}-${symbol.exchange}-search`}
                    onClick={() => handleSymbolSelect(symbol.symbol)}
                    className="w-full px-3 py-2 text-left hover:bg-muted/50 focus:bg-muted/50 focus:outline-none transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        {getCategoryIcon(symbol)}
                        <div>
                          <div className="font-mono font-semibold text-sm">
                            {symbol.symbol}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {symbol.exchange.toUpperCase()}
                            {symbol.hasPosition && ` • ${symbol.positionSide?.toUpperCase()}`}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {getCategoryBadge(symbol)}
                      </div>
                    </div>
                  </button>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export { SymbolSelector }
export type { SymbolSelectorProps }