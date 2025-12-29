/**
 * Chat Context
 * Global state management for AI Chat system
 * OTIMIZADO para evitar re-renders e chamadas excessivas
 */
import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { ChatState, ChatMessage, ChatAlert, ChatContextType } from '@/types/chat'
import { aiChatService } from '@/services/aiChatService'

interface ChatContextValue extends ChatState {
  openChat: () => void
  closeChat: () => void
  toggleChat: () => void
  sendMessage: (content: string) => Promise<void>
  setContext: (type: ChatContextType, id?: string, name?: string) => void
  markAlertRead: (alertId: string) => void
  clearAlerts: () => void
  refreshAlerts: () => Promise<void>
}

const ChatContext = createContext<ChatContextValue | null>(null)

// Generate unique ID for messages
const generateId = (): string => {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
}

// Intervalo de polling em minutos (5 minutos para reduzir carga)
const ALERTS_POLLING_INTERVAL = 5 * 60 * 1000

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<ChatState>({
    isOpen: false,
    messages: [],
    alerts: [],
    unreadAlerts: 0,
    isLoading: false,
    conversationId: null,
    currentContext: 'general'
  })

  // Usar ref para evitar re-criação do callback
  const isFetchingRef = useRef(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch alerts - função estável que não muda
  const fetchAlerts = useCallback(async () => {
    // Evita chamadas simultâneas
    if (isFetchingRef.current) return

    isFetchingRef.current = true
    try {
      const alerts = await aiChatService.getAlerts()
      const unread = alerts.filter(a => !a.read).length
      setState(prev => ({ ...prev, alerts, unreadAlerts: unread }))
    } catch (error) {
      // Silenciar erros de rede para não poluir o console
      // console.error('Failed to fetch alerts:', error)
    } finally {
      isFetchingRef.current = false
    }
  }, []) // Sem dependências - função estável

  // Setup polling apenas uma vez no mount
  useEffect(() => {
    // Fetch inicial
    fetchAlerts()

    // Setup polling com intervalo longo
    intervalRef.current = setInterval(fetchAlerts, ALERTS_POLLING_INTERVAL)

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, []) // Array vazio - executa apenas no mount

  const openChat = useCallback(() => {
    setState(prev => ({ ...prev, isOpen: true }))
    // Refresh alerts quando abre o chat
    fetchAlerts()
  }, [fetchAlerts])

  const closeChat = useCallback(() => {
    setState(prev => ({ ...prev, isOpen: false }))
  }, [])

  const toggleChat = useCallback(() => {
    setState(prev => {
      if (!prev.isOpen) {
        // Se está abrindo, refresh alerts
        fetchAlerts()
      }
      return { ...prev, isOpen: !prev.isOpen }
    })
  }, [fetchAlerts])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    }

    setState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true
    }))

    try {
      const response = await aiChatService.sendMessage(
        content,
        state.currentContext,
        undefined,
        state.conversationId || undefined
      )

      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date()
      }

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
        conversationId: response.conversation_id,
        isLoading: false
      }))
    } catch (error) {
      console.error('Chat error:', error)

      const errorMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: 'Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.',
        timestamp: new Date()
      }

      setState(prev => ({
        ...prev,
        messages: [...prev.messages, errorMessage],
        isLoading: false
      }))
    }
  }, [state.currentContext, state.conversationId])

  const setContext = useCallback((type: ChatContextType) => {
    setState(prev => ({
      ...prev,
      currentContext: type,
    }))
  }, [])

  const markAlertRead = useCallback((alertId: string) => {
    setState(prev => {
      const alert = prev.alerts.find(a => a.id === alertId)
      const wasUnread = alert && !alert.read

      return {
        ...prev,
        alerts: prev.alerts.map(a =>
          a.id === alertId ? { ...a, read: true } : a
        ),
        unreadAlerts: wasUnread ? Math.max(0, prev.unreadAlerts - 1) : prev.unreadAlerts
      }
    })

    // Update on server (fire and forget)
    aiChatService.markAlertRead(alertId).catch(() => {})
  }, [])

  const clearAlerts = useCallback(() => {
    setState(prev => {
      // Mark all as read on server
      prev.alerts.filter(a => !a.read).forEach(alert => {
        aiChatService.markAlertRead(alert.id).catch(() => {})
      })

      return {
        ...prev,
        alerts: prev.alerts.map(a => ({ ...a, read: true })),
        unreadAlerts: 0
      }
    })
  }, [])

  const refreshAlerts = useCallback(async () => {
    await fetchAlerts()
  }, [fetchAlerts])

  return (
    <ChatContext.Provider
      value={{
        ...state,
        openChat,
        closeChat,
        toggleChat,
        sendMessage,
        setContext,
        markAlertRead,
        clearAlerts,
        refreshAlerts
      }}
    >
      {children}
    </ChatContext.Provider>
  )
}

export const useChat = (): ChatContextValue => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider')
  }
  return context
}

export default ChatContext
