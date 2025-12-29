/**
 * Strategy Service
 * Service for managing trading strategies (CRUD operations)
 */
import { apiClient } from '@/lib/api'

// ============================================================================
// Types & Interfaces
// ============================================================================

export interface Strategy {
  id: string
  name: string
  description: string | null
  config_type: 'visual' | 'yaml' | 'pinescript'
  symbols: string[]
  timeframe: string
  is_active: boolean
  is_backtesting: boolean
  bot_id: string | null
  created_by: string | null
  config_yaml: string | null
  pinescript_source: string | null
  created_at: string
  updated_at: string
}

export interface StrategyWithStats {
  strategy: Strategy
  signals_today: number
  total_executed: number
  indicators: string[]
}

export interface StrategyWithRelations extends Strategy {
  indicators: StrategyIndicator[]
  conditions: StrategyCondition[]
}

export interface StrategyIndicator {
  id: string
  strategy_id: string
  indicator_type: string
  parameters: Record<string, any>
  order_index: number
  created_at: string
}

export interface StrategyCondition {
  id: string
  strategy_id: string
  condition_type: string
  conditions: ConditionRule[]
  logic_operator: 'AND' | 'OR'
  order_index: number
  created_at: string
}

export interface ConditionRule {
  left: string
  operator: string
  right: string
}

export interface StrategySignal {
  id: string
  strategy_id: string
  symbol: string
  signal_type: string
  entry_price: number | null
  indicator_values: Record<string, any>
  status: 'pending' | 'executed' | 'failed'
  bot_signal_id: string | null
  created_at: string
}

export interface StrategyBacktestResult {
  id: string
  strategy_id: string
  start_date: string
  end_date: string
  symbol: string
  initial_capital: number
  leverage: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  profit_factor: number
  total_pnl: number
  total_pnl_percent: number
  max_drawdown: number
  sharpe_ratio: number
  created_at: string
}

export interface RunBacktestConfig {
  symbol: string
  start_date: string
  end_date: string
  initial_capital: number
  leverage: number
  margin_percent?: number
  stop_loss_percent?: number
  take_profit_percent?: number
  include_fees?: boolean
  include_slippage?: boolean
}

export interface BacktestTrade {
  entry_time: string
  exit_time: string | null
  signal_type: 'long' | 'short'
  entry_price: number
  exit_price: number | null
  quantity: number
  pnl: number | null
  pnl_percent: number | null
  exit_reason: string | null
}

