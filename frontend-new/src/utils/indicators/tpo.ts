/**
 * TPO (Time Price Opportunity) / Market Profile Indicator
 * RÉPLICA EXATA do Pine Script "TPO (Replica)" by Criptooasis
 *
 * Características:
 * - Divisão por SESSÕES (períodos de tempo configuráveis)
 * - Auto Tick Size baseado na média de altura das barras
 * - Value Area 68.26% (1 desvio padrão - padrão estatístico)
 * - Letras TPO (A, B, C, D...) baseadas na ordem DENTRO da sessão
 * - Cores: Laranja (open), Vermelho (POC), Azul (VA), Verde (fora VA)
 */

import { CandlestickData } from 'lightweight-charts'

// ============================================================================
// TIPOS
// ============================================================================

export interface TPOConfig {
  // Session Settings - BASEADO EM HORÁRIO (como TradingView)
  use24hSession: boolean         // Se true, usa sessão de 24h (21:00 - 20:59 UTC)
  sessionStartHour: number       // Hora de início da sessão (padrão: 21 = 21:00 UTC)
  sessionBars: number            // Fallback: número de barras por sessão (usado se use24hSession = false)

  // Auto Tick Size
  autoTickSize: boolean
  tickBarsBack: number           // Bars back for avg tick size calculation
  targetSessionHeight: number    // Target number of price levels per session
  manualTickSize: number         // Manual tick size multiplier

  // Value Area
  valueAreaPercent: number       // Default: 68.26 (1 std dev)

  // Visual Options
  showTPOLetters: boolean
  showPOCLine: boolean
  showValueAreaLines: boolean
  showValueAreaBoxes: boolean
  showInfoBox: boolean

  // Colors (Pine Script original)
  colors: {
    open: string              // Laranja - primeiro TPO da sessão
    poc: string               // Vermelho - POC
    pocBox: string            // Vermelho - box do POC
    inValue: string           // Azul - Value Area
    inValueBox: string        // Azul - box do Value Area
    outOfValue: string        // Verde - fora do Value Area
    outOfValueBox: string     // Verde - box fora do Value Area
  }

  // Transparency (0-100)
  inValueBoxTransparency: number
  outOfValueBoxTransparency: number
}

// TPO Letter info for each candle that touched a price level
export interface TPOLetter {
  letter: string              // A, B, C, D... baseado na ordem DENTRO da sessão
  barIndex: number            // Índice global do candle
  sessionBarIndex: number     // Índice DENTRO da sessão (0, 1, 2...)
  isOpen: boolean             // Se é o TPO de abertura deste candle
  time: number                // Timestamp do candle
}

// Nível de preço com todos os TPOs
export interface TPOLevel {
  priceMin: number
  priceMax: number
  priceMid: number
  tpoCount: number
  letters: TPOLetter[]
  isPOC: boolean
  isInValueArea: boolean
}

// Profile completo de uma sessão
export interface TPOProfile {
  sessionIndex: number          // Índice da sessão (0, 1, 2...)
  startTime: number
  endTime: number
  startBarIndex: number         // Índice global da primeira barra
  endBarIndex: number           // Índice global da última barra

  levels: TPOLevel[]
  tickSize: number
  tickSizeTicks: number

  poc: number
  pocIndex: number
  vah: number
  val: number
  vahIndex: number
  valIndex: number

  totalTPOs: number
  highestHigh: number
  lowestLow: number
  openPrice: number

  sessionName: string
  currentLetter: string
}

export interface TPOResult {
  profiles: TPOProfile[]
  currentProfile: TPOProfile | null
  config: TPOConfig
}

export interface TPORenderData {
  profile: TPOProfile
  candles: CandlestickData[]
}

export interface TPOBox {
  left: number
  right: number
  top: number
  bottom: number
  color: string
  transparency: number
  isPOC: boolean
  isInValueArea: boolean
}

