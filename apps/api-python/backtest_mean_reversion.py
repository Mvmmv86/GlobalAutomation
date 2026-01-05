"""
Backtest da Estratégia Mean Reversion (NW+RSI+BB)
- Nadaraya-Watson Envelope (mult=3, bandwidth=8)
- RSI (period=14, oversold=35, overbought=65)
- Bollinger Bands (period=20, stddev=2)

Condições:
- LONG: close < NW.lower AND RSI < 35 AND BB %B < 0.2
- SHORT: close > NW.upper AND RSI > 65 AND BB %B > 0.8
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Configurações da estratégia
STRATEGY_CONFIG = {
    "nadaraya_watson": {"mult": 3, "bandwidth": 8},
    "rsi": {"period": 14, "oversold": 35, "overbought": 65},
    "bollinger": {"period": 20, "stddev": 2}
}

# Configurações de trading
TRADING_CONFIG = {
    "stop_loss_pct": 1.5,
    "take_profit_pct": 5.0,
    "leverage": 10,
    "margin_usd": 10
}

# ==================== INDICADORES ====================

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calcula RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_bollinger(df: pd.DataFrame, period: int = 20, stddev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Calcula Bollinger Bands e %B"""
    middle = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper = middle + (std * stddev)
    lower = middle - (std * stddev)
    percent_b = (df['close'] - lower) / (upper - lower)
    return upper, middle, lower, percent_b

def kernel_regression(src: np.ndarray, bandwidth: float, x: int) -> float:
    """Nadaraya-Watson Kernel Regression"""
    size = len(src)
    weights_sum = 0.0
    value_sum = 0.0

    for i in range(size):
        weight = np.exp(-((x - i) ** 2) / (2 * bandwidth ** 2))
        weights_sum += weight
        value_sum += weight * src[i]

    if weights_sum == 0:
        return src[x] if x < size else src[-1]
    return value_sum / weights_sum

