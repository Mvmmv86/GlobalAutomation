#!/usr/bin/env python3
"""
Backtest da Estratégia Momentum Combo (MACD+RSI+EMA)

Estratégia de momentum tripla confirmação:
- MACD crossover como timing de entrada
- RSI > 50 / < 50 como filtro de momentum
- EMA lenta (48) como filtro de tendência

Condições:
- ENTRY LONG: MACD > Signal + RSI > 50 + Close > EMA(48)
- ENTRY SHORT: MACD < Signal + RSI < 50 + Close < EMA(48)
- EXIT LONG: MACD < Signal
- EXIT SHORT: MACD > Signal

Baseado em: QuantifiedStrategies Research
Sharpe esperado: 1.19-1.4 | Win Rate: 73-85%
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

# ==================== CONFIGURAÇÃO ====================

STRATEGY_CONFIG = {
    "macd": {
        "fast": 12,
        "slow": 26,
        "signal": 9
    },
    "rsi": {
        "period": 14,
        "overbought": 70,
        "oversold": 30
    },
    "ema_cross": {
        "fast_period": 13,
        "slow_period": 48
    }
}

TRADING_CONFIG = {
    "stop_loss_pct": 2.0,      # Stop loss %
    "take_profit_pct": 6.0,    # Take profit %
    "leverage": 10,
    "margin_usd": 10,          # Margem por trade
    "use_macd_exit": True      # Usar MACD crossover para saída
}

# ==================== DATA FETCHING ====================

async def fetch_klines(symbol: str, interval: str, start_time: int, end_time: int) -> List:
    """Busca dados históricos da Binance"""
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
                    klines = await response.json()
                    if not klines:
                        break
                    all_klines.extend(klines)
                    current_start = klines[-1][0] + 1
                    await asyncio.sleep(0.1)
                else:
                    print(f"Erro na API: {response.status}")
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
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    return df

# ==================== INDICADORES ====================

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcula EMA"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula MACD, Signal Line e Histogram"""
    fast = STRATEGY_CONFIG['macd']['fast']
    slow = STRATEGY_CONFIG['macd']['slow']
    signal_period = STRATEGY_CONFIG['macd']['signal']

    # MACD Line = Fast EMA - Slow EMA
    fast_ema = calculate_ema(df['close'], fast)
    slow_ema = calculate_ema(df['close'], slow)
    df['macd'] = fast_ema - slow_ema

    # Signal Line = EMA of MACD
    df['macd_signal'] = calculate_ema(df['macd'], signal_period)

    # Histogram
    df['macd_histogram'] = df['macd'] - df['macd_signal']

    # MACD Crossover
    df['macd_prev'] = df['macd'].shift(1)
    df['signal_prev'] = df['macd_signal'].shift(1)

    return df

