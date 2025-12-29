# Plano de Desenvolvimento: Indicadores e Melhorias do Sistema de Estrategias

> Data: 2025-12-26
> Gerado pelo Agente: crypto-trading-analyst

---

## 1. RESUMO EXECUTIVO

Este documento detalha os gaps identificados no sistema de estrategias do GlobalAutomation e apresenta um plano de desenvolvimento para implementar indicadores faltantes e melhorias no sistema de backtesting.

---

## 2. ESTADO ATUAL DO SISTEMA

### 2.1 Indicadores Implementados

| Indicador | Backend | Frontend | Notas |
|-----------|---------|----------|-------|
| Nadaraya-Watson Envelope | OK | OK | Implementacao propria |
| TPO / Market Profile | OK | OK | Implementacao propria |
| RSI | OK (inline) | OK | Via strategy_engine_service |
| MACD | OK (inline) | OK | Via strategy_engine_service |
| Bollinger Bands | OK (inline) | OK | Via strategy_engine_service |
| EMA / EMA Cross | OK (inline) | OK | Via strategy_engine_service |
| ATR | Parcial | OK | Definido no schema, calculo inline |
| SMA | - | OK | Apenas frontend |
| WMA | - | OK | Apenas frontend |
| Stochastic | - | OK | Apenas frontend |
| Stochastic RSI | - | OK | Apenas frontend |
| ADX | - | OK | Apenas frontend |
| VWAP | - | OK | Apenas frontend |
| Ichimoku Cloud | - | OK | Apenas frontend |
| Volume Profile | Planejado | OK | Apenas frontend |

### 2.2 Funcionalidades de Backtesting

| Funcionalidade | Status | Notas |
|----------------|--------|-------|
| Stop Loss Fixo | OK | Implementado |
| Take Profit Fixo | OK | Implementado |
| Fees e Slippage | OK | Configuravel |
| Win Rate | OK | Calculado |
| Sharpe Ratio | OK | Calculado |
| Max Drawdown | OK | Calculado |
| Profit Factor | OK | Calculado |
| Trailing Stop | FALTA | Critico para estrategias de tendencia |
| Partial Take Profit | FALTA | Importante para gestao de risco |
| Position Sizing Dinamico | FALTA | Baseado em ATR ou volatilidade |
| Sortino Ratio | FALTA | Melhor que Sharpe para risco downside |

---

## 3. GAPS IDENTIFICADOS

### 3.1 Indicadores Faltantes no Backend (Prioridade ALTA)

Estes indicadores existem no frontend mas NAO estao implementados no backend para uso em estrategias automatizadas:

| Indicador | Prioridade | Complexidade | Uso |
|-----------|------------|--------------|-----|
| **Stochastic RSI** | CRITICA | Media | Estrategias de reversao |
| **Stochastic** | ALTA | Baixa | Base para StochRSI |
| **ADX** | ALTA | Media | Filtro de forca de tendencia |
| **SuperTrend** | ALTA | Baixa | Trend following |
| **VWAP** | MEDIA | Media | Confirmacao intraday |
| **Ichimoku Cloud** | MEDIA | Alta | Suporte/Resistencia dinamico |

### 3.2 Funcionalidades de Gestao de Risco Faltantes

| Funcionalidade | Prioridade | Impacto |
|----------------|------------|---------|
| **Trailing Stop Loss** | CRITICA | Maximiza lucros em tendencias |
| **Break-Even Automatico** | ALTA | Protege capital |
| **Partial Take Profit** | ALTA | Gestao de risco gradual |
| **Max Daily Loss** | CRITICA | Protecao contra sequencias negativas |
| **Position Sizing ATR** | ALTA | Ajusta tamanho ao risco |

### 3.3 Metricas de Backtesting Faltantes

