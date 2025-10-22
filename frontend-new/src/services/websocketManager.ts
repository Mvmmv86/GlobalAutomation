/**
 * WebSocket Manager - Singleton pattern for managing WebSocket connections
 * Ensures only one connection exists at a time and handles reconnection logic
 */

export interface WSMessage {
  type: 'connected' | 'ping' | 'order_update' | 'position_update' | 'balance_update' | 'subscribed'
  timestamp: string
  data?: any
  message?: string
  user_id?: string
  events?: string[]
}

type MessageHandler = (message: WSMessage) => void
type ConnectionHandler = (isConnected: boolean) => void

class WebSocketManager {
  private static instance: WebSocketManager | null = null
  private ws: WebSocket | null = null
  private messageHandlers: Set<MessageHandler> = new Set()
  private connectionHandlers: Set<ConnectionHandler> = new Set()
  private reconnectTimer: NodeJS.Timeout | null = null
  private pingInterval: NodeJS.Timeout | null = null
  private connectionDebounceTimer: NodeJS.Timeout | null = null
  private isConnecting: boolean = false
  private isIntentionalClose: boolean = false
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 3  // Reduced from 5 to avoid too many attempts
  private reconnectDelay: number = 5000      // Increased from 3s to 5s initial delay
  private currentUrl: string | null = null
  private userId: string | null = null
  private lastConnectionTime: number = 0

  private constructor() {
    console.log('🔌 WebSocketManager initialized')
  }

  public static getInstance(): WebSocketManager {
    if (!WebSocketManager.instance) {
      WebSocketManager.instance = new WebSocketManager()
    }
    return WebSocketManager.instance
  }

  /**
   * Connect to WebSocket server
   */
  public connect(userId: string): void {
    // Clear any pending connection debounce
    if (this.connectionDebounceTimer) {
      clearTimeout(this.connectionDebounceTimer)
    }

    // Debounce rapid connection attempts (wait 500ms)
    this.connectionDebounceTimer = setTimeout(() => {
      this.doConnect(userId)
    }, 500)
  }

  private doConnect(userId: string): void {
    // Check if recently connected (within 2 seconds)
    const now = Date.now()
    if (now - this.lastConnectionTime < 2000) {
      console.log('⚠️ Too soon since last connection attempt, skipping...')
      return
    }

    // Prevent multiple simultaneous connection attempts
    if (this.isConnecting) {
      console.log('⚠️ Connection already in progress, skipping...')
      return
    }

    // If already connected with same userId, skip
    if (this.ws?.readyState === WebSocket.OPEN && this.userId === userId) {
      console.log('✅ Already connected with same userId')
      return
    }

    // If connected with different userId, disconnect first
    if (this.ws?.readyState === WebSocket.OPEN && this.userId !== userId) {
      console.log('🔄 Different userId, disconnecting and reconnecting...')
      this.disconnect()
    }

    this.userId = userId
    this.isIntentionalClose = false
    this.isConnecting = true
    this.lastConnectionTime = now

    // Generate WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = process.env.NODE_ENV === 'production' ? '' : ':8000'
    const clientId = `web_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    this.currentUrl = `${protocol}//${host}${port}/api/v1/ws/notifications?user_id=${userId}&client_id=${clientId}`

    console.log('🔌 Connecting to WebSocket:', this.currentUrl)

    try {
      this.ws = new WebSocket(this.currentUrl)

      this.ws.onopen = this.handleOpen.bind(this)
      this.ws.onmessage = this.handleMessage.bind(this)
      this.ws.onerror = this.handleError.bind(this)
      this.ws.onclose = this.handleClose.bind(this)
    } catch (error) {
      console.error('❌ Failed to create WebSocket:', error)
      this.isConnecting = false
      this.notifyConnectionHandlers(false)
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    console.log('🔌 Disconnecting WebSocket...')
    this.isIntentionalClose = true

    // Clear all timers
    if (this.connectionDebounceTimer) {
      clearTimeout(this.connectionDebounceTimer)
      this.connectionDebounceTimer = null
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }

    // Close WebSocket
    if (this.ws) {
      this.ws.close(1000, 'User disconnect')
      this.ws = null
    }

    this.isConnecting = false
    this.reconnectAttempts = 0
    this.userId = null
    this.notifyConnectionHandlers(false)
  }

  /**
   * Send message through WebSocket
   */
  public sendMessage(message: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('⚠️ Cannot send message, WebSocket not connected')
    }
  }

  /**
   * Add message handler
   */
  public addMessageHandler(handler: MessageHandler): void {
    this.messageHandlers.add(handler)
  }

  /**
   * Remove message handler
   */
  public removeMessageHandler(handler: MessageHandler): void {
    this.messageHandlers.delete(handler)
  }

  /**
   * Add connection status handler
   */
  public addConnectionHandler(handler: ConnectionHandler): void {
    this.connectionHandlers.add(handler)
    // Immediately notify current status
    handler(this.isConnected())
  }

  /**
   * Remove connection status handler
   */
  public removeConnectionHandler(handler: ConnectionHandler): void {
    this.connectionHandlers.delete(handler)
  }

  /**
   * Check if WebSocket is connected
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * Handle WebSocket open event
   */
  private handleOpen(): void {
    console.log('✅ WebSocket connection opened')
    this.isConnecting = false
    this.reconnectAttempts = 0

    // Start ping interval (every 25 seconds)
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
    }
    this.pingInterval = setInterval(() => {
      this.sendPong()
    }, 25000)

    this.notifyConnectionHandlers(true)
  }

  /**
   * Handle WebSocket message
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WSMessage = JSON.parse(event.data)
      console.log('📡 WebSocket message received:', message.type)

      // Handle ping-pong
      if (message.type === 'ping') {
        this.sendPong()
      }

      // Notify all handlers
      this.messageHandlers.forEach(handler => {
        try {
          handler(message)
        } catch (error) {
          console.error('Error in message handler:', error)
        }
      })
    } catch (error) {
      console.error('❌ Error parsing WebSocket message:', error)
    }
  }

  /**
   * Handle WebSocket error
   */
  private handleError(event: Event): void {
    console.error('❌ WebSocket error:', event)
    this.isConnecting = false
  }

  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    console.log('🔌 WebSocket closed:', event.code, event.reason)
    this.isConnecting = false

    // Clear ping interval
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }

    this.notifyConnectionHandlers(false)

    // Only reconnect if not intentional close and within retry limits
    if (!this.isIntentionalClose && this.userId && this.reconnectAttempts < this.maxReconnectAttempts) {
      // More gradual exponential backoff: 5s, 10s, 20s
      const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts), 30000) // Max 30s
      console.log(`🔄 Reconnecting in ${delay/1000}s (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`)

      this.reconnectTimer = setTimeout(() => {
        this.reconnectAttempts++
        if (this.userId) {
          // Use doConnect directly to bypass debounce during reconnection
          this.doConnect(this.userId)
        }
      }, delay)
    } else if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`❌ Max reconnection attempts reached (${this.maxReconnectAttempts})`)
    }
  }

  /**
   * Send pong message
   */
  private sendPong(): void {
    this.sendMessage({
      type: 'pong',
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Notify all connection handlers
   */
  private notifyConnectionHandlers(isConnected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(isConnected)
      } catch (error) {
        console.error('Error in connection handler:', error)
      }
    })
  }
}

// Export singleton instance
export const wsManager = WebSocketManager.getInstance()