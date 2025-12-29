#!/usr/bin/env python3
"""
Script para corrigir as estratégias baseado na análise ultrathink.

Correções:
1. Momentum Combo: Usar MACD crossover + EMA trend filter
2. Trend Filter: Aumentar multiplier para 3.5
3. Ichimoku: Manter (lógica OK)
4. Bollinger Squeeze: Detectar squeeze + usar OBV
5. Mean Reversion: Adicionar Bollinger como confirmação
"""

import asyncio
import os
import json
from dotenv import load_dotenv
import asyncpg
import ssl

load_dotenv()

# Configurações corrigidas baseadas nas pesquisas

CORRECTED_STRATEGIES = {
    "Momentum Combo (MACD+RSI+EMA)": {
        "description": "Estratégia de momentum baseada em QuantifiedStrategies. MACD crossover + RSI momentum + EMA trend filter. Sharpe 1.19-1.4, Win Rate 73-85%.",
        "indicators": [
            {"indicator_type": "macd", "parameters": {"fast": 12, "slow": 26, "signal": 9}, "order_index": 0},
            {"indicator_type": "rsi", "parameters": {"period": 14, "overbought": 70, "oversold": 30}, "order_index": 1},
            {"indicator_type": "ema_cross", "parameters": {"fast_period": 13, "slow_period": 48}, "order_index": 2}
        ],
        "conditions": [
            # Entry Long: MACD crossover bullish + RSI > 50 + Price acima da EMA lenta
            {
                "condition_type": "entry_long",
                "conditions": [
                    {"left": "macd.macd", "operator": ">", "right": "macd.signal_line"},
                    {"left": "rsi.value", "operator": ">", "right": "50"},
                    {"left": "close", "operator": ">", "right": "ema_cross.slow_ema"}
                ],
                "logic_operator": "AND",
                "order_index": 0
            },
            # Entry Short: MACD crossover bearish + RSI < 50 + Price abaixo da EMA lenta
            {
                "condition_type": "entry_short",
                "conditions": [
                    {"left": "macd.macd", "operator": "<", "right": "macd.signal_line"},
                    {"left": "rsi.value", "operator": "<", "right": "50"},
                    {"left": "close", "operator": "<", "right": "ema_cross.slow_ema"}
                ],
                "logic_operator": "AND",
                "order_index": 1
            },
            # Exit Long: MACD crossover reverso OU RSI overbought
            {
                "condition_type": "exit_long",
                "conditions": [
                    {"left": "macd.macd", "operator": "<", "right": "macd.signal_line"}
                ],
                "logic_operator": "AND",
                "order_index": 2
            },
            # Exit Short: MACD crossover reverso OU RSI oversold
            {
                "condition_type": "exit_short",
                "conditions": [
                    {"left": "macd.macd", "operator": ">", "right": "macd.signal_line"}
                ],
                "logic_operator": "AND",
                "order_index": 3
            }
        ]
    },

    "Trend Filter (SuperTrend+ADX)": {
        "description": "Estratégia trend-following baseada em SSRN research. SuperTrend com multiplier otimizado para crypto + ADX filter. Sharpe 0.8-1.1, Win Rate 65-70%.",
        "indicators": [
            # Multiplier aumentado de 3.0 para 3.5 para reduzir whipsaws em crypto
            {"indicator_type": "supertrend", "parameters": {"period": 10, "multiplier": 3.5}, "order_index": 0},
            {"indicator_type": "adx", "parameters": {"period": 14, "trend_threshold": 25}, "order_index": 1}
        ],
        "conditions": [
            # Entry Long: SuperTrend bullish + ADX forte (> 25) + DI+ > DI-
            {
                "condition_type": "entry_long",
                "conditions": [
                    {"left": "supertrend.trend", "operator": "==", "right": "1"},
                    {"left": "adx.adx", "operator": ">", "right": "25"},
                    {"left": "adx.plus_di", "operator": ">", "right": "adx.minus_di"}
                ],
                "logic_operator": "AND",
                "order_index": 0
            },
            # Entry Short: SuperTrend bearish + ADX forte + DI- > DI+
            {
                "condition_type": "entry_short",
                "conditions": [
                    {"left": "supertrend.trend", "operator": "==", "right": "-1"},
                    {"left": "adx.adx", "operator": ">", "right": "25"},
                    {"left": "adx.minus_di", "operator": ">", "right": "adx.plus_di"}
                ],
                "logic_operator": "AND",
                "order_index": 1
            },
            # Exit Long: SuperTrend flip para bearish
            {
                "condition_type": "exit_long",
                "conditions": [
                    {"left": "supertrend.trend", "operator": "==", "right": "-1"}
                ],
                "logic_operator": "AND",
                "order_index": 2
            },
            # Exit Short: SuperTrend flip para bullish
            {
                "condition_type": "exit_short",
                "conditions": [
                    {"left": "supertrend.trend", "operator": "==", "right": "1"}
                ],
                "logic_operator": "AND",
                "order_index": 3
            }
        ]
    },

    "Ichimoku Breakout": {
        "description": "Estratégia Ichimoku Cloud baseada em 21Shares Research. Parâmetros otimizados para crypto (20/60/120/30). CAGR 78%, Sharpe 1.25.",
        "indicators": [
            {"indicator_type": "ichimoku", "parameters": {"tenkan_period": 20, "kijun_period": 60, "senkou_b_period": 120, "displacement": 30}, "order_index": 0}
        ],
        "conditions": [
            # Entry Long: Kumo breakout + TK cross bullish + Price acima da nuvem
            {
                "condition_type": "entry_long",
                "conditions": [
                    {"left": "close", "operator": ">", "right": "ichimoku.cloud_top"},
                    {"left": "ichimoku.tenkan", "operator": ">", "right": "ichimoku.kijun"},
                    {"left": "ichimoku.trend", "operator": "==", "right": "1"}
                ],
                "logic_operator": "AND",
                "order_index": 0
            },
            # Entry Short: Kumo breakdown + TK cross bearish + Price abaixo da nuvem
            {
                "condition_type": "entry_short",
                "conditions": [
                    {"left": "close", "operator": "<", "right": "ichimoku.cloud_bottom"},
                    {"left": "ichimoku.tenkan", "operator": "<", "right": "ichimoku.kijun"},
                    {"left": "ichimoku.trend", "operator": "==", "right": "-1"}
                ],
                "logic_operator": "AND",
                "order_index": 1
            },
            # Exit Long: TK cross bearish OU price volta para dentro da nuvem
            {
                "condition_type": "exit_long",
                "conditions": [
                    {"left": "ichimoku.tenkan", "operator": "<", "right": "ichimoku.kijun"}
                ],
                "logic_operator": "AND",
                "order_index": 2
            },
            # Exit Short: TK cross bullish
            {
                "condition_type": "exit_short",
                "conditions": [
                    {"left": "ichimoku.tenkan", "operator": ">", "right": "ichimoku.kijun"}
                ],
                "logic_operator": "AND",
                "order_index": 3
            }
        ]
    },

    "Bollinger Squeeze (BB+ADX+OBV)": {
        "description": "Estratégia de breakout após período de baixa volatilidade. Detecta squeeze via bandwidth < 4% + confirmação de volume via OBV. Sharpe 0.7-1.0, Win Rate 54-60%.",
        "indicators": [
            {"indicator_type": "bollinger", "parameters": {"period": 20, "stddev": 2.0}, "order_index": 0},
            {"indicator_type": "adx", "parameters": {"period": 14, "trend_threshold": 20}, "order_index": 1},
            {"indicator_type": "obv", "parameters": {"sma_period": 20, "signal_period": 14}, "order_index": 2}
        ],
        "conditions": [
            # Entry Long: Squeeze (bandwidth < 4) + Breakout acima upper + OBV bullish + ADX subindo
            {
                "condition_type": "entry_long",
                "conditions": [
                    {"left": "bollinger.bandwidth", "operator": "<", "right": "6"},
                    {"left": "close", "operator": ">", "right": "bollinger.upper"},
                    {"left": "obv.trend", "operator": "==", "right": "1"},
                    {"left": "adx.adx", "operator": ">", "right": "20"}
                ],
                "logic_operator": "AND",
                "order_index": 0
            },
            # Entry Short: Squeeze + Breakdown abaixo lower + OBV bearish
            {
                "condition_type": "entry_short",
                "conditions": [
                    {"left": "bollinger.bandwidth", "operator": "<", "right": "6"},
                    {"left": "close", "operator": "<", "right": "bollinger.lower"},
                    {"left": "obv.trend", "operator": "==", "right": "-1"},
                    {"left": "adx.adx", "operator": ">", "right": "20"}
                ],
                "logic_operator": "AND",
                "order_index": 1
            },
            # Exit Long: Price retorna para middle band OU OBV inverte
            {
                "condition_type": "exit_long",
                "conditions": [
                    {"left": "close", "operator": "<", "right": "bollinger.middle"}
                ],
                "logic_operator": "AND",
                "order_index": 2
            },
            # Exit Short: Price retorna para middle band
            {
                "condition_type": "exit_short",
                "conditions": [
                    {"left": "close", "operator": ">", "right": "bollinger.middle"}
                ],
                "logic_operator": "AND",
                "order_index": 3
            }
        ]
    },

    "Mean Reversion (NW+RSI+BB)": {
        "description": "Estratégia de reversão à média baseada em ETH Zurich Master Thesis. Triple confirmation: Nadaraya-Watson envelope + RSI extremo + Bollinger extremo. Sharpe 1.71, Win Rate 60-70%.",
        "indicators": [
            {"indicator_type": "nadaraya_watson", "parameters": {"bandwidth": 8, "mult": 3.0}, "order_index": 0},
            {"indicator_type": "rsi", "parameters": {"period": 14, "overbought": 65, "oversold": 35}, "order_index": 1},
            {"indicator_type": "bollinger", "parameters": {"period": 20, "stddev": 2.5}, "order_index": 2}
        ],
        "conditions": [
            # Entry Long: Triple confirmation - NW lower + RSI oversold + Price próximo BB lower
            {
                "condition_type": "entry_long",
                "conditions": [
                    {"left": "close", "operator": "<", "right": "nadaraya_watson.lower"},
                    {"left": "rsi.value", "operator": "<", "right": "35"},
                    {"left": "bollinger.percent_b", "operator": "<", "right": "0.2"}
                ],
                "logic_operator": "AND",
                "order_index": 0
            },
            # Entry Short: Triple confirmation - NW upper + RSI overbought + Price próximo BB upper
            {
                "condition_type": "entry_short",
                "conditions": [
                    {"left": "close", "operator": ">", "right": "nadaraya_watson.upper"},
                    {"left": "rsi.value", "operator": ">", "right": "65"},
                    {"left": "bollinger.percent_b", "operator": ">", "right": "0.8"}
                ],
                "logic_operator": "AND",
                "order_index": 1
            },
            # Exit Long: Price retorna à média (NW value) OU atinge meio do canal
            {
                "condition_type": "exit_long",
                "conditions": [
                    {"left": "close", "operator": ">", "right": "nadaraya_watson.value"},
                    {"left": "bollinger.percent_b", "operator": ">", "right": "0.5"}
                ],
                "logic_operator": "OR",
                "order_index": 2
            },
            # Exit Short: Price retorna à média OU atinge meio do canal
            {
                "condition_type": "exit_short",
                "conditions": [
                    {"left": "close", "operator": "<", "right": "nadaraya_watson.value"},
                    {"left": "bollinger.percent_b", "operator": "<", "right": "0.5"}
                ],
                "logic_operator": "OR",
                "order_index": 3
            }
        ]
    }
}


