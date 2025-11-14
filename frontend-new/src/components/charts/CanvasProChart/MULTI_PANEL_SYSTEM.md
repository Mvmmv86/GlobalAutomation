# Sistema de Painéis Múltiplos - CanvasProChart

## Visão Geral

Sistema completo de painéis separados para o CanvasProChart, permitindo renderizar indicadores técnicos em painéis independentes com auto-scale, grid e sincronização de zoom/pan.

## Arquitetura

### Componentes Principais

1. **PanelManager.ts** - Gerenciador de painéis
   - Controla layout e posicionamento
   - Redimensionamento dinâmico
   - Adiciona/remove painéis

2. **SeparatePanelLayer.ts** - Layer para painéis separados
   - Renderiza indicadores em painéis próprios
   - Auto-scale por tipo de indicador
   - Grid e labels específicos

3. **PanelDivider.tsx** - Componente React para divisores
   - Drag vertical para redimensionar
   - Visual feedback
   - Touch support para mobile

4. **LayerManager.ts** (atualizado)
   - Suporta adição/remoção dinâmica de layers
   - Renderiza layers estáticas + dinâmicas

## Fluxo de Funcionamento

### 1. Adicionar Indicador

```typescript
// Usuário adiciona RSI
chartRef.current?.addIndicator({
  id: 'rsi-1',
  type: 'RSI',
  displayType: 'separate', // ← Indica painel separado
  enabled: true,
  color: '#9C27B0',
  lineWidth: 2,
  params: { period: 14, overbought: 70, oversold: 30 }
})
```

**O que acontece:**
1. IndicatorLayer adiciona o indicador à lista
2. CanvasProChart detecta `displayType: 'separate'`
3. PanelManager cria novo painel com altura 150px
4. SeparatePanelLayer é criada e inicializada
5. Layer é adicionada ao LayerManager
6. Painel é renderizado na posição correta

### 2. Renderização

**Painel Principal (main):**
- Candles (MainLayer)
- Indicadores overlay: SMA, EMA, Bollinger Bands, etc (IndicatorLayer)
- SL/TP lines (OverlayLayer)

**Painéis Separados (separate):**
- RSI (0-100) com linhas em 30/50/70
- MACD com histogram
- Stochastic (0-100)
- Volume
- ATR
- Etc...

### 3. Sincronização

**Zoom:**
- Usuário faz scroll no gráfico
- ChartEngine.zoom() é chamado
- TODAS as layers (main + separate) são marcadas como dirty
- Painéis separados sincronizam horizontalmente

**Pan:**
- Usuário arrasta o gráfico
- ChartEngine.pan() é chamado
- TODAS as layers são atualizadas
- Eixo X sincronizado entre todos os painéis

### 4. Redimensionamento

**Arrastar Divisor:**
```
┌──────────────────┐
│  Main Panel      │ 500px
├──────────────────┤ ← Divisor arrastável
│  RSI Panel       │ 150px
├──────────────────┤ ← Divisor arrastável
│  MACD Panel      │ 150px
└──────────────────┘
```

- Usuário arrasta divisor
- PanelManager.resizePanel() ajusta alturas
- updatePanelPositions() recalcula posições Y
- SeparatePanelLayer.setPanelPosition() atualiza
- Renderização automática

## Auto-Scale por Tipo

### Indicadores com Faixa Fixa

```typescript
// RSI, STOCHRSI, MFI
bounds = { min: 0, max: 100, range: 100 }
grid = [30, 50, 70]

// Williams %R
bounds = { min: -100, max: 0, range: 100 }
grid = [-20, -50, -80]

// CCI
bounds = { min: -200, max: 200, range: 400 }
grid = [-100, 0, 100]
```

### Indicadores Dinâmicos

```typescript
// MACD, Volume, OBV, etc
bounds = calculateBounds(values) // min/max dos valores
grid = 5 linhas espaçadas uniformemente
```

## Grid e Labels

Cada painel renderiza:
1. **Background** - Cor de fundo
2. **Grid Lines** - Linhas horizontais com valores
3. **Labels** - Valores numéricos no lado direito
4. **Title** - Nome do indicador no topo
5. **Border** - Linha separadora

## Performance

### Otimizações

1. **Dirty Regions** - Apenas redesenha o que mudou
2. **Cache de Indicadores** - Resultados são cached
3. **requestAnimationFrame** - Renderização batched
4. **Canvas por Layer** - Isolamento de contextos

### Invalidação de Cache

```typescript
// Quando candles mudam
separatePanelLayersRef.current.forEach(layer => {
  layer.invalidateCache() // ← Força recálculo
  layer.markDirty()
})
```

## Uso no Código

### Adicionar Indicador Overlay (Painel Principal)

```typescript
chartRef.current?.addIndicator({
  id: 'ema-20',
  type: 'EMA',
  displayType: 'overlay', // ← Renderiza no painel principal
  enabled: true,
  color: '#FF9800',
  lineWidth: 2,
  params: { period: 20 }
})
```

### Adicionar Indicador Separate (Painel Próprio)

```typescript
chartRef.current?.addIndicator({
  id: 'macd-1',
  type: 'MACD',
  displayType: 'separate', // ← Cria painel separado
  enabled: true,
  color: '#4CAF50',
  lineWidth: 2,
  params: { fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 }
})
```

### Remover Indicador

```typescript
// Remove indicador E painel (se for separate)
chartRef.current?.removeIndicator('macd-1')
```

### Limpar Todos

```typescript
// Remove TODOS os indicadores e painéis
chartRef.current?.clearIndicators()
```

## Estrutura de Arquivos

```
CanvasProChart/
├── PanelManager.ts              # Gerenciador de painéis
├── components/
│   └── PanelDivider.tsx         # Divisor arrastável
├── layers/
│   ├── IndicatorLayer.ts        # Indicadores overlay (atualizado)
│   └── SeparatePanelLayer.ts    # Indicadores em painéis separados
├── core/
│   └── LayerManager.ts          # Gerenciador de layers (atualizado)
└── index.tsx                    # CanvasProChart principal (atualizado)
```

## Próximos Passos Possíveis

- [ ] Persistir layout de painéis no localStorage
- [ ] Drag & drop de indicadores entre painéis
- [ ] Maximizar/minimizar painéis
- [ ] Templates de layout pré-configurados
- [ ] Múltiplos indicadores por painel
- [ ] Personalização de cores de grid/background por painel
- [ ] Export de screenshot incluindo todos os painéis

## Compatibilidade

- ✅ Desktop (Mouse)
- ✅ Mobile (Touch)
- ✅ Todos os 30+ indicadores
- ✅ Dark/Light theme
- ✅ Resize de janela
- ✅ 100k+ candles