export interface TPOHorizontalLine {
  price: number
  type: 'poc' | 'vah' | 'val'
  color: string
  startBarIndex: number
  endBarIndex: number
}

// ============================================================================
// CONFIGURAÇÃO PADRÃO
// ============================================================================

export const DEFAULT_TPO_CONFIG: TPOConfig = {
  // Sessão 24h como TradingView (21:00 UTC - 20:59 UTC próximo dia)
  use24hSession: true,           // ATIVADO por padrão - como TradingView
  sessionStartHour: 21,          // 21:00 UTC (= 18:00 BRT) - início da sessão de 24h
  sessionBars: 48,               // Fallback: 48 barras (usado se use24hSession = false)

  autoTickSize: true,
  tickBarsBack: 48,
  targetSessionHeight: 42,       // 🔥 ~42 níveis = tick ~$75 como TradingView (menos níveis = tick maior)
  manualTickSize: 100,

  valueAreaPercent: 68.26,

  showTPOLetters: true,
  showPOCLine: true,
  showValueAreaLines: true,
  showValueAreaBoxes: true,
  showInfoBox: true,

  colors: {
    open: '#FF9800',
    poc: '#FF0000',
    pocBox: '#FF0000',
    inValue: '#2196F3',
    inValueBox: '#2196F3',
    outOfValue: '#4CAF50',
    outOfValueBox: '#4CAF50',
  },

  inValueBoxTransparency: 70,
  outOfValueBoxTransparency: 70,
}

// Letras TPO - A letra é baseada no índice DENTRO da sessão
const TPO_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%&*'

// ============================================================================
// FUNÇÕES AUXILIARES
// ============================================================================

function estimateMinTick(candles: CandlestickData[]): number {
  if (candles.length === 0) return 0.01
  const price = candles[0].close as number
  if (price >= 10000) return 1
  if (price >= 1000) return 0.1
  if (price >= 100) return 0.01
  if (price >= 10) return 0.001
  if (price >= 1) return 0.0001
  return 0.00001
}

function calculateAutoTickSize(
  candles: CandlestickData[],
  tickBarsBack: number,
  targetSessionHeight: number,
  minTick: number
): number {
  if (candles.length === 0) return minTick

  const barsToUse = Math.min(tickBarsBack, candles.length)
  const recentCandles = candles.slice(-barsToUse)

  // 🔥 FIX: Calcular baseado na AMPLITUDE TOTAL (high - low) das barras recentes
  // Isso é como o TradingView faz - usa o range total, não a média de cada barra
  let sessionHigh = -Infinity
  let sessionLow = Infinity

  for (const candle of recentCandles) {
    const high = candle.high as number
    const low = candle.low as number
    if (high > sessionHigh) sessionHigh = high
    if (low < sessionLow) sessionLow = low
  }

  const sessionRange = sessionHigh - sessionLow

  // Tick size = range total / número desejado de níveis
  let tickSize = sessionRange / targetSessionHeight
  tickSize = Math.round(tickSize / minTick) * minTick
  if (tickSize <= 0) tickSize = minTick

  return tickSize
}

function findPOC(levels: TPOLevel[]): number {
  if (levels.length === 0) return 0

  let maxTPOs = 0
  let pocCandidates: number[] = []

  for (let i = 0; i < levels.length; i++) {
    if (levels[i].tpoCount > maxTPOs) {
      maxTPOs = levels[i].tpoCount
      pocCandidates = [i]
    } else if (levels[i].tpoCount === maxTPOs) {
      pocCandidates.push(i)
    }
  }

  if (pocCandidates.length === 1) {
    return pocCandidates[0]
  }

  const midIndex = (levels.length - 1) / 2
  let bestIndex = pocCandidates[0]
  let bestDist = Math.abs(pocCandidates[0] - midIndex)

  for (const idx of pocCandidates) {
    const dist = Math.abs(idx - midIndex)
    if (dist < bestDist) {
      bestDist = dist
      bestIndex = idx
    }
  }

  return bestIndex
}

