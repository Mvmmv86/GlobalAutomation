"""
Backtest da Estrategia Trend Filter (SuperTrend+ADX)
- SuperTrend (period=10, multiplier=3.5)
- ADX (period=14, trend_threshold=25)

Condicoes:
- LONG: supertrend.trend == 1 AND adx > 25 AND +DI > -DI
- SHORT: supertrend.trend == -1 AND adx > 25 AND -DI > +DI
- EXIT: SuperTrend inverte (stop dinamico)
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Configuracoes da estrategia
STRATEGY_CONFIG = {
    "supertrend": {"period": 10, "multiplier": 3.5},
    "adx": {"period": 14, "trend_threshold": 25}
}

# Configuracoes de trading
TRADING_CONFIG = {
    "stop_loss_pct": 2.0,  # Stop loss fixo (backup)
    "take_profit_pct": 6.0,  # Take profit fixo (backup)
    "leverage": 10,
    "margin_usd": 10,
    "use_supertrend_exit": True  # Usar SuperTrend como stop dinamico
}

# ==================== INDICADORES ====================

def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate Average True Range using Wilder's smoothing"""
    n = len(closes)
    tr = np.zeros(n)

    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )

    atr = np.zeros(n)
    if period <= n:
        atr[period - 1] = np.mean(tr[:period])

    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

    return atr

def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate SuperTrend indicator
    Returns: (supertrend_values, trend_direction)
    - trend: 1 = bullish, -1 = bearish
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values

    atr = calculate_atr(highs, lows, closes, period)

    hl2 = (highs + lows) / 2
    upper_basic = hl2 + (multiplier * atr)
    lower_basic = hl2 - (multiplier * atr)

    n = len(closes)
    upper_band = np.zeros(n)
    lower_band = np.zeros(n)
    supertrend = np.zeros(n)
    trend = np.zeros(n)

    upper_band[0] = upper_basic[0]
    lower_band[0] = lower_basic[0]
    trend[0] = 1

    for i in range(1, n):
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
        if trend[i-1] == 1:  # Was bullish
            if closes[i] < lower_band[i]:
                trend[i] = -1
                supertrend[i] = upper_band[i]
            else:
                trend[i] = 1
                supertrend[i] = lower_band[i]
        else:  # Was bearish
            if closes[i] > upper_band[i]:
                trend[i] = 1
                supertrend[i] = lower_band[i]
            else:
                trend[i] = -1
                supertrend[i] = upper_band[i]

    return supertrend, trend

def wilder_smooth(data: np.ndarray, period: int) -> np.ndarray:
    """Apply Wilder's smoothing method"""
    result = np.zeros(len(data))

    if period <= len(data):
        result[period - 1] = np.mean(data[:period])

    for i in range(period, len(data)):
        result[i] = result[i-1] + (data[i] - result[i-1]) / period

    return result

def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate ADX, +DI, and -DI
    Returns: (adx, plus_di, minus_di)
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values

    n = len(closes)

    # True Range
    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )

    # Directional Movement
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move

        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move

    # Smooth TR, +DM, -DM
    smoothed_tr = wilder_smooth(tr, period)
    smoothed_plus_dm = wilder_smooth(plus_dm, period)
    smoothed_minus_dm = wilder_smooth(minus_dm, period)

    # Calculate +DI and -DI
    plus_di = np.zeros(n)
    minus_di = np.zeros(n)

    for i in range(n):
        if smoothed_tr[i] > 0:
            plus_di[i] = (smoothed_plus_dm[i] / smoothed_tr[i]) * 100
            minus_di[i] = (smoothed_minus_dm[i] / smoothed_tr[i]) * 100

    # Calculate DX
    dx = np.zeros(n)
    for i in range(n):
        di_sum = plus_di[i] + minus_di[i]
        if di_sum > 0:
            dx[i] = abs(plus_di[i] - minus_di[i]) / di_sum * 100

    # Calculate ADX
    adx = wilder_smooth(dx, period)

    return adx, plus_di, minus_di

# ==================== FETCH DATA ====================