| Metrica | Prioridade | Formula |
|---------|------------|---------|
| **Sortino Ratio** | MEDIA | (Return - RFR) / Downside Deviation |
| **Calmar Ratio** | BAIXA | CAGR / Max Drawdown |
| **Payoff Ratio** | MEDIA | Avg Win / Avg Loss |
| **Expectancy** | MEDIA | (WR x AvgWin) - (LR x AvgLoss) |
| **Recovery Factor** | BAIXA | Net Profit / Max Drawdown |

---

## 4. PLANO DE IMPLEMENTACAO

### Fase 1: Indicadores Criticos (Semana 1-2)

#### 4.1.1 Stochastic Oscillator

**Arquivo:** `apps/api-python/infrastructure/indicators/stochastic.py`

```python
"""
Stochastic Oscillator Implementation

Formula:
%K = (Close - Lowest Low) / (Highest High - Lowest Low) x 100
%D = SMA(%K, d_period)

Parametros:
- k_period: Periodo do %K (default: 14)
- d_period: Periodo do %D (default: 3)
- smooth: Suavizacao (default: 3)
"""

from decimal import Decimal
from typing import List
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class StochasticCalculator(BaseIndicatorCalculator):
    name = "stochastic"
    required_candles = 50

    def __init__(self, parameters: dict = None):
        super().__init__(parameters)
        self.k_period = self.parameters.get("k_period", 14)
        self.d_period = self.parameters.get("d_period", 3)
        self.smooth = self.parameters.get("smooth", 3)
        self.overbought = self.parameters.get("overbought", 80)
        self.oversold = self.parameters.get("oversold", 20)

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles")

        highs = np.array([float(c.high) for c in candles])
        lows = np.array([float(c.low) for c in candles])
        closes = np.array([float(c.close) for c in candles])

        # Calculate %K
        k_values = []
        for i in range(self.k_period - 1, len(closes)):
            highest = np.max(highs[i - self.k_period + 1:i + 1])
            lowest = np.min(lows[i - self.k_period + 1:i + 1])

            if highest - lowest > 0:
                k = ((closes[i] - lowest) / (highest - lowest)) * 100
            else:
                k = 50  # Neutral
            k_values.append(k)

        # Smooth %K
        k_smooth = self._sma(k_values, self.smooth)

        # Calculate %D (SMA of smoothed %K)
        d_values = self._sma(k_smooth, self.d_period)

        # Get latest values
        k = k_smooth[-1] if k_smooth else 50
        d = d_values[-1] if d_values else 50

        # Generate signal
        signal = 0
        if k < self.oversold and k > d:  # Oversold + bullish cross
            signal = 1  # Buy
        elif k > self.overbought and k < d:  # Overbought + bearish cross
            signal = -1  # Sell

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "k": Decimal(str(round(k, 2))),
                "d": Decimal(str(round(d, 2))),
                "signal": Decimal(str(signal)),
            }
        )

    def _sma(self, data: List[float], period: int) -> List[float]:
        result = []
        for i in range(period - 1, len(data)):
            result.append(np.mean(data[i - period + 1:i + 1]))
        return result
```

#### 4.1.2 Stochastic RSI

**Arquivo:** `apps/api-python/infrastructure/indicators/stochastic_rsi.py`