def calculate_rsi(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula RSI"""
    period = STRATEGY_CONFIG['rsi']['period']

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    # Avoid division by zero
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)

    return df

def calculate_ema_cross(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula EMA Cross"""
    fast_period = STRATEGY_CONFIG['ema_cross']['fast_period']
    slow_period = STRATEGY_CONFIG['ema_cross']['slow_period']

    df['ema_fast'] = calculate_ema(df['close'], fast_period)
    df['ema_slow'] = calculate_ema(df['close'], slow_period)

    # Trend: 1 = bullish (fast > slow), -1 = bearish
    df['ema_trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)

    return df

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona todos os indicadores"""
    df = calculate_macd(df)
    df = calculate_rsi(df)
    df = calculate_ema_cross(df)
    return df

# ==================== BACKTEST ENGINE ====================

@dataclass
class Trade:
    entry_time: datetime
    entry_price: float
    direction: str  # 'long' or 'short'
    stop_loss: float
    take_profit: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None

class BacktestEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.trades: List[Trade] = []
        self.current_trade: Optional[Trade] = None
        self.balance = 0.0

    def check_entry_long(self, row, prev_row) -> bool:
        """Verifica condições de entrada long"""
        # MACD acima da Signal Line
        cond1 = row['macd'] > row['macd_signal']

        # RSI > 50 (momentum bullish)
        cond2 = row['rsi'] > 50

        # Preço acima da EMA lenta (trend filter)
        cond3 = row['close'] > row['ema_slow']

        # MACD crossover (acabou de cruzar para cima)
        cond4 = prev_row['macd'] <= prev_row['macd_signal'] and row['macd'] > row['macd_signal']

        # Todas as condições devem ser verdadeiras + crossover
        return cond1 and cond2 and cond3 and cond4

    def check_entry_short(self, row, prev_row) -> bool:
        """Verifica condições de entrada short"""
        # MACD abaixo da Signal Line
        cond1 = row['macd'] < row['macd_signal']

        # RSI < 50 (momentum bearish)
        cond2 = row['rsi'] < 50

        # Preço abaixo da EMA lenta (trend filter)
        cond3 = row['close'] < row['ema_slow']

        # MACD crossover (acabou de cruzar para baixo)
        cond4 = prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']

        # Todas as condições devem ser verdadeiras + crossover
        return cond1 and cond2 and cond3 and cond4

    def check_exit_long(self, row, prev_row, trade: Trade) -> Tuple[bool, str]:
        """Verifica condições de saída long"""
        # Stop Loss
        if row['low'] <= trade.stop_loss:
            return True, "stop_loss"

        # Take Profit
        if row['high'] >= trade.take_profit:
            return True, "take_profit"

        # MACD Exit: cruza para baixo
        if TRADING_CONFIG['use_macd_exit']:
            if prev_row['macd'] >= prev_row['macd_signal'] and row['macd'] < row['macd_signal']:
                return True, "macd_exit"

        return False, ""

    def check_exit_short(self, row, prev_row, trade: Trade) -> Tuple[bool, str]:
        """Verifica condições de saída short"""
        # Stop Loss
        if row['high'] >= trade.stop_loss:
            return True, "stop_loss"

        # Take Profit
        if row['low'] <= trade.take_profit:
            return True, "take_profit"

        # MACD Exit: cruza para cima
        if TRADING_CONFIG['use_macd_exit']:
            if prev_row['macd'] <= prev_row['macd_signal'] and row['macd'] > row['macd_signal']:
                return True, "macd_exit"

        return False, ""

    def run(self):
        """Executa o backtest"""
        # Precisamos de dados suficientes para os indicadores
        # MACD slow (26) + signal (9) = ~35 candles
        # EMA slow (48) = 48 candles
        min_candles = 50

        for i in range(min_candles, len(self.df)):
            row = self.df.iloc[i]
            prev_row = self.df.iloc[i-1]

            # Se não temos posição, verifica entrada
            if self.current_trade is None:
                # Check Long Entry
                if self.check_entry_long(row, prev_row):
                    entry_price = row['close']
                    stop_loss = entry_price * (1 - TRADING_CONFIG['stop_loss_pct'] / 100)
                    take_profit = entry_price * (1 + TRADING_CONFIG['take_profit_pct'] / 100)

                    self.current_trade = Trade(
                        entry_time=row['timestamp'],
                        entry_price=entry_price,
                        direction='long',
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )

                # Check Short Entry
                elif self.check_entry_short(row, prev_row):
                    entry_price = row['close']
                    stop_loss = entry_price * (1 + TRADING_CONFIG['stop_loss_pct'] / 100)
                    take_profit = entry_price * (1 - TRADING_CONFIG['take_profit_pct'] / 100)

                    self.current_trade = Trade(
                        entry_time=row['timestamp'],
                        entry_price=entry_price,
                        direction='short',
                        stop_loss=stop_loss,
                        take_profit=take_profit
                    )

            # Se temos posição, verifica saída
            else:
                should_exit = False
                exit_reason = ""
                exit_price = row['close']

                if self.current_trade.direction == 'long':
                    should_exit, exit_reason = self.check_exit_long(row, prev_row, self.current_trade)
                    if exit_reason == "stop_loss":
                        exit_price = self.current_trade.stop_loss
                    elif exit_reason == "take_profit":
                        exit_price = self.current_trade.take_profit
                else:
                    should_exit, exit_reason = self.check_exit_short(row, prev_row, self.current_trade)
                    if exit_reason == "stop_loss":
                        exit_price = self.current_trade.stop_loss
                    elif exit_reason == "take_profit":
                        exit_price = self.current_trade.take_profit

                if should_exit:
                    self.current_trade.exit_time = row['timestamp']
                    self.current_trade.exit_price = exit_price
                    self.current_trade.exit_reason = exit_reason

                    # Calcula P&L
                    if self.current_trade.direction == 'long':
                        pnl_pct = (exit_price - self.current_trade.entry_price) / self.current_trade.entry_price * 100
                    else:
                        pnl_pct = (self.current_trade.entry_price - exit_price) / self.current_trade.entry_price * 100

                    # P&L com alavancagem
                    pnl_usd = (pnl_pct / 100) * TRADING_CONFIG['margin_usd'] * TRADING_CONFIG['leverage']

                    self.current_trade.pnl = pnl_usd
                    self.current_trade.pnl_pct = pnl_pct
                    self.balance += pnl_usd

                    self.trades.append(self.current_trade)
                    self.current_trade = None

        # Fecha posição aberta no final
        if self.current_trade is not None:
            last_row = self.df.iloc[-1]
            exit_price = last_row['close']
            self.current_trade.exit_time = last_row['timestamp']
            self.current_trade.exit_price = exit_price
            self.current_trade.exit_reason = "end_of_period"

            if self.current_trade.direction == 'long':
                pnl_pct = (exit_price - self.current_trade.entry_price) / self.current_trade.entry_price * 100
            else:
                pnl_pct = (self.current_trade.entry_price - exit_price) / self.current_trade.entry_price * 100

            pnl_usd = (pnl_pct / 100) * TRADING_CONFIG['margin_usd'] * TRADING_CONFIG['leverage']
            self.current_trade.pnl = pnl_usd
            self.current_trade.pnl_pct = pnl_pct
            self.balance += pnl_usd

            self.trades.append(self.current_trade)
            self.current_trade = None

    def get_metrics(self) -> Dict:
        """Calcula métricas do backtest"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'max_win': 0,
                'max_loss': 0,
                'profit_factor': 0,
                'avg_duration_hours': 0,
                'long_trades': 0,
                'short_trades': 0,
                'macd_exits': 0,
                'sl_exits': 0,
                'tp_exits': 0
            }

        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        long_trades = [t for t in self.trades if t.direction == 'long']
        short_trades = [t for t in self.trades if t.direction == 'short']

        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))

        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in self.trades]
        avg_duration = sum(durations) / len(durations) if durations else 0

        macd_exits = len([t for t in self.trades if t.exit_reason == 'macd_exit'])
        sl_exits = len([t for t in self.trades if t.exit_reason == 'stop_loss'])
        tp_exits = len([t for t in self.trades if t.exit_reason == 'take_profit'])

        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(len(winning_trades) / len(self.trades) * 100, 2),
            'total_pnl': round(self.balance, 2),
            'avg_pnl': round(self.balance / len(self.trades), 2),
            'max_win': round(max(t.pnl for t in self.trades), 2),
            'max_loss': round(min(t.pnl for t in self.trades), 2),
            'profit_factor': round(profit_factor, 2),
            'avg_duration_hours': round(avg_duration, 2),
            'long_trades': len(long_trades),
            'short_trades': len(short_trades),
            'macd_exits': macd_exits,
            'sl_exits': sl_exits,
            'tp_exits': tp_exits
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
    df = add_indicators(df)

    engine = BacktestEngine(df)
    engine.run()

    metrics = engine.get_metrics()
    metrics['symbol'] = symbol
    metrics['period'] = f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}"

    return metrics

