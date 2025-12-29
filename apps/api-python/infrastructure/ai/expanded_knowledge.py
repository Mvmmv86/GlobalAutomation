"""
EXPANDED INSTITUTIONAL KNOWLEDGE BASE
=====================================

Conhecimento expandido baseado em:
- BlackRock Aladdin Risk Framework
- Renaissance Technologies / Medallion Fund
- Two Sigma ML Approaches
- On-Chain Analytics (Glassnode, CryptoQuant, Santiment)
- Crypto Market Microstructure
- Academic Research in Quantitative Finance
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
from enum import Enum


# =============================================================================
# BLACKROCK ALADDIN RISK FRAMEWORK (Expanded)
# =============================================================================

class AladdinRiskFramework:
    """
    BlackRock Aladdin Risk Management Framework
    Fonte: BlackRock Investment Institute, Risk Management Whitepapers

    Aladdin (Asset, Liability, Debt and Derivative Investment Network)
    gerencia $21.6 trilhoes em ativos e e o padrao ouro de risk management.
    """

    # Value at Risk (VaR) Parameters
    VAR_CONFIDENCE_LEVELS = {
        "standard": 0.95,      # 95% - padrao regulatorio
        "conservative": 0.99,  # 99% - usado por hedge funds
        "extreme": 0.999       # 99.9% - tail risk
    }

    VAR_TIME_HORIZONS = {
        "intraday": 1,         # 1 dia - trading ativo
        "weekly": 5,           # 5 dias - swing trading
        "monthly": 21,         # 21 dias - position trading
        "quarterly": 63        # 63 dias - institutional
    }

    # Conditional VaR (CVaR) / Expected Shortfall
    CVAR_METHODOLOGY = {
        "description": "Media das perdas alem do VaR - captura tail risk",
        "importance": "CVaR > VaR indica fat tails - comum em crypto",
        "crypto_adjustment": "Em crypto, CVaR tipicamente 1.5-2x o VaR",
        "action": "Se CVaR/VaR > 1.5, reduzir alavancagem em 30%"
    }

    # Stress Testing Scenarios (Aladdin Style)
    STRESS_SCENARIOS = {
        "covid_crash_2020": {
            "description": "Crash de marco 2020 - BTC caiu 50% em 2 dias",
            "btc_drawdown": -50,
            "eth_drawdown": -60,
            "alts_drawdown": -70,
            "duration_days": 30,
            "recovery_days": 150,
            "lesson": "Liquidez seca rapidamente - cash is king"
        },
        "ftx_collapse_2022": {
            "description": "Colapso FTX - contagio sistemico",
            "btc_drawdown": -25,
            "eth_drawdown": -30,
            "alts_drawdown": -50,
            "duration_days": 60,
            "recovery_days": 400,
            "lesson": "Counterparty risk - diversificar exchanges"
        },
        "luna_terra_2022": {
            "description": "Colapso UST/LUNA - desvinculacao de stablecoin",
            "btc_drawdown": -30,
            "eth_drawdown": -40,
            "alts_drawdown": -80,
            "duration_days": 45,
            "recovery_days": 300,
            "lesson": "Algoritmic stablecoins sao arriscadas"
        },
        "china_ban_2021": {
            "description": "China bane mineracao - hash rate crash",
            "btc_drawdown": -55,
            "eth_drawdown": -60,
            "alts_drawdown": -70,
            "duration_days": 90,
            "recovery_days": 180,
            "lesson": "Risco regulatorio e real"
        },
        "flash_crash": {
            "description": "Flash crash tipico - liquidacoes em cascata",
            "btc_drawdown": -30,
            "eth_drawdown": -35,
            "alts_drawdown": -50,
            "duration_days": 1,
            "recovery_days": 7,
            "lesson": "Stop loss amplo para evitar stop hunting"
        }
    }

    # Factor Risk Model
    RISK_FACTORS = {
        "market_beta": {
            "description": "Sensibilidade ao movimento geral do mercado crypto",
            "measurement": "Correlacao com BTC",
            "target": "0.7-0.9 para alts, 1.0 para BTC",
            "action": "Se beta > 1.2, posicao esta amplificando risco"
        },
        "volatility_regime": {
            "description": "Nivel atual de volatilidade vs historico",
            "measurement": "ATR atual / ATR 30d medio",
            "regimes": {
                "low": "< 0.8 - pode aumentar leverage",
                "normal": "0.8-1.2 - manter posicao normal",
                "high": "> 1.2 - reduzir leverage",
                "extreme": "> 2.0 - reduzir 50% exposure"
            }
        },
        "liquidity_risk": {
            "description": "Capacidade de sair de posicao sem impacto",
            "measurement": "Volume 24h / Position Size",
            "thresholds": {
                "safe": "> 100x",
                "caution": "10-100x",
                "danger": "< 10x"
            }
        },
        "concentration_risk": {
            "description": "Risco de ter muito capital em um ativo",
            "max_single_position": "5% do portfolio",
            "max_sector": "20% do portfolio",
            "max_correlated_assets": "30% do portfolio"
        },
        "funding_rate_risk": {
            "description": "Custo de manter posicao futures",
            "neutral": "-0.01% a 0.01% / 8h",
            "expensive_long": "> 0.05% / 8h",
            "expensive_short": "< -0.05% / 8h",
            "action": "Funding alto = mercado lotado nessa direcao"
        }
    }

    # Position Sizing (Aladdin/Kelly Criterion hybrid)
    POSITION_SIZING = {
        "kelly_criterion": {
            "formula": "f* = (p*b - q) / b",
            "explanation": "p=win_rate, q=loss_rate, b=win/loss ratio",
            "crypto_adjustment": "Usar 1/4 Kelly para seguranca",
            "example": "Win rate 55%, Win/Loss 1.5 -> Full Kelly 21.7%, Use 5.4%"
        },
        "volatility_adjusted": {
            "formula": "position = target_risk / (ATR * multiplier)",
            "target_risk_pct": 1.0,
            "atr_multiplier": 2.0
        },
        "max_position_by_volatility": {
            "low_vol": "5% max position",
            "medium_vol": "3% max position",
            "high_vol": "1% max position",
            "extreme_vol": "0.5% max position"
        }
    }


# =============================================================================
# ON-CHAIN ANALYTICS (Glassnode, CryptoQuant, Santiment)
# =============================================================================

class OnChainKnowledge:
    """
    Conhecimento de metricas on-chain para analise institucional
    Fonte: Glassnode Academy, CryptoQuant Research, Santiment Insights
    """

    FUNDAMENTAL_METRICS = {
        "mvrv_ratio": {
            "name": "Market Value to Realized Value",
            "description": "Compara market cap com preco medio de aquisicao de todas as moedas",
            "interpretation": {
                "< 1.0": "Mercado em prejuizo medio - zona de acumulacao",
                "1.0-2.0": "Mercado em lucro moderado - neutro",
                "2.0-3.5": "Mercado em lucro significativo - cautela",
                "> 3.5": "Euforia - topo historico provavel"
            },
            "signal": "MVRV < 1 = compra forte, MVRV > 3 = considerar venda",
            "source": "Glassnode"
        },
        "sopr": {
            "name": "Spent Output Profit Ratio",
            "description": "Ratio de lucro/prejuizo das moedas movidas",
            "interpretation": {
                "< 1.0": "Holders vendendo em prejuizo - capitulacao",
                "= 1.0": "Break-even - suporte/resistencia psicologico",
                "> 1.0": "Holders vendendo em lucro - realizacao"
            },
            "signal": "SOPR < 0.95 por varios dias = fundo provavel",
            "source": "Glassnode"
        },
        "nvt_ratio": {
            "name": "Network Value to Transactions",
            "description": "P/E ratio do Bitcoin - market cap / volume transacionado",
            "interpretation": {
                "< 40": "Rede subvalorizada - bullish",
                "40-65": "Valor justo",
                "> 65": "Rede supervalorizada - bearish"
            },
            "signal": "NVT signal (90d MA) mais confiavel que raw",
            "source": "Willy Woo / CryptoQuant"
        },
        "puell_multiple": {
            "name": "Puell Multiple",
            "description": "Revenue diario de mineradores / media 365d",
            "interpretation": {
                "< 0.5": "Mineradores em stress - fundo historico",
                "0.5-1.0": "Mineradores em dificuldade - acumulacao",
                "1.0-4.0": "Normal",
                "> 4.0": "Mineradores em euforia - topo provavel"
            },
            "signal": "Puell < 0.5 = melhor momento para comprar historicamente",
            "source": "Glassnode"
        },
        "stablecoin_supply_ratio": {
            "name": "SSR - Stablecoin Supply Ratio",
            "description": "BTC market cap / Total stablecoin supply",
            "interpretation": {
                "Baixo (< 5)": "Muito buying power disponivel - bullish",
                "Alto (> 15)": "Pouco buying power - bearish ou topo"
            },
            "signal": "SSR baixo + sentimento negativo = setup ideal",
            "source": "CryptoQuant"
        },
        "reserve_risk": {
            "name": "Reserve Risk",
            "description": "Confianca dos hodlers vs preco",
            "interpretation": {
                "< 0.002": "Excelente momento para comprar",
                "0.002-0.008": "Zona neutra",
                "> 0.008": "Considerar vender"
            },
            "source": "Glassnode"
        }
    }

    WHALE_METRICS = {
        "exchange_whale_ratio": {
            "description": "Depositos de whales vs total de depositos",
            "interpretation": {
                "< 0.4": "Whales nao estao vendendo - bullish",
                "0.4-0.6": "Atividade normal",
                "> 0.6": "Whales depositando para vender - bearish"
            }
        },
        "whale_transaction_count": {
            "description": "Numero de transacoes > $1M",
            "signal": "Aumento repentino = movimentacao institucional"
        },
        "exchange_netflow": {
            "description": "Entradas - Saidas de exchanges",
            "interpretation": {
                "Positivo": "Mais depositos = pressao vendedora",
                "Negativo": "Mais saques = acumulacao"
            },
            "signal": "Netflow negativo consistente = bullish"
        },
        "miners_position_index": {
            "description": "Posicao net dos mineradores",
            "interpretation": {
                "< 0": "Mineradores acumulando - bullish",
                "> 0": "Mineradores distribuindo - bearish"
            }
        },
        "long_term_holder_supply": {
            "description": "Supply held by LTH (>155 days)",
            "interpretation": {
                "Aumentando": "Acumulacao - bullish",
                "Diminuindo": "Distribuicao - bearish"
            }
        }
    }

    SENTIMENT_METRICS = {
        "fear_greed_index": {
            "description": "Indice de medo e ganancia (0-100)",
            "interpretation": {
                "0-25": "Extreme Fear - historicamente bom para comprar",
                "25-45": "Fear - considerar compras graduais",
                "45-55": "Neutral",
                "55-75": "Greed - cautela",
                "75-100": "Extreme Greed - historicamente ruim para comprar"
            },
            "contrarian_signal": "Compre quando outros tem medo, venda quando tem ganancia"
        },
        "funding_rates_sentiment": {
            "description": "Funding rates agregado de todas exchanges",
            "interpretation": {
                "Muito positivo (> 0.1%)": "Mercado muito long - correcao provavel",
                "Positivo moderado": "Bullish saudavel",
                "Negativo": "Mercado short - squeeze possivel"
            }
        },
        "open_interest_change": {
            "description": "Mudanca em posicoes abertas de futuros",
            "signal": "OI subindo + preco subindo = tendencia forte"
        },
        "long_short_ratio": {
            "description": "Ratio de posicoes long vs short",
            "interpretation": {
                "> 2.0": "Muito bullish - risco de long squeeze",
                "< 0.5": "Muito bearish - risco de short squeeze"
            }
        },
        "social_volume": {
            "description": "Mencoes em redes sociais",
            "interpretation": {
                "Spike repentino": "Pode indicar pump and dump",
                "Aumento gradual": "Interesse organico"
            }
        }
    }


# =============================================================================
# RENAISSANCE TECHNOLOGIES / TWO SIGMA METHODOLOGIES
# =============================================================================

class QuantHedgeFundMethods:
    """
    Metodologias usadas pelos maiores hedge funds quantitativos
    Fonte: Publicacoes academicas, entrevistas, analise de patentes
    """

    RENAISSANCE_PRINCIPLES = {
        "statistical_significance": {
            "description": "Medallion exige significancia estatistica extrema",
            "requirements": {
                "min_t_statistic": 3.0,
                "min_observations": 1000,
                "out_of_sample_validation": "Obrigatorio",
                "walk_forward_periods": 12
            },
            "key_insight": "Se nao for estatisticamente significante, nao e uma edge"
        },
        "transaction_costs": {
            "description": "Modelagem realista de custos e crucial",
            "components": {
                "exchange_fees": "0.02-0.1% maker/taker",
                "slippage": "0.05-0.5% dependendo do tamanho",
                "funding_costs": "Variavel - pode ser 30%+ anual",
                "spread": "0.01-0.1% dependendo do ativo"
            },
            "rule": "Estrategia deve ser lucrativa com 2x os custos estimados"
        },
        "alpha_decay": {
            "description": "Edges perdem eficacia com o tempo",
            "typical_halflife": "6-18 meses para estrategias publicas",
            "action": "Monitorar degradacao, ter pipeline de novas estrategias"
        },
        "diversification": {
            "description": "Medallion roda milhares de estrategias simultaneamente",
            "retail_adaptation": "Minimo 5 estrategias descorrelacionadas",
            "correlation_target": "< 0.3 entre estrategias"
        },
        "data_quality": {
            "description": "Dados limpos sao essenciais",
            "requirements": [
                "Remover outliers suspeitos",
                "Ajustar para splits/dividendos",
                "Verificar timestamp accuracy",
                "Cross-validate com multiplas fontes"
            ]
        }
    }

    TWO_SIGMA_ML_APPROACH = {
        "feature_engineering": {
            "description": "Criar features preditivas de dados raw",
            "examples": [
                "Momentum normalizado por volatilidade",
                "Desvio da media movel em unidades de ATR",
                "Ratio de volume atual vs media",
                "Skewness dos retornos ultimos N periodos",
                "Correlacao rolling com BTC",
                "Z-score de funding rates",
                "Divergencia RSI vs preco"
            ]
        },
        "model_validation": {
            "description": "Validacao rigorosa para evitar overfitting",
            "techniques": [
                "Time-series cross validation (nao random split!)",
                "Walk-forward optimization",
                "Purged K-fold (gap entre train/test)",
                "Combinatorial purged CV",
                "Monte Carlo permutation tests"
            ],
            "red_flags": [
                "Sharpe muito alto (> 3) no backtest",
                "Performance degrada significativamente OOS",
                "Muitos parametros vs observacoes",
                "Features olham para o futuro (lookahead bias)",
                "Resultados sensiveis a pequenas mudancas"
            ]
        },
        "ensemble_methods": {
            "description": "Combinar multiplos modelos reduz risco",
            "approaches": [
                "Voting entre modelos",
                "Stacking (meta-model)",
                "Bagging para reducao de variancia",
                "Signal averaging"
            ]
        }
    }

    BACKTESTING_BIASES = {
        "survivorship_bias": {
            "description": "Testar apenas em ativos que sobreviveram",
            "impact": "Infla retornos em 1-3% anual",
            "solution": "Incluir ativos delisted no backtest"
        },
        "lookahead_bias": {
            "description": "Usar informacao que nao estava disponivel",
            "examples": [
                "Usar high/low do dia para calcular indicador",
                "Point-in-time data vs dados revisados",
                "Usar preco de fechamento antes de fechar"
            ],
            "solution": "Usar apenas dados disponiveis no momento"
        },
        "selection_bias": {
            "description": "Escolher periodo de teste favoravel",
            "solution": "Testar em multiplos periodos, incluir bear markets"
        },
        "overfitting": {
            "description": "Estrategia funciona apenas nos dados de teste",
            "detection": [
                "Muitos parametros otimizados",
                "Performance muito diferente in/out of sample",
                "Sensivel a pequenas mudancas de parametros",
                "Curva de equity muito suave"
            ],
            "solution": "Walk-forward analysis, cross-validation, simplificar"
        },
        "data_snooping": {
            "description": "Testar muitas estrategias ate achar uma que funciona",
            "impact": "1 em 20 estrategias sera 'significante' por acaso",
            "solution": "Ajustar p-value para multiplas comparacoes (Bonferroni)"
        }
    }


# =============================================================================
# CRYPTO MARKET MICROSTRUCTURE
# =============================================================================

class CryptoMarketStructure:
    """
    Conhecimento sobre microestrutura de mercados crypto
    Essencial para execucao profissional
    """

    EXCHANGE_KNOWLEDGE = {
        "binance": {
            "type": "CEX - Maior volume",
            "strengths": ["Liquidez", "Variedade de pares", "Ferramentas"],
            "weaknesses": ["Regulatorio", "Historico de hacks"],
            "maker_fee": 0.02,
            "taker_fee": 0.04,
            "funding_interval": "8h",
            "max_leverage": 125,
            "volume_rank": 1
        },
        "bybit": {
            "type": "CEX - Derivativos",
            "strengths": ["Interface", "Copy trading", "Baixas taxas"],
            "weaknesses": ["Menos pares que Binance"],
            "maker_fee": 0.01,
            "taker_fee": 0.06,
            "funding_interval": "8h",
            "max_leverage": 100,
            "volume_rank": 2
        },
        "okx": {
            "type": "CEX - All-in-one",
            "strengths": ["Variedade produtos", "Web3 wallet"],
            "weaknesses": ["UX complexa"],
            "maker_fee": 0.02,
            "taker_fee": 0.05,
            "volume_rank": 3
        },
        "coinbase": {
            "type": "CEX - Institucional",
            "strengths": ["Regulado", "Custody", "Confiavel"],
            "weaknesses": ["Taxas altas", "Menos pares"],
            "maker_fee": 0.04,
            "taker_fee": 0.06,
            "volume_rank": 4
        },
        "dex_aggregators": {
            "type": "DEX",
            "examples": ["1inch", "Jupiter", "Paraswap"],
            "strengths": ["Descentralizado", "Sem KYC", "Self-custody"],
            "weaknesses": ["Slippage", "Gas fees", "MEV"],
            "consideration": "Usar para tokens nao listados em CEX"
        }
    }

    LIQUIDITY_ANALYSIS = {
        "order_book_depth": {
            "description": "Quantidade de ordens em cada nivel de preco",
            "healthy_market": "Bid/Ask depth similar",
            "warning_signs": [
                "Gaps grandes no order book",
                "Spoofing (ordens que somem)",
                "Thin order book em um lado",
                "Imbalance > 3:1 bid/ask"
            ]
        },
        "volume_profile": {
            "description": "Onde ocorreu mais volume historicamente",
            "use": "Identificar suportes/resistencias reais",
            "signal": "High volume nodes = areas de interesse institucional"
        },
        "slippage_estimation": {
            "formula": "slippage = order_size / (bid_ask_depth * 0.1)",
            "rule": "Se slippage > 0.5%, dividir ordem ou usar TWAP"
        },
        "spread_analysis": {
            "description": "Diferenca entre melhor bid e ask",
            "healthy": "< 0.05% para majors",
            "concerning": "> 0.2%",
            "action": "Spread alto = usar limit orders"
        }
    }

    MARKET_MANIPULATION = {
        "wash_trading": {
            "description": "Volume falso para inflar metricas",
            "detection": "Volume sem impacto no preco",
            "prevalence": "Comum em exchanges menores e altcoins",
            "protection": "Usar apenas exchanges top 10"
        },
        "pump_and_dump": {
            "description": "Compra coordenada seguida de venda",
            "warning_signs": [
                "Volume subito em altcoin pequena",
                "Shilling em redes sociais",
                "Gap entre spot e futures price",
                "Grupos de Telegram/Discord suspeitos"
            ],
            "protection": "Evitar altcoins com market cap < $100M"
        },
        "stop_hunting": {
            "description": "Mover preco para acionar stops e depois reverter",
            "common_zones": ["Round numbers", "Recent highs/lows", "MA levels"],
            "protection": "Stop loss em ATR, nao em valores fixos"
        },
        "whale_manipulation": {
            "description": "Grandes players movendo mercado",
            "detection": [
                "Grandes depositos em exchanges",
                "Ordens iceberg",
                "Divergencia preco/OI",
                "Spoofing no order book"
            ],
            "strategy": "Seguir whales, nao lutar contra"
        },
        "front_running": {
            "description": "Ver ordem grande e executar antes",
            "types": ["Exchange front-running", "MEV em DEX"],
            "protection": "Usar private RPCs, MEV protection"
        }
    }

    FUNDING_RATE_STRATEGIES = {
        "cash_and_carry": {
            "description": "Long spot + short perp para capturar funding",
            "expected_return": "5-30% APY dependendo do funding",
            "risks": ["Liquidation if funding inverts", "Exchange risk"],
            "when_to_use": "Funding > 0.03% consistentemente"
        },
        "funding_arbitrage": {
            "description": "Long em exchange com funding baixo, short em alta",
            "complexity": "Alta - requer capital em multiplas exchanges",
            "return": "3-15% APY"
        },
        "contrarian_funding": {
            "description": "Ir contra funding extremo",
            "signal": "Funding > 0.1% = considerar short, < -0.05% = considerar long",
            "caution": "Funding pode ficar extremo por mais tempo"
        }
    }


# =============================================================================
# ADVANCED TRADING CONCEPTS
# =============================================================================

class AdvancedTradingConcepts:
    """
    Conceitos avancados de trading institucional
    """

    PORTFOLIO_OPTIMIZATION = {
        "mean_variance": {
            "description": "Markowitz - maximizar retorno para dado risco",
            "limitation": "Assume distribuicao normal - errado para crypto",
            "crypto_alternative": "Usar CVaR em vez de variancia"
        },
        "risk_parity": {
            "description": "Alocar para que cada ativo contribua igual ao risco",
            "formula": "weight_i = (1/vol_i) / sum(1/vol_j)",
            "benefit": "Diversificacao real, nao apenas por capital"
        },
        "black_litterman": {
            "description": "Combinar views do investidor com equilibrio de mercado",
            "use_case": "Quando tem convicao em certos ativos"
        },
        "hierarchical_risk_parity": {
            "description": "Clusters de ativos por correlacao, risk parity dentro",
            "benefit": "Melhor diversificacao que risk parity tradicional"
        }
    }

    REGIME_DETECTION = {
        "hmm": {
            "name": "Hidden Markov Models",
            "description": "Detecta mudancas de regime de forma probabilistica",
            "states": ["Bull", "Bear", "Sideways", "High Vol"],
            "used_by": "Renaissance Technologies"
        },
        "simple_rules": {
            "bull": "200 EMA up + ADX > 25 + price > 200 EMA",
            "bear": "200 EMA down + ADX > 25 + price < 200 EMA",
            "sideways": "ADX < 20 + price crossing 200 EMA repeatedly",
            "high_vol": "ATR > 2x ATR(30)"
        },
        "action_per_regime": {
            "bull": "Trend following, higher leverage OK, buy dips",
            "bear": "Reduce exposure, short or hedge, avoid alts",
            "sideways": "Mean reversion, reduce size, range trade",
            "high_vol": "Cut leverage 50%, widen stops, reduce size"
        }
    }

    EXECUTION_ALGORITHMS = {
        "twap": {
            "name": "Time Weighted Average Price",
            "description": "Dividir ordem em partes iguais ao longo do tempo",
            "use_case": "Ordens grandes, evitar impacto de mercado",
            "implementation": "1 ordem a cada X minutos"
        },
        "vwap": {
            "name": "Volume Weighted Average Price",
            "description": "Executar proporcionalmente ao volume",
            "use_case": "Seguir padrao de volume do mercado"
        },
        "iceberg": {
            "name": "Iceberg Orders",
            "description": "Mostrar apenas parte da ordem no book",
            "use_case": "Esconder tamanho real da posicao"
        },
        "sniper": {
            "name": "Sniper/DCA Bot",
            "description": "Comprar em dips automaticamente",
            "use_case": "Acumulacao de longo prazo"
        }
    }

    CORRELATION_DYNAMICS = {
        "btc_dominance": {
            "description": "% do market cap total que e BTC",
            "interpretation": {
                "Rising (> 50%)": "Risk-off, money flowing to BTC",
                "Falling (< 45%)": "Alt season, risk-on"
            },
            "current_levels": {
                "high": "> 55%",
                "normal": "45-55%",
                "low": "< 45%"
            }
        },
        "eth_btc_ratio": {
            "description": "Strength of ETH vs BTC",
            "interpretation": {
                "Rising": "DeFi/L2 narrative strong, alts bullish",
                "Falling": "BTC-only accumulation, risk-off"
            }
        },
        "crypto_stock_correlation": {
            "current_state": "Alta correlacao com NASDAQ desde 2020",
            "implication": "Crypto nao e mais descorrelacionado",
            "macro_factors": ["Fed policy", "DXY", "Risk appetite", "Liquidity"]
        },
        "correlation_breakdown": {
            "description": "Em stress, correlacoes vao para 1",
            "implication": "Diversificacao falha quando mais precisa",
            "protection": "Ter cash/stables, usar opcoes, reduce exposure"
        },
        "sector_correlations": {
            "l1_blockchains": "Alta correlacao entre ETH, SOL, AVAX",
            "defi": "Correlacionados com ETH + gas fees",
            "memecoins": "Altamente correlacionados entre si",
            "ai_tokens": "Novo setor - correlacao ainda formando"
        }
    }

    RISK_MANAGEMENT_ADVANCED = {
        "tail_risk_hedging": {
            "description": "Protecao contra eventos extremos",
            "instruments": ["Options (puts)", "Short futures", "Cash reserve"],
            "cost": "1-3% do portfolio anualmente"
        },
        "delta_hedging": {
            "description": "Neutralizar exposicao direcional",
            "use_case": "Quando quer exposure apenas a volatilidade"
        },
        "portfolio_insurance": {
            "description": "Stop loss no portfolio inteiro",
            "implementation": "Reduzir exposure quando portfolio cai X%",
            "levels": {
                "5% drawdown": "Review positions",
                "10% drawdown": "Reduce leverage by 50%",
                "20% drawdown": "Exit all positions",
                "25% drawdown": "Pause trading"
            }
        }
    }


# =============================================================================
# RESEARCH SOURCES AND UPDATES
# =============================================================================

RESEARCH_SOURCES = {
    "on_chain": [
        {"name": "Glassnode", "url": "glassnode.com", "focus": "On-chain analytics", "quality": "Excellent"},
        {"name": "CryptoQuant", "url": "cryptoquant.com", "focus": "Exchange flows", "quality": "Excellent"},
        {"name": "Santiment", "url": "santiment.net", "focus": "Social + on-chain", "quality": "Good"},
        {"name": "IntoTheBlock", "url": "intotheblock.com", "focus": "ML on-chain", "quality": "Good"},
        {"name": "Nansen", "url": "nansen.ai", "focus": "Smart money tracking", "quality": "Excellent"}
    ],
    "macro_research": [
        {"name": "Messari", "url": "messari.io", "focus": "Crypto research", "quality": "Excellent"},
        {"name": "Delphi Digital", "url": "delphidigital.io", "focus": "Deep dives", "quality": "Excellent"},
        {"name": "The Block", "url": "theblock.co", "focus": "Data + news", "quality": "Good"},
        {"name": "Blockworks", "url": "blockworks.co", "focus": "Institutional", "quality": "Good"}
    ],
    "quant_papers": [
        {"name": "SSRN", "focus": "Academic papers on trading"},
        {"name": "arXiv q-fin", "focus": "Quantitative finance papers"},
        {"name": "Journal of Finance", "focus": "Peer-reviewed research"},
        {"name": "Journal of Portfolio Management", "focus": "Institutional strategies"}
    ],
    "institutional": [
        {"name": "PwC Crypto HF Report", "annual": True, "focus": "Industry overview"},
        {"name": "Bitwise Asset Management", "focus": "Institutional analysis"},
        {"name": "Grayscale Research", "focus": "Market reports"},
        {"name": "Fidelity Digital Assets", "focus": "Institutional perspective"},
        {"name": "Galaxy Digital Research", "focus": "Deep research"}
    ],
    "real_time_data": [
        {"name": "TradingView", "focus": "Charts and indicators"},
        {"name": "Coinglass", "focus": "Derivatives data"},
        {"name": "Laevitas", "focus": "Options data"},
        {"name": "Kaiko", "focus": "Institutional data"}
    ]
}


# =============================================================================
# INTEGRATION WITH MAIN KNOWLEDGE BASE
# =============================================================================

def get_expanded_knowledge():
    """Returns all expanded knowledge classes"""
    return {
        "aladdin_framework": AladdinRiskFramework,
        "onchain": OnChainKnowledge,
        "quant_methods": QuantHedgeFundMethods,
        "market_structure": CryptoMarketStructure,
        "advanced_concepts": AdvancedTradingConcepts,
        "research_sources": RESEARCH_SOURCES
    }