```python
"""
Stochastic RSI Implementation

Formula:
1. Calculate RSI
2. Apply Stochastic formula to RSI values
   StochRSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI)

Parametros:
- rsi_period: Periodo do RSI (default: 14)
- stoch_period: Periodo do Stochastic (default: 14)
- k_period: Suavizacao %K (default: 3)
- d_period: Suavizacao %D (default: 3)
"""

from decimal import Decimal
from typing import List
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class StochasticRSICalculator(BaseIndicatorCalculator):
    name = "stochastic_rsi"
    required_candles = 100

    def __init__(self, parameters: dict = None):
        super().__init__(parameters)
        self.rsi_period = self.parameters.get("rsi_period", 14)
        self.stoch_period = self.parameters.get("stoch_period", 14)
        self.k_period = self.parameters.get("k_period", 3)
        self.d_period = self.parameters.get("d_period", 3)
        self.overbought = self.parameters.get("overbought", 80)
        self.oversold = self.parameters.get("oversold", 20)

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles")

        closes = np.array([float(c.close) for c in candles])

        # Step 1: Calculate RSI
        rsi_values = self._calculate_rsi(closes)

        # Step 2: Apply Stochastic to RSI
        stoch_rsi = []
        for i in range(self.stoch_period - 1, len(rsi_values)):
            window = rsi_values[i - self.stoch_period + 1:i + 1]
            min_rsi = np.min(window)
            max_rsi = np.max(window)

            if max_rsi - min_rsi > 0:
                sr = ((rsi_values[i] - min_rsi) / (max_rsi - min_rsi)) * 100
            else:
                sr = 50
            stoch_rsi.append(sr)

        # Step 3: Smooth %K
        k_values = self._sma(stoch_rsi, self.k_period)

        # Step 4: Calculate %D
        d_values = self._sma(k_values, self.d_period)

        # Get latest values
        k = k_values[-1] if k_values else 50
        d = d_values[-1] if d_values else 50
        prev_k = k_values[-2] if len(k_values) > 1 else k
        prev_d = d_values[-2] if len(d_values) > 1 else d

        # Generate signal
        signal = 0
        # Bullish cross from oversold
        if prev_k < prev_d and k > d and k < self.oversold + 10:
            signal = 1
        # Bearish cross from overbought
        elif prev_k > prev_d and k < d and k > self.overbought - 10:
            signal = -1

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "k": Decimal(str(round(k, 2))),
                "d": Decimal(str(round(d, 2))),
                "signal": Decimal(str(signal)),
            }
        )

    def _calculate_rsi(self, closes: np.ndarray) -> List[float]:
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(deltas))
        avg_loss = np.zeros(len(deltas))

        # Initial SMA
        avg_gain[self.rsi_period - 1] = np.mean(gains[:self.rsi_period])
        avg_loss[self.rsi_period - 1] = np.mean(losses[:self.rsi_period])

        # EMA style calculation
        for i in range(self.rsi_period, len(deltas)):
            avg_gain[i] = (avg_gain[i-1] * (self.rsi_period - 1) + gains[i]) / self.rsi_period
            avg_loss[i] = (avg_loss[i-1] * (self.rsi_period - 1) + losses[i]) / self.rsi_period

        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi = 100 - (100 / (1 + rs))

        return list(rsi[self.rsi_period - 1:])

    def _sma(self, data: List[float], period: int) -> List[float]:
        result = []
        for i in range(period - 1, len(data)):
            result.append(np.mean(data[i - period + 1:i + 1]))
        return result
```

#### 4.1.3 SuperTrend

**Arquivo:** `apps/api-python/infrastructure/indicators/supertrend.py`