export interface BacktestCandle {
  time: number  // Unix timestamp
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface BacktestIndicatorPoint {
  time: number  // Unix timestamp
  value: number
}

export interface BacktestIndicators {
  [key: string]: BacktestIndicatorPoint[]
}

export interface BacktestEquityPoint {
  timestamp: string
  equity: number
  price: number
}

export interface BacktestRunResult {
  id: string
  strategy_id: string
  symbol: string
  start_date: string
  end_date: string
  metrics: {
    total_trades: number
    winning_trades: number
    losing_trades: number
    win_rate: number | null
    profit_factor: number | null
    total_pnl: number | null
    total_pnl_percent: number | null
    max_drawdown: number | null
    sharpe_ratio: number | null
  }
  trades: BacktestTrade[]
  equity_curve: BacktestEquityPoint[]
  candles: BacktestCandle[]
  indicators: BacktestIndicators
}

export interface CreateStrategyData {
  name: string
  description?: string
  config_type?: 'visual' | 'yaml' | 'pinescript'
  symbols?: string[]
  timeframe?: string
  bot_id?: string
  config_yaml?: string
  pinescript_source?: string
}

export interface UpdateStrategyData {
  name?: string
  description?: string
  symbols?: string[]
  timeframe?: string
  bot_id?: string
  config_yaml?: string
  pinescript_source?: string
}

export interface AddIndicatorData {
  indicator_type: string
  parameters?: Record<string, any>
  order_index?: number
}

export interface AddConditionData {
  condition_type: string
  conditions: ConditionRule[]
  logic_operator?: 'AND' | 'OR'
  order_index?: number
}

// Available indicator types
export const INDICATOR_TYPES = [
  { value: 'nadaraya_watson', label: 'Nadaraya-Watson Envelope', params: { bandwidth: 8, mult: 3.0 } },
  { value: 'rsi', label: 'RSI (Relative Strength Index)', params: { period: 14, overbought: 70, oversold: 30 } },
  { value: 'macd', label: 'MACD', params: { fast: 12, slow: 26, signal: 9 } },
  { value: 'ema', label: 'EMA (Exponential Moving Average)', params: { period: 20 } },
  { value: 'bollinger', label: 'Bollinger Bands', params: { period: 20, std_dev: 2 } },
  { value: 'atr', label: 'ATR (Average True Range)', params: { period: 14 } },
  { value: 'volume_profile', label: 'Volume Profile', params: { lookback: 24 } },
]

// Available timeframes
export const TIMEFRAMES = [
  { value: '1m', label: '1 Minuto' },
  { value: '3m', label: '3 Minutos' },
  { value: '5m', label: '5 Minutos' },
  { value: '15m', label: '15 Minutos' },
  { value: '30m', label: '30 Minutos' },
  { value: '1h', label: '1 Hora' },
  { value: '2h', label: '2 Horas' },
  { value: '4h', label: '4 Horas' },
  { value: '6h', label: '6 Horas' },
  { value: '12h', label: '12 Horas' },
  { value: '1d', label: '1 Dia' },
]

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Parse JSON string fields from API response
 */
function parseStrategyFields(data: any): any {
  if (!data) return data

  // Parse symbols if it's a string
  if (typeof data.symbols === 'string') {
    try {
      data.symbols = JSON.parse(data.symbols)
    } catch {
      data.symbols = []
    }
  }

  // Parse indicator parameters if it's a string
  if (data.parameters && typeof data.parameters === 'string') {
    try {
      data.parameters = JSON.parse(data.parameters)
    } catch {
      data.parameters = {}
    }
  }

  // Parse conditions if it's a string
  if (data.conditions && typeof data.conditions === 'string') {
    try {
      data.conditions = JSON.parse(data.conditions)
    } catch {
      data.conditions = []
    }
  }

  return data
}

// ============================================================================
// Strategy Service Class
// ============================================================================

class StrategyService {
  /**
   * Get all strategies with statistics
   */
  async getStrategies(params?: {
    limit?: number
    offset?: number
    active_only?: boolean
  }): Promise<{ strategies: StrategyWithStats[]; total: number }> {
    const response = await apiClient.instance.get('/strategies', { params })

    if (response.data?.success && response.data?.data) {
      // API returns data with strategy nested inside each item
      const strategies = response.data.data.map((item: any) => {
        // Check if strategy is nested or flat
        const strategyData = item.strategy || item
        const strategyFields = {
          id: strategyData.id,
          name: strategyData.name,
          description: strategyData.description,
          config_type: strategyData.config_type,
          symbols: strategyData.symbols,
          timeframe: strategyData.timeframe,
          is_active: strategyData.is_active,
          is_backtesting: strategyData.is_backtesting,
          bot_id: strategyData.bot_id,
          created_by: strategyData.created_by,
          config_yaml: strategyData.config_yaml,
          pinescript_source: strategyData.pinescript_source,
          created_at: strategyData.created_at,
          updated_at: strategyData.updated_at,
          documentation: strategyData.documentation,
        }

        return {
          strategy: parseStrategyFields(strategyFields),
          signals_today: item.signals_today || 0,
          total_executed: item.total_executed || 0,
          indicators: item.indicators || [],
        }
      })
      return {
        strategies,
        total: response.data.total || strategies.length
      }
    }

    return { strategies: [], total: 0 }
  }

  /**
   * Get a strategy by ID with all relations
   */
  async getStrategy(strategyId: string): Promise<StrategyWithRelations | null> {
    const response = await apiClient.instance.get(`/strategies/${strategyId}`)

    if (response.data?.success && response.data?.data) {
      const data = response.data.data

      // Parse the strategy
      const strategy = parseStrategyFields(data)

      // Parse indicators
      if (strategy.indicators) {
        strategy.indicators = strategy.indicators.map((ind: any) => parseStrategyFields(ind))
      }

      // Parse conditions
      if (strategy.conditions) {
        strategy.conditions = strategy.conditions.map((cond: any) => parseStrategyFields(cond))
      }

      return strategy
    }

    return null
  }

  /**
   * Create a new strategy
   */
  async createStrategy(data: CreateStrategyData): Promise<Strategy> {
    const response = await apiClient.instance.post('/strategies', data)

    if (response.data?.success && response.data?.data) {
      return parseStrategyFields(response.data.data)
    }

    throw new Error(response.data?.message || 'Failed to create strategy')
  }

  /**
   * Update a strategy
   */
  async updateStrategy(strategyId: string, data: UpdateStrategyData): Promise<Strategy> {
    const response = await apiClient.instance.put(`/strategies/${strategyId}`, data)

    if (response.data?.success && response.data?.data) {
      return parseStrategyFields(response.data.data)
    }

    throw new Error(response.data?.message || 'Failed to update strategy')
  }