async def main():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    timeframe = "1h"  # Testing lower timeframe

    # Períodos de backtest - Ano inteiro 2024
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
    print("BACKTEST ESTRATÉGIA MOMENTUM COMBO (MACD+RSI+EMA)")
    print("="*80)
    print(f"\nTimeframe: {timeframe}")
    print(f"\nConfiguração:")
    print(f"  - MACD: fast={STRATEGY_CONFIG['macd']['fast']}, slow={STRATEGY_CONFIG['macd']['slow']}, signal={STRATEGY_CONFIG['macd']['signal']}")
    print(f"  - RSI: period={STRATEGY_CONFIG['rsi']['period']}")
    print(f"  - EMA Cross: fast={STRATEGY_CONFIG['ema_cross']['fast_period']}, slow={STRATEGY_CONFIG['ema_cross']['slow_period']}")
    print(f"\nTrading:")
    print(f"  - Stop Loss: {TRADING_CONFIG['stop_loss_pct']}%")
    print(f"  - Take Profit: {TRADING_CONFIG['take_profit_pct']}%")
    print(f"  - Alavancagem: {TRADING_CONFIG['leverage']}x")
    print(f"  - Margem: ${TRADING_CONFIG['margin_usd']}")
    print(f"  - Exit MACD: {TRADING_CONFIG['use_macd_exit']}")

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
                print(f"  P&L Total: ${result['total_pnl']}")
                print(f"  Profit Factor: {result['profit_factor']}")
                print(f"  Long/Short: {result['long_trades']}/{result['short_trades']}")
                print(f"  Exits - MACD: {result['macd_exits']} | SL: {result['sl_exits']} | TP: {result['tp_exits']}")

    # Resumo final
    print("\n" + "="*80)
    print("RESUMO FINAL - ANO 2024")
    print("="*80)

    # Agrupa por símbolo
    for symbol in symbols:
        symbol_results = [r for r in all_results if r['symbol'] == symbol]
        if symbol_results:
            total_trades = sum(r['total_trades'] for r in symbol_results)
            total_pnl = sum(r['total_pnl'] for r in symbol_results)
            total_wins = sum(r['winning_trades'] for r in symbol_results)

            win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

            print(f"\n{symbol}:")
            print(f"  Total Trades: {total_trades}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  P&L Total: ${total_pnl:.2f}")
            print(f"  P&L Médio/Trade: ${(total_pnl/total_trades):.2f}" if total_trades > 0 else "  P&L Médio/Trade: $0.00")

    # Total geral
    total_all_trades = sum(r['total_trades'] for r in all_results)
    total_all_pnl = sum(r['total_pnl'] for r in all_results)
    total_all_wins = sum(r['winning_trades'] for r in all_results)

    print(f"\n{'='*80}")
    print("TOTAL GERAL:")
    print(f"  Total Trades: {total_all_trades}")
    print(f"  Win Rate Geral: {(total_all_wins/total_all_trades*100):.2f}%" if total_all_trades > 0 else "  Win Rate Geral: 0%")
    print(f"  P&L Total: ${total_all_pnl:.2f}")
    print(f"{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())