```python
"""
SuperTrend Indicator Implementation

Formula:
Upper Band = (High + Low) / 2 + Multiplier x ATR
Lower Band = (High + Low) / 2 - Multiplier x ATR

Trend:
- Bullish when price closes above upper band
- Bearish when price closes below lower band

Parametros:
- period: ATR period (default: 10)
- multiplier: ATR multiplier (default: 3.0)
"""

from decimal import Decimal
from typing import List
import numpy as np

from .base import BaseIndicatorCalculator, Candle, IndicatorResult


class SuperTrendCalculator(BaseIndicatorCalculator):
    name = "supertrend"
    required_candles = 50

    def __init__(self, parameters: dict = None):
        super().__init__(parameters)
        self.period = self.parameters.get("period", 10)
        self.multiplier = self.parameters.get("multiplier", 3.0)

    def calculate(self, candles: List[Candle]) -> IndicatorResult:
        if len(candles) < self.required_candles:
            raise ValueError(f"Need at least {self.required_candles} candles")

        highs = np.array([float(c.high) for c in candles])
        lows = np.array([float(c.low) for c in candles])
        closes = np.array([float(c.close) for c in candles])

        # Calculate ATR
        atr = self._calculate_atr(highs, lows, closes)

        # Calculate basic bands
        hl2 = (highs + lows) / 2
        upper_basic = hl2 + (self.multiplier * atr)
        lower_basic = hl2 - (self.multiplier * atr)

        # Calculate final bands with trend logic
        upper_band = np.zeros(len(closes))
        lower_band = np.zeros(len(closes))
        supertrend = np.zeros(len(closes))
        trend = np.zeros(len(closes))  # 1 = bullish, -1 = bearish

        upper_band[0] = upper_basic[0]
        lower_band[0] = lower_basic[0]
        trend[0] = 1

        for i in range(1, len(closes)):
            # Upper band
            if upper_basic[i] < upper_band[i-1] or closes[i-1] > upper_band[i-1]:
                upper_band[i] = upper_basic[i]
            else:
                upper_band[i] = upper_band[i-1]

            # Lower band
            if lower_basic[i] > lower_band[i-1] or closes[i-1] < lower_band[i-1]:
                lower_band[i] = lower_basic[i]
            else:
                lower_band[i] = lower_band[i-1]

            # Trend direction
            if trend[i-1] == 1:
                if closes[i] < lower_band[i]:
                    trend[i] = -1
                    supertrend[i] = upper_band[i]
                else:
                    trend[i] = 1
                    supertrend[i] = lower_band[i]
            else:
                if closes[i] > upper_band[i]:
                    trend[i] = 1
                    supertrend[i] = lower_band[i]
                else:
                    trend[i] = -1
                    supertrend[i] = upper_band[i]

        # Generate signal (trend change)
        signal = 0
        if len(trend) > 1:
            if trend[-2] == -1 and trend[-1] == 1:
                signal = 1  # Bullish reversal
            elif trend[-2] == 1 and trend[-1] == -1:
                signal = -1  # Bearish reversal

        return IndicatorResult(
            name=self.name,
            timestamp=candles[-1].timestamp,
            values={
                "value": Decimal(str(round(supertrend[-1], 8))),
                "trend": Decimal(str(int(trend[-1]))),
                "upper": Decimal(str(round(upper_band[-1], 8))),
                "lower": Decimal(str(round(lower_band[-1], 8))),
                "signal": Decimal(str(signal)),
            }
        )

    def _calculate_atr(self, highs, lows, closes) -> np.ndarray:
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]

        for i in range(1, len(closes)):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )

        atr = np.zeros(len(closes))
        atr[self.period - 1] = np.mean(tr[:self.period])

        for i in range(self.period, len(closes)):
            atr[i] = (atr[i-1] * (self.period - 1) + tr[i]) / self.period

        return atr
```

### Fase 2: Gestao de Risco Avancada (Semana 2-3)

#### 4.2.1 Trailing Stop Loss

Adicionar ao `backtest_service.py`:

```python
@dataclass
class BacktestConfig:
    # ... existing fields ...

    # Trailing Stop
    use_trailing_stop: bool = False
    trailing_stop_trigger_percent: Decimal = Decimal("1.0")  # Trigger after +1%
    trailing_stop_distance_percent: Decimal = Decimal("0.8")  # Trail by 0.8%

    # Break-even
    use_break_even: bool = False
    break_even_trigger_percent: Decimal = Decimal("0.5")  # Move to BE after +0.5%

    # Partial TP
    use_partial_tp: bool = False
    partial_tp_percent: Decimal = Decimal("50")  # Close 50% at TP1
    partial_tp_1_percent: Decimal = Decimal("2.0")  # TP1 at +2%
    partial_tp_2_percent: Decimal = Decimal("4.0")  # TP2 at +4%


@dataclass
class BacktestState:
    # ... existing fields ...

    # Trailing stop tracking
    trailing_stop_active: bool = False
    trailing_stop_price: Decimal = Decimal("0")
    highest_price_since_entry: Decimal = Decimal("0")
    lowest_price_since_entry: Decimal = Decimal("0")

    # Partial close tracking
    partial_closed: bool = False
    remaining_size: Decimal = Decimal("0")
```

#### 4.2.2 Metricas Adicionais

Adicionar ao `_calculate_metrics`:

