/**
 * DirtyRegionsTestPage - Página de teste SIMPLIFICADA para Dirty Regions
 * Demonstra as otimizações de renderização parcial
 */

import React, { useEffect, useRef, useState } from 'react'

const DirtyRegionsTestPage: React.FC = () => {
  console.log('🧪 DirtyRegionsTestPage RENDERIZADO!')

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [metrics, setMetrics] = useState({
    fullRepaintTime: 0,
    partialRepaintTime: 0,
    improvement: 0
  })

  // Desenhar grid de retângulos
  const drawGrid = (ctx: CanvasRenderingContext2D, dirtyRect?: { x: number; y: number; width: number; height: number } | null) => {
    const gridSize = 20
    const rectWidth = 35
    const rectHeight = 25
    const spacing = 40

    let rendered = 0
    let skipped = 0

    for (let row = 0; row < gridSize; row++) {
      for (let col = 0; col < gridSize; col++) {
        const x = col * spacing + 10
        const y = row * spacing + 10

        // Dirty region culling
        if (dirtyRect) {
          const rectRight = x + rectWidth
          const rectLeft = x
          const dirtyRight = dirtyRect.x + dirtyRect.width

          if (rectRight < dirtyRect.x || rectLeft > dirtyRight ||
              y + rectHeight < dirtyRect.y || y > dirtyRect.y + dirtyRect.height) {
            skipped++
            continue
          }
        }

        const hue = (row * gridSize + col) * (360 / (gridSize * gridSize))
        ctx.fillStyle = `hsl(${hue}, 70%, 60%)`
        ctx.fillRect(x, y, rectWidth, rectHeight)
        rendered++
      }
    }

    // Desenhar dirty region
    if (dirtyRect) {
      ctx.strokeStyle = 'red'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 5])
      ctx.strokeRect(dirtyRect.x, dirtyRect.y, dirtyRect.width, dirtyRect.height)
      ctx.setLineDash([])

      ctx.fillStyle = 'red'
      ctx.font = 'bold 14px monospace'
      ctx.fillText(`Dirty Region`, dirtyRect.x + 5, dirtyRect.y + 20)
      ctx.fillText(`Rendered: ${rendered}`, dirtyRect.x + 5, dirtyRect.y + 40)
      ctx.fillText(`Skipped: ${skipped}`, dirtyRect.x + 5, dirtyRect.y + 60)
    }
  }

  // Inicializar canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Desenhar grid inicial
    drawGrid(ctx, null)
  }, [])

  // Full Repaint
  const testFullRepaint = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const start = performance.now()
    ctx.clearRect(0, 0, 800, 600)
    drawGrid(ctx, null)
    const end = performance.now()

    setMetrics(prev => ({ ...prev, fullRepaintTime: end - start }))
  }

  // Partial Repaint
  const testPartialRepaint = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dirtyRect = { x: 100, y: 100, width: 200, height: 150 }

    const start = performance.now()
    ctx.clearRect(dirtyRect.x, dirtyRect.y, dirtyRect.width, dirtyRect.height)
    drawGrid(ctx, dirtyRect)
    const end = performance.now()

    const time = end - start
    setMetrics(prev => ({
      ...prev,
      partialRepaintTime: time,
      improvement: prev.fullRepaintTime > 0 ? ((prev.fullRepaintTime - time) / prev.fullRepaintTime) * 100 : 0
    }))
  }

  return (
    <div style={{ padding: 20, fontFamily: 'monospace', background: '#1a1a1a', minHeight: '100vh', color: 'white' }}>
      <h1 style={{ color: 'white' }}>🧪 Dirty Regions Test</h1>
      <p>Este teste demonstra a otimização de Dirty Regions</p>

      <div style={{ marginBottom: 20 }}>
        <button
          onClick={testFullRepaint}
          style={{
            padding: '10px 20px',
            marginRight: 10,
            fontSize: 16,
            cursor: 'pointer',
            background: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: 4
          }}
        >
          🔄 Full Repaint
        </button>

        <button
          onClick={testPartialRepaint}
          style={{
            padding: '10px 20px',
            fontSize: 16,
            cursor: 'pointer',
            background: '#FF9800',
            color: 'white',
            border: 'none',
            borderRadius: 4
          }}
        >
          ⚡ Partial Repaint
        </button>
      </div>

      {/* Métricas */}
      <div style={{
        background: '#2a2a2a',
        padding: 20,
        borderRadius: 8,
        marginBottom: 20,
        color: 'white'
      }}>
        <h3 style={{ color: 'white' }}>📊 Métricas de Performance</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid #444' }}>
              <td style={{ padding: 8 }}><strong>Full Repaint Time:</strong></td>
              <td style={{ padding: 8, color: '#f44336' }}>
                {metrics.fullRepaintTime.toFixed(2)} ms
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #444' }}>
              <td style={{ padding: 8 }}><strong>Partial Repaint Time:</strong></td>
              <td style={{ padding: 8, color: '#4CAF50' }}>
                {metrics.partialRepaintTime.toFixed(2)} ms
              </td>
            </tr>
            <tr>
              <td style={{ padding: 8 }}><strong>Improvement:</strong></td>
              <td style={{ padding: 8, color: '#2196F3', fontWeight: 'bold' }}>
                {metrics.improvement.toFixed(1)}% mais rápido!
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={{
          border: '2px solid #333',
          borderRadius: 8,
          background: '#000'
        }}
      />

      {/* Legenda */}
      <div style={{ marginTop: 20, fontSize: 14, color: 'white' }}>
        <p><strong>Como funciona:</strong></p>
        <ul>
          <li><strong>Full Repaint:</strong> Redesenha todos os 400 retângulos</li>
          <li><strong>Partial Repaint:</strong> Redesenha apenas retângulos dentro da caixa vermelha</li>
          <li><strong>Resultado esperado:</strong> 60-80% mais rápido no partial repaint</li>
        </ul>
      </div>
    </div>
  )
}

export default DirtyRegionsTestPage
