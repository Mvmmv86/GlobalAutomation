/**
 * DrawingToolbar - Painel de Ferramentas de Desenho
 * FASE 11: UI profissional para seleção de ferramentas
 */

import React, { useState } from 'react'
import {
  TrendingUp,
  Minus,
  SquareDashedBottom,
  Square,
  GitBranch,
  Type,
  ArrowRight,
  Edit3,
  Trash2,
  Save,
  Upload,
  X
} from 'lucide-react'
import { DrawingType, AnyDrawing } from './types'

export interface DrawingToolbarProps {
  activeDrawingType: DrawingType | null
  selectedDrawingId: string | null
  drawings: AnyDrawing[]
  onSelectTool: (type: DrawingType | null) => void
  onDeleteSelected: () => void
  onClearAll: () => void
  onExport: () => void
  onImport: (json: string) => void
  theme?: 'dark' | 'light'
}

export const DrawingToolbar: React.FC<DrawingToolbarProps> = ({
  activeDrawingType,
  selectedDrawingId,
  drawings,
  onSelectTool,
  onDeleteSelected,
  onClearAll,
  onExport,
  onImport,
  theme = 'dark'
}) => {
  const [expanded, setExpanded] = useState(true)

  const bgColor = theme === 'dark' ? '#1e222d' : '#ffffff'
  const borderColor = theme === 'dark' ? '#2a2e39' : '#e0e3eb'
  const textColor = theme === 'dark' ? '#d1d4dc' : '#131722'
  const hoverBg = theme === 'dark' ? '#2a2e39' : '#f0f3fa'
  const activeBg = '#2196F3'

  const tools: Array<{
    type: DrawingType
    icon: React.ReactNode
    label: string
    description: string
  }> = [
    {
      type: DrawingType.TREND_LINE,
      icon: <TrendingUp size={18} />,
      label: 'Trend Line',
      description: 'Linha de tendência'
    },
    {
      type: DrawingType.HORIZONTAL_LINE,
      icon: <Minus size={18} />,
      label: 'Horizontal',
      description: 'Linha horizontal'
    },
    {
      type: DrawingType.VERTICAL_LINE,
      icon: <SquareDashedBottom size={18} style={{ transform: 'rotate(90deg)' }} />,
      label: 'Vertical',
      description: 'Linha vertical'
    },
    {
      type: DrawingType.RECTANGLE,
      icon: <Square size={18} />,
      label: 'Rectangle',
      description: 'Retângulo'
    },
    {
      type: DrawingType.FIBONACCI_RETRACEMENT,
      icon: <GitBranch size={18} />,
      label: 'Fibonacci',
      description: 'Fibonacci Retracement'
    },
    {
      type: DrawingType.TEXT,
      icon: <Type size={18} />,
      label: 'Text',
      description: 'Anotação de texto'
    },
    {
      type: DrawingType.ARROW,
      icon: <ArrowRight size={18} />,
      label: 'Arrow',
      description: 'Seta'
    },
    {
      type: DrawingType.CHANNEL,
      icon: <Edit3 size={18} />,
      label: 'Channel',
      description: 'Canal paralelo'
    }
  ]

  const handleToolClick = (type: DrawingType) => {
    if (activeDrawingType === type) {
      onSelectTool(null) // Desselecionar
    } else {
      onSelectTool(type)
    }
  }

  const handleFileImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const json = event.target?.result as string
      onImport(json)
    }
    reader.readAsText(file)
  }

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        style={{
          position: 'absolute',
          left: 10,
          top: 10,
          padding: '8px 12px',
          background: bgColor,
          border: `1px solid ${borderColor}`,
          borderRadius: '6px',
          color: textColor,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '13px',
          fontWeight: 500,
          zIndex: 100,
          boxShadow: theme === 'dark'
            ? '0 2px 8px rgba(0,0,0,0.3)'
            : '0 2px 8px rgba(0,0,0,0.1)'
        }}
      >
        <Edit3 size={16} />
        Desenhos ({drawings.length})
      </button>
    )
  }

  return (
    <div
      style={{
        position: 'absolute',
        left: 10,
        top: 10,
        width: '240px',
        background: bgColor,
        border: `1px solid ${borderColor}`,
        borderRadius: '8px',
        padding: '12px',
        zIndex: 100,
        boxShadow: theme === 'dark'
          ? '0 4px 16px rgba(0,0,0,0.4)'
          : '0 4px 16px rgba(0,0,0,0.15)',
        maxHeight: 'calc(100vh - 40px)',
        overflowY: 'auto'
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
          paddingBottom: '8px',
          borderBottom: `1px solid ${borderColor}`
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Edit3 size={16} color={textColor} />
          <span style={{ color: textColor, fontSize: '14px', fontWeight: 600 }}>
            Ferramentas de Desenho
          </span>
        </div>
        <button
          onClick={() => setExpanded(false)}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            color: textColor,
            opacity: 0.7
          }}
          onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
          onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
        >
          <X size={16} />
        </button>
      </div>

      {/* Tools Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '8px',
          marginBottom: '12px'
        }}
      >
        {tools.map((tool) => {
          const isActive = activeDrawingType === tool.type

          return (
            <button
              key={tool.type}
              onClick={() => handleToolClick(tool.type)}
              title={tool.description}
              style={{
                padding: '10px',
                background: isActive ? activeBg : 'transparent',
                border: `1px solid ${isActive ? activeBg : borderColor}`,
                borderRadius: '6px',
                color: isActive ? '#ffffff' : textColor,
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '4px',
                fontSize: '11px',
                fontWeight: 500,
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = hoverBg
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              {tool.icon}
              <span>{tool.label}</span>
            </button>
          )
        })}
      </div>

      {/* Drawing Info */}
      <div
        style={{
          padding: '8px',
          background: theme === 'dark' ? '#131722' : '#f5f7fa',
          borderRadius: '6px',
          marginBottom: '12px'
        }}
      >
        <div style={{ fontSize: '12px', color: textColor, opacity: 0.8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span>Total de desenhos:</span>
            <span style={{ fontWeight: 600 }}>{drawings.length}</span>
          </div>
          {selectedDrawingId && (
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Selecionado:</span>
              <span style={{ fontWeight: 600, color: activeBg }}>Sim</span>
            </div>
          )}
          {activeDrawingType && (
            <div style={{ marginTop: '4px', color: activeBg, fontWeight: 500 }}>
              Modo: Criando {tools.find(t => t.type === activeDrawingType)?.label}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '6px'
        }}
      >
        {selectedDrawingId && (
          <button
            onClick={onDeleteSelected}
            style={{
              padding: '8px 12px',
              background: 'transparent',
              border: `1px solid #F44336`,
              borderRadius: '6px',
              color: '#F44336',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 500,
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#F44336'
              e.currentTarget.style.color = '#ffffff'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = '#F44336'
            }}
          >
            <Trash2 size={14} />
            Deletar Selecionado
          </button>
        )}

        {drawings.length > 0 && (
          <>
            <button
              onClick={onClearAll}
              style={{
                padding: '8px 12px',
                background: 'transparent',
                border: `1px solid ${borderColor}`,
                borderRadius: '6px',
                color: textColor,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 500,
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = hoverBg
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              <Trash2 size={14} />
              Limpar Todos
            </button>

            <button
              onClick={onExport}
              style={{
                padding: '8px 12px',
                background: 'transparent',
                border: `1px solid ${borderColor}`,
                borderRadius: '6px',
                color: textColor,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 500,
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = hoverBg
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              <Save size={14} />
              Exportar Desenhos
            </button>
          </>
        )}

        <label
          style={{
            padding: '8px 12px',
            background: 'transparent',
            border: `1px solid ${borderColor}`,
            borderRadius: '6px',
            color: textColor,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            fontSize: '12px',
            fontWeight: 500,
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = hoverBg
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent'
          }}
        >
          <Upload size={14} />
          Importar Desenhos
          <input
            type="file"
            accept=".json"
            onChange={handleFileImport}
            style={{ display: 'none' }}
          />
        </label>
      </div>

      {/* Instructions */}
      {activeDrawingType && (
        <div
          style={{
            marginTop: '12px',
            padding: '8px',
            background: theme === 'dark' ? 'rgba(33, 150, 243, 0.1)' : 'rgba(33, 150, 243, 0.05)',
            border: `1px solid rgba(33, 150, 243, 0.3)`,
            borderRadius: '6px',
            fontSize: '11px',
            color: textColor,
            lineHeight: '1.4'
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '4px', color: activeBg }}>
            Instruções:
          </div>
          {getInstructions(activeDrawingType)}
        </div>
      )}
    </div>
  )
}

/**
 * Retorna instruções de uso para cada ferramenta
 */
function getInstructions(type: DrawingType): string {
  switch (type) {
    case DrawingType.TREND_LINE:
      return 'Clique em 2 pontos no gráfico para criar a linha de tendência.'
    case DrawingType.HORIZONTAL_LINE:
      return 'Clique em 1 ponto no gráfico para criar a linha horizontal.'
    case DrawingType.VERTICAL_LINE:
      return 'Clique em 1 ponto no gráfico para criar a linha vertical.'
    case DrawingType.RECTANGLE:
      return 'Clique em 2 cantos opostos do retângulo (diagonal).'
    case DrawingType.FIBONACCI_RETRACEMENT:
      return 'Clique no início e no fim da onda para calcular os níveis de Fibonacci.'
    case DrawingType.TEXT:
      return 'Clique no gráfico onde deseja adicionar o texto.'
    case DrawingType.ARROW:
      return 'Clique no ponto inicial e no ponto final da seta.'
    case DrawingType.CHANNEL:
      return 'Clique em 2 pontos para a linha base, depois 1 ponto para a largura do canal.'
    default:
      return 'Clique no gráfico para usar a ferramenta.'
  }
}

export default DrawingToolbar