```python
def _calculate_extended_metrics(
    self,
    state: BacktestState,
    config: BacktestConfig,
) -> Dict[str, Any]:
    metrics = self._calculate_metrics(state, config)
    trades = state.trades

    if not trades:
        return metrics

    # Payoff Ratio (Avg Win / Avg Loss)
    winning_pnls = [float(t.pnl) for t in trades if t.pnl and t.pnl > 0]
    losing_pnls = [abs(float(t.pnl)) for t in trades if t.pnl and t.pnl < 0]

    avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
    avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 1
    payoff_ratio = avg_win / avg_loss if avg_loss > 0 else 0

    # Expectancy
    win_rate = float(metrics["win_rate"]) / 100 if metrics["win_rate"] else 0
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    # Sortino Ratio (downside deviation only)
    returns = [float(t.pnl_percent) for t in trades if t.pnl_percent]
    negative_returns = [r for r in returns if r < 0]

    if negative_returns and len(negative_returns) > 1:
        downside_variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
        downside_dev = downside_variance ** 0.5
        avg_return = sum(returns) / len(returns)
        sortino = (avg_return / downside_dev) * (252 ** 0.5) if downside_dev > 0 else 0
    else:
        sortino = 0

    # Consecutive wins/losses
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    current_wins = 0
    current_losses = 0

    for t in trades:
        if t.pnl and t.pnl > 0:
            current_wins += 1
            current_losses = 0
            max_consecutive_wins = max(max_consecutive_wins, current_wins)
        elif t.pnl and t.pnl < 0:
            current_losses += 1
            current_wins = 0
            max_consecutive_losses = max(max_consecutive_losses, current_losses)

    metrics.update({
        "payoff_ratio": Decimal(str(round(payoff_ratio, 4))),
        "expectancy": Decimal(str(round(expectancy, 2))),
        "sortino_ratio": Decimal(str(round(sortino, 4))),
        "avg_win": Decimal(str(round(avg_win, 2))),
        "avg_loss": Decimal(str(round(avg_loss, 2))),
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses,
    })

    return metrics
```

### Fase 3: Atualizar Enum e Registry (Semana 1)

#### 4.3.1 Atualizar IndicatorType

**Arquivo:** `apps/api-python/infrastructure/database/models/strategy.py`

```python
class IndicatorType(str, Enum):
    """Supported indicator types"""
    # Existentes
    NADARAYA_WATSON = "nadaraya_watson"
    TPO = "tpo"
    RSI = "rsi"
    MACD = "macd"
    EMA = "ema"
    BOLLINGER = "bollinger"
    ATR = "atr"
    VOLUME_PROFILE = "volume_profile"

    # Novos - Fase 1
    STOCHASTIC = "stochastic"
    STOCHASTIC_RSI = "stochastic_rsi"
    SUPERTREND = "supertrend"

    # Novos - Fase 2
    ADX = "adx"
    VWAP = "vwap"
    ICHIMOKU = "ichimoku"
```

#### 4.3.2 Atualizar Registry

**Arquivo:** `apps/api-python/infrastructure/services/backtest_service.py`

```python
from infrastructure.indicators import (
    # Existentes
    NadarayaWatsonCalculator,
    TPOCalculator,
    # Novos
    StochasticCalculator,
    StochasticRSICalculator,
    SuperTrendCalculator,
)

class BacktestService:
    INDICATOR_CALCULATORS = {
        # Existentes
        IndicatorType.NADARAYA_WATSON: NadarayaWatsonCalculator,
        IndicatorType.TPO: TPOCalculator,
        # Novos
        IndicatorType.STOCHASTIC: StochasticCalculator,
        IndicatorType.STOCHASTIC_RSI: StochasticRSICalculator,
        IndicatorType.SUPERTREND: SuperTrendCalculator,
    }
```

---

## 5. CRONOGRAMA SUGERIDO

