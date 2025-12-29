/**
 * AI Chat Service
 * Service for AI Trading Assistant communication
 */
import { apiClient } from '@/lib/api'
import {
  ChatAlert,
  ChatContextType,
  SendMessageResponse,
  EvaluateStrategyRequest,
  AnalyzeBotRequest,
  AskQuestionRequest
} from '@/types/chat'

class AIChatService {
  /**
   * Send a message to the AI assistant
   */
  async sendMessage(
    message: string,
    contextType: ChatContextType = 'general',
    contextId?: string,
    conversationId?: string
  ): Promise<SendMessageResponse> {
    const response = await apiClient.instance.post('/ai/chat', {
      message,
      context_type: contextType,
      context_id: contextId,
      conversation_id: conversationId
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }

  /**
   * Evaluate a strategy using AI
   */
  async evaluateStrategy(strategyId: string, includeRecommendations: boolean = true): Promise<any> {
    const response = await apiClient.instance.post('/ai/evaluate-strategy', {
      strategy_id: strategyId,
      include_recommendations: includeRecommendations
    } as EvaluateStrategyRequest)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }

  /**
   * Analyze a bot's performance using AI
   */
  async analyzeBot(botId: string, days: number = 30): Promise<any> {
    const response = await apiClient.instance.post('/ai/analyze-bot', {
      bot_id: botId,
      include_history: true,
      days_to_analyze: days
    } as AnalyzeBotRequest)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }

  /**
   * Get daily report from AI
   */
  async getDailyReport(date?: string): Promise<any> {
    const params = date ? { date } : {}
    const response = await apiClient.instance.get('/ai/daily-report', { params })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }

  /**
   * Get pending alerts for the chat
   */
  async getAlerts(): Promise<ChatAlert[]> {
    try {
      const response = await apiClient.instance.get('/ai/alerts')

      if (response.data?.success && response.data?.data) {
        return response.data.data.map((alert: any) => ({
          ...alert,
          timestamp: new Date(alert.timestamp)
        }))
      }

      return []
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
      return []
    }
  }

  /**
   * Ask a general question to the AI
   */
  async askQuestion(question: string): Promise<any> {
    const response = await apiClient.instance.post('/ai/ask', {
      question,
      include_examples: true
    } as AskQuestionRequest)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }

  /**
   * Mark an alert as read
   */
  async markAlertRead(alertId: string): Promise<void> {
    try {
      await apiClient.instance.patch(`/ai/alerts/${alertId}/read`)
    } catch (error) {
      console.error('Failed to mark alert as read:', error)
    }
  }

  /**
   * Get market analysis/news digest
   */
  async getNewsDigest(date?: string): Promise<any> {
    const params = date ? { date } : {}
    const response = await apiClient.instance.get('/ai/news/digest', { params })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return response.data
  }
}

export const aiChatService = new AIChatService()
export default aiChatService
