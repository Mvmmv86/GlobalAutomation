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
  category: 'position' | 'popular' | 'favorite' | 'recent'
}

// Símbolos populares para trading
const POPULAR_SYMBOLS = [
  'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
  'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT',
  'LINKUSDT', 'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'FILUSDT',
  'TRXUSDT', 'ETCUSDT', 'XLMUSDT', 'VETUSDT', 'ICPUSDT',
  'THETAUSDT', 'FTMUSDT', 'AAVEUSDT', 'AXSUSDT', 'SANDUSDT',
  'MANAUSDT', 'NEARUSDT', 'ALGOUSDT', 'GRTUSDT', 'MKRUSDT',
  'COMPUSDT', 'SUSHIUSDT', '1INCHUSDT', 'ENJUSDT', 'CHZUSDT',
  'BATUSDT', 'ZRXUSDT', 'CRVUSDT', 'SNXUSDT', 'YFIUSDT',
  'ALPHAUSDT', 'OCEANUSDT', 'COTIUSDT', 'ZILUSDT', 'IOTAUSDT',
  'ONTUSDT', 'NEOUSDT', 'QTUMUSDT', 'STORJUSDT', 'AUDIOUSDT'
]

export const symbolDiscoveryService = {
  /**
   * Descobre todos os símbolos relevantes para o usuário
   */
  async discoverSymbols(): Promise<DiscoveredSymbol[]> {
    try {
      const [positions, favoriteSymbols] = await Promise.all([
        this.getPositionSymbols(),
        this.getFavoriteSymbols(),
      ])

      const discoveredSymbols: DiscoveredSymbol[] = []

      // 1. Adicionar símbolos das posições ativas
      positions.forEach(position => {
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
        if (!discoveredSymbols.find(s => s.symbol === symbol)) {
          discoveredSymbols.push({
            symbol,
            exchange: 'binance',
            hasPosition: false,
            category: 'favorite'
          })
        }
      })

      // 3. Adicionar símbolos populares
      POPULAR_SYMBOLS.forEach(symbol => {
        if (!discoveredSymbols.find(s => s.symbol === symbol)) {
          discoveredSymbols.push({
            symbol,
            exchange: 'binance',
            hasPosition: false,
            isPopular: true,
            category: 'popular'
          })
        }
      })

      // 4. Ordenar: posições primeiro, depois favoritos, depois populares
      return discoveredSymbols.sort((a, b) => {
        const order = { position: 0, favorite: 1, popular: 2, recent: 3 }
        return order[a.category] - order[b.category]
      })

    } catch (error) {
      console.error('Error discovering symbols:', error)

      // Fallback: retornar apenas símbolos populares
      return POPULAR_SYMBOLS.map(symbol => ({
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
   * Busca um símbolo específico (para pesquisa)
   */
  async searchSymbol(query: string): Promise<DiscoveredSymbol[]> {
    const allSymbols = await this.discoverSymbols()

    if (!query || query.length < 2) {
      return allSymbols.slice(0, 20) // Top 20
    }

    const filtered = allSymbols.filter(symbol =>
      symbol.symbol.toLowerCase().includes(query.toLowerCase())
    )

    // Se não encontrar nada, sugerir símbolos populares que começam com a busca
    if (filtered.length === 0) {
      const suggestions = POPULAR_SYMBOLS
        .filter(symbol => symbol.toLowerCase().startsWith(query.toLowerCase()))
        .map(symbol => ({
          symbol,
          exchange: 'binance',
          hasPosition: false,
          isPopular: true,
          category: 'popular' as const
        }))

      return suggestions
    }

    return filtered
  }
}