async def fetch_klines(symbol: str, interval: str, start_ts: int, end_ts: int) -> List:
    """Fetch klines from Binance Futures API"""
    url = 'https://fapi.binance.com/fapi/v1/klines'
    all_klines = []
    current_start = start_ts

    async with aiohttp.ClientSession() as session:
        while current_start < end_ts:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_start,
                'endTime': end_ts,
                'limit': 1500
            }

            try:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"API Error: {response.status}")
                        break

                    data = await response.json()
                    if not data:
                        break

                    all_klines.extend(data)
                    current_start = data[-1][0] + 1
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"Fetch error: {e}")
                break

    return all_klines

def klines_to_dataframe(klines: List) -> pd.DataFrame:
    """Convert klines to DataFrame"""
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    df.set_index('timestamp', inplace=True)
    return df

# ==================== BACKTEST ENGINE ====================

class TrendFilterBacktestEngine:
    def __init__(self, df: pd.DataFrame, config: Dict):
        self.df = df.copy()
        self.config = config
        self.trades = []
        self.current_position = None

    def calculate_indicators(self):
        """Calculate all indicators"""
        print("  Calculando SuperTrend...")
        st_values, st_trend = calculate_supertrend(
            self.df,
            period=STRATEGY_CONFIG['supertrend']['period'],
            multiplier=STRATEGY_CONFIG['supertrend']['multiplier']
        )
        self.df['supertrend'] = st_values
        self.df['st_trend'] = st_trend

        print("  Calculando ADX...")
        adx, plus_di, minus_di = calculate_adx(
            self.df,
            period=STRATEGY_CONFIG['adx']['period']
        )
        self.df['adx'] = adx
        self.df['plus_di'] = plus_di
        self.df['minus_di'] = minus_di

    def check_entry_long(self, row, prev_row) -> bool:
        """Check LONG entry conditions"""
        if pd.isna(row['adx']) or pd.isna(row['st_trend']):
            return False

        # SuperTrend bullish
        cond1 = row['st_trend'] == 1
        # ADX > threshold (strong trend)
        cond2 = row['adx'] > STRATEGY_CONFIG['adx']['trend_threshold']
        # +DI > -DI (bullish direction)
        cond3 = row['plus_di'] > row['minus_di']
        # Trend just changed (signal)
        cond4 = prev_row['st_trend'] == -1 and row['st_trend'] == 1

        return cond1 and cond2 and cond3 and cond4

    def check_entry_short(self, row, prev_row) -> bool:
        """Check SHORT entry conditions"""
        if pd.isna(row['adx']) or pd.isna(row['st_trend']):
            return False

        # SuperTrend bearish
        cond1 = row['st_trend'] == -1
        # ADX > threshold (strong trend)
        cond2 = row['adx'] > STRATEGY_CONFIG['adx']['trend_threshold']
        # -DI > +DI (bearish direction)
        cond3 = row['minus_di'] > row['plus_di']
        # Trend just changed (signal)
        cond4 = prev_row['st_trend'] == 1 and row['st_trend'] == -1

        return cond1 and cond2 and cond3 and cond4

    def check_exit(self, row, position) -> Tuple[bool, str, float]:
        """
        Check exit conditions
        Returns: (should_exit, reason, exit_price)
        """
        high = row['high']
        low = row['low']
        close = row['close']

        # SuperTrend exit (dynamic stop)
        if TRADING_CONFIG['use_supertrend_exit']:
            if position['side'] == 'LONG' and row['st_trend'] == -1:
                return True, 'ST_EXIT', close
            elif position['side'] == 'SHORT' and row['st_trend'] == 1:
                return True, 'ST_EXIT', close

        # Fixed SL/TP as backup
        sl_pct = TRADING_CONFIG['stop_loss_pct'] / 100
        tp_pct = TRADING_CONFIG['take_profit_pct'] / 100

        if position['side'] == 'LONG':
            sl_price = position['entry_price'] * (1 - sl_pct)
            tp_price = position['entry_price'] * (1 + tp_pct)

            if low <= sl_price:
                return True, 'SL', sl_price
            elif high >= tp_price:
                return True, 'TP', tp_price
        else:  # SHORT
            sl_price = position['entry_price'] * (1 + sl_pct)
            tp_price = position['entry_price'] * (1 - tp_pct)

            if high >= sl_price:
                return True, 'SL', sl_price
            elif low <= tp_price:
                return True, 'TP', tp_price

        return False, '', 0

    def run_backtest(self):
        """Execute backtest"""
        self.calculate_indicators()

        # Remove NaN
        self.df = self.df.dropna()

        print(f"  Executando backtest com {len(self.df)} candles...")

        df_list = list(self.df.iterrows())

        for i in range(1, len(df_list)):
            idx, row = df_list[i]
            prev_idx, prev_row = df_list[i-1]

            # Check exit if in position
            if self.current_position:
                should_exit, reason, exit_price = self.check_exit(row, self.current_position)
                if should_exit:
                    self._close_position(idx, exit_price, reason)

            # Check entry if not in position
            if not self.current_position:
                if self.check_entry_long(row, prev_row):
                    self._open_position('LONG', idx, row['close'], row['supertrend'])
                elif self.check_entry_short(row, prev_row):
                    self._open_position('SHORT', idx, row['close'], row['supertrend'])

        # Close any open position at end
        if self.current_position:
            last_row = self.df.iloc[-1]
            self._close_position(self.df.index[-1], last_row['close'], 'END')

    def _open_position(self, side: str, timestamp, price: float, supertrend: float):
        """Open a position"""
        self.current_position = {
            'side': side,
            'entry_time': timestamp,
            'entry_price': price,
            'supertrend_at_entry': supertrend
        }

    def _close_position(self, timestamp, price: float, reason: str):
        """Close position and record trade"""
        pos = self.current_position

        if pos['side'] == 'LONG':
            pnl_pct = ((price - pos['entry_price']) / pos['entry_price']) * 100
        else:
            pnl_pct = ((pos['entry_price'] - price) / pos['entry_price']) * 100

        pnl_pct_leveraged = pnl_pct * TRADING_CONFIG['leverage']
        pnl_usd = (pnl_pct_leveraged / 100) * TRADING_CONFIG['margin_usd']

        trade = {
            'side': pos['side'],
            'entry_time': pos['entry_time'],
            'entry_price': pos['entry_price'],
            'exit_time': timestamp,
            'exit_price': price,
            'exit_reason': reason,
            'pnl_pct': pnl_pct,
            'pnl_pct_leveraged': pnl_pct_leveraged,
            'pnl_usd': pnl_usd,
            'duration': (timestamp - pos['entry_time']).total_seconds() / 3600
        }

        self.trades.append(trade)
        self.current_position = None

    def get_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_tp': 0,
                'total_sl': 0,
                'total_st_exit': 0,
                'total_pnl_pct': 0,
                'total_pnl_usd': 0,
                'avg_pnl_pct': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
                'avg_duration_hours': 0,
                'long_trades': 0,
                'short_trades': 0
            }

        trades_df = pd.DataFrame(self.trades)

        total_trades = len(trades_df)
        wins = trades_df[trades_df['pnl_usd'] > 0]
        losses = trades_df[trades_df['pnl_usd'] <= 0]

        win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0

        total_tp = len(trades_df[trades_df['exit_reason'] == 'TP'])
        total_sl = len(trades_df[trades_df['exit_reason'] == 'SL'])
        total_st_exit = len(trades_df[trades_df['exit_reason'] == 'ST_EXIT'])

        total_pnl_pct = trades_df['pnl_pct_leveraged'].sum()
        total_pnl_usd = trades_df['pnl_usd'].sum()
        avg_pnl_pct = trades_df['pnl_pct_leveraged'].mean()

        # Max Drawdown
        cumulative = trades_df['pnl_usd'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = running_max - cumulative
        max_drawdown_pct = (drawdown.max() / TRADING_CONFIG['margin_usd']) * 100 if TRADING_CONFIG['margin_usd'] > 0 else 0

        # Sharpe Ratio
        if len(trades_df) > 1 and trades_df['pnl_pct_leveraged'].std() > 0:
            sharpe_ratio = (trades_df['pnl_pct_leveraged'].mean() / trades_df['pnl_pct_leveraged'].std()) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # Profit Factor
        gross_profit = wins['pnl_usd'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['pnl_usd'].sum()) if len(losses) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        avg_duration = trades_df['duration'].mean()
        long_trades = len(trades_df[trades_df['side'] == 'LONG'])
        short_trades = len(trades_df[trades_df['side'] == 'SHORT'])

        return {
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'total_tp': total_tp,
            'total_sl': total_sl,
            'total_st_exit': total_st_exit,
            'total_pnl_pct': round(total_pnl_pct, 2),
            'total_pnl_usd': round(total_pnl_usd, 2),
            'avg_pnl_pct': round(avg_pnl_pct, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_duration_hours': round(avg_duration, 2),
            'long_trades': long_trades,
            'short_trades': short_trades
        }

# ==================== MAIN ====================

async def run_backtest_for_symbol(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "1h") -> Dict:
    """Run backtest for a symbol"""
    print(f"\n{'='*60}")
    print(f"BACKTEST: {symbol}")
    print(f"Periodo: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    print(f"Timeframe: {timeframe}")
    print(f"{'='*60}")

    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)

    print(f"Buscando dados historicos...")
    klines = await fetch_klines(symbol, timeframe, start_ts, end_ts)

    if not klines:
        print(f"Erro: Nenhum dado encontrado para {symbol}")
        return None

    print(f"  Recebidos {len(klines)} candles")

    df = klines_to_dataframe(klines)

    engine = TrendFilterBacktestEngine(df, TRADING_CONFIG)
    engine.run_backtest()

    metrics = engine.get_metrics()
    metrics['symbol'] = symbol
    metrics['period'] = f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}"

    return metrics

async def main():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    timeframe = "4h"  # Testing higher timeframe

    # Periods - Full year 2024
    periods = [
        ("Janeiro 2024", datetime(2024, 1, 1), datetime(2024, 1, 31, 23, 59, 59)),
        ("Fevereiro 2024", datetime(2024, 2, 1), datetime(2024, 2, 29, 23, 59, 59)),
        ("Marco 2024", datetime(2024, 3, 1), datetime(2024, 3, 31, 23, 59, 59)),
        ("Abril 2024", datetime(2024, 4, 1), datetime(2024, 4, 30, 23, 59, 59)),
        ("Maio 2024", datetime(2024, 5, 1), datetime(2024, 5, 31, 23, 59, 59)),
        ("Junho 2024", datetime(2024, 6, 1), datetime(2024, 6, 30, 23, 59, 59)),
        ("Julho 2024", datetime(2024, 7, 1), datetime(2024, 7, 31, 23, 59, 59)),
        ("Agosto 2024", datetime(2024, 8, 1), datetime(2024, 8, 31, 23, 59, 59)),
        ("Setembro 2024", datetime(2024, 9, 1), datetime(2024, 9, 30, 23, 59, 59)),
        ("Outubro 2024", datetime(2024, 10, 1), datetime(2024, 10, 31, 23, 59, 59)),
        ("Novembro 2024", datetime(2024, 11, 1), datetime(2024, 11, 30, 23, 59, 59)),
        ("Dezembro 2024", datetime(2024, 12, 1), datetime(2024, 12, 31, 23, 59, 59))
    ]

    all_results = []

    print("\n" + "="*80)
    print("BACKTEST ESTRATEGIA TREND FILTER (SuperTrend+ADX)")
    print("="*80)
    print(f"\nTimeframe: {timeframe}")
    print(f"\nConfiguracao:")
    print(f"  - SuperTrend: period={STRATEGY_CONFIG['supertrend']['period']}, multiplier={STRATEGY_CONFIG['supertrend']['multiplier']}")
    print(f"  - ADX: period={STRATEGY_CONFIG['adx']['period']}, threshold={STRATEGY_CONFIG['adx']['trend_threshold']}")
    print(f"\nTrading:")
    print(f"  - Stop Loss (backup): {TRADING_CONFIG['stop_loss_pct']}%")
    print(f"  - Take Profit (backup): {TRADING_CONFIG['take_profit_pct']}%")
    print(f"  - SuperTrend Exit: {TRADING_CONFIG['use_supertrend_exit']}")
    print(f"  - Alavancagem: {TRADING_CONFIG['leverage']}x")
    print(f"  - Margem: ${TRADING_CONFIG['margin_usd']}")

    for period_name, start_date, end_date in periods:
        print(f"\n\n{'#'*80}")
        print(f"# PERIODO: {period_name}")
        print(f"{'#'*80}")

        period_results = []

        for symbol in symbols:
            result = await run_backtest_for_symbol(symbol, start_date, end_date, timeframe)
            if result:
                result['period_name'] = period_name
                period_results.append(result)
                all_results.append(result)

                print(f"\n  Resultado {symbol} - {period_name}:")
                print(f"  Total de Operacoes: {result['total_trades']}")
                print(f"  Win Rate: {result['win_rate']}%")
                print(f"  TP: {result['total_tp']} | SL: {result['total_sl']} | ST_Exit: {result['total_st_exit']}")
                print(f"  PnL Total: {result['total_pnl_pct']}% (${result['total_pnl_usd']})")
                print(f"  Max Drawdown: {result['max_drawdown_pct']}%")
                print(f"  Sharpe Ratio: {result['sharpe_ratio']}")
                print(f"  Profit Factor: {result['profit_factor']}")
                print(f"  Duracao Media: {result['avg_duration_hours']}h")
                print(f"  Longs/Shorts: {result['long_trades']}/{result['short_trades']}")

    # Final Summary
    print("\n\n" + "="*80)
    print("RESUMO FINAL")
    print("="*80)

    if all_results:
        results_df = pd.DataFrame(all_results)

        print(f"\n  TABELA RESUMO POR ATIVO E PERIODO:\n")
        print(f"{'Ativo':<12} {'Periodo':<16} {'Trades':<8} {'Win%':<8} {'TP':<6} {'SL':<6} {'ST':<6} {'PnL%':<10} {'PnL$':<10} {'DD%':<8} {'Sharpe':<8} {'PF':<8}")
        print("-"*110)

        for _, row in results_df.iterrows():
            print(f"{row['symbol']:<12} {row['period_name']:<16} {row['total_trades']:<8} {row['win_rate']:<8} {row['total_tp']:<6} {row['total_sl']:<6} {row['total_st_exit']:<6} {row['total_pnl_pct']:<10} {row['total_pnl_usd']:<10} {row['max_drawdown_pct']:<8} {row['sharpe_ratio']:<8} {row['profit_factor']:<8}")

        # Summary by symbol
        print(f"\n\n  RESUMO POR ATIVO (ANO COMPLETO):\n")
        print(f"{'Ativo':<12} {'Trades':<10} {'Win%':<10} {'PnL Total $':<15} {'Sharpe Medio':<15} {'PF Medio':<10}")
        print("-"*80)

        for symbol in symbols:
            symbol_data = results_df[results_df['symbol'] == symbol]
            total_trades = symbol_data['total_trades'].sum()
            avg_win_rate = symbol_data['win_rate'].mean()
            total_pnl = symbol_data['total_pnl_usd'].sum()
            avg_sharpe = symbol_data['sharpe_ratio'].mean()
            avg_pf = symbol_data['profit_factor'].mean()

            print(f"{symbol:<12} {total_trades:<10} {avg_win_rate:<10.2f} ${total_pnl:<14.2f} {avg_sharpe:<15.2f} {avg_pf:<10.2f}")

        # Grand totals
        print(f"\n  TOTAL GERAL:")
        print(f"  - Total de Trades: {results_df['total_trades'].sum()}")
        print(f"  - Win Rate Media: {results_df['win_rate'].mean():.2f}%")
        print(f"  - PnL Total: ${results_df['total_pnl_usd'].sum():.2f}")
        print(f"  - Sharpe Medio: {results_df['sharpe_ratio'].mean():.2f}")
        print(f"  - Profit Factor Medio: {results_df['profit_factor'].mean():.2f}")

if __name__ == "__main__":
    asyncio.run(main())
