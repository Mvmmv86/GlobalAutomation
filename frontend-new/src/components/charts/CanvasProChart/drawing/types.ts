/**
 * Drawing Tools Types - Sistema Profissional de Ferramentas de Desenho
 * FASE 11: Trend Lines, Rectangles, Fibonacci, Text Annotations
 */

// ============================================================================
// ENUMS
// ============================================================================

export enum DrawingType {
  TREND_LINE = 'TREND_LINE',
  HORIZONTAL_LINE = 'HORIZONTAL_LINE',
  VERTICAL_LINE = 'VERTICAL_LINE',
  RECTANGLE = 'RECTANGLE',
  FIBONACCI_RETRACEMENT = 'FIBONACCI_RETRACEMENT',
  TEXT = 'TEXT',
  ARROW = 'ARROW',
  CHANNEL = 'CHANNEL'
}

export enum DrawingState {
  IDLE = 'IDLE',           // Nenhum desenho ativo
  CREATING = 'CREATING',   // Criando novo desenho (aguardando cliques)
  SELECTED = 'SELECTED',   // Desenho selecionado
  DRAGGING = 'DRAGGING',   // Movendo desenho
  RESIZING = 'RESIZING'    // Redimensionando desenho
}

export enum LineStyle {
  SOLID = 'SOLID',
  DASHED = 'DASHED',
  DOTTED = 'DOTTED'
}

export enum AnchorPoint {
  START = 'START',         // Ponto inicial (ex: início da linha)
  END = 'END',             // Ponto final
  TOP_LEFT = 'TOP_LEFT',   // Cantos do retângulo
  TOP_RIGHT = 'TOP_RIGHT',
  BOTTOM_LEFT = 'BOTTOM_LEFT',
  BOTTOM_RIGHT = 'BOTTOM_RIGHT',
  CENTER = 'CENTER'        // Centro do desenho
}

// ============================================================================
// INTERFACES BASE
// ============================================================================

/**
 * Representa um ponto no gráfico
 * timestamp: Timestamp do candle (eixo X)
 * price: Preço (eixo Y)
 */
export interface ChartPoint {
  timestamp: number
  price: number
}

/**
 * Representa um ponto em coordenadas de canvas
 */
export interface CanvasPoint {
  x: number
  y: number
}

/**
 * Configuração de estilo para desenhos
 */
export interface DrawingStyle {
  color: string
  lineWidth: number
  lineStyle: LineStyle
  fillColor?: string       // Para retângulos
  fillOpacity?: number     // Opacidade do preenchimento (0-1)
  fontSize?: number        // Para texto
  fontFamily?: string
  textColor?: string
}

/**
 * Interface base para todos os desenhos
 */
export interface BaseDrawing {
  id: string
  type: DrawingType
  points: ChartPoint[]     // Pontos âncora no gráfico (timestamp + price)
  style: DrawingStyle
  locked: boolean          // Se true, não pode ser editado
  visible: boolean
  zIndex: number           // Ordem de renderização
  createdAt: number
  updatedAt: number
  metadata?: Record<string, any>  // Dados customizados
}

// ============================================================================
// SPECIFIC DRAWING INTERFACES
// ============================================================================

/**
 * Linha de tendência (2 pontos)
 */
export interface TrendLineDrawing extends BaseDrawing {
  type: DrawingType.TREND_LINE
  points: [ChartPoint, ChartPoint]
  extendLeft?: boolean     // Estender linha para a esquerda
  extendRight?: boolean    // Estender linha para a direita
  showAngle?: boolean      // Mostrar ângulo da linha
  showDistance?: boolean   // Mostrar distância em %
}

/**
 * Linha horizontal (1 ponto, se estende horizontalmente)
 */
export interface HorizontalLineDrawing extends BaseDrawing {
  type: DrawingType.HORIZONTAL_LINE
  points: [ChartPoint]
  label?: string           // Texto ao lado da linha (ex: "Suporte", "Resistência")
}

/**
 * Linha vertical (1 ponto, se estende verticalmente)
 */
export interface VerticalLineDrawing extends BaseDrawing {
  type: DrawingType.VERTICAL_LINE
  points: [ChartPoint]
  label?: string
}

/**
 * Retângulo (2 pontos diagonalmente opostos)
 */
export interface RectangleDrawing extends BaseDrawing {
  type: DrawingType.RECTANGLE
  points: [ChartPoint, ChartPoint]  // Top-left e bottom-right
  filled: boolean
  showPriceRange?: boolean  // Mostrar altura em % ou preço
}

/**
 * Fibonacci Retracement (2 pontos: início e fim da onda)
 */
export interface FibonacciDrawing extends BaseDrawing {
  type: DrawingType.FIBONACCI_RETRACEMENT
  points: [ChartPoint, ChartPoint]
  levels: FibonacciLevel[]
  showLabels: boolean
  showPrices: boolean
}

export interface FibonacciLevel {
  ratio: number            // Ex: 0.236, 0.382, 0.5, 0.618, 0.786, 1.0
  color: string
  lineStyle: LineStyle
  label: string            // Ex: "23.6%", "38.2%"
  price?: number           // Calculado dinamicamente
}

/**
 * Anotação de texto
 */
export interface TextDrawing extends BaseDrawing {
  type: DrawingType.TEXT
  points: [ChartPoint]
  text: string
  backgroundColor?: string
  borderColor?: string
  padding?: number
  anchor?: 'top' | 'bottom' | 'left' | 'right' | 'center'
}

/**
 * Seta (2 pontos: início e fim)
 */