  /**
   * Delete a strategy
   */
  async deleteStrategy(strategyId: string): Promise<void> {
    const response = await apiClient.instance.delete(`/strategies/${strategyId}`)

    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to delete strategy')
    }
  }

  /**
   * Activate a strategy
   */
  async activateStrategy(strategyId: string): Promise<Strategy> {
    const response = await apiClient.instance.post(`/strategies/${strategyId}/activate`)

    if (response.data?.success && response.data?.data) {
      return parseStrategyFields(response.data.data)
    }

    throw new Error(response.data?.message || 'Failed to activate strategy')
  }

  /**
   * Deactivate a strategy
   */
  async deactivateStrategy(strategyId: string): Promise<Strategy> {
    const response = await apiClient.instance.post(`/strategies/${strategyId}/deactivate`)

    if (response.data?.success && response.data?.data) {
      return parseStrategyFields(response.data.data)
    }

    throw new Error(response.data?.message || 'Failed to deactivate strategy')
  }

  /**
   * Add an indicator to a strategy
   */
  async addIndicator(strategyId: string, data: AddIndicatorData): Promise<StrategyIndicator> {
    const response = await apiClient.instance.post(`/strategies/${strategyId}/indicators`, data)

    if (response.data?.success && response.data?.data) {
      return parseStrategyFields(response.data.data)
    }

    throw new Error(response.data?.message || 'Failed to add indicator')
  }

  /**
   * Remove an indicator
   */
  async removeIndicator(strategyId: string, indicatorId: string): Promise<void> {
    const response = await apiClient.instance.delete(`/strategies/${strategyId}/indicators/${indicatorId}`)

    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to remove indicator')
    }
  }

  /**
   * Add a condition to a strategy
   */
  async addCondition(strategyId: string, data: AddConditionData): Promise<StrategyCondition> {
    const response = await apiClient.instance.post(`/strategies/${strategyId}/conditions`, data)

    if (response.data?.success && response.data?.data) {
      return parseStrategyFields(response.data.data)
    }

    throw new Error(response.data?.message || 'Failed to add condition')
  }

  /**
   * Remove a condition
   */
  async removeCondition(strategyId: string, conditionId: string): Promise<void> {
    const response = await apiClient.instance.delete(`/strategies/${strategyId}/conditions/${conditionId}`)

    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to remove condition')
    }
  }

  /**
   * Get signals for a strategy
   */
  async getSignals(strategyId: string, params?: {
    limit?: number
    offset?: number
  }): Promise<StrategySignal[]> {
    const response = await apiClient.instance.get(`/strategies/${strategyId}/signals`, { params })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Run a backtest for a strategy
   */
  async runBacktest(strategyId: string, config: RunBacktestConfig): Promise<BacktestRunResult> {
    const response = await apiClient.instance.post(`/strategies/${strategyId}/backtest`, {
      symbol: config.symbol,
      start_date: config.start_date,
      end_date: config.end_date,
      initial_capital: config.initial_capital,
      leverage: config.leverage,
      margin_percent: config.margin_percent ?? 5.0,
      stop_loss_percent: config.stop_loss_percent ?? 2.0,
      take_profit_percent: config.take_profit_percent ?? 4.0,
      include_fees: config.include_fees ?? true,
      include_slippage: config.include_slippage ?? true,
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    throw new Error(response.data?.message || 'Failed to run backtest')
  }

  /**
   * Get backtest results for a strategy
   */
  async getBacktestResults(strategyId: string): Promise<StrategyBacktestResult[]> {
    const response = await apiClient.instance.get(`/strategies/${strategyId}/backtest/results`)

    if (response.data?.success && response.data?.data) {
      return response.data.data
    }

    return []
  }

  /**
   * Apply YAML configuration to a strategy
   */
  async applyYamlConfig(strategyId: string, yamlContent: string): Promise<StrategyWithRelations> {
    const response = await apiClient.instance.post(`/strategies/${strategyId}/yaml`, {
      yaml_content: yamlContent
    })

    if (response.data?.success && response.data?.data) {
      return parseStrategyFields(response.data.data)
    }

    throw new Error(response.data?.message || 'Failed to apply YAML config')
  }

  /**
   * Generate YAML template
   */
  async generateYamlTemplate(indicators?: string[], symbols?: string[]): Promise<string> {
    const response = await apiClient.instance.get('/strategies/yaml-template', {
      params: { indicators, symbols }
    })

    if (response.data?.success && response.data?.data) {
      return response.data.data.template
    }

    throw new Error('Failed to generate YAML template')
  }
}

export const strategyService = new StrategyService()
