/**
 * usePositionsWebSocket Hook
 *
 * Provides real-time WebSocket connection for positions and orders updates.
 * Uses WebSocketManager singleton to ensure only one connection exists.
 *
 * Features:
 * - Singleton WebSocket connection
 * - Auto-reconnect with exponential backoff
 * - React Query cache invalidation on updates
 * - Type-safe message handling
 *
 * Security: Requires user_id for scoped notifications
 */

import { useEffect, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { wsManager, WSMessage } from '@/services/websocketManager'

// WebSocket message data types
interface OrderUpdateData {
  action: 'order_created' | 'order_filled' | 'order_cancelled' | 'order_failed'
  order_id: string
  exchange_order_id: string
  symbol: string
  side: 'buy' | 'sell'
  type: string
  quantity: number
  status: string
  has_stop_loss?: boolean
  has_take_profit?: boolean
}

interface PositionUpdateData {
  action: 'position_opened' | 'position_closed' | 'position_modified'
  position_id: string
  symbol: string
  side: 'LONG' | 'SHORT'
  closed_percentage?: number
  closed_quantity?: number
  order_id?: string
}

interface BalanceUpdateData {
  spot_balance_usdt?: number
  futures_balance_usdt?: number
  futures_available_balance?: number
}

interface UseWebSocketOptions {
  userId: string | null
  enabled?: boolean
  onOrderUpdate?: (data: OrderUpdateData) => void
  onPositionUpdate?: (data: PositionUpdateData) => void
  onBalanceUpdate?: (data: BalanceUpdateData) => void
}

export const usePositionsWebSocket = (options: UseWebSocketOptions) => {
  const {
    userId,
    enabled = true,
    onOrderUpdate,
    onPositionUpdate,
    onBalanceUpdate
  } = options

  const queryClient = useQueryClient()

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((message: WSMessage) => {
    setLastMessage(message)
    console.log('📡 WebSocket message:', message.type, message)

    switch (message.type) {
      case 'connected':
        console.log('✅ WebSocket connected:', message.message)
        setConnectionError(null)
        break

      case 'order_update':
        console.log('📦 Order update:', message.data)

        // Invalidate cache for orders and positions (order might open/close position)
        queryClient.invalidateQueries({ queryKey: ['orders'] })
        queryClient.invalidateQueries({ queryKey: ['positions'] })
        queryClient.invalidateQueries({ queryKey: ['balances'] })

        // Custom callback
        if (onOrderUpdate && message.data) {
          onOrderUpdate(message.data as OrderUpdateData)
        }
        break

      case 'position_update':
        console.log('📊 Position update:', message.data)

        // Invalidate cache for positions and balances
        queryClient.invalidateQueries({ queryKey: ['positions'] })
        queryClient.invalidateQueries({ queryKey: ['balances'] })

        // Custom callback
        if (onPositionUpdate && message.data) {
          onPositionUpdate(message.data as PositionUpdateData)
        }
        break

      case 'balance_update':
        console.log('💰 Balance update:', message.data)

        // Invalidate cache for balances
        queryClient.invalidateQueries({ queryKey: ['balances'] })

        // Custom callback
        if (onBalanceUpdate && message.data) {
          onBalanceUpdate(message.data as BalanceUpdateData)
        }
        break

      case 'subscribed':
        console.log('✅ Subscribed to events:', (message as any).events)
        break

      default:
        console.log('📨 Other message type:', message.type)
    }
  }, [queryClient, onOrderUpdate, onPositionUpdate, onBalanceUpdate])

  // Handle connection status changes
  const handleConnectionChange = useCallback((connected: boolean) => {
    setIsConnected(connected)
    if (!connected) {
      setConnectionError('WebSocket disconnected')
    } else {
      setConnectionError(null)
    }
  }, [])

  // Connect/disconnect based on userId and enabled
  useEffect(() => {
    if (!enabled || !userId) {
      console.log('⏸️ WebSocket disabled or no userId')
      wsManager.disconnect()
      return
    }

    // 🚀 PERFORMANCE: Logs commented out to reduce overhead
    // console.log('🔌 Setting up WebSocket connection for userId:', userId)

    // Add handlers
    wsManager.addMessageHandler(handleMessage)
    wsManager.addConnectionHandler(handleConnectionChange)

    // Connect
    wsManager.connect(userId)

    // Cleanup
    return () => {
      // console.log('🧹 Cleaning up WebSocket handlers')
      wsManager.removeMessageHandler(handleMessage)
      wsManager.removeConnectionHandler(handleConnectionChange)
      // Only disconnect if this component is unmounting due to userId or enabled change
      if (!enabled || !userId) {
        wsManager.disconnect()
      }
    }
  }, [enabled, userId, handleMessage, handleConnectionChange])

  // Public methods
  const sendMessage = useCallback((message: any) => {
    wsManager.sendMessage(message)
  }, [])

  const subscribe = useCallback((events: string[]) => {
    wsManager.sendMessage({
      type: 'subscribe',
      events
    })
  }, [])

  const connect = useCallback(() => {
    if (userId) {
      wsManager.connect(userId)
    }
  }, [userId])

  const disconnect = useCallback(() => {
    wsManager.disconnect()
  }, [])

  return {
    isConnected,
    lastMessage,
    connectionError,
    connect,
    disconnect,
    subscribe,
    sendMessage
  }
}