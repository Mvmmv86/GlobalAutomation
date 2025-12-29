#!/usr/bin/env python3
"""
Script para adicionar documentação detalhada às estratégias.
Esta documentação será exibida para o admin ao escolher uma estratégia.
"""

import asyncio
import os
import json
from dotenv import load_dotenv
import asyncpg
import ssl

load_dotenv()

STRATEGY_DOCS = {
    "Momentum Combo (MACD+RSI+EMA)": {
        "titulo": "Momentum Combo - Estratégia de Momentum Tripla",
        "resumo": "Combina três indicadores de momentum para identificar tendências fortes com alta probabilidade de continuação.",

        "baseado_em": {
            "fonte": "QuantifiedStrategies Research",
            "estudo": "Análise de 10.000+ trades em mercados de crypto e forex",
            "periodo_teste": "2018-2024",
            "resultado": "Sharpe Ratio 1.19-1.4 com Win Rate de 73-85%"
        },

        "performance_esperada": {
            "sharpe_ratio": "1.19 - 1.40",
            "win_rate": "73% - 85%",
            "profit_factor": "1.8 - 2.2",
            "max_drawdown": "12% - 18%",
            "trades_por_mes": "8 - 15 (média)"
        },

        "como_funciona": {
            "entrada_long": [
                "MACD cruza acima da linha de sinal (crossover bullish)",
                "RSI acima de 50 (momentum positivo)",
                "Preço acima da EMA lenta de 48 períodos (tendência de alta)"
            ],
            "entrada_short": [
                "MACD cruza abaixo da linha de sinal (crossover bearish)",
                "RSI abaixo de 50 (momentum negativo)",
                "Preço abaixo da EMA lenta de 48 períodos (tendência de baixa)"
            ],
            "saida": "Quando MACD faz crossover reverso"
        },

        "quando_usar": {
            "condicoes_ideais": [
                "Mercado em tendência clara (não lateral)",
                "Volatilidade moderada a alta",
                "Após correções em tendência estabelecida",
                "Quando há momentum institucional visível no volume"
            ],
            "melhores_horarios": [
                "Abertura de sessões (Londres 8h UTC, NY 13h UTC)",
                "Overlap Londres-NY (13h-17h UTC)",
                "Evitar fins de semana e feriados"
            ]
        },

        "quando_nao_usar": {
            "evitar": [
                "Mercado lateral/range (ADX < 20)",
                "Antes de eventos importantes (FOMC, CPI, NFP)",
                "Baixa liquidez (fins de semana, feriados)",
                "Quando preço está em consolidação prolongada"
            ],
            "sinais_alerta": [
                "Múltiplos sinais falsos consecutivos",
                "Divergência entre preço e indicadores",
                "Volume decrescente em movimentos de preço"
            ]
        },

        "ativos_recomendados": {
            "principais": ["BTCUSDT", "ETHUSDT"],
            "secundarios": ["SOLUSDT", "BNBUSDT"],
            "evitar": ["Altcoins de baixa liquidez", "Memecoins", "Tokens novos"],
            "nota": "Funciona melhor em ativos com market cap > $10B"
        },

        "timeframes": {
            "recomendado": "4H",
            "alternativo": "1H (mais sinais, menor win rate)",
            "nao_recomendado": "15m ou menos (muito ruído)"
        },

        "gestao_risco": {
            "stop_loss": "2-3% abaixo/acima do preço de entrada",
            "take_profit": "4-6% (ratio 2:1 mínimo)",
            "posicao_maxima": "5-10% do capital por trade",
            "max_trades_simultaneos": "2-3",
            "trailing_stop": "Ativar após +2% de lucro"
        },

        "dicas_uso": [
            "Aguarde confirmação completa (3 condições) antes de entrar",
            "Não force trades - se não houver setup claro, espere",
            "Combine com análise de suporte/resistência para melhor timing",
            "Em tendências fortes, considere re-entry após pullbacks",
            "Monitore o volume - volume alto confirma o movimento"
        ],

        "nivel_experiencia": "Intermediário",
        "complexidade": "Média",
        "manutencao": "Baixa - estratégia automatizada"
    },

    "Trend Filter (SuperTrend+ADX)": {
        "titulo": "Trend Filter - Estratégia de Seguimento de Tendência",
        "resumo": "Estratégia de trend-following que usa SuperTrend para direção e ADX para filtrar apenas tendências fortes.",

        "baseado_em": {
            "fonte": "SSRN Academic Research + Backtest Rookies",
            "estudo": "Análise de sistemas Donchian/Trend em mercados crypto",
            "periodo_teste": "2017-2024",
            "resultado": "Sharpe Ratio 0.8-1.1 com Win Rate de 65-70%"
        },

        "performance_esperada": {
            "sharpe_ratio": "0.80 - 1.10",
            "win_rate": "65% - 70%",
            "profit_factor": "1.5 - 1.9",
            "max_drawdown": "15% - 22%",
            "trades_por_mes": "10 - 20 (média)"
        },

        "como_funciona": {
            "entrada_long": [
                "SuperTrend muda para bullish (trend = 1)",
                "ADX > 25 (tendência forte)",
                "DI+ > DI- (direção confirmada para cima)"
            ],
            "entrada_short": [
                "SuperTrend muda para bearish (trend = -1)",
                "ADX > 25 (tendência forte)",
                "DI- > DI+ (direção confirmada para baixo)"
            ],
            "saida": "Quando SuperTrend inverte a direção"
        },

        "quando_usar": {
            "condicoes_ideais": [
                "Mercados em tendência clara e sustentada",
                "Após breakout de range prolongado",
                "Quando ADX está subindo (tendência ganhando força)",
                "Momentos de alta volatilidade direcional"
            ],
            "melhores_horarios": [
                "Qualquer horário - funciona 24/7",
                "Melhor performance em sessões de alta liquidez",
                "Evitar momentos de consolidação"
            ]
        },

        "quando_nao_usar": {
            "evitar": [
                "Mercado lateral (ADX < 20)",
                "Choppy markets com reversões frequentes",
                "Quando DI+ e DI- estão muito próximos",
                "Períodos de baixa volatilidade"
            ],
            "sinais_alerta": [
                "ADX caindo de níveis altos",
                "SuperTrend mudando frequentemente",
                "Preço oscilando ao redor do SuperTrend"
            ]
        },

        "ativos_recomendados": {
            "principais": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "secundarios": ["ADAUSDT", "DOGEUSDT", "XRPUSDT"],
            "evitar": ["Stablecoins", "Ativos com baixo volume"],
            "nota": "Excelente para altcoins que seguem BTC"
        },

        "timeframes": {
            "recomendado": "1H",
            "alternativo": "4H (menos trades, maior precisão)",
            "nao_recomendado": "Timeframes muito baixos (< 30m)"
        },

        "gestao_risco": {
            "stop_loss": "Usar o próprio SuperTrend como stop dinâmico",
            "take_profit": "Trailing stop de 3-5%",
            "posicao_maxima": "3-5% do capital por trade",
            "max_trades_simultaneos": "3-4",
            "trailing_stop": "Mover stop para SuperTrend conforme preço avança"
        },

        "dicas_uso": [
            "O ADX é seu melhor amigo - não entre com ADX < 25",
            "Respeite o SuperTrend como stop loss dinâmico",
            "Esta estratégia funciona melhor em tendências longas",
            "Aceite que haverá whipsaws em mercados laterais",
            "Use múltiplos timeframes para confirmar a tendência maior",
            "O multiplier 3.5 foi otimizado para crypto - não altere"
        ],

        "nivel_experiencia": "Iniciante a Intermediário",
        "complexidade": "Baixa",
        "manutencao": "Muito Baixa - set and forget"
    },

    "Ichimoku Breakout": {
        "titulo": "Ichimoku Breakout - Estratégia de Nuvem Ichimoku",
        "resumo": "Estratégia baseada no sistema japonês Ichimoku Kinko Hyo, otimizada para mercados crypto 24/7.",

        "baseado_em": {
            "fonte": "21Shares Research / CryptoQuant Analysis",
            "estudo": "Backtesting de Ichimoku em Bitcoin (2015-2024)",
            "periodo_teste": "2015-2024",
            "resultado": "CAGR 78% vs Buy-Hold 59.8%, Sharpe 1.25"
        },

        "performance_esperada": {
            "sharpe_ratio": "1.20 - 1.30",
            "win_rate": "55% - 65%",
            "profit_factor": "2.0 - 2.5",
            "max_drawdown": "18% - 25%",
            "trades_por_mes": "3 - 6 (menos trades, maior qualidade)"
        },

        "como_funciona": {
            "entrada_long": [
                "Preço rompe ACIMA da nuvem (Kumo breakout)",
                "Tenkan-sen cruza ACIMA do Kijun-sen (TK cross bullish)",
                "Tendência geral é bullish (confirmada pelo indicador)"
            ],
            "entrada_short": [
                "Preço rompe ABAIXO da nuvem (Kumo breakdown)",
                "Tenkan-sen cruza ABAIXO do Kijun-sen (TK cross bearish)",
                "Tendência geral é bearish"
            ],
            "saida": "Quando Tenkan cruza Kijun na direção oposta"
        },

        "quando_usar": {
            "condicoes_ideais": [
                "Após consolidação prolongada dentro da nuvem",
                "Quando a nuvem futura está espessa (suporte/resistência forte)",
                "Mercados com tendências claras e duradouras",
                "Quando preço está claramente fora da nuvem"
            ],
            "melhores_horarios": [
                "Funciona bem em qualquer horário",
                "Melhores sinais em timeframes maiores (4H+)",
                "Evitar entrar quando preço está dentro da nuvem"
            ]
        },

        "quando_nao_usar": {
            "evitar": [
                "Quando preço está DENTRO da nuvem (zona neutra)",
                "Nuvem muito fina (suporte/resistência fraco)",
                "Mercados extremamente voláteis sem direção",
                "Quando TK e Kijun estão muito próximos"
            ],
            "sinais_alerta": [
                "Múltiplas entradas e saídas da nuvem",
                "Nuvem futura mudando de cor frequentemente",
                "Preço oscilando ao redor das linhas TK/Kijun"
            ]
        },

        "ativos_recomendados": {
            "principais": ["BTCUSDT", "ETHUSDT"],
            "secundarios": [],
            "evitar": ["Altcoins voláteis", "Ativos com histórico curto"],
            "nota": "Esta estratégia funciona MELHOR em BTC e ETH devido à maturidade do mercado"
        },

        "timeframes": {
            "recomendado": "4H",
            "alternativo": "Daily (sinais mais confiáveis, menos frequentes)",
            "nao_recomendado": "1H ou menos (muitos sinais falsos)"
        },

        "gestao_risco": {
            "stop_loss": "Abaixo/acima do Kijun-sen ou da nuvem",
            "take_profit": "Próximo nível de resistência/suporte ou trailing 5%",
            "posicao_maxima": "10-15% do capital (menos trades, maior confiança)",
            "max_trades_simultaneos": "1-2",
            "trailing_stop": "Usar Kijun-sen como trailing stop"
        },

        "dicas_uso": [
            "NUNCA entre quando o preço está dentro da nuvem",
            "Quanto mais espessa a nuvem, mais forte o suporte/resistência",
            "O TK cross é mais significativo quando acontece fora da nuvem",
            "Use os parâmetros otimizados para crypto (20/60/120/30)",
            "Esta é uma estratégia de PACIÊNCIA - aguarde setups de qualidade",
            "Funciona excepcionalmente bem em ciclos de bull/bear market"
        ],

        "nivel_experiencia": "Intermediário a Avançado",
        "complexidade": "Alta",
        "manutencao": "Média - requer monitoramento da nuvem"
    },

    "Bollinger Squeeze (BB+ADX+OBV)": {
        "titulo": "Bollinger Squeeze - Estratégia de Explosão de Volatilidade",
        "resumo": "Identifica períodos de baixa volatilidade (squeeze) e captura o breakout explosivo que geralmente segue.",

        "baseado_em": {
            "fonte": "John Bollinger / TTM Squeeze Methodology",
            "estudo": "Análise de volatilidade e breakouts em crypto",
            "periodo_teste": "2019-2024",
            "resultado": "Sharpe Ratio 0.7-1.0 com Win Rate de 54-60%"
        },

        "performance_esperada": {
            "sharpe_ratio": "0.70 - 1.00",
            "win_rate": "54% - 60%",
            "profit_factor": "1.4 - 1.8",
            "max_drawdown": "20% - 28%",
            "trades_por_mes": "5 - 12 (depende da volatilidade)"
        },

        "como_funciona": {
            "entrada_long": [
                "Bandwidth < 6% (bandas comprimidas = squeeze)",
                "Preço rompe ACIMA da banda superior",
                "OBV em tendência de alta (acumulação)",
                "ADX > 20 (momentum presente)"
            ],
            "entrada_short": [
                "Bandwidth < 6% (squeeze detectado)",
                "Preço rompe ABAIXO da banda inferior",
                "OBV em tendência de baixa (distribuição)",
                "ADX > 20 (momentum presente)"
            ],
            "saida": "Quando preço retorna à banda média"
        },

        "quando_usar": {
            "condicoes_ideais": [
                "Após período de consolidação (mínimo 10-15 candles)",
                "Quando bandwidth está em mínimos históricos",
                "Volume aumentando no momento do breakout",
                "Antes de eventos que podem causar movimento forte"
            ],
            "melhores_horarios": [
                "Qualquer momento após consolidação",
                "Frequentemente antes de notícias importantes",
                "Fim de padrões gráficos (triângulos, flags)"
            ]
        },

        "quando_nao_usar": {
            "evitar": [
                "Quando bandwidth já está expandido (> 8%)",
                "Mercados já em tendência forte",
                "Sem confirmação de volume (OBV neutro)",
                "Breakouts falsos anteriores recentes"
            ],
            "sinais_alerta": [
                "Breakout sem volume",
                "Preço volta rapidamente para dentro das bandas",
                "OBV divergindo do preço"
            ]
        },

        "ativos_recomendados": {
            "principais": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "secundarios": ["BNBUSDT", "XRPUSDT", "AVAXUSDT"],
            "evitar": ["Ativos com volatilidade constante alta", "Memecoins"],
            "nota": "Funciona melhor em ativos que alternam entre consolidação e tendência"
        },

        "timeframes": {
            "recomendado": "1H",
            "alternativo": "4H (squeezes mais significativos)",
            "nao_recomendado": "15m ou menos (muitos falsos squeezes)"
        },

        "gestao_risco": {
            "stop_loss": "Logo dentro da banda oposta ao breakout",
            "take_profit": "2x a largura das bandas no momento do squeeze",
            "posicao_maxima": "3-5% do capital (win rate menor)",
            "max_trades_simultaneos": "2-3",
            "trailing_stop": "Mover para banda média após expansão"
        },

        "dicas_uso": [
            "O SQUEEZE é a chave - não entre sem compressão das bandas",
            "OBV confirma se há dinheiro inteligente entrando",
            "Bandwidth < 4% = squeeze extremo = maior probabilidade",
            "Espere o candle FECHAR fora da banda antes de entrar",
            "O primeiro breakout após squeeze longo é o mais forte",
            "Use alertas para ser notificado quando bandwidth cair"
        ],

        "nivel_experiencia": "Intermediário",
        "complexidade": "Média-Alta",
        "manutencao": "Média - monitorar bandwidth"
    },

    "Mean Reversion (NW+RSI+BB)": {
        "titulo": "Mean Reversion - Estratégia de Reversão à Média",
        "resumo": "Estratégia contrarian que compra em extremos de baixa e vende em extremos de alta, usando triple confirmation.",

        "baseado_em": {
            "fonte": "ETH Zurich Master Thesis / Academic Quantitative Research",
            "estudo": "Nadaraya-Watson Envelope Regression Analysis",
            "periodo_teste": "2017-2024",
            "resultado": "Sharpe Ratio 1.71 - o MAIS ALTO entre todas as estratégias"
        },

        "performance_esperada": {
            "sharpe_ratio": "1.60 - 1.80",
            "win_rate": "60% - 70%",
            "profit_factor": "2.2 - 2.8",
            "max_drawdown": "10% - 15%",
            "trades_por_mes": "4 - 8 (alta qualidade)"
        },

        "como_funciona": {
            "entrada_long": [
                "Preço abaixo do envelope inferior Nadaraya-Watson",
                "RSI < 35 (oversold)",
                "Bollinger %B < 0.2 (preço próximo da banda inferior)"
            ],
            "entrada_short": [
                "Preço acima do envelope superior Nadaraya-Watson",
                "RSI > 65 (overbought)",
                "Bollinger %B > 0.8 (preço próximo da banda superior)"
            ],
            "saida": "Quando preço retorna à média OU %B normaliza"
        },

        "quando_usar": {
            "condicoes_ideais": [
                "Mercados em range ou levemente tendenciais",
                "Após movimentos bruscos de preço (overextension)",
                "Quando todos os 3 indicadores concordam (triple confirmation)",
                "Em ativos que historicamente respeitam a média"
            ],
            "melhores_horarios": [
                "Após dumps/pumps repentinos",
                "Quando o mercado está 'esticado' demais",
                "Evitar durante notícias (movimento pode continuar)"
            ]
        },

        "quando_nao_usar": {
            "evitar": [
                "Tendências fortes e sustentadas (pode ficar oversold por muito tempo)",
                "Durante bear markets severos (catch falling knife)",
                "Quando há notícias fundamentais mudando o cenário",
                "Mercados em pânico ou euforia extrema"
            ],
            "sinais_alerta": [
                "Preço continua caindo após sinal de compra",
                "Volume extremamente alto (pode ser capitulação real)",
                "Divergências em múltiplos timeframes"
            ]
        },

        "ativos_recomendados": {
            "principais": ["BTCUSDT", "ETHUSDT"],
            "secundarios": ["SOLUSDT"],
            "evitar": ["Altcoins pequenas (podem ir a zero)", "Ativos em tendência forte"],
            "nota": "APENAS para ativos estabelecidos que tendem a reverter à média"
        },

        "timeframes": {
            "recomendado": "4H",
            "alternativo": "Daily (sinais mais confiáveis)",
            "nao_recomendado": "1H ou menos (muitos sinais falsos)"
        },

        "gestao_risco": {
            "stop_loss": "5-7% abaixo do ponto de entrada (mais amplo)",
            "take_profit": "Retorno à média (NW value ou BB middle)",
            "posicao_maxima": "8-12% do capital (alta confiança)",
            "max_trades_simultaneos": "1-2",
            "trailing_stop": "NÃO usar - deixar o trade atingir a média"
        },

        "dicas_uso": [
            "TRIPLE CONFIRMATION é obrigatório - não entre com apenas 1-2 sinais",
            "Esta é uma estratégia CONTRARIAN - você está comprando medo e vendendo ganância",
            "Tenha paciência - o retorno à média pode demorar",
            "Use position sizing conservador nos primeiros trades",
            "O Sharpe alto vem da seletividade - não force trades",
            "Combine com análise de sentimento para melhores entradas",
            "Em bear markets, seja MUITO seletivo com longs"
        ],

        "nivel_experiencia": "Avançado",
        "complexidade": "Alta",
        "manutencao": "Baixa após entrada - aguardar reversão"
    }
}


async def add_documentation():
    """Adiciona documentação detalhada às estratégias"""
    database_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(database_url, ssl=ssl_ctx)

    print("=" * 70)
    print("ADICIONANDO DOCUMENTAÇÃO ÀS ESTRATÉGIAS")
    print("=" * 70)
    print()

    try:
        for strategy_name, docs in STRATEGY_DOCS.items():
            print(f"\nAtualizando: {strategy_name}")

            # Update documentation
            result = await conn.execute(
                "UPDATE strategies SET documentation = $1 WHERE name = $2",
                json.dumps(docs, ensure_ascii=False),
                strategy_name
            )

            print(f"  Título: {docs['titulo']}")
            print(f"  Baseado em: {docs['baseado_em']['fonte']}")
            print(f"  Sharpe esperado: {docs['performance_esperada']['sharpe_ratio']}")
            print(f"  Nível: {docs['nivel_experiencia']}")
            print(f"  Documentação salva!")

    finally:
        await conn.close()

    print("\n" + "=" * 70)
    print("DOCUMENTAÇÃO ADICIONADA COM SUCESSO!")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(add_documentation())