export interface ArrowDrawing extends BaseDrawing {
  type: DrawingType.ARROW
  points: [ChartPoint, ChartPoint]
  arrowHeadSize: number
}

/**
 * Canal paralelo (3 pontos: 2 para linha base, 1 para largura)
 */
export interface ChannelDrawing extends BaseDrawing {
  type: DrawingType.CHANNEL
  points: [ChartPoint, ChartPoint, ChartPoint]
  filled: boolean
}

// ============================================================================
// UNION TYPE FOR ALL DRAWINGS
// ============================================================================

export type AnyDrawing =
  | TrendLineDrawing
  | HorizontalLineDrawing
  | VerticalLineDrawing
  | RectangleDrawing
  | FibonacciDrawing
  | TextDrawing
  | ArrowDrawing
  | ChannelDrawing

// ============================================================================
// DRAWING MANAGER STATE
// ============================================================================

export interface DrawingManagerState {
  drawings: AnyDrawing[]
  activeDrawingType: DrawingType | null  // Tipo de desenho sendo criado
  selectedDrawingId: string | null
  state: DrawingState
  tempPoints: ChartPoint[]               // Pontos temporários durante criação
  hoveredDrawingId: string | null        // Desenho sob o cursor
  hoveredAnchor: AnchorPoint | null      // Âncora sob o cursor (para resize)
}

// ============================================================================
// DRAWING TEMPLATES
// ============================================================================

export const DEFAULT_DRAWING_STYLES: Record<DrawingType, DrawingStyle> = {
  [DrawingType.TREND_LINE]: {
    color: '#2196F3',
    lineWidth: 2,
    lineStyle: LineStyle.SOLID
  },
  [DrawingType.HORIZONTAL_LINE]: {
    color: '#F44336',
    lineWidth: 2,
    lineStyle: LineStyle.DASHED
  },
  [DrawingType.VERTICAL_LINE]: {
    color: '#9C27B0',
    lineWidth: 2,
    lineStyle: LineStyle.DASHED
  },
  [DrawingType.RECTANGLE]: {
    color: '#4CAF50',
    lineWidth: 2,
    lineStyle: LineStyle.SOLID,
    fillColor: '#4CAF50',
    fillOpacity: 0.1
  },
  [DrawingType.FIBONACCI_RETRACEMENT]: {
    color: '#FF9800',
    lineWidth: 1,
    lineStyle: LineStyle.SOLID
  },
  [DrawingType.TEXT]: {
    color: '#FFFFFF',
    lineWidth: 1,
    lineStyle: LineStyle.SOLID,
    fontSize: 14,
    fontFamily: 'Arial, sans-serif',
    textColor: '#FFFFFF',
    fillColor: '#000000',
    fillOpacity: 0.7
  },
  [DrawingType.ARROW]: {
    color: '#00BCD4',
    lineWidth: 2,
    lineStyle: LineStyle.SOLID
  },
  [DrawingType.CHANNEL]: {
    color: '#E91E63',
    lineWidth: 2,
    lineStyle: LineStyle.SOLID,
    fillColor: '#E91E63',
    fillOpacity: 0.05
  }
}

export const DEFAULT_FIBONACCI_LEVELS: FibonacciLevel[] = [
  { ratio: 0, color: '#808080', lineStyle: LineStyle.SOLID, label: '0%' },
  { ratio: 0.236, color: '#F44336', lineStyle: LineStyle.DASHED, label: '23.6%' },
  { ratio: 0.382, color: '#FF9800', lineStyle: LineStyle.DASHED, label: '38.2%' },
  { ratio: 0.5, color: '#FFC107', lineStyle: LineStyle.DASHED, label: '50%' },
  { ratio: 0.618, color: '#4CAF50', lineStyle: LineStyle.DASHED, label: '61.8%' },
  { ratio: 0.786, color: '#2196F3', lineStyle: LineStyle.DASHED, label: '78.6%' },
  { ratio: 1, color: '#808080', lineStyle: LineStyle.SOLID, label: '100%' }
]

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Gera ID único para desenho
 */
export const generateDrawingId = (type: DrawingType): string => {
  return `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Calcula distância entre dois pontos em canvas
 */
export const distance = (p1: CanvasPoint, p2: CanvasPoint): number => {
  const dx = p2.x - p1.x
  const dy = p2.y - p1.y
  return Math.sqrt(dx * dx + dy * dy)
}

/**
 * Verifica se um ponto está próximo de uma linha (para hit detection)
 */
export const isPointNearLine = (
  point: CanvasPoint,
  lineStart: CanvasPoint,
  lineEnd: CanvasPoint,
  threshold: number = 5
): boolean => {
  const dx = lineEnd.x - lineStart.x
  const dy = lineEnd.y - lineStart.y
  const length = Math.sqrt(dx * dx + dy * dy)

  if (length === 0) return distance(point, lineStart) <= threshold

  const t = Math.max(0, Math.min(1, ((point.x - lineStart.x) * dx + (point.y - lineStart.y) * dy) / (length * length)))
  const projection = {
    x: lineStart.x + t * dx,
    y: lineStart.y + t * dy
  }

  return distance(point, projection) <= threshold
}

/**
 * Verifica se um ponto está dentro de um retângulo
 */
export const isPointInRect = (
  point: CanvasPoint,
  rectTopLeft: CanvasPoint,
  rectBottomRight: CanvasPoint
): boolean => {
  return (
    point.x >= rectTopLeft.x &&
    point.x <= rectBottomRight.x &&
    point.y >= rectTopLeft.y &&
    point.y <= rectBottomRight.y
  )
}
