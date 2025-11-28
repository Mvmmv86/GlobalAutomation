import { apiClient } from '@/lib/api'

export interface DiscoveredSymbol {
  symbol: string
  exchange: string
  hasPosition: boolean
  positionSide?: 'long' | 'short'
  positionSize?: number
  entryPrice?: number
  unrealizedPnl?: number
  isPopular?: boolean
  category: 'position' | 'popular' | 'favorite' | 'recent' | 'all'
  baseAsset?: string
  marketType?: string
}

// Interface para resposta da API de símbolos
interface SymbolsApiResponse {
  success: boolean
  count: number
  filters: {
    exchange: string
    market_type: string
    search: string | null
  }
  symbols: Array<{
    symbol: string
    baseAsset: string
    quoteAsset: string
    exchange: string
    marketType: string
    symbolBingX?: string  // Formato BingX (ex: "BTC-USDT")
  }>
}

// Símbolos populares (fallback caso API falhe)
const POPULAR_SYMBOLS_FALLBACK = [
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
  'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT',
  'LINKUSDT', 'ATOMUSDT', 'LTCUSDT', 'NEARUSDT', 'UNIUSDT',
  'APTUSDT', 'ARBUSDT', 'OPUSDT', 'INJUSDT', 'SUIUSDT'
]

// Cache local para símbolos (evita chamadas repetidas)
let symbolsCache: {
  data: DiscoveredSymbol[]
  timestamp: number
  exchange: string | null
  marketType: string | null
} | null = null
const CACHE_TTL = 5 * 60 * 1000  // 5 minutos

