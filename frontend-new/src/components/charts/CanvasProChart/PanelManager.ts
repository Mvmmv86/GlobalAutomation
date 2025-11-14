/**
 * PanelManager - Gerencia múltiplos painéis de gráficos
 * Suporta:
 * - Painel principal (candles + indicators overlay)
 * - Painéis separados (RSI, MACD, Stochastic, etc)
 * - Resize dinâmico entre painéis
 */

export interface PanelConfig {
  id: string
  type: 'main' | 'separate'
  height: number // Altura em pixels
  minHeight: number // Altura mínima
  maxHeight: number // Altura máxima
  indicators: string[] // IDs dos indicadores neste painel
  title?: string
}

export interface PanelLayout {
  panels: PanelConfig[]
  totalHeight: number
  dividerHeight: number // Altura do divisor arrastável
}

export class PanelManager {
  private layout: PanelLayout
  private container: HTMLElement
  private onLayoutChange?: (layout: PanelLayout) => void

  constructor(container: HTMLElement, totalHeight: number) {
    this.container = container
    this.layout = {
      panels: [
        {
          id: 'main',
          type: 'main',
          height: totalHeight, // 100% inicialmente
          minHeight: 300,
          maxHeight: totalHeight - 100,
          indicators: []
        }
      ],
      totalHeight,
      dividerHeight: 4
    }
  }