function calculateValueArea(
  levels: TPOLevel[],
  pocIndex: number,
  totalTPOs: number,
  valueAreaPercent: number
): { valIndex: number; vahIndex: number } {
  if (levels.length === 0 || pocIndex < 0 || pocIndex >= levels.length) {
    return { valIndex: 0, vahIndex: levels.length - 1 }
  }

  // =========================================================================
  // ALGORITMO CME VALUE AREA - 2-Level Look-Ahead (como TradingView)
  //
  // 1. Começar no POC
  // 2. Somar TPOs dos PRÓXIMOS 2 NÍVEIS em cada direção
  // 3. Comparar somas: upSum vs dnSum
  // 4. Expandir na direção com MAIOR soma (adiciona apenas 1 nível por vez)
  // 5. Se empate: expandir para BAIXO (VAL) - como TradingView
  // 6. Repetir até atingir ~68.26% dos TPOs
  // =========================================================================

  const targetVATPOs = Math.round(totalTPOs * (valueAreaPercent / 100))
  let currentVATPOs = levels[pocIndex].tpoCount

  let vahIndex = pocIndex
  let valIndex = pocIndex

  const maxIndex = levels.length - 1

  while (currentVATPOs < targetVATPOs && (vahIndex < maxIndex || valIndex > 0)) {
    const canGoUp = vahIndex < maxIndex
    const canGoDn = valIndex > 0

    if (!canGoUp && !canGoDn) break

    // Soma dos próximos 2 níveis ACIMA (look-ahead)
    let upSum = 0
    if (canGoUp) {
      upSum += levels[vahIndex + 1].tpoCount
      if (vahIndex + 2 <= maxIndex) {
        upSum += levels[vahIndex + 2].tpoCount
      }
    }

    // Soma dos próximos 2 níveis ABAIXO (look-ahead)
    let dnSum = 0
    if (canGoDn) {
      dnSum += levels[valIndex - 1].tpoCount
      if (valIndex - 2 >= 0) {
        dnSum += levels[valIndex - 2].tpoCount
      }
    }

    // Decidir direção baseado na SOMA de 2 níveis
    if (canGoUp && canGoDn) {
      if (upSum > dnSum) {
        // CIMA tem mais TPOs nos próximos 2 níveis
        vahIndex++
        currentVATPOs += levels[vahIndex].tpoCount
      } else if (dnSum > upSum) {
        // BAIXO tem mais TPOs nos próximos 2 níveis
        valIndex--
        currentVATPOs += levels[valIndex].tpoCount
      } else {
        // EMPATE: TradingView prefere expandir para BAIXO (VAL)
        valIndex--
        currentVATPOs += levels[valIndex].tpoCount
      }
    } else if (canGoUp) {
      vahIndex++
      currentVATPOs += levels[vahIndex].tpoCount
    } else {
      valIndex--
      currentVATPOs += levels[valIndex].tpoCount
    }
  }

  return { valIndex, vahIndex }
}

// ============================================================================
// FUNÇÃO PARA CALCULAR UMA ÚNICA SESSÃO
// ============================================================================