export const symbolDiscoveryService = {
  /**
   * Busca TODOS os símbolos disponíveis das exchanges via API pública
   * Combina Binance + BingX para máxima cobertura
   */
  async fetchAllSymbols(
    exchange: string | null = null,
    marketType: string = 'futures'
  ): Promise<DiscoveredSymbol[]> {
    try {
      // Verificar cache
      if (symbolsCache &&
          Date.now() - symbolsCache.timestamp < CACHE_TTL &&
          symbolsCache.exchange === exchange &&
          symbolsCache.marketType === marketType) {
        console.log(`📦 Symbols from cache (${symbolsCache.data.length} symbols)`)
        return symbolsCache.data
      }

      console.log(`🔍 Fetching symbols from API (exchange=${exchange || 'all'}, type=${marketType})`)

      // Chamar endpoint do backend
      const params = new URLSearchParams()
      if (exchange) params.append('exchange', exchange)
      if (marketType) params.append('market_type', marketType)

      const response = await apiClient.get<SymbolsApiResponse>(`/market/symbols?${params.toString()}`)

      if (!response.success) {
        throw new Error('API returned success=false')
      }

      // Converter para formato DiscoveredSymbol
      const symbols: DiscoveredSymbol[] = response.symbols.map(s => ({
        symbol: s.symbol,
        exchange: s.exchange,
        hasPosition: false,
        isPopular: false,
        category: 'all' as const,
        baseAsset: s.baseAsset,
        marketType: s.marketType
      }))

      // Atualizar cache
      symbolsCache = {
        data: symbols,
        timestamp: Date.now(),
        exchange,
        marketType
      }

      console.log(`✅ Fetched ${symbols.length} symbols from API`)
      return symbols

    } catch (error) {
      console.error('Error fetching symbols from API:', error)

      // Fallback para lista estática
      return POPULAR_SYMBOLS_FALLBACK.map(symbol => ({
        symbol,
        exchange: 'binance',
        hasPosition: false,
        isPopular: true,
        category: 'popular' as const
      }))
    }
  },

  /**
   * Descobre todos os símbolos relevantes para o usuário
   * Prioriza: posições ativas > favoritos > todos os disponíveis
   */
  async discoverSymbols(): Promise<DiscoveredSymbol[]> {
    try {
      // Buscar em paralelo: posições, favoritos e todos os símbolos
      const [positions, favoriteSymbols, allSymbols] = await Promise.all([
        this.getPositionSymbols(),
        this.getFavoriteSymbols(),
        this.fetchAllSymbols(null, 'futures')  // Buscar todos os futures
      ])

      const discoveredSymbols: DiscoveredSymbol[] = []
      const addedSymbols = new Set<string>()

      // 1. Adicionar símbolos das posições ativas (prioridade máxima)
      positions.forEach(position => {
        addedSymbols.add(position.symbol)
        discoveredSymbols.push({
          symbol: position.symbol,
          exchange: position.exchange,
          hasPosition: true,
          positionSide: position.positionSide,
          positionSize: position.positionSize,
          entryPrice: position.entryPrice,
          unrealizedPnl: position.unrealizedPnl,
          category: 'position'
        })
      })

      // 2. Adicionar símbolos favoritos
      favoriteSymbols.forEach(symbol => {
        if (!addedSymbols.has(symbol)) {
          addedSymbols.add(symbol)
          discoveredSymbols.push({
            symbol,
            exchange: 'binance',
            hasPosition: false,
            category: 'favorite'
          })
        }
      })

      // 3. Marcar símbolos populares
      const popularSet = new Set(POPULAR_SYMBOLS_FALLBACK)

      // 4. Adicionar TODOS os símbolos disponíveis
      allSymbols.forEach(s => {
        if (!addedSymbols.has(s.symbol)) {
          addedSymbols.add(s.symbol)
          discoveredSymbols.push({
            ...s,
            hasPosition: false,
            isPopular: popularSet.has(s.symbol),
            category: popularSet.has(s.symbol) ? 'popular' : 'all'
          })
        }
      })

      // 5. Ordenar: posições > favoritos > populares > resto (alfabético)
      return discoveredSymbols.sort((a, b) => {
        const order = { position: 0, favorite: 1, popular: 2, recent: 3, all: 4 }
        const orderDiff = order[a.category] - order[b.category]
        if (orderDiff !== 0) return orderDiff
        return a.symbol.localeCompare(b.symbol)
      })

    } catch (error) {
      console.error('Error discovering symbols:', error)

      // Fallback: retornar símbolos populares
      return POPULAR_SYMBOLS_FALLBACK.map(symbol => ({
        symbol,
        exchange: 'binance',
        hasPosition: false,
        isPopular: true,
        category: 'popular' as const
      }))
    }
  },

  /**
   * Busca símbolos das posições ativas
   */
  async getPositionSymbols(): Promise<Array<{
    symbol: string
    exchange: string
    positionSide: 'long' | 'short'
    positionSize: number
    entryPrice: number
    unrealizedPnl: number
  }>> {
    try {
      const response = await apiClient.get<any[]>('/positions?status=open')

      return response.map((position: any) => ({
        symbol: position.symbol,
        exchange: position.exchange || 'binance',
        positionSide: position.side === 'LONG' ? 'long' : 'short',
        positionSize: Math.abs(position.size),
        entryPrice: position.entryPrice,
        unrealizedPnl: position.unrealizedPnl
      }))
    } catch (error) {
      console.error('Error fetching position symbols:', error)
      return []
    }
  },

  /**
   * Busca símbolos favoritos do usuário (implementar depois)
   */
  async getFavoriteSymbols(): Promise<string[]> {
    try {
      // TODO: Implementar endpoint para favoritos do usuário
      // const response = await apiClient.get('/user/favorite-symbols')
      // return response.symbols || []
      return []
    } catch (error) {
      console.error('Error fetching favorite symbols:', error)
      return []
    }
  },

  /**
   * Busca símbolos com filtro de pesquisa (via API do backend)
   */
  async searchSymbol(query: string): Promise<DiscoveredSymbol[]> {
    try {
      // Se query vazia ou muito curta, retornar descobertos
      if (!query || query.length < 2) {
        const discovered = await this.discoverSymbols()
        return discovered.slice(0, 50)  // Top 50
      }

      // Buscar via API com filtro de search
      const response = await apiClient.get<SymbolsApiResponse>(
        `/market/symbols?search=${encodeURIComponent(query)}&market_type=all`
      )

      if (!response.success || response.symbols.length === 0) {
        // Se API não retornar resultados, filtrar localmente
        const allSymbols = await this.discoverSymbols()
        return allSymbols.filter(s =>
          s.symbol.toLowerCase().includes(query.toLowerCase()) ||
          s.baseAsset?.toLowerCase().includes(query.toLowerCase())
        )
      }

      // Converter resposta da API
      return response.symbols.map(s => ({
        symbol: s.symbol,
        exchange: s.exchange,
        hasPosition: false,
        isPopular: POPULAR_SYMBOLS_FALLBACK.includes(s.symbol),
        category: 'all' as const,
        baseAsset: s.baseAsset,
        marketType: s.marketType
      }))

    } catch (error) {
      console.error('Error searching symbols:', error)

      // Fallback: filtrar símbolos populares localmente
      const filtered = POPULAR_SYMBOLS_FALLBACK.filter(symbol =>
        symbol.toLowerCase().includes(query.toLowerCase())
      )

      return filtered.map(symbol => ({
        symbol,
        exchange: 'binance',
        hasPosition: false,
        isPopular: true,
        category: 'popular' as const
      }))
    }
  },

  /**
   * Limpa o cache de símbolos (útil para forçar refresh)
   */
  clearCache(): void {
    symbolsCache = null
    console.log('🗑️ Symbols cache cleared')
  }
}