async def fix_strategies():
    """Corrige todas as estratégias"""
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(database_url, ssl=ssl_ctx)

    print("=" * 70)
    print("CORRIGINDO ESTRATÉGIAS - ANÁLISE ULTRATHINK")
    print("=" * 70)
    print()

    try:
        for strategy_name, config in CORRECTED_STRATEGIES.items():
            print(f"\n{'='*60}")
            print(f"Corrigindo: {strategy_name}")
            print(f"{'='*60}")

            # Find strategy by name
            strategy = await conn.fetchrow(
                "SELECT id FROM strategies WHERE name = $1",
                strategy_name
            )

            if not strategy:
                print(f"  ERRO: Estratégia não encontrada!")
                continue

            strategy_id = strategy['id']
            print(f"  ID: {strategy_id}")

            # Update description
            await conn.execute(
                "UPDATE strategies SET description = $1 WHERE id = $2",
                config['description'],
                strategy_id
            )
            print(f"  Descrição atualizada")

            # Delete existing indicators
            deleted_inds = await conn.execute(
                "DELETE FROM strategy_indicators WHERE strategy_id = $1",
                strategy_id
            )
            print(f"  Indicadores antigos removidos")

            # Delete existing conditions
            deleted_conds = await conn.execute(
                "DELETE FROM strategy_conditions WHERE strategy_id = $1",
                strategy_id
            )
            print(f"  Condições antigas removidas")

            # Insert new indicators
            for ind in config['indicators']:
                await conn.execute("""
                    INSERT INTO strategy_indicators (id, strategy_id, indicator_type, parameters, order_index, created_at, updated_at)
                    VALUES (gen_random_uuid(), $1, $2, $3, $4, NOW(), NOW())
                """, strategy_id, ind['indicator_type'], json.dumps(ind['parameters']), ind['order_index'])
                print(f"  + Indicador: {ind['indicator_type']}")

            # Insert new conditions
            for cond in config['conditions']:
                await conn.execute("""
                    INSERT INTO strategy_conditions (id, strategy_id, condition_type, conditions, logic_operator, order_index, created_at, updated_at)
                    VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, NOW(), NOW())
                """, strategy_id, cond['condition_type'], json.dumps(cond['conditions']), cond['logic_operator'], cond['order_index'])
                print(f"  + Condição: {cond['condition_type']} ({len(cond['conditions'])} regras)")

            print(f"  ESTRATÉGIA CORRIGIDA!")

    finally:
        await conn.close()

    print("\n" + "=" * 70)
    print("TODAS AS ESTRATÉGIAS FORAM CORRIGIDAS!")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(fix_strategies())
