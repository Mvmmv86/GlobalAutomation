#!/usr/bin/env python3
"""Simple script to create 5 optimized strategies using requests"""

import requests
import time

API_URL = "http://localhost:8001/api/v1"


def create_strategy(data):
    """Create a strategy"""
    response = requests.post(f"{API_URL}/strategies", json=data, timeout=120)
    return response.json()


def add_indicator(strategy_id, data):
    """Add an indicator"""
    response = requests.post(f"{API_URL}/strategies/{strategy_id}/indicators", json=data, timeout=60)
    return response.json()


def add_condition(strategy_id, data):
    """Add a condition"""
    response = requests.post(f"{API_URL}/strategies/{strategy_id}/conditions", json=data, timeout=60)
    return response.json()


STRATEGIES = [
    # Strategy 1: Momentum Combo
    {
        "strategy": {
            "name": "Momentum Combo (MACD+RSI+EMA)",
            "description": "Estratégia de momentum com Sharpe 1.19-1.4 e Win Rate 73-85%",
            "config_type": "visual",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
            "timeframe": "4h"
        },
        "indicators": [
            {"indicator_type": "macd", "parameters": {"fast": 12, "slow": 26, "signal": 9}, "order_index": 0},
            {"indicator_type": "rsi", "parameters": {"period": 14, "overbought": 70, "oversold": 30}, "order_index": 1},
            {"indicator_type": "ema_cross", "parameters": {"fast_period": 13, "slow_period": 48}, "order_index": 2}
        ],
        "conditions": [
            {"condition_type": "entry_long", "conditions": [{"left": "macd.histogram", "operator": ">", "right": "0"}, {"left": "rsi.value", "operator": ">", "right": "50"}], "logic_operator": "AND", "order_index": 0},
            {"condition_type": "entry_short", "conditions": [{"left": "macd.histogram", "operator": "<", "right": "0"}, {"left": "rsi.value", "operator": "<", "right": "50"}], "logic_operator": "AND", "order_index": 1},
            {"condition_type": "exit_long", "conditions": [{"left": "rsi.value", "operator": ">", "right": "70"}], "logic_operator": "AND", "order_index": 2},
            {"condition_type": "exit_short", "conditions": [{"left": "rsi.value", "operator": "<", "right": "30"}], "logic_operator": "AND", "order_index": 3}
        ]
    },
    # Strategy 2: Trend Filter
    {
        "strategy": {
            "name": "Trend Filter (SuperTrend+ADX)",
            "description": "Estratégia de trend-following com Sharpe 0.8-1.1 e Win Rate 65-70%",
            "config_type": "visual",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT"],
            "timeframe": "1h"
        },
        "indicators": [
            {"indicator_type": "supertrend", "parameters": {"period": 10, "multiplier": 3.0}, "order_index": 0},
            {"indicator_type": "adx", "parameters": {"period": 14, "trend_threshold": 25}, "order_index": 1}
        ],
        "conditions": [
            {"condition_type": "entry_long", "conditions": [{"left": "supertrend.trend", "operator": "==", "right": "1"}, {"left": "adx.adx", "operator": ">", "right": "25"}], "logic_operator": "AND", "order_index": 0},
            {"condition_type": "entry_short", "conditions": [{"left": "supertrend.trend", "operator": "==", "right": "-1"}, {"left": "adx.adx", "operator": ">", "right": "25"}], "logic_operator": "AND", "order_index": 1},
            {"condition_type": "exit_long", "conditions": [{"left": "supertrend.trend", "operator": "==", "right": "-1"}], "logic_operator": "AND", "order_index": 2},
            {"condition_type": "exit_short", "conditions": [{"left": "supertrend.trend", "operator": "==", "right": "1"}], "logic_operator": "AND", "order_index": 3}
        ]
    },
    # Strategy 3: Ichimoku Breakout
    {
        "strategy": {
            "name": "Ichimoku Breakout",
            "description": "Estratégia Ichimoku Cloud com CAGR 78% e Sharpe 1.25",
            "config_type": "visual",
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframe": "4h"
        },
        "indicators": [
            {"indicator_type": "ichimoku", "parameters": {"tenkan_period": 20, "kijun_period": 60, "senkou_b_period": 120, "displacement": 30}, "order_index": 0}
        ],
        "conditions": [
            {"condition_type": "entry_long", "conditions": [{"left": "close", "operator": ">", "right": "ichimoku.cloud_top"}, {"left": "ichimoku.tenkan", "operator": ">", "right": "ichimoku.kijun"}], "logic_operator": "AND", "order_index": 0},
            {"condition_type": "entry_short", "conditions": [{"left": "close", "operator": "<", "right": "ichimoku.cloud_bottom"}, {"left": "ichimoku.tenkan", "operator": "<", "right": "ichimoku.kijun"}], "logic_operator": "AND", "order_index": 1},
            {"condition_type": "exit_long", "conditions": [{"left": "close", "operator": "<", "right": "ichimoku.kijun"}], "logic_operator": "AND", "order_index": 2},
            {"condition_type": "exit_short", "conditions": [{"left": "close", "operator": ">", "right": "ichimoku.kijun"}], "logic_operator": "AND", "order_index": 3}
        ]
    },
    # Strategy 4: Bollinger Squeeze
    {
        "strategy": {
            "name": "Bollinger Squeeze (BB+ADX+OBV)",
            "description": "Estratégia de breakout após squeeze com Sharpe 0.7-1.0 e Win Rate 54-60%",
            "config_type": "visual",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "AVAXUSDT"],
            "timeframe": "1h"
        },
        "indicators": [
            {"indicator_type": "bollinger", "parameters": {"period": 20, "stddev": 2.0}, "order_index": 0},
            {"indicator_type": "adx", "parameters": {"period": 14, "trend_threshold": 20}, "order_index": 1},
            {"indicator_type": "obv", "parameters": {"sma_period": 20, "signal_period": 14}, "order_index": 2}
        ],
        "conditions": [
            {"condition_type": "entry_long", "conditions": [{"left": "close", "operator": ">", "right": "bollinger.upper"}, {"left": "adx.adx", "operator": ">", "right": "20"}], "logic_operator": "AND", "order_index": 0},
            {"condition_type": "entry_short", "conditions": [{"left": "close", "operator": "<", "right": "bollinger.lower"}, {"left": "adx.adx", "operator": ">", "right": "20"}], "logic_operator": "AND", "order_index": 1},
            {"condition_type": "exit_long", "conditions": [{"left": "close", "operator": "<", "right": "bollinger.middle"}], "logic_operator": "AND", "order_index": 2},
            {"condition_type": "exit_short", "conditions": [{"left": "close", "operator": ">", "right": "bollinger.middle"}], "logic_operator": "AND", "order_index": 3}
        ]
    },
    # Strategy 5: Mean Reversion
    {
        "strategy": {
            "name": "Mean Reversion (NW+RSI+BB)",
            "description": "Estratégia de reversão à média com Sharpe 1.71 e Win Rate 60-70%",
            "config_type": "visual",
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "timeframe": "4h"
        },
        "indicators": [
            {"indicator_type": "nadaraya_watson", "parameters": {"bandwidth": 8, "mult": 3.0}, "order_index": 0},
            {"indicator_type": "rsi", "parameters": {"period": 14, "overbought": 65, "oversold": 35}, "order_index": 1},
            {"indicator_type": "bollinger", "parameters": {"period": 20, "stddev": 2.5}, "order_index": 2}
        ],
        "conditions": [
            {"condition_type": "entry_long", "conditions": [{"left": "close", "operator": "<", "right": "nadaraya_watson.lower"}, {"left": "rsi.value", "operator": "<", "right": "35"}], "logic_operator": "AND", "order_index": 0},
            {"condition_type": "entry_short", "conditions": [{"left": "close", "operator": ">", "right": "nadaraya_watson.upper"}, {"left": "rsi.value", "operator": ">", "right": "65"}], "logic_operator": "AND", "order_index": 1},
            {"condition_type": "exit_long", "conditions": [{"left": "close", "operator": ">", "right": "nadaraya_watson.value"}], "logic_operator": "AND", "order_index": 2},
            {"condition_type": "exit_short", "conditions": [{"left": "close", "operator": "<", "right": "nadaraya_watson.value"}], "logic_operator": "AND", "order_index": 3}
        ]
    }
]