| Fase | Tarefa | Duracao | Prioridade |
|------|--------|---------|------------|
| 1.1 | Implementar Stochastic | 2-3 horas | ALTA |
| 1.2 | Implementar Stochastic RSI | 3-4 horas | CRITICA |
| 1.3 | Implementar SuperTrend | 2-3 horas | ALTA |
| 1.4 | Atualizar Enum e Registry | 1 hora | ALTA |
| 1.5 | Testes unitarios indicadores | 4 horas | ALTA |
| 2.1 | Trailing Stop Loss | 3-4 horas | CRITICA |
| 2.2 | Partial Take Profit | 2-3 horas | ALTA |
| 2.3 | Break-even automatico | 2 horas | MEDIA |
| 2.4 | Metricas adicionais | 2-3 horas | MEDIA |
| 3.1 | Implementar ADX | 3 horas | MEDIA |
| 3.2 | Implementar VWAP | 3 horas | MEDIA |
| 3.3 | Implementar Ichimoku | 5 horas | BAIXA |

**Tempo Total Estimado:** 30-40 horas de desenvolvimento

---

## 6. ARQUIVOS A CRIAR/MODIFICAR

### Criar:
- `apps/api-python/infrastructure/indicators/stochastic.py`
- `apps/api-python/infrastructure/indicators/stochastic_rsi.py`
- `apps/api-python/infrastructure/indicators/supertrend.py`
- `apps/api-python/infrastructure/indicators/adx.py`
- `apps/api-python/infrastructure/indicators/vwap.py`
- `apps/api-python/tests/unit/test_indicators.py`

### Modificar:
- `apps/api-python/infrastructure/database/models/strategy.py` (IndicatorType enum)
- `apps/api-python/infrastructure/indicators/__init__.py` (exports)
- `apps/api-python/infrastructure/services/backtest_service.py` (registry + trailing stop)
- `apps/api-python/infrastructure/services/indicator_alert_monitor.py` (novos indicadores)

---

## 7. FONTES E REFERENCIAS

1. [QuantifiedStrategies - MACD and Bollinger Bands Strategy (78% Win Rate)](https://www.quantifiedstrategies.com/macd-and-bollinger-bands-strategy/)
2. [QuantifiedStrategies - Stochastic RSI (78% Win Rate)](https://www.quantifiedstrategies.com/stochastic-rsi/)
3. [QuantifiedStrategies - MACD and RSI Strategy (73% Win Rate)](https://www.quantifiedstrategies.com/macd-and-rsi-strategy/)
4. [QuantifiedStrategies - SuperTrend Indicator Strategy](https://www.quantifiedstrategies.com/supertrend-indicator-trading-strategy/)
5. [LuxAlgo - SuperTrend Indicator Guide](https://www.luxalgo.com/blog/how-to-use-the-supertrend-indicator-effectively/)
6. [WunderTrading - Crypto Bots with Technical Indicators](https://wundertrading.com/journal/en/learn/article/integrating-crypto-bots-with-technical-indicators)
7. [CoinBureau - How to Backtest Crypto Trading Strategy 2025](https://coinbureau.com/guides/how-to-backtest-your-crypto-trading-strategy/)

---

## 8. CONCLUSAO

O sistema GlobalAutomation possui uma base solida com indicadores avancados (Nadaraya-Watson, TPO) e arquitetura bem estruturada. Os gaps identificados sao principalmente:

1. **Indicadores de momentum** (Stochastic RSI) para estrategias de reversao
2. **Gestao de risco avancada** (Trailing Stop, Partial TP) para maximizar lucros
3. **Metricas adicionais** para avaliacao mais completa de estrategias

A implementacao deste plano permitira:
- Usar as 3 estrategias pre-configuradas de alta performance
- Criar estrategias mais sofisticadas
- Melhorar a gestao de risco dos bots
- Avaliar estrategias com metricas mais completas

**Proximos passos recomendados:**
1. Implementar Stochastic RSI (critico para Estrategia 2)
2. Implementar Trailing Stop (critico para todas as estrategias)
3. Executar backtests das 3 estrategias
4. Ajustar parametros baseado nos resultados
