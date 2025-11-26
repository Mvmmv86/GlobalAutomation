/**
 * Binance WebSocket Service - Real-time price updates
 * Conecta com WebSocket público da Binance para preços em tempo real
 */

interface TickerData {
  symbol: string
  price: string
  priceChange: string
  priceChangePercent: string
  volume: string
  timestamp: number
}

interface BinanceWebSocketData {
  stream: string
  data: {
    e: string // Event type
    E: number // Event time
    s: string // Symbol
    c: string // Current price
    P: string // Price change percent
    p: string // Price change
    v: string // Volume
  }
}

class BinanceWebSocketService {
  private ws: WebSocket | null = null
  private subscribers: Map<string, Set<(data: TickerData) => void>> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnecting = false
  private subscribedSymbols: Set<string> = new Set()

  constructor() {
    this.connect()
  }

  /**
   * Conecta ao WebSocket da Binance
   */
  private connect() {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.isConnecting = true
    console.log('🔌 Conectando ao WebSocket FUTURES da Binance...')

    try {
      // WebSocket FUTURES da Binance para todos os tickers
      this.ws = new WebSocket('wss://fstream.binance.com/ws/!ticker@arr')

      this.ws.onopen = () => {
        console.log('✅ WebSocket da Binance conectado!')
        this.reconnectAttempts = 0
        this.isConnecting = false
      }

      this.ws.onmessage = (event) => {
        try {
          const tickers = JSON.parse(event.data)

          // Processa array de tickers
          if (Array.isArray(tickers)) {
            tickers.forEach((ticker) => {
              if (ticker.s && this.subscribedSymbols.has(ticker.s)) {
                const tickerData: TickerData = {
                  symbol: ticker.s,
                  price: ticker.c,
                  priceChange: ticker.p,
                  priceChangePercent: ticker.P,
                  volume: ticker.v,
                  timestamp: Date.now()
                }

                this.notifySubscribers(ticker.s, tickerData)
              }
            })
          }
        } catch (error) {
          console.error('❌ Erro ao processar dados WebSocket:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('🔌 WebSocket desconectado')
        this.isConnecting = false
        this.reconnect()
      }

      this.ws.onerror = (error) => {
        console.error('❌ Erro no WebSocket:', error)
        this.isConnecting = false
      }

    } catch (error) {
      console.error('❌ Erro ao criar WebSocket:', error)
      this.isConnecting = false
      this.reconnect()
    }
  }

  /**
   * Reconecta automaticamente
   */
  private reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('❌ Máximo de tentativas de reconexão atingido')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * this.reconnectAttempts

    console.log(`🔄 Tentando reconectar em ${delay}ms (tentativa ${this.reconnectAttempts})`)

    setTimeout(() => {
      this.connect()
    }, delay)
  }

  /**
   * Notifica todos os subscribers de um símbolo
   */
  private notifySubscribers(symbol: string, data: TickerData) {
    const symbolSubscribers = this.subscribers.get(symbol)
    if (symbolSubscribers) {
      symbolSubscribers.forEach(callback => {
        try {
          callback(data)
        } catch (error) {
          console.error(`❌ Erro ao notificar subscriber para ${symbol}:`, error)
        }
      })
    }
  }

  /**
   * Subscreve para receber atualizações de preço de um símbolo
   */
  subscribe(symbol: string, callback: (data: TickerData) => void): () => void {
    // Adiciona símbolo à lista de símbolos monitorados
    this.subscribedSymbols.add(symbol)

    // Cria set de subscribers para o símbolo se não existir
    if (!this.subscribers.has(symbol)) {
      this.subscribers.set(symbol, new Set())
    }

    // Adiciona callback ao set
    this.subscribers.get(symbol)!.add(callback)

    console.log(`📡 Subscrito para ${symbol} (${this.subscribers.get(symbol)!.size} subscribers)`)

    // Retorna função de unsubscribe
    return () => {
      const symbolSubscribers = this.subscribers.get(symbol)
      if (symbolSubscribers) {
        symbolSubscribers.delete(callback)

        // Remove símbolo se não há mais subscribers
        if (symbolSubscribers.size === 0) {
          this.subscribers.delete(symbol)
          this.subscribedSymbols.delete(symbol)
          console.log(`📡 Unsubscribed from ${symbol}`)
        }
      }
    }
  }

  /**
   * Obtém último preço conhecido de um símbolo
   */
  getLastPrice(symbol: string): string | null {
    // Esta implementação simples poderia ser melhorada com cache
    return null
  }

  /**
   * Desconecta o WebSocket
   */
  disconnect() {
    console.log('🔌 Desconectando WebSocket da Binance...')

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.subscribers.clear()
    this.subscribedSymbols.clear()
    this.isConnecting = false
  }

  /**
   * Verifica se está conectado
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Singleton instance
export const binanceWebSocket = new BinanceWebSocketService()
export type { TickerData }