def main():
    print("=" * 70)
    print("CRIANDO 5 ESTRATÉGIAS OTIMIZADAS")
    print("=" * 70)
    print()

    created = []

    for i, config in enumerate(STRATEGIES, 1):
        strategy_data = config["strategy"]
        print(f"[{i}/5] Criando: {strategy_data['name']}")
        print(f"       Ativos: {', '.join(strategy_data['symbols'])}")
        print(f"       Timeframe: {strategy_data['timeframe']}")

        try:
            # Create strategy
            result = create_strategy(strategy_data)
            if not result.get("success"):
                print(f"       ❌ Falha: {result}")
                continue

            strategy_id = result["data"]["id"]
            print(f"       ✓ Estratégia criada: {strategy_id}")

            # Add indicators
            for ind in config["indicators"]:
                ind_result = add_indicator(strategy_id, ind)
                if ind_result.get("success"):
                    print(f"       ✓ Indicador: {ind['indicator_type']}")
                else:
                    print(f"       ⚠ Indicador falhou: {ind['indicator_type']}")
                time.sleep(0.3)

            # Add conditions
            for cond in config["conditions"]:
                cond_result = add_condition(strategy_id, cond)
                if cond_result.get("success"):
                    print(f"       ✓ Condição: {cond['condition_type']}")
                else:
                    print(f"       ⚠ Condição falhou: {cond['condition_type']}")
                time.sleep(0.3)

            created.append({
                "id": strategy_id,
                "name": strategy_data["name"],
                "symbols": strategy_data["symbols"],
                "timeframe": strategy_data["timeframe"]
            })
            print()

        except Exception as e:
            print(f"       ❌ Erro: {e}")
            print()

        time.sleep(1)  # Wait between strategies

    # Summary
    print("=" * 70)
    print("RESUMO")
    print("=" * 70)
    for s in created:
        print(f"ID: {s['id']}")
        print(f"Nome: {s['name']}")
        print(f"Ativos: {', '.join(s['symbols'])}")
        print(f"Timeframe: {s['timeframe']}")
        print("-" * 40)

    print(f"\nTotal: {len(created)} estratégias criadas com sucesso!")


if __name__ == "__main__":
    main()
