/**
 * Chat Types
 * Types for AI Chat system with alerts and notifications
 */

export type ChatContextType = 'general' | 'strategy' | 'bot' | 'backtest' | 'market';

export type AlertType = 'critical' | 'warning' | 'info' | 'success';
export type AlertCategory = 'trade' | 'news' | 'strategy' | 'system';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  context?: {
    type: ChatContextType;
    id?: string;
    name?: string;
  };
}

export interface ChatAlert {
  id: string;
  type: AlertType;
  category: AlertCategory;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  actionUrl?: string;
  strategyId?: string;
  botId?: string;
  fullContent?: string;  // Full report content for expandable view
  reportDate?: string;   // Date of the report (YYYY-MM-DD)
}

export interface ChatState {
  isOpen: boolean;
  messages: ChatMessage[];
  alerts: ChatAlert[];
  unreadAlerts: number;
  isLoading: boolean;
  conversationId: string | null;
  currentContext: ChatContextType;
}

export interface SendMessageRequest {
  message: string;
  context_type?: ChatContextType;
  context_id?: string;
  conversation_id?: string;
}

export interface SendMessageResponse {
  response: string;
  conversation_id: string;
  context_used?: string[];
}

export interface EvaluateStrategyRequest {
  strategy_id: string;
  include_recommendations?: boolean;
}

export interface AnalyzeBotRequest {
  bot_id: string;
  include_history?: boolean;
  days_to_analyze?: number;
}

export interface AskQuestionRequest {
  question: string;
  include_examples?: boolean;
}
