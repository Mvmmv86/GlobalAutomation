import React, { useRef, useState } from 'react'
import { X, Download, Share2, MessageCircle, Twitter, Copy, Check, TrendingUp, TrendingDown } from 'lucide-react'
import html2canvas from 'html2canvas'

interface SharePnLModalProps {
  isOpen: boolean
  onClose: () => void
  botName: string
  pnlUsd: number
  pnlPercent?: number
  winRate: number
  totalTrades: number
  period: string
}

export const SharePnLModal: React.FC<SharePnLModalProps> = ({
  isOpen,
  onClose,
  botName,
  pnlUsd,
  pnlPercent,
  winRate,
  totalTrades,
  period
}) => {
  const cardRef = useRef<HTMLDivElement>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [copied, setCopied] = useState(false)

  if (!isOpen) return null

  const isProfit = pnlUsd >= 0
  const formattedPnl = `${isProfit ? '+' : ''}$${Math.abs(pnlUsd).toFixed(2)}`
  const formattedPercent = pnlPercent !== undefined ? `${isProfit ? '+' : ''}${pnlPercent.toFixed(2)}%` : null

  // Generate image from card
  const generateImage = async (): Promise<string | null> => {
    if (!cardRef.current) return null

    setIsGenerating(true)
    try {
      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: '#050505',
        scale: 2,
        useCORS: true,
        logging: false
      })
      return canvas.toDataURL('image/png')
    } catch (error) {
      console.error('Error generating image:', error)
      return null
    } finally {
      setIsGenerating(false)
    }
  }

  // Download image
  const handleDownload = async () => {
    const imageData = await generateImage()
    if (imageData) {
      const link = document.createElement('a')
      link.download = `${botName}-pnl-${Date.now()}.png`
      link.href = imageData
      link.click()
    }
  }

  // Copy image to clipboard
  const handleCopyImage = async () => {
    const imageData = await generateImage()
    if (imageData) {
      try {
        const blob = await (await fetch(imageData)).blob()
        await navigator.clipboard.write([
          new ClipboardItem({ 'image/png': blob })
        ])
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (error) {
        console.error('Error copying image:', error)
      }
    }
  }

  // Generate share text
  const getShareText = () => {
    const emoji = isProfit ? '📈' : '📉'
    return `${emoji} Meu resultado com ${botName}!\n\nP&L: ${formattedPnl}${formattedPercent ? ` (${formattedPercent})` : ''}\nWin Rate: ${winRate.toFixed(1)}%\nTrades: ${totalTrades}\nPeriodo: ${period}\n\n#Trading #CopyTrading #Crypto`
  }

  // Share to WhatsApp
  const shareWhatsApp = () => {
    const text = encodeURIComponent(getShareText())
    window.open(`https://wa.me/?text=${text}`, '_blank')
  }

  // Share to Twitter/X
  const shareTwitter = () => {
    const text = encodeURIComponent(getShareText())
    window.open(`https://twitter.com/intent/tweet?text=${text}`, '_blank')
  }

  // Share to Telegram
  const shareTelegram = () => {
    const text = encodeURIComponent(getShareText())
    window.open(`https://t.me/share/url?text=${text}`, '_blank')
  }

  // Share to Instagram (opens Instagram - user needs to manually share)
  const shareInstagram = () => {
    // Instagram doesn't have a direct share URL, so we'll download the image and inform user
    handleDownload()
    alert('Imagem baixada! Abra o Instagram e compartilhe nos Stories ou Feed.')
  }

  // Copy text to clipboard
  const copyText = async () => {
    await navigator.clipboard.writeText(getShareText())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[300] p-4">
      <div className="bg-card border border-border rounded-lg max-w-sm w-full shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-border">
          <div className="flex items-center gap-1.5">
            <Share2 className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Compartilhar Resultado</h2>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded hover:bg-muted"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* P&L Card - This will be captured as image */}
        <div className="p-3">
          <div
            ref={cardRef}
            className="rounded-lg overflow-hidden relative"
            style={{
              background: isProfit
                ? 'linear-gradient(145deg, #020a06 0%, #051a0f 30%, #0a2818 60%, #051a0f 100%)'
                : 'linear-gradient(145deg, #0a0202 0%, #1a0505 30%, #280a0a 60%, #1a0505 100%)',
              padding: '16px',
              border: isProfit ? '1px solid rgba(34, 197, 94, 0.2)' : '1px solid rgba(239, 68, 68, 0.2)',
              boxShadow: isProfit
                ? '0 0 30px rgba(34, 197, 94, 0.15), inset 0 0 60px rgba(34, 197, 94, 0.05)'
                : '0 0 30px rgba(239, 68, 68, 0.15), inset 0 0 60px rgba(239, 68, 68, 0.05)'
            }}
          >
            {/* Neon glow effect overlay */}
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: isProfit
                  ? 'radial-gradient(ellipse at 50% 0%, rgba(34, 197, 94, 0.1) 0%, transparent 60%)'
                  : 'radial-gradient(ellipse at 50% 0%, rgba(239, 68, 68, 0.1) 0%, transparent 60%)'
              }}
            />

            {/* Grid pattern overlay for tech feel */}
            <div
              className="absolute inset-0 pointer-events-none opacity-[0.03]"
              style={{
                backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
                backgroundSize: '20px 20px'
              }}
            />

            {/* Platform Branding */}
            <div className="flex items-center justify-between mb-3 relative">
              <div className="flex items-center gap-1.5">
                <div
                  className="w-6 h-6 rounded flex items-center justify-center"
                  style={{
                    background: isProfit
                      ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.3), rgba(34, 197, 94, 0.1))'
                      : 'linear-gradient(135deg, rgba(239, 68, 68, 0.3), rgba(239, 68, 68, 0.1))',
                    border: isProfit ? '1px solid rgba(34, 197, 94, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)'
                  }}
                >
                  <TrendingUp className={`w-3.5 h-3.5 ${isProfit ? 'text-green-400' : 'text-red-400'}`} />
                </div>
                <span className="text-white/70 text-xs font-medium">GlobalAutomation</span>
              </div>
              <span className="text-white/50 text-[10px]">{period}</span>
            </div>

            {/* Bot Name */}
            <h3 className="text-white text-sm font-bold mb-3 relative">{botName}</h3>

            {/* Main P&L Display */}
            <div className="text-center py-4 relative">
              <div className="flex items-center justify-center gap-2 mb-1">
                {isProfit ? (
                  <TrendingUp
                    className="w-7 h-7"
                    style={{
                      color: '#22c55e',
                      filter: 'drop-shadow(0 0 8px rgba(34, 197, 94, 0.5))'
                    }}
                  />
                ) : (
                  <TrendingDown
                    className="w-7 h-7"
                    style={{
                      color: '#ef4444',
                      filter: 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.5))'
                    }}
                  />
                )}
                <span
                  className="text-3xl font-bold"
                  style={{
                    color: isProfit ? '#22c55e' : '#ef4444',
                    textShadow: isProfit
                      ? '0 0 20px rgba(34, 197, 94, 0.5), 0 0 40px rgba(34, 197, 94, 0.3)'
                      : '0 0 20px rgba(239, 68, 68, 0.5), 0 0 40px rgba(239, 68, 68, 0.3)'
                  }}
                >
                  {formattedPnl}
                </span>
              </div>
              {formattedPercent && (
                <p
                  className="text-lg font-semibold"
                  style={{
                    color: isProfit ? 'rgba(34, 197, 94, 0.8)' : 'rgba(239, 68, 68, 0.8)',
                    textShadow: isProfit
                      ? '0 0 10px rgba(34, 197, 94, 0.3)'
                      : '0 0 10px rgba(239, 68, 68, 0.3)'
                  }}
                >
                  {formattedPercent}
                </p>
              )}
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-2 gap-3 mt-3 pt-3 border-t border-white/10 relative">
              <div className="text-center">
                <p className="text-white/50 text-[10px] uppercase tracking-wider mb-0.5">Win Rate</p>
                <p className="text-white text-base font-bold">{winRate.toFixed(1)}%</p>
              </div>
              <div className="text-center">
                <p className="text-white/50 text-[10px] uppercase tracking-wider mb-0.5">Trades</p>
                <p className="text-white text-base font-bold">{totalTrades}</p>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-3 pt-2 border-t border-white/10 text-center relative">
              <p className="text-white/30 text-[10px]">
                Gerado em {new Date().toLocaleDateString('pt-BR')}
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="px-3 pb-3 space-y-2">
          {/* Download & Copy Row */}
          <div className="flex gap-1.5">
            <button
              onClick={handleDownload}
              disabled={isGenerating}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors text-xs font-medium disabled:opacity-50"
            >
              <Download className="w-3.5 h-3.5" />
              {isGenerating ? 'Gerando...' : 'Baixar Imagem'}
            </button>
            <button
              onClick={handleCopyImage}
              disabled={isGenerating}
              className="flex items-center justify-center gap-1.5 py-2 px-3 bg-secondary text-foreground rounded hover:bg-secondary/80 transition-colors text-xs font-medium disabled:opacity-50"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          {/* Social Share Row */}
          <div className="grid grid-cols-4 gap-1.5">
            <button
              onClick={shareWhatsApp}
              className="flex flex-col items-center justify-center gap-1 py-2 px-2 bg-[#25D366]/10 text-[#25D366] border border-[#25D366]/30 rounded hover:bg-[#25D366]/20 transition-colors"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              <span className="text-[10px] font-medium">WhatsApp</span>
            </button>
            <button
              onClick={shareTwitter}
              className="flex flex-col items-center justify-center gap-1 py-2 px-2 bg-[#1DA1F2]/10 text-[#1DA1F2] border border-[#1DA1F2]/30 rounded hover:bg-[#1DA1F2]/20 transition-colors"
            >
              <Twitter className="w-3.5 h-3.5" />
              <span className="text-[10px] font-medium">Twitter</span>
            </button>
            <button
              onClick={shareTelegram}
              className="flex flex-col items-center justify-center gap-1 py-2 px-2 bg-[#0088cc]/10 text-[#0088cc] border border-[#0088cc]/30 rounded hover:bg-[#0088cc]/20 transition-colors"
            >
              <MessageCircle className="w-3.5 h-3.5" />
              <span className="text-[10px] font-medium">Telegram</span>
            </button>
            <button
              onClick={shareInstagram}
              className="flex flex-col items-center justify-center gap-1 py-2 px-2 bg-[#E4405F]/10 text-[#E4405F] border border-[#E4405F]/30 rounded hover:bg-[#E4405F]/20 transition-colors"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
              </svg>
              <span className="text-[10px] font-medium">Instagram</span>
            </button>
          </div>

          {/* Copy Text */}
          <button
            onClick={copyText}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-green-500" />
                Copiado!
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                Copiar texto para compartilhar
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