function calculateSingleSession(
  candles: CandlestickData[],
  sessionIndex: number,
  globalStartIndex: number,
  config: TPOConfig,
  minTick: number,
  tickSize: number
): TPOProfile | null {
  if (candles.length < 2) return null

  // Encontrar high/low da sessão
  let highestHigh = -Infinity
  let lowestLow = Infinity

  for (const candle of candles) {
    const high = candle.high as number
    const low = candle.low as number
    if (high > highestHigh) highestHigh = high
    if (low < lowestLow) lowestLow = low
  }

  const openPrice = candles[0].open as number

  // Calcular limites do TPO
  const tpoMax = Math.ceil(highestHigh / tickSize) * tickSize
  const tpoMin = Math.floor(lowestLow / tickSize) * tickSize

  const numRows = Math.round((tpoMax - tpoMin) / tickSize)

  if (numRows <= 0 || numRows > 500) {
    return null
  }

  // Criar níveis de preço
  const levels: TPOLevel[] = []

  for (let i = 0; i <= numRows; i++) {
    const priceMin = tpoMin + i * tickSize
    const priceMax = priceMin + tickSize
    const priceMid = priceMin + tickSize / 2

    const letters: TPOLetter[] = []

    // Para cada candle na sessão, verificar se tocou este nível
    for (let barIdx = 0; barIdx < candles.length; barIdx++) {
      const candle = candles[barIdx]
      const high = candle.high as number
      const low = candle.low as number

      // Se o candle tocou este nível de preço
      if (high >= priceMin && low <= priceMax) {
        // A letra é baseada no índice DENTRO da sessão
        const letterIndex = barIdx % TPO_LETTERS.length
        const letter = TPO_LETTERS[letterIndex]

        // Verificar se é abertura
        const candleOpen = candle.open as number
        const isOpen = candleOpen >= priceMin && candleOpen <= priceMax

        letters.push({
          letter,
          barIndex: globalStartIndex + barIdx,  // Índice global
          sessionBarIndex: barIdx,               // Índice dentro da sessão
          isOpen: isOpen && barIdx === 0,        // Apenas primeiro candle da sessão
          time: candle.time as number
        })
      }
    }

    levels.push({
      priceMin,
      priceMax,
      priceMid,
      tpoCount: letters.length,
      letters,
      isPOC: false,
      isInValueArea: false,
    })
  }

  // Filtrar níveis vazios
  const nonEmptyLevels = levels.filter((l) => l.tpoCount > 0)

  if (nonEmptyLevels.length === 0) {
    return null
  }

  // Encontrar POC
  const pocIndex = findPOC(nonEmptyLevels)
  nonEmptyLevels[pocIndex].isPOC = true

  // Calcular total de TPOs
  const totalTPOs = nonEmptyLevels.reduce((sum, l) => sum + l.tpoCount, 0)

  // Calcular Value Area
  const { valIndex, vahIndex } = calculateValueArea(
    nonEmptyLevels,
    pocIndex,
    totalTPOs,
    config.valueAreaPercent
  )

  // Marcar níveis dentro do Value Area
  for (let i = valIndex; i <= vahIndex; i++) {
    if (nonEmptyLevels[i]) {
      nonEmptyLevels[i].isInValueArea = true
    }
  }

  // Letra atual
  const currentLetter = TPO_LETTERS[(candles.length - 1) % TPO_LETTERS.length]

  // DEBUG: Log dos valores calculados
  // 🔥 FIX: Usar priceMid para todos (POC, VAH, VAL)
  // TradingView usa o ponto central de cada nível para representar o preço
  const pocPrice = nonEmptyLevels[pocIndex]?.priceMid || 0
  const vahPrice = nonEmptyLevels[vahIndex]?.priceMid || highestHigh
  const valPrice = nonEmptyLevels[valIndex]?.priceMid || lowestLow

  // Calcular TPOs reais no Value Area
  let vaTPOs = 0
  for (let i = valIndex; i <= vahIndex; i++) {
    vaTPOs += nonEmptyLevels[i].tpoCount
  }
  const vaPercentActual = (vaTPOs / totalTPOs) * 100

  console.log(`📊 TPO Session ${sessionIndex + 1}:`, {
    totalLevels: nonEmptyLevels.length,
    pocIndex,
    valIndex,
    vahIndex,
    vaLevels: vahIndex - valIndex + 1,
    prices: {
      lowestLow: lowestLow.toFixed(2),
      val: valPrice.toFixed(2),
      poc: pocPrice.toFixed(2),
      vah: vahPrice.toFixed(2),
      highestHigh: highestHigh.toFixed(2),
    },
    totalTPOs,
    vaTPOs,
    targetVA: Math.round(totalTPOs * (config.valueAreaPercent / 100)),
    vaPercentActual: vaPercentActual.toFixed(2) + '%',
    tickSize: tickSize.toFixed(2),
  })

  return {
    sessionIndex,
    startTime: candles[0].time as number,
    endTime: candles[candles.length - 1].time as number,
    startBarIndex: globalStartIndex,
    endBarIndex: globalStartIndex + candles.length - 1,

    levels: nonEmptyLevels,
    tickSize,
    tickSizeTicks: Math.round(tickSize / minTick),

    poc: pocPrice,
    pocIndex,
    vah: vahPrice,
    val: valPrice,
    vahIndex,
    valIndex,

    totalTPOs,
    highestHigh,
    lowestLow,
    openPrice,

    sessionName: `Session ${sessionIndex + 1}`,
    currentLetter,
  }
}

