import React, { useRef, useEffect, useState, useCallback } from 'react'
import { ISeriesApi, IChartApi } from 'lightweight-charts'

interface DraggableLine {
  id: string
  type: 'STOP_LOSS' | 'TAKE_PROFIT'
  price: number
  orderId?: string
  positionSide: 'LONG' | 'SHORT'
  quantity: number
}

interface ChartDragOverlayProps {
  chart: IChartApi | null
  series: ISeriesApi<'Candlestick'> | null
  stopLoss?: number
  takeProfit?: number
  positionSide?: 'LONG' | 'SHORT'
  quantity?: number
  onDragEnd: (type: 'STOP_LOSS' | 'TAKE_PROFIT', newPrice: number, orderId?: string) => void
  exchangeAccountId?: string
  symbol?: string
}

export const ChartDragOverlay: React.FC<ChartDragOverlayProps> = ({
  chart,
  series,
  stopLoss,
  takeProfit,
  positionSide = 'LONG',
  quantity = 0,
  onDragEnd,
  exchangeAccountId,
  symbol
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [draggedLine, setDraggedLine] = useState<DraggableLine | null>(null)
  const [mouseY, setMouseY] = useState(0)
  const [lines, setLines] = useState<DraggableLine[]>([])

  // Atualizar linhas quando SL/TP mudam
  useEffect(() => {
    const newLines: DraggableLine[] = []

    if (stopLoss && stopLoss > 0) {
      newLines.push({
        id: 'sl',
        type: 'STOP_LOSS',
        price: stopLoss,
        positionSide,
        quantity
      })
    }

    if (takeProfit && takeProfit > 0) {
      newLines.push({
        id: 'tp',
        type: 'TAKE_PROFIT',
        price: takeProfit,
        positionSide,
        quantity
      })
    }

    setLines(newLines)
  }, [stopLoss, takeProfit, positionSide, quantity])

  // Converter preço para coordenada Y
  const priceToY = useCallback((price: number): number | null => {
    if (!series || !chart) return null

    try {
      const coordinate = series.priceToCoordinate(price)
      return coordinate !== null ? coordinate : null
    } catch {
      return null
    }
  }, [series, chart])

  // Converter coordenada Y para preço
  const yToPrice = useCallback((y: number): number | null => {
    if (!series || !chart) return null

    try {
      const price = series.coordinateToPrice(y)
      return price !== null ? price : null
    } catch {
      return null
    }
  }, [series, chart])

  // Detectar se o mouse está sobre uma linha (com tolerância)
  const getLineAtPosition = useCallback((y: number): DraggableLine | null => {
    const TOLERANCE = 5 // pixels

    for (const line of lines) {
      const lineY = priceToY(line.price)
      if (lineY !== null && Math.abs(y - lineY) <= TOLERANCE) {
        return line
      }
    }

    return null
  }, [lines, priceToY])

  // Renderizar o canvas
  const render = useCallback(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx || !chart) return

    // Limpar canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // Renderizar linhas draggable
    lines.forEach(line => {
      const y = priceToY(line.price)
      if (y === null) return

      // Estilo da linha
      ctx.strokeStyle = line.type === 'STOP_LOSS' ? '#ef4444' : '#10b981'
      ctx.lineWidth = 2
      ctx.setLineDash([])

      // Se está sendo arrastada, usar linha pontilhada
      if (draggedLine?.id === line.id) {
        ctx.setLineDash([5, 5])
        ctx.globalAlpha = 0.7
      } else {
        ctx.globalAlpha = 1
      }

      // Desenhar linha horizontal
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(canvas.width, y)
      ctx.stroke()

      // Adicionar handle de drag (círculo no lado direito)
      const handleX = canvas.width - 30
      const handleRadius = 8

      // Área de hit maior para facilitar o clique
      const hitRadius = 15

      // Desenhar área de hit (invisível)
      ctx.fillStyle = 'transparent'
      ctx.beginPath()
      ctx.arc(handleX, y, hitRadius, 0, 2 * Math.PI)
      ctx.fill()

      // Desenhar handle visual
      ctx.fillStyle = line.type === 'STOP_LOSS' ? '#ef4444' : '#10b981'
      ctx.globalAlpha = draggedLine?.id === line.id ? 0.9 : 0.7
      ctx.beginPath()
      ctx.arc(handleX, y, handleRadius, 0, 2 * Math.PI)
      ctx.fill()

      // Ícone de drag (≡)
      ctx.strokeStyle = 'white'
      ctx.lineWidth = 1.5
      ctx.setLineDash([])
      ctx.beginPath()
      ctx.moveTo(handleX - 4, y - 3)
      ctx.lineTo(handleX + 4, y - 3)
      ctx.moveTo(handleX - 4, y)
      ctx.lineTo(handleX + 4, y)
      ctx.moveTo(handleX - 4, y + 3)
      ctx.lineTo(handleX + 4, y + 3)
      ctx.stroke()

      // Label com o preço
      ctx.fillStyle = line.type === 'STOP_LOSS' ? '#ef4444' : '#10b981'
      ctx.globalAlpha = 1
      ctx.font = 'bold 12px Inter'
      const label = `${line.type === 'STOP_LOSS' ? 'SL' : 'TP'}: $${line.price.toFixed(2)}`
      const labelWidth = ctx.measureText(label).width

      // Background do label
      ctx.fillStyle = line.type === 'STOP_LOSS' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)'
      ctx.fillRect(10, y - 10, labelWidth + 10, 20)

      // Texto do label
      ctx.fillStyle = line.type === 'STOP_LOSS' ? '#ef4444' : '#10b981'
      ctx.fillText(label, 15, y + 4)
    })

    // Se está arrastando, mostrar preview da nova posição
    if (isDragging && draggedLine) {
      const newPrice = yToPrice(mouseY)
      if (newPrice !== null && newPrice > 0) {
        ctx.strokeStyle = '#60a5fa'
        ctx.lineWidth = 2
        ctx.setLineDash([10, 5])
        ctx.globalAlpha = 0.5

        ctx.beginPath()
        ctx.moveTo(0, mouseY)
        ctx.lineTo(canvas.width, mouseY)
        ctx.stroke()

        // Mostrar preço preview
        ctx.fillStyle = '#60a5fa'
        ctx.globalAlpha = 1
        ctx.font = 'bold 14px Inter'
        const previewLabel = `Novo: $${newPrice.toFixed(2)}`
        ctx.fillText(previewLabel, canvas.width / 2 - 50, mouseY - 10)
      }
    }
  }, [lines, priceToY, yToPrice, isDragging, draggedLine, mouseY])

  // Atualizar canvas quando necessário
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !chart) return

    // Ajustar tamanho do canvas
    const container = canvas.parentElement
    if (container) {
      canvas.width = container.clientWidth
      canvas.height = container.clientHeight
    }

    render()
  }, [render, chart])

  // Handlers de mouse
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const y = e.clientY - rect.top

    const line = getLineAtPosition(y)
    if (line) {
      setIsDragging(true)
      setDraggedLine(line)
      setMouseY(y)

      // Mudar cursor
      canvas.style.cursor = 'grabbing'

      // Prevenir seleção de texto
      e.preventDefault()
    }
  }, [getLineAtPosition])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const y = e.clientY - rect.top

    // Atualizar cursor
    if (!isDragging) {
      const line = getLineAtPosition(y)
      canvas.style.cursor = line ? 'grab' : 'default'
    }

    // Se está arrastando, atualizar posição
    if (isDragging) {
      setMouseY(y)
      render() // Re-renderizar para mostrar preview
    }
  }, [isDragging, getLineAtPosition, render])

  const handleMouseUp = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas || !isDragging || !draggedLine) return

    const rect = canvas.getBoundingClientRect()
    const y = e.clientY - rect.top
    const newPrice = yToPrice(y)

    if (newPrice !== null && newPrice > 0) {
      // Validar que o novo preço faz sentido
      const minChange = draggedLine.price * 0.001 // 0.1% mínimo de mudança
      if (Math.abs(newPrice - draggedLine.price) > minChange) {
        console.log('🎯 Drag finalizado:', {
          type: draggedLine.type,
          oldPrice: draggedLine.price,
          newPrice,
          orderId: draggedLine.orderId
        })

        // Chamar callback para atualizar na exchange
        onDragEnd(draggedLine.type, newPrice, draggedLine.orderId)
      }
    }

    // Reset estado de drag
    setIsDragging(false)
    setDraggedLine(null)
    canvas.style.cursor = 'default'
  }, [isDragging, draggedLine, yToPrice, onDragEnd])

  const handleMouseLeave = useCallback(() => {
    if (isDragging) {
      // Cancelar drag se sair do canvas
      setIsDragging(false)
      setDraggedLine(null)

      const canvas = canvasRef.current
      if (canvas) {
        canvas.style.cursor = 'default'
      }
    }
  }, [isDragging])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'all',
        zIndex: 10, // Acima do gráfico mas abaixo de modals
        cursor: 'default'
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
    />
  )
}