def calculate_nadaraya_watson(df: pd.DataFrame, bandwidth: float = 8, mult: float = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calcula Nadaraya-Watson Envelope"""
    close_values = df['close'].values
    size = len(close_values)

    # Calcular linha central (kernel regression)
    nw_values = []
    for i in range(size):
        lookback = min(i + 1, 500)  # Limitar lookback
        src = close_values[max(0, i - lookback + 1):i + 1]
        nw_value = kernel_regression(src, bandwidth, len(src) - 1)
        nw_values.append(nw_value)

    nw_series = pd.Series(nw_values, index=df.index)

    # Calcular ATR para as bandas
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()

    # Bandas superior e inferior
    upper = nw_series + (atr * mult)
    lower = nw_series - (atr * mult)

    return upper, nw_series, lower

# ==================== BINANCE API ====================

async def fetch_klines(symbol: str, interval: str, start_time: int, end_time: int) -> List[Dict]:
    """Busca candles da Binance"""
    url = "https://fapi.binance.com/fapi/v1/klines"
    all_klines = []
    current_start = start_time

    async with aiohttp.ClientSession() as session:
        while current_start < end_time:
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": end_time,
                "limit": 1500
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data:
                        break
                    all_klines.extend(data)
                    current_start = data[-1][0] + 1
                    await asyncio.sleep(0.1)  # Rate limiting
                else:
                    print(f"Erro ao buscar klines: {response.status}")
                    break

    return all_klines

def klines_to_dataframe(klines: List) -> pd.DataFrame:
    """Converte klines para DataFrame"""
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df.set_index('timestamp', inplace=True)

    return df

# ==================== BACKTEST ENGINE ====================

class BacktestEngine:
    def __init__(self, df: pd.DataFrame, config: Dict):
        self.df = df
        self.config = config
        self.trades = []
        self.current_position = None

    def calculate_indicators(self):
        """Calcula todos os indicadores"""
        print("  Calculando RSI...")
        self.df['rsi'] = calculate_rsi(self.df['close'], STRATEGY_CONFIG['rsi']['period'])

        print("  Calculando Bollinger Bands...")
        bb_upper, bb_middle, bb_lower, bb_percent_b = calculate_bollinger(
            self.df,
            STRATEGY_CONFIG['bollinger']['period'],
            STRATEGY_CONFIG['bollinger']['stddev']
        )
        self.df['bb_upper'] = bb_upper
        self.df['bb_middle'] = bb_middle
        self.df['bb_lower'] = bb_lower
        self.df['bb_percent_b'] = bb_percent_b

        print("  Calculando Nadaraya-Watson (pode demorar)...")
        nw_upper, nw_middle, nw_lower = calculate_nadaraya_watson(
            self.df,
            STRATEGY_CONFIG['nadaraya_watson']['bandwidth'],
            STRATEGY_CONFIG['nadaraya_watson']['mult']
        )
        self.df['nw_upper'] = nw_upper
        self.df['nw_middle'] = nw_middle
        self.df['nw_lower'] = nw_lower

    def check_entry_long(self, row) -> bool:
        """Verifica condição de entrada LONG"""
        if pd.isna(row['nw_lower']) or pd.isna(row['rsi']) or pd.isna(row['bb_percent_b']):
            return False

        cond1 = row['close'] < row['nw_lower']
        cond2 = row['rsi'] < STRATEGY_CONFIG['rsi']['oversold']
        cond3 = row['bb_percent_b'] < 0.2

        return cond1 and cond2 and cond3

    def check_entry_short(self, row) -> bool:
        """Verifica condição de entrada SHORT"""
        if pd.isna(row['nw_upper']) or pd.isna(row['rsi']) or pd.isna(row['bb_percent_b']):
            return False

        cond1 = row['close'] > row['nw_upper']
        cond2 = row['rsi'] > STRATEGY_CONFIG['rsi']['overbought']
        cond3 = row['bb_percent_b'] > 0.8

        return cond1 and cond2 and cond3

    def run_backtest(self):
        """Executa o backtest"""
        self.calculate_indicators()

        # Remover NaN iniciais
        self.df = self.df.dropna()

        print(f"  Executando backtest com {len(self.df)} candles...")

        for idx, row in self.df.iterrows():
            # Se tem posição aberta, verificar SL/TP
            if self.current_position:
                self._check_exit(idx, row)

            # Se não tem posição, verificar entrada
            if not self.current_position:
                if self.check_entry_long(row):
                    self._open_position('LONG', idx, row['close'])
                elif self.check_entry_short(row):
                    self._open_position('SHORT', idx, row['close'])

        # Fechar posição aberta no final
        if self.current_position:
            last_row = self.df.iloc[-1]
            self._close_position(self.df.index[-1], last_row['close'], 'END')

    def _open_position(self, side: str, timestamp, price: float):
        """Abre uma posição"""
        sl_pct = TRADING_CONFIG['stop_loss_pct'] / 100
        tp_pct = TRADING_CONFIG['take_profit_pct'] / 100

        if side == 'LONG':
            sl_price = price * (1 - sl_pct)
            tp_price = price * (1 + tp_pct)
        else:
            sl_price = price * (1 + sl_pct)
            tp_price = price * (1 - tp_pct)

        self.current_position = {
            'side': side,
            'entry_time': timestamp,
            'entry_price': price,
            'sl_price': sl_price,
            'tp_price': tp_price
        }

    def _check_exit(self, timestamp, row):
        """Verifica se deve sair da posição"""
        pos = self.current_position
        high = row['high']
        low = row['low']

        if pos['side'] == 'LONG':
            if low <= pos['sl_price']:
                self._close_position(timestamp, pos['sl_price'], 'SL')
            elif high >= pos['tp_price']:
                self._close_position(timestamp, pos['tp_price'], 'TP')
        else:  # SHORT
            if high >= pos['sl_price']:
                self._close_position(timestamp, pos['sl_price'], 'SL')
            elif low <= pos['tp_price']:
                self._close_position(timestamp, pos['tp_price'], 'TP')

    def _close_position(self, timestamp, price: float, reason: str):
        """Fecha a posição"""
        pos = self.current_position

        if pos['side'] == 'LONG':
            pnl_pct = ((price - pos['entry_price']) / pos['entry_price']) * 100
        else:
            pnl_pct = ((pos['entry_price'] - price) / pos['entry_price']) * 100

        # Aplicar alavancagem ao PnL
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
            'duration': (timestamp - pos['entry_time']).total_seconds() / 3600  # horas
        }

        self.trades.append(trade)
        self.current_position = None

    def get_metrics(self) -> Dict:
        """Calcula métricas do backtest"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_tp': 0,
                'total_sl': 0,
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
        wins = trades_df[trades_df['pnl_pct'] > 0]
        losses = trades_df[trades_df['pnl_pct'] <= 0]

        win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0

        total_tp = len(trades_df[trades_df['exit_reason'] == 'TP'])
        total_sl = len(trades_df[trades_df['exit_reason'] == 'SL'])

        total_pnl_pct = trades_df['pnl_pct_leveraged'].sum()
        total_pnl_usd = trades_df['pnl_usd'].sum()
        avg_pnl_pct = trades_df['pnl_pct_leveraged'].mean()

        # Calcular Drawdown
        cumulative_pnl = trades_df['pnl_usd'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = running_max - cumulative_pnl
        max_drawdown = drawdown.max()
        max_drawdown_pct = (max_drawdown / (TRADING_CONFIG['margin_usd'] * total_trades)) * 100 if total_trades > 0 else 0

        # Calcular Sharpe Ratio (simplificado)
        returns = trades_df['pnl_pct_leveraged']
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(len(returns))
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

async def run_backtest_for_symbol(symbol: str, start_date: datetime, end_date: datetime, timeframe: str = "4h") -> Dict:
    """Executa backtest para um símbolo"""
    print(f"\n{'='*60}")
    print(f"BACKTEST: {symbol}")
    print(f"Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    print(f"Timeframe: {timeframe}")
    print(f"{'='*60}")

    start_ts = int(start_date.timestamp() * 1000)
    end_ts = int(end_date.timestamp() * 1000)

    print(f"Buscando dados históricos...")
    klines = await fetch_klines(symbol, timeframe, start_ts, end_ts)

    if not klines:
        print(f"Erro: Nenhum dado encontrado para {symbol}")
        return None

    print(f"  Recebidos {len(klines)} candles")

    df = klines_to_dataframe(klines)

    engine = BacktestEngine(df, TRADING_CONFIG)
    engine.run_backtest()

    metrics = engine.get_metrics()
    metrics['symbol'] = symbol
    metrics['period'] = f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}"

    return metrics

async def main():
    symbols = ["BTCUSDT", "ETHUSDT", "LDOUSDT"]
    timeframe = "2h"  # Timeframe configurável

    # Períodos de backtest - Ano inteiro 2025
    periods = [
        ("Janeiro 2025", datetime(2025, 1, 1), datetime(2025, 1, 31, 23, 59, 59)),
        ("Fevereiro 2025", datetime(2025, 2, 1), datetime(2025, 2, 28, 23, 59, 59)),
        ("Marco 2025", datetime(2025, 3, 1), datetime(2025, 3, 31, 23, 59, 59)),
        ("Abril 2025", datetime(2025, 4, 1), datetime(2025, 4, 30, 23, 59, 59)),
        ("Maio 2025", datetime(2025, 5, 1), datetime(2025, 5, 31, 23, 59, 59)),
        ("Junho 2025", datetime(2025, 6, 1), datetime(2025, 6, 30, 23, 59, 59)),
        ("Julho 2025", datetime(2025, 7, 1), datetime(2025, 7, 31, 23, 59, 59)),
        ("Agosto 2025", datetime(2025, 8, 1), datetime(2025, 8, 31, 23, 59, 59)),
        ("Setembro 2025", datetime(2025, 9, 1), datetime(2025, 9, 30, 23, 59, 59)),
        ("Outubro 2025", datetime(2025, 10, 1), datetime(2025, 10, 31, 23, 59, 59)),
        ("Novembro 2025", datetime(2025, 11, 1), datetime(2025, 11, 30, 23, 59, 59)),
        ("Dezembro 2025", datetime(2025, 12, 1), datetime(2025, 12, 31, 23, 59, 59))
    ]

    all_results = []

    print("\n" + "="*80)
    print("BACKTEST ESTRATÉGIA MEAN REVERSION (NW+RSI+BB)")
    print("="*80)
    print(f"\nTimeframe: {timeframe}")
    print(f"\nConfiguração:")
    print(f"  - Nadaraya-Watson: mult={STRATEGY_CONFIG['nadaraya_watson']['mult']}, bandwidth={STRATEGY_CONFIG['nadaraya_watson']['bandwidth']}")
    print(f"  - RSI: period={STRATEGY_CONFIG['rsi']['period']}, oversold={STRATEGY_CONFIG['rsi']['oversold']}, overbought={STRATEGY_CONFIG['rsi']['overbought']}")
    print(f"  - Bollinger: period={STRATEGY_CONFIG['bollinger']['period']}, stddev={STRATEGY_CONFIG['bollinger']['stddev']}")
    print(f"\nTrading:")
    print(f"  - Stop Loss: {TRADING_CONFIG['stop_loss_pct']}%")
    print(f"  - Take Profit: {TRADING_CONFIG['take_profit_pct']}%")
    print(f"  - Alavancagem: {TRADING_CONFIG['leverage']}x")
    print(f"  - Margem: ${TRADING_CONFIG['margin_usd']}")

    for period_name, start_date, end_date in periods:
        print(f"\n\n{'#'*80}")
        print(f"# PERÍODO: {period_name}")
        print(f"{'#'*80}")

        period_results = []

        for symbol in symbols:
            result = await run_backtest_for_symbol(symbol, start_date, end_date, timeframe)
            if result:
                result['period_name'] = period_name
                period_results.append(result)
                all_results.append(result)

                # Mostrar resultado
                print(f"\n📊 Resultado {symbol} - {period_name}:")
                print(f"  Total de Operações: {result['total_trades']}")
                print(f"  Win Rate: {result['win_rate']}%")
                print(f"  Take Profits: {result['total_tp']}")
                print(f"  Stop Losses: {result['total_sl']}")
                print(f"  PnL Total: {result['total_pnl_pct']}% (${result['total_pnl_usd']})")
                print(f"  PnL Médio por Trade: {result['avg_pnl_pct']}%")
                print(f"  Max Drawdown: {result['max_drawdown_pct']}%")
                print(f"  Sharpe Ratio: {result['sharpe_ratio']}")
                print(f"  Profit Factor: {result['profit_factor']}")
                print(f"  Duração Média: {result['avg_duration_hours']}h")
                print(f"  Longs/Shorts: {result['long_trades']}/{result['short_trades']}")

    # Resumo Final
    print("\n\n" + "="*80)
    print("RESUMO FINAL")
    print("="*80)

    if all_results:
        df_results = pd.DataFrame(all_results)

        print("\n📊 TABELA RESUMO POR ATIVO E PERÍODO:\n")
        print(f"{'Ativo':<12} {'Período':<15} {'Trades':<8} {'Win%':<8} {'TP':<6} {'SL':<6} {'PnL%':<10} {'PnL$':<10} {'DD%':<8} {'Sharpe':<8} {'PF':<8}")
        print("-" * 110)

        for _, row in df_results.iterrows():
            print(f"{row['symbol']:<12} {row['period_name']:<15} {row['total_trades']:<8} {row['win_rate']:<8} {row['total_tp']:<6} {row['total_sl']:<6} {row['total_pnl_pct']:<10} {row['total_pnl_usd']:<10} {row['max_drawdown_pct']:<8} {row['sharpe_ratio']:<8} {row['profit_factor']:<8}")

        # Totais por período
        print("\n📊 TOTAIS POR PERÍODO:\n")
        for period_name in df_results['period_name'].unique():
            period_data = df_results[df_results['period_name'] == period_name]
            total_trades = period_data['total_trades'].sum()
            avg_winrate = period_data['win_rate'].mean()
            total_tp = period_data['total_tp'].sum()
            total_sl = period_data['total_sl'].sum()
            total_pnl = period_data['total_pnl_usd'].sum()
            avg_sharpe = period_data['sharpe_ratio'].mean()

            print(f"{period_name}:")
            print(f"  Total Trades: {total_trades}")
            print(f"  Win Rate Médio: {avg_winrate:.2f}%")
            print(f"  Total TP/SL: {total_tp}/{total_sl}")
            print(f"  PnL Total: ${total_pnl:.2f}")
            print(f"  Sharpe Médio: {avg_sharpe:.2f}")
            print()

if __name__ == "__main__":
    asyncio.run(main())