// ============================================================================
// FUNÇÃO AUXILIAR - Dividir candles por sessão de 24h baseada em horário
// ============================================================================

function divideCandlesByTimeSession(
  candles: CandlestickData[],
  sessionStartHour: number // 0-23 (UTC)
): { candles: CandlestickData[]; globalStartIndex: number }[] {
  if (candles.length === 0) return []

  const sessions: { candles: CandlestickData[]; globalStartIndex: number }[] = []
  let currentSessionCandles: CandlestickData[] = []
  let currentSessionStartIndex = 0

  for (let i = 0; i < candles.length; i++) {
    const candle = candles[i]
    const candleTime = candle.time as number
    const candleDate = new Date(candleTime * 1000)
    const candleHour = candleDate.getUTCHours()

    // Verificar se este candle inicia uma nova sessão
    // Nova sessão começa quando a hora == sessionStartHour E é o primeiro candle dessa hora
    // OU quando mudou de dia e já passou do horário de início
    const isNewSession = candleHour === sessionStartHour && (
      currentSessionCandles.length === 0 ||
      i === 0 ||
      new Date((candles[i - 1].time as number) * 1000).getUTCHours() !== sessionStartHour
    )

    if (isNewSession && currentSessionCandles.length > 0) {
      // Salvar sessão anterior
      sessions.push({
        candles: currentSessionCandles,
        globalStartIndex: currentSessionStartIndex
      })
      // Iniciar nova sessão
      currentSessionCandles = []
      currentSessionStartIndex = i
    }

    currentSessionCandles.push(candle)
  }

  // Adicionar última sessão (mesmo que incompleta)
  if (currentSessionCandles.length > 0) {
    sessions.push({
      candles: currentSessionCandles,
      globalStartIndex: currentSessionStartIndex
    })
  }

  return sessions
}

// ============================================================================
// FUNÇÃO PRINCIPAL - DIVIDE EM MÚLTIPLAS SESSÕES
// Suporta divisão por HORÁRIO (24h) ou por número de barras
// ============================================================================

