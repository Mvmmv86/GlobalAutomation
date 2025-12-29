/**
 * AI Chat Modal
 * Full chat interface with messages, alerts, and context tabs
 * Identity: Cyan (#00F0FF) and Purple (#8B5CF6) theme
 */
import React, { useRef, useEffect, useState } from 'react'
import { X, Send, Sparkles, AlertTriangle, TrendingUp, Newspaper, Bot, ChevronLeft, FileText } from 'lucide-react'
import { useChat } from '@/contexts/ChatContext'
import { ChatContextType, ChatAlert } from '@/types/chat'

// Neural Node Logo for header (same style as AIChatBubble)
const HeaderNeuralLogo: React.FC = () => {
  const size = 40
  const particleSize = 5
  const orbitRadius = 16

  return (
    <div className="relative" style={{ width: size, height: size }}>
      {/* Outer Ring */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          border: '2px solid rgba(0, 240, 255, 0.4)',
          animation: 'rotate-cw 20s linear infinite',
        }}
      />

      {/* Middle Ring */}
      <div
        className="absolute rounded-full"
        style={{
          inset: '15%',
          border: '1px solid rgba(139, 92, 246, 0.5)',
          animation: 'rotate-ccw 15s linear infinite',
        }}
      />

      {/* Core */}
      <div
        className="absolute rounded-full"
        style={{
          inset: '30%',
          background: 'linear-gradient(to bottom right, #00F0FF, #8B5CF6)',
          boxShadow: '0 0 15px rgba(0, 240, 255, 0.5)',
          animation: 'pulse-scale 2s ease-in-out infinite',
        }}
      />

      {/* Orbiting Particles */}
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="absolute"
          style={{
            width: particleSize,
            height: particleSize,
            top: '50%',
            left: '50%',
            marginTop: -particleSize / 2,
            marginLeft: -particleSize / 2,
            animation: `orbit ${3 + i * 0.5}s linear infinite ${i * 0.4}s`,
          }}
        >
          <div
            className="absolute rounded-full"
            style={{
              width: particleSize,
              height: particleSize,
              backgroundColor: '#00F0FF',
              boxShadow: '0 0 8px rgba(0, 240, 255, 0.8)',
              transform: `translateX(${orbitRadius}px)`,
            }}
          />
        </div>
      ))}

      <style>{`
        @keyframes rotate-cw {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes rotate-ccw {
          from { transform: rotate(0deg); }
          to { transform: rotate(-360deg); }
        }
        @keyframes pulse-scale {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
        @keyframes orbit {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

// Report Viewer Component - Full screen view of the report
const ReportViewer: React.FC<{
  alert: ChatAlert
  onClose: () => void
}> = ({ alert, onClose }) => {
  return (
    <div className="absolute inset-0 bg-gray-900 z-10 flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-gray-800 bg-gray-900/95">
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 flex-1">
          <FileText className="w-5 h-5 text-cyan-400" />
          <div>
            <h3 className="text-white font-medium">{alert.title}</h3>
            <p className="text-xs text-gray-400">
              {alert.reportDate || new Date(alert.timestamp).toLocaleDateString('pt-BR')}
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
        <div className="prose prose-invert prose-sm max-w-none">
          <div className="whitespace-pre-wrap text-gray-200 text-sm leading-relaxed">
            {alert.fullContent || alert.message}
          </div>
        </div>
      </div>
    </div>
  )
}

// Context options for the tabs
const contextOptions: Array<{ value: ChatContextType; label: string; icon: React.FC<{ className?: string }> }> = [
  { value: 'general', label: 'Geral', icon: Sparkles },
  { value: 'strategy', label: 'Estrategias', icon: TrendingUp },
  { value: 'bot', label: 'Bots', icon: Bot },
  { value: 'market', label: 'Mercado', icon: Newspaper },
]

// Quick suggestions for empty chat
const quickSuggestions = [
  "Analise minha melhor estrategia",
  "Como esta o mercado hoje?",
  "Qual bot esta performando melhor?",
  "Sugira melhorias para minhas estrategias",
  "Mostre meu relatorio diario",
  "Quais sao os riscos atuais?"
]

export const AIChatModal: React.FC = () => {
  const {
    isOpen,
    closeChat,
    messages,
    alerts,
    isLoading,
    sendMessage,
    currentContext,
    setContext,
    markAlertRead,
    unreadAlerts,
    clearAlerts
  } = useChat()

  const [input, setInput] = useState('')
  const [showAlerts, setShowAlerts] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<ChatAlert | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to last message
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return
    const message = input
    setInput('')
    await sendMessage(message)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion)
    inputRef.current?.focus()
  }

  // Handle alert click - open report if it has full content
  const handleAlertClick = (alert: ChatAlert) => {
    markAlertRead(alert.id)

    // If the alert has full content (like a report), open the viewer
    if (alert.fullContent || alert.category === 'system') {
      setSelectedAlert(alert)
    }
  }

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={closeChat}
      />

      {/* Modal */}
      <div
        className="
          relative w-full max-w-lg h-[85vh] max-h-[750px]
          bg-gray-900 rounded-2xl shadow-2xl
          flex flex-col overflow-hidden
          border border-cyan-500/20
          animate-in slide-in-from-bottom-5 fade-in duration-300
        "
        style={{
          boxShadow: '0 0 60px rgba(0, 240, 255, 0.15), 0 25px 50px -12px rgba(0, 0, 0, 0.5)'
        }}
      >
        {/* Report Viewer Overlay */}
        {selectedAlert && (
          <ReportViewer
            alert={selectedAlert}
            onClose={() => setSelectedAlert(null)}
          />
        )}

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800 bg-gray-900/95 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <HeaderNeuralLogo />
            <div>
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <span className="bg-gradient-to-r from-cyan-400 to-violet-500 bg-clip-text text-transparent">
                  AutoNode
                </span>
                <span className="text-white">AI</span>
                <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
              </h2>
              <p className="text-xs text-gray-400">
                Powered by Claude • Conhecimento Institucional
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Alerts Button */}
            <button
              onClick={() => setShowAlerts(!showAlerts)}
              className={`
                relative p-2 rounded-lg transition-all duration-200
                ${showAlerts
                  ? 'bg-cyan-500/20 text-cyan-400'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }
              `}
              title="Alertas"
            >
              <AlertTriangle className="w-5 h-5" />
              {unreadAlerts > 0 && (
                <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-[10px] flex items-center justify-center text-white font-bold">
                  {unreadAlerts > 9 ? '9+' : unreadAlerts}
                </span>
              )}
            </button>
            {/* Close Button */}
            <button
              onClick={closeChat}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
              title="Fechar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Context Tabs */}
        <div className="flex gap-1 p-2 border-b border-gray-800 bg-gray-900/50 overflow-x-auto scrollbar-hide">
          {contextOptions.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => setContext(value)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap
                transition-all duration-200
                ${currentContext === value
                  ? 'bg-gradient-to-r from-cyan-500/20 to-violet-500/20 text-cyan-400 shadow-sm shadow-cyan-500/20 border border-cyan-500/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800 border border-transparent'
                }
              `}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Alerts Panel (collapsible) */}
        {showAlerts && (
          <div className="border-b border-gray-800 bg-gray-800/30 max-h-52 overflow-y-auto">
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700/50">
              <span className="text-sm font-medium text-gray-300">
                Alertas ({alerts.length})
              </span>
              {alerts.some(a => !a.read) && (
                <button
                  onClick={clearAlerts}
                  className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                >
                  Marcar todos como lidos
                </button>
              )}
            </div>
            {alerts.length === 0 ? (
              <p className="p-4 text-center text-gray-500 text-sm">
                Nenhum alerta no momento
              </p>
            ) : (
              <div className="divide-y divide-gray-700/50">
                {alerts.map(alert => (
                  <div
                    key={alert.id}
                    onClick={() => handleAlertClick(alert)}
                    className={`
                      p-3 cursor-pointer transition-colors group
                      ${!alert.read ? 'bg-gray-800/50' : 'hover:bg-gray-800/30'}
                    `}
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className={`
                          w-2 h-2 rounded-full mt-1.5 flex-shrink-0
                          ${alert.type === 'critical' ? 'bg-red-500' : ''}
                          ${alert.type === 'warning' ? 'bg-yellow-500' : ''}
                          ${alert.type === 'info' ? 'bg-cyan-500' : ''}
                          ${alert.type === 'success' ? 'bg-violet-500' : ''}
                        `}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className={`text-sm font-medium ${!alert.read ? 'text-white' : 'text-gray-300'}`}>
                            {alert.title}
                          </p>
                          {(alert.fullContent || alert.category === 'system') && (
                            <span className="text-xs text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity">
                              Ver completo
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-400 line-clamp-2">{alert.message}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(alert.timestamp).toLocaleTimeString('pt-BR', {
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent">
          {/* Empty state with suggestions */}
          {messages.length === 0 && (
            <div className="text-center py-8">
              <div
                className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.15) 0%, rgba(139, 92, 246, 0.15) 100%)',
                  border: '1px solid rgba(0, 240, 255, 0.3)',
                }}
              >
                <Sparkles className="w-8 h-8 text-cyan-400" />
              </div>
              <h3 className="text-lg font-medium text-white mb-2">
                Como posso ajudar?
              </h3>
              <p className="text-sm text-gray-400 mb-6 max-w-sm mx-auto">
                Tenho acesso a todas as suas estrategias, bots, trades e dados de mercado.
                Pergunte qualquer coisa!
              </p>
              <div className="flex flex-wrap justify-center gap-2 max-w-md mx-auto">
                {quickSuggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className="
                      px-3 py-1.5 bg-gray-800 hover:bg-gray-700
                      rounded-lg text-sm text-gray-300 hover:text-white
                      transition-all duration-200
                      border border-gray-700 hover:border-cyan-500/30
                    "
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Message bubbles */}
          {messages.map(msg => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`
                  max-w-[85%] rounded-2xl px-4 py-3
                  ${msg.role === 'user'
                    ? 'bg-gradient-to-r from-cyan-600 to-violet-600 text-white rounded-br-md'
                    : 'bg-gray-800 text-gray-100 rounded-bl-md border border-gray-700/50'
                  }
                `}
              >
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </p>
                <p
                  className={`
                    text-xs mt-1.5
                    ${msg.role === 'user' ? 'text-cyan-200' : 'text-gray-500'}
                  `}
                >
                  {new Date(msg.timestamp).toLocaleTimeString('pt-BR', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-2xl rounded-bl-md px-4 py-3 border border-gray-700/50">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-800 bg-gray-900/95 backdrop-blur-sm">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyPress}
                placeholder="Digite sua mensagem..."
                rows={1}
                className="
                  w-full resize-none rounded-xl px-4 py-3 pr-12
                  bg-gray-800 border border-gray-700
                  text-white placeholder-gray-500
                  focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50
                  transition-all duration-200
                  max-h-32 scrollbar-thin scrollbar-thumb-gray-600
                "
                style={{ minHeight: '48px' }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className={`
                h-12 w-12 rounded-xl flex items-center justify-center
                transition-all duration-200
                ${input.trim() && !isLoading
                  ? 'bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white shadow-lg shadow-cyan-500/25'
                  : 'bg-gray-800 text-gray-500 cursor-not-allowed'
                }
              `}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Pressione Enter para enviar • Shift+Enter para nova linha
          </p>
        </div>
      </div>
    </div>
  )
}

export default AIChatModal