  /**
   * Adiciona um novo painel separado
   */
  addPanel(config: Omit<PanelConfig, 'id'>): string {
    const id = `panel-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

    // Calcular altura disponível
    const usedHeight = this.layout.panels.reduce((sum, p) => sum + p.height, 0)
    const dividersHeight = (this.layout.panels.length) * this.layout.dividerHeight
    const availableHeight = this.layout.totalHeight - usedHeight - dividersHeight - this.layout.dividerHeight

    const newPanel: PanelConfig = {
      id,
      ...config,
      height: Math.min(config.height, availableHeight),
      minHeight: Math.max(config.minHeight || 100, 80),
      maxHeight: Math.min(config.maxHeight || 400, availableHeight)
    }

    // Reduzir altura do painel principal se necessário
    const mainPanel = this.layout.panels.find(p => p.type === 'main')
    if (mainPanel) {
      const requiredSpace = newPanel.height + this.layout.dividerHeight
      if (requiredSpace > availableHeight) {
        mainPanel.height = Math.max(mainPanel.minHeight, mainPanel.height - requiredSpace + availableHeight)
      }
    }

    this.layout.panels.push(newPanel)
    this.notifyLayoutChange()

    return id
  }

  /**
   * Remove um painel
   */
  removePanel(panelId: string): void {
    const index = this.layout.panels.findIndex(p => p.id === panelId)
    if (index === -1 || this.layout.panels[index].type === 'main') {
      return // Não pode remover painel principal
    }

    const removedPanel = this.layout.panels[index]
    this.layout.panels.splice(index, 1)

    // Redistribuir altura para o painel principal
    const mainPanel = this.layout.panels.find(p => p.type === 'main')
    if (mainPanel) {
      mainPanel.height += removedPanel.height + this.layout.dividerHeight
    }

    this.notifyLayoutChange()
  }

  /**
   * Redimensiona um painel (usado durante drag do divisor)
   */
  resizePanel(panelId: string, deltaHeight: number): void {
    const index = this.layout.panels.findIndex(p => p.id === panelId)
    if (index === -1) return

    const panel = this.layout.panels[index]
    const nextPanel = this.layout.panels[index + 1]

    if (!nextPanel) return // Último painel não pode ser redimensionado

    // Calcular novos tamanhos respeitando limites
    const newHeight = Math.max(
      panel.minHeight,
      Math.min(panel.maxHeight, panel.height + deltaHeight)
    )
    const actualDelta = newHeight - panel.height

    const newNextHeight = Math.max(
      nextPanel.minHeight,
      Math.min(nextPanel.maxHeight, nextPanel.height - actualDelta)
    )
    const actualNextDelta = nextPanel.height - newNextHeight

    // Aplicar mudanças apenas se ambos os painéis puderem ser redimensionados
    if (Math.abs(actualDelta + actualNextDelta) < 1) {
      panel.height = newHeight
      nextPanel.height = newNextHeight
      this.notifyLayoutChange()
    }
  }

  /**
   * Adiciona um indicador a um painel
   */
  addIndicatorToPanel(panelId: string, indicatorId: string): void {
    const panel = this.layout.panels.find(p => p.id === panelId)
    if (panel && !panel.indicators.includes(indicatorId)) {
      panel.indicators.push(indicatorId)
      this.notifyLayoutChange()
    }
  }

  /**
   * Remove um indicador de um painel
   */
  removeIndicatorFromPanel(panelId: string, indicatorId: string): void {
    const panel = this.layout.panels.find(p => p.id === panelId)
    if (panel) {
      panel.indicators = panel.indicators.filter(id => id !== indicatorId)

      // Se painel separado ficou vazio, removê-lo
      if (panel.type === 'separate' && panel.indicators.length === 0) {
        this.removePanel(panelId)
      } else {
        this.notifyLayoutChange()
      }
    }
  }

  /**
   * Move indicador entre painéis
   */
  moveIndicator(indicatorId: string, fromPanelId: string, toPanelId: string): void {
    this.removeIndicatorFromPanel(fromPanelId, indicatorId)
    this.addIndicatorToPanel(toPanelId, indicatorId)
  }

  /**
   * Retorna todos os painéis
   */
  getPanels(): PanelConfig[] {
    return [...this.layout.panels]
  }

  /**
   * Retorna um painel específico
   */
  getPanel(panelId: string): PanelConfig | undefined {
    return this.layout.panels.find(p => p.id === panelId)
  }

  /**
   * Retorna o painel principal
   */
  getMainPanel(): PanelConfig | undefined {
    return this.layout.panels.find(p => p.type === 'main')
  }

  /**
   * Atualiza altura total e recalcula layout
   */
  resize(newHeight: number): void {
    const ratio = newHeight / this.layout.totalHeight

    this.layout.panels.forEach(panel => {
      panel.height = Math.floor(panel.height * ratio)
      panel.maxHeight = Math.floor(panel.maxHeight * ratio)
    })

    this.layout.totalHeight = newHeight
    this.notifyLayoutChange()
  }

  /**
   * Define callback para mudanças de layout
   */
  onLayoutChangeCallback(callback: (layout: PanelLayout) => void): void {
    this.onLayoutChange = callback
  }

  /**
   * Notifica mudanças no layout
   */
  private notifyLayoutChange(): void {
    if (this.onLayoutChange) {
      this.onLayoutChange(this.layout)
    }
  }

  /**
   * Retorna layout atual
   */
  getLayout(): PanelLayout {
    return { ...this.layout, panels: [...this.layout.panels] }
  }

  /**
   * Define layout completo
   */
  setLayout(layout: PanelLayout): void {
    this.layout = layout
    this.notifyLayoutChange()
  }

  /**
   * Calcula posições Y de cada painel
   */
  calculatePanelPositions(): Array<{ panelId: string; y: number; height: number }> {
    const positions: Array<{ panelId: string; y: number; height: number }> = []
    let currentY = 0

    this.layout.panels.forEach((panel, index) => {
      positions.push({
        panelId: panel.id,
        y: currentY,
        height: panel.height
      })

      currentY += panel.height

      // Adicionar espaço do divisor (exceto após último painel)
      if (index < this.layout.panels.length - 1) {
        currentY += this.layout.dividerHeight
      }
    })

    return positions
  }

  /**
   * Encontra painel em uma coordenada Y
   */
  findPanelAtY(y: number): PanelConfig | undefined {
    const positions = this.calculatePanelPositions()

    for (const pos of positions) {
      if (y >= pos.y && y < pos.y + pos.height) {
        return this.layout.panels.find(p => p.id === pos.panelId)
      }
    }

    return undefined
  }

  /**
   * Verifica se Y está sobre um divisor
   */
  isDividerAtY(y: number, tolerance: number = 4): { panelId: string; index: number } | null {
    const positions = this.calculatePanelPositions()

    for (let i = 0; i < positions.length - 1; i++) {
      const dividerY = positions[i].y + positions[i].height

      if (Math.abs(y - dividerY) <= tolerance) {
        return {
          panelId: positions[i].panelId,
          index: i
        }
      }
    }

    return null
  }

  /**
   * Limpa todos os painéis separados
   */
  clearSeparatePanels(): void {
    const mainPanel = this.getMainPanel()
    if (!mainPanel) return

    // Calcular altura total dos painéis separados
    const separatePanelsHeight = this.layout.panels
      .filter(p => p.type === 'separate')
      .reduce((sum, p) => sum + p.height + this.layout.dividerHeight, 0)

    // Remover todos os painéis separados
    this.layout.panels = this.layout.panels.filter(p => p.type === 'main')

    // Redistribuir altura para o painel principal
    mainPanel.height += separatePanelsHeight

    this.notifyLayoutChange()
  }

  /**
   * Destrói o PanelManager
   */
  destroy(): void {
    this.layout.panels = []
    this.onLayoutChange = undefined
  }
}