export function calculateTPO(
  candles: CandlestickData[],
  config: Partial<TPOConfig> = {}
): TPOResult {
  const cfg: TPOConfig = { ...DEFAULT_TPO_CONFIG, ...config }

  if (candles.length < 2) {
    return { profiles: [], currentProfile: null, config: cfg }
  }

  const profiles: TPOProfile[] = []

  // Calcular tick size global
  const minTick = estimateMinTick(candles)
  const tickSize = cfg.autoTickSize
    ? calculateAutoTickSize(candles, cfg.tickBarsBack, cfg.targetSessionHeight, minTick)
    : cfg.manualTickSize * minTick

  if (tickSize <= 0) {
    return { profiles: [], currentProfile: null, config: cfg }
  }

  // =========================================================================
  // DIVIDIR CANDLES EM SESSÕES
  // Se use24hSession = true: divide por horário (21:00 UTC - 20:59 UTC)
  // Se use24hSession = false: divide por número de barras (sessionBars)
  // =========================================================================

  let sessionGroups: { candles: CandlestickData[]; globalStartIndex: number }[]

  if (cfg.use24hSession) {
    // MODO 24H: Dividir por horário de início da sessão
    sessionGroups = divideCandlesByTimeSession(candles, cfg.sessionStartHour)
    console.log(`📊 TPO: Modo 24h ativado (início às ${cfg.sessionStartHour}:00 UTC) - ${sessionGroups.length} sessões encontradas`)
  } else {
    // MODO BARRAS: Dividir por número de barras (comportamento antigo)
    const sessionBars = cfg.sessionBars
    const numSessions = Math.ceil(candles.length / sessionBars)
    sessionGroups = []

    for (let sessionIdx = 0; sessionIdx < numSessions; sessionIdx++) {
      const startIdx = sessionIdx * sessionBars
      const endIdx = Math.min(startIdx + sessionBars, candles.length)
      const sessionCandles = candles.slice(startIdx, endIdx)

      if (sessionCandles.length >= 2) {
        sessionGroups.push({
          candles: sessionCandles,
          globalStartIndex: startIdx
        })
      }
    }
    console.log(`📊 TPO: Modo barras ativado (${cfg.sessionBars} barras/sessão) - ${sessionGroups.length} sessões`)
  }

  // Processar cada sessão
  for (let sessionIdx = 0; sessionIdx < sessionGroups.length; sessionIdx++) {
    const { candles: sessionCandles, globalStartIndex } = sessionGroups[sessionIdx]

    if (sessionCandles.length < 2) continue

    const profile = calculateSingleSession(
      sessionCandles,
      sessionIdx,
      globalStartIndex,
      cfg,
      minTick,
      tickSize
    )

    if (profile) {
      profiles.push(profile)
    }
  }

  return {
    profiles,
    currentProfile: profiles.length > 0 ? profiles[profiles.length - 1] : null,
    config: cfg,
  }
}

// ============================================================================
// FUNÇÕES DE RENDERIZAÇÃO
// ============================================================================

export function generateRenderData(
  profile: TPOProfile,
  candles: CandlestickData[],
  _config: TPOConfig
): TPORenderData {
  return {
    profile,
    candles,
  }
}

export function getTPOColor(
  level: TPOLevel,
  tpoLetter: TPOLetter,
  config: TPOConfig
): string {
  if (tpoLetter.isOpen && tpoLetter.sessionBarIndex === 0) {
    return config.colors.open
  }
  if (level.isPOC) {
    return config.colors.poc
  }
  if (level.isInValueArea) {
    return config.colors.inValue
  }
  return config.colors.outOfValue
}

export function getBoxColor(
  level: TPOLevel,
  config: TPOConfig
): { color: string; transparency: number } {
  if (level.isPOC) {
    return { color: config.colors.pocBox, transparency: 0 }
  }
  if (level.isInValueArea) {
    return { color: config.colors.inValueBox, transparency: config.inValueBoxTransparency }
  }
  return { color: config.colors.outOfValueBox, transparency: config.outOfValueBoxTransparency }
}

export function getTPOBoxColor(
  level: { isPOC: boolean; isInValueArea: boolean },
  _periodIndex: number,
  config: TPOConfig
): string {
  if (level.isPOC) return config.colors.poc
  if (level.isInValueArea) return config.colors.inValue
  return config.colors.outOfValue
}

export function getBlockColor(letterIndex: number, totalLetters: number, colors: string[]): string {
  if (colors.length === 0) return '#00D4FF'
  const colorIndex = Math.floor((letterIndex / Math.max(totalLetters, 1)) * (colors.length - 1))
  return colors[Math.min(colorIndex, colors.length - 1)]
}

export default {
  calculate: calculateTPO,
  generateRenderData,
  getTPOColor,
  getBoxColor,
  DEFAULT_CONFIG: DEFAULT_TPO_CONFIG,